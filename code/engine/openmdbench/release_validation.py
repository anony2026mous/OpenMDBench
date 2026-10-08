"""Repeatable MD-AD-002 release performance, batch, and soak gates."""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import time
import tracemalloc
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np

try:  # ``resource`` is POSIX-only; Windows needs a usable module to import at all.
    import resource
except ImportError:  # pragma: no cover - exercised on Windows only
    resource = None  # type: ignore[assignment]

from openmdbench.envs import OpenMDBenchEnv
from openmdbench.runners.md_ad_002 import (
    run_md_ad_002_easy,
    run_md_ad_002_hard,
    run_md_ad_002_medium,
)

SCENARIOS = ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD")


def _fd_count() -> int | None:
    return len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else None


def _rss_mb() -> float:
    if resource is None:
        # No ``getrusage`` on this platform; report 0.0 rather than failing the run.
        return 0.0
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def host_metadata() -> dict[str, object]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "rendering": "headless",
    }


def benchmark_training_sessions(session_count: int, *, ticks: int = 2) -> dict[str, object]:
    """Exercise independent formal environments in a synchronous training batch."""
    if session_count <= 0 or ticks <= 0:
        raise ValueError("session_count and ticks must be positive")
    environments = [
        OpenMDBenchEnv(scenario_id=SCENARIOS[index % len(SCENARIOS)], seed=index)
        for index in range(session_count)
    ]
    started = time.perf_counter()
    try:
        for index, environment in enumerate(environments):
            environment.reset(seed=index)
        identities = {id(environment._communication) for environment in environments}
        if len(identities) != session_count:
            raise RuntimeError("communication state leaked across training sessions")
        action = np.asarray((0.0, 0.0), dtype=np.float32)
        for _ in range(ticks):
            for environment in environments:
                environment.step(action)
    finally:
        for environment in environments:
            environment.close()
    elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "sessions": session_count,
        "ticks_per_session": ticks,
        "aggregate_ticks_per_second": session_count * ticks / elapsed,
        "elapsed_seconds": elapsed,
        "peak_rss_mb": _rss_mb(),
        "isolated_communication_objects": len(identities),
    }


def _batch_match(index_and_limit: tuple[int, int]) -> dict[str, object]:
    index, max_ticks = index_and_limit
    runners = (run_md_ad_002_easy, run_md_ad_002_medium, run_md_ad_002_hard)
    scenario = SCENARIOS[index % len(SCENARIOS)]
    result = runners[index % len(runners)](seed=index, max_ticks=max_ticks)
    if result.outcome == "in_progress":
        raise RuntimeError(f"batch match did not terminate: {scenario} seed={index}")
    return {
        "scenario_id": scenario,
        "seed": index,
        "ticks": result.ticks,
        "outcome": result.outcome,
        "reason": result.reason,
        "breaches": result.breaches,
    }


def run_batch_matches(
    count: int = 100, *, max_ticks: int = 1_800, workers: int = 1
) -> dict[str, object]:
    """Run a deterministic round-robin batch and reject crashes or unfinished matches."""
    if count <= 0 or max_ticks <= 0 or workers <= 0:
        raise ValueError("count and max_ticks must be positive")
    started = time.perf_counter()
    outcomes: dict[str, int] = {}
    inputs = tuple((index, max_ticks) for index in range(count))
    if workers == 1:
        summaries = [_batch_match(item) for item in inputs]
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as executor:
            summaries = list(executor.map(_batch_match, inputs))
    for summary in summaries:
        key = f"{summary['scenario_id']}:{summary['outcome']}"
        outcomes[key] = outcomes.get(key, 0) + 1
    return {
        "matches": count,
        "max_ticks": max_ticks,
        "workers": workers,
        "elapsed_seconds": time.perf_counter() - started,
        "outcomes": outcomes,
        "summaries": summaries,
        "peak_rss_mb": _rss_mb(),
    }


def soak_scenario(
    scenario_id: str, *, duration_seconds: float, steps_per_episode: int = 60
) -> dict[str, object]:
    """Churn one scenario until the wall-clock target while measuring owned resources."""
    if scenario_id not in SCENARIOS:
        raise ValueError("unknown MD-AD-002 scenario")
    if duration_seconds < 0.0 or steps_per_episode <= 0:
        raise ValueError("invalid soak duration or episode length")
    warmup = OpenMDBenchEnv(scenario_id=scenario_id, seed=0)
    warmup.reset(seed=0)
    warmup.step(np.asarray((0.0, 0.0), dtype=np.float32))
    warmup.close()
    gc.collect()
    fds_before = _fd_count()
    tracemalloc.start()
    heap_before, _ = tracemalloc.get_traced_memory()
    started = time.monotonic()
    deadline = started + duration_seconds
    episodes = 0
    ticks = 0
    action = np.asarray((0.0, 0.0), dtype=np.float32)
    while episodes == 0 or time.monotonic() < deadline:
        environment = OpenMDBenchEnv(scenario_id=scenario_id, seed=episodes)
        environment.reset(seed=episodes)
        try:
            for _ in range(steps_per_episode):
                _, _, terminated, truncated, _ = environment.step(action)
                ticks += 1
                if terminated or truncated:
                    break
        finally:
            environment.close()
        episodes += 1
    gc.collect()
    heap_after, peak_heap = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.monotonic() - started
    return {
        "scenario_id": scenario_id,
        "target_duration_seconds": duration_seconds,
        "duration_seconds": elapsed,
        "episodes": episodes,
        "ticks": ticks,
        "ticks_per_second": ticks / max(elapsed, 1e-12),
        "heap_growth_bytes": heap_after - heap_before,
        "peak_traced_heap_bytes": peak_heap,
        "fd_before": fds_before,
        "fd_after": _fd_count(),
        "peak_rss_mb": _rss_mb(),
    }


def write_report(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    concurrency = subparsers.add_parser("concurrency")
    concurrency.add_argument("--ticks", type=int, default=2)
    concurrency.add_argument("--output")
    batch = subparsers.add_parser("batch")
    batch.add_argument("--count", type=int, default=100)
    batch.add_argument("--max-ticks", type=int, default=1_800)
    batch.add_argument("--workers", type=int, default=4)
    batch.add_argument("--output")
    soak = subparsers.add_parser("soak")
    soak.add_argument("--scenario", choices=SCENARIOS, required=True)
    soak.add_argument("--hours", type=float, default=2.0)
    soak.add_argument("--steps-per-episode", type=int, default=60)
    soak.add_argument("--output")
    args = parser.parse_args()
    if args.command == "concurrency":
        payload = {
            "host": host_metadata(),
            "concurrency": [
                benchmark_training_sessions(16, ticks=args.ticks),
                benchmark_training_sessions(32, ticks=args.ticks),
            ],
        }
    elif args.command == "batch":
        payload = {
            "host": host_metadata(),
            "batch": run_batch_matches(args.count, max_ticks=args.max_ticks, workers=args.workers),
        }
    else:
        payload = {
            "host": host_metadata(),
            "soak": soak_scenario(
                args.scenario,
                duration_seconds=args.hours * 3_600.0,
                steps_per_episode=args.steps_per_episode,
            ),
        }
    if args.output:
        write_report(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

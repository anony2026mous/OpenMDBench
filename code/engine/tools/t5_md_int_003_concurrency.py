"""Run a bounded MD-INT-003 concurrent-session resource probe."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from openmdbench.policies.rule_v2 import FormalRuleAgentTeamV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from tools.t5_resource_probe import ResourceSample, sample_process

_SCENARIO_IDS = ("MD-INT-003-EASY", "MD-INT-003-MEDIUM", "MD-INT-003-HARD")


def _latency_summary_milliseconds(samples_seconds: list[float]) -> dict[str, float]:
    """Return stable nearest-rank tick latencies without a statistics dependency."""

    if not samples_seconds:
        raise ValueError("tick latency sample must not be empty")
    ordered = sorted(value * 1_000.0 for value in samples_seconds)

    def percentile(percent: float) -> float:
        index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percent)))
        return ordered[index]

    return {
        "mean": sum(ordered) / len(ordered),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
    }


def _sample_payload(sample: ResourceSample) -> dict[str, int | float | None]:
    return {
        "monotonic_seconds": sample.monotonic_seconds,
        "rss_bytes": sample.rss_bytes,
        "fd_count": sample.fd_count,
        "thread_count": sample.thread_count,
        "child_process_count": sample.child_process_count,
    }


def run_concurrency_probe(
    *,
    session_count: int,
    ticks: int,
    seed_base: int,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Advance independent formal sessions and report real parent-plus-child resources."""

    if session_count < 1 or ticks < 1:
        raise ValueError("session_count and ticks must both be positive")
    if scenario_id is not None and scenario_id not in _SCENARIO_IDS:
        raise ValueError("scenario_id must be one of the installed MD-INT-003 levels")
    sessions = []
    teams = []
    started = time.perf_counter()
    active_sample: ResourceSample | None = None
    try:
        for index in range(session_count):
            selected_scenario_id = (
                scenario_id
                if scenario_id is not None
                else _SCENARIO_IDS[index % len(_SCENARIO_IDS)]
            )
            seed = seed_base + index
            session = create_formal_session_v2(
                selected_scenario_id,
                session_id=f"t5.mdi3.concurrent.{index:03d}",
                seed=seed,
            )
            session.load().start()
            sessions.append(session)
            teams.append(FormalRuleAgentTeamV2.for_scenario(selected_scenario_id, seed=seed))
        started_sample = sample_process()
        for tick in range(ticks):
            for index, session in enumerate(sessions):
                teams[index](session)
                receipt = session.step(
                    operation_id=f"t5.mdi3.concurrent.{index:03d}.{tick}",
                    expected_tick=tick,
                )
                if receipt.tick != tick + 1:
                    raise RuntimeError("concurrent session did not advance exactly one tick")
        active_sample = sample_process()
        elapsed = time.perf_counter() - started
        return {
            "schema_version": "md3-concurrency-probe@1.0",
            "session_count": session_count,
            "ticks_per_session": ticks,
            "seed_base": seed_base,
            "scenario_id": scenario_id,
            "elapsed_seconds": elapsed,
            "aggregate_ticks_per_second": session_count * ticks / elapsed,
            "started_resources": _sample_payload(started_sample),
            "active_resources": _sample_payload(active_sample),
            "session_ticks": [session.world_view.tick for session in sessions],
        }
    finally:
        for session in reversed(sessions):
            session.stop().close()


def run_sequential_probe(
    *,
    session_count: int,
    ticks: int,
    seed_base: int,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Run complete independent matches while releasing each World before the next.

    This is deliberately distinct from the concurrent resource probe: complete
    tick histories are retained by a live World for authoritative audit, so a
    long batch closes one match before constructing the next instead of keeping
    many full histories resident at once.
    """
    if session_count < 1 or ticks < 1:
        raise ValueError("session_count and ticks must both be positive")
    if scenario_id is not None and scenario_id not in _SCENARIO_IDS:
        raise ValueError("scenario_id must be one of the installed MD-INT-003 levels")
    started = time.perf_counter()
    started_sample = sample_process()
    session_ticks: list[int] = []
    active_samples: list[ResourceSample] = []
    released_samples: list[ResourceSample] = []
    tick_latency_summaries: list[dict[str, float]] = []
    for index in range(session_count):
        selected_scenario_id = (
            scenario_id if scenario_id is not None else _SCENARIO_IDS[index % len(_SCENARIO_IDS)]
        )
        seed = seed_base + index
        session = create_formal_session_v2(
            selected_scenario_id,
            session_id=f"t5.mdi3.sequential.{index:03d}",
            seed=seed,
        )
        session.load().start()
        team = FormalRuleAgentTeamV2.for_scenario(selected_scenario_id, seed=seed)
        tick_durations_seconds: list[float] = []
        try:
            for tick in range(ticks):
                team(session)
                tick_started = time.perf_counter()
                receipt = session.step(
                    operation_id=f"t5.mdi3.sequential.{index:03d}.{tick}",
                    expected_tick=tick,
                )
                tick_durations_seconds.append(time.perf_counter() - tick_started)
                if receipt.tick != tick + 1:
                    raise RuntimeError("sequential session did not advance exactly one tick")
            session_ticks.append(session.world_view.tick)
            active_samples.append(sample_process())
            tick_latency_summaries.append(_latency_summary_milliseconds(tick_durations_seconds))
        finally:
            session.stop().close()
        released_samples.append(sample_process())
    elapsed = time.perf_counter() - started
    return {
        "schema_version": "md3-sequential-probe@1.0",
        "execution_mode": "sequential",
        "session_count": session_count,
        "ticks_per_session": ticks,
        "seed_base": seed_base,
        "scenario_id": scenario_id,
        "elapsed_seconds": elapsed,
        "aggregate_ticks_per_second": session_count * ticks / elapsed,
        "started_resources": _sample_payload(started_sample),
        "active_resources": [_sample_payload(sample) for sample in active_samples],
        "released_resources": [_sample_payload(sample) for sample in released_samples],
        "session_ticks": session_ticks,
        "step_latency_milliseconds": tick_latency_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, required=True)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--scenario-id", choices=_SCENARIO_IDS)
    parser.add_argument("--sequential", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        run = run_sequential_probe if args.sequential else run_concurrency_probe
        report = run(
            session_count=args.sessions,
            ticks=args.ticks,
            seed_base=args.seed_base,
            scenario_id=args.scenario_id,
        )
        if not args.sequential:
            report["released_resources"] = _sample_payload(sample_process())
        report["result"] = "passed"
    except Exception as error:
        report = {
            "schema_version": "md3-concurrency-probe@1.0",
            "session_count": args.sessions,
            "ticks_per_session": args.ticks,
            "seed_base": args.seed_base,
            "scenario_id": args.scenario_id,
            "execution_mode": "sequential" if args.sequential else "concurrent",
            "result": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "released_resources": _sample_payload(sample_process()),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

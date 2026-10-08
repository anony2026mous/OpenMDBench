"""Fixed CPU performance benchmarks and machine-readable results."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

try:  # ``resource`` is POSIX-only; Windows needs a usable module to import at all.
    import resource
except ImportError:  # pragma: no cover - exercised on Windows only
    resource = None  # type: ignore[assignment]

import numpy as np

from openmdbench.api.sessions import SessionStore
from openmdbench.envs import OpenMDBenchEnv, make_vector_env
from openmdbench.replay import ReplayReader, ReplayWriter
from openmdbench.visualization.schema import (
    DetectionSets,
    ReplayMetadata,
    ScoreSets,
    SideScore,
    VisualizationFrame,
)


def _rss_mb() -> float:
    if resource is None:
        # No ``getrusage`` on this platform; report 0.0 rather than failing the run.
        return 0.0
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def benchmark_scenario(scenario_id: str, ticks: int) -> dict[str, float | int | str]:
    env = OpenMDBenchEnv(scenario_id=scenario_id, seed=7)
    env.reset(seed=7)
    action = np.array([0.0, 0.0], dtype=np.float32)
    started = time.perf_counter()
    completed = 0
    for _ in range(ticks):
        _, _, terminated, truncated, _ = env.step(action)
        completed += 1
        if terminated or truncated:
            break
    elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "scenario_id": scenario_id,
        "ticks": completed,
        "elapsed_seconds": elapsed,
        "rtf": completed / elapsed,
        "peak_rss_mb": _rss_mb(),
    }


def benchmark_concurrency(session_count: int, ticks: int = 500) -> dict[str, float | int]:
    env = make_vector_env(tuple("MD-TRK-008" for _ in range(session_count)))
    env.reset(seed=list(range(session_count)))
    actions = np.zeros((session_count, 2), dtype=np.float32)
    started = time.perf_counter()
    for _ in range(ticks):
        env.step(actions)
    elapsed = max(time.perf_counter() - started, 1e-12)
    env.close()
    return {
        "sessions": session_count,
        "ticks_per_session": ticks,
        "aggregate_ticks_per_second": session_count * ticks / elapsed,
        "elapsed_seconds": elapsed,
    }


def benchmark_logging(ticks: int = 300) -> dict[str, float | int]:
    action = (1.0, 45.0)
    with tempfile.TemporaryDirectory(prefix="openmdbench-benchmark-") as temporary:
        store = SessionStore(replay_dir=temporary)
        session = store.create("MD-REC-001", 7)
        started = time.perf_counter()
        for _ in range(ticks):
            store.step(session, action)
        elapsed = max(time.perf_counter() - started, 1e-12)
        store.delete(session.session_id)
        size = (Path(temporary) / f"{session.session_id}.replay.jsonl").stat().st_size
    return {
        "ticks": ticks,
        "elapsed_seconds": elapsed,
        "ticks_per_second": ticks / elapsed,
        "bytes": size,
        "bytes_per_tick": size / ticks,
    }


def benchmark_replay(frame_count: int = 5_000) -> dict[str, float | int]:
    with tempfile.TemporaryDirectory(prefix="openmdbench-replay-") as temporary:
        path = Path(temporary) / "benchmark.jsonl"
        metadata = ReplayMetadata(
            match_id="benchmark",
            scenario_id="MD-REC-001",
            seed=7,
            tick_seconds=1.0,
            coordinate_system="local_enu",
            engine_version="0.1.0",
            config_hash="sha256:abc",
        )
        scores = ScoreSets(blue=SideScore(total=0.0), red=SideScore(total=0.0))
        with ReplayWriter(path, metadata, flush_every=1_000) as writer:
            for timestamp in range(frame_count):
                writer.write_frame(
                    VisualizationFrame(
                        timestamp=timestamp,
                        entities=(),
                        detections=DetectionSets(),
                        scores=scores,
                    )
                )
        reader = ReplayReader(path)
        started = time.perf_counter()
        count = sum(1 for _ in reader.frames())
        elapsed = max(time.perf_counter() - started, 1e-12)
    return {
        "frames": count,
        "elapsed_seconds": elapsed,
        "frames_per_second": count / elapsed,
    }


def run_benchmark_suite() -> dict[str, Any]:
    return {
        "scenarios": [
            benchmark_scenario("MD-REC-001", 1_200),
            benchmark_scenario("MD-TRK-008", 2_400),
            benchmark_scenario("MD-AD-006", 10_800),
        ],
        "concurrency": [benchmark_concurrency(4), benchmark_concurrency(8)],
        "logging": benchmark_logging(),
        "replay": benchmark_replay(),
        "peak_rss_mb": _rss_mb(),
    }

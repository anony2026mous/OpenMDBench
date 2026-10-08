"""Long-duration session churn and resource-release checks."""

from __future__ import annotations

import gc
import os
import time
import tracemalloc
from typing import Any

from openmdbench.api.sessions import SessionStore


def _fd_count() -> int | None:
    path = "/proc/self/fd"
    return len(os.listdir(path)) if os.path.isdir(path) else None


def run_soak(
    *,
    duration_seconds: float,
    minimum_sessions: int = 1_000,
    steps_per_session: int = 2,
) -> dict[str, Any]:
    if duration_seconds < 0.0 or minimum_sessions <= 0 or steps_per_session < 0:
        raise ValueError("duration must be non-negative and session counts must be valid")
    store = SessionStore()
    for seed in range(10):
        warmup = store.create("MD-REC-001", seed)
        store.delete(warmup.session_id)
    gc.collect()
    fds_before = _fd_count()
    tracemalloc.start()
    heap_before, _ = tracemalloc.get_traced_memory()
    started = time.monotonic()
    deadline = started + duration_seconds
    completed = 0
    while completed < minimum_sessions or time.monotonic() < deadline:
        session = store.create("MD-REC-001", completed)
        for _ in range(steps_per_session):
            store.step(session, (0.0, 0.0))
        store.delete(session.session_id)
        completed += 1
    gc.collect()
    heap_after, peak_heap = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    fds_after = _fd_count()
    elapsed = time.monotonic() - started
    return {
        "completed_sessions": completed,
        "duration_seconds": elapsed,
        "target_duration_seconds": duration_seconds,
        "steps_per_session": steps_per_session,
        "active_sessions": store.active_count,
        "heap_growth_bytes": heap_after - heap_before,
        "peak_traced_heap_bytes": peak_heap,
        "fd_before": fds_before,
        "fd_after": fds_after,
    }

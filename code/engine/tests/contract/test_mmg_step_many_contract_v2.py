"""PERF-01 red tests for one-RPC MMG substep batching.

The production worker is used where numerical/IPC equivalence matters.  The
atomic-failure case drives the child-only engine directly so it can inject a
failure at an exact substep without adding a testing escape hatch to the RPC.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


def _worker_api() -> Any:
    from openmdbench.dynamics import sim2sea_mmg_worker

    return sim2sea_mmg_worker


def _state(*, x_m: float = 10.0, y_m: float = 20.0) -> SimpleNamespace:
    return SimpleNamespace(
        position_m=(x_m, y_m, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
        heading_deg=0.0,
    )


def _core() -> Any:
    core = _worker_api().spawn_sim2sea_mmg_core_v2()
    core.set_state(_state())
    return core


def test_p01_substeps_one_is_exactly_one_legacy_step() -> None:
    legacy = _core()
    batched = _core()
    try:
        expected = legacy.step(nps=2.0, rudder_rad=0.1, dt_s=0.1)
        assert batched.step_many(nps=2.0, rudder_rad=0.1, dt_s=0.1, substeps=1) == expected
    finally:
        legacy.close()
        batched.close()


def test_p01_many_matches_strictly_ordered_legacy_substeps() -> None:
    legacy = _core()
    batched = _core()
    try:
        expected: tuple[float, ...] = ()
        for _ in range(4):
            expected = legacy.step(nps=3.0, rudder_rad=-0.2, dt_s=0.1)
        assert batched.step_many(nps=3.0, rudder_rad=-0.2, dt_s=0.1, substeps=4) == expected
    finally:
        legacy.close()
        batched.close()


@pytest.mark.parametrize("substeps", (True, 0, -1, 1.0, 257))
def test_p01_invalid_substeps_are_rejected_stably(substeps: object) -> None:
    core = _core()
    try:
        with pytest.raises(ValueError):
            core.step_many(nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=substeps)
    finally:
        core.close()


def test_p01_child_failure_at_substep_rolls_back_engine_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _worker_api()
    engine = api._Sim2SeaMMGWorkerEngine()
    engine.set_state(
        {
            "position_m": [10.0, 20.0, 0.0],
            "velocity_mps": [0.0, 0.0, 0.0],
            "heading_deg": 0.0,
        }
    )
    before = engine.snapshot()
    calls = 0

    class _Core:
        def core_init(self, *_values: object) -> None:
            return None

    class _Runtime:
        def core_for(self, *_values: object) -> _Core:
            return _Core()

    def staged_failure(**_values: object) -> tuple[float, ...]:
        nonlocal calls
        calls += 1
        engine._position_m = (10.0 + calls, 20.0, 0.0)
        if calls == 3:
            raise ValueError("injected substep failure")
        return (10.0 + calls, 20.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(engine, "_advance_prepared_substep", staged_failure)
    with pytest.raises(ValueError, match="injected substep failure"):
        engine.step_many(runtime=_Runtime(), nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=4)
    assert calls == 3
    assert engine.snapshot() == before


def test_p01_checkpoint_restore_preserves_first_batched_step() -> None:
    source = _core()
    restored = _core()
    try:
        source.step_many(nps=2.5, rudder_rad=0.05, dt_s=0.1, substeps=3)
        checkpoint = source.snapshot()
        expected = source.step_many(nps=2.5, rudder_rad=0.05, dt_s=0.1, substeps=3)
        restored.restore(dict(checkpoint))
        assert restored.step_many(nps=2.5, rudder_rad=0.05, dt_s=0.1, substeps=3) == expected
    finally:
        source.close()
        restored.close()


def test_p01_closed_worker_handle_fails_without_silent_retry_and_new_handle_recovers() -> None:
    closed = _core()
    closed.close()
    with pytest.raises(ValueError):
        closed.step_many(nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=1)

    replacement = _core()
    try:
        result = replacement.step_many(nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=1)
        assert len(result) == 6
    finally:
        replacement.close()


def test_p01_worker_disconnect_is_visible_and_fresh_handle_starts_new_worker() -> None:
    disconnected = _core()
    process = disconnected._worker._process
    process.terminate()
    process.join(timeout=5.0)
    assert not process.is_alive()
    try:
        with pytest.raises(ValueError):
            disconnected.step_many(nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=1)
    finally:
        # The process is already gone, so release cannot receive its normal acknowledgement.
        # Mark only this test-owned handle closed before creating the replacement worker.
        disconnected._closed = True

    replacement = _core()
    try:
        assert len(replacement.step_many(nps=1.0, rudder_rad=0.0, dt_s=0.1, substeps=1)) == 6
    finally:
        replacement.close()

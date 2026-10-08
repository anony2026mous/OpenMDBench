"""RF-08 real runner timing and ownership contracts."""

from __future__ import annotations

from threading import Event

import pytest
from openmdbench.sessions.runners_v2 import (
    ContinuousRunnerV2,
    LockstepRunnerV2,
    ReplayRunnerV2,
    RunnerConfigV2,
    RunnerFailureV2,
)
from tests.integration.test_session_action_world_v2 import _session


@pytest.mark.parametrize("decision_interval", (1, 10, 100))
def test_lockstep_runner_advances_exact_decision_interval(decision_interval: int) -> None:
    session = _session(f"session.lockstep.{decision_interval}").load().start()
    runner = LockstepRunnerV2(
        session=session,
        config=RunnerConfigV2(
            physics_dt_seconds=1.0,
            decision_interval_ticks=decision_interval,
            speed_ratio=1.0,
        ),
    )
    receipt = runner.step(operation_id="decision.000", expected_tick=0)
    assert receipt.start_tick == 0
    assert receipt.end_tick == decision_interval
    assert len(receipt.tick_receipts) == decision_interval
    assert session.world_view.tick == decision_interval


@pytest.mark.parametrize("speed_ratio", (1.0, 10.0, float("inf")))
def test_speed_ratio_changes_only_wall_pacing(speed_ratio: float) -> None:
    session = _session(f"session.speed.{speed_ratio}").load().start()
    sleeps: list[float] = []
    runner = ContinuousRunnerV2(
        session=session,
        config=RunnerConfigV2(
            physics_dt_seconds=1.0,
            decision_interval_ticks=1,
            speed_ratio=speed_ratio,
        ),
        sleep=sleeps.append,
    )
    receipts = runner.run_steps(steps=3, operation_prefix="continuous")
    assert tuple(item.end_tick for item in receipts) == (1, 2, 3)
    assert len(sleeps) == (0 if speed_ratio == float("inf") else 3)
    if sleeps:
        assert sleeps == [1.0 / speed_ratio] * 3


def test_pause_resume_and_terminate_are_linearized_with_writer_thread() -> None:
    session = _session("session.threaded").load().start()
    entered = Event()
    release = Event()

    def controlled_sleep(_duration: float) -> None:
        entered.set()
        release.wait(timeout=2.0)

    runner = ContinuousRunnerV2(
        session=session,
        config=RunnerConfigV2(
            physics_dt_seconds=1.0,
            decision_interval_ticks=1,
            speed_ratio=1.0,
        ),
        sleep=controlled_sleep,
    )
    runner.start(operation_prefix="background")
    assert entered.wait(timeout=2.0)
    runner.pause()
    paused_tick = session.world_view.tick
    release.set()
    runner.resume()
    runner.terminate(timeout_seconds=2.0)
    assert session.world_view.tick >= paused_tick
    assert not runner.is_alive


def test_replay_runner_is_read_only_and_never_accepts_session_or_world() -> None:
    records = ({"tick": 0, "value": "a"}, {"tick": 1, "value": "b"})
    runner = ReplayRunnerV2(records=records)
    assert runner.next() == records[0]
    assert runner.seek(1) == records[1]
    assert runner.next() is None
    assert not hasattr(runner, "session")
    assert not hasattr(runner, "world")


def test_runner_rejects_mode_timing_and_tick_mismatch_without_mutation() -> None:
    session = _session("session.runner.reject").load().start()
    before = session.world_view.checkpoint()
    with pytest.raises(RunnerFailureV2):
        LockstepRunnerV2(
            session=session,
            config=RunnerConfigV2(
                physics_dt_seconds=0.5,
                decision_interval_ticks=1,
                speed_ratio=1.0,
            ),
        )
    runner = LockstepRunnerV2(
        session=session,
        config=RunnerConfigV2(
            physics_dt_seconds=1.0,
            decision_interval_ticks=1,
            speed_ratio=1.0,
        ),
    )
    with pytest.raises(RunnerFailureV2):
        runner.step(operation_id="wrong.tick", expected_tick=1)
    assert session.world_view.checkpoint() == before


def test_session_stop_and_runner_close_release_background_writer() -> None:
    session = _session("session.runner.release").load().start()
    runner = ContinuousRunnerV2(
        session=session,
        config=RunnerConfigV2(
            physics_dt_seconds=1.0,
            decision_interval_ticks=1,
            speed_ratio=float("inf"),
        ),
        sleep=lambda _duration: None,
    ).start(operation_prefix="release")
    session.stop()
    runner.close()
    session.close()
    assert not runner.is_alive

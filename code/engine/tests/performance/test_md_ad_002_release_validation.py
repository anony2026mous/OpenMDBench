"""Fast contract tests for the separately runnable AD2-11 release gates."""

from collections.abc import Callable
from typing import cast

from openmdbench.release_validation import (
    benchmark_training_sessions,
    run_batch_matches,
    soak_scenario,
)


def test_training_session_benchmark_validates_isolation() -> None:
    result = benchmark_training_sessions(3, ticks=1)
    assert result["isolated_communication_objects"] == 3
    assert cast(float, result["aggregate_ticks_per_second"]) > 0


def test_batch_and_soak_validation_reject_invalid_limits() -> None:
    operations: tuple[Callable[[], object], ...] = (
        lambda: run_batch_matches(0),
        lambda: soak_scenario("unknown", duration_seconds=0),
    )
    for operation in operations:
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError("release gate must reject an invalid limit")


def test_zero_duration_soak_completes_one_episode_and_releases_resources() -> None:
    result = soak_scenario("MD-AD-002-EASY", duration_seconds=0.0, steps_per_episode=1)
    assert result["episodes"] == 1
    assert result["ticks"] == 1
    assert result["fd_after"] == result["fd_before"]

"""Short-session churn and resource-release stability test."""

from openmdbench.soak import run_soak


def test_one_thousand_short_sessions_release_resources() -> None:
    result = run_soak(duration_seconds=0.0, minimum_sessions=1_000, steps_per_session=1)
    assert result["completed_sessions"] == 1_000
    assert result["active_sessions"] == 0
    assert result["heap_growth_bytes"] < 5 * 1024 * 1024
    if result["fd_before"] is not None:
        assert result["fd_after"] == result["fd_before"]

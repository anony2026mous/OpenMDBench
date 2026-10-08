"""M0 command-line surface smoke acceptance test."""

from openmdbench.cli.__main__ import _run_surface_smoke


def test_surface_smoke_runs_1000_ticks() -> None:
    result = _run_surface_smoke(seed=7, ticks=1_000)
    assert result["ticks"] == 1_000
    assert result["terminated"] is False
    assert result["truncated"] is True
    assert result["seed"] == 7

"""Sim2Sea MMG adapter conversion and delegation tests."""

import math

import numpy as np
import pytest
from openmdbench.domains.surface.mmg_adapter import MMGState, Sim2SeaMMGAdapter


def test_adapter_converts_heading_to_rudder_and_calls_sim2sea() -> None:
    adapter = Sim2SeaMMGAdapter(
        MMGState(
            position_xy_m=(100.0, 200.0),
            heading_deg=0.0,
            body_velocity_mps=(0.0, 0.0, 0.0),
        ),
        substeps=10,
    )
    result = adapter.step_target(target_speed_mps=7.7, target_heading_deg=90.0)
    assert adapter.last_trace is not None
    assert adapter.last_trace.solver == "sim2sea_mmg"
    assert adapter.last_trace.integrator == "sim2sea_rk4"
    assert adapter.last_trace.nps == pytest.approx(5.0 * 7.7 / 12.9)
    assert adapter.last_trace.rudder_rad == pytest.approx(-0.3)
    assert adapter.last_trace.rudder_rad != math.radians(90.0)
    assert np.isfinite(result.position_xy_m).all()


def test_adapter_rejects_target_speed_outside_usv_contract() -> None:
    adapter = Sim2SeaMMGAdapter(
        MMGState(
            position_xy_m=(0.0, 0.0),
            heading_deg=0.0,
            body_velocity_mps=(0.0, 0.0, 0.0),
        ),
        substeps=10,
    )
    with pytest.raises(ValueError, match="target_speed"):
        adapter.step_target(target_speed_mps=13.0, target_heading_deg=0.0)


def test_shared_core_caches_owner_but_reloads_when_vessels_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A vessel continues without reset; a different vessel restores itself."""
    first = Sim2SeaMMGAdapter(
        MMGState(
            position_xy_m=(100.0, 0.0),
            heading_deg=0.0,
            body_velocity_mps=(0.0, 0.0, 0.0),
        )
    )
    second = Sim2SeaMMGAdapter(
        MMGState(
            position_xy_m=(-100.0, 0.0),
            heading_deg=0.0,
            body_velocity_mps=(0.0, 0.0, 0.0),
        )
    )
    initialize = first._initialize_core
    initialization_count = 0

    def count_and_initialize(state: MMGState) -> None:
        nonlocal initialization_count
        initialization_count += 1
        initialize(state)

    monkeypatch.setattr(first, "_initialize_core", count_and_initialize)
    first.step_target(target_speed_mps=5.0, target_heading_deg=0.0)
    first.step_target(target_speed_mps=5.0, target_heading_deg=0.0)

    assert initialization_count == 1

    restored_second = second.step_target(target_speed_mps=5.0, target_heading_deg=0.0)
    assert restored_second.position_xy_m[0] < 0.0

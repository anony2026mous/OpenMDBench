"""Public navigation must remain independent of MMG actuator details."""

from __future__ import annotations

import pytest
from openmdbench.domains.surface.controller_v2 import mmg_navigation_action_v2

_PARAMETERS = {
    "max_speed_mps": 12.9,
    "max_nps": 60.0,
    "max_rudder_rad": 0.3,
    "controller_gain": 1.0,
}


def test_navigation_maps_speed_and_heading_to_bounded_mmg_actuators() -> None:
    action = mmg_navigation_action_v2(
        current_heading_deg=0.0,
        target_speed_mps=6.45,
        target_heading_deg=90.0,
        parameters=_PARAMETERS,
    )
    assert action.nps == pytest.approx(30.0)
    assert action.rudder_rad == pytest.approx(-0.3)


def test_navigation_clamps_only_to_the_selected_vessel_speed_profile() -> None:
    action = mmg_navigation_action_v2(
        current_heading_deg=350.0,
        target_speed_mps=50.0,
        target_heading_deg=10.0,
        parameters=_PARAMETERS,
    )
    assert action.nps == pytest.approx(60.0)
    assert action.rudder_rad == pytest.approx(-0.3)


@pytest.mark.parametrize(
    "parameters",
    (
        {**_PARAMETERS, "max_nps": 240.1},
        {**_PARAMETERS, "max_rudder_rad": 0.31},
        {**_PARAMETERS, "controller_gain": 0.0},
    ),
)
def test_navigation_rejects_controller_profiles_outside_trusted_mmg_limits(
    parameters: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        mmg_navigation_action_v2(
            current_heading_deg=0.0,
            target_speed_mps=1.0,
            target_heading_deg=0.0,
            parameters=parameters,
        )

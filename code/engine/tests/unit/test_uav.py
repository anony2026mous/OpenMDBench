"""UAV kinematic-boundary and silhouette tests."""

import numpy as np
import pytest
from openmdbench.domains.air import UAVCommand, UAVState, step_uav, uav_path
from openmdbench.domains.surface import usv_path
from pydantic import ValidationError


def test_uav_turn_and_climb_are_rate_limited() -> None:
    state = UAVState(position=(0.0, 0.0, 100.0), heading_deg=0.0, speed_mps=40.0)
    command = UAVCommand(heading_deg=90.0, speed_mps=80.0, altitude_m=1000.0)
    result = step_uav(state, command)
    assert result.heading_deg == pytest.approx(30.0)
    assert result.position[2] == pytest.approx(120.0)
    assert result.speed_mps == 48.0


@pytest.mark.parametrize(
    ("heading", "expected"),
    [(0.0, (0.0, 40.0)), (90.0, (40.0, 0.0)), (180.0, (0.0, -40.0)), (270.0, (-40.0, 0.0))],
)
def test_uav_cardinal_heading_motion(heading: float, expected: tuple[float, float]) -> None:
    state = UAVState(position=(0.0, 0.0, 100.0), heading_deg=heading, speed_mps=40.0)
    result = step_uav(
        state,
        UAVCommand(heading_deg=heading, speed_mps=40.0, altitude_m=100.0),
    )
    assert result.position[:2] == pytest.approx(expected, abs=1e-12)


def test_uav_shortest_turn_crosses_zero_and_speed_response_is_bounded() -> None:
    state = UAVState(position=(0.0, 0.0, 100.0), heading_deg=350.0, speed_mps=40.0)
    accelerated = step_uav(
        state,
        UAVCommand(heading_deg=10.0, speed_mps=80.0, altitude_m=100.0),
    )
    assert accelerated.heading_deg == pytest.approx(10.0)
    assert accelerated.speed_mps == pytest.approx(48.0)
    decelerated = step_uav(
        accelerated,
        UAVCommand(heading_deg=10.0, speed_mps=0.0, altitude_m=100.0),
    )
    assert decelerated.speed_mps == pytest.approx(38.0)


def test_degraded_uav_limits_speed_and_turn_rate() -> None:
    state = UAVState(position=(0.0, 0.0, 2995.0), heading_deg=0.0, speed_mps=70.0)
    result = step_uav(
        state,
        UAVCommand(heading_deg=90.0, speed_mps=80.0, altitude_m=3000.0),
        performance_factor=0.7,
    )
    assert result.heading_deg == pytest.approx(21.0)
    assert result.speed_mps == pytest.approx(56.0)
    assert result.position[2] == pytest.approx(3000.0)


@pytest.mark.parametrize(
    "command",
    [
        {"heading_deg": 0.0, "speed_mps": 80.1, "altitude_m": 100.0},
        {"heading_deg": 0.0, "speed_mps": 40.0, "altitude_m": 3000.1},
    ],
)
def test_uav_rejects_speed_and_altitude_outside_limits(command: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        UAVCommand(**command)


def test_uav_path_faces_north_and_differs_from_usv() -> None:
    uav_vertices = np.asarray(uav_path().vertices)
    usv_vertices = np.asarray(usv_path().vertices)
    nose = uav_vertices[np.argmax(uav_vertices[:, 1])]
    np.testing.assert_allclose(nose, [0.0, 0.55])
    assert uav_vertices.shape != usv_vertices.shape

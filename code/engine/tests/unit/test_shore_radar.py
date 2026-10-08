"""Fixed shore-radar command and icon tests."""

import numpy as np
import pytest
from openmdbench.domains.shore import ShoreRadarState, apply_shore_command, shore_radar_path


def test_shore_radar_rejects_move_and_keeps_position() -> None:
    state = ShoreRadarState(position=(10.0, 20.0, 0.0))
    with pytest.raises(ValueError, match="rejects movement"):
        apply_shore_command(state, "move_to", {"target": [100.0, 100.0, 0.0]})
    held = apply_shore_command(state, "hold_position", {})
    assert held.position == state.position


def test_directional_sensor_updates_beam_but_not_facility_position() -> None:
    state = ShoreRadarState(position=(10.0, 20.0, 0.0))
    updated = apply_shore_command(
        state,
        "set_sensor_mode",
        {"mode": "sector_scan", "beam_heading_deg": 135.0},
    )
    assert updated.beam_heading_deg == 135.0
    assert updated.position == state.position


def test_radar_icon_has_north_facing_antenna() -> None:
    vertices = np.asarray(shore_radar_path().vertices)
    top = vertices[np.argmax(vertices[:, 1])]
    np.testing.assert_allclose(top, [0.0, 0.5])

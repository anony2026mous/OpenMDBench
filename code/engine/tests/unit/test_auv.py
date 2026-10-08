"""AUV motion-boundary, collision, and silhouette tests."""

import numpy as np
import pytest
from openmdbench.domains.surface import usv_path
from openmdbench.domains.underwater import AUVCommand, AUVState, auv_geometry, auv_path, step_auv
from openmdbench.schemas.geometry import CollisionShape
from pydantic import ValidationError


def test_auv_turn_and_depth_change_are_rate_limited() -> None:
    state = AUVState(position=(0.0, 0.0, -10.0), heading_deg=0.0, speed_mps=2.1)
    command = AUVCommand(heading_deg=90.0, speed_mps=4.1, depth_m=300.0)
    result = step_auv(state, command)
    assert result.heading_deg == pytest.approx(15.0)
    assert result.position[2] == pytest.approx(-12.0)


@pytest.mark.parametrize("depth", [-0.1, 300.1])
def test_auv_command_cannot_cross_surface_or_maximum_depth(depth: float) -> None:
    with pytest.raises(ValidationError):
        AUVCommand(heading_deg=0.0, speed_mps=2.1, depth_m=depth)


def test_auv_uses_capsule_and_distinct_torpedo_outline() -> None:
    assert auv_geometry().collision_shape is CollisionShape.CAPSULE
    auv_vertices = np.asarray(auv_path().vertices)
    usv_vertices = np.asarray(usv_path().vertices)
    assert auv_vertices.shape != usv_vertices.shape
    np.testing.assert_allclose(auv_vertices[np.argmax(auv_vertices[:, 1])], [0.0, 0.52])

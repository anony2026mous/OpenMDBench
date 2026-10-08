"""Legacy obstacle compatibility and control-isolation tests."""

import numpy as np
from openmdbench.core.entities import DynamicObstacle, PlatformAsset
from openmdbench.domains.surface.obstacles import (
    LegacyCircleObstacle,
    ObstacleProfile,
    adapt_legacy_obstacle,
    civilian_vessel_path,
)


def test_old_circle_obstacle_loads_with_compatible_profile() -> None:
    legacy = LegacyCircleObstacle(id="circle-1", x=10.0, y=20.0, radius_m=5.0)
    entity = adapt_legacy_obstacle(legacy)
    assert isinstance(entity, DynamicObstacle)
    assert not isinstance(entity, PlatformAsset)
    assert entity.obstacle_type == ObstacleProfile.CIRCLE.value


def test_civilian_profile_remains_non_controllable_and_has_ship_outline() -> None:
    legacy = LegacyCircleObstacle(
        id="civilian-1",
        x=10.0,
        y=20.0,
        radius_m=5.0,
        profile=ObstacleProfile.CIVILIAN_VESSEL,
    )
    entity = adapt_legacy_obstacle(legacy)
    assert entity.obstacle_type == "civilian_vessel"
    vertices = np.asarray(civilian_vessel_path().vertices)
    np.testing.assert_allclose(vertices[np.argmax(vertices[:, 1])], [0.0, 0.5])

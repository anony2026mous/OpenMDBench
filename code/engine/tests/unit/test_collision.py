"""Entity, vertical-layer, terrain-line, and no-go-zone collision tests."""

from openmdbench.core.entities import Domain
from openmdbench.systems.collision import (
    CollisionBody,
    collides_with_body,
    collides_with_segments,
    point_in_polygon,
    swept_collision,
    swept_path_crosses_segments,
    swept_points_collide,
)


def test_same_xy_is_safe_when_altitude_or_depth_is_separated() -> None:
    surface = CollisionBody("usv", Domain.SURFACE, (0.0, 0.0, 0.0), 10.0, 4.0)
    uav = CollisionBody("uav", Domain.AIR, (0.0, 0.0, 100.0), 10.0, 4.0)
    auv = CollisionBody("auv", Domain.UNDERWATER, (0.0, 0.0, -50.0), 10.0, 4.0)
    assert not collides_with_body(surface, uav)
    assert not collides_with_body(surface, auv)


def test_entities_in_same_layer_collide_using_geometry() -> None:
    first = CollisionBody("usv-1", Domain.SURFACE, (0.0, 0.0, 0.0), 10.0, 4.0)
    second = CollisionBody("usv-2", Domain.SURFACE, (5.0, 0.0, 0.0), 10.0, 4.0)
    assert collides_with_body(first, second)


def test_usv_line_obstacle_compatibility() -> None:
    usv = CollisionBody("usv", Domain.SURFACE, (5.0, 1.0, 0.0), 10.0, 4.0)
    segments = (((0.0, 0.0), (10.0, 0.0)),)
    assert collides_with_segments(usv, segments)


def test_no_go_polygon_contains_reference_point() -> None:
    polygon = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    assert point_in_polygon((5.0, 5.0), polygon)
    assert not point_in_polygon((20.0, 5.0), polygon)


def test_swept_collision_detects_tunneling_between_clear_endpoints() -> None:
    assert swept_points_collide(
        (-10.0, 0.0, 100.0),
        (10.0, 0.0, 100.0),
        (0.0, -10.0, 100.0),
        (0.0, 10.0, 100.0),
        horizontal_limit_m=2.0,
    )
    assert swept_path_crosses_segments((-10.0, 0.0), (10.0, 0.0), (((0.0, -5.0), (0.0, 5.0)),))
    assert not swept_path_crosses_segments((-10.0, 0.0), (10.0, 0.0), (((20.0, 0.0), (30.0, 0.0)),))


def test_swept_collision_returns_reproducible_impact_evidence() -> None:
    evidence = swept_collision(
        (-10.0, 0.0, 100.0),
        (10.0, 0.0, 100.0),
        (0.0, -10.0, 100.0),
        (0.0, 10.0, 100.0),
        horizontal_limit_m=2.0,
    )
    assert evidence is not None
    assert evidence.closest_fraction == 0.5
    assert evidence.impact_position == (0.0, 0.0, 100.0)
    assert evidence.horizontal_separation_m == 0.0
    assert evidence.vertical_separation_m == 0.0
    assert round(evidence.relative_speed_mps, 6) == round(20.0 * 2.0**0.5, 6)

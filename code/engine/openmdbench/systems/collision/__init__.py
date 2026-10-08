"""Unified collision and exclusion-zone checks."""

from openmdbench.systems.collision.model import (
    CollisionBody,
    SweptCollision,
    collides_with_body,
    collides_with_segments,
    point_in_polygon,
    swept_collision,
    swept_path_crosses_segments,
    swept_points_collide,
)

__all__ = [
    "CollisionBody",
    "SweptCollision",
    "collides_with_body",
    "collides_with_segments",
    "point_in_polygon",
    "swept_path_crosses_segments",
    "swept_collision",
    "swept_points_collide",
]

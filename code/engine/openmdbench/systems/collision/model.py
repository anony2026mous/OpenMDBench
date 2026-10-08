"""Configurable broad-phase geometry with vertical domain separation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from openmdbench.core.entities import Domain


@dataclass(frozen=True, slots=True)
class CollisionBody:
    entity_id: str
    domain: Domain
    position: tuple[float, float, float]
    length_m: float
    width_m: float
    vertical_separation_m: float = 5.0

    @property
    def horizontal_radius_m(self) -> float:
        return 0.5 * math.hypot(self.length_m, self.width_m)


@dataclass(frozen=True, slots=True)
class SweptCollision:
    closest_fraction: float
    first_position: tuple[float, float, float]
    second_position: tuple[float, float, float]
    impact_position: tuple[float, float, float]
    horizontal_separation_m: float
    vertical_separation_m: float
    relative_speed_mps: float


def collides_with_body(first: CollisionBody, second: CollisionBody) -> bool:
    vertical_distance = abs(first.position[2] - second.position[2])
    vertical_limit = max(first.vertical_separation_m, second.vertical_separation_m)
    if vertical_distance > vertical_limit:
        return False
    horizontal_distance = math.dist(first.position[:2], second.position[:2])
    return horizontal_distance <= first.horizontal_radius_m + second.horizontal_radius_m


def _distance_to_segment(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    segment_x = end[0] - start[0]
    segment_y = end[1] - start[1]
    length_squared = segment_x**2 + segment_y**2
    if length_squared == 0.0:
        return math.dist(point, start)
    projection = (
        (point[0] - start[0]) * segment_x + (point[1] - start[1]) * segment_y
    ) / length_squared
    projection = max(0.0, min(1.0, projection))
    closest = (start[0] + projection * segment_x, start[1] + projection * segment_y)
    return math.dist(point, closest)


def collides_with_segments(
    body: CollisionBody,
    segments: tuple[tuple[tuple[float, float], tuple[float, float]], ...],
) -> bool:
    """Retain legacy USV line-obstacle collision capability."""
    return any(
        _distance_to_segment(body.position[:2], start, end) <= body.width_m / 2.0
        for start, end in segments
    )


def swept_points_collide(
    first_start: tuple[float, float, float],
    first_end: tuple[float, float, float],
    second_start: tuple[float, float, float],
    second_end: tuple[float, float, float],
    *,
    horizontal_limit_m: float,
    vertical_limit_m: float = 5.0,
) -> bool:
    """Detect closest approach during one synchronous linear movement interval."""
    return (
        swept_collision(
            first_start,
            first_end,
            second_start,
            second_end,
            horizontal_limit_m=horizontal_limit_m,
            vertical_limit_m=vertical_limit_m,
        )
        is not None
    )


def swept_collision(
    first_start: tuple[float, float, float],
    first_end: tuple[float, float, float],
    second_start: tuple[float, float, float],
    second_end: tuple[float, float, float],
    *,
    horizontal_limit_m: float,
    vertical_limit_m: float = 5.0,
    tick_seconds: float = 1.0,
) -> SweptCollision | None:
    """Return deterministic closest-approach evidence for a swept 3-D collision."""
    if min(horizontal_limit_m, vertical_limit_m) < 0.0 or tick_seconds <= 0.0:
        raise ValueError("collision limits must be nonnegative and tick_seconds positive")
    relative_start = tuple(a - b for a, b in zip(first_start, second_start, strict=True))
    relative_delta = tuple(
        (a1 - a0) - (b1 - b0)
        for a0, a1, b0, b1 in zip(first_start, first_end, second_start, second_end, strict=True)
    )
    denominator = sum(value * value for value in relative_delta)
    closest_t = (
        0.0
        if denominator == 0.0
        else max(
            0.0,
            min(
                1.0,
                -sum(a * b for a, b in zip(relative_start, relative_delta, strict=True))
                / denominator,
            ),
        )
    )
    closest_relative = tuple(
        start + closest_t * delta
        for start, delta in zip(relative_start, relative_delta, strict=True)
    )
    horizontal_separation = math.hypot(closest_relative[0], closest_relative[1])
    vertical_separation = abs(closest_relative[2])
    if horizontal_separation > horizontal_limit_m or vertical_separation > vertical_limit_m:
        return None
    first_position = (
        first_start[0] + closest_t * (first_end[0] - first_start[0]),
        first_start[1] + closest_t * (first_end[1] - first_start[1]),
        first_start[2] + closest_t * (first_end[2] - first_start[2]),
    )
    second_position = (
        second_start[0] + closest_t * (second_end[0] - second_start[0]),
        second_start[1] + closest_t * (second_end[1] - second_start[1]),
        second_start[2] + closest_t * (second_end[2] - second_start[2]),
    )
    impact_position = (
        (first_position[0] + second_position[0]) / 2.0,
        (first_position[1] + second_position[1]) / 2.0,
        (first_position[2] + second_position[2]) / 2.0,
    )
    relative_speed = (
        math.dist(
            tuple(end - start for start, end in zip(first_start, first_end, strict=True)),
            tuple(end - start for start, end in zip(second_start, second_end, strict=True)),
        )
        / tick_seconds
    )
    return SweptCollision(
        closest_t,
        first_position,
        second_position,
        impact_position,
        horizontal_separation,
        vertical_separation,
        relative_speed,
    )


def swept_path_crosses_segments(
    start: tuple[float, float],
    end: tuple[float, float],
    segments: tuple[tuple[tuple[float, float], tuple[float, float]], ...],
) -> bool:
    """Detect a path crossing a coastline segment even when both endpoints are clear."""

    def orientation(
        a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
    ) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_segment(
        a: tuple[float, float], b: tuple[float, float], point: tuple[float, float]
    ) -> bool:
        return min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= point[
            1
        ] <= max(a[1], b[1])

    def intersects(a: tuple[float, float], b: tuple[float, float]) -> bool:
        first_a, first_b = orientation(start, end, a), orientation(start, end, b)
        second_a, second_b = orientation(a, b, start), orientation(a, b, end)
        if first_a * first_b < 0.0 and second_a * second_b < 0.0:
            return True
        return (
            (first_a == 0.0 and on_segment(start, end, a))
            or (first_b == 0.0 and on_segment(start, end, b))
            or (second_a == 0.0 and on_segment(a, b, start))
            or (second_b == 0.0 and on_segment(a, b, end))
        )

    return any(intersects(a, b) for a, b in segments)


def point_in_polygon(point: tuple[float, float], polygon: tuple[tuple[float, float], ...]) -> bool:
    """Return whether an entity reference point is inside a configured no-go zone."""
    if len(polygon) < 3:
        raise ValueError("collision polygon requires at least three vertices")
    inside = False
    previous = polygon[-1]
    for current in polygon:
        crosses = (current[1] > point[1]) != (previous[1] > point[1])
        if crosses:
            crossing_x = (previous[0] - current[0]) * (point[1] - current[1]) / (
                previous[1] - current[1]
            ) + current[0]
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside

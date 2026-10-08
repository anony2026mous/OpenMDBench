"""Continuous, scenario-independent geometry facts for interdiction missions.

These helpers are deliberately pure: callers provide local-metre trajectories
and parameter objects, receive auditable facts, and decide how they affect a
mission or score.  No helper mutates entity state or applies damage.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

Vector2V2 = tuple[float, float]
_EPSILON = 1e-9


def _point(value: Sequence[float], *, name: str) -> Vector2V2:
    if (
        isinstance(value, (str, bytes, bytearray))
        or len(value) < 2
        or any(
            not isinstance(axis, (int, float))
            or isinstance(axis, bool)
            or not math.isfinite(float(axis))
            for axis in value[:2]
        )
    ):
        raise ValueError(f"{name} must contain two finite numeric axes")
    return float(value[0]), float(value[1])


def _finite(value: float, *, name: str, minimum: float | None = None) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or (minimum is not None and float(value) < minimum)
    ):
        raise ValueError(f"{name} must be finite and within its declared range")
    return float(value)


def _identifier(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be a bounded nonempty identifier")
    return value


def _interpolate(start: Vector2V2, end: Vector2V2, fraction: float) -> Vector2V2:
    return (
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
    )


def _bearing(center: Vector2V2, point: Vector2V2) -> float:
    return math.degrees(math.atan2(point[0] - center[0], point[1] - center[1])) % 360.0


def _deduplicated(values: Sequence[float]) -> tuple[float, ...]:
    ordered = tuple(sorted(min(1.0, max(0.0, value)) for value in values))
    return tuple(
        value
        for index, value in enumerate(ordered)
        if index == 0 or value - ordered[index - 1] > _EPSILON
    )


def _roots_for_circle(
    start: Vector2V2, end: Vector2V2, center: Vector2V2, radius: float
) -> tuple[float, ...]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    ox, oy = start[0] - center[0], start[1] - center[1]
    a = dx * dx + dy * dy
    if a <= _EPSILON:
        return ()
    b = 2.0 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < -_EPSILON:
        return ()
    root = math.sqrt(max(0.0, discriminant))
    return tuple(
        value for value in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)) if 0.0 <= value <= 1.0
    )


def _radial_line_fraction(
    start: Vector2V2, end: Vector2V2, center: Vector2V2, bearing_deg: float
) -> float | None:
    # A heading is north=0, clockwise-positive.  The corresponding local ray
    # uses east/north components (sin, cos).
    ray = (math.sin(math.radians(bearing_deg)), math.cos(math.radians(bearing_deg)))
    segment = (end[0] - start[0], end[1] - start[1])
    determinant = segment[0] * ray[1] - segment[1] * ray[0]
    if abs(determinant) <= _EPSILON:
        return None
    offset = (center[0] - start[0], center[1] - start[1])
    fraction = (offset[0] * ray[1] - offset[1] * ray[0]) / determinant
    ray_distance = (offset[0] * segment[1] - offset[1] * segment[0]) / determinant
    if -_EPSILON <= fraction <= 1.0 + _EPSILON and ray_distance >= -_EPSILON:
        return min(1.0, max(0.0, fraction))
    return None


@dataclass(frozen=True, slots=True)
class AnnularSectorV2:
    """A local-metre annular sector with an explicit sweep orientation."""

    center_m: Vector2V2
    inner_radius_m: float
    outer_radius_m: float
    start_bearing_deg: float
    end_bearing_deg: float
    direction: Literal["clockwise", "counterclockwise"] = "clockwise"

    def __post_init__(self) -> None:
        object.__setattr__(self, "center_m", _point(self.center_m, name="center_m"))
        inner = _finite(self.inner_radius_m, name="inner_radius_m", minimum=0.0)
        outer = _finite(self.outer_radius_m, name="outer_radius_m", minimum=0.0)
        if outer <= inner:
            raise ValueError("outer_radius_m must be greater than inner_radius_m")
        object.__setattr__(self, "inner_radius_m", inner)
        object.__setattr__(self, "outer_radius_m", outer)
        for name in ("start_bearing_deg", "end_bearing_deg"):
            value = _finite(getattr(self, name), name=name)
            object.__setattr__(self, name, value % 360.0)
        if self.direction not in {"clockwise", "counterclockwise"}:
            raise ValueError("sector direction is invalid")

    def contains(self, point_m: Sequence[float], *, tolerance_m: float = 0.0) -> bool:
        point = _point(point_m, name="point_m")
        tolerance = _finite(tolerance_m, name="tolerance_m", minimum=0.0)
        distance = math.dist(point, self.center_m)
        if not self.inner_radius_m - tolerance <= distance <= self.outer_radius_m + tolerance:
            return False
        bearing = _bearing(self.center_m, point)
        if self.direction == "clockwise":
            span = (self.end_bearing_deg - self.start_bearing_deg) % 360.0
            progress = (bearing - self.start_bearing_deg) % 360.0
        else:
            span = (self.start_bearing_deg - self.end_bearing_deg) % 360.0
            progress = (self.start_bearing_deg - bearing) % 360.0
        return progress <= span + 1e-9


@dataclass(frozen=True, slots=True)
class RadialCrossingFactV2:
    time_fraction: float
    position_m: Vector2V2
    bearing_deg: float
    direction: Literal["clockwise", "counterclockwise"]


@dataclass(frozen=True, slots=True)
class AnnularSectorOccupancyFactV2:
    subject_id: str
    tick: int
    duration_seconds: float
    intervals: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class FrontOfTrackOccupancyFactV2:
    subject_id: str
    target_id: str
    time_fraction: float
    lead_m: float
    cross_track_m: float


@dataclass(frozen=True, slots=True)
class PathConflictFactV2:
    entity_a_id: str
    entity_b_id: str
    time_fraction: float
    position_a_m: Vector2V2
    position_b_m: Vector2V2
    separation_m: float
    threshold_m: float


@dataclass(frozen=True, slots=True)
class DurationFactV2:
    key: str
    tick: int
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class ReplanningLatencyFactV2:
    key: str
    trigger_tick: int
    replanned_tick: int
    latency_ticks: int


def radial_crossings(
    *,
    start_m: Sequence[float],
    end_m: Sequence[float],
    center_m: Sequence[float],
    bearing_deg: float,
    minimum_radius_m: float = 0.0,
    maximum_radius_m: float | None = None,
) -> tuple[RadialCrossingFactV2, ...]:
    """Return continuous intersections with a directed radial line segment."""

    start, end, center = (
        _point(start_m, name="start_m"),
        _point(end_m, name="end_m"),
        _point(center_m, name="center_m"),
    )
    bearing = _finite(bearing_deg, name="bearing_deg") % 360.0
    minimum = _finite(minimum_radius_m, name="minimum_radius_m", minimum=0.0)
    maximum = (
        math.inf
        if maximum_radius_m is None
        else _finite(maximum_radius_m, name="maximum_radius_m", minimum=minimum)
    )
    fraction = _radial_line_fraction(start, end, center, bearing)
    if fraction is None:
        return ()
    position = _interpolate(start, end, fraction)
    radius = math.dist(position, center)
    if radius < minimum - _EPSILON or radius > maximum + _EPSILON:
        return ()
    ray = (math.sin(math.radians(bearing)), math.cos(math.radians(bearing)))
    before = (start[0] - center[0]) * ray[1] - (start[1] - center[1]) * ray[0]
    after = (end[0] - center[0]) * ray[1] - (end[1] - center[1]) * ray[0]
    if abs(before) <= _EPSILON or abs(after) <= _EPSILON or before * after >= 0.0:
        return ()
    return (
        RadialCrossingFactV2(
            time_fraction=fraction,
            position_m=position,
            bearing_deg=bearing,
            direction="counterclockwise" if before < after else "clockwise",
        ),
    )


def annular_sector_occupancy(
    *,
    subject_id: str,
    tick: int,
    start_m: Sequence[float],
    end_m: Sequence[float],
    sector: AnnularSectorV2,
    dt_seconds: float,
) -> AnnularSectorOccupancyFactV2:
    """Measure exact piecewise-linear dwell time in an annular sector."""

    identifier = _identifier(subject_id, name="subject_id")
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise ValueError("tick must be a nonnegative integer")
    duration = _finite(dt_seconds, name="dt_seconds", minimum=0.0)
    start, end = _point(start_m, name="start_m"), _point(end_m, name="end_m")
    breakpoints: list[float] = [0.0, 1.0]
    for radius in (sector.inner_radius_m, sector.outer_radius_m):
        if radius > 0.0:
            breakpoints.extend(_roots_for_circle(start, end, sector.center_m, radius))
    for bearing in (sector.start_bearing_deg, sector.end_bearing_deg):
        crossing = _radial_line_fraction(start, end, sector.center_m, bearing)
        if crossing is not None:
            breakpoints.append(crossing)
    ordered = _deduplicated(breakpoints)
    intervals = tuple(
        (first, second)
        for first, second in zip(ordered, ordered[1:], strict=False)
        if second - first > _EPSILON
        and sector.contains(_interpolate(start, end, (first + second) / 2.0))
    )
    return AnnularSectorOccupancyFactV2(
        subject_id=identifier,
        tick=tick,
        duration_seconds=math.fsum((second - first) * duration for first, second in intervals),
        intervals=intervals,
    )


def front_of_track_occupancy(
    *,
    subject_id: str,
    subject_start_m: Sequence[float],
    subject_end_m: Sequence[float],
    target_id: str,
    target_start_m: Sequence[float],
    target_end_m: Sequence[float],
    minimum_lead_m: float,
    maximum_lead_m: float,
    lateral_tolerance_m: float,
) -> FrontOfTrackOccupancyFactV2 | None:
    """Return the first continuous time a subject occupies a target's front corridor."""

    subject_id, target_id = (
        _identifier(subject_id, name="subject_id"),
        _identifier(target_id, name="target_id"),
    )
    subject_start, subject_end = (
        _point(subject_start_m, name="subject_start_m"),
        _point(subject_end_m, name="subject_end_m"),
    )
    target_start, target_end = (
        _point(target_start_m, name="target_start_m"),
        _point(target_end_m, name="target_end_m"),
    )
    minimum = _finite(minimum_lead_m, name="minimum_lead_m", minimum=0.0)
    maximum = _finite(maximum_lead_m, name="maximum_lead_m", minimum=minimum)
    lateral = _finite(lateral_tolerance_m, name="lateral_tolerance_m", minimum=0.0)
    if maximum < minimum:
        raise ValueError("maximum_lead_m must be at least minimum_lead_m")
    track = (target_end[0] - target_start[0], target_end[1] - target_start[1])
    norm = math.hypot(*track)
    if norm <= _EPSILON:
        return None
    forward = (track[0] / norm, track[1] / norm)
    relative_start = (subject_start[0] - target_start[0], subject_start[1] - target_start[1])
    relative_delta = (
        (subject_end[0] - subject_start[0]) - (target_end[0] - target_start[0]),
        (subject_end[1] - subject_start[1]) - (target_end[1] - target_start[1]),
    )
    lead_start = relative_start[0] * forward[0] + relative_start[1] * forward[1]
    lead_delta = relative_delta[0] * forward[0] + relative_delta[1] * forward[1]
    cross_start = relative_start[0] * forward[1] - relative_start[1] * forward[0]
    cross_delta = relative_delta[0] * forward[1] - relative_delta[1] * forward[0]
    breakpoints = [0.0, 1.0]
    for intercept in (minimum, maximum):
        if abs(lead_delta) > _EPSILON:
            breakpoints.append((intercept - lead_start) / lead_delta)
    for intercept in (-lateral, lateral):
        if abs(cross_delta) > _EPSILON:
            breakpoints.append((intercept - cross_start) / cross_delta)
    ordered = _deduplicated(breakpoints)
    for first, second in zip(ordered, ordered[1:], strict=False):
        fraction = (first + second) / 2.0
        lead = lead_start + lead_delta * fraction
        cross = cross_start + cross_delta * fraction
        if minimum - _EPSILON <= lead <= maximum + _EPSILON and abs(cross) <= lateral + _EPSILON:
            return FrontOfTrackOccupancyFactV2(subject_id, target_id, fraction, lead, cross)
    return None


def path_conflict(
    *,
    entity_a_id: str,
    start_a_m: Sequence[float],
    end_a_m: Sequence[float],
    entity_b_id: str,
    start_b_m: Sequence[float],
    end_b_m: Sequence[float],
    threshold_m: float,
) -> PathConflictFactV2 | None:
    """Find synchronous closest approach for two continuous local-metre paths."""

    entity_a_id, entity_b_id = (
        _identifier(entity_a_id, name="entity_a_id"),
        _identifier(entity_b_id, name="entity_b_id"),
    )
    if entity_a_id == entity_b_id:
        raise ValueError("path conflict requires two distinct entity identities")
    start_a, end_a = _point(start_a_m, name="start_a_m"), _point(end_a_m, name="end_a_m")
    start_b, end_b = _point(start_b_m, name="start_b_m"), _point(end_b_m, name="end_b_m")
    threshold = _finite(threshold_m, name="threshold_m", minimum=0.0)
    relative_start = (start_a[0] - start_b[0], start_a[1] - start_b[1])
    relative_delta = (
        (end_a[0] - start_a[0]) - (end_b[0] - start_b[0]),
        (end_a[1] - start_a[1]) - (end_b[1] - start_b[1]),
    )
    denominator = relative_delta[0] ** 2 + relative_delta[1] ** 2
    fraction = (
        0.0
        if denominator <= _EPSILON
        else min(
            1.0,
            max(
                0.0,
                -(relative_start[0] * relative_delta[0] + relative_start[1] * relative_delta[1])
                / denominator,
            ),
        )
    )
    point_a, point_b = (
        _interpolate(start_a, end_a, fraction),
        _interpolate(start_b, end_b, fraction),
    )
    separation = math.dist(point_a, point_b)
    if separation > threshold + _EPSILON:
        return None
    first, second = sorted((entity_a_id, entity_b_id))
    return PathConflictFactV2(
        first,
        second,
        fraction,
        point_a if first == entity_a_id else point_b,
        point_b if first == entity_a_id else point_a,
        separation,
        threshold,
    )


@dataclass(frozen=True, slots=True)
class InterdictionGeometryCheckpointV2:
    occupancy_seconds: Mapping[str, float]
    blocked_seconds: Mapping[str, float]
    last_conflict_tick: Mapping[str, int]
    replan_trigger_tick: Mapping[str, int]


class InterdictionGeometryAccumulatorV2:
    """Small checkpointable ledger for duration, debounce and replan facts."""

    def __init__(self) -> None:
        self._occupancy_seconds: dict[str, float] = {}
        self._blocked_seconds: dict[str, float] = {}
        self._last_conflict_tick: dict[str, int] = {}
        self._replan_trigger_tick: dict[str, int] = {}

    def add_occupancy(self, fact: AnnularSectorOccupancyFactV2, *, key: str) -> DurationFactV2:
        identifier = _identifier(key, name="key")
        self._occupancy_seconds[identifier] = (
            self._occupancy_seconds.get(identifier, 0.0) + fact.duration_seconds
        )
        return DurationFactV2(identifier, fact.tick, self._occupancy_seconds[identifier])

    def add_blocked_or_slow(
        self, *, key: str, tick: int, blocked_or_slow: bool, dt_seconds: float
    ) -> DurationFactV2:
        identifier = _identifier(key, name="key")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        duration = _finite(dt_seconds, name="dt_seconds", minimum=0.0)
        if not isinstance(blocked_or_slow, bool):
            raise ValueError("blocked_or_slow must be boolean")
        if blocked_or_slow:
            self._blocked_seconds[identifier] = (
                self._blocked_seconds.get(identifier, 0.0) + duration
            )
        return DurationFactV2(identifier, tick, self._blocked_seconds.get(identifier, 0.0))

    def debounce_path_conflict(
        self, *, key: str, tick: int, candidate: PathConflictFactV2 | None, debounce_ticks: int
    ) -> PathConflictFactV2 | None:
        identifier = _identifier(key, name="key")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        if (
            not isinstance(debounce_ticks, int)
            or isinstance(debounce_ticks, bool)
            or debounce_ticks < 0
        ):
            raise ValueError("debounce_ticks must be a nonnegative integer")
        if candidate is None:
            return None
        prior = self._last_conflict_tick.get(identifier)
        if prior is not None and tick - prior <= debounce_ticks:
            return None
        self._last_conflict_tick[identifier] = tick
        return candidate

    def mark_replan_trigger(self, *, key: str, tick: int) -> None:
        identifier = _identifier(key, name="key")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        self._replan_trigger_tick.setdefault(identifier, tick)

    def record_replan(self, *, key: str, tick: int) -> ReplanningLatencyFactV2 | None:
        identifier = _identifier(key, name="key")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        trigger = self._replan_trigger_tick.pop(identifier, None)
        if trigger is None:
            return None
        if tick < trigger:
            raise ValueError("replan tick cannot precede its trigger")
        return ReplanningLatencyFactV2(identifier, trigger, tick, tick - trigger)

    def snapshot(self) -> InterdictionGeometryCheckpointV2:
        return InterdictionGeometryCheckpointV2(
            occupancy_seconds=MappingProxyType(dict(sorted(self._occupancy_seconds.items()))),
            blocked_seconds=MappingProxyType(dict(sorted(self._blocked_seconds.items()))),
            last_conflict_tick=MappingProxyType(dict(sorted(self._last_conflict_tick.items()))),
            replan_trigger_tick=MappingProxyType(dict(sorted(self._replan_trigger_tick.items()))),
        )

    @classmethod
    def restore(
        cls, checkpoint: InterdictionGeometryCheckpointV2
    ) -> InterdictionGeometryAccumulatorV2:
        result = cls()
        for name, target, source in (
            ("occupancy_seconds", result._occupancy_seconds, checkpoint.occupancy_seconds),
            ("blocked_seconds", result._blocked_seconds, checkpoint.blocked_seconds),
        ):
            if not isinstance(source, Mapping):
                raise ValueError(f"{name} checkpoint evidence is invalid")
            for key, value in source.items():
                target[_identifier(key, name="checkpoint key")] = _finite(
                    value, name=name, minimum=0.0
                )
        for name, integer_target, source in (
            ("last_conflict_tick", result._last_conflict_tick, checkpoint.last_conflict_tick),
            ("replan_trigger_tick", result._replan_trigger_tick, checkpoint.replan_trigger_tick),
        ):
            if not isinstance(source, Mapping):
                raise ValueError(f"{name} checkpoint evidence is invalid")
            for key, value in source.items():
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"{name} checkpoint value is invalid")
                integer_target[_identifier(key, name="checkpoint key")] = value
        return result


__all__ = [
    "AnnularSectorOccupancyFactV2",
    "AnnularSectorV2",
    "DurationFactV2",
    "FrontOfTrackOccupancyFactV2",
    "InterdictionGeometryAccumulatorV2",
    "InterdictionGeometryCheckpointV2",
    "PathConflictFactV2",
    "RadialCrossingFactV2",
    "ReplanningLatencyFactV2",
    "annular_sector_occupancy",
    "front_of_track_occupancy",
    "path_conflict",
    "radial_crossings",
]

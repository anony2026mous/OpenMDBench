"""Public, contact-only intercept guidance for agent and SDK callers.

The helper deliberately has no dependency on a simulation session or WorldState.
It turns caller-authorized contact evidence and own-platform capability into a
normal navigation proposal; the ordinary gateway and World validation remain
the only command authority.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Vector3V2 = tuple[float, float, float]


def _vector3(value: Sequence[float], *, name: str) -> Vector3V2:
    if (
        isinstance(value, (str, bytes, bytearray))
        or len(value) != 3
        or any(
            not isinstance(axis, (int, float))
            or isinstance(axis, bool)
            or not math.isfinite(float(axis))
            for axis in value
        )
    ):
        raise ValueError(f"{name} must be exactly three finite numeric axes")
    return float(value[0]), float(value[1]), float(value[2])


def _identifier(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be a bounded nonempty identifier")
    return value


@dataclass(frozen=True, slots=True)
class PublicContactEstimateV2:
    """A caller-authorized track estimate; it is not a World entity reference."""

    contact_id: str
    position_m: Vector3V2
    velocity_mps: Vector3V2
    observed_tick: int
    valid_until_tick: int
    confidence: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "contact_id", _identifier(self.contact_id, name="contact_id"))
        object.__setattr__(self, "position_m", _vector3(self.position_m, name="position_m"))
        object.__setattr__(self, "velocity_mps", _vector3(self.velocity_mps, name="velocity_mps"))
        if (
            not isinstance(self.observed_tick, int)
            or isinstance(self.observed_tick, bool)
            or self.observed_tick < 0
            or not isinstance(self.valid_until_tick, int)
            or isinstance(self.valid_until_tick, bool)
            or self.valid_until_tick < self.observed_tick
        ):
            raise ValueError("contact tick window is invalid")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(float(self.confidence))
            or not 0.0 <= float(self.confidence) <= 1.0
        ):
            raise ValueError("contact confidence must be within [0, 1]")
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True, slots=True)
class InterceptorCapabilityV2:
    """Public own-platform kinematic envelope supplied by an agent."""

    entity_id: str
    position_m: Vector3V2
    maximum_speed_mps: float
    preferred_speed_mps: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _identifier(self.entity_id, name="entity_id"))
        object.__setattr__(self, "position_m", _vector3(self.position_m, name="position_m"))
        maximum = float(self.maximum_speed_mps)
        preferred = maximum if self.preferred_speed_mps is None else float(self.preferred_speed_mps)
        if (
            isinstance(self.maximum_speed_mps, bool)
            or not math.isfinite(maximum)
            or maximum <= 0.0
            or isinstance(self.preferred_speed_mps, bool)
            or not math.isfinite(preferred)
            or not 0.0 < preferred <= maximum
        ):
            raise ValueError("interceptor speeds must be finite and within the public envelope")
        object.__setattr__(self, "maximum_speed_mps", maximum)
        object.__setattr__(self, "preferred_speed_mps", preferred)


@dataclass(frozen=True, slots=True)
class InterceptRegionV2:
    """Optional circular region that constrains a proposed navigation waypoint."""

    center_m: Vector3V2
    radius_m: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "center_m", _vector3(self.center_m, name="center_m"))
        if (
            isinstance(self.radius_m, bool)
            or not isinstance(self.radius_m, (int, float))
            or not math.isfinite(float(self.radius_m))
            or float(self.radius_m) <= 0.0
        ):
            raise ValueError("intercept region radius must be positive and finite")
        object.__setattr__(self, "radius_m", float(self.radius_m))


@dataclass(frozen=True, slots=True)
class InterceptNavigationProposalV2:
    """An ordinary navigation target; callers still submit it through ActionBatch."""

    contact_id: str
    waypoint_m: Vector3V2
    suggested_speed_mps: float
    suggested_heading_deg: float
    intercept_time_seconds: float
    source_observed_tick: int


def _clamp_region(point: Vector3V2, region: InterceptRegionV2 | None) -> Vector3V2:
    if region is None:
        return point
    dx = point[0] - region.center_m[0]
    dy = point[1] - region.center_m[1]
    distance = math.hypot(dx, dy)
    if distance <= region.radius_m:
        return point
    scale = region.radius_m / distance
    return (
        region.center_m[0] + dx * scale,
        region.center_m[1] + dy * scale,
        point[2],
    )


def predict_intercept_waypoint(
    *,
    contact: PublicContactEstimateV2,
    interceptor: InterceptorCapabilityV2,
    standoff_m: float = 0.0,
    region: InterceptRegionV2 | None = None,
) -> InterceptNavigationProposalV2:
    """Solve a constant-velocity intercept using only public caller inputs.

    If a physical intercept is unreachable at the requested speed, the helper
    projects a finite closest-approach look-ahead instead of manufacturing a
    truth-dependent route.  ``standoff_m`` places the waypoint behind the
    contact's velocity vector when the target has nonzero speed.
    """

    if (
        isinstance(standoff_m, bool)
        or not isinstance(standoff_m, (int, float))
        or not math.isfinite(float(standoff_m))
        or float(standoff_m) < 0.0
    ):
        raise ValueError("standoff_m must be a finite nonnegative distance")
    own = interceptor.position_m
    target = contact.position_m
    velocity = contact.velocity_mps
    preferred_speed = interceptor.preferred_speed_mps
    if preferred_speed is None:
        raise ValueError("validated interceptor capability has no preferred speed")
    speed = float(preferred_speed)
    relative = (target[0] - own[0], target[1] - own[1], target[2] - own[2])
    target_speed_squared = math.fsum(axis * axis for axis in velocity)
    a = target_speed_squared - speed * speed
    b = 2.0 * math.fsum(relative[index] * velocity[index] for index in range(3))
    c = math.fsum(axis * axis for axis in relative)
    discriminant = b * b - 4.0 * a * c
    candidates: list[float] = []
    if abs(a) <= 1e-12:
        if abs(b) > 1e-12:
            candidates.append(-c / b)
    elif discriminant >= 0.0:
        root = math.sqrt(discriminant)
        candidates.extend(((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)))
    viable = tuple(value for value in candidates if math.isfinite(value) and value >= 0.0)
    if viable:
        intercept_time = min(viable)
    else:
        # Finite closest-approach horizon, independent of any simulation tick.
        intercept_time = (
            0.0
            if target_speed_squared <= 1e-12
            else max(
                0.0,
                -math.fsum(relative[index] * velocity[index] for index in range(3))
                / target_speed_squared,
            )
        )
    projected = tuple(target[index] + velocity[index] * intercept_time for index in range(3))
    target_speed = math.sqrt(target_speed_squared)
    if target_speed > 1e-12 and standoff_m:
        projected = tuple(
            projected[index] - velocity[index] / target_speed * float(standoff_m)
            for index in range(3)
        )
    waypoint = _clamp_region(_vector3(projected, name="projected_waypoint"), region)
    heading = math.degrees(math.atan2(waypoint[0] - own[0], waypoint[1] - own[1])) % 360.0
    return InterceptNavigationProposalV2(
        contact_id=contact.contact_id,
        waypoint_m=waypoint,
        suggested_speed_mps=speed,
        suggested_heading_deg=heading,
        intercept_time_seconds=intercept_time,
        source_observed_tick=contact.observed_tick,
    )


__all__ = [
    "InterceptNavigationProposalV2",
    "InterceptRegionV2",
    "InterceptorCapabilityV2",
    "PublicContactEstimateV2",
    "predict_intercept_waypoint",
]

"""Deterministic guided-missile flight contracts and kinematics for World v2.

Missiles are runtime flight objects rather than World entities: they cannot be
commanded, observed as a platform, or collide with the platform boundary
system.  Their complete state is nevertheless immutable and checkpointable so
that launch, seeker, terminal and damage evidence remain replayable.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Literal

from pydantic import Field, StrictInt, model_validator

from openmdbench.core.units import bounded_heading_deg
from openmdbench.schemas.core_v2 import CoreModelV2


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _heading_to(source: tuple[float, float, float], target: tuple[float, float, float]) -> float:
    """Return the public north-zero clockwise heading from *source* to *target*."""

    east = target[0] - source[0]
    north = target[1] - source[1]
    if east == 0.0 and north == 0.0:
        return 0.0
    return math.degrees(math.atan2(east, north)) % 360.0


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.dist(a, b)


def _closest_segment_distance(
    start_a: tuple[float, float, float],
    end_a: tuple[float, float, float],
    start_b: tuple[float, float, float],
    end_b: tuple[float, float, float],
) -> tuple[float, float, tuple[float, float, float], tuple[float, float, float]]:
    """Closest missile/target approach under linear motion over one tick."""

    relative_start = tuple(start_a[index] - start_b[index] for index in range(3))
    relative_delta = tuple(
        (end_a[index] - start_a[index]) - (end_b[index] - start_b[index]) for index in range(3)
    )
    denominator = sum(value * value for value in relative_delta)
    fraction = (
        0.0
        if denominator == 0.0
        else max(
            0.0,
            min(
                1.0,
                -sum(relative_start[index] * relative_delta[index] for index in range(3))
                / denominator,
            ),
        )
    )
    missile_position = (
        start_a[0] + (end_a[0] - start_a[0]) * fraction,
        start_a[1] + (end_a[1] - start_a[1]) * fraction,
        start_a[2] + (end_a[2] - start_a[2]) * fraction,
    )
    target_position = (
        start_b[0] + (end_b[0] - start_b[0]) * fraction,
        start_b[1] + (end_b[1] - start_b[1]) * fraction,
        start_b[2] + (end_b[2] - start_b[2]) * fraction,
    )
    return _distance(missile_position, target_position), fraction, missile_position, target_position


class GuidedMissileProfileV2(CoreModelV2):
    """Catalog-defined kinematic, seeker, and fuse settings for a missile."""

    schema_version: Literal["2.0"] = "2.0"
    launch_speed_mps: float = Field(ge=0.0)
    cruise_speed_mps: float = Field(gt=0.0)
    max_acceleration_mps2: float = Field(gt=0.0)
    max_turn_rate_deg_s: float = Field(gt=0.0, le=360.0)
    max_vertical_speed_mps: float = Field(gt=0.0)
    seeker_range_m: float = Field(gt=0.0)
    seeker_fov_deg: float = Field(gt=0.0, le=360.0)
    seeker_detection_probability: float = Field(ge=0.0, le=1.0)
    fuse_radius_m: float = Field(gt=0.0)
    max_flight_ticks: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def validate_speed_envelope(self) -> GuidedMissileProfileV2:
        if self.launch_speed_mps > self.cruise_speed_mps:
            raise ValueError("missile launch speed cannot exceed cruise speed")
        return self


class MissileFlightV2(CoreModelV2):
    """One active, launch-authorized missile in World-owned flight state."""

    schema_version: Literal["2.0"] = "2.0"
    missile_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=256)
    launcher_id: str = Field(min_length=1, max_length=256)
    faction_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    weapon_ref: str = Field(min_length=1, max_length=256)
    ammunition_ref: str = Field(min_length=1, max_length=256)
    effect_ref: str = Field(min_length=1, max_length=256)
    damage_model_ref: str = Field(min_length=1, max_length=256)
    magnitude: float = Field(ge=0.0)
    hit_probability: float = Field(ge=0.0, le=1.0)
    launch_tick: StrictInt = Field(ge=0)
    flight_ticks: StrictInt = Field(ge=0)
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    heading_deg: float = Field(ge=0.0, lt=360.0)
    last_known_target_position_m: tuple[float, float, float]
    seeker_state: Literal["searching", "tracking"] = "searching"
    last_detection_tick: StrictInt | None = Field(default=None, ge=0)
    profile: GuidedMissileProfileV2

    @model_validator(mode="after")
    def validate_detection_clock(self) -> MissileFlightV2:
        if self.last_detection_tick is not None and self.last_detection_tick < self.launch_tick:
            raise ValueError("missile detection cannot precede launch")
        return self

    @property
    def speed_mps(self) -> float:
        return math.sqrt(sum(value * value for value in self.velocity_mps))


class MissileTerminalReceiptV2(CoreModelV2):
    """Immutable audit evidence for a terminal missile outcome.

    ``position_m`` is the terminal location. ``impact_position_m`` is set only
    for an actual hit, keeping fuse-miss geometry distinguishable for metrics.
    """

    schema_version: Literal["2.0"] = "2.0"
    missile_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=256)
    launcher_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    tick: StrictInt = Field(ge=0)
    status: Literal["hit", "fuse_miss", "expired", "target_unavailable"]
    position_m: tuple[float, float, float]
    closest_approach_m: float | None = Field(default=None, ge=0.0)
    seeker_state: Literal["searching", "tracking"]
    seeker_detected: bool
    target_position_m: tuple[float, float, float] | None = None
    missile_velocity_mps: tuple[float, float, float] | None = None
    closest_approach_time_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    impact_position_m: tuple[float, float, float] | None = None
    coordinate_frame: Literal["local-m"] = "local-m"
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class MissileAdvanceV2(CoreModelV2):
    """Result of one deterministic missile kinematics/seeker integration step."""

    schema_version: Literal["2.0"] = "2.0"
    status: Literal["active", "fuse_candidate", "expired", "target_unavailable"]
    flight: MissileFlightV2 | None = None
    position_m: tuple[float, float, float]
    closest_approach_m: float | None = Field(default=None, ge=0.0)
    seeker_detected: bool
    target_position_m: tuple[float, float, float] | None = None
    missile_velocity_mps: tuple[float, float, float] | None = None
    closest_approach_time_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_terminal_state(self) -> MissileAdvanceV2:
        if (self.status == "active") != (self.flight is not None):
            raise ValueError("only active missile advances may retain flight state")
        return self


def advance_guided_missile_v2(
    flight: MissileFlightV2,
    *,
    target_start_position_m: tuple[float, float, float] | None,
    target_end_position_m: tuple[float, float, float] | None,
    tick: int,
    dt_seconds: float,
) -> MissileAdvanceV2:
    """Advance one missile using aircraft-style bounded turn/accel/climb motion.

    A deterministic seeker sample is evaluated once per tick.  Continuous
    relative-motion closest approach prevents a fast missile from stepping over
    a target between discrete World frames.
    """

    if not isinstance(tick, int) or isinstance(tick, bool) or tick < flight.launch_tick:
        raise ValueError("missile tick must be an integer no earlier than launch")
    if (
        not isinstance(dt_seconds, (int, float))
        or isinstance(dt_seconds, bool)
        or dt_seconds <= 0.0
    ):
        raise ValueError("missile integration requires a positive time step")
    if target_start_position_m is None or target_end_position_m is None:
        evidence_hash = _canonical_hash([flight.missile_id, tick, "target_unavailable"])
        return MissileAdvanceV2(
            status="target_unavailable",
            position_m=flight.position_m,
            seeker_detected=False,
            missile_velocity_mps=flight.velocity_mps,
            evidence_hash=evidence_hash,
        )

    target_heading = _heading_to(flight.position_m, target_end_position_m)
    angular_error = (target_heading - flight.heading_deg + 180.0) % 360.0 - 180.0
    target_range = _distance(flight.position_m, target_end_position_m)
    within_fov = abs(angular_error) <= flight.profile.seeker_fov_deg / 2.0
    can_detect = target_range <= flight.profile.seeker_range_m and within_fov
    seeker_seed_payload = [flight.missile_id, tick, "seeker"]
    seeker_seed = int(hashlib.sha256(json.dumps(seeker_seed_payload).encode()).hexdigest()[:16], 16)
    # This is a reproducible simulation substream, never a security secret.
    seeker_sample = random.Random(seeker_seed).random()  # nosec B311
    detected = can_detect and seeker_sample < flight.profile.seeker_detection_probability
    remembered_target = target_end_position_m if detected else flight.last_known_target_position_m
    desired_heading = _heading_to(flight.position_m, remembered_target)
    heading = bounded_heading_deg(
        flight.heading_deg,
        desired_heading,
        flight.profile.max_turn_rate_deg_s * float(dt_seconds),
    )
    speed = min(
        flight.profile.cruise_speed_mps,
        flight.speed_mps + flight.profile.max_acceleration_mps2 * float(dt_seconds),
    )
    altitude_delta = max(
        -flight.profile.max_vertical_speed_mps * float(dt_seconds),
        min(
            flight.profile.max_vertical_speed_mps * float(dt_seconds),
            remembered_target[2] - flight.position_m[2],
        ),
    )
    heading_rad = math.radians(heading)
    velocity = (
        speed * math.sin(heading_rad),
        speed * math.cos(heading_rad),
        altitude_delta / float(dt_seconds),
    )
    position = (
        flight.position_m[0] + velocity[0] * float(dt_seconds),
        flight.position_m[1] + velocity[1] * float(dt_seconds),
        flight.position_m[2] + velocity[2] * float(dt_seconds),
    )
    closest_approach, fraction, impact_position, closest_target_position = (
        _closest_segment_distance(
            flight.position_m,
            position,
            target_start_position_m,
            target_end_position_m,
        )
    )
    evidence_hash = _canonical_hash(
        [
            flight.missile_id,
            tick,
            "seeker",
            seeker_sample,
            detected,
            position,
            closest_approach,
        ]
    )
    if closest_approach <= flight.profile.fuse_radius_m and (
        detected or flight.seeker_state == "tracking"
    ):
        return MissileAdvanceV2(
            status="fuse_candidate",
            position_m=impact_position,
            closest_approach_m=closest_approach,
            seeker_detected=detected,
            target_position_m=closest_target_position,
            missile_velocity_mps=velocity,
            closest_approach_time_fraction=fraction,
            evidence_hash=evidence_hash,
        )
    flight_ticks = flight.flight_ticks + 1
    if flight_ticks >= flight.profile.max_flight_ticks:
        return MissileAdvanceV2(
            status="expired",
            position_m=position,
            closest_approach_m=closest_approach,
            seeker_detected=detected,
            target_position_m=closest_target_position,
            missile_velocity_mps=velocity,
            closest_approach_time_fraction=fraction,
            evidence_hash=evidence_hash,
        )
    return MissileAdvanceV2(
        status="active",
        flight=flight.model_copy(
            update={
                "flight_ticks": flight_ticks,
                "position_m": position,
                "velocity_mps": velocity,
                "heading_deg": heading,
                "last_known_target_position_m": remembered_target,
                "seeker_state": "tracking" if detected else "searching",
                "last_detection_tick": tick if detected else flight.last_detection_tick,
            }
        ),
        position_m=position,
        closest_approach_m=closest_approach,
        seeker_detected=detected,
        target_position_m=closest_target_position,
        missile_velocity_mps=velocity,
        closest_approach_time_fraction=fraction,
        evidence_hash=evidence_hash,
    )


__all__ = [
    "GuidedMissileProfileV2",
    "MissileAdvanceV2",
    "MissileFlightV2",
    "MissileTerminalReceiptV2",
    "advance_guided_missile_v2",
]

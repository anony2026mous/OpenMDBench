"""Capability-driven sensing, communication, and energy tick mechanisms."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal


def _hash(value: object) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class SubsystemEntityFactV2:
    entity_id: str
    faction_id: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    energy: float | None
    domain: str | None = None
    sensors: tuple[Mapping[str, object], ...] = ()
    communications: tuple[Mapping[str, object], ...] = ()
    energy_profiles: tuple[Mapping[str, object], ...] = ()
    # This value is supplied by the World geography boundary.  It is deliberately
    # optional because only sensors with an explicit AGL profile require it.
    surface_elevation_m: float | None = None


@dataclass(frozen=True, slots=True)
class SensorContactReceiptV2:
    """Audit-only sensor geometry; faction observations remain separately filtered."""

    evidence_id: str
    owner_entity_id: str
    target_entity_id: str
    sensor_ref: str
    tick: int
    distance_m: float
    sensor_position_m: tuple[float, float, float]
    target_position_m: tuple[float, float, float]
    target_velocity_mps: tuple[float, float, float]
    bearing_deg: float
    elevation_deg: float
    sensor_range_m: float
    coordinate_frame: Literal["local-m"]
    probability: float
    sample: float | None
    detected: bool
    rng_substream: str
    measurement_position_m: tuple[float, float, float] | None = None
    measurement_range_m: float | None = None
    measurement_bearing_deg: float | None = None
    range_noise_fraction: float = 0.0
    bearing_noise_deg: float = 0.0
    update_ticks: int = 1
    confirmation_frames: int = 1
    stale_after_ticks: int = 1
    engagement_max_age_ticks: int = 1
    minimum_contact_confidence: float = 0.0
    measurement_rng_substream: str = ""
    target_agl_m: float | None = None
    altitude_range_reference: Literal["agl"] | None = None


@dataclass(frozen=True, slots=True)
class EnergyTickReceiptV2:
    entity_id: str
    energy_ref: str
    tick: int
    before: float
    consumed: float
    after: float


@dataclass(frozen=True, slots=True)
class CommunicationTickReceiptV2:
    tick: int
    endpoint_ids: tuple[str, ...]
    queued_message_count: int


@dataclass(frozen=True, slots=True)
class GenericSubsystemTickReceiptV2:
    tick: int
    stage_order: tuple[str, ...]
    contacts: tuple[SensorContactReceiptV2, ...]
    energy: tuple[EnergyTickReceiptV2, ...]
    communication: CommunicationTickReceiptV2
    receipt_hash: str


class GenericSubsystemEngineV2:
    """Pure deterministic subsystem evaluation over immutable World facts."""

    @staticmethod
    def _number(content: Mapping[str, object], name: str, default: float) -> float:
        value = content.get(name, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"subsystem field {name} must be numeric")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"subsystem field {name} must be finite")
        return result

    @staticmethod
    def _positive_int(content: Mapping[str, object], name: str, default: int) -> int:
        value = content.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"subsystem field {name} must be a positive integer")
        return value

    @staticmethod
    def _strings(content: Mapping[str, object], name: str) -> tuple[str, ...]:
        value = content.get(name, ())
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"subsystem field {name} must be a sequence")
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError(f"subsystem field {name} must contain nonempty strings")
        return tuple(value)

    @staticmethod
    def _sample(seed: int, tick: int, substream: str, offset: int = 0) -> float:
        digest = hashlib.sha256(f"{seed}|{tick}|{substream}".encode()).digest()
        start = offset * 8
        return int.from_bytes(digest[start : start + 8], "big") / float(2**64)

    @classmethod
    def _effective_range_m(
        cls,
        *,
        sensor: Mapping[str, object],
        resolved_nominal_range_m: float,
        target: SubsystemEntityFactV2,
    ) -> tuple[float, float | None, Literal["agl"] | None]:
        """Select an explicitly declared altitude band before probability sampling.

        ``resolved_nominal_range_m`` has already passed through the generic
        capability modifier pipeline.  Scaling the selected raw band by its
        nominal ratio applies those modifiers after the altitude decision.
        """

        raw_profile = sensor.get("altitude_range_profile")
        if raw_profile is None:
            return resolved_nominal_range_m, None, None
        if not isinstance(raw_profile, Mapping):
            raise ValueError("sensor altitude range profile must be a mapping")
        required = {
            "reference",
            "low_altitude_ceiling_m",
            "low_altitude_range_m",
            "nominal_range_m",
            "transition",
        }
        if set(raw_profile) != required:
            raise ValueError("sensor altitude range profile fields are invalid")
        if raw_profile.get("reference") != "agl" or raw_profile.get("transition") != "step":
            raise ValueError("sensor altitude range profile reference or transition is unsupported")
        ceiling_m = cls._number(raw_profile, "low_altitude_ceiling_m", math.nan)
        low_range_m = cls._number(raw_profile, "low_altitude_range_m", math.nan)
        nominal_range_m = cls._number(raw_profile, "nominal_range_m", math.nan)
        if ceiling_m < 0.0 or low_range_m <= 0.0 or nominal_range_m <= 0.0:
            raise ValueError("sensor altitude range profile values are invalid")
        surface_elevation_m = target.surface_elevation_m
        if (
            isinstance(surface_elevation_m, bool)
            or not isinstance(surface_elevation_m, (int, float))
            or not math.isfinite(float(surface_elevation_m))
        ):
            raise ValueError("sensor altitude range profile requires target AGL evidence")
        target_agl_m = target.position_m[2] - float(surface_elevation_m)
        raw_selected_range_m = low_range_m if target_agl_m <= ceiling_m else nominal_range_m
        return (
            raw_selected_range_m * resolved_nominal_range_m / nominal_range_m,
            target_agl_m,
            "agl",
        )

    def evaluate(
        self,
        *,
        entities: Sequence[SubsystemEntityFactV2],
        tick: int,
        dt_seconds: float,
        seed: int,
        queued_message_count: int,
    ) -> GenericSubsystemTickReceiptV2:
        if tick < 0 or dt_seconds <= 0.0 or not math.isfinite(dt_seconds) or seed < 0:
            raise ValueError("subsystem tick anchors are invalid")
        ordered = tuple(sorted(entities, key=lambda item: item.entity_id))
        contacts: list[SensorContactReceiptV2] = []
        energy_receipts: list[EnergyTickReceiptV2] = []
        for owner in ordered:
            for sensor in sorted(owner.sensors, key=lambda item: str(item.get("exact_ref", ""))):
                sensor_ref = str(sensor.get("exact_ref", ""))
                range_m = self._number(sensor, "range_m", 0.0)
                probability = self._number(
                    sensor,
                    "detection_probability",
                    self._number(sensor, "probability", 1.0),
                )
                range_noise_fraction = self._number(sensor, "range_noise_fraction", 0.0)
                bearing_noise_deg = self._number(sensor, "bearing_noise_deg", 0.0)
                update_ticks = self._positive_int(sensor, "update_ticks", 1)
                confirmation_frames = self._positive_int(sensor, "confirmation_frames", 1)
                stale_after_ticks = self._positive_int(sensor, "stale_after_ticks", 1)
                engagement_max_age_ticks = self._positive_int(
                    sensor, "engagement_max_age_ticks", stale_after_ticks
                )
                minimum_contact_confidence = self._number(sensor, "minimum_contact_confidence", 0.0)
                target_domains = self._strings(sensor, "target_domains")
                if not sensor_ref or range_m <= 0.0 or not 0.0 <= probability <= 1.0:
                    continue
                if (
                    not 0.0 <= range_noise_fraction <= 1.0
                    or not 0.0 <= bearing_noise_deg <= 180.0
                    or not 0.0 <= minimum_contact_confidence <= 1.0
                ):
                    raise ValueError("sensor profile probability, noise, or confidence is invalid")
                if tick % update_ticks != 0:
                    continue
                for target in ordered:
                    if target.entity_id == owner.entity_id or target.faction_id == owner.faction_id:
                        continue
                    if (
                        target_domains
                        and target.domain is not None
                        and target.domain not in target_domains
                    ):
                        continue
                    distance = math.dist(owner.position_m, target.position_m)
                    east = target.position_m[0] - owner.position_m[0]
                    north = target.position_m[1] - owner.position_m[1]
                    horizontal = math.hypot(east, north)
                    bearing = math.degrees(math.atan2(east, north)) % 360.0
                    elevation = math.degrees(
                        math.atan2(target.position_m[2] - owner.position_m[2], horizontal)
                    )
                    substream = f"sensor:{owner.entity_id}:{sensor_ref}:{target.entity_id}"
                    effective_range_m, target_agl_m, altitude_reference = self._effective_range_m(
                        sensor=sensor,
                        resolved_nominal_range_m=range_m,
                        target=target,
                    )
                    evidence_id = _hash(
                        {
                            "tick": tick,
                            "owner": owner.entity_id,
                            "target": target.entity_id,
                            "sensor": sensor_ref,
                        }
                    )
                    if distance > effective_range_m:
                        contacts.append(
                            SensorContactReceiptV2(
                                evidence_id=evidence_id,
                                owner_entity_id=owner.entity_id,
                                target_entity_id=target.entity_id,
                                sensor_ref=sensor_ref,
                                tick=tick,
                                distance_m=distance,
                                sensor_position_m=owner.position_m,
                                target_position_m=target.position_m,
                                target_velocity_mps=target.velocity_mps,
                                bearing_deg=bearing,
                                elevation_deg=elevation,
                                sensor_range_m=effective_range_m,
                                coordinate_frame="local-m",
                                probability=probability,
                                sample=None,
                                detected=False,
                                rng_substream=substream,
                                range_noise_fraction=range_noise_fraction,
                                bearing_noise_deg=bearing_noise_deg,
                                update_ticks=update_ticks,
                                confirmation_frames=confirmation_frames,
                                stale_after_ticks=stale_after_ticks,
                                engagement_max_age_ticks=engagement_max_age_ticks,
                                minimum_contact_confidence=minimum_contact_confidence,
                                target_agl_m=target_agl_m,
                                altitude_range_reference=altitude_reference,
                            )
                        )
                        continue
                    sample = self._sample(seed, tick, substream)
                    measurement_substream = f"{substream}:measurement"
                    range_error = (
                        2.0 * self._sample(seed, tick, measurement_substream) - 1.0
                    ) * range_noise_fraction
                    bearing_error = (
                        2.0 * self._sample(seed, tick, measurement_substream, 1) - 1.0
                    ) * bearing_noise_deg
                    measurement_range = distance * (1.0 + range_error)
                    measurement_bearing = (bearing + bearing_error) % 360.0
                    measured_horizontal = measurement_range * math.cos(math.radians(elevation))
                    measured_position = (
                        owner.position_m[0]
                        + measured_horizontal * math.sin(math.radians(measurement_bearing)),
                        owner.position_m[1]
                        + measured_horizontal * math.cos(math.radians(measurement_bearing)),
                        owner.position_m[2] + measurement_range * math.sin(math.radians(elevation)),
                    )
                    contacts.append(
                        SensorContactReceiptV2(
                            evidence_id=evidence_id,
                            owner_entity_id=owner.entity_id,
                            target_entity_id=target.entity_id,
                            sensor_ref=sensor_ref,
                            tick=tick,
                            distance_m=distance,
                            sensor_position_m=owner.position_m,
                            target_position_m=target.position_m,
                            target_velocity_mps=target.velocity_mps,
                            bearing_deg=bearing,
                            elevation_deg=elevation,
                            sensor_range_m=effective_range_m,
                            coordinate_frame="local-m",
                            probability=probability,
                            sample=sample,
                            detected=sample < probability,
                            rng_substream=substream,
                            measurement_position_m=measured_position,
                            measurement_range_m=measurement_range,
                            measurement_bearing_deg=measurement_bearing,
                            range_noise_fraction=range_noise_fraction,
                            bearing_noise_deg=bearing_noise_deg,
                            update_ticks=update_ticks,
                            confirmation_frames=confirmation_frames,
                            stale_after_ticks=stale_after_ticks,
                            engagement_max_age_ticks=engagement_max_age_ticks,
                            minimum_contact_confidence=minimum_contact_confidence,
                            measurement_rng_substream=measurement_substream,
                            target_agl_m=target_agl_m,
                            altitude_range_reference=altitude_reference,
                        )
                    )
            if owner.energy is None:
                continue
            for profile in sorted(
                owner.energy_profiles, key=lambda item: str(item.get("exact_ref", ""))
            ):
                energy_ref = str(profile.get("exact_ref", ""))
                idle_rate = self._number(profile, "idle_rate_per_second", 0.0)
                motion_rate = self._number(profile, "motion_rate_per_meter", 0.0)
                if not energy_ref or idle_rate < 0.0 or motion_rate < 0.0:
                    raise ValueError("energy profile is invalid")
                speed = math.sqrt(sum(value * value for value in owner.velocity_mps))
                consumed = min(owner.energy, dt_seconds * (idle_rate + motion_rate * speed))
                energy_receipts.append(
                    EnergyTickReceiptV2(
                        entity_id=owner.entity_id,
                        energy_ref=energy_ref,
                        tick=tick,
                        before=owner.energy,
                        consumed=consumed,
                        after=owner.energy - consumed,
                    )
                )
                break
        communication = CommunicationTickReceiptV2(
            tick=tick,
            endpoint_ids=tuple(item.entity_id for item in ordered if item.communications),
            queued_message_count=queued_message_count,
        )
        payload = {
            "tick": tick,
            "stage_order": ("energy", "sensing", "communications"),
            "contacts": [
                item.__dict__
                if hasattr(item, "__dict__")
                else {field: getattr(item, field) for field in item.__dataclass_fields__}
                for item in contacts
            ],
            "energy": [
                {field: getattr(item, field) for field in item.__dataclass_fields__}
                for item in energy_receipts
            ],
            "communication": {
                field: getattr(communication, field) for field in communication.__dataclass_fields__
            },
        }
        return GenericSubsystemTickReceiptV2(
            tick=tick,
            stage_order=("energy", "sensing", "communications"),
            contacts=tuple(contacts),
            energy=tuple(energy_receipts),
            communication=communication,
            receipt_hash=_hash(payload),
        )


__all__ = [
    "CommunicationTickReceiptV2",
    "EnergyTickReceiptV2",
    "GenericSubsystemEngineV2",
    "GenericSubsystemTickReceiptV2",
    "SensorContactReceiptV2",
    "SubsystemEntityFactV2",
]

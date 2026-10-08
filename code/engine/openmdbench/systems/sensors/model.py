"""Cross-domain sensing with side-scoped contacts and private audit details."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from openmdbench.core.entities import Domain, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack
from openmdbench.systems.weather import SensorKind, Weather, effective_range


@dataclass(frozen=True, slots=True)
class Sensor:
    sensor_id: str
    kind: SensorKind
    range_m: float
    update_hz: float
    base_detection_probability: float = 1.0
    field_of_view_deg: float = 360.0
    uncertainty_fraction: float = 0.01
    minimum_uncertainty_m: float = 1.0
    initial_confidence: float = 0.7


@dataclass(frozen=True, slots=True)
class SensorPlatform:
    platform_id: str
    platform_type: str
    side: Side
    domain: Domain
    position: tuple[float, float, float]
    sensor: Sensor
    heading_deg: float = 0.0


@dataclass(frozen=True, slots=True)
class TargetTruth:
    entity_id: str
    domain: Domain
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]


class DetectionEngine:
    def __init__(self, rng: SessionRNG, *, tick_seconds: float = 1.0) -> None:
        self._rng = rng.stream("sensor")
        self.tick_seconds = tick_seconds
        self._contact_ids: dict[tuple[Side, str], str] = {}
        self._tracks: dict[tuple[Side, str], ContactTrack] = {}
        self._next_contact: dict[Side, int] = {}
        self.audit_log: list[dict[str, object]] = []

    def _is_update_tick(self, sensor: Sensor, tick: int) -> bool:
        interval = max(1, round(1.0 / (sensor.update_hz * self.tick_seconds)))
        return tick % interval == 0

    @staticmethod
    def _cross_domain_allowed(platform: SensorPlatform, target: TargetTruth) -> bool:
        if platform.sensor.kind is SensorKind.EO_IR:
            return platform.domain is Domain.AIR and target.domain in {
                Domain.AIR,
                Domain.SURFACE,
            }
        if platform.sensor.kind is SensorKind.SONAR:
            return platform.domain is Domain.UNDERWATER and target.domain in {
                Domain.UNDERWATER,
                Domain.SURFACE,
            }
        if platform.sensor.kind is SensorKind.RADAR:
            if target.domain is Domain.UNDERWATER and target.position[2] < -1.0:
                return False
            if platform.domain is Domain.SHORE:
                return target.domain in {Domain.AIR, Domain.SURFACE}
            if platform.domain is Domain.SURFACE:
                return target.domain is Domain.SURFACE or (
                    target.domain is Domain.AIR and target.position[2] <= 200.0
                )
        return False

    @staticmethod
    def _inside_field_of_view(platform: SensorPlatform, target: TargetTruth) -> bool:
        if platform.sensor.field_of_view_deg >= 360.0:
            return True
        east = target.position[0] - platform.position[0]
        north = target.position[1] - platform.position[1]
        bearing = math.degrees(math.atan2(east, north)) % 360.0
        error = (bearing - platform.heading_deg + 180.0) % 360.0 - 180.0
        return abs(error) <= platform.sensor.field_of_view_deg / 2.0

    def _contact_id(self, side: Side, entity_id: str) -> str:
        key = (side, entity_id)
        if key not in self._contact_ids:
            sequence = self._next_contact.get(side, 1)
            self._next_contact[side] = sequence + 1
            self._contact_ids[key] = f"contact-{side.value}-{sequence}"
        return self._contact_ids[key]

    def scan(
        self,
        platform: SensorPlatform,
        targets: tuple[TargetTruth, ...],
        *,
        tick: int,
        weather: Weather,
    ) -> tuple[ContactTrack, ...]:
        if not self._is_update_tick(platform.sensor, tick):
            return self.tracks_for_side(platform.side)
        detected_truth_ids: set[str] = set()
        for target in sorted(targets, key=lambda item: item.entity_id):
            if not self._cross_domain_allowed(platform, target):
                continue
            if not self._inside_field_of_view(platform, target):
                continue
            distance = math.dist(platform.position, target.position)
            sensor_range = effective_range(platform.sensor.range_m, platform.sensor.kind, weather)
            probability = (
                platform.sensor.base_detection_probability if distance <= sensor_range else 0.0
            )
            sample = float(self._rng.random())
            detected = sample < probability
            self.audit_log.append(
                {
                    "detected": detected,
                    "distance_m": distance,
                    "effective_range_m": sensor_range,
                    "probability": probability,
                    "random_sample": sample,
                    "sensor_id": platform.sensor.sensor_id,
                    "target_entity_id": target.entity_id,
                    "weather": weather.value,
                }
            )
            if not detected:
                continue
            detected_truth_ids.add(target.entity_id)
            noise_scale = max(
                platform.sensor.minimum_uncertainty_m,
                distance * platform.sensor.uncertainty_fraction,
            )
            noisy_position = tuple(
                coordinate + float(self._rng.normal(0.0, noise_scale))
                for coordinate in target.position
            )
            key = (platform.side, target.entity_id)
            previous = self._tracks.get(key)
            self._tracks[key] = ContactTrack(
                contact_id=self._contact_id(platform.side, target.entity_id),
                owner_side=platform.side,
                estimated_domain=target.domain,
                position=noisy_position,  # type: ignore[arg-type]
                velocity=target.velocity,
                uncertainty_m=noise_scale,
                confidence=(
                    platform.sensor.initial_confidence
                    if previous is None
                    else min(1.0, previous.confidence + 0.1)
                ),
                first_detected_tick=tick if previous is None else previous.first_detected_tick,
                detected_by=(platform.sensor.sensor_id,),
                last_update_tick=tick,
            )
        for key, track in tuple(self._tracks.items()):
            if key[0] is platform.side and key[1] not in detected_truth_ids:
                confidence = max(0.0, track.confidence - 0.1)
                if confidence <= 1e-9:
                    del self._tracks[key]
                    continue
                self._tracks[key] = ContactTrack(
                    contact_id=track.contact_id,
                    owner_side=track.owner_side,
                    estimated_domain=track.estimated_domain,
                    position=track.position,
                    velocity=track.velocity,
                    uncertainty_m=track.uncertainty_m * 1.25,
                    confidence=confidence,
                    first_detected_tick=track.first_detected_tick,
                    detected_by=track.detected_by,
                    inferred_type=track.inferred_type,
                    message_sent_tick=track.message_sent_tick,
                    message_source=track.message_source,
                    last_update_tick=track.last_update_tick,
                )
        return self.tracks_for_side(platform.side)

    def tracks_for_side(self, side: Side) -> tuple[ContactTrack, ...]:
        return tuple(track for (owner, _), track in self._tracks.items() if owner is side)

    def truth_by_contact(self) -> dict[str, str]:
        """Return the private active association used for engagement adjudication."""
        return {track.contact_id: truth_id for (_side, truth_id), track in self._tracks.items()}

    def snapshot(self) -> dict[str, Any]:
        return {
            "tick_seconds": self.tick_seconds,
            "rng_state": deepcopy(self._rng.bit_generator.state),
            "contact_ids": [
                [side.value, entity_id, contact_id]
                for (side, entity_id), contact_id in sorted(
                    self._contact_ids.items(), key=lambda item: (item[0][0].value, item[0][1])
                )
            ],
            "tracks": [
                [side.value, entity_id, asdict(track)]
                for (side, entity_id), track in sorted(
                    self._tracks.items(), key=lambda item: (item[0][0].value, item[0][1])
                )
            ],
            "next_contact": {side.value: value for side, value in self._next_contact.items()},
            "audit_log": deepcopy(self.audit_log),
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> DetectionEngine:
        engine = cls(SessionRNG(0), tick_seconds=float(snapshot["tick_seconds"]))
        engine._rng.bit_generator.state = deepcopy(snapshot["rng_state"])
        engine._contact_ids = {
            (Side(side), str(entity_id)): str(contact_id)
            for side, entity_id, contact_id in snapshot["contact_ids"]
        }
        engine._tracks = {}
        for side, entity_id, record in snapshot["tracks"]:
            values = dict(record)
            values["owner_side"] = Side(values["owner_side"])
            values["estimated_domain"] = Domain(values["estimated_domain"])
            engine._tracks[(Side(side), str(entity_id))] = ContactTrack(**values)
        engine._next_contact = {
            Side(side): int(value) for side, value in snapshot["next_contact"].items()
        }
        engine.audit_log = deepcopy(snapshot["audit_log"])
        return engine

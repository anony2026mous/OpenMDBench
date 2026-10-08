"""MD-AD-002 deterministic multi-sensor reporting and opaque public tracks."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from typing import Any

from openmdbench.core.entities import Domain, Lifecycle, PlatformAsset, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack, WorldState
from openmdbench.scenarios.md_ad_002_config import MDAD002Config, SensorProfile


def detection_probability(
    profile: SensorProfile,
    platform: PlatformAsset,
    target: PlatformAsset,
    *,
    weather: str,
    sea_state: int = 2,
    target_rcs_m2: float = 0.1,
) -> float:
    """Apply range, low-altitude, weather, motion, and health modifiers."""
    sensor_range = profile.range_m
    if profile.kind == "radar":
        sensor_range = min(
            sensor_range,
            profile.range_m * (target_rcs_m2 / profile.reference_rcs_m2) ** 0.25,
        )
    if target.position[2] <= 30.0:
        sensor_range = min(sensor_range, profile.low_altitude_range_m)
    weather_name = weather.removesuffix("_v1").split("_at_", 1)[0]
    if profile.kind == "eo_ir":
        weather_factor = {"fog": 0.1, "light_rain": 0.3, "cloudy": 0.8}.get(weather_name, 1.0)
    else:
        weather_factor = {
            "cloudy": 0.95,
            "light_rain": 0.9,
            "heavy_rain": 0.7,
            "fog": 0.8,
        }.get(weather_name, 1.0)
    distance = math.dist(platform.position, target.position)
    distance_factor = max(0.0, 1.0 - distance / (sensor_range * weather_factor))
    motion_factor = (
        0.6
        if platform.platform_type == "usv"
        and math.hypot(platform.velocity[0], platform.velocity[1]) > 0.5
        else 1.0
    )
    if (sea_state >= 4 or weather_name == "high_sea_state") and platform.platform_type == "usv":
        motion_factor *= 0.8
    if not platform.components.sensor_operational:
        return 0.0
    health_factor = 0.7 if platform.lifecycle is Lifecycle.DEGRADED else 1.0
    return profile.base_detection_probability * distance_factor * motion_factor * health_factor


@dataclass(frozen=True, slots=True)
class Measurement:
    truth_id: str
    sensor_id: str
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    uncertainty_m: float
    domain: Domain


class AD2Perception:
    """Own private truth association while exposing only opaque side-scoped contacts."""

    def __init__(self, config: MDAD002Config, seed: int) -> None:
        self.config = config
        self.rng = SessionRNG(seed)
        self.sensor_hits: dict[tuple[str, str], int] = {}
        self.pending: dict[str, list[Measurement]] = {}
        self.tracks: dict[str, ContactTrack] = {}
        self.misses: dict[str, int] = {}
        self.contact_ids: dict[str, str] = {}
        self.next_contact = 1
        self.false_tracks: dict[str, tuple[ContactTrack, int]] = {}
        self.evaluated_since_fusion: set[str] = set()
        self.events: list[dict[str, object]] = []

    def _contact_id(self, private_key: str) -> str:
        if private_key not in self.contact_ids:
            self.contact_ids[private_key] = f"contact-red-{self.next_contact}"
            self.next_contact += 1
        return self.contact_ids[private_key]

    def truth_by_contact(self) -> dict[str, str]:
        """Return the private association used only by referee-side combat."""
        return {
            contact_id: truth_id
            for truth_id, contact_id in self.contact_ids.items()
            if not truth_id.startswith("false-")
        }

    @staticmethod
    def _in_fov(profile: SensorProfile, platform: PlatformAsset, target: PlatformAsset) -> bool:
        if profile.field_of_view_deg >= 360.0:
            return True
        east = target.position[0] - platform.position[0]
        north = target.position[1] - platform.position[1]
        bearing = math.degrees(math.atan2(east, north)) % 360.0
        error = (bearing - platform.heading_deg + 180.0) % 360.0 - 180.0
        return abs(error) <= profile.field_of_view_deg / 2.0

    def _measure(
        self, profile: SensorProfile, platform: PlatformAsset, target: PlatformAsset
    ) -> Measurement:
        east = target.position[0] - platform.position[0]
        north = target.position[1] - platform.position[1]
        distance = math.hypot(east, north)
        noisy_range = max(
            0.0,
            distance
            * (
                1.0
                + float(
                    self.rng.stream("sensor_range_noise").normal(
                        0.0, self.config.tracking.range_noise_fraction
                    )
                )
            ),
        )
        bearing = math.atan2(east, north) + math.radians(
            float(
                self.rng.stream("sensor_bearing_noise").normal(
                    0.0, self.config.tracking.bearing_noise_deg
                )
            )
        )
        position = (
            platform.position[0] + noisy_range * math.sin(bearing),
            platform.position[1] + noisy_range * math.cos(bearing),
            target.position[2],
        )
        return Measurement(
            target.id,
            f"{platform.id}:{profile.sensor_id}",
            position,
            target.velocity,
            max(1.0, distance * self.config.tracking.range_noise_fraction),
            target.domain,
        )

    def update(self, world: WorldState, tick: int) -> tuple[ContactTrack, ...]:
        targets = tuple(
            entity
            for entity in world.entities_for_side(Side.BLUE)
            if isinstance(entity, PlatformAsset)
            and entity.lifecycle
            in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
        )
        active_truth_ids = {target.id for target in targets}
        self.evaluated_since_fusion.update(set(self.tracks) - active_truth_ids)
        for profile in self.config.sensors:
            if tick % profile.report_interval_ticks:
                continue
            for platform_id in sorted(profile.assigned_entities):
                platform = world.registry.get(platform_id)
                if not isinstance(platform, PlatformAsset):
                    continue
                sensor_key_prefix = f"{platform.id}:{profile.sensor_id}"
                self.evaluated_since_fusion.update(target.id for target in targets)
                if platform.components.sensor_mode == "off":
                    for target in targets:
                        self.sensor_hits[(sensor_key_prefix, target.id)] = 0
                    continue
                for target in targets:
                    key = (sensor_key_prefix, target.id)
                    probability = (
                        detection_probability(
                            profile,
                            platform,
                            target,
                            weather=world.weather,
                            sea_state=world.sea_state,
                            target_rcs_m2=self.config.tracking.target_rcs_m2,
                        )
                        if self._in_fov(profile, platform, target)
                        else 0.0
                    )
                    sample = float(self.rng.stream("sensor_detection").random())
                    detected = sample < probability
                    self.events.append(
                        {
                            "tick": tick,
                            "event_type": "sensor_report",
                            "sensor_id": sensor_key_prefix,
                            "detected": detected,
                            "probability": probability,
                            "truth_id": target.id,
                        }
                    )
                    if detected:
                        self.sensor_hits[key] = self.sensor_hits.get(key, 0) + 1
                        self.pending.setdefault(target.id, []).append(
                            self._measure(profile, platform, target)
                        )
                    else:
                        self.sensor_hits[key] = 0
        if tick % self.config.tracking.fusion_interval_ticks == 0:
            self._fuse(tick, world)
        false_public = tuple(
            track
            for track, age in self.false_tracks.values()
            if age >= self.config.tracking.confirmation_frames
        )
        return tuple(
            sorted((*self.tracks.values(), *false_public), key=lambda item: item.contact_id)
        )

    def _fuse(self, tick: int, world: WorldState) -> None:
        for truth_id, reports in sorted(self.pending.items()):
            confirmed = (
                max(
                    (
                        hits
                        for (sensor_key, target_id), hits in self.sensor_hits.items()
                        if target_id == truth_id
                    ),
                    default=0,
                )
                >= self.config.tracking.confirmation_frames
            )
            if not confirmed:
                continue
            count = len(reports)
            position = tuple(
                sum(report.position[axis] for report in reports) / count for axis in range(3)
            )
            uncertainty = min(report.uncertainty_m for report in reports)
            previous = self.tracks.get(truth_id)
            track = ContactTrack(
                contact_id=self._contact_id(truth_id),
                owner_side=Side.RED,
                estimated_domain=reports[0].domain,
                position=position,  # type: ignore[arg-type]
                velocity=reports[0].velocity,
                uncertainty_m=uncertainty,
                confidence=min(
                    1.0,
                    max(0.7, previous.confidence + 0.1 if previous is not None else 0.7)
                    + 0.05 * (count - 1),
                ),
                first_detected_tick=tick if previous is None else previous.first_detected_tick,
                detected_by=tuple(sorted({report.sensor_id for report in reports})),
                inferred_type="hostile_uav",
                last_update_tick=tick,
            )
            self.tracks[truth_id] = track
            self.misses[truth_id] = 0
            self.events.append(
                {
                    "tick": tick,
                    "event_type": "track_fused",
                    "contact_id": track.contact_id,
                    "sources": track.detected_by,
                }
            )
        for truth_id in tuple(self.tracks):
            if truth_id not in self.pending and truth_id in self.evaluated_since_fusion:
                self.misses[truth_id] = self.misses.get(truth_id, 0) + 1
                self.tracks[truth_id] = replace(
                    self.tracks[truth_id],
                    confidence=max(0.0, self.tracks[truth_id].confidence - 0.1),
                    uncertainty_m=self.tracks[truth_id].uncertainty_m * 1.25,
                )
                if self.misses[truth_id] >= self.config.tracking.deletion_frames:
                    del self.tracks[truth_id]
                    del self.misses[truth_id]
                    self.sensor_hits = {
                        key: value for key, value in self.sensor_hits.items() if key[1] != truth_id
                    }
        self.pending.clear()
        self.evaluated_since_fusion.clear()
        self._update_false_alarms(tick, world)

    def _update_false_alarms(self, tick: int, world: WorldState) -> None:
        interval = self.config.tracking.false_alarm_interval_ticks
        if interval is not None and tick and tick % interval == 0:
            key = f"false-{tick}"
            red_assets = world.entities_for_side(Side.RED)
            anchor = red_assets[0].position
            offset = self.rng.stream("false_alarm").uniform(-5_000.0, 5_000.0, size=2)
            track = ContactTrack(
                contact_id=self._contact_id(key),
                owner_side=Side.RED,
                estimated_domain=Domain.AIR,
                position=(anchor[0] + float(offset[0]), anchor[1] + float(offset[1]), 100.0),
                velocity=(0.0, 0.0, 0.0),
                uncertainty_m=1_000.0,
                confidence=0.35,
                first_detected_tick=tick,
                detected_by=("clutter",),
                inferred_type="unknown",
                last_update_tick=tick,
            )
            self.false_tracks[key] = (track, 0)
            self.events.append(
                {
                    "tick": tick,
                    "event_type": "false_alarm_created",
                    "contact_id": track.contact_id,
                }
            )
        for key, (track, age) in tuple(self.false_tracks.items()):
            age += 1
            if age > self.config.tracking.false_alarm_lifetime_frames:
                del self.false_tracks[key]
                self.events.append(
                    {
                        "tick": tick,
                        "event_type": "false_alarm_deleted",
                        "contact_id": track.contact_id,
                    }
                )
            else:
                aged = replace(
                    track,
                    confidence=max(
                        0.0,
                        0.35 * (1.0 - age / (self.config.tracking.false_alarm_lifetime_frames + 1)),
                    ),
                    uncertainty_m=track.uncertainty_m * 1.1,
                )
                self.false_tracks[key] = (aged, age)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(
            {
                "rng": self.rng.snapshot(),
                "sensor_hits": [[*key, value] for key, value in sorted(self.sensor_hits.items())],
                "pending": {
                    key: [asdict(item) for item in value] for key, value in self.pending.items()
                },
                "tracks": {key: asdict(value) for key, value in self.tracks.items()},
                "misses": self.misses,
                "contact_ids": self.contact_ids,
                "next_contact": self.next_contact,
                "false_tracks": {
                    key: [asdict(value[0]), value[1]] for key, value in self.false_tracks.items()
                },
                "evaluated_since_fusion": sorted(self.evaluated_since_fusion),
                "events": self.events,
            }
        )

    @classmethod
    def from_snapshot(cls, config: MDAD002Config, snapshot: dict[str, Any]) -> AD2Perception:
        tracker = cls(config, 0)
        tracker.rng = SessionRNG.from_snapshot(snapshot["rng"])
        tracker.sensor_hits = {
            (str(sensor), str(target)): int(value)
            for sensor, target, value in snapshot["sensor_hits"]
        }
        tracker.pending = {
            str(key): [
                Measurement(
                    truth_id=str(record["truth_id"]),
                    sensor_id=str(record["sensor_id"]),
                    position=tuple(record["position"]),
                    velocity=tuple(record["velocity"]),
                    uncertainty_m=float(record["uncertainty_m"]),
                    domain=Domain(record["domain"]),
                )
                for record in records
            ]
            for key, records in snapshot["pending"].items()
        }

        def restore_track(record: dict[str, Any]) -> ContactTrack:
            values = dict(record)
            values["owner_side"] = Side(values["owner_side"])
            values["estimated_domain"] = Domain(values["estimated_domain"])
            return ContactTrack(**values)

        tracker.tracks = {
            str(key): restore_track(record) for key, record in snapshot["tracks"].items()
        }
        tracker.misses = {str(key): int(value) for key, value in snapshot["misses"].items()}
        tracker.contact_ids = {
            str(key): str(value) for key, value in snapshot["contact_ids"].items()
        }
        tracker.next_contact = int(snapshot["next_contact"])
        tracker.false_tracks = {
            str(key): (restore_track(value[0]), int(value[1]))
            for key, value in snapshot["false_tracks"].items()
        }
        tracker.evaluated_since_fusion = set(snapshot["evaluated_since_fusion"])
        tracker.events = list(snapshot["events"])
        return tracker

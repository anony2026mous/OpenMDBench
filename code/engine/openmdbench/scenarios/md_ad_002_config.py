"""Strict, versioned configuration contract for the MD-AD-002 scenario family."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ScenarioId = Literal["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"]
MDAD002_CONFIG_PATHS: dict[str, str] = {
    "MD-AD-002-EASY": "openmdbench/config/md_ad_002_easy_v2.yaml",
    "MD-AD-002-MEDIUM": "openmdbench/config/md_ad_002_medium_v2.yaml",
    "MD-AD-002-HARD": "openmdbench/config/md_ad_002_hard_v2.yaml",
}
EXPECTED_MAP_HASH = "sha256:1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MapConfig(FrozenModel):
    map_id: Literal["weihai_v1"]
    raw_sha256: str
    geographic_crs: Literal["EPSG:4326"]
    xy_sha256: Literal[
        "sha256:6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067"
    ] = "sha256:6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067"
    origin_lonlat: tuple[float, float] = (122.0, 37.4)
    legacy_scale: float = Field(default=50.0, gt=0)
    legacy_offset_margin: float = Field(default=10.0, ge=0)

    @model_validator(mode="after")
    def known_asset(self) -> MapConfig:
        if self.raw_sha256 != EXPECTED_MAP_HASH:
            raise ValueError("map hash does not identify the frozen Weihai asset")
        return self


class GeoFeature(FrozenModel):
    lon_deg: float = Field(ge=-180, le=180)
    lat_deg: float = Field(ge=-90, le=90)


class DenialZone(GeoFeature):
    radius: float = Field(gt=0)
    radius_unit: Literal["metre"]


class SpawnZone(GeoFeature):
    half_width_m: float = Field(gt=0)


class Deployment(GeoFeature):
    id: str = Field(min_length=1)
    side: Literal["red"]
    platform: Literal["shore_radar", "interceptor_uav", "picket_usv"]
    terrain: Literal["land", "air", "water"]
    altitude_m: float = Field(ge=0)
    inventory: int = Field(ge=0)
    heading_deg: float = Field(default=0.0, ge=0, lt=360)
    speed_mps: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def valid_terrain(self) -> Deployment:
        required = {"shore_radar": "land", "interceptor_uav": "air", "picket_usv": "water"}[
            self.platform
        ]
        if self.terrain != required:
            raise ValueError(f"{self.platform} requires {required} terrain")
        if self.platform != "interceptor_uav" and self.altitude_m != 0:
            raise ValueError("surface deployments require zero altitude")
        return self


class Wave(FrozenModel):
    id: Literal["wave-1", "wave-2", "wave-3"]
    count: int = Field(gt=0)
    time_seconds: int = Field(ge=0)
    time_jitter_seconds: int = Field(default=0, ge=0)
    behavior: Literal["direct", "split_evasion", "multi_axis_serpentine"]
    altitude_min_m: float = Field(ge=0)
    altitude_max_m: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered_altitude(self) -> Wave:
        if self.altitude_min_m > self.altitude_max_m:
            raise ValueError("minimum altitude exceeds maximum altitude")
        return self


class DifficultyEvent(FrozenModel):
    tick: int = Field(ge=0)
    component: Literal["weather", "jamming", "suppression", "sea_state"]
    mode: str = Field(min_length=1)
    duration_seconds: int = Field(default=0, ge=0)


class Communication(FrozenModel):
    component: Literal["shore_uav_los", "usv_relay", "wired_shore"]
    range_m: float = Field(ge=0)
    bandwidth_bps: int = Field(gt=0)
    delay_ticks: int = Field(ge=0)


class SensorProfile(FrozenModel):
    sensor_id: Literal["radar_ew", "radar_gap", "radar_usv", "radar_uav", "eo_uav"]
    assigned_entities: tuple[str, ...]
    kind: Literal["radar", "eo_ir"]
    range_m: float = Field(gt=0)
    low_altitude_range_m: float = Field(gt=0)
    report_interval_ticks: int = Field(gt=0)
    base_detection_probability: float = Field(ge=0, le=1)
    field_of_view_deg: float = Field(gt=0, le=360)
    reference_rcs_m2: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def validate_ranges(self) -> SensorProfile:
        if self.low_altitude_range_m > self.range_m:
            raise ValueError("low-altitude sensor range cannot exceed nominal range")
        return self


class TrackingConfig(FrozenModel):
    confirmation_frames: int = Field(ge=1)
    deletion_frames: int = Field(ge=1)
    fusion_interval_ticks: int = Field(ge=1)
    range_noise_fraction: float = Field(ge=0, le=1)
    bearing_noise_deg: float = Field(ge=0, le=180)
    false_alarm_interval_ticks: int | None = Field(default=None, ge=1)
    false_alarm_lifetime_frames: int = Field(default=5, ge=1)
    target_rcs_m2: float = Field(gt=0)


class Weapon(FrozenModel):
    component: Literal["uav_interceptor_missile", "shore_ciws"]
    inventory: int = Field(ge=0)
    minimum_range_m: float = Field(ge=0)
    maximum_range_m: float = Field(gt=0)
    hit_probability: float = Field(ge=0, le=1)
    range_unit: Literal["metre"]
    damage: float = Field(gt=0, le=1)
    cooldown_ticks: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered_range(self) -> Weapon:
        if self.minimum_range_m > self.maximum_range_m:
            raise ValueError("minimum range exceeds maximum range")
        return self


class Rules(FrozenModel):
    mode: str = Field(min_length=1)
    breach_threshold: int = Field(gt=0)
    time_limit_seconds: int = Field(gt=0)


class Scoring(FrozenModel):
    mode: Literal["md_ad_002_v1"]
    weights: dict[str, float]

    @model_validator(mode="after")
    def weights_valid(self) -> Scoring:
        if (
            any(value < 0 for value in self.weights.values())
            or abs(sum(self.weights.values()) - 1) > 1e-6
        ):
            raise ValueError("scoring weights must be nonnegative and sum to one")
        return self


class Visualization(FrozenModel):
    layers: tuple[
        Literal["island", "denial_zone", "spawn_zones", "entities", "waves", "links", "score"], ...
    ]


class MDAD002Config(FrozenModel):
    schema_version: Literal["1.0"]
    config_version: Literal["2.0.0"]
    scenario_id: ScenarioId
    difficulty: Literal["easy", "medium", "hard"]
    map: MapConfig
    island: GeoFeature
    denial_zone: DenialZone
    spawn_zones: tuple[Literal["east_sea", "northeast_sea"], ...]
    spawn_zone_geometry: dict[Literal["east_sea", "northeast_sea"], SpawnZone]
    deployments: tuple[Deployment, ...]
    waves: tuple[Wave, ...]
    difficulty_events: tuple[DifficultyEvent, ...]
    weather_profile: Literal["clear_v1", "cloudy_at_600_v1", "rain_or_fog_at_900_v1"]
    sensors: tuple[SensorProfile, ...]
    tracking: TrackingConfig
    communications: tuple[Communication, ...]
    weapons: tuple[Weapon, ...]
    adjudication: Rules
    scoring: Scoring
    visualization: Visualization

    @model_validator(mode="after")
    def complete_contract(self) -> MDAD002Config:
        expected_difficulty = self.scenario_id.rsplit("-", 1)[1].lower()
        if self.difficulty != expected_difficulty:
            raise ValueError("scenario ID and difficulty disagree")
        ids = [item.id for item in self.deployments]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate deployment ID")
        if len(self.deployments) != 7:
            raise ValueError("exactly seven red deployments are required")
        if set(self.spawn_zone_geometry) != {"east_sea", "northeast_sea"}:
            raise ValueError("both spawn zone geometries are required")
        sensor_ids = [sensor.sensor_id for sensor in self.sensors]
        if set(sensor_ids) != {"radar_ew", "radar_gap", "radar_usv", "radar_uav", "eo_uav"}:
            raise ValueError("all five sensor profiles are required")
        if len(sensor_ids) != len(set(sensor_ids)):
            raise ValueError("duplicate sensor profile ID")
        deployment_ids = {item.id for item in self.deployments}
        if any(
            entity_id not in deployment_ids
            for sensor in self.sensors
            for entity_id in sensor.assigned_entities
        ):
            raise ValueError("sensor profile references unknown deployment")
        expected_assignments = {
            "radar_ew": {"red-island-radar-1"},
            "radar_gap": {"red-island-radar-2"},
            "radar_usv": {"red-picket-usv-1", "red-picket-usv-2"},
            "radar_uav": {
                "red-interceptor-uav-1",
                "red-interceptor-uav-2",
                "red-interceptor-uav-3",
            },
            "eo_uav": {
                "red-interceptor-uav-1",
                "red-interceptor-uav-2",
                "red-interceptor-uav-3",
            },
        }
        if any(
            set(sensor.assigned_entities) != expected_assignments[sensor.sensor_id]
            for sensor in self.sensors
        ):
            raise ValueError("sensor profile assignment is incompatible with platform role")
        if [wave.count for wave in self.waves] != [4, 5, 6]:
            raise ValueError("waves must contain the normative 4/5/6 attackers")
        weapon_totals = {weapon.component: weapon.inventory for weapon in self.weapons}
        deployment_totals = {
            "uav_interceptor_missile": sum(
                item.inventory for item in self.deployments if item.platform == "interceptor_uav"
            ),
            "shore_ciws": sum(
                item.inventory for item in self.deployments if item.platform == "shore_radar"
            ),
        }
        if weapon_totals != deployment_totals:
            raise ValueError("weapon inventory totals disagree with platform deployments")
        if any(
            wave.time_seconds + wave.time_jitter_seconds >= self.adjudication.time_limit_seconds
            for wave in self.waves
        ):
            raise ValueError("wave time exceeds scenario time limit")
        return self


class LoadedMDAD002Config(NamedTuple):
    config: MDAD002Config
    sha256: str
    path: Path


def load_md_ad_002_config(scenario_id: str) -> LoadedMDAD002Config:
    try:
        relative = MDAD002_CONFIG_PATHS[scenario_id]
    except KeyError as error:
        raise ValueError(f"unknown MD-AD-002 scenario_id: {scenario_id}") from error
    path = Path(__file__).parents[2] / relative
    payload = path.read_bytes()
    raw = yaml.safe_load(payload)
    config = MDAD002Config.model_validate(raw)
    if config.scenario_id != scenario_id:
        raise ValueError("requested scenario ID differs from internal config ID")
    effective = yaml.safe_dump(
        config.model_dump(mode="json"), sort_keys=True, allow_unicode=True
    ).encode()
    return LoadedMDAD002Config(config, "sha256:" + hashlib.sha256(effective).hexdigest(), path)

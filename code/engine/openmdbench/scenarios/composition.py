"""Generic declarative scenario composition schema.

This schema describes *instances* and their catalog-backed components.  It is
deliberately independent of benchmark IDs: MD-AD-002 is one possible package,
not the schema of every future area-denial scenario.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CompositionModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class InitialState(CompositionModel):
    lon_deg: float
    lat_deg: float
    altitude_m: float
    heading_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0)
    terrain: Literal["air", "water", "land"]


class EntityInstance(CompositionModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    side: Literal["blue", "red"]
    platform_ref: str
    dynamics_ref: str
    loadout_ref: str | None = None
    sensor_refs: tuple[str, ...] = ()
    communication_ref: str | None = None
    initial_state: InitialState
    inventory: dict[str, int] = Field(default_factory=dict)
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def positive_inventory(self) -> EntityInstance:
        if any(value < 0 for value in self.inventory.values()):
            raise ValueError("inventory quantities must be nonnegative")
        return self


class SpawnZone(CompositionModel):
    id: str
    lon_deg: float
    lat_deg: float
    half_width_m: float = Field(gt=0.0)


class MapBinding(CompositionModel):
    map_id: str
    version: str
    raw_sha256: str
    xy_sha256: str
    origin_lonlat: tuple[float, float]
    legacy_scale: float = Field(gt=0.0)
    offset_margin: float = Field(ge=0.0)


class EntityWave(CompositionModel):
    id: str
    entity_prefix: str
    side: Literal["blue", "red"]
    count: int = Field(gt=0, le=1_000)
    platform_ref: str
    dynamics_ref: str
    loadout_ref: str | None = None
    sensor_refs: tuple[str, ...] = ()
    communication_ref: str | None = None
    inventory: dict[str, int] = Field(default_factory=dict)
    spawn_zone: str
    time_tick: int = Field(ge=0)
    time_jitter_ticks: int = Field(default=0, ge=0)
    behavior: str = "direct"
    altitude_min_m: float = Field(ge=0.0)
    altitude_max_m: float = Field(ge=0.0)
    speed_mps: float = Field(ge=0.0)

    @model_validator(mode="after")
    def valid_range_and_inventory(self) -> EntityWave:
        if self.altitude_min_m > self.altitude_max_m:
            raise ValueError("minimum wave altitude exceeds maximum")
        if any(value < 0 for value in self.inventory.values()):
            raise ValueError("inventory quantities must be nonnegative")
        return self


class ScenarioEvent(CompositionModel):
    tick: int = Field(ge=0)
    type: Literal[
        "spawn",
        "weather_change",
        "jamming_start",
        "jamming_end",
        "component_suppression",
        "zone_activation",
        "message",
        "mission_marker",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)


class GenericComposition(CompositionModel):
    schema_version: Literal["composition@1.0"]
    scenario_id: str = Field(max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    scenario_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    mission_model: str = "generic_timeline_v1"
    map: MapBinding
    primary_entity_id: str
    protected_point_lonlat: tuple[float, float]
    entities: tuple[EntityInstance, ...] = Field(min_length=1, max_length=10_000)
    spawn_zones: tuple[SpawnZone, ...] = Field(default=(), max_length=1_000)
    waves: tuple[EntityWave, ...] = Field(default=(), max_length=1_000)
    events: tuple[ScenarioEvent, ...] = Field(default=(), max_length=10_000)
    adjudication: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_and_referenced(self) -> GenericComposition:
        entity_ids = [item.id for item in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entity IDs must be unique")
        if self.primary_entity_id not in entity_ids:
            raise ValueError("primary_entity_id must reference a deployed entity")
        zone_ids = [item.id for item in self.spawn_zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("spawn zone IDs must be unique")
        missing = sorted({wave.spawn_zone for wave in self.waves} - set(zone_ids))
        if missing:
            raise ValueError(f"waves reference missing spawn zones: {missing}")
        wave_ids = [item.id for item in self.waves]
        if len(wave_ids) != len(set(wave_ids)):
            raise ValueError("wave IDs must be unique")
        if len(self.entities) + sum(item.count for item in self.waves) > 10_000:
            raise ValueError("scenario may contain at most 10000 resolved entities")
        return self


__all__ = ["EntityInstance", "EntityWave", "GenericComposition", "ScenarioEvent"]

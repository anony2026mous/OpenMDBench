"""Immutable, versioned resource definitions for the unified catalog."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ResourceType = Literal[
    "maps",
    "platforms",
    "dynamics",
    "loadouts",
    "sensors",
    "weapons",
    "effects",
    "communications",
    "energy",
    "environments",
    "missions",
    "scoring",
    "visualization_assets",
    "trusted_model_plugins",
]


def _finite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("catalog numeric values must be finite")
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            _finite(item)
    elif isinstance(value, Mapping):
        for item in value.values():
            _finite(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _finite(item)


class CatalogModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_numbers_only(self) -> CatalogModel:
        for value in self.__dict__.values():
            _finite(value)
        return self


class EngineCompatibility(CatalogModel):
    engine: str = Field(
        pattern=r"^(?:(?:>=|>|<=|<|==)\d+\.\d+\.\d+)"
        r"(?:,(?:>=|>|<=|<|==)\d+\.\d+\.\d+)*$"
    )


class ResourceDefinition(CatalogModel):
    schema_version: Literal["1.0"]
    resource_type: ResourceType
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    display_name: str = Field(min_length=1)
    model: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    compatibility: EngineCompatibility
    dependencies: tuple[str, ...] = ()
    metadata_json: str = "{}"


class EffectDefinition(ResourceDefinition):
    resource_type: Literal["effects"] = "effects"
    damage_fraction: float = Field(gt=0.0, le=1.0)
    terminal_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class WeaponDefinition(ResourceDefinition):
    resource_type: Literal["weapons"] = "weapons"
    allowed_platform_types: tuple[str, ...] = Field(min_length=1)
    target_domains: tuple[Literal["air", "surface", "shore", "underwater"], ...] = Field(
        min_length=1
    )
    minimum_range_m: float = Field(ge=0.0)
    maximum_range_m: float = Field(gt=0.0)
    hit_probability: float = Field(ge=0.0, le=1.0)
    guidance: str = Field(min_length=1)
    contact_required: bool
    cooldown_ticks: int = Field(ge=0)
    rounds_per_action: int = Field(ge=1)
    energy_cost: float = Field(ge=0.0)
    effect_ref: str

    @model_validator(mode="after")
    def valid_envelope_and_effect(self) -> WeaponDefinition:
        if self.minimum_range_m > self.maximum_range_m:
            raise ValueError("minimum range exceeds maximum range")
        if self.effect_ref not in self.dependencies:
            raise ValueError("effect_ref must be declared as a dependency")
        return self


class SensorDefinition(ResourceDefinition):
    resource_type: Literal["sensors"] = "sensors"
    compatible_platform_types: tuple[str, ...] = Field(min_length=1)
    kind: Literal["radar", "eo_ir", "sonar"]
    range_m: float = Field(gt=0.0)
    update_hz: float = Field(gt=0.0)
    base_detection_probability: float = Field(ge=0.0, le=1.0)
    field_of_view_deg: float = Field(gt=0.0, le=360.0)
    low_altitude_range_m: float | None = Field(default=None, gt=0.0)
    reference_rcs_m2: float = Field(default=1.0, gt=0.0)


class DynamicsDefinition(ResourceDefinition):
    resource_type: Literal["dynamics"] = "dynamics"
    compatible_platform_types: tuple[str, ...] = Field(min_length=1)
    spatial_dimensions: Literal[2, 3]
    maximum_speed_mps: float = Field(ge=0.0)


class LoadoutDefinition(ResourceDefinition):
    resource_type: Literal["loadouts"] = "loadouts"
    compatible_platform_types: tuple[str, ...] = Field(min_length=1)
    weapon_refs: tuple[str, ...]
    mass_kg: float = Field(ge=0.0)
    slot_requirements: tuple[str, ...] = ()


class CommunicationLinkDefinition(CatalogModel):
    component: str = Field(min_length=1)
    range_m: float = Field(ge=0.0)
    bandwidth_bps: int = Field(gt=0)
    delay_ticks: int = Field(ge=0)


class CommunicationDefinition(ResourceDefinition):
    resource_type: Literal["communications"] = "communications"
    links: tuple[CommunicationLinkDefinition, ...] = Field(min_length=1)


class ScoringDefinition(ResourceDefinition):
    resource_type: Literal["scoring"] = "scoring"
    weights: tuple[tuple[str, float], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_weights(self) -> ScoringDefinition:
        names = [name for name, _weight in self.weights]
        if len(names) != len(set(names)):
            raise ValueError("duplicate scoring metric")
        if any(weight < 0.0 for _name, weight in self.weights):
            raise ValueError("scoring weights must be nonnegative")
        if abs(sum(weight for _name, weight in self.weights) - 1.0) > 1e-9:
            raise ValueError("scoring weights must sum to one")
        return self


class PlatformDefinition(ResourceDefinition):
    resource_type: Literal["platforms"] = "platforms"
    domain: Literal["air", "surface", "shore", "underwater"]
    platform_type: str = Field(min_length=1)
    dimensions_m: tuple[float, float, float]
    collision_radius_m: float = Field(gt=0.0)
    health_threshold: float = Field(gt=0.0)
    energy_capacity: float = Field(gt=0.0)
    loadout_slots: tuple[str, ...]
    payload_capacity_kg: float = Field(ge=0.0)
    allowed_dynamics: tuple[str, ...] = Field(min_length=1)
    visualization_ref: str
    fidelity: str = Field(min_length=1)

    @model_validator(mode="after")
    def positive_dimensions(self) -> PlatformDefinition:
        if any(value <= 0.0 for value in self.dimensions_m):
            raise ValueError("platform dimensions must be positive")
        return self


CatalogDefinition = (
    ResourceDefinition
    | EffectDefinition
    | WeaponDefinition
    | SensorDefinition
    | PlatformDefinition
    | DynamicsDefinition
    | LoadoutDefinition
    | CommunicationDefinition
    | ScoringDefinition
)


__all__ = [
    "CatalogDefinition",
    "CommunicationDefinition",
    "CommunicationLinkDefinition",
    "EffectDefinition",
    "DynamicsDefinition",
    "EngineCompatibility",
    "PlatformDefinition",
    "LoadoutDefinition",
    "ResourceDefinition",
    "ResourceType",
    "SensorDefinition",
    "ScoringDefinition",
    "WeaponDefinition",
]

"""Immutable, fully resolved scenario artifacts produced by the compiler.

``ResolvedScenario`` is the only formal input a simulation session accepts
(RF-ADR-001 decision 2): every resource reference is expanded, coordinates
are in the unified local metre frame, units are declared, the canonical
formal component configuration is embedded so a session can be created from
the artifact alone, and the whole artifact carries a stable content hash.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.core.rng import configuration_hash

SCHEMA_VERSION: Literal["1.0"] = "1.0"


class FrozenDict(dict[str, Any]):
    """JSON-compatible dictionary that rejects mutation after validation."""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> FrozenDict:
        frozen = cls()
        for key, item in value.items():
            dict.__setitem__(frozen, key, _freeze(item))
        return frozen

    @staticmethod
    def _immutable() -> Never:
        raise TypeError("resolved scenario mappings are immutable")

    def __setitem__(self, key: str, value: Any) -> None:
        self._immutable()

    def __delitem__(self, key: str) -> None:
        self._immutable()

    def clear(self) -> None:
        self._immutable()

    def pop(self, key: str, default: Any = None) -> Any:
        self._immutable()

    def popitem(self) -> tuple[str, Any]:
        self._immutable()

    def setdefault(self, key: str, default: Any = None) -> Any:
        self._immutable()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._immutable()

    def __ior__(self, value: object) -> Never:  # type: ignore[misc]
        self._immutable()


def _freeze(value: Any) -> Any:
    if isinstance(value, FrozenDict):
        return value
    if isinstance(value, Mapping):
        return FrozenDict.from_mapping(value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _finite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("resolved scenario numeric values must be finite")
    if isinstance(value, Mapping):
        for item in value.values():
            _finite(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _finite(item)


class ResolvedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_numbers_only(self) -> ResolvedModel:
        for name, value in tuple(self.__dict__.items()):
            _finite(value)
            object.__setattr__(self, name, _freeze(value))
        return self


class ResolvedMap(ResolvedModel):
    """Verified map identity; unverified for generic (non-formal) scenarios."""

    map_id: str
    version: str | None = None
    raw_sha256: str | None = None
    xy_sha256: str | None = None
    geographic_crs: str | None = None
    local_crs: str | None = None
    legacy_projection: str | None = None
    origin_lonlat: tuple[float, float] | None = None
    legacy_scale: float | None = None
    offset_margin: float | None = None
    offset_xy: tuple[float, float] | None = None
    verified: bool = False


class ResolvedClock(ResolvedModel):
    time_limit_ticks: int = Field(gt=0)
    tick_seconds: float | None = Field(default=None, gt=0.0)
    time_unit: Literal["tick"] = "tick"


class ResolvedDeployment(ResolvedModel):
    entity_id: str
    side: Literal["blue", "red"]
    platform_type: Literal["uav", "usv", "shore_radar", "auv"]
    domain: Literal["air", "surface", "shore", "underwater"]
    lon_deg: float | None = None
    lat_deg: float | None = None
    position_m: tuple[float, float, float]
    heading_deg: float
    speed_mps: float = Field(ge=0.0)
    weapon_inventory: dict[str, int] = Field(default_factory=dict)
    terrain: Literal["air", "water", "land"] | None = None
    platform_ref: str | None = None
    dynamics_ref: str | None = None
    loadout_ref: str | None = None
    sensor_refs: tuple[str, ...] = ()
    communication_ref: str | None = None


class ResolvedZone(ResolvedModel):
    zone_id: str
    kind: Literal["denial", "spawn"]
    lon_deg: float
    lat_deg: float
    centre_m: tuple[float, float]
    radius_m: float | None = Field(default=None, gt=0.0)
    half_width_m: float | None = Field(default=None, gt=0.0)


class ResolvedWave(ResolvedModel):
    wave_id: str
    count: int = Field(gt=0)
    base_tick: int = Field(ge=0)
    jitter_ticks: int = Field(ge=0)
    behavior: str = Field(min_length=1)
    altitude_min_m: float = Field(ge=0.0)
    altitude_max_m: float = Field(ge=0.0)
    entity_prefix: str = "blue-striker-uav"
    side: Literal["blue", "red"] = "blue"
    platform_type: Literal["uav", "usv", "shore_radar", "auv"] = "uav"
    spawn_zone: str | None = None
    speed_mps: float = 30.0
    weapon_inventory: dict[str, int] = Field(default_factory=dict)
    platform_ref: str | None = None
    dynamics_ref: str | None = None
    loadout_ref: str | None = None
    sensor_refs: tuple[str, ...] = ()
    communication_ref: str | None = None

    @model_validator(mode="after")
    def ordered_altitude(self) -> ResolvedWave:
        if self.altitude_min_m > self.altitude_max_m:
            raise ValueError("minimum altitude exceeds maximum altitude")
        return self


class ResolvedEvent(ResolvedModel):
    tick: int = Field(ge=0)
    event_type: str = Field(min_length=1)
    origin: Literal["weather", "difficulty", "referee"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ResolvedCatalog(ResolvedModel):
    schema_version: Literal["1.0"] = "1.0"
    content_hash: str = Field(min_length=1)
    resource_hashes: tuple[tuple[str, str], ...] = ()


class ResolvedScenario(ResolvedModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    scenario_id: str = Field(min_length=1)
    scenario_version: str = Field(min_length=1)
    category: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    formal: bool
    package_hash: str
    map: ResolvedMap
    clock: ResolvedClock
    deployments: tuple[ResolvedDeployment, ...] = Field(min_length=1)
    zones: tuple[ResolvedZone, ...] = ()
    waves: tuple[ResolvedWave, ...] = ()
    events: tuple[ResolvedEvent, ...] = ()
    catalog: ResolvedCatalog | None = None
    scoring: dict[str, Any]
    adjudication: dict[str, Any]
    roe: tuple[str, ...] = ()
    public_briefing: str = Field(min_length=1)
    components: dict[str, dict[str, Any]]
    component_hashes: dict[str, str]
    coordinate_system: Literal["local_aeqd_metre"] = "local_aeqd_metre"
    units: dict[str, str]
    resolved_hash: str = Field(min_length=1)

    @model_validator(mode="after")
    def stable_ordering(self) -> ResolvedScenario:
        deployment_ids = tuple(item.entity_id for item in self.deployments)
        if deployment_ids != tuple(sorted(deployment_ids)):
            raise ValueError("deployments must be sorted by entity_id")
        if len(deployment_ids) != len(set(deployment_ids)):
            raise ValueError("duplicate entity_id in resolved deployments")
        wave_keys = tuple((item.base_tick, item.wave_id) for item in self.waves)
        if wave_keys != tuple(sorted(wave_keys)):
            raise ValueError("waves must be sorted by (base_tick, wave_id)")
        event_keys = tuple((item.tick, item.event_type, item.origin) for item in self.events)
        if event_keys != tuple(sorted(event_keys)):
            raise ValueError("events must be sorted by (tick, event_type, origin)")
        if set(self.component_hashes) != set(self.components):
            raise ValueError("component_hashes must cover exactly the embedded components")
        if self.resolved_hash != "unhashed" and self.resolved_hash != self.expected_hash():
            raise ValueError("resolved scenario hash does not match its content")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        """JSON-compatible payload used for the resolved content hash."""
        return self.model_dump(mode="json", exclude={"resolved_hash"})

    def expected_hash(self) -> str:
        return configuration_hash(self.canonical_payload())

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, encoded: str) -> ResolvedScenario:
        resolved = cls.model_validate(json.loads(encoded))
        if resolved.resolved_hash != resolved.expected_hash():
            raise ValueError("resolved scenario hash does not match its content")
        return resolved


def build_resolved_scenario(payload: Mapping[str, Any]) -> ResolvedScenario:
    """Validate the complete artifact, then bind its stable content hash."""
    data = {key: value for key, value in payload.items() if key != "resolved_hash"}
    resolved = ResolvedScenario.model_validate({**data, "resolved_hash": "unhashed"})
    data["resolved_hash"] = resolved.expected_hash()
    return ResolvedScenario.model_validate(data)

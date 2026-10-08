"""Scenario-independent, immutable public contracts for platform schema v2.

This module deliberately contains data contracts only.  It has no dependency on
legacy side enums, formal scenario identifiers, catalogs, or runtime mechanisms.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _FrozenDict(dict[str, Any]):
    """JSON-serializable mapping whose complete value graph is immutable."""

    @classmethod
    def from_mapping(cls, value: Mapping[object, Any]) -> _FrozenDict:
        frozen = cls()
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON mapping keys must be strings")
            dict.__setitem__(frozen, key, _deep_freeze(item))
        return frozen

    @staticmethod
    def _reject() -> Never:
        raise TypeError("schema v2 mappings are immutable")

    def __setitem__(self, key: str, value: Any) -> None:
        self._reject()

    def __delitem__(self, key: str) -> None:
        self._reject()

    def clear(self) -> None:
        self._reject()

    def pop(self, key: str, default: Any = None) -> Any:
        self._reject()

    def popitem(self) -> tuple[str, Any]:
        self._reject()

    def setdefault(self, key: str, default: Any = None) -> Any:
        self._reject()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._reject()

    def __ior__(self, value: object) -> Never:  # type: ignore[misc]
        self._reject()


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, _FrozenDict):
        return value
    if isinstance(value, Mapping):
        return _FrozenDict.from_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _require_json_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("all schema v2 numeric values must be finite")
    if isinstance(value, float):
        return
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            _require_json_value(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON mapping keys must be strings")
            _require_json_value(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _require_json_value(item)
    else:
        raise ValueError(f"value of type {type(value).__name__} is not a JSON value")


class CoreModelV2(BaseModel):
    """Strict immutable base shared by all public v2 DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    schema_version: Literal["2.0"]

    @model_validator(mode="after")
    def freeze_and_reject_nonfinite(self) -> Self:
        for name, value in tuple(self.__dict__.items()):
            _require_json_value(value)
            object.__setattr__(self, name, _deep_freeze(value))
        return self


class FactionV2(CoreModelV2):
    id: str = Field(min_length=1)
    display_name: str | None = None
    tags: tuple[str, ...] = ()


class RelationshipV2(CoreModelV2):
    source_faction_id: str = Field(min_length=1)
    target_faction_id: str = Field(min_length=1)
    relation: Literal["hostile", "friendly", "neutral", "protected"]


class InitialStateV2(CoreModelV2):
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    heading_deg: float = Field(ge=0.0, lt=360.0)
    health: float = Field(default=1.0, ge=0.0, le=1.0)
    energy: float | None = Field(default=None, ge=0.0, le=1.0)
    component_states: dict[str, Any] = Field(default_factory=dict)


class EntitySpecV2(CoreModelV2):
    id: str = Field(min_length=1)
    faction_id: str = Field(min_length=1)
    platform_ref: str = Field(min_length=1)
    dynamics_ref: str | None = None
    loadout_ref: str | None = None
    component_refs: tuple[str, ...] = ()
    ammunition: dict[str, int] = Field(default_factory=dict)
    target_domains: tuple[str, ...] = ()
    initial_state: InitialStateV2
    controller_slot: str | None = None
    tags: tuple[str, ...] = ()
    # Preserve the pre-policy runtime contract for existing scenario packages;
    # new packages may explicitly select despawn.
    destroyed_lifecycle: Literal["wreck", "despawn"] = "wreck"

    @model_validator(mode="after")
    def validate_runtime_inventory(self) -> Self:
        if any(count < 0 for count in self.ammunition.values()):
            raise ValueError("ammunition count cannot be negative")
        if len(self.target_domains) != len(set(self.target_domains)):
            raise ValueError("duplicate target domain")
        return self


class FormationSpecV2(CoreModelV2):
    id: str = Field(min_length=1)
    count: int = Field(ge=1)
    id_pattern: str = Field(min_length=1)
    entity_template: EntitySpecV2
    offsets_m: tuple[tuple[float, float, float], ...] = ()

    @model_validator(mode="after")
    def validate_expansion_contract(self) -> Self:
        if "{index" not in self.id_pattern:
            raise ValueError("formation id_pattern must contain an {index} placeholder")
        try:
            expanded = tuple(self.id_pattern.format(index=index) for index in range(self.count))
        except (IndexError, KeyError, ValueError) as error:
            raise ValueError("formation id_pattern is invalid") from error
        if len(expanded) != len(set(expanded)):
            raise ValueError("formation id_pattern must generate unique IDs")
        if len(self.offsets_m) not in {0, 1, self.count}:
            raise ValueError("formation offsets must be empty, singular, or match count")
        return self


class ZoneV2(CoreModelV2):
    id: str = Field(min_length=1)
    geometry_type: str = Field(min_length=1)
    coordinates_m: tuple[tuple[float, float], ...]
    tags: tuple[str, ...] = ()


class SpatialDamagePolicyV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    collision_effect_ref: str = Field(min_length=1)
    magnitude_model: Literal["constant", "scaled_relative_speed", "relative_kinetic_energy"]
    magnitude_parameters: dict[str, float]
    output_unit: Literal["1"]

    @model_validator(mode="after")
    def validate_magnitude_parameters(self) -> Self:
        expected = {
            "constant": "value",
            "scaled_relative_speed": "scale",
            "relative_kinetic_energy": "scale",
        }[self.magnitude_model]
        if set(self.magnitude_parameters) != {expected}:
            raise ValueError("spatial magnitude parameters do not match the selected model")
        value = self.magnitude_parameters[expected]
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("spatial magnitude parameter must be finite and nonnegative")
        return self


class RoePolicyV2(CoreModelV2):
    id: str = Field(min_length=1)
    source_faction_id: str = Field(min_length=1)
    target_faction_id: str = Field(min_length=1)
    relationship: str = Field(min_length=1)
    engagement_permitted: bool


class WorldSpecV2(CoreModelV2):
    coordinate_system: Literal["local_m", "wgs84", "map"]
    map_ref: str | None = None
    zones: tuple[ZoneV2, ...] = ()
    boundary_policy: str | None = None
    spatial_damage_policy: SpatialDamagePolicyV2 | None = None
    roe_rules: tuple[RoePolicyV2, ...] = ()
    duration_ticks: int | None = Field(default=None, gt=0)
    tick_seconds: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def validate_zone_ids(self) -> Self:
        zone_ids = tuple(item.id for item in self.zones)
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("duplicate zone id")
        rule_ids = tuple(item.id for item in self.roe_rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("duplicate ROE rule id")
        return self


class EventSpecV2(CoreModelV2):
    id: str = Field(min_length=1)
    event_type: Literal[
        "spawn",
        "despawn",
        "weather_change",
        "zone_activation",
        "jamming_start",
        "jamming_end",
        "component_suppression",
        "message",
        "mission_marker",
        "apply_effect",
        "spatial_effect_trigger",
    ]
    trigger: dict[str, Any]
    priority: int = 0
    depends_on: tuple[str, ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)


class MissionSelectorV2(CoreModelV2):
    factions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


class ConditionV2(CoreModelV2):
    operator: Literal[
        "all",
        "any",
        "not",
        "count",
        "zone",
        "state",
        "survival",
        "time",
        "event",
        "wave",
        "contact",
        "communication",
        "resource",
        "score",
    ]
    operands: tuple[ConditionV2, ...] = ()
    selector: MissionSelectorV2 | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class MissionRuleV2(CoreModelV2):
    id: str = Field(min_length=1)
    priority: int = 0
    condition: ConditionV2
    outcome: str = Field(min_length=1)
    latch: bool = True


class ScoreMetricV2(CoreModelV2):
    id: str = Field(min_length=1)
    value: float | None = None
    available: bool = False
    weight: float = Field(default=1.0, ge=0.0)

    @model_validator(mode="after")
    def validate_availability(self) -> Self:
        if self.available != (self.value is not None):
            raise ValueError("score value must be null exactly when metric is N/A/ unavailable")
        return self


class CoreScenarioV2(CoreModelV2):
    scenario_id: str = Field(min_length=1)
    factions: tuple[FactionV2, ...] = Field(min_length=1)
    relationships: tuple[RelationshipV2, ...] = ()
    entities: tuple[EntitySpecV2, ...] = ()
    formations: tuple[FormationSpecV2, ...] = ()
    world: WorldSpecV2
    events: tuple[EventSpecV2, ...] = ()
    mission_rules: tuple[MissionRuleV2, ...] = ()
    score_metrics: tuple[ScoreMetricV2, ...] = ()

    @model_validator(mode="after")
    def validate_faction_references(self) -> Self:
        faction_ids = tuple(item.id for item in self.factions)
        if len(faction_ids) != len(set(faction_ids)):
            raise ValueError("duplicate faction id")
        known = set(faction_ids)
        for relation in self.relationships:
            if relation.source_faction_id not in known or relation.target_faction_id not in known:
                raise ValueError("relationship references an unknown faction")
        for entity in self.entities:
            if entity.faction_id not in known:
                raise ValueError("entity references an unknown faction")
        for formation in self.formations:
            if formation.entity_template.faction_id not in known:
                raise ValueError("formation entity template references an unknown faction")
        aggregates = {
            "entity": tuple(item.id for item in self.entities),
            "formation": tuple(item.id for item in self.formations),
            "event": tuple(item.id for item in self.events),
            "mission rule": tuple(item.id for item in self.mission_rules),
            "score metric": tuple(item.id for item in self.score_metrics),
        }
        for label, identifiers in aggregates.items():
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"duplicate {label} id")
        controller_slots = tuple(
            item.controller_slot for item in self.entities if item.controller_slot is not None
        )
        expanded_entity_ids = list(item.id for item in self.entities)
        expanded_controller_slots = list(controller_slots)
        for formation in self.formations:
            expanded_entity_ids.extend(
                formation.id_pattern.format(index=index) for index in range(formation.count)
            )
            if formation.entity_template.controller_slot is not None:
                expanded_controller_slots.extend(
                    formation.entity_template.controller_slot for _index in range(formation.count)
                )
        if len(expanded_entity_ids) != len(set(expanded_entity_ids)):
            raise ValueError("duplicate or overlapping expanded entity id")
        if len(expanded_controller_slots) != len(set(expanded_controller_slots)):
            raise ValueError("controller slot conflict")
        return self


class ObservationV2(CoreModelV2):
    session_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    observer_faction_id: str = Field(min_length=1)
    # This is a data-scope declaration, not an authentication principal. S6
    # owns identity and unforgeable authorization.
    controller_slot_id: str | None = Field(default=None, min_length=1)
    controlled_entity_ids: tuple[str, ...] = ()
    own_entities: tuple[dict[str, Any], ...] = ()
    organic_contacts: tuple[dict[str, Any], ...] = ()
    shared_contacts: tuple[dict[str, Any], ...] = ()
    received_messages: tuple[dict[str, Any], ...] = ()
    contacts_by_faction: dict[str, tuple[dict[str, Any], ...]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualizationFrameV2(CoreModelV2):
    session_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    view: Literal["referee", "faction", "public"]
    view_faction_id: str | None = None
    entities: tuple[dict[str, Any], ...] = ()
    contacts_by_faction: dict[str, tuple[dict[str, Any], ...]] = Field(default_factory=dict)
    scores_by_faction: dict[str, dict[str, Any]] = Field(default_factory=dict)
    sim_time_s: float = Field(default=0.0, ge=0.0)
    map_identity: dict[str, Any] = Field(default_factory=dict)
    world_bounds_m: tuple[float, float, float, float] | None = None
    static_polygons: tuple[tuple[tuple[float, float], ...], ...] = ()
    static_lines: tuple[tuple[tuple[float, float], ...], ...] = ()
    zones: tuple[dict[str, Any], ...] = ()
    sensor_coverage: tuple[dict[str, Any], ...] = ()
    weapon_coverage: tuple[dict[str, Any], ...] = ()
    communication_links: tuple[dict[str, Any], ...] = ()
    targeting_links: tuple[dict[str, Any], ...] = ()
    events: tuple[dict[str, Any], ...] = ()
    environment: dict[str, Any] = Field(default_factory=dict)
    mission: dict[str, Any] = Field(default_factory=dict)
    annotations: tuple[dict[str, Any], ...] = ()


__all__ = [
    "ConditionV2",
    "CoreScenarioV2",
    "EntitySpecV2",
    "EventSpecV2",
    "FactionV2",
    "FormationSpecV2",
    "InitialStateV2",
    "MissionRuleV2",
    "MissionSelectorV2",
    "ObservationV2",
    "RelationshipV2",
    "RoePolicyV2",
    "ScoreMetricV2",
    "SpatialDamagePolicyV2",
    "VisualizationFrameV2",
    "WorldSpecV2",
    "ZoneV2",
]

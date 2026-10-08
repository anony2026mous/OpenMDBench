"""Unified world entities and lifecycle registry."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Side(StrEnum):
    BLUE = "blue"
    RED = "red"
    NEUTRAL = "neutral"


class Domain(StrEnum):
    AIR = "air"
    SURFACE = "surface"
    SHORE = "shore"
    UNDERWATER = "underwater"


class Lifecycle(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    CRASHED = "crashed"
    DRIFTING = "drifting"
    DESTROYED = "destroyed"
    BREACHED_ACTIVE = "breached_active"
    IMPACTED = "impacted"
    OUT_OF_BOUNDS = "out_of_bounds"
    REMOVED = "removed"


class ComponentState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    health: float = Field(default=1.0, ge=0.0, le=1.0)
    energy: float = Field(default=1.0, ge=0.0, le=1.0)
    sensor_mode: str = "off"
    communication_status: str = "connected"
    sensor_operational: bool = True
    communication_operational: bool = True
    propulsion_operational: bool = True
    weapons_operational: bool = True
    weapon_inventory: dict[str, int] = Field(default_factory=dict)
    current_command: dict[str, Any] | None = None

    @field_validator("weapon_inventory")
    @classmethod
    def validate_inventory(cls, inventory: dict[str, int]) -> dict[str, int]:
        if any(count < 0 for count in inventory.values()):
            raise ValueError("weapon inventory cannot be negative")
        return inventory


class WorldEntity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_kind: str
    id: str = Field(min_length=1)
    side: Side
    domain: Domain
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    heading_deg: float = Field(default=0.0, ge=0.0, lt=360.0)
    lifecycle: Lifecycle = Lifecycle.ACTIVE


class PlatformAsset(WorldEntity):
    entity_kind: Literal["platform"] = "platform"
    platform_type: Literal["uav", "usv", "shore_radar", "auv"]
    components: ComponentState = Field(default_factory=ComponentState)
    home_id: str | None = None


class StaticFeature(WorldEntity):
    entity_kind: Literal["static_feature"] = "static_feature"
    feature_type: str


class DynamicObstacle(WorldEntity):
    entity_kind: Literal["dynamic_obstacle"] = "dynamic_obstacle"
    obstacle_type: str


class MissionObject(WorldEntity):
    entity_kind: Literal["mission_object"] = "mission_object"
    mission_role: str


Entity = PlatformAsset | StaticFeature | DynamicObstacle | MissionObject


class EntityRegistry:
    """Own entities while permanently reserving every ID used in the session."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._used_ids: set[str] = set()

    def register(self, entity: Entity) -> None:
        if entity.id in self._used_ids:
            raise ValueError(f"entity ID cannot be reused in a session: {entity.id}")
        self._used_ids.add(entity.id)
        self._entities[entity.id] = entity

    def get(self, entity_id: str) -> Entity:
        return self._entities[entity_id]

    def update(self, entity: Entity) -> None:
        """Replace a registered entity without permitting identity reuse."""
        if entity.id not in self._entities:
            raise KeyError(f"cannot update unregistered entity: {entity.id}")
        self._entities[entity.id] = entity

    def destroy(self, entity_id: str) -> Entity:
        entity = self.get(entity_id)
        destroyed = entity.model_copy(update={"lifecycle": Lifecycle.DESTROYED})
        self._entities[entity_id] = destroyed
        return destroyed

    def active_entities(self) -> tuple[Entity, ...]:
        return tuple(
            entity for entity in self._entities.values() if entity.lifecycle is Lifecycle.ACTIVE
        )

    def all_entities(self) -> tuple[Entity, ...]:
        """Return active and terminal records in stable registration order."""
        return tuple(self._entities.values())

"""Versioned public observation and action DTOs for MD-AD-002."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PublicDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NavigationAction(PublicDTO):
    mode: Literal["move_to", "patrol", "hold_position", "guard", "active_search"]
    target_m: tuple[float, float, float] | None = None
    speed_mps: float = Field(default=0.0, ge=0.0, le=80.0, allow_inf_nan=False)

    @field_validator("target_m")
    @classmethod
    def finite_target(
        cls, target: tuple[float, float, float] | None
    ) -> tuple[float, float, float] | None:
        if target is not None and not all(math.isfinite(value) for value in target):
            raise ValueError("navigation target_m must contain finite values")
        if target is not None and not 0.0 <= target[2] <= 3_000.0:
            raise ValueError("navigation target altitude must be within [0,3000] metres")
        return target

    @model_validator(mode="after")
    def target_required_for_motion(self) -> NavigationAction:
        if self.mode in {"move_to", "patrol", "guard"} and self.target_m is None:
            raise ValueError("navigation target_m is required for motion modes")
        return self


class SensorAction(PublicDTO):
    mode: Literal["off", "passive", "active_search"]


class CommunicationAction(PublicDTO):
    relay_enabled: bool = False


class EngagementAction(PublicDTO):
    contact_id: str = Field(min_length=1)
    weapon_id: Literal["uav_interceptor_missile", "shore_ciws"]
    count: Literal[1] = 1


class RedPlatformAction(PublicDTO):
    entity_id: str = Field(min_length=1)
    navigation: NavigationAction
    sensor: SensorAction | None = None
    communication: CommunicationAction | None = None
    engagement: EngagementAction | None = None
    ciws_auto: bool | None = None


class RedActionBatch(PublicDTO):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: Literal["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"]
    timestamp: int = Field(ge=0)
    actions: tuple[RedPlatformAction, ...] = Field(max_length=7)
    high_level_intent: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_entities(self) -> RedActionBatch:
        ids = [action.entity_id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate entity action")
        return self


class RedOwnForce(PublicDTO):
    entity_id: str
    platform_type: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    heading_deg: float
    health: float
    energy: float
    operational_status: str = "active"
    sensor_mode: str
    communication_status: str
    weapons: dict[str, int]
    current_command: dict[str, Any] | None = None


class RedContact(PublicDTO):
    contact_id: str
    estimated_domain: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    estimated_type: str
    confidence: float
    uncertainty_m: float
    age: int
    sources: tuple[str, ...]
    last_update: int | None


class RedObservation(PublicDTO):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: Literal["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"]
    timestamp: int
    own_forces: tuple[RedOwnForce, ...]
    contacts: tuple[RedContact, ...]
    environment: dict[str, str | int | float | bool | None]
    mission_status: dict[str, str | int | float | bool | None]
    visible_events: tuple[dict[str, str | int | float | bool | None], ...] = ()
    action_deadline_ms: int = 5_000

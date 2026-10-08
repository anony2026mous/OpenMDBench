"""Immutable public observation contract."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.core.entities import Domain


class PublicModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_numbers_only(self) -> PublicModel:
        def check(value: object) -> None:
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("all numeric values must be finite")
            if isinstance(value, BaseModel):
                for item in value.__dict__.values():
                    check(item)
            elif isinstance(value, Mapping):
                for item in value.values():
                    check(item)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                for item in value:
                    check(item)

        for value in self.__dict__.values():
            check(value)
        return self


class FriendlyAsset(PublicModel):
    id: str
    type: str
    domain: Domain
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    heading: float = Field(ge=0.0, lt=360.0)
    health: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    sensor_mode: str
    weapon_count: int = Field(ge=0)
    comm_status: str


class DetectedContact(PublicModel):
    id: str
    type: str = "unknown"
    estimated_domain: Domain
    position: tuple[float, float, float]
    position_uncertainty: float = Field(ge=0.0)
    velocity: tuple[float, float, float]
    confidence: float = Field(ge=0.0, le=1.0)
    first_detected_time: int = Field(ge=0)
    detected_by: tuple[str, ...]
    message_sent_time: int | None = Field(default=None, ge=0)
    message_source: str | None = None
    last_update_time: int | None = Field(default=None, ge=0)
    age: int = Field(default=0, ge=0)


class EnvironmentObservation(PublicModel):
    weather: str
    weather_trend: str
    sea_state: int = Field(ge=0)
    visibility_km: float = Field(ge=0.0)
    wind_speed: float = Field(ge=0.0)
    wind_direction: float = Field(ge=0.0, lt=360.0)


class SituationalData(PublicModel):
    friendly_assets: tuple[FriendlyAsset, ...]
    detected_contacts: tuple[DetectedContact, ...]
    environment: EnvironmentObservation


class Observation(PublicModel):
    schema_version: Literal["1.0"] = "1.0"
    session_id: str
    scenario_id: str = "legacy"
    timestamp: int = Field(ge=0)
    sim_time_s: float = Field(default=0.0, ge=0.0)
    state_version: int = Field(default=0, ge=0)
    view: Literal["red", "blue", "public"] = "public"
    mission_briefing: str
    situational_data: SituationalData
    event_log: tuple[dict[str, str | int | float | bool | None], ...] = ()
    time_remaining: int = Field(ge=0)
    mission_status: str
    action_masks: dict[str, Any] = Field(default_factory=dict)
    last_applied_command: str | None = None

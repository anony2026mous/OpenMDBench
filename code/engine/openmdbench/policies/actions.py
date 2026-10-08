"""Strict action batch shared by built-in and external rule agents."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.schemas.md_ad_002_interface import RedActionBatch, RedPlatformAction
from openmdbench.schemas.observation import Observation


class PlatformAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(min_length=1)
    navigation: Literal["move_to", "patrol", "hold_position", "guard", "active_search"]
    target: tuple[float, float, float] | None = None
    speed_mps: float = Field(default=0.0, ge=0.0)
    engage_contact_id: str | None = None
    weapon_id: str | None = None
    count: int = Field(default=1, ge=1)
    ram_target_id: str | None = None

    @model_validator(mode="after")
    def valid_ramming_intent(self) -> PlatformAction:
        if self.ram_target_id is None:
            return self
        if self.ram_target_id == self.entity_id:
            raise ValueError("ram target must differ from the acting entity")
        if self.navigation != "move_to" or self.target is None or self.speed_mps <= 0.0:
            raise ValueError("ramming requires a positive-speed move_to target")
        return self


class ActionBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: int = Field(ge=0)
    actions: tuple[PlatformAction, ...]
    high_level_intent: dict[str, Any] = Field(default_factory=dict)


class RuleAgent(Protocol):
    def reset(self, observation: Observation, seed: int) -> None: ...

    def act(self, observation: Observation) -> ActionBatch: ...


__all__ = [
    "ActionBatch",
    "PlatformAction",
    "RedActionBatch",
    "RedPlatformAction",
    "RuleAgent",
]

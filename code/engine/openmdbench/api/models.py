"""JSON request models for the public API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.schemas.md_ad_002_interface import RedActionBatch


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSessionRequest(ApiModel):
    scenario_id: str = Field(pattern=r"^MD-(REC|TRK|INT|AD|ER)-\d{3}(?:-(?:EASY|MEDIUM|HARD))?$")
    seed: int = 0


class ActionRequest(ApiModel):
    timestamp: int = Field(ge=0)
    action: tuple[float, float] | None = None
    action_batch: RedActionBatch | None = None

    @model_validator(mode="after")
    def exactly_one_action_form(self) -> ActionRequest:
        if (self.action is None) == (self.action_batch is None):
            raise ValueError("provide exactly one of action or action_batch")
        if self.action_batch is not None and self.timestamp != self.action_batch.timestamp:
            raise ValueError("request and action batch timestamps differ")
        return self


class RestoreRequest(ApiModel):
    checkpoint: dict[str, object]


class ErrorResponse(ApiModel):
    code: str
    message: str
    details: object | None = None
    request_id: str

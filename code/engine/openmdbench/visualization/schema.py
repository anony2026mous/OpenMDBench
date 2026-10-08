"""Versioned, renderer-independent visualization and replay contracts."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from openmdbench.core.entities import Domain, Lifecycle, Side


class VisualizationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_numbers_only(self) -> VisualizationModel:
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


class ReplayMetadata(VisualizationModel):
    record_type: Literal["metadata"] = "metadata"
    schema_version: Literal["1.0"] = "1.0"
    match_id: str = Field(min_length=1)
    scenario_id: str = Field(pattern=r"^MD-(REC|TRK|INT|AD|ER)-\d{3}(?:-(?:EASY|MEDIUM|HARD))?$")
    seed: int = Field(ge=0)
    tick_seconds: float = Field(gt=0.0)
    coordinate_system: Literal["local_enu", "wgs84"]
    engine_version: str = Field(min_length=1)
    config_hash: str = Field(pattern=r"^sha256:[0-9a-f]{3,64}$")
    resolved_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    schema_versions: dict[str, str] = Field(default_factory=lambda: {"replay": "1.0"})
    map_identity: dict[str, Any] | None = None
    dynamics_metadata: dict[str, Any] | None = None


class VisualizationEntity(VisualizationModel):
    id: str = Field(min_length=1)
    side: Side
    type: str = Field(min_length=1)
    domain: Domain
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    heading: float = Field(ge=0.0, lt=360.0)
    health: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    sensor_mode: str
    comm_status: str
    status: Lifecycle
    visual_profile: str = Field(min_length=1)
    weapon_inventory: dict[str, int] = Field(default_factory=dict)
    position_wgs84: tuple[float, float, float] | None = None


class VisualizationDetection(VisualizationModel):
    id: str = Field(min_length=1)
    estimated_domain: Domain
    position: tuple[float, float, float]
    position_uncertainty: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    message_sent_time: int | None = Field(default=None, ge=0)
    message_source: str | None = None


class DetectionSets(VisualizationModel):
    blue: tuple[VisualizationDetection, ...] = ()
    red: tuple[VisualizationDetection, ...] = ()


class VisualizationEvent(VisualizationModel):
    event_type: str = Field(min_length=1)
    entity_id: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class SideScore(VisualizationModel):
    total: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, float | None] = Field(default_factory=dict)


class ScoreSets(VisualizationModel):
    blue: SideScore
    red: SideScore


class EnvironmentPanel(VisualizationModel):
    weather: str = "unknown"
    sea_state: int | None = Field(default=None, ge=0)
    visibility_km: float | None = Field(default=None, ge=0.0)


class MissionPanel(VisualizationModel):
    status: str = "unknown"
    objective: str = ""
    time_remaining: int | None = Field(default=None, ge=0)


class VisualizationFrame(VisualizationModel):
    record_type: Literal["frame"] = "frame"
    schema_version: Literal["1.0"] = "1.0"
    session_id: str = "legacy"
    scenario_id: str = "legacy"
    timestamp: int = Field(ge=0)
    sim_time_s: float = Field(default=0.0, ge=0.0)
    view: Literal["referee", "red", "blue", "public"] = "referee"
    map_identity: dict[str, Any] | None = None
    actions: tuple[dict[str, Any], ...] = ()
    entities: tuple[VisualizationEntity, ...]
    detections: DetectionSets
    events: tuple[VisualizationEvent, ...] = ()
    scores: ScoreSets
    environment: EnvironmentPanel = Field(default_factory=EnvironmentPanel)
    mission: MissionPanel = Field(default_factory=MissionPanel)
    zones: tuple[dict[str, Any], ...] = ()
    sensor_coverage: tuple[dict[str, Any], ...] = ()
    communication_links: tuple[dict[str, Any], ...] = ()
    weapon_events: tuple[VisualizationEvent, ...] = ()
    mission_events: tuple[VisualizationEvent, ...] = ()
    annotations: tuple[dict[str, Any], ...] = ()


ReplayRecord = Annotated[ReplayMetadata | VisualizationFrame, Field(discriminator="record_type")]
REPLAY_RECORD_ADAPTER: TypeAdapter[ReplayRecord] = TypeAdapter(ReplayRecord)


def replay_json_schema() -> dict[str, Any]:
    """Return the authoritative JSON Schema for metadata and frame records."""
    return REPLAY_RECORD_ADAPTER.json_schema()

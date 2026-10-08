"""Canonical versioned platform DTOs frozen by RF-01."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from openmdbench.schemas.observation import Observation as LegacyObservation

SchemaVersion = Literal["1.0"]
Visibility = Literal["referee", "red", "blue", "public"]
HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$"
SCENARIO_PATTERN = r"^MD-(REC|TRK|INT|AD|ER)-\d{3}(?:-(?:EASY|MEDIUM|HARD))?$"


def _reject_nonfinite(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("all numeric values must be finite")
    if isinstance(value, BaseModel):
        for item in value.__dict__.values():
            _reject_nonfinite(item)
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_nonfinite(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _reject_nonfinite(item)


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}
    return value


class VersionedModel(BaseModel):
    """Immutable strict base with recursive finite-number enforcement."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    schema_version: SchemaVersion

    @model_validator(mode="after")
    def finite_numbers_only(self) -> VersionedModel:
        for value in self.__dict__.values():
            _reject_nonfinite(value)
        return self


class Observation(LegacyObservation):
    """Canonical observation input; legacy producers may still default the version."""

    schema_version: SchemaVersion


class ResourceType(StrEnum):
    MAPS = "maps"
    PLATFORMS = "platforms"
    DYNAMICS = "dynamics"
    LOADOUTS = "loadouts"
    SENSORS = "sensors"
    WEAPONS = "weapons"
    EFFECTS = "effects"
    COMMUNICATIONS = "communications"
    ENERGY = "energy"
    ENVIRONMENTS = "environments"
    MISSIONS = "missions"
    SCORING = "scoring"
    VISUALIZATION_ASSETS = "visualization_assets"
    TRUSTED_MODEL_PLUGINS = "trusted_model_plugins"


class RunnerMode(StrEnum):
    CONTINUOUS = "continuous"
    LOCKSTEP = "lockstep"
    REPLAY = "replay"


class SessionStatus(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATING = "terminating"
    COMPLETED = "completed"
    CLOSED = "closed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ReceiptStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    APPLIED = "applied"
    EXECUTED = "executed"
    REJECTED = "rejected"


class CommandStatus(StrEnum):
    QUEUED = "queued"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    APPLIED = "applied"
    EXECUTED = "executed"
    COMPLETED = "completed"
    REPLACED = "replaced"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REJECTED = "rejected"


class StableErrorCode(StrEnum):
    SCHEMA_INVALID = "schema.invalid"
    RESOURCE_NOT_FOUND = "resource.not_found"
    RESOURCE_VERSION_CONFLICT = "resource.version_conflict"
    SCENARIO_COMPILE_FAILED = "scenario.compile_failed"
    SESSION_INVALID_STATE = "session.invalid_state"
    SESSION_NOT_FOUND = "session.not_found"
    ACTION_INVALID = "action.invalid"
    ACTION_STALE = "action.stale"
    ACTION_DUPLICATE = "action.duplicate"
    ACTION_UNAUTHORIZED = "action.unauthorized"
    COMMAND_EXPIRED = "command.expired"
    COMMAND_REJECTED = "command.rejected"
    CHECKPOINT_INCOMPATIBLE = "checkpoint.incompatible"
    REPLAY_INCOMPATIBLE = "replay.incompatible"
    INTERNAL_ERROR = "internal.error"


class CatalogResourceRef(VersionedModel):
    resource_type: ResourceType
    resource_id: str = Field(min_length=1)
    version: str = Field(pattern=SEMVER_PATTERN)
    content_hash: str = Field(pattern=HASH_PATTERN)


class ScenarioPackageMetadata(VersionedModel):
    package_id: str = Field(min_length=1)
    version: str = Field(pattern=SEMVER_PATTERN)
    package_hash: str = Field(pattern=HASH_PATTERN)
    entrypoint: str = "scenario.yaml"
    resources: tuple[CatalogResourceRef, ...] = ()


class ResolvedScenarioMetadata(VersionedModel):
    scenario_id: str = Field(pattern=SCENARIO_PATTERN)
    scenario_version: str = Field(pattern=SEMVER_PATTERN)
    package_hash: str = Field(pattern=HASH_PATTERN)
    resolved_hash: str = Field(pattern=HASH_PATTERN)
    resource_hashes: tuple[str, ...] = Field(default=())
    map_hash: str | None = Field(default=None, pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def valid_resource_hashes(self) -> ResolvedScenarioMetadata:
        import re

        if any(re.fullmatch(HASH_PATTERN, value) is None for value in self.resource_hashes):
            raise ValueError("resource_hashes must contain sha256 hashes")
        return self


class SessionConfig(VersionedModel):
    resolved_scenario: ResolvedScenarioMetadata
    seed: int = Field(ge=0)
    runner_mode: RunnerMode
    physics_dt_s: float = Field(gt=0.0)
    decision_interval_ticks: int = Field(ge=1)
    speed_ratio: float = Field(gt=0.0)
    wall_clock_timeout_s: float | None = Field(default=None, gt=0.0)


class SessionState(VersionedModel):
    session_id: str = Field(min_length=1)
    scenario_id: str = Field(pattern=SCENARIO_PATTERN)
    status: SessionStatus
    runner_mode: RunnerMode
    tick: int = Field(ge=0)
    sim_time_s: float = Field(ge=0.0)
    state_version: int = Field(ge=0)


class SessionResult(VersionedModel):
    session_id: str = Field(min_length=1)
    scenario_id: str = Field(pattern=SCENARIO_PATTERN)
    outcome: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    terminal_tick: int = Field(ge=0)
    sim_time_s: float = Field(ge=0.0)
    scores: dict[str, float | None] = Field(default_factory=dict)


class TickBoundModel(VersionedModel):
    entity_id: str = Field(min_length=1)
    based_on_tick: int = Field(ge=0)
    valid_until_tick: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload", mode="before")
    @classmethod
    def json_stable_payload(cls, value: Any) -> Any:
        return _normalize_json_value(value)

    @model_validator(mode="after")
    def valid_tick_window(self) -> TickBoundModel:
        if self.valid_until_tick < self.based_on_tick:
            raise ValueError("valid_until_tick must be >= based_on_tick")
        return self


class PersistentCommand(TickBoundModel):
    command_id: str = Field(min_length=1)
    command_type: Literal[
        "navigation",
        "patrol",
        "hold",
        "sensor_mode",
        "relay_mode",
        "ciws_auto",
    ]


class DiscreteAction(TickBoundModel):
    action_id: str = Field(min_length=1)
    action_type: Literal["fire_weapon", "release_payload", "send_message", "device_action", "ram"]


class ActionBatch(VersionedModel):
    session_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    based_on_tick: int = Field(ge=0)
    valid_until_tick: int = Field(ge=0)
    persistent_commands: tuple[PersistentCommand, ...] = ()
    discrete_actions: tuple[DiscreteAction, ...] = ()
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("extensions", mode="before")
    @classmethod
    def json_stable_extensions(cls, value: Any) -> Any:
        return _normalize_json_value(value)

    @model_validator(mode="after")
    def valid_batch(self) -> ActionBatch:
        if self.valid_until_tick < self.based_on_tick:
            raise ValueError("valid_until_tick must be >= based_on_tick")
        ids = [item.command_id for item in self.persistent_commands]
        ids.extend(item.action_id for item in self.discrete_actions)
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate command/action ID")
        if any(
            item.based_on_tick < self.based_on_tick or item.valid_until_tick > self.valid_until_tick
            for item in (*self.persistent_commands, *self.discrete_actions)
        ):
            raise ValueError("child command validity must fit within the batch validity window")
        return self


class ActionReceipt(VersionedModel):
    session_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    status: ReceiptStatus
    received_at_tick: int = Field(ge=0)
    scheduled_for_tick: int | None = Field(default=None, ge=0)
    error_code: StableErrorCode | None = None


class CommandResult(VersionedModel):
    session_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1)
    status: CommandStatus
    applied_tick: int | None = Field(default=None, ge=0)
    completed_tick: int | None = Field(default=None, ge=0)
    error_code: StableErrorCode | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Event(VersionedModel):
    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    sim_time_s: float = Field(ge=0.0)
    event_type: str = Field(min_length=1)
    visibility: tuple[Visibility, ...]
    entity_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class EventPage(VersionedModel):
    session_id: str = Field(min_length=1)
    events: tuple[Event, ...]
    next_cursor: str | None = None


class CheckpointMetadata(VersionedModel):
    checkpoint_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    resolved_hash: str = Field(pattern=HASH_PATTERN)
    state_hash: str = Field(pattern=HASH_PATTERN)
    engine_version: str = "0.1.0"


class StableError(VersionedModel):
    code: StableErrorCode
    message: str = Field(min_length=1)
    field_path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    suggestion: str | None = None


class _PlatformSchemaBundle(BaseModel):
    catalog_resource_ref: CatalogResourceRef | None = None
    scenario_package_metadata: ScenarioPackageMetadata | None = None
    resolved_scenario_metadata: ResolvedScenarioMetadata | None = None
    session_config: SessionConfig | None = None
    session_state: SessionState | None = None
    session_result: SessionResult | None = None
    action_batch: ActionBatch | None = None
    persistent_command: PersistentCommand | None = None
    discrete_action: DiscreteAction | None = None
    action_receipt: ActionReceipt | None = None
    command_result: CommandResult | None = None
    event: Event | None = None
    event_page: EventPage | None = None
    checkpoint_metadata: CheckpointMetadata | None = None
    stable_error: StableError | None = None
    observation: Observation | None = None


def platform_json_schema() -> dict[str, Any]:
    """Return one JSON Schema bundle containing every canonical 1.0 DTO."""
    # Import lazily: visualization's live renderer depends on core.world, while
    # core.world imports public observation DTOs during module initialization.
    from openmdbench.visualization.schema import replay_json_schema

    schema = _PlatformSchemaBundle.model_json_schema()
    replay_schema = replay_json_schema()
    schema.setdefault("$defs", {}).update(replay_schema.get("$defs", {}))
    for name in ("ReplayMetadata", "VisualizationFrame"):
        definition = schema["$defs"].get(name)
        if definition is not None:
            required = definition.setdefault("required", [])
            if "schema_version" not in required:
                required.append("schema_version")
    return schema


__all__ = [
    "ActionBatch",
    "ActionReceipt",
    "CatalogResourceRef",
    "CheckpointMetadata",
    "CommandResult",
    "CommandStatus",
    "DiscreteAction",
    "Event",
    "EventPage",
    "Observation",
    "PersistentCommand",
    "ReceiptStatus",
    "ResolvedScenarioMetadata",
    "ResourceType",
    "RunnerMode",
    "ScenarioPackageMetadata",
    "SessionConfig",
    "SessionResult",
    "SessionState",
    "SessionStatus",
    "StableError",
    "StableErrorCode",
    "VersionedModel",
    "platform_json_schema",
]

"""Scenario-independent action, event, replay, checkpoint, and error DTOs."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from openmdbench.schemas.core_v2 import CoreModelV2

HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _TickBoundV2(CoreModelV2):
    entity_id: str = Field(min_length=1)
    faction_id: str = Field(min_length=1)
    based_on_tick: int = Field(ge=0)
    valid_until_tick: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tick_window(self) -> Self:
        if self.valid_until_tick < self.based_on_tick:
            raise ValueError("valid_until_tick must be at or after based_on_tick")
        return self


class PersistentCommandV2(_TickBoundV2):
    command_id: str = Field(min_length=1)
    command_type: Literal["navigation", "patrol", "hold", "sensor_mode", "relay_mode", "ciws_auto"]


class DiscreteActionV2(_TickBoundV2):
    action_id: str = Field(min_length=1)
    action_type: Literal["fire_weapon", "release_payload", "send_message", "device_action", "ram"]


class ActionBatchV2(CoreModelV2):
    session_id: str = Field(min_length=1)
    batch_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    faction_id: str = Field(min_length=1)
    based_on_tick: int = Field(ge=0)
    valid_until_tick: int = Field(ge=0)
    persistent_commands: tuple[PersistentCommandV2, ...] = ()
    discrete_actions: tuple[DiscreteActionV2, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        if self.valid_until_tick < self.based_on_tick:
            raise ValueError("valid_until_tick must be at or after based_on_tick")
        identifiers = tuple(item.command_id for item in self.persistent_commands) + tuple(
            item.action_id for item in self.discrete_actions
        )
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate command or action id")
        children = (*self.persistent_commands, *self.discrete_actions)
        if any(item.faction_id != self.faction_id for item in children):
            raise ValueError("child command faction must match batch faction")
        if any(
            item.based_on_tick < self.based_on_tick or item.valid_until_tick > self.valid_until_tick
            for item in children
        ):
            raise ValueError("child command tick window must fit within its batch")
        return self


class AuthorityEventV2(CoreModelV2):
    event_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    sim_time_s: float = Field(ge=0.0)
    event_type: str = Field(min_length=1)
    faction_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_participant_ids(self) -> Self:
        if len(self.faction_ids) != len(set(self.faction_ids)):
            raise ValueError("duplicate faction id in authority event")
        if len(self.entity_ids) != len(set(self.entity_ids)):
            raise ValueError("duplicate entity id in authority event")
        return self


class _ReproducibilityMetadataV2(CoreModelV2):
    session_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    seed: int = Field(ge=0)
    resolved_hash: str = Field(pattern=HASH_PATTERN)
    catalog_hashes: dict[str, str] = Field(default_factory=dict)
    plugin_hashes: dict[str, str] = Field(default_factory=dict)
    map_hash: str = Field(pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def validate_hash_mappings(self) -> Self:
        import re

        hashes = (*self.catalog_hashes.values(), *self.plugin_hashes.values())
        if any(re.fullmatch(HASH_PATTERN, value) is None for value in hashes):
            raise ValueError("resource and plugin hashes must be sha256 values")
        return self


class ReplayMetadataV2(_ReproducibilityMetadataV2):
    pass


class CheckpointMetadataV2(_ReproducibilityMetadataV2):
    tick: int = Field(ge=0)
    checkpoint_hash: str = Field(pattern=HASH_PATTERN)
    rng_streams: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_rng_streams(self) -> Self:
        if len(self.rng_streams) != len(set(self.rng_streams)):
            raise ValueError("duplicate RNG stream id")
        return self


class StableErrorV2(CoreModelV2):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
    message: str = Field(min_length=1)
    path: tuple[str, ...] = ()
    value: Any = None
    suggestion: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ActionBatchV2",
    "AuthorityEventV2",
    "CheckpointMetadataV2",
    "DiscreteActionV2",
    "PersistentCommandV2",
    "ReplayMetadataV2",
    "StableErrorV2",
]

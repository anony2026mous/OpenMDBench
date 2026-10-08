"""Versioned minimal core checkpoint for M1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from openmdbench.core.entities import (
    DynamicObstacle,
    Entity,
    EntityRegistry,
    MissionObject,
    PlatformAsset,
    StaticFeature,
)
from openmdbench.core.rng import SessionRNG
from openmdbench.core.scheduling import EventQueue, SimulationClock


class CheckpointRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    config_hash: str
    clock: dict[str, Any]
    entities: tuple[dict[str, Any], ...]
    events: dict[str, Any]
    rng: dict[str, Any]
    task_state: dict[str, Any]


@dataclass(slots=True)
class RestoredCore:
    clock: SimulationClock
    registry: EntityRegistry
    events: EventQueue
    rng: SessionRNG
    task_state: dict[str, Any]


def create_checkpoint(
    *,
    config_hash: str,
    clock: SimulationClock,
    registry: EntityRegistry,
    events: EventQueue,
    rng: SessionRNG,
    task_state: dict[str, Any],
) -> str:
    record = CheckpointRecord(
        config_hash=config_hash,
        clock={"paused": clock.paused, "tick": clock.tick, "tick_seconds": clock.tick_seconds},
        entities=tuple(entity.model_dump(mode="json") for entity in registry.all_entities()),
        events=events.snapshot(),
        rng=rng.snapshot(),
        task_state=task_state,
    )
    return record.model_dump_json()


def _restore_entity(record: dict[str, Any]) -> Entity:
    kind = record.get("entity_kind")
    if kind == "dynamic_obstacle":
        return DynamicObstacle.model_validate(record)
    if kind == "mission_object":
        return MissionObject.model_validate(record)
    if kind == "platform":
        return PlatformAsset.model_validate(record)
    if kind == "static_feature":
        return StaticFeature.model_validate(record)
    raise ValueError(f"unknown checkpoint entity kind: {kind}")


def restore_checkpoint(payload: str, *, expected_config_hash: str) -> RestoredCore:
    raw = json.loads(payload)
    if raw.get("schema_version") != "1.0":
        raise ValueError(f"unsupported checkpoint schema version: {raw.get('schema_version')}")
    record = CheckpointRecord.model_validate(raw)
    if record.config_hash != expected_config_hash:
        raise ValueError("checkpoint configuration hash mismatch")
    registry = EntityRegistry()
    for entity_record in record.entities:
        registry.register(_restore_entity(entity_record))
    return RestoredCore(
        clock=SimulationClock(**record.clock),
        registry=registry,
        events=EventQueue.from_snapshot(record.events),
        rng=SessionRNG.from_snapshot(record.rng),
        task_state=record.task_state,
    )

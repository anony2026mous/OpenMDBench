"""Canonical immutable checkpoints for session-owned v2 runtime worlds."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_serializer, model_validator

from openmdbench.combat.models_v2 import PendingImpactReceiptV2, PendingImpactV2
from openmdbench.dynamics.native_v2 import (
    NativeDynamicsSnapshotV2,
    validate_native_dynamics_snapshot_v2,
)
from openmdbench.scenarios.declarative_v2 import ResolvedSpatialEffectPolicyV2
from openmdbench.world.missile_v2 import MissileFlightV2, MissileTerminalReceiptV2

_HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"


class CheckpointErrorV2(ValueError):
    """Stable checkpoint serialization or nested-integrity failure."""

    def __init__(self, reason: str) -> None:
        self.code = "checkpoint.integrity_invalid"
        self.path = ("checkpoint", "integrity")
        self.value = reason
        self.reason = reason
        self.suggestion = "restore an unmodified canonical checkpoint"
        super().__init__(f"{self.code}: {reason}; suggestion: {self.suggestion}")


class _FrozenDict(dict[str, Any]):
    @classmethod
    def from_mapping(cls, value: Mapping[object, Any]) -> _FrozenDict:
        result = cls()
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("checkpoint mapping keys must be strings")
            dict.__setitem__(result, key, _freeze(item))
        return result

    @staticmethod
    def _reject() -> Never:
        raise TypeError("checkpoint mappings are immutable")

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


def _freeze(value: Any) -> Any:
    if isinstance(value, _FrozenDict):
        return value
    if isinstance(value, Mapping):
        return _FrozenDict.from_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, BaseModel):
        return {str(key): _plain(item) for key, item in value.__dict__.items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _canonical_json(value: Any, *, allow_nan: bool) -> str:
    return json.dumps(
        _plain(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=allow_nan,
    )


class _CheckpointModelV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def deep_freeze(self) -> Self:
        for name, value in tuple(self.__dict__.items()):
            object.__setattr__(self, name, _freeze(value))
        return self


class CheckpointEntityV2(_CheckpointModelV2):
    id: str = Field(min_length=1, max_length=256)
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    heading_deg: float = Field(ge=0.0, lt=360.0)
    health: float = Field(ge=0.0)
    energy: float | None = Field(default=None, ge=0.0)
    ammunition: dict[str, StrictInt]
    component_states: dict[str, Any]
    lifecycle: Literal["active", "degraded", "disabled", "destroyed"]
    controller_state: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def reject_ambiguous_state(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            raise ValueError("checkpoint entity state must be an object")
        for field_name in ("health", "energy", "heading_deg"):
            candidate = value.get(field_name)
            if candidate is not None and (
                isinstance(candidate, bool)
                or not isinstance(candidate, (int, float))
                or not math.isfinite(float(candidate))
            ):
                raise ValueError(f"{field_name} must be a finite canonical number")
        for field_name in ("position_m", "velocity_mps"):
            vector = value.get(field_name)
            if (
                not isinstance(vector, (list, tuple))
                or len(vector) != 3
                or any(
                    isinstance(axis, bool)
                    or not isinstance(axis, (int, float))
                    or not math.isfinite(float(axis))
                    for axis in vector
                )
            ):
                raise ValueError(f"{field_name} must be a finite canonical three-vector")
        ammunition = value.get("ammunition")
        if not isinstance(ammunition, Mapping) or any(
            not isinstance(key, str)
            or not key
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for key, count in ammunition.items()
        ):
            raise ValueError("checkpoint ammunition must contain exact nonnegative integers")
        return value


class CheckpointLifecycleReceiptV2(_CheckpointModelV2):
    tick: int = Field(ge=0)
    operation_id: str = Field(min_length=1, max_length=256)
    status: Literal["committed", "committed_with_cleanup_errors"]
    applied_event_ids: tuple[str, ...]
    spawned_entity_ids: tuple[str, ...]
    despawned_entity_ids: tuple[str, ...]


class CheckpointTombstoneV2(_CheckpointModelV2):
    entity_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    source_event_id: str = Field(min_length=1)
    adapters_closed: bool
    cleanup_errors: tuple[str, ...]


class CheckpointSpatialClockV2(_CheckpointModelV2):
    tick: int = Field(ge=0)
    tick_start_time_seconds: float = Field(ge=0.0)
    next_tick_time_seconds: float = Field(ge=0.0)


class CheckpointZoneActivationReceiptV2(_CheckpointModelV2):
    operation_id: str = Field(min_length=1, max_length=256)
    zone_id: str = Field(min_length=1, max_length=256)
    active: bool
    tick: int = Field(ge=0)
    changed: bool


class CheckpointMotionReceiptV2(_CheckpointModelV2):
    tick: int = Field(ge=0)
    next_tick: int = Field(ge=0)
    operation_id: str = Field(min_length=1, max_length=256)
    dt_seconds: float = Field(gt=0.0)
    tick_start_time_seconds: float = Field(ge=0.0)
    candidate_entity_ids: tuple[str, ...]
    boundary_events: tuple[dict[str, Any], ...]
    collision_events: tuple[dict[str, Any], ...]
    damage_intents: tuple[dict[str, Any], ...]
    policy_actions: tuple[dict[str, Any], ...]
    fingerprint: str = Field(pattern=_HASH_PATTERN)


class CheckpointWorldTickReceiptV2(_CheckpointModelV2):
    operation_id: str = Field(min_length=1, max_length=256)
    fingerprint: str = Field(pattern=_HASH_PATTERN)
    start_tick: int = Field(ge=0)
    tick: int = Field(ge=0)
    steps: int = Field(ge=1)
    motion_operation_ids: tuple[str, ...]
    lifecycle_operation_ids: tuple[str, ...] = ()
    event_receipts: tuple[dict[str, Any], ...] = ()
    damage_receipts: tuple[dict[str, Any], ...] = ()
    provider_receipts: tuple[str, ...] = ()
    dynamics_receipts: tuple[dict[str, Any], ...] = ()
    mission_receipts: tuple[dict[str, Any], ...] = ()
    score_receipts: tuple[dict[str, Any], ...] = ()
    combat_receipts: tuple[dict[str, Any], ...] = ()
    subsystem_receipts: tuple[dict[str, Any], ...] = ()


class CheckpointCombatEngagementV2(_CheckpointModelV2):
    request_id: str = Field(min_length=1)
    request_fingerprint: str = Field(pattern=_HASH_PATTERN)
    operation_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    attacker_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    execution_hash: str = Field(pattern=_HASH_PATTERN)
    execution: dict[str, Any]


class CheckpointContactEvidenceV2(_CheckpointModelV2):
    schema_version: Literal["world-contact@2.0"] = "world-contact@2.0"
    evidence_id: str = Field(min_length=1, max_length=256)
    owner_entity_id: str = Field(min_length=1, max_length=256)
    target_entity_id: str = Field(min_length=1, max_length=256)
    observed_tick: StrictInt = Field(ge=0)
    age_ticks: StrictInt = Field(ge=0)
    max_age_ticks: StrictInt = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    minimum_confidence: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    measurement_position_m: tuple[float, float, float] | None = None
    confirmation_count: StrictInt = Field(default=1, ge=1)
    confirmation_frames: StrictInt = Field(default=1, ge=1)
    stale_after_ticks: StrictInt = Field(default=1, ge=1)
    confirmed: bool = True
    source_sensor_ref: str | None = Field(default=None, min_length=1, max_length=256)


class CheckpointRoeRuleV2(_CheckpointModelV2):
    schema_version: Literal["world-roe@2.0"] = "world-roe@2.0"
    rule_id: str = Field(min_length=1, max_length=256)
    source_faction_id: str = Field(min_length=1, max_length=256)
    target_faction_id: str = Field(min_length=1, max_length=256)
    relationship: str = Field(min_length=1, max_length=256)
    engagement_permitted: bool


class CheckpointHitModelStateV2(_CheckpointModelV2):
    schema_version: Literal["hit-model-state@2.0"] = "hit-model-state@2.0"
    model_ref: str = Field(min_length=1, max_length=256)
    model_identity: str = Field(pattern=_HASH_PATTERN)
    call_count: StrictInt = Field(ge=0)


@dataclass(frozen=True, slots=True)
class WorldEventStateSnapshotV2:
    """Deep-frozen state owned by the typed World event dispatcher."""

    weather_state: Mapping[str, Any] = field(default_factory=dict)
    jamming_sessions: Mapping[str, Any] = field(default_factory=dict)
    message_queue: tuple[Mapping[str, Any], ...] = ()
    shared_contact_queue: tuple[Mapping[str, Any], ...] = ()
    shared_contacts_by_controller: Mapping[str, Any] = field(default_factory=dict)
    command_queue: tuple[Mapping[str, Any], ...] = ()
    controller_inboxes: Mapping[str, Any] = field(default_factory=dict)
    inbox_evictions: tuple[Mapping[str, Any], ...] = ()
    component_suppressions: Mapping[str, Any] = field(default_factory=dict)
    mission_marker_ledger: Mapping[str, Any] = field(default_factory=dict)
    zone_activation_state: Mapping[str, bool] = field(default_factory=dict)
    effect_application_ledger: Mapping[str, Any] = field(default_factory=dict)
    spatial_effect_triggers: Mapping[str, Any] = field(default_factory=dict)
    spatial_effect_trigger_ledger: Mapping[str, Any] = field(default_factory=dict)
    spatial_effect_trigger_consumption: Mapping[str, Any] = field(default_factory=dict)
    destroyed_lifecycle_ledger: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for item in fields(self):
            object.__setattr__(self, item.name, _freeze(getattr(self, item.name)))


class WorldCheckpointV2(_CheckpointModelV2):
    schema_version: Literal["world-checkpoint@2.0"] = "world-checkpoint@2.0"
    resolved_hash: str = Field(pattern=_HASH_PATTERN)
    catalog_hash: str = Field(pattern=_HASH_PATTERN)
    model_registry_hash: str = Field(pattern=_HASH_PATTERN)
    session_id: str = Field(min_length=1, max_length=256)
    seed: StrictInt
    tick: int = Field(ge=0)
    entities: tuple[CheckpointEntityV2, ...]
    used_entity_ids: tuple[str, ...]
    schedule_cursor: int = Field(ge=0)
    applied_lifecycle_event_ids: tuple[str, ...]
    lifecycle_ledger: tuple[CheckpointLifecycleReceiptV2, ...]
    controller_ownership: dict[str, Any]
    rng_state: tuple[Any, ...]
    native_adapter_snapshots: tuple[NativeDynamicsSnapshotV2, ...]
    tombstones: tuple[CheckpointTombstoneV2, ...]
    spatial_clock: CheckpointSpatialClockV2 = CheckpointSpatialClockV2(
        tick=0, tick_start_time_seconds=0.0, next_tick_time_seconds=0.0
    )
    boundary_topology_hash: str = Field(default="sha256:" + "0" * 64, pattern=_HASH_PATTERN)
    zone_activation_state: dict[str, bool] = Field(default_factory=dict)
    zone_activation_ledger: tuple[CheckpointZoneActivationReceiptV2, ...] = ()
    motion_ledger: tuple[CheckpointMotionReceiptV2, ...] = ()
    world_tick_ledger: tuple[CheckpointWorldTickReceiptV2, ...] = ()
    consumed_provider_receipts: tuple[str, ...] = ()
    combat_ledger: tuple[dict[str, Any], ...] = ()
    combat_rng_state: tuple[str, ...] = ()
    combat_ammunition: dict[str, StrictInt] = Field(default_factory=dict)
    combat_energy: dict[str, float] = Field(default_factory=dict)
    combat_component_health: dict[str, float] = Field(default_factory=dict)
    combat_cooldowns: dict[str, StrictInt] = Field(default_factory=dict)
    combat_engagement_ledger: tuple[CheckpointCombatEngagementV2, ...] = ()
    combat_profiles: tuple[dict[str, Any], ...] = ()
    combat_adapter_states: tuple[dict[str, Any], ...] = ()
    combat_contact_evidence: tuple[CheckpointContactEvidenceV2, ...] = ()
    combat_roe_rules: tuple[CheckpointRoeRuleV2, ...] = ()
    combat_hit_model_state: CheckpointHitModelStateV2 | None = None
    missile_flights: tuple[MissileFlightV2, ...] = ()
    missile_terminal_receipts: tuple[MissileTerminalReceiptV2, ...] = ()
    pending_impacts: tuple[PendingImpactV2, ...] = ()
    pending_impact_receipts: tuple[PendingImpactReceiptV2, ...] = ()
    world_adapter_snapshots: tuple[dict[str, Any], ...] = ()
    world_adapter_receipts: tuple[dict[str, Any], ...] = ()
    world_adapter_ledger: tuple[dict[str, Any], ...] = ()
    mission_scoring_checkpoint: dict[str, Any] | None = None
    mission_zone_membership: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    mission_zone_transitions: tuple[dict[str, Any], ...] = ()
    event_state: WorldEventStateSnapshotV2 = Field(default_factory=WorldEventStateSnapshotV2)
    spatial_effect_policy: ResolvedSpatialEffectPolicyV2 | None = None
    checkpoint_hash: str = Field(pattern=_HASH_PATTERN)

    @model_validator(mode="before")
    @classmethod
    def restore_resolved_policy_types(cls, value: Any) -> Any:
        if isinstance(value, Mapping) and isinstance(value.get("spatial_effect_policy"), Mapping):
            result = dict(value)
            result["spatial_effect_policy"] = ResolvedSpatialEffectPolicyV2.from_mapping(
                value["spatial_effect_policy"]
            )
            return result
        return value

    @field_serializer("event_state", "spatial_effect_policy")
    def serialize_frozen_event_evidence(self, value: Any) -> Any:
        return _plain(value)

    @staticmethod
    def compute_checkpoint_hash(checkpoint: WorldCheckpointV2 | Mapping[str, Any]) -> str:
        payload = (
            checkpoint.model_dump(mode="json")
            if isinstance(checkpoint, WorldCheckpointV2)
            else _plain(checkpoint)
        )
        payload = dict(payload)
        payload.pop("checkpoint_hash", None)
        encoded = _canonical_json(payload, allow_nan=True).encode()
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    @property
    def semantic_hash(self) -> str:
        payload = self.model_dump(mode="json")
        payload.pop("checkpoint_hash", None)
        for snapshot in payload["native_adapter_snapshots"]:
            snapshot.pop("instance_id", None)
            snapshot.pop("restored_from_instance_id", None)
            snapshot.pop("snapshot_hash", None)
        encoded = _canonical_json(payload, allow_nan=False).encode()
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    def validate_integrity(self) -> None:
        if self.checkpoint_hash != self.compute_checkpoint_hash(self):
            raise CheckpointErrorV2("checkpoint canonical hash mismatch")
        if self.mission_scoring_checkpoint is None:
            raise CheckpointErrorV2("checkpoint mission scoring state is absent")
        try:
            from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2

            mission_checkpoint = MissionScoringCheckpointV2.model_validate(
                self.mission_scoring_checkpoint
            )
            mission_checkpoint.validate_integrity()
        except (TypeError, ValueError) as error:
            raise CheckpointErrorV2("checkpoint mission scoring state is invalid") from error
        if (
            mission_checkpoint.resolved_hash != self.resolved_hash
            or mission_checkpoint.tick != self.tick
        ):
            raise CheckpointErrorV2("checkpoint mission scoring anchors differ from World")
        entity_ids = tuple(item.id for item in self.entities)
        if entity_ids != tuple(sorted(entity_ids)) or len(entity_ids) != len(set(entity_ids)):
            raise CheckpointErrorV2("checkpoint entity identities are duplicated or unstable")
        if self.used_entity_ids != tuple(sorted(set(self.used_entity_ids))):
            raise CheckpointErrorV2("checkpoint used entity identities are not canonical")
        if not set(entity_ids).issubset(self.used_entity_ids):
            raise CheckpointErrorV2("active entity is absent from permanent used identities")
        trigger_configs = self.event_state.spatial_effect_triggers
        trigger_ledger = self.event_state.spatial_effect_trigger_ledger
        trigger_consumption = self.event_state.spatial_effect_trigger_consumption
        destroyed_lifecycle_ledger = self.event_state.destroyed_lifecycle_ledger
        if not (
            isinstance(trigger_configs, Mapping)
            and isinstance(trigger_ledger, Mapping)
            and isinstance(trigger_consumption, Mapping)
            and isinstance(destroyed_lifecycle_ledger, Mapping)
        ):
            raise CheckpointErrorV2("checkpoint spatial trigger state is not a mapping")
        if any(
            not isinstance(trigger_id, str)
            or not trigger_id
            or not isinstance(config, Mapping)
            or config.get("trigger_event_id") != trigger_id
            or not isinstance(config.get("activation_tick"), int)
            or isinstance(config.get("activation_tick"), bool)
            or config["activation_tick"] < 0
            or config.get("source_kind") not in {"zone_entry", "collision"}
            or config.get("source_lifecycle") not in {"wreck", "despawn"}
            for trigger_id, config in trigger_configs.items()
        ):
            raise CheckpointErrorV2("checkpoint armed spatial trigger is invalid")
        entities_by_id = {item.id: item for item in self.entities}
        tombstones_by_id = {item.entity_id: item for item in self.tombstones}
        for authority_event_id, record in trigger_ledger.items():
            source_entity_id = (
                record.get("source_entity_id") if isinstance(record, Mapping) else None
            )
            status = record.get("lifecycle_status") if isinstance(record, Mapping) else None
            if (
                not isinstance(authority_event_id, str)
                or not authority_event_id
                or not isinstance(record, Mapping)
                or record.get("authority_event_id") != authority_event_id
                or not isinstance(record.get("trigger_event_id"), str)
                or not isinstance(source_entity_id, str)
                or source_entity_id not in self.used_entity_ids
                or record.get("source_kind") not in {"zone_entry", "collision"}
                or not isinstance(record.get("tick"), int)
                or isinstance(record.get("tick"), bool)
                or record["tick"] > self.tick
                or status
                not in {
                    "pending_damage_resolution",
                    "not_destroyed",
                    "wreck",
                    "despawned",
                    "despawned_with_cleanup_errors",
                    "already_unavailable",
                }
            ):
                raise CheckpointErrorV2("checkpoint spatial trigger ledger is invalid")
            if status == "wreck" and (
                source_entity_id not in entities_by_id
                or entities_by_id[source_entity_id].lifecycle != "destroyed"
            ):
                raise CheckpointErrorV2("checkpoint wreck lifecycle evidence is invalid")
            if status in {"despawned", "despawned_with_cleanup_errors"} and (
                source_entity_id in entities_by_id
                or source_entity_id not in tombstones_by_id
                or tombstones_by_id[source_entity_id].source_event_id
                != record.get("lifecycle_source_event_id", authority_event_id)
            ):
                raise CheckpointErrorV2("checkpoint despawn lifecycle evidence is invalid")
        for consumption_key, record in trigger_consumption.items():
            if (
                not isinstance(consumption_key, str)
                or not consumption_key
                or not isinstance(record, Mapping)
                or record.get("consumption_key") != consumption_key
                or record.get("trigger_event_id") not in trigger_configs
                or not isinstance(record.get("source_entity_id"), str)
                or record["source_entity_id"] not in self.used_entity_ids
                or record.get("authority_event_id") not in trigger_ledger
            ):
                raise CheckpointErrorV2("checkpoint spatial trigger consumption is invalid")
        for entity_id, record in destroyed_lifecycle_ledger.items():
            if (
                not isinstance(entity_id, str)
                or not isinstance(record, Mapping)
                or record.get("entity_id") != entity_id
                or entity_id not in self.used_entity_ids
                or record.get("policy") not in {"wreck", "despawn"}
                or record.get("status")
                not in {"wreck", "despawned", "despawned_with_cleanup_errors"}
                or not isinstance(record.get("tick"), int)
                or isinstance(record.get("tick"), bool)
                or record["tick"] > self.tick
                or not isinstance(record.get("source_event_id"), str)
                or not record["source_event_id"]
            ):
                raise CheckpointErrorV2("checkpoint destroyed lifecycle evidence is invalid")
            if record["status"] == "wreck" and (
                entity_id not in entities_by_id
                or entities_by_id[entity_id].lifecycle != "destroyed"
            ):
                raise CheckpointErrorV2("checkpoint generic wreck lifecycle evidence is invalid")
            if record["status"] in {"despawned", "despawned_with_cleanup_errors"} and (
                entity_id in entities_by_id
                or entity_id not in tombstones_by_id
                or tombstones_by_id[entity_id].source_event_id != record["source_event_id"]
            ):
                raise CheckpointErrorV2("checkpoint generic despawn lifecycle evidence is invalid")
        membership_keys = tuple(self.mission_zone_membership)
        if membership_keys != tuple(sorted(membership_keys)) or any(
            not key or zones != tuple(sorted(set(zones))) or any(not zone for zone in zones)
            for key, zones in self.mission_zone_membership.items()
        ):
            raise CheckpointErrorV2("checkpoint mission zone membership is not canonical")
        transition_hashes: set[str] = set()
        for transition in self.mission_zone_transitions:
            required = {
                "entity_id",
                "zone_id",
                "transition",
                "tick",
                "time_fraction",
                "evidence_hash",
            }
            evidence_hash = str(transition.get("evidence_hash", ""))
            fraction = transition.get("time_fraction")
            transition_tick = transition.get("tick")
            if (
                set(transition) != required
                or not transition.get("entity_id")
                or not transition.get("zone_id")
                or transition.get("transition") not in {"entered", "left"}
                or not isinstance(transition_tick, int)
                or isinstance(transition_tick, bool)
                or transition_tick < 0
                or not isinstance(fraction, (int, float))
                or isinstance(fraction, bool)
                or not math.isfinite(float(fraction))
                or not 0.0 <= float(fraction) <= 1.0
                or re.fullmatch(_HASH_PATTERN, evidence_hash) is None
                or evidence_hash in transition_hashes
            ):
                raise CheckpointErrorV2("checkpoint mission zone transition is invalid")
            transition_hashes.add(evidence_hash)
        if self.schedule_cursor != len(self.applied_lifecycle_event_ids):
            raise CheckpointErrorV2("checkpoint lifecycle cursor differs from applied events")
        operations = tuple(item.operation_id for item in self.lifecycle_ledger)
        if len(operations) != len(set(operations)):
            raise CheckpointErrorV2("checkpoint lifecycle operation identities are duplicated")
        world_snapshot_refs = tuple(
            str(item.get("resource_ref", "")) for item in self.world_adapter_snapshots
        )
        if (
            not all(world_snapshot_refs)
            or world_snapshot_refs != tuple(sorted(world_snapshot_refs))
            or len(world_snapshot_refs) != len(set(world_snapshot_refs))
        ):
            raise CheckpointErrorV2("checkpoint World adapter snapshots are not canonical")
        if any(not isinstance(active, bool) for active in self.zone_activation_state.values()):
            raise CheckpointErrorV2("checkpoint zone activation states are not boolean")
        if dict(self.event_state.zone_activation_state) != dict(self.zone_activation_state):
            raise CheckpointErrorV2("checkpoint event and spatial zone states differ")
        if self.spatial_effect_policy is not None:
            effect = self.spatial_effect_policy.effect_binding
            damage = self.spatial_effect_policy.damage_binding
            if (
                effect.resource_type != "effects"
                or damage.resource_type != "damage_models"
                or effect.normalized_content.get("damage_model_ref") != damage.exact_ref
                or self.spatial_effect_policy.magnitude_model
                not in {"constant", "scaled_relative_speed", "relative_kinetic_energy"}
                or self.spatial_effect_policy.output_unit != "1"
                or any(
                    not math.isfinite(float(value)) or float(value) < 0.0
                    for value in self.spatial_effect_policy.magnitude_parameters.values()
                )
            ):
                raise CheckpointErrorV2("checkpoint spatial effect policy is invalid")
        zone_operations = tuple(item.operation_id for item in self.zone_activation_ledger)
        motion_operations = tuple(item.operation_id for item in self.motion_ledger)
        world_tick_operations = tuple(item.operation_id for item in self.world_tick_ledger)
        if (
            any(
                not isinstance(item, str) or not item
                for item in (*zone_operations, *motion_operations)
            )
            or len(zone_operations) != len(set(zone_operations))
            or len(motion_operations) != len(set(motion_operations))
        ):
            raise CheckpointErrorV2("checkpoint spatial operation identities are invalid")
        motion_operation_set = set(motion_operations)
        lifecycle_operation_set = set(operations)
        if len(world_tick_operations) != len(set(world_tick_operations)) or any(
            item.tick - item.start_tick != item.steps
            or len(item.motion_operation_ids) != item.steps
            or len(item.event_receipts) != item.steps
            or len(item.damage_receipts) != item.steps
            or len(item.provider_receipts) != item.steps
            or len(item.mission_receipts) != item.steps
            or len(item.score_receipts) != item.steps
            or len(item.dynamics_receipts) % item.steps != 0
            or not set(item.motion_operation_ids).issubset(motion_operation_set)
            or not set(item.lifecycle_operation_ids).issubset(lifecycle_operation_set)
            or any(re.fullmatch(_HASH_PATTERN, value) is None for value in item.provider_receipts)
            for item in self.world_tick_ledger
        ):
            raise CheckpointErrorV2("checkpoint World tick ledger is inconsistent")
        authoritative_typed_receipts: dict[str, Any] = {}
        for tick_receipt in self.world_tick_ledger:
            for event_receipt in tick_receipt.event_receipts:
                typed_receipts = event_receipt.get("typed_event_receipts", ())
                resolved_ids = tuple(event_receipt.get("resolved_event_ids", ()))
                if not isinstance(typed_receipts, (list, tuple)) or resolved_ids != tuple(
                    item.get("event_id") for item in typed_receipts
                ):
                    raise CheckpointErrorV2("checkpoint typed event ledger differs from events")
                for typed in typed_receipts:
                    payload = typed.get("payload")
                    payload_hash = (
                        "sha256:"
                        + hashlib.sha256(
                            _canonical_json(payload, allow_nan=False).encode()
                        ).hexdigest()
                    )
                    if (
                        typed.get("payload_hash") != payload_hash
                        or re.fullmatch(
                            _HASH_PATTERN, str(typed.get("owner_state_hash_before", ""))
                        )
                        is None
                        or re.fullmatch(_HASH_PATTERN, str(typed.get("owner_state_hash_after", "")))
                        is None
                    ):
                        raise CheckpointErrorV2("checkpoint typed event receipt is invalid")
                    typed_hash = (
                        "sha256:"
                        + hashlib.sha256(
                            _canonical_json(typed, allow_nan=False).encode()
                        ).hexdigest()
                    )
                    prior_typed = authoritative_typed_receipts.get(typed_hash)
                    if prior_typed is not None and prior_typed != typed:
                        raise CheckpointErrorV2("checkpoint typed event receipt hash is ambiguous")
                    authoritative_typed_receipts[typed_hash] = typed
        for input_receipt in mission_checkpoint.event_score_input_receipts:
            world_receipt = input_receipt.get("world_event_receipt")
            supplied_hash = input_receipt.get("world_event_receipt_hash")
            if (
                not isinstance(world_receipt, Mapping)
                or supplied_hash not in authoritative_typed_receipts
                or authoritative_typed_receipts[supplied_hash] != dict(world_receipt)
            ):
                raise CheckpointErrorV2(
                    "checkpoint event score input lacks authoritative World receipt"
                )
        if self.consumed_provider_receipts != tuple(
            sorted(set(self.consumed_provider_receipts))
        ) or any(
            not isinstance(item, str) or re.fullmatch(_HASH_PATTERN, item) is None
            for item in self.consumed_provider_receipts
        ):
            raise CheckpointErrorV2("checkpoint provider receipts are not canonical")
        combat_operations = tuple(item.get("operation_id") for item in self.combat_ledger)
        if (
            any(not isinstance(item, str) or not item for item in combat_operations)
            or len(combat_operations) != len(set(combat_operations))
            or any(value < 0 for value in self.combat_cooldowns.values())
            or any(value < 0 for value in self.combat_ammunition.values())
            or any(not math.isfinite(value) or value < 0.0 for value in self.combat_energy.values())
            or any(
                not math.isfinite(value) or not 0.0 <= value <= 1.0
                for value in self.combat_component_health.values()
            )
            or any(re.fullmatch(_HASH_PATTERN, item) is None for item in self.combat_rng_state)
        ):
            raise CheckpointErrorV2("checkpoint combat continuation state is not canonical")
        engagement_requests: set[str] = set()
        for engagement in self.combat_engagement_ledger:
            if engagement.request_id in engagement_requests:
                raise CheckpointErrorV2("checkpoint combat request identities are duplicated")
            engagement_requests.add(engagement.request_id)
            execution_hash = (
                "sha256:"
                + hashlib.sha256(
                    _canonical_json(engagement.execution, allow_nan=False).encode()
                ).hexdigest()
            )
            if (
                execution_hash != engagement.execution_hash
                or engagement.execution.get("request_id") != engagement.request_id
                or engagement.execution.get("attacker_id") != engagement.attacker_id
                or engagement.execution.get("target_id") != engagement.target_id
            ):
                raise CheckpointErrorV2("checkpoint combat execution evidence is inconsistent")
        contact_keys = tuple(
            (item.evidence_id, item.owner_entity_id, item.target_entity_id)
            for item in self.combat_contact_evidence
        )
        if contact_keys != tuple(sorted(set(contact_keys))) or any(
            item.owner_entity_id not in entity_ids
            or item.target_entity_id not in entity_ids
            or item.observed_tick > self.tick
            or item.age_ticks < self.tick - item.observed_tick
            for item in self.combat_contact_evidence
        ):
            raise CheckpointErrorV2("checkpoint contact evidence is not authoritative")
        roe_ids = tuple(item.rule_id for item in self.combat_roe_rules)
        if roe_ids != tuple(sorted(set(roe_ids))):
            raise CheckpointErrorV2("checkpoint ROE policy identities are not canonical")
        if self.combat_engagement_ledger and self.combat_hit_model_state is None:
            raise CheckpointErrorV2("checkpoint hit model continuation state is absent")
        active_missile_ids = tuple(item.missile_id for item in self.missile_flights)
        terminal_missile_ids = tuple(item.missile_id for item in self.missile_terminal_receipts)
        if (
            active_missile_ids != tuple(sorted(active_missile_ids))
            or len(active_missile_ids) != len(set(active_missile_ids))
            or terminal_missile_ids != tuple(sorted(terminal_missile_ids))
            or len(terminal_missile_ids) != len(set(terminal_missile_ids))
            or set(active_missile_ids) & set(terminal_missile_ids)
            or any(
                item.launcher_id not in self.used_entity_ids
                or item.target_id not in self.used_entity_ids
                or item.launch_tick > self.tick
                or item.flight_ticks >= item.profile.max_flight_ticks
                for item in self.missile_flights
            )
            or any(
                item.launcher_id not in self.used_entity_ids
                or item.target_id not in self.used_entity_ids
                or item.tick > self.tick
                for item in self.missile_terminal_receipts
            )
        ):
            raise CheckpointErrorV2("checkpoint guided missile state is not canonical")
        pending_impact_ids = tuple(item.impact_id for item in self.pending_impacts)
        pending_receipt_ids = tuple(item.impact_id for item in self.pending_impact_receipts)
        if (
            pending_impact_ids != tuple(sorted(pending_impact_ids))
            or len(pending_impact_ids) != len(set(pending_impact_ids))
            or pending_receipt_ids != tuple(sorted(pending_receipt_ids))
            or len(pending_receipt_ids) != len(set(pending_receipt_ids))
            or set(pending_impact_ids) & set(pending_receipt_ids)
            or any(
                item.source_entity_id not in self.used_entity_ids
                or item.target_entity_id not in self.used_entity_ids
                or item.launch_tick >= item.scheduled_tick
                or item.scheduled_tick <= self.tick
                for item in self.pending_impacts
            )
            or any(
                item.source_entity_id not in self.used_entity_ids
                or item.target_entity_id not in self.used_entity_ids
                or item.tick > self.tick
                for item in self.pending_impact_receipts
            )
        ):
            raise CheckpointErrorV2("checkpoint delayed impact state is not canonical")
        for profile in self.combat_profiles:
            evidence = profile.get("model_evidence")
            if not isinstance(evidence, Mapping):
                raise CheckpointErrorV2("checkpoint combat profile evidence is absent")
            artifact = evidence.get("artifact_hash")
            if (
                artifact != evidence.get("expected_artifact_hash")
                or not isinstance(artifact, str)
                or re.fullmatch(_HASH_PATTERN, artifact) is None
            ):
                raise CheckpointErrorV2("checkpoint combat profile artifact evidence differs")
        adapter_keys = tuple(
            (item.get("entity_id"), item.get("resource_ref")) for item in self.combat_adapter_states
        )
        if len(adapter_keys) != len(set(adapter_keys)) or any(
            not isinstance(entity_id, str)
            or not entity_id
            or not isinstance(resource_ref, str)
            or not resource_ref
            or "state" not in item
            for (entity_id, resource_ref), item in zip(
                adapter_keys, self.combat_adapter_states, strict=True
            )
        ):
            raise CheckpointErrorV2("checkpoint combat adapter state is not canonical")
        if (
            tuple(event_id for item in self.lifecycle_ledger for event_id in item.applied_event_ids)
            != self.applied_lifecycle_event_ids
        ):
            raise CheckpointErrorV2("checkpoint ledger differs from applied event cursor")
        tombstone_ids = tuple(item.entity_id for item in self.tombstones)
        if tombstone_ids != tuple(sorted(set(tombstone_ids))):
            raise CheckpointErrorV2("checkpoint tombstones are duplicated or unstable")
        if set(tombstone_ids) & set(entity_ids) or not set(tombstone_ids).issubset(
            self.used_entity_ids
        ):
            raise CheckpointErrorV2("checkpoint tombstones conflict with active or used identities")
        claimed = self.controller_ownership.get("claimed_entity_ids")
        uncontrolled = self.controller_ownership.get("uncontrolled_entity_ids")
        if (
            not isinstance(claimed, (list, tuple))
            or not isinstance(uncontrolled, (list, tuple))
            or any(item not in entity_ids for item in (*claimed, *uncontrolled))
            or set(claimed) & set(uncontrolled)
            or set(claimed) | set(uncontrolled) != set(entity_ids)
        ):
            raise CheckpointErrorV2("checkpoint controller ownership is inconsistent")
        try:
            # This validates deterministic simulation state; no security randomness is involved.
            random.Random().setstate(_tuple_tree(self.rng_state))  # nosec B311
        except (TypeError, ValueError) as error:
            raise CheckpointErrorV2("checkpoint RNG continuation state is invalid") from error
        snapshot_keys: set[tuple[str, str]] = set()
        for snapshot in self.native_adapter_snapshots:
            key = (snapshot.entity_id, snapshot.resource_ref)
            if key in snapshot_keys or snapshot.entity_id not in entity_ids:
                raise CheckpointErrorV2("checkpoint native snapshot ownership is invalid")
            snapshot_keys.add(key)
            try:
                validate_native_dynamics_snapshot_v2(snapshot)
            except ValueError as error:
                raise CheckpointErrorV2(
                    "checkpoint native snapshot integrity is invalid"
                ) from error

    def to_json(self) -> str:
        self.validate_integrity()
        return _canonical_json(self.model_dump(mode="json"), allow_nan=False)

    @classmethod
    def from_json(cls, encoded: str) -> WorldCheckpointV2:
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, Mapping):
                raise ValueError("checkpoint payload must be an object")
            value = cls.model_validate(payload)
            value.validate_integrity()
            return value
        except CheckpointErrorV2:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise CheckpointErrorV2("checkpoint nested structure is invalid") from error

    @classmethod
    def create(cls, payload: Mapping[str, Any]) -> WorldCheckpointV2:
        value = dict(payload)
        value["checkpoint_hash"] = cls.compute_checkpoint_hash(value)
        result = cls.model_validate(value)
        result.validate_integrity()
        return result


def _tuple_tree(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_tuple_tree(item) for item in value)
    return value


class CheckpointRestoreFaultInjectorV2:
    def __init__(self) -> None:
        self.fail_after_restored_adapters: int | None = None
        self.fail_on_replacement_adapter_index: int | None = None
        self.fail_on_native_replacement_index: int | None = None


@dataclass(frozen=True, slots=True)
class CheckpointAdapterCleanupErrorV2:
    adapter_instance_id: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class CheckpointRestoreAuditV2:
    status: Literal["rolled_back", "committed", "committed_with_cleanup_errors"]
    created_adapter_instance_ids: tuple[str, ...]
    closed_adapter_instance_ids: tuple[str, ...]
    failed_adapter_index: int | None = None
    failed_adapter_instance_id: str | None = None
    failed_stage: Literal["initial", "native_replacement"] | None = None
    adapter_stages: tuple[Literal["initial", "native_replacement"], ...] = ()
    replaced_initial_adapter_instance_ids: tuple[str, ...] = ()
    closed_replaced_initial_adapter_instance_ids: tuple[str, ...] = ()
    failed_replaced_initial_adapter_instance_ids: tuple[str, ...] = ()
    cleanup_errors: tuple[CheckpointAdapterCleanupErrorV2, ...] = ()


__all__ = [
    "CheckpointEntityV2",
    "CheckpointAdapterCleanupErrorV2",
    "CheckpointErrorV2",
    "CheckpointCombatEngagementV2",
    "CheckpointContactEvidenceV2",
    "CheckpointHitModelStateV2",
    "CheckpointLifecycleReceiptV2",
    "CheckpointMotionReceiptV2",
    "CheckpointWorldTickReceiptV2",
    "CheckpointRestoreAuditV2",
    "CheckpointRestoreFaultInjectorV2",
    "CheckpointRoeRuleV2",
    "CheckpointTombstoneV2",
    "CheckpointSpatialClockV2",
    "CheckpointZoneActivationReceiptV2",
    "WorldEventStateSnapshotV2",
    "WorldCheckpointV2",
]

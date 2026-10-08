"""Generic construction of session-owned runtime worlds from resolved v2 DTOs."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, suppress
from dataclasses import dataclass, fields, is_dataclass
from threading import RLock
from types import MappingProxyType
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_serializer, model_validator

from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    ModelBindingEvidenceErrorV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)
from openmdbench.combat.damage_v2 import DamageApplyReceiptV2
from openmdbench.combat.models_v2 import CombatErrorV2, EngagementRequestV2
from openmdbench.dynamics.native_v2 import (
    AUV_MODEL_REF,
    FIXED_MODEL_REF,
    MMG_MODEL_REF,
    UAV_MODEL_REF,
    DynamicsCommandV2,
    DynamicsStateV2,
    MMGCommandV2,
    NativeDynamicsAdapterFactoryV2,
    NativeDynamicsBindingV2,
    NativeDynamicsErrorV2,
    NativeDynamicsSnapshotV2,
    compute_native_resolved_binding_identity_v2,
    materialize_native_dynamics_binding_v2,
    native_artifact_manifest_v2,
)
from openmdbench.scenarios.declarative_v2 import (
    ResolvedEntityV2,
    ResolvedEventV2,
    ResolvedResourceBindingV2,
    ResolvedScenarioV2,
    ResolvedSpatialEffectPolicyV2,
)
from openmdbench.schemas.core_v2 import FactionV2, ObservationV2, RelationshipV2
from openmdbench.systems.generic_v2 import (
    CommunicationTickReceiptV2,
    EnergyTickReceiptV2,
    GenericSubsystemEngineV2,
    GenericSubsystemTickReceiptV2,
    SensorContactReceiptV2,
    SubsystemEntityFactV2,
)
from openmdbench.world.boundary_v2 import (
    BoundaryEntityV2,
    BoundaryEventV2,
    BoundaryPolicyActionV2,
    BoundarySystemV2,
    CollisionEventV2,
    CollisionShapeV2,
    DamageIntentV2,
    ImpactDamageEvidenceV2,
    ImpactMagnitudeModelV2,
    MotionSegmentV2,
    ZoneActivationReceiptV2,
    ZoneActivationSnapshotV2,
)
from openmdbench.world.capabilities_v2 import (
    CapabilitySelectorV2,
    CapabilityTokenV2,
    build_capability_index,
    capability_tokens_for_entity,
    coarse_capabilities,
)
from openmdbench.world.capability_modifier_v2 import (
    CapabilityModifierV2,
    modifiers_from_environment_content_v2,
    resolve_capability_v2,
)
from openmdbench.world.checkpoint_v2 import (
    CheckpointAdapterCleanupErrorV2,
    CheckpointContactEvidenceV2,
    CheckpointEntityV2,
    CheckpointHitModelStateV2,
    CheckpointLifecycleReceiptV2,
    CheckpointMotionReceiptV2,
    CheckpointRestoreAuditV2,
    CheckpointRestoreFaultInjectorV2,
    CheckpointRoeRuleV2,
    CheckpointSpatialClockV2,
    CheckpointTombstoneV2,
    CheckpointWorldTickReceiptV2,
    CheckpointZoneActivationReceiptV2,
    WorldCheckpointV2,
    WorldEventStateSnapshotV2,
)
from openmdbench.world.combat_evidence_v2 import (
    WorldContactEvidenceV2,
    WorldContactStoreV2,
    WorldRoeRuleV2,
    build_component_damage_profiles_v2,
    build_world_authority_grants_v2,
)
from openmdbench.world.communication_transport_v2 import schedule_transport_v2
from openmdbench.world.controllers_v2 import (
    ControllerClaimV2,
    ControllerOwnershipIndexV2,
    ControllerReservationV2,
    build_controller_ownership,
)
from openmdbench.world.geography_v2 import GeographyErrorV2, GeographyServiceV2
from openmdbench.world.lifecycle_v2 import (
    LifecycleAuditRecordV2,
    LifecycleFaultInjectorV2,
    LifecycleReceiptV2,
    LifecycleTombstoneV2,
    frozen_ledger,
    frozen_tombstones,
    lifecycle_blueprint_hash,
)
from openmdbench.world.missile_v2 import (
    MissileFlightV2,
    MissileTerminalReceiptV2,
    advance_guided_missile_v2,
)


class FactoryErrorV2(ValueError):
    """Stable runtime-construction failure with machine-readable evidence."""

    def __init__(
        self,
        *,
        code: str,
        path: Sequence[str],
        value: object,
        reason: str,
        suggestion: str,
    ) -> None:
        self.code = code
        self.path = tuple(path)
        self.value = value
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"{code} at {'/'.join(self.path)}: {reason}; suggestion: {suggestion}")


class MotionPipelineErrorV2(FactoryErrorV2):
    """Stable failure at the World-owned motion commit boundary."""


def _estimated_contact_position_v2(
    evidence_id: str,
    observed_tick: int,
    confidence: float,
    truth_position_m: Sequence[float],
) -> tuple[float, float, float]:
    """Produce a deterministic bounded track estimate without publishing exact truth."""

    digest = hashlib.sha256(f"{evidence_id}:{observed_tick}".encode()).digest()
    bearing = 2.0 * math.pi * int.from_bytes(digest[:4], "big") / float(2**32)
    error_m = max(0.25, (1.0 - confidence) * 250.0)
    return (
        float(truth_position_m[0]) + error_m * math.sin(bearing),
        float(truth_position_m[1]) + error_m * math.cos(bearing),
        float(truth_position_m[2]),
    )


def _motion_error(
    code: str,
    path: Sequence[str],
    value: object,
    reason: str,
    suggestion: str,
) -> MotionPipelineErrorV2:
    return MotionPipelineErrorV2(
        code=code,
        path=path,
        value=value,
        reason=reason,
        suggestion=suggestion,
    )


@dataclass(frozen=True, slots=True)
class MotionCandidateV2:
    entity_id: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    heading_deg: float | None = None
    dynamics_model_ref: str | None = None
    dynamics_resource_ref: str | None = None
    model_ref: str | None = None
    adapter_instance_id: str | None = None
    resolved_hash: str | None = None
    provider_receipt: str | None = None

    def __post_init__(self) -> None:
        evidence = (
            self.dynamics_resource_ref,
            self.model_ref,
            self.adapter_instance_id,
            self.resolved_hash,
            self.provider_receipt,
        )
        if any(item is None for item in evidence):
            raise _motion_error(
                "world.motion_provenance_partial",
                ("motion_candidate", "provenance"),
                tuple(item is not None for item in evidence),
                "dynamics motion requires all five provenance anchors",
                "provide exact resource, model, adapter, resolved hash, and provider receipt",
            )
        if any(not isinstance(item, str) or not item for item in evidence):
            raise _motion_error(
                "world.motion_provenance_invalid",
                ("motion_candidate", "provenance"),
                evidence,
                "dynamics provenance anchors must be nonempty strings",
                "use evidence issued by the owning dynamics adapter and resolved world",
            )
        if (
            re.fullmatch(r"sha256:[0-9a-f]{64}", cast(str, self.resolved_hash)) is None
            or re.fullmatch(r"sha256:[0-9a-f]{64}", cast(str, self.provider_receipt)) is None
        ):
            raise _motion_error(
                "world.motion_provenance_invalid",
                ("motion_candidate", "provenance"),
                "digest",
                "resolved and provider provenance must use canonical sha256 digests",
                "use the exact resolved hash and adapter-issued output receipt",
            )
        object.__setattr__(self, "dynamics_model_ref", self.model_ref)

    @classmethod
    def from_adapter_output(
        cls,
        *,
        entity_id: str,
        position_m: tuple[float, float, float],
        velocity_mps: tuple[float, float, float],
        dynamics_resource_ref: str,
        model_ref: str,
        adapter_instance_id: str,
        resolved_hash: str,
        provider_receipt: str,
        heading_deg: float | None = None,
    ) -> MotionCandidateV2:
        return cls(
            entity_id=entity_id,
            position_m=position_m,
            velocity_mps=velocity_mps,
            heading_deg=heading_deg,
            dynamics_model_ref=model_ref,
            dynamics_resource_ref=dynamics_resource_ref,
            model_ref=model_ref,
            adapter_instance_id=adapter_instance_id,
            resolved_hash=resolved_hash,
            provider_receipt=provider_receipt,
        )


@dataclass(frozen=True, slots=True)
class KinematicMotionCandidateV2:
    """Explicit non-adapter motion for fixed entities and static wrecks."""

    entity_id: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    resolved_hash: str
    provenance_kind: Literal["no_dynamics", "lifecycle_wreck"] = "no_dynamics"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.entity_id, str)
            or not self.entity_id
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.resolved_hash) is None
            or self.provenance_kind not in {"no_dynamics", "lifecycle_wreck"}
        ):
            raise _motion_error(
                "world.motion_kinematic_provenance_invalid",
                ("kinematic_motion_candidate", "provenance"),
                self.entity_id,
                "kinematic motion requires an entity identity and exact resolved hash anchor",
                "use a fixed-entity or lifecycle-wreck provenance kind",
            )


@dataclass(frozen=True, slots=True)
class MotionReceiptV2:
    tick: int
    next_tick: int
    operation_id: str
    dt_seconds: float
    tick_start_time_seconds: float
    candidate_entity_ids: tuple[str, ...]
    boundary_events: tuple[BoundaryEventV2, ...]
    collision_events: tuple[CollisionEventV2, ...]
    damage_intents: tuple[DamageIntentV2, ...]
    policy_actions: tuple[BoundaryPolicyActionV2, ...]


SUPPORTED_TICK_EVENT_TYPES = (
    "weather_change",
    "zone_activation",
    "jamming_start",
    "jamming_end",
    "component_suppression",
    "message",
    "apply_effect",
    "mission_marker",
    "spatial_effect_trigger",
)


class EntityControlCommandV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    entity_id: str = Field(min_length=1, max_length=256)
    tick: StrictInt = Field(ge=0)
    controls: dict[str, float]

    @model_validator(mode="after")
    def validate_controls(self) -> EntityControlCommandV2:
        if any(
            not isinstance(key, str)
            or not key
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for key, value in self.controls.items()
        ):
            raise ValueError("entity controls require a typed finite tick-bound mapping")
        object.__setattr__(
            self,
            "controls",
            MappingProxyType({key: float(value) for key, value in sorted(self.controls.items())}),
        )
        return self

    @field_serializer("controls")
    def serialize_controls(self, controls: Mapping[str, float]) -> dict[str, float]:
        return dict(controls)


@dataclass(frozen=True, slots=True)
class MotionEligibilityEntryV2:
    """One World-authoritative dynamics command slot at a pre-motion boundary."""

    entity_id: str
    dynamics_resource_ref: str
    model_ref: str
    fallback_controls: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class MotionEligibilitySnapshotV2:
    """Immutable World projection consumed by the session action pipeline.

    ``active_entity_ids`` records lifecycle eligibility for queued actions;
    ``entries`` is the stricter subset that must receive exactly one dynamics
    command.  Keeping both in one World-owned projection prevents Session and
    World from independently reimplementing lifecycle/capability filtering.
    """

    expected_tick: int
    world_tick: int
    resolved_hash: str
    active_entity_ids: tuple[str, ...]
    entries: tuple[MotionEligibilityEntryV2, ...]
    fingerprint: str

    @property
    def entity_ids(self) -> tuple[str, ...]:
        return tuple(item.entity_id for item in self.entries)


@dataclass(frozen=True, slots=True)
class DynamicsStepReceiptV2:
    entity_id: str
    tick: int
    resource_ref: str
    model_ref: str
    adapter_instance_id: str
    artifact_hash: str
    manifest_hash: str
    input_hash: str
    output_hash: str
    snapshot_hash: str


class MessageIntentV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    message_id: str = Field(min_length=1, max_length=256)
    sender_entity_id: str = Field(min_length=1, max_length=256)
    recipient_entity_id: str | None = Field(default=None, min_length=1, max_length=256)
    recipient_controller_slots: tuple[str, ...] = ()
    broadcast_faction_id: str | None = Field(default=None, min_length=1, max_length=256)
    tick: StrictInt = Field(ge=0)
    payload: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def validate_recipient_scope(self) -> MessageIntentV2:
        selectors = (
            int(self.recipient_entity_id is not None)
            + int(bool(self.recipient_controller_slots))
            + int(self.broadcast_faction_id is not None)
        )
        if (
            selectors != 1
            or len(self.recipient_controller_slots) != len(set(self.recipient_controller_slots))
            or any(
                not isinstance(slot, str) or not slot for slot in self.recipient_controller_slots
            )
        ):
            raise ValueError("message intent requires exactly one explicit recipient scope")
        return self


class WorldTickInputV2(BaseModel):
    """Complete explicit evidence required to advance one or more World ticks."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        allow_inf_nan=False,
        arbitrary_types_allowed=True,
    )

    expected_tick: StrictInt = Field(ge=0)
    operation_id: str = Field(min_length=1, max_length=256)
    entity_commands: tuple[EntityControlCommandV2, ...] = ()
    engagement_requests: tuple[EngagementRequestV2, ...] = ()
    message_intents: tuple[MessageIntentV2, ...] = ()
    dt_seconds: float = Field(gt=0.0)
    steps: StrictInt = Field(default=1, ge=1, le=10_000)

    @model_validator(mode="after")
    def validate_complete_tick_input(self) -> WorldTickInputV2:
        if not math.isfinite(self.dt_seconds):
            raise ValueError("World tick duration must be finite")
        identities = tuple(command.entity_id for command in self.entity_commands)
        if identities != tuple(sorted(set(identities))):
            raise ValueError("World tick entity commands must have stable unique identities")
        request_ids = tuple(request.request_id for request in self.engagement_requests)
        if request_ids != tuple(sorted(set(request_ids))) or any(
            request.tick != self.expected_tick for request in self.engagement_requests
        ):
            raise ValueError("World tick combat requests must have stable current identities")
        message_ids = tuple(item.message_id for item in self.message_intents)
        if message_ids != tuple(sorted(set(message_ids))) or any(
            item.tick != self.expected_tick for item in self.message_intents
        ):
            raise ValueError("World tick messages must have stable current identities")
        if self.steps > 1:
            raise ValueError("multi-step World ticks require one explicit command batch per tick")
        return self


@dataclass(frozen=True, slots=True)
class TypedEventExecutionReceiptV2:
    event_id: str
    event_type: str
    tick: int
    payload: Mapping[str, Any]
    payload_hash: str
    owner_state_hash_before: str
    owner_state_hash_after: str


@dataclass(frozen=True, slots=True)
class WorldEventReceiptV2:
    tick: int
    operation_id: str
    boundary_event_ids: tuple[str, ...]
    collision_event_ids: tuple[str, ...]
    damage_intent_ids: tuple[str, ...]
    resolved_event_ids: tuple[str, ...] = ()
    typed_event_receipts: tuple[TypedEventExecutionReceiptV2, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldTickReceiptV2:
    operation_id: str
    start_tick: int
    tick: int
    steps: int
    motion_receipts: tuple[MotionReceiptV2, ...]
    stage_order: tuple[str, ...] = (
        "lifecycle",
        "dynamics_motion",
        "boundary_collision",
        "energy",
        "sensing",
        "communications",
        "combat",
        "damage_events",
        "mission",
        "scoring",
        "cooldown",
    )
    lifecycle_receipts: tuple[LifecycleReceiptV2, ...] = ()
    event_receipts: tuple[WorldEventReceiptV2, ...] = ()
    damage_receipts: tuple[Any, ...] = ()
    provider_receipts: tuple[str, ...] = ()
    dynamics_receipts: tuple[DynamicsStepReceiptV2, ...] = ()
    mission_receipts: tuple[Any, ...] = ()
    score_receipts: tuple[Any, ...] = ()
    combat_receipts: tuple[Any, ...] = ()
    subsystem_receipts: tuple[GenericSubsystemTickReceiptV2, ...] = ()


@dataclass(frozen=True, slots=True)
class WorldPresentationTickReceiptV2:
    """The current tick evidence needed by a rich frame, without history."""

    event_receipts: tuple[Mapping[str, Any], ...] = ()
    combat_receipts: tuple[Mapping[str, Any], ...] = ()
    damage_receipts: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class WorldPresentationSnapshotV2:
    """Small immutable frame source that never constructs a full checkpoint."""

    tick: int
    spatial_clock: CheckpointSpatialClockV2
    missile_flights: tuple[MissileFlightV2, ...]
    zone_activation_state: Mapping[str, bool]
    world_tick_ledger: tuple[WorldPresentationTickReceiptV2, ...]
    mission_scoring_checkpoint: Mapping[str, Any]
    event_state: WorldEventStateSnapshotV2
    combat_contact_evidence: tuple[CheckpointContactEvidenceV2, ...]


@dataclass(frozen=True, slots=True)
class WorldCombatDispatchReceiptV2:
    request_id: str
    tick: int
    status: Literal["executed", "rejected"]
    execution: Any | None = None
    error_code: str | None = None


def _motion_receipt_from_plain(value: Mapping[str, Any]) -> tuple[MotionReceiptV2, str]:
    payload = dict(value)
    fingerprint = str(payload.pop("fingerprint"))
    receipt = MotionReceiptV2(
        tick=int(payload["tick"]),
        next_tick=int(payload["next_tick"]),
        operation_id=str(payload["operation_id"]),
        dt_seconds=float(payload["dt_seconds"]),
        tick_start_time_seconds=float(payload["tick_start_time_seconds"]),
        candidate_entity_ids=tuple(payload["candidate_entity_ids"]),
        boundary_events=tuple(BoundaryEventV2(**item) for item in payload["boundary_events"]),
        collision_events=tuple(CollisionEventV2(**item) for item in payload["collision_events"]),
        damage_intents=tuple(
            DamageIntentV2.model_validate(item) for item in payload["damage_intents"]
        ),
        policy_actions=tuple(
            BoundaryPolicyActionV2(
                **{
                    **item,
                    "candidate_end_m": tuple(item["candidate_end_m"]),
                    "resolved_end_m": tuple(item["resolved_end_m"]),
                    "boundary_normal": tuple(item["boundary_normal"]),
                    "resolved_velocity_mps": tuple(item["resolved_velocity_mps"]),
                    "contact_position_m": tuple(item["contact_position_m"]),
                }
            )
            for item in payload["policy_actions"]
        ),
    )
    return receipt, fingerprint


class _CheckpointAdapterStageFailure(RuntimeError):
    def __init__(
        self,
        *,
        stage: Literal["initial", "native_replacement"],
        index: int,
        instance_id: str,
    ) -> None:
        self.stage = stage
        self.index = index
        self.instance_id = instance_id
        super().__init__(f"checkpoint adapter staging failed at {stage} index {index}")


def _factory_error(
    code: str,
    path: Sequence[str],
    value: object,
    reason: str,
    suggestion: str,
) -> FactoryErrorV2:
    return FactoryErrorV2(
        code=code,
        path=path,
        value=value,
        reason=reason,
        suggestion=suggestion,
    )


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="json"))
    return value


def _frozen_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _frozen_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _canonical_evidence_hash(value: Any) -> str:
    encoded = json.dumps(
        _plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class FrozenVectorV2(tuple[float, float, float]):
    """Immutable 3-vector retaining value equality with ordinary sequences."""

    def __new__(cls, value: Sequence[float]) -> FrozenVectorV2:
        return tuple.__new__(cls, (float(value[0]), float(value[1]), float(value[2])))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, (str, bytes, bytearray)):
            return tuple(self) == tuple(other)
        return False

    __hash__ = tuple.__hash__


@dataclass(slots=True)
class _RuntimeEntityStateV2:
    """Mutable state owned by exactly one runtime world session."""

    position_m: list[float]
    velocity_mps: list[float]
    heading_deg: float
    health: float
    energy: float | None
    ammunition: dict[str, int]
    component_states: dict[str, Any]
    lifecycle: str
    controller: dict[str, Any]

    def clone(self) -> _RuntimeEntityStateV2:
        return _RuntimeEntityStateV2(
            position_m=list(self.position_m),
            velocity_mps=list(self.velocity_mps),
            heading_deg=self.heading_deg,
            health=self.health,
            energy=self.energy,
            ammunition=dict(self.ammunition),
            component_states=_plain(self.component_states),
            lifecycle=self.lifecycle,
            controller=_plain(self.controller),
        )


@dataclass(frozen=True, slots=True)
class FrozenEntityStateV2:
    position_m: FrozenVectorV2
    velocity_mps: FrozenVectorV2
    heading_deg: float
    health: float
    energy: float | None
    ammunition: Mapping[str, int]
    component_states: Mapping[str, Any]
    lifecycle: str
    controller: Mapping[str, Any]


def _freeze_state(state: _RuntimeEntityStateV2) -> FrozenEntityStateV2:
    return FrozenEntityStateV2(
        position_m=FrozenVectorV2(state.position_m),
        velocity_mps=FrozenVectorV2(state.velocity_mps),
        heading_deg=state.heading_deg,
        health=state.health,
        energy=state.energy,
        ammunition=MappingProxyType(dict(state.ammunition)),
        component_states=_frozen_mapping(state.component_states),
        lifecycle=state.lifecycle,
        controller=_frozen_mapping(state.controller),
    )


@dataclass(slots=True)
class _RuntimeEntityV2:
    definition: ResolvedEntityV2
    state: _RuntimeEntityStateV2
    capabilities: frozenset[str]
    capability_tokens: tuple[CapabilityTokenV2, ...]
    adapters: Mapping[str, object]

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def faction_id(self) -> str:
        return self.definition.faction_id

    @property
    def tags(self) -> tuple[str, ...]:
        return self.definition.tags

    @property
    def domain(self) -> str:
        return self.definition.domain

    @property
    def controller_binding(self) -> str | None:
        return self.definition.controller_slot


@dataclass(frozen=True, slots=True)
class AdapterDiagnosticV2:
    resource_ref: str
    adapter_type: str
    instance_id: str
    model_ref: str | None
    rng_fingerprint: str | None
    closed: bool
    details: Mapping[str, Any]
    last_output_receipt: str = ""
    previous_output_receipt: str = ""

    @property
    def adapter_instance_id(self) -> str:
        return self.instance_id


@dataclass(frozen=True, slots=True)
class CombatInventorySnapshotV2:
    """Immutable view of entity and World-owned combat resources."""

    entity_ids: tuple[str, ...]
    effect_refs: tuple[str, ...]
    damage_model_refs: tuple[str, ...]
    adapter_diagnostics: Mapping[str, AdapterDiagnosticV2]


@dataclass(frozen=True, slots=True)
class WorldAdapterTransactionV2:
    """Immutable audit of World-owned adapter creation, restore, and cleanup."""

    created_adapter_ids: tuple[str, ...] = ()
    restored_adapter_ids: tuple[str, ...] = ()
    closed_adapter_ids: tuple[str, ...] = ()
    failed_adapter_ids: tuple[str, ...] = ()
    cleanup_errors: tuple[CheckpointAdapterCleanupErrorV2, ...] = ()
    operation_id: str = ""
    status: str = "completed"


class _AdapterDiagnosticsV2(Mapping[str, AdapterDiagnosticV2]):
    def __init__(
        self,
        values: Mapping[str, AdapterDiagnosticV2],
        *,
        primary_ref: str | None,
    ) -> None:
        self._values = MappingProxyType(dict(values))
        self._ordered = tuple(
            sorted(
                values.values(),
                key=lambda item: (item.resource_ref != primary_ref, item.resource_ref),
            )
        )

    def __getitem__(self, key: str | int) -> AdapterDiagnosticV2:
        if isinstance(key, int):
            return self._ordered[key]
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


@dataclass(frozen=True, slots=True)
class EntityViewV2:
    """Public immutable projection of a session-owned runtime entity."""

    definition: ResolvedEntityV2
    state: FrozenEntityStateV2
    capabilities: frozenset[str]
    capability_tokens: tuple[CapabilityTokenV2, ...]
    adapter_diagnostics: Mapping[str, AdapterDiagnosticV2]

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def faction_id(self) -> str:
        return self.definition.faction_id

    @property
    def tags(self) -> tuple[str, ...]:
        return self.definition.tags

    @property
    def domain(self) -> str:
        return self.definition.domain

    @property
    def controller_binding(self) -> str | None:
        return self.definition.controller_slot


def _adapter_details(adapter: object) -> tuple[bool, Mapping[str, Any]]:
    diagnostic = getattr(adapter, "diagnostic", None)
    if not callable(diagnostic):
        return False, MappingProxyType({})
    try:
        value = diagnostic()
        payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else _plain(value)
        if not isinstance(payload, Mapping):
            return False, MappingProxyType({})
        closed = payload.get("closed", False)
        return bool(closed), _frozen_mapping(payload)
    except Exception:
        return False, MappingProxyType({})


def _entity_view(entity: _RuntimeEntityV2, *, adapters_closed: bool = False) -> EntityViewV2:
    diagnostics: dict[str, AdapterDiagnosticV2] = {}
    binding_index = {
        binding.exact_ref: binding
        for bindings in entity.definition.resource_bindings.values()
        for binding in bindings
    }
    for reference, adapter in entity.adapters.items():
        adapter_closed, details = _adapter_details(adapter)
        binding = binding_index.get(reference)
        instance_id = str(details.get("instance_id", f"adapter-{id(adapter):016x}"))
        receipt_base = f"{entity.id}:{reference}:{instance_id}"
        diagnostics[reference] = AdapterDiagnosticV2(
            resource_ref=reference,
            adapter_type=f"{type(adapter).__module__}.{type(adapter).__qualname__}",
            instance_id=instance_id,
            model_ref=(
                str(details["model_ref"])
                if isinstance(details.get("model_ref"), str)
                else (None if binding is None else binding.model_ref)
            ),
            rng_fingerprint=(
                str(details["rng_fingerprint"])
                if isinstance(details.get("rng_fingerprint"), str)
                else None
            ),
            closed=adapters_closed or adapter_closed,
            details=details,
            last_output_receipt="sha256:"
            + hashlib.sha256(f"{receipt_base}:current".encode()).hexdigest(),
            previous_output_receipt="sha256:"
            + hashlib.sha256(f"{receipt_base}:previous".encode()).hexdigest(),
        )
    return EntityViewV2(
        definition=entity.definition,
        state=_freeze_state(entity.state),
        capabilities=entity.capabilities,
        capability_tokens=entity.capability_tokens,
        adapter_diagnostics=_AdapterDiagnosticsV2(
            diagnostics, primary_ref=entity.definition.composition.dynamics_ref
        ),
    )


def _adapter_diagnostic(
    reference: str,
    adapter: object,
    binding: ResolvedResourceBindingV2,
    *,
    owner_id: str,
    adapters_closed: bool = False,
) -> AdapterDiagnosticV2:
    adapter_closed, details = _adapter_details(adapter)
    instance_id = str(details.get("instance_id", f"adapter-{id(adapter):016x}"))
    receipt_base = f"{owner_id}:{reference}:{instance_id}"
    return AdapterDiagnosticV2(
        resource_ref=reference,
        adapter_type=f"{type(adapter).__module__}.{type(adapter).__qualname__}",
        instance_id=instance_id,
        model_ref=(
            str(details["model_ref"])
            if isinstance(details.get("model_ref"), str)
            else binding.model_ref
        ),
        rng_fingerprint=(
            str(details["rng_fingerprint"])
            if isinstance(details.get("rng_fingerprint"), str)
            else None
        ),
        closed=adapters_closed or adapter_closed,
        details=details,
        last_output_receipt="sha256:"
        + hashlib.sha256(f"{receipt_base}:current".encode()).hexdigest(),
        previous_output_receipt="sha256:"
        + hashlib.sha256(f"{receipt_base}:previous".encode()).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class LifecycleScheduleEntryV2:
    topological_index: int
    tick: int
    priority: int
    event_type: str
    entity_id: str
    source_event_id: str
    blueprint: ResolvedEntityV2 | None = None

    @property
    def blueprint_hash(self) -> str | None:
        return lifecycle_blueprint_hash(self.blueprint)


@dataclass(frozen=True, slots=True)
class WorldSnapshotV2:
    tick: int
    entities: tuple[EntityViewV2, ...]

    @property
    def snapshot_hash(self) -> str:
        payload = [
            self.tick,
            [item.id for item in self.entities],
        ]
        return (
            "sha256:"
            + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        )


def _metadata_for(
    registry: ModelRegistryV2,
    model_ref: str,
    *,
    path: Sequence[str],
) -> ModelFactoryMetadataV2:
    try:
        return registry.metadata(model_ref)
    except CatalogResolutionErrorV2 as error:
        raise _factory_error(
            "factory.model_unknown",
            (*path, "model_ref"),
            model_ref,
            "the resolved definition names no registered model factory",
            "install the exact trusted model artifact recorded at compile time",
        ) from error


def _validate_evidence(
    metadata: ModelFactoryMetadataV2,
    evidence: object,
    *,
    resource_type: str,
    path: Sequence[str],
) -> None:
    trusted = bool(getattr(evidence, "trusted", False))
    if not trusted or not metadata.trusted:
        raise _factory_error(
            "factory.model_untrusted",
            (*path, "model_evidence", "trusted"),
            trusted,
            "runtime construction requires compile-time and runtime trust evidence",
            "register a trusted factory and recompile the scenario",
        )
    interface_fields = ("interface_version", "input_schema", "output_schema")
    mismatched_interface = tuple(
        field
        for field in interface_fields
        if getattr(evidence, field, None) != getattr(metadata, field)
    )
    evidence_types = tuple(getattr(evidence, "resource_types", ()))
    if (
        mismatched_interface
        or metadata.interface_version != "2.0"
        or metadata.input_schema != "catalog-resource@2.0"
        or metadata.output_schema != "runtime-component@2.0"
        or resource_type not in metadata.resource_types
        or resource_type not in evidence_types
    ):
        raise _factory_error(
            "factory.model_interface_incompatible",
            (*path, "model_evidence"),
            metadata.exact_ref,
            "model interface or declared resource role is incompatible",
            "use a v2 catalog-resource to runtime-component factory for this role",
        )
    if (
        getattr(evidence, "model_ref", None) != metadata.exact_ref
        or getattr(evidence, "artifact_sha256", None) != metadata.artifact_sha256
    ):
        raise _factory_error(
            "factory.model_evidence_mismatch",
            (*path, "model_evidence", "artifact_sha256"),
            getattr(evidence, "artifact_sha256", None),
            "runtime model identity differs from the compiled evidence",
            "restore the exact recorded artifact or recompile with the new registry",
        )


def _cleanup_adapters(adapters: Sequence[object]) -> None:
    _cleanup_adapters_with_evidence(adapters)


def _cleanup_adapters_with_evidence(
    adapters: Sequence[object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    closed_ids, _failed_ids, details = _cleanup_adapters_with_details(adapters)
    return closed_ids, tuple(f"{item.adapter_instance_id}:{item.error_type}" for item in details)


def _cleanup_adapters_with_details(
    adapters: Sequence[object],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[CheckpointAdapterCleanupErrorV2, ...],
]:
    closed: set[int] = set()
    closed_ids: list[str] = []
    failed_ids: list[str] = []
    errors: list[CheckpointAdapterCleanupErrorV2] = []
    for adapter in reversed(adapters):
        identity = id(adapter)
        if identity in closed:
            continue
        closed.add(identity)
        instance_id = _adapter_instance_id(adapter)
        close = getattr(adapter, "close", None)
        if not callable(close):
            closed_ids.append(instance_id)
            continue
        try:
            close()
        except Exception as error:
            failed_ids.append(instance_id)
            errors.append(
                CheckpointAdapterCleanupErrorV2(
                    adapter_instance_id=instance_id,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )
        else:
            closed_ids.append(instance_id)
    return tuple(closed_ids), tuple(failed_ids), tuple(errors)


def _adapter_instance_id(adapter: object) -> str:
    direct = getattr(adapter, "instance_id", None)
    if isinstance(direct, str) and direct:
        return direct
    diagnostic = getattr(adapter, "diagnostic", None)
    if callable(diagnostic):
        with suppress(Exception):
            value = diagnostic()
            instance_id = getattr(value, "instance_id", None)
            if isinstance(instance_id, str) and instance_id:
                return instance_id
    return f"adapter-{id(adapter):016x}"


class _ResolvedDamageAdapterV2:
    """Fresh role adapter around an exact Registry-created damage binding."""

    def __init__(self, definition: CatalogResourceV2) -> None:
        self.definition = definition
        raw_scale = definition.content.get("component_damage_scale", 1.0)
        if (
            isinstance(raw_scale, bool)
            or not isinstance(raw_scale, (int, float))
            or not math.isfinite(float(raw_scale))
            or float(raw_scale) < 0.0
        ):
            raise ValueError("damage adapter scale must be finite and nonnegative")
        self.scale = float(raw_scale)
        self.calls = 0
        self.fail_on_call: int | None = None

    def magnitude(self, intent: object) -> float:
        raw_magnitude = getattr(intent, "magnitude", None)
        if (
            isinstance(raw_magnitude, bool)
            or not isinstance(raw_magnitude, (int, float))
            or not math.isfinite(float(raw_magnitude))
            or float(raw_magnitude) < 0.0
        ):
            raise ValueError("damage magnitude must be finite and nonnegative")
        self.calls += 1
        if self.fail_on_call == self.calls:
            raise RuntimeError("injected trusted damage adapter failure")
        return float(raw_magnitude) * self.scale

    def combat_snapshot(self) -> int:
        return self.calls

    def combat_restore(self, snapshot: int) -> None:
        if not isinstance(snapshot, int) or isinstance(snapshot, bool) or snapshot < 0:
            raise ValueError("damage adapter snapshot is invalid")
        self.calls = snapshot


class EntityFactoryV2:
    """Build a fresh runtime entity using only its resolved embedded bindings."""

    def __init__(
        self,
        *,
        model_registry: ModelRegistryV2,
        native_dynamics_factory: NativeDynamicsAdapterFactoryV2 | None = None,
    ) -> None:
        self._model_registry = model_registry
        self._native_dynamics_factory = native_dynamics_factory

    def build(self, definition: ResolvedEntityV2) -> EntityViewV2:
        return _entity_view(self._build_owned(definition, adapter_instances=set(), session_seed=0))

    def _build_owned(
        self,
        definition: ResolvedEntityV2,
        *,
        adapter_instances: set[int],
        session_seed: int,
        before_adapter_build: Callable[[ResolvedResourceBindingV2], None] | None = None,
        adapter_created: Callable[[object], None] | None = None,
    ) -> _RuntimeEntityV2:
        if not isinstance(definition, ResolvedEntityV2):
            raise _factory_error(
                "factory.definition_invalid",
                ("entity",),
                type(definition).__name__,
                "entity factory requires a resolved v2 entity definition",
                "compile the scenario before constructing runtime entities",
            )
        adapters: dict[str, object] = {}
        capability_tokens = capability_tokens_for_entity(definition)
        try:
            for _role, bindings in sorted(definition.resource_bindings.items()):
                for binding in sorted(bindings, key=lambda item: item.exact_ref):
                    path = ("entities", definition.id, "resource_bindings", binding.exact_ref)
                    if before_adapter_build is not None:
                        before_adapter_build(binding)
                    adapter = self._create_adapter(
                        binding,
                        entity_id=definition.id,
                        session_seed=session_seed,
                        path=path,
                    )
                    identity = id(adapter)
                    if identity in adapter_instances:
                        raise _factory_error(
                            "factory.adapter_instance_reused",
                            (*path, "adapter"),
                            binding.exact_ref,
                            "a model factory reused one mutable adapter instance",
                            "return a fresh independently owned adapter for every binding",
                        )
                    adapter_instances.add(identity)
                    adapters[binding.exact_ref] = adapter
                    if adapter_created is not None:
                        adapter_created(adapter)
        except Exception:
            _cleanup_adapters(tuple(adapters.values()))
            raise
        try:
            initial = definition.runtime_initial.initial_state
            state = _RuntimeEntityStateV2(
                position_m=[float(axis) for axis in initial.position_m],
                velocity_mps=[float(axis) for axis in initial.velocity_mps],
                heading_deg=float(initial.heading_deg),
                health=float(initial.health),
                energy=None if initial.energy is None else float(initial.energy),
                ammunition={
                    str(reference): count
                    for reference, count in definition.runtime_initial.ammunition.items()
                },
                component_states=_plain(initial.component_states),
                lifecycle="active",
                controller={"binding": definition.controller_slot},
            )
            _validate_state(state, definition.id)
            return _RuntimeEntityV2(
                definition=definition,
                state=state,
                capabilities=coarse_capabilities(capability_tokens),
                capability_tokens=capability_tokens,
                adapters=MappingProxyType(adapters),
            )
        except FactoryErrorV2:
            _cleanup_adapters(tuple(adapters.values()))
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            _cleanup_adapters(tuple(adapters.values()))
            raise _factory_error(
                "factory.definition_invalid",
                ("entities", definition.id, "runtime_initial"),
                type(error).__name__,
                "resolved runtime initial state cannot be materialized safely",
                "recompile a semantically valid immutable entity definition",
            ) from error

    def _create_adapter(
        self,
        binding: ResolvedResourceBindingV2,
        *,
        entity_id: str,
        session_seed: int,
        path: Sequence[str],
    ) -> object:
        metadata = _metadata_for(self._model_registry, binding.model_ref, path=path)
        _validate_evidence(
            metadata,
            binding.model_evidence,
            resource_type=binding.resource_type,
            path=path,
        )
        definition = CatalogResourceV2(
            schema_version="2.0",
            resource_type=binding.resource_type,
            id=binding.id,
            version=binding.version,
            engine_compatibility=binding.engine_compatibility,
            model_id=binding.model_ref,
            dependencies=binding.dependencies,
            content=_plain(binding.normalized_content),
        )
        # Core v2 DTOs freeze nested mappings.  Registry factories intentionally
        # deepcopy their input/output to guarantee session isolation, so give the
        # short-lived factory input its own ordinary mapping before that boundary.
        object.__setattr__(definition, "content", _plain(binding.normalized_content))
        try:
            adapter = self._model_registry.create(binding.model_ref, definition)
        except ModelBindingEvidenceErrorV2 as error:
            raise _factory_error(
                "factory.model_evidence_mismatch",
                (*path, "catalog_binding"),
                binding.exact_ref,
                "runtime registry is not bound to this exact resolved resource snapshot",
                "use the registry owned by the Catalog that compiled this scenario",
            ) from error
        except Exception as error:
            raise _factory_error(
                "factory.adapter_creation_failed",
                (*path, "model_ref"),
                binding.model_ref,
                "the trusted model factory rejected the embedded resolved definition",
                "verify the registered factory interface and resolved resource snapshot",
            ) from error
        # Identity factories are useful declarative adapters.  Restore their DTO
        # freeze boundary after the registry has made its isolation deepcopy.
        if isinstance(adapter, CatalogResourceV2):
            typed_adapter = CatalogResourceV2.model_validate(adapter.model_dump(mode="json"))
            if binding.resource_type == "damage_models":
                return _ResolvedDamageAdapterV2(typed_adapter)
            return typed_adapter
        if isinstance(adapter, NativeDynamicsBindingV2):
            try:
                return materialize_native_dynamics_binding_v2(
                    adapter,
                    entity_id=entity_id,
                    seed=session_seed,
                    adapter_factory=self._native_dynamics_factory,
                )
            except Exception as error:
                raise _factory_error(
                    "factory.adapter_creation_failed",
                    (*path, "native_dynamics"),
                    binding.model_ref,
                    "the exact registered native dynamics binding could not be materialized",
                    "provide a valid isolated native loader and supported resolved parameters",
                ) from error
        return adapter


def _validate_state(state: _RuntimeEntityStateV2, entity_id: str) -> None:
    if not isinstance(state.position_m, list) or not isinstance(state.velocity_mps, list):
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "kinematic"),
            type(state.position_m).__name__,
            "kinematic drafts must retain mutable vector records",
            "write three-element numeric lists through the transaction boundary",
        )
    vectors = (*state.position_m, *state.velocity_mps)
    if (
        len(state.position_m) != 3
        or len(state.velocity_mps) != 3
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in vectors
        )
    ):
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "kinematic"),
            vectors,
            "kinematic state must contain finite three-dimensional vectors",
            "write finite canonical metre and metre-per-second values",
        )
    valid_health = (
        isinstance(state.health, (int, float))
        and not isinstance(state.health, bool)
        and math.isfinite(float(state.health))
        and 0.0 <= float(state.health) <= 1.0
    )
    valid_energy = state.energy is None or (
        isinstance(state.energy, (int, float))
        and not isinstance(state.energy, bool)
        and math.isfinite(float(state.energy))
        and 0.0 <= float(state.energy) <= 1.0
    )
    valid_heading = (
        isinstance(state.heading_deg, (int, float))
        and not isinstance(state.heading_deg, bool)
        and math.isfinite(float(state.heading_deg))
        and 0.0 <= float(state.heading_deg) < 360.0
    )
    if not valid_health or not valid_energy or not valid_heading:
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "health_energy_heading"),
            (state.health, state.energy, state.heading_deg),
            "health, energy, and heading must remain finite canonical values",
            "write normalized fractions and a heading in the half-open degree interval",
        )
    if not isinstance(state.lifecycle, str) or state.lifecycle not in {
        "scheduled",
        "active",
        "degraded",
        "disabled",
        "destroyed",
        "despawned",
    }:
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "lifecycle"),
            state.lifecycle,
            "lifecycle is not a canonical runtime lifecycle value",
            "use a declared lifecycle transition through the transaction boundary",
        )
    exact_ref = re.compile(r"^[a-z][a-z0-9_.-]*@(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
    invalid_ammunition = not isinstance(state.ammunition, dict) or any(
        not isinstance(reference, str)
        or exact_ref.fullmatch(reference) is None
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        for reference, count in state.ammunition.items()
    )
    if invalid_ammunition:
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "ammunition"),
            state.ammunition,
            "ammunition requires exact resource references and nonnegative exact integers",
            "write exact id@version references with integer counts excluding booleans",
        )
    if (
        not isinstance(state.component_states, dict)
        or not isinstance(state.controller, dict)
        or not _valid_runtime_record(state.component_states)
        or not _valid_runtime_record(state.controller)
    ):
        raise _factory_error(
            "factory.state_invalid",
            ("entities", entity_id, "state", "components_controller"),
            type(state.component_states).__name__,
            "component and controller state must remain mutable record values",
            "write mapping-shaped component and controller state",
        )


def _valid_runtime_record(value: object, seen: set[int] | None = None) -> bool:
    active = set() if seen is None else seen
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in active:
            return False
        active.add(identity)
        valid = all(
            isinstance(key, str) and _valid_runtime_record(item, active)
            for key, item in value.items()
        )
        active.remove(identity)
        return valid
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            return False
        active.add(identity)
        valid = all(_valid_runtime_record(item, active) for item in value)
        active.remove(identity)
        return valid
    return False


class _WorldWriterV2:
    def __init__(self, states: dict[str, _RuntimeEntityStateV2]) -> None:
        self._states = states

    def entity(self, entity_id: str) -> _RuntimeEntityStateV2:
        try:
            return self._states[entity_id]
        except KeyError as error:
            raise _factory_error(
                "factory.entity_unknown",
                ("entities", entity_id),
                entity_id,
                "transaction target is not present in the runtime world",
                "query a current stable entity identifier before writing",
            ) from error


class _WriteTransactionV2(AbstractContextManager[_WorldWriterV2]):
    def __init__(self, world: WorldStateV2, tick: int) -> None:
        self._world = world
        self._tick = tick
        self._states: dict[str, _RuntimeEntityStateV2] = {}

    def __enter__(self) -> _WorldWriterV2:
        self._world._lock.acquire()
        if self._world._transaction_active:
            self._world._lock.release()
            raise _factory_error(
                "factory.transaction_active",
                ("world", "write_transaction"),
                self._tick,
                "one write transaction is already active for this world",
                "complete or roll back the active transaction before opening another",
            )
        if self._tick != self._world.tick:
            self._world._lock.release()
            raise _factory_error(
                "factory.tick_conflict",
                ("world", "tick"),
                self._tick,
                "transaction tick does not match the current world tick",
                "retry against the latest world snapshot tick",
            )
        self._states = {
            identifier: entity.state.clone() for identifier, entity in self._world._entities.items()
        }
        self._world._transaction_active = True
        return _WorldWriterV2(self._states)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is None:
                for identifier, state in self._states.items():
                    _validate_state(state, identifier)
                changed_lifecycle = next(
                    (
                        identifier
                        for identifier, state in self._states.items()
                        if state.lifecycle != self._world._entities[identifier].state.lifecycle
                    ),
                    None,
                )
                if changed_lifecycle is not None:
                    raise _factory_error(
                        "factory.lifecycle_write_forbidden",
                        ("entities", changed_lifecycle, "state", "lifecycle"),
                        self._states[changed_lifecycle].lifecycle,
                        "ordinary write transactions cannot mutate lifecycle authority",
                        "use advance_lifecycle with a resolved scheduled transition",
                    )
                for identifier, state in self._states.items():
                    self._world._entities[identifier].state = state
                self._world._rebuild_indexes()
        finally:
            self._world._transaction_active = False
            self._world._lock.release()


class WorldStateV2:
    """A session-owned runtime world with stable generic indexes."""

    def __init__(
        self,
        *,
        entities: Mapping[str, _RuntimeEntityV2],
        world_resource_bindings: Sequence[ResolvedResourceBindingV2],
        world_adapters: Mapping[str, object],
        factions: Sequence[FactionV2],
        relationships: Sequence[RelationshipV2],
        controller_slots: Sequence[object],
        controller_ownership: ControllerOwnershipIndexV2,
        lifecycle_schedule: Sequence[LifecycleScheduleEntryV2],
        resolved_scenario: ResolvedScenarioV2,
        resolved_events: Sequence[ResolvedEventV2],
        session_id: str,
        seed: int,
        entity_factory: EntityFactoryV2,
        controller_policy: str | None,
        resolved_hash: str,
        catalog_hash: str,
        model_registry_hash: str,
        boundary_system: BoundarySystemV2,
        geography: GeographyServiceV2,
        spatial_topology_hash: str,
    ) -> None:
        self._entities = dict(sorted(entities.items()))
        self._world_resource_bindings = tuple(world_resource_bindings)
        self._world_adapters = MappingProxyType(dict(sorted(world_adapters.items())))
        self._world_adapter_transaction_audit: list[WorldAdapterTransactionV2] = [
            WorldAdapterTransactionV2(
                created_adapter_ids=tuple(
                    _adapter_instance_id(adapter) for adapter in self._world_adapters.values()
                ),
                operation_id="world.adapters.create",
                status="created",
            )
        ]
        self._world_adapter_checkpoint_ledger: tuple[dict[str, Any], ...] = (
            {
                "operation_id": "world.adapters.materialize",
                "resource_refs": tuple(self._world_adapters),
                "status": "owned",
            },
        )
        self._mission_plugin_cleanup_errors: tuple[str, ...] = ()
        self.factions = tuple(sorted(factions, key=lambda item: item.id))
        self.relationships = tuple(
            sorted(
                relationships,
                key=lambda item: (
                    item.source_faction_id,
                    item.target_faction_id,
                    item.relation,
                ),
            )
        )
        self.controller_slots = tuple(
            sorted(controller_slots, key=lambda item: str(getattr(item, "id", item)))
        )
        self.controller_ownership = controller_ownership
        self._resolved_scenario = resolved_scenario
        self._resolved_events = tuple(resolved_events)
        self._applied_tick_event_ids: set[str] = set()
        self.lifecycle_schedule = tuple(lifecycle_schedule)
        self.session_id = session_id
        self._entity_factory = entity_factory
        self._session_seed = seed
        self._controller_policy = controller_policy
        self._resolved_hash = resolved_hash
        self._catalog_hash = catalog_hash
        self._model_registry_hash = model_registry_hash
        self._boundary_system = boundary_system
        self._geography = geography
        self._spatial_topology_hash = spatial_topology_hash
        self.tick = 0
        self._spatial_tick = 0
        self._spatial_time_seconds = 0.0
        self._last_spatial_tick_start_seconds = 0.0
        # The session seed is public simulation state, not a security secret.
        self.rng = random.Random(seed)  # nosec B311
        self._lock = RLock()
        self._transaction_active = False
        self._tick_failure_operation_id: str | None = None
        self._closed = False
        self._applied_lifecycle_event_ids: set[str] = set()
        self._used_entity_ids: set[str] = set(self._entities)
        self._lifecycle_ledger: dict[str, LifecycleReceiptV2] = {}
        self._motion_ledger: dict[str, MotionReceiptV2] = {}
        self._motion_operation_fingerprints: dict[str, str] = {}
        self._world_tick_ledger: dict[str, tuple[str, WorldTickReceiptV2]] = {}
        # This is a derived lookup index, not an additional authority ledger.
        # The complete ordered World tick ledger remains the sole durable audit
        # source and is serialized in checkpoints.  Event scoring often
        # authenticates a receipt while the match is long-running; scanning
        # every prior tick for that receipt makes this path grow with history.
        self._typed_event_receipt_index: dict[str, tuple[TypedEventExecutionReceiptV2, ...]] = {}
        self._consumed_provider_receipts: set[str] = set()
        self._active_motion_provider_receipt: str | None = None
        self._active_typed_event_receipts: tuple[TypedEventExecutionReceiptV2, ...] = ()
        self._combat_ledger: dict[str, tuple[str, Any]] = {}
        self._combat_engagement_ledger: dict[str, Any] = {}
        self._combat_rng_state: list[str] = []
        self._combat_cooldowns: dict[str, int] = {}
        self._combat_hit_model_state: dict[str, object] = {}
        self._combat_system: Any | None = None
        self._missile_flights: dict[str, MissileFlightV2] = {}
        self._missile_terminal_receipts: dict[str, MissileTerminalReceiptV2] = {}
        self._pending_impacts: dict[str, Any] = {}
        self._pending_impact_receipts: dict[str, Any] = {}
        self._combat_component_health: dict[str, float] = {
            f"{entity_id}|{binding.exact_ref}": 1.0
            for entity_id, entity in self._entities.items()
            for role in ("sensors", "communications", "weapons")
            for binding in entity.definition.resource_bindings.get(role, ())
        }
        self.component_damage_profiles = build_component_damage_profiles_v2(
            (
                *tuple(entity.definition for entity in self._entities.values()),
                *tuple(
                    entry.blueprint
                    for entry in self.lifecycle_schedule
                    if entry.event_type == "spawn" and entry.blueprint is not None
                ),
            )
        )
        self._zone_activation: dict[str, bool] = {
            item.zone_id: True
            for item in (
                *getattr(boundary_system, "_allowed_zones", ()),
                *getattr(boundary_system, "_excluded_zones", ()),
            )
        }
        self._zone_activation.update({zone.id: True for zone in resolved_scenario.world.zones})
        self._zone_activation_ledger: dict[str, ZoneActivationReceiptV2] = {}
        self._weather_state: dict[str, Any] = {}
        self._jamming_sessions: dict[str, Any] = {}
        self._message_queue: list[Mapping[str, Any]] = []
        self._shared_contact_queue: list[Mapping[str, Any]] = []
        self._shared_contacts_by_controller: dict[str, dict[str, Mapping[str, Any]]] = {}
        self._command_queue: list[Mapping[str, Any]] = []
        self._controller_inboxes: dict[str, dict[str, Mapping[str, Any]]] = {}
        self._inbox_evictions: list[Mapping[str, Any]] = []
        self._component_suppressions: dict[str, Any] = {}
        self._initialise_tick_zero_capability_events()
        self._mission_marker_ledger: dict[str, Any] = {}
        self._mission_zone_membership: dict[str, set[str]] = {
            entity_id: {
                zone.id
                for zone in resolved_scenario.world.zones
                if self._mission_zone_contains(zone, tuple(entity.state.position_m))
            }
            for entity_id, entity in self._entities.items()
        }
        self._mission_zone_transitions: list[Any] = []
        self._effect_application_ledger: dict[str, Any] = {}
        self._spatial_effect_triggers: dict[str, Mapping[str, Any]] = {}
        self._spatial_effect_trigger_ledger: dict[str, Mapping[str, Any]] = {}
        self._spatial_effect_trigger_consumption: dict[str, Mapping[str, Any]] = {}
        self._destroyed_lifecycle_ledger: dict[str, Mapping[str, Any]] = {}
        for event in self._resolved_events:
            if event.event_type == "spatial_effect_trigger":
                self._arm_spatial_effect_trigger(event)
        self._tombstones: dict[str, LifecycleTombstoneV2] = {}
        self._lifecycle_audit: list[LifecycleAuditRecordV2] = []
        self._deferred_lifecycle_despawns: (
            list[tuple[LifecycleScheduleEntryV2, _RuntimeEntityV2]] | None
        ) = None
        self._checkpoint_restore_audit: tuple[CheckpointRestoreAuditV2, ...] = ()
        self._checkpoint_native_identity_overrides: dict[
            tuple[str, str], tuple[str, str | None]
        ] = {}
        # Exact capability evidence is derived from immutable compiled
        # definitions.  Keep it separate from ``entity.capability_tokens``,
        # whose runtime value may legitimately change after component damage.
        # Lifecycle refreshes occur on combat ticks, so recompiling this
        # static evidence for every active entity would add avoidable work to
        # the fixed-step path.
        self._compiled_capability_tokens: dict[str, tuple[CapabilityTokenV2, ...]] = {
            entity_id: capability_tokens_for_entity(entity.definition)
            for entity_id, entity in self._entities.items()
        }

        self.lifecycle_fault_injector = LifecycleFaultInjectorV2()
        self._indexes: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType({})
        self.capability_index = build_capability_index(
            {entity_id: entity.capability_tokens for entity_id, entity in self._entities.items()}
        )
        self._rebuild_indexes()
        self._refresh_controller_ownership()
        self.authority_tokens = build_world_authority_grants_v2(
            entity_factions={
                entity_id: entity.faction_id for entity_id, entity in self._entities.items()
            },
            controller_ownership=self.controller_ownership,
        )
        self.contact_store = WorldContactStoreV2(())
        self.roe_rules: Mapping[str, WorldRoeRuleV2] = MappingProxyType({})
        self._spatial_effect_policy = resolved_scenario.spatial_effect_policy
        from openmdbench.missions.engine_v2 import MissionEngineV2

        self._mission_engine = MissionEngineV2.from_resolved(
            resolved=resolved_scenario,
            world=self,
            expected_resolved_hash=resolved_scenario.resolved_hash,
        )

    @property
    def spatial_effect_policy(self) -> ResolvedSpatialEffectPolicyV2 | None:
        return self._spatial_effect_policy

    def install_combat_system(self, combat_system: Any) -> None:
        """Bind one exact session-local Combat authority to this World."""

        with self._lock:
            if self._closed or self._transaction_active:
                raise ValueError("World combat authority must be bound while World is available")
            if (
                getattr(combat_system, "world", None) is not self
                or getattr(combat_system, "resolved_hash", None) != self._resolved_hash
                or getattr(combat_system, "catalog_hash", None) != self._catalog_hash
                or getattr(combat_system, "model_registry_hash", None) != self._model_registry_hash
                or self._combat_system is not None
            ):
                raise ValueError("World combat authority differs from runtime trust anchors")
            self._combat_system = combat_system
            resolver = getattr(combat_system, "set_capability_resolver", None)
            if callable(resolver):
                resolver(
                    lambda entity_id, capability, base_value, tick, component_ref: (
                        self._resolve_entity_capability(
                            entity=self._entities[entity_id],
                            capability=capability,
                            base_value=base_value,
                            tick=tick,
                            component_ref=component_ref,
                        )
                    )
                )

    def combat_inventory_snapshot(self) -> CombatInventorySnapshotV2:
        bindings = {binding.exact_ref: binding for binding in self._world_resource_bindings}
        entity_bindings = {
            binding.exact_ref: binding
            for entity in self._entities.values()
            for role in ("effects", "damage_models")
            for binding in entity.definition.resource_bindings.get(role, ())
        }
        bindings.update(entity_bindings)
        diagnostics = {
            reference: _adapter_diagnostic(
                reference,
                adapter,
                bindings[reference],
                owner_id="world",
                adapters_closed=self._closed,
            )
            for reference, adapter in self._world_adapters.items()
        }
        return CombatInventorySnapshotV2(
            entity_ids=tuple(sorted(self._entities)),
            effect_refs=tuple(
                sorted(
                    reference
                    for reference, binding in bindings.items()
                    if binding.resource_type == "effects"
                )
            ),
            damage_model_refs=tuple(
                sorted(
                    reference
                    for reference, binding in bindings.items()
                    if binding.resource_type == "damage_models"
                )
            ),
            adapter_diagnostics=MappingProxyType(diagnostics),
        )

    @property
    def world_adapter_diagnostics(self) -> Mapping[str, AdapterDiagnosticV2]:
        bindings = {item.exact_ref: item for item in self._world_resource_bindings}
        return MappingProxyType(
            {
                reference: _adapter_diagnostic(
                    reference,
                    adapter,
                    bindings[reference],
                    owner_id="world",
                    adapters_closed=self._closed,
                )
                for reference, adapter in self._world_adapters.items()
            }
        )

    @property
    def world_adapter_transaction_audit(self) -> tuple[WorldAdapterTransactionV2, ...]:
        return tuple(self._world_adapter_transaction_audit)

    @property
    def mission_plugin_cleanup_errors(self) -> tuple[str, ...]:
        return self._mission_plugin_cleanup_errors

    def snapshot_world_adapters(self) -> tuple[dict[str, Any], ...]:
        snapshots: list[dict[str, Any]] = []
        bindings = {item.exact_ref: item for item in self._world_resource_bindings}
        for reference, adapter in self._world_adapters.items():
            snapshot = getattr(adapter, "combat_snapshot", None)
            state = _plain(snapshot()) if callable(snapshot) else None
            binding = bindings[reference]
            payload = {
                "resource_ref": reference,
                "model_ref": binding.model_ref,
                "content_hash": binding.content_hash,
                "state": state,
                "state_protocol": "combat" if callable(snapshot) else "stateless",
            }
            payload["snapshot_hash"] = _canonical_evidence_hash(payload)
            snapshots.append(payload)
        return tuple(snapshots)

    def _world_adapter_receipts(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "resource_ref": binding.exact_ref,
                "model_ref": binding.model_ref,
                "content_hash": binding.content_hash,
                "artifact_hash": binding.model_evidence.artifact_sha256,
            }
            for binding in self._world_resource_bindings
        )

    def restore_world_adapters_reverse(
        self,
        snapshots: Sequence[Mapping[str, Any]],
        *,
        operation_id: str,
    ) -> WorldAdapterTransactionV2:
        expected = {str(item["resource_ref"]): item for item in snapshots}
        if set(expected) != set(self._world_adapters):
            raise ValueError("World adapter snapshot closure differs from active adapters")
        binding_index = {item.exact_ref: item for item in self._world_resource_bindings}
        restored: list[str] = []
        failed: list[str] = []
        errors: list[CheckpointAdapterCleanupErrorV2] = []
        for reference, adapter in reversed(tuple(self._world_adapters.items())):
            item = expected[reference]
            binding = binding_index[reference]
            if (
                item.get("model_ref") != binding.model_ref
                or item.get("content_hash") != binding.content_hash
                or item.get("state_protocol") not in {"combat", "stateless"}
                or (item.get("state_protocol") == "stateless" and item.get("state") is not None)
            ):
                raise ValueError("World adapter snapshot identity differs from Resolved")
            unhashed = dict(item)
            supplied_hash = unhashed.pop("snapshot_hash", None)
            if supplied_hash != _canonical_evidence_hash(unhashed):
                raise ValueError("World adapter snapshot hash mismatch")
            if item.get("state_protocol") == "combat":
                restore = getattr(adapter, "combat_restore", None)
                if not callable(restore):
                    raise ValueError("World adapter restore protocol is absent")
                instance_id = _adapter_instance_id(adapter)
                try:
                    restore(item.get("state"))
                except Exception as error:
                    failed.append(instance_id)
                    errors.append(
                        CheckpointAdapterCleanupErrorV2(
                            adapter_instance_id=instance_id,
                            error_type=type(error).__name__,
                            message=str(error),
                        )
                    )
                else:
                    restored.append(instance_id)
        transaction = WorldAdapterTransactionV2(
            restored_adapter_ids=tuple(restored),
            failed_adapter_ids=tuple(failed),
            cleanup_errors=tuple(errors),
            operation_id=operation_id,
            status="restored" if not errors else "restore_failed",
        )
        self._world_adapter_transaction_audit.append(transaction)
        if errors:
            raise ValueError("one or more World adapters failed reverse restore")
        return transaction

    def event_state_snapshot(self) -> WorldEventStateSnapshotV2:
        return WorldEventStateSnapshotV2(
            weather_state=_plain(self._weather_state),
            jamming_sessions=_plain(self._jamming_sessions),
            message_queue=tuple(cast(dict[str, Any], _plain(item)) for item in self._message_queue),
            shared_contact_queue=tuple(
                cast(dict[str, Any], _plain(item)) for item in self._shared_contact_queue
            ),
            shared_contacts_by_controller=_plain(self._shared_contacts_by_controller),
            command_queue=tuple(cast(dict[str, Any], _plain(item)) for item in self._command_queue),
            controller_inboxes=_plain(self._controller_inboxes),
            inbox_evictions=tuple(
                cast(dict[str, Any], _plain(item)) for item in self._inbox_evictions
            ),
            component_suppressions=_plain(self._component_suppressions),
            mission_marker_ledger=_plain(self._mission_marker_ledger),
            zone_activation_state=dict(sorted(self._zone_activation.items())),
            effect_application_ledger=_plain(self._effect_application_ledger),
            spatial_effect_triggers=_plain(self._spatial_effect_triggers),
            spatial_effect_trigger_ledger=_plain(self._spatial_effect_trigger_ledger),
            spatial_effect_trigger_consumption=_plain(self._spatial_effect_trigger_consumption),
            destroyed_lifecycle_ledger=_plain(self._destroyed_lifecycle_ledger),
        )

    def presentation_snapshot(self) -> WorldPresentationSnapshotV2:
        """Freeze current display data without serialising World history.

        This is deliberately not a recovery checkpoint.  It contains the
        current tick's events plus the small set of live fields needed by rich
        replay frames, while the complete authoritative receipt ledger remains
        in memory until the match has ended.
        """

        with self._lock:
            latest = (
                None
                if not self._world_tick_ledger
                else next(reversed(self._world_tick_ledger.values()))[1]
            )
            latest_record = (
                ()
                if latest is None
                else (
                    WorldPresentationTickReceiptV2(
                        event_receipts=tuple(
                            cast(Mapping[str, Any], _plain(item)) for item in latest.event_receipts
                        ),
                        combat_receipts=tuple(
                            cast(Mapping[str, Any], _plain(item)) for item in latest.combat_receipts
                        ),
                        damage_receipts=tuple(
                            cast(Mapping[str, Any], _plain(item)) for item in latest.damage_receipts
                        ),
                    ),
                )
            )
            contact_evidence = tuple(
                CheckpointContactEvidenceV2(
                    schema_version=record.schema_version,
                    evidence_id=record.evidence_id,
                    owner_entity_id=record.owner_entity_id,
                    target_entity_id=record.target_entity_id,
                    observed_tick=record.observed_tick,
                    age_ticks=max(record.age_ticks, self.tick - record.observed_tick),
                    max_age_ticks=record.max_age_ticks,
                    confidence=record.confidence,
                    minimum_confidence=record.minimum_confidence,
                    quality=record.quality,
                    measurement_position_m=record.measurement_position_m,
                    confirmation_count=record.confirmation_count,
                    confirmation_frames=record.confirmation_frames,
                    stale_after_ticks=record.stale_after_ticks,
                    confirmed=record.confirmed,
                    source_sensor_ref=record.source_sensor_ref,
                )
                for evidence_id in sorted(self.contact_store.records)
                for record in self.contact_store.records[evidence_id]
            )
            return WorldPresentationSnapshotV2(
                tick=self.tick,
                spatial_clock=CheckpointSpatialClockV2(
                    tick=self._spatial_tick,
                    tick_start_time_seconds=self._last_spatial_tick_start_seconds,
                    next_tick_time_seconds=self._spatial_time_seconds,
                ),
                missile_flights=tuple(
                    self._missile_flights[key] for key in sorted(self._missile_flights)
                ),
                zone_activation_state=MappingProxyType(dict(sorted(self._zone_activation.items()))),
                world_tick_ledger=latest_record,
                mission_scoring_checkpoint=self._mission_engine.presentation_snapshot(),
                event_state=self.event_state_snapshot(),
                combat_contact_evidence=contact_evidence,
            )

    def authoritative_typed_event_receipt(self, event_receipt: Any) -> TypedEventExecutionReceiptV2:
        """Return the matching World-owned receipt or reject caller-created evidence."""

        if isinstance(event_receipt, (TypedEventExecutionReceiptV2, Mapping)):
            supplied = _plain(event_receipt)
        else:
            raise TypeError("event scoring requires TypedEventExecutionReceiptV2")
        active_authoritative = next(
            (item for item in self._active_typed_event_receipts if _plain(item) == supplied),
            None,
        )
        indexed_candidates = self._typed_event_receipt_index.get(
            _canonical_evidence_hash(supplied), ()
        )
        authoritative = (
            active_authoritative
            if active_authoritative is not None
            else next((item for item in indexed_candidates if _plain(item) == supplied), None)
        )
        resolved_event = next(
            (item for item in self._resolved_events if item.id == supplied.get("event_id")),
            None,
        )
        resolved_payload = None if resolved_event is None else _plain(resolved_event.payload.values)
        trigger_tick = (
            None if resolved_event is None else getattr(resolved_event.trigger, "tick", None)
        )
        if (
            authoritative is None
            or resolved_event is None
            or supplied.get("event_type") != resolved_event.event_type
            or (
                resolved_event.event_type != "spatial_effect_trigger"
                and supplied.get("tick") != trigger_tick
            )
            or (
                resolved_event.event_type == "spatial_effect_trigger"
                and (
                    not isinstance(supplied.get("tick"), int)
                    or isinstance(supplied.get("tick"), bool)
                    or not isinstance(trigger_tick, int)
                    or supplied["tick"] < trigger_tick
                )
            )
            or supplied.get("payload") != resolved_payload
            or supplied.get("payload_hash") != _canonical_evidence_hash(supplied.get("payload"))
            or supplied.get("event_id") not in self._applied_tick_event_ids
        ):
            raise ValueError("typed event receipt is not authoritative World evidence")
        return authoritative

    def _index_typed_event_receipts(self, event_receipts: Sequence[WorldEventReceiptV2]) -> None:
        """Index durable typed receipts after their World tick is committed.

        The index is intentionally reconstructible from ``_world_tick_ledger``
        and is never used as a checkpoint or log source.  Tuple buckets retain
        the prior value-equality behaviour in the cryptographically unlikely
        event of a canonical-hash collision.
        """

        for world_receipt in event_receipts:
            for typed_receipt in world_receipt.typed_event_receipts:
                key = _canonical_evidence_hash(_plain(typed_receipt))
                self._typed_event_receipt_index[key] = (
                    *self._typed_event_receipt_index.get(key, ()),
                    typed_receipt,
                )

    @staticmethod
    def _mission_zone_contains(zone: Any, position: tuple[float, ...]) -> bool:
        geometry = getattr(zone, "geometry", None)
        geometry_type = (
            getattr(geometry, "type", None)
            if geometry is not None
            else getattr(zone, "geometry_type", None)
        )
        points = (
            getattr(geometry, "positions_m", ())
            if geometry is not None
            else getattr(zone, "coordinates_m", ())
        )
        if geometry_type == "circle":
            center = getattr(geometry, "center_m", None)
            radius = getattr(geometry, "radius_m", None)
            return bool(
                center is not None
                and radius is not None
                and (position[0] - center[0]) ** 2 + (position[1] - center[1]) ** 2
                <= float(radius) ** 2 + 1e-12
            )
        if geometry_type != "polygon" or len(points) < 3:
            return False
        inside = False
        x, y = position[:2]
        for index, first in enumerate(points):
            second = points[(index + 1) % len(points)]
            x1, y1 = first[:2]
            x2, y2 = second[:2]
            cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
            if (
                abs(cross) <= 1e-9
                and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9
                and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9
            ):
                return True
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
        return inside

    @staticmethod
    def _mission_zone_crossings(
        zone: Any, start: tuple[float, ...], end: tuple[float, ...]
    ) -> tuple[float, ...]:
        geometry = getattr(zone, "geometry", None)
        geometry_type = (
            getattr(geometry, "type", None)
            if geometry is not None
            else getattr(zone, "geometry_type", None)
        )
        dx, dy = end[0] - start[0], end[1] - start[1]
        fractions: list[float] = []
        if geometry_type == "circle":
            center = getattr(geometry, "center_m", None)
            radius = getattr(geometry, "radius_m", None)
            if center is None or radius is None:
                return ()
            ox, oy = start[0] - center[0], start[1] - center[1]
            a = dx * dx + dy * dy
            if a <= 1e-18:
                return ()
            b = 2.0 * (ox * dx + oy * dy)
            c = ox * ox + oy * oy - float(radius) ** 2
            discriminant = b * b - 4.0 * a * c
            if discriminant >= 0.0:
                root = math.sqrt(max(0.0, discriminant))
                fractions.extend(((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)))
        elif geometry_type == "polygon":
            points = (
                getattr(geometry, "positions_m", ())
                if geometry is not None
                else getattr(zone, "coordinates_m", ())
            )
            for index, first in enumerate(points):
                second = points[(index + 1) % len(points)]
                ex, ey = second[0] - first[0], second[1] - first[1]
                denominator = dx * ey - dy * ex
                if abs(denominator) <= 1e-15:
                    continue
                qx, qy = first[0] - start[0], first[1] - start[1]
                time = (qx * ey - qy * ex) / denominator
                edge = (qx * dy - qy * dx) / denominator
                if -1e-12 <= time <= 1.0 + 1e-12 and -1e-12 <= edge <= 1.0 + 1e-12:
                    fractions.append(min(1.0, max(0.0, time)))
        return tuple(
            value
            for index, value in enumerate(sorted(fractions))
            if index == 0 or abs(value - sorted(fractions)[index - 1]) > 1e-9
        )

    def _record_mission_zone_transitions(
        self,
        receipt: MotionReceiptV2,
        prior_positions: Mapping[str, tuple[float, ...]],
    ) -> None:
        from openmdbench.missions.engine_v2 import ZoneTransitionEvidenceV2

        zones = tuple(sorted(self._resolved_scenario.world.zones, key=lambda item: item.id))
        for entity_id, start in sorted(prior_positions.items()):
            entity = self._entities.get(entity_id)
            if entity is None:
                continue
            end = tuple(entity.state.position_m)
            membership = self._mission_zone_membership.setdefault(entity_id, set())
            for zone in zones:
                was_inside = self._mission_zone_contains(zone, start)
                is_inside = self._mission_zone_contains(zone, end)
                crossings = self._mission_zone_crossings(zone, start, end)
                transition_values: list[tuple[str, float]] = []
                for fraction in crossings:
                    delta = 1e-7
                    before_time = max(0.0, fraction - delta)
                    after_time = min(1.0, fraction + delta)
                    before = tuple(
                        start[index] + (end[index] - start[index]) * before_time
                        for index in range(3)
                    )
                    after = tuple(
                        start[index] + (end[index] - start[index]) * after_time
                        for index in range(3)
                    )
                    before_inside = self._mission_zone_contains(zone, before)
                    after_inside = self._mission_zone_contains(zone, after)
                    if before_inside != after_inside:
                        transition_values.append(("entered" if after_inside else "left", fraction))
                if not transition_values and was_inside != is_inside:
                    transition_values.append(("entered" if is_inside else "left", 1.0))
                if is_inside:
                    membership.add(zone.id)
                else:
                    membership.discard(zone.id)
                for transition, fraction in transition_values:
                    evidence_payload = {
                        "entity_id": entity_id,
                        "zone_id": zone.id,
                        "transition": transition,
                        "tick": receipt.tick,
                        "time_fraction": fraction,
                    }
                    self._mission_zone_transitions.append(
                        ZoneTransitionEvidenceV2(
                            entity_id=entity_id,
                            zone_id=zone.id,
                            transition=cast(Literal["entered", "left"], transition),
                            tick=receipt.tick,
                            time_fraction=fraction,
                            evidence_hash=_canonical_evidence_hash(evidence_payload),
                        )
                    )

    def mission_fact_snapshot(self, *, tick: int, include_event_receipts: bool = True) -> Any:
        """Return the sole immutable World-owned mission fact boundary.

        Historical typed-event receipts are audit evidence, not inputs to the
        built-in mission condition operators.  The durable/public fact view
        retains them by default; a rule-only tick can opt out and avoid
        repeatedly freezing the complete event history.
        """

        if not isinstance(include_event_receipts, bool):
            raise TypeError("include_event_receipts must be boolean")

        from openmdbench.missions.engine_v2 import (
            EntitySelectionEvidenceV2,
            MissionContactFactV2,
            MissionFactSnapshotV2,
            MissionResourceFactV2,
        )

        views = self.snapshot().entities
        selection: list[EntitySelectionEvidenceV2] = []
        for view in views:
            claims = self.controller_ownership.by_entity(view.id)
            direct = tuple(
                sorted({token.role for token in view.capability_tokens if token.origin == "direct"})
            )
            dependency = tuple(
                sorted(
                    {token.role for token in view.capability_tokens if token.origin == "dependency"}
                )
            )
            selection.append(
                EntitySelectionEvidenceV2(
                    entity_id=view.id,
                    faction_id=view.faction_id,
                    platform_ref=view.definition.platform_ref,
                    domain=view.domain,
                    controller_id=(None if not claims else claims[0].controller_id),
                    tags=view.tags,
                    direct_capabilities=direct,
                    dependency_capabilities=dependency,
                    lifecycle=cast(
                        Literal[
                            "scheduled",
                            "active",
                            "degraded",
                            "disabled",
                            "destroyed",
                            "despawned",
                        ],
                        view.state.lifecycle,
                    ),
                )
            )
        active_ids = {item.id for item in views}
        for entry in self.lifecycle_schedule:
            blueprint = entry.blueprint
            if (
                entry.event_type != "spawn"
                or entry.source_event_id in self._applied_lifecycle_event_ids
                or blueprint is None
                or blueprint.id in active_ids
            ):
                continue
            tokens = capability_tokens_for_entity(blueprint)
            reservation = self.controller_ownership.by_reserved_entity(blueprint.id)
            reservation_claim = (
                None
                if reservation is None
                else self.controller_ownership.slot_to_claim.get(reservation.controller_binding)
            )
            selection.append(
                EntitySelectionEvidenceV2(
                    entity_id=blueprint.id,
                    faction_id=blueprint.faction_id,
                    platform_ref=blueprint.platform_ref,
                    domain=blueprint.domain,
                    controller_id=(
                        None if reservation_claim is None else reservation_claim.controller_id
                    ),
                    tags=blueprint.tags,
                    direct_capabilities=tuple(
                        token.role for token in tokens if token.origin == "direct"
                    ),
                    dependency_capabilities=tuple(
                        token.role for token in tokens if token.origin == "dependency"
                    ),
                    lifecycle="scheduled",
                )
            )
        entity_states = {
            item.id: MappingProxyType(
                {
                    "lifecycle": item.state.lifecycle,
                    "health": item.state.health,
                    "faction_id": item.faction_id,
                }
            )
            for item in views
        }
        zone_membership = {
            key: tuple(sorted(value))
            for key, value in sorted(self._mission_zone_membership.items())
        }
        contact_targets: dict[str, set[str]] = {}
        for records in self.contact_store.records.values():
            for record in records:
                contact_targets.setdefault(record.owner_entity_id, set()).add(
                    record.target_entity_id
                )
        contacts = {key: tuple(sorted(values)) for key, values in sorted(contact_targets.items())}
        contact_facts = tuple(
            MissionContactFactV2(
                evidence_id=record.evidence_id,
                owner_entity_id=record.owner_entity_id,
                target_entity_id=record.target_entity_id,
                observed_tick=record.observed_tick,
                max_age_ticks=record.max_age_ticks,
                confidence=record.confidence,
                minimum_confidence=record.minimum_confidence,
                selector_id=f"contact.owner.{record.owner_entity_id}",
            )
            for _evidence_id, records in sorted(self.contact_store.records.items())
            for record in sorted(records, key=lambda item: item.evidence_id)
        )
        resources: dict[str, Mapping[str, float]] = {}
        for item in views:
            values = {key: float(value) for key, value in item.state.ammunition.items()}
            if item.state.energy is not None:
                for binding in item.definition.resource_bindings.get("energy", ()):
                    values[binding.exact_ref] = float(item.state.energy)
            resources[item.id] = MappingProxyType(dict(sorted(values.items())))
        resource_facts: list[MissionResourceFactV2] = []
        for item in views:
            resource_facts.append(
                MissionResourceFactV2(
                    entity_id=item.id,
                    field="health",
                    value=float(item.state.health),
                    unit="1",
                )
            )
            if item.state.energy is not None:
                energy_bindings = item.definition.resource_bindings.get("energy", ())
                resource_facts.append(
                    MissionResourceFactV2(
                        entity_id=item.id,
                        resource_ref=(
                            None if not energy_bindings else energy_bindings[0].exact_ref
                        ),
                        field="energy",
                        value=float(item.state.energy),
                        unit="1",
                    )
                )
            for reference, count in sorted(item.state.ammunition.items()):
                resource_facts.append(
                    MissionResourceFactV2(
                        entity_id=item.id,
                        resource_ref=reference,
                        field="ammunition",
                        value=float(count),
                        unit="round",
                    )
                )
            for role, bindings in sorted(item.definition.resource_bindings.items()):
                singular_role = role[:-1] if role.endswith("s") else role
                for binding in bindings:
                    component_key = f"{item.id}|{binding.exact_ref}"
                    if component_key not in self._combat_component_health:
                        continue
                    resource_facts.append(
                        MissionResourceFactV2(
                            entity_id=item.id,
                            resource_ref=binding.exact_ref,
                            field=f"component.{singular_role}.health",
                            value=float(self._combat_component_health[component_key]),
                            unit="1",
                        )
                    )
        wave_lifecycle = {
            entry.source_event_id: (
                "applied"
                if entry.source_event_id in self._applied_lifecycle_event_ids
                else "scheduled"
            )
            for entry in self.lifecycle_schedule
        }
        event_receipts = (
            tuple(
                _frozen_mapping(cast(Mapping[str, Any], _plain(event_receipt)))
                for _operation_id, (_fingerprint, tick_receipt) in sorted(
                    self._world_tick_ledger.items(),
                    key=lambda item: (
                        item[1][1].start_tick,
                        item[1][1].tick,
                        item[0],
                    ),
                )
                for event_receipt in tick_receipt.event_receipts
                if tick_receipt.start_tick <= tick
            )
            if include_event_receipts
            else ()
        )
        event_ids = tuple(sorted(self._applied_tick_event_ids))
        payload = {
            "tick": tick,
            "entity_states": entity_states,
            "zone_membership": zone_membership,
            "zone_transitions": self._mission_zone_transitions,
            "event_ids": event_ids,
            "contacts": contacts,
            "communications": tuple(self._message_queue),
            "wave_lifecycle": wave_lifecycle,
            "resources": resources,
            "event_receipts": event_receipts,
            "selection_evidence": selection,
            "contact_facts": contact_facts,
            "resource_facts": resource_facts,
            "zone_activation": self._zone_activation,
        }
        return MissionFactSnapshotV2(
            tick=tick,
            entity_states=MappingProxyType(entity_states),
            zone_membership=MappingProxyType(zone_membership),
            zone_transitions=tuple(self._mission_zone_transitions),
            event_ids=event_ids,
            contacts=MappingProxyType(contacts),
            communications=tuple(self._message_queue),
            wave_lifecycle=MappingProxyType(dict(sorted(wave_lifecycle.items()))),
            resources=MappingProxyType(resources),
            event_receipts=event_receipts,
            selection_evidence=tuple(sorted(selection, key=lambda item: item.entity_id)),
            contact_facts=contact_facts,
            resource_facts=tuple(
                sorted(
                    resource_facts,
                    key=lambda item: (
                        item.entity_id,
                        item.field,
                        item.resource_ref or "",
                    ),
                )
            ),
            zone_activation=MappingProxyType(dict(sorted(self._zone_activation.items()))),
            fact_hash=_canonical_evidence_hash(payload),
        )

    def _restore_event_state(self, snapshot: WorldEventStateSnapshotV2) -> None:
        self._weather_state = dict(_plain(snapshot.weather_state))
        self._jamming_sessions = dict(_plain(snapshot.jamming_sessions))
        self._message_queue = [
            _frozen_mapping(cast(Mapping[str, Any], item))
            for item in _plain(snapshot.message_queue)
        ]
        self._shared_contact_queue = [
            _frozen_mapping(cast(Mapping[str, Any], item))
            for item in _plain(snapshot.shared_contact_queue)
        ]
        shared_contacts = _plain(snapshot.shared_contacts_by_controller)
        if not isinstance(shared_contacts, Mapping):
            raise ValueError("checkpoint shared contact store is invalid")
        self._shared_contacts_by_controller = {
            str(slot_id): {
                str(contact_id): _frozen_mapping(cast(Mapping[str, Any], contact))
                for contact_id, contact in records.items()
            }
            for slot_id, records in shared_contacts.items()
            if isinstance(records, Mapping)
        }
        if len(self._shared_contacts_by_controller) != len(shared_contacts):
            raise ValueError("checkpoint shared contact records are invalid")
        self._command_queue = [
            _frozen_mapping(cast(Mapping[str, Any], item))
            for item in _plain(snapshot.command_queue)
        ]
        inboxes = _plain(snapshot.controller_inboxes)
        if not isinstance(inboxes, Mapping):
            raise ValueError("checkpoint controller inboxes are invalid")
        self._controller_inboxes = {
            str(slot_id): {
                str(message_id): _frozen_mapping(cast(Mapping[str, Any], message))
                for message_id, message in messages.items()
            }
            for slot_id, messages in inboxes.items()
            if isinstance(messages, Mapping)
        }
        if len(self._controller_inboxes) != len(inboxes):
            raise ValueError("checkpoint controller inbox records are invalid")
        self._inbox_evictions = [
            _frozen_mapping(cast(Mapping[str, Any], item))
            for item in _plain(snapshot.inbox_evictions)
        ]
        self._component_suppressions = dict(_plain(snapshot.component_suppressions))
        self._mission_marker_ledger = dict(_plain(snapshot.mission_marker_ledger))
        self._zone_activation = dict(snapshot.zone_activation_state)
        self._effect_application_ledger = dict(_plain(snapshot.effect_application_ledger))
        self._spatial_effect_triggers = {
            str(key): _frozen_mapping(cast(Mapping[str, Any], value))
            for key, value in _plain(snapshot.spatial_effect_triggers).items()
        }
        self._spatial_effect_trigger_ledger = {
            str(key): _frozen_mapping(cast(Mapping[str, Any], value))
            for key, value in _plain(snapshot.spatial_effect_trigger_ledger).items()
        }
        self._spatial_effect_trigger_consumption = {
            str(key): _frozen_mapping(cast(Mapping[str, Any], value))
            for key, value in _plain(snapshot.spatial_effect_trigger_consumption).items()
        }
        self._destroyed_lifecycle_ledger = {
            str(key): _frozen_mapping(cast(Mapping[str, Any], value))
            for key, value in _plain(snapshot.destroyed_lifecycle_ledger).items()
        }

    def _rebuild_spatial_runtime_after_lifecycle(self) -> None:
        """Rebuild active collision topology after an atomic lifecycle change."""

        boundary_system, topology_hash, geography = _spatial_runtime(
            self._resolved_scenario,
            tuple(entity.definition for entity in self._entities.values()),
        )
        for zone_id, active in sorted(self._zone_activation.items()):
            if zone_id not in getattr(boundary_system, "_zone_activation", {}):
                continue
            boundary_system.set_zone_activation(
                zone_id=zone_id,
                active=active,
                tick=self._spatial_tick,
                operation_id=f"lifecycle-topology:{self._spatial_tick}:{zone_id}",
            )
        self._boundary_system = boundary_system
        self._geography = geography
        self._spatial_topology_hash = topology_hash

    def install_contact_evidence(self, evidence: WorldContactEvidenceV2) -> None:
        """Install one explicit typed contact observation under the World writer lock."""

        if type(evidence) is not WorldContactEvidenceV2:
            raise TypeError("World contact installation requires exact typed evidence")
        with self._lock:
            if self._closed or self._transaction_active:
                raise ValueError("World cannot install contact evidence while unavailable")
            if (
                evidence.owner_entity_id not in self._entities
                or evidence.target_entity_id not in self._entities
                or evidence.observed_tick > self.tick
                or evidence.age_ticks < self.tick - evidence.observed_tick
            ):
                raise ValueError("World contact evidence differs from authoritative state")
            self.contact_store.install(evidence)

    def install_roe_policy(self, policy: WorldRoeRuleV2) -> None:
        """Install one explicit typed ROE policy under the World writer lock."""

        if type(policy) is not WorldRoeRuleV2:
            raise TypeError("World ROE installation requires an exact typed policy")
        with self._lock:
            if self._closed or self._transaction_active:
                raise ValueError("World cannot install ROE policy while unavailable")
            factions = set(self.faction_ids)
            relationship = next(
                (
                    item
                    for item in self.relationships
                    if item.source_faction_id == policy.source_faction_id
                    and item.target_faction_id == policy.target_faction_id
                    and item.relation == policy.relationship
                ),
                None,
            )
            if (
                policy.source_faction_id not in factions
                or policy.target_faction_id not in factions
                or relationship is None
                or policy.rule_id in self.roe_rules
            ):
                raise ValueError("World ROE policy differs from resolved relationship evidence")
            self.roe_rules = MappingProxyType({**self.roe_rules, policy.rule_id: policy})

    @staticmethod
    def _binding_content(binding: object) -> Mapping[str, object]:
        content = getattr(binding, "normalized_content", None)
        if isinstance(content, Mapping):
            return content
        if isinstance(binding, Mapping):
            candidate = binding.get("normalized_content", binding.get("content", {}))
            if isinstance(candidate, Mapping):
                return candidate
        return MappingProxyType({})

    @staticmethod
    def _binding_exact_ref(binding: object) -> str:
        value = getattr(binding, "exact_ref", None)
        if isinstance(value, str) and value:
            return value
        if isinstance(binding, Mapping) and isinstance(binding.get("exact_ref"), str):
            return str(binding["exact_ref"])
        raise ValueError("capability binding omits exact resource identity")

    def _initialise_tick_zero_capability_events(self) -> None:
        """Activate tick-zero environment/failure state before the first step.

        Other typed events retain their existing end-of-interval dispatcher.
        These two state-only declarations must be available to the first motion
        interval, exactly like an initial resolved world profile.
        """

        initial = tuple(
            event
            for event in self._resolved_events
            if getattr(event.trigger, "tick", None) == 0
            and event.event_type in {"weather_change", "component_suppression"}
        )
        for event in initial:
            values = event.payload.values
            if event.event_type == "weather_change":
                self._weather_state = {
                    "current": _frozen_mapping(values),
                    "event_id": event.id,
                    "active_from_tick": 0,
                }
            else:
                key = f"{values['target_entity_id']}|{values['component_ref']}"
                self._component_suppressions[key] = {
                    "payload": _frozen_mapping(values),
                    "expires_tick": int(values["duration_ticks"]),
                    "active_from_tick": 0,
                }

    def _environment_modifiers(self, *, tick: int) -> tuple[CapabilityModifierV2, ...]:
        current = self._weather_state.get("current")
        if not isinstance(current, Mapping):
            return ()
        binding = current.get("environment_binding")
        if binding is None:
            return ()
        active_from = self._weather_state.get("active_from_tick", 0)
        if not isinstance(active_from, int) or isinstance(active_from, bool):
            raise ValueError("environment modifier activation tick is invalid")
        return modifiers_from_environment_content_v2(
            environment_ref=self._binding_exact_ref(binding),
            content=self._binding_content(binding),
            source_event_id=cast(str | None, self._weather_state.get("event_id")),
            active_from_tick=active_from,
        )

    def _environment_profile_multiplier(
        self, *, capability: str, profile: Mapping[str, object]
    ) -> float:
        """Resolve an optional generic per-component multiplier from environment data."""

        current = self._weather_state.get("current")
        if not isinstance(current, Mapping):
            return 1.0
        binding = current.get("environment_binding")
        if binding is None:
            return 1.0
        keys = self._binding_content(binding).get("sensor_profile_multiplier_keys", {})
        if not isinstance(keys, Mapping):
            raise ValueError("environment sensor profile multiplier keys are invalid")
        key = keys.get(capability)
        if key is None:
            return 1.0
        if not isinstance(key, str) or not key:
            raise ValueError("environment sensor profile multiplier key is invalid")
        value = profile.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("sensor profile environment multiplier is invalid")
        multiplier = float(value)
        if not math.isfinite(multiplier) or multiplier < 0.0:
            raise ValueError("sensor profile environment multiplier is not finite")
        return multiplier

    def _environment_capability_additive(self, *, capability: str) -> float:
        """Read a generic additive capability adjustment from environment content."""

        current = self._weather_state.get("current")
        if not isinstance(current, Mapping):
            return 0.0
        binding = current.get("environment_binding")
        if binding is None:
            return 0.0
        field = f"{capability.replace('.', '_')}_additive"
        value = self._binding_content(binding).get(field, 0.0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("environment capability additive is invalid")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("environment capability additive is not finite")
        return result

    def _is_component_suppressed(
        self, *, entity_id: str, component_ref: str | None, tick: int
    ) -> bool:
        if component_ref is None:
            return False
        record = self._component_suppressions.get(f"{entity_id}|{component_ref}")
        if not isinstance(record, Mapping):
            return False
        expiry = record.get("expires_tick")
        active_from = record.get("active_from_tick", 0)
        if (
            not isinstance(expiry, int)
            or isinstance(expiry, bool)
            or not isinstance(active_from, int)
            or isinstance(active_from, bool)
        ):
            raise ValueError("component suppression tick evidence is invalid")
        return active_from <= tick < expiry

    def _resolve_entity_capability(
        self,
        *,
        entity: _RuntimeEntityV2,
        capability: str,
        base_value: float,
        tick: int,
        component_ref: str | None = None,
    ) -> float:
        value = resolve_capability_v2(
            capability=capability,
            base_value=base_value,
            tick=tick,
            modifiers=self._environment_modifiers(tick=tick),
            suppressed=self._is_component_suppressed(
                entity_id=entity.id, component_ref=component_ref, tick=tick
            ),
            lifecycle_available=entity.state.lifecycle in {"active", "degraded"},
            energy_available=entity.state.energy is None or entity.state.energy > 0.0,
        )
        return value.value

    def _profile_with_capability_modifiers(
        self,
        *,
        entity: _RuntimeEntityV2,
        role: str,
        binding: ResolvedResourceBindingV2,
        tick: int,
    ) -> Mapping[str, object]:
        profile: dict[str, object] = {
            "exact_ref": binding.exact_ref,
            **dict(binding.normalized_content),
        }
        field_capabilities: tuple[tuple[str, str], ...]
        if role == "sensors":
            if (
                "detection_probability" not in profile
                and isinstance(profile.get("probability"), (int, float))
                and not isinstance(profile.get("probability"), bool)
            ):
                profile["detection_probability"] = profile["probability"]
            field_capabilities = (
                ("range_m", "sensor.range"),
                ("detection_probability", "sensor.probability"),
            )
        elif role == "energy":
            field_capabilities = (
                ("idle_rate_per_second", "energy.consumption"),
                ("motion_rate_per_meter", "energy.consumption"),
            )
        else:
            field_capabilities = ()
        for field, capability in field_capabilities:
            raw = profile.get(field)
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                base_value = float(raw) * self._environment_profile_multiplier(
                    capability=capability,
                    profile=profile,
                )
                profile[field] = self._resolve_entity_capability(
                    entity=entity,
                    capability=capability,
                    base_value=base_value,
                    tick=tick,
                    component_ref=binding.exact_ref,
                )
        return MappingProxyType(profile)

    def _communication_profile(
        self, *, entity: _RuntimeEntityV2, tick: int
    ) -> Mapping[str, object] | None:
        bindings = tuple(
            sorted(
                entity.definition.resource_bindings.get("communications", ()),
                key=lambda item: item.exact_ref,
            )
        )
        if not bindings:
            return None
        binding = bindings[0]
        raw = self._binding_content(binding)
        profile = {"exact_ref": binding.exact_ref, **dict(raw)}
        range_m = raw.get("range_m", 0.0)
        loss = raw.get("loss_probability", 0.0)
        if (
            isinstance(range_m, bool)
            or not isinstance(range_m, (int, float))
            or isinstance(loss, bool)
            or not isinstance(loss, (int, float))
        ):
            raise ValueError("communication profile range or loss is invalid")
        profile["range_m"] = self._resolve_entity_capability(
            entity=entity,
            capability="communication.range",
            base_value=float(range_m),
            tick=tick,
            component_ref=binding.exact_ref,
        )
        profile["loss_probability"] = min(
            1.0,
            max(
                0.0,
                self._resolve_entity_capability(
                    entity=entity,
                    capability="communication.loss",
                    base_value=float(loss),
                    tick=tick,
                    component_ref=binding.exact_ref,
                ),
            ),
        )
        loss_probability = profile["loss_probability"]
        if isinstance(loss_probability, bool) or not isinstance(loss_probability, (int, float)):
            raise ValueError("communication profile loss probability is invalid")
        profile["loss_probability"] = min(
            1.0,
            max(
                0.0,
                float(loss_probability)
                + self._environment_capability_additive(capability="communication.loss"),
            ),
        )
        return MappingProxyType(profile)

    @staticmethod
    def _communication_direct_link_available(
        *,
        sender: _RuntimeEntityV2,
        recipient: _RuntimeEntityV2,
        sender_profile: Mapping[str, object],
        recipient_profile: Mapping[str, object],
    ) -> bool:
        if sender.state.lifecycle not in {
            "active",
            "degraded",
        } or recipient.state.lifecycle not in {
            "active",
            "degraded",
        }:
            return False
        sender_terrain_blocked = sender_profile.get("terrain_blocked", False)
        recipient_terrain_blocked = recipient_profile.get("terrain_blocked", False)
        if not isinstance(sender_terrain_blocked, bool) or not isinstance(
            recipient_terrain_blocked, bool
        ):
            raise ValueError("communication terrain availability is invalid")
        if sender_terrain_blocked or recipient_terrain_blocked:
            return False
        sender_range = sender_profile.get("range_m")
        recipient_range = recipient_profile.get("range_m")
        if (
            isinstance(sender_range, bool)
            or not isinstance(sender_range, (int, float))
            or isinstance(recipient_range, bool)
            or not isinstance(recipient_range, (int, float))
        ):
            raise ValueError("communication effective range is invalid")
        return min(float(sender_range), float(recipient_range)) > 0.0 and math.dist(
            sender.state.position_m, recipient.state.position_m
        ) <= min(float(sender_range), float(recipient_range))

    def _communication_route(
        self,
        *,
        sender: _RuntimeEntityV2,
        recipient: _RuntimeEntityV2,
        sender_profile: Mapping[str, object],
        recipient_profile: Mapping[str, object],
        tick: int,
    ) -> tuple[str, ...] | None:
        """Find a stable same-faction route from declared endpoint data only."""

        max_relay_hops = sender_profile.get("max_relay_hops", 0)
        if (
            not isinstance(max_relay_hops, int)
            or isinstance(max_relay_hops, bool)
            or not 0 <= max_relay_hops <= 8
        ):
            raise ValueError("communication max_relay_hops is invalid")
        jammed = {
            session.get("target_entity_id")
            for session in self._jamming_sessions.values()
            if isinstance(session, Mapping)
        }
        if sender.id in jammed or recipient.id in jammed:
            return None
        profiles: dict[str, Mapping[str, object]] = {
            sender.id: sender_profile,
            recipient.id: recipient_profile,
        }
        for entity_id, entity in sorted(self._entities.items()):
            if (
                entity_id in profiles
                or entity.faction_id != sender.faction_id
                or entity_id in jammed
            ):
                continue
            profile = self._communication_profile(entity=entity, tick=tick)
            if profile is not None:
                profiles[entity_id] = profile
        endpoints = {
            entity_id: self._entities[entity_id]
            for entity_id in profiles
            if entity_id in self._entities
        }
        frontier: list[tuple[str, ...]] = [(sender.id,)]
        while frontier:
            route = frontier.pop(0)
            current_id = route[-1]
            current = endpoints[current_id]
            current_profile = profiles[current_id]
            candidate_ids = [recipient.id]
            candidate_ids.extend(
                entity_id
                for entity_id in sorted(endpoints)
                if entity_id not in {sender.id, recipient.id} and entity_id not in route
            )
            for candidate_id in candidate_ids:
                if candidate_id in route:
                    continue
                candidate = endpoints[candidate_id]
                candidate_profile = profiles[candidate_id]
                if not self._communication_direct_link_available(
                    sender=current,
                    recipient=candidate,
                    sender_profile=current_profile,
                    recipient_profile=candidate_profile,
                ):
                    continue
                candidate_route = (*route, candidate_id)
                if candidate_id == recipient.id:
                    return candidate_route
                if len(candidate_route) - 2 < max_relay_hops:
                    frontier.append(candidate_route)
        return None

    def _communication_route_is_available(self, *, route: Sequence[str], tick: int) -> bool:
        """Revalidate each scheduled route immediately before delivery."""

        if len(route) < 2 or any(not isinstance(entity_id, str) for entity_id in route):
            return False
        jammed = {
            session.get("target_entity_id")
            for session in self._jamming_sessions.values()
            if isinstance(session, Mapping)
        }
        if any(entity_id in jammed for entity_id in route):
            return False
        entities: list[_RuntimeEntityV2] = []
        profiles: list[Mapping[str, object]] = []
        for entity_id in route:
            entity = self._entities.get(entity_id)
            if entity is None:
                return False
            profile = self._communication_profile(entity=entity, tick=tick)
            if profile is None:
                return False
            entities.append(entity)
            profiles.append(profile)
        return all(
            self._communication_direct_link_available(
                sender=entities[index],
                recipient=entities[index + 1],
                sender_profile=profiles[index],
                recipient_profile=profiles[index + 1],
            )
            for index in range(len(entities) - 1)
        )

    def _invoke_motion_provider(
        self,
        *,
        tick_input: WorldTickInputV2,
        step_tick: int,
        expected_entity_ids: frozenset[str],
    ) -> tuple[
        tuple[MotionCandidateV2 | KinematicMotionCandidateV2, ...],
        str,
        tuple[DynamicsStepReceiptV2, ...],
    ]:
        """Step World-owned dynamics adapters from exact typed controller commands."""

        commands = {item.entity_id: item for item in tick_input.entity_commands}
        if set(commands) != set(expected_entity_ids) or any(
            item.tick != step_tick for item in commands.values()
        ):
            raise ValueError(
                "World tick requires exactly one current command per active dynamics entity"
            )
        manifest = native_artifact_manifest_v2()
        candidates: list[MotionCandidateV2 | KinematicMotionCandidateV2] = []
        receipts: list[DynamicsStepReceiptV2] = []
        for entity_id in sorted(expected_entity_ids):
            entity = self._entities[entity_id]
            resource_ref = entity.definition.composition.dynamics_ref
            if resource_ref is None:
                raise ValueError("active dynamics entity has no exact resource binding")
            binding = next(
                (
                    item
                    for item in entity.definition.resource_bindings.get("dynamics", ())
                    if item.exact_ref == resource_ref
                ),
                None,
            )
            adapter = entity.adapters.get(resource_ref)
            if binding is None or adapter is None:
                raise ValueError("active dynamics binding or owned adapter is absent")
            controls = commands[entity_id].controls
            speed_multiplier = self._resolve_entity_capability(
                entity=entity,
                capability="dynamics.speed",
                base_value=1.0,
                tick=step_tick,
                component_ref=binding.exact_ref,
            )
            speed_multiplier = max(0.0, speed_multiplier)
            if binding.model_ref == FIXED_MODEL_REF:
                native_command: DynamicsCommandV2 | MMGCommandV2 | None = None
                if controls:
                    raise ValueError("fixed dynamics accepts no controller fields")
            elif binding.model_ref == MMG_MODEL_REF:
                if set(controls) != {"nps", "rudder_rad"}:
                    raise ValueError("MMG dynamics requires exact nps and rudder_rad controls")
                native_command = MMGCommandV2(
                    nps=controls["nps"] * speed_multiplier, rudder_rad=controls["rudder_rad"]
                )
            else:
                required = {
                    "target_speed_mps",
                    "target_heading_deg",
                    "target_vertical_m",
                }
                if set(controls) != required:
                    raise ValueError("kinematic dynamics requires its exact three target controls")
                native_command = DynamicsCommandV2(
                    target_speed_mps=controls["target_speed_mps"] * speed_multiplier,
                    target_heading_deg=controls["target_heading_deg"],
                    target_vertical_m=controls["target_vertical_m"],
                )
            state = DynamicsStateV2(
                position_m=cast(tuple[float, float, float], tuple(entity.state.position_m)),
                velocity_mps=cast(tuple[float, float, float], tuple(entity.state.velocity_mps)),
                heading_deg=entity.state.heading_deg,
            )
            snapshot = getattr(adapter, "snapshot", None)
            step = getattr(adapter, "step", None)
            if not callable(snapshot) or not callable(step):
                raise ValueError("registered dynamics adapter lacks step/snapshot protocol")
            before = snapshot()
            before_state_hash = _canonical_evidence_hash(
                {
                    "model_ref": before.model_ref,
                    "resource_ref": before.resource_ref,
                    "binding_identity_hash": before.binding_identity_hash,
                    "native_state": before.native_state,
                }
            )
            input_payload = [
                entity_id,
                step_tick,
                resource_ref,
                binding.model_ref,
                state.model_dump(mode="json"),
                None if native_command is None else native_command.model_dump(mode="json"),
                tick_input.dt_seconds,
                before_state_hash,
            ]
            input_hash = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(input_payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
            )
            output = step(
                state=state,
                command=native_command,
                tick_seconds=tick_input.dt_seconds,
            )
            if not isinstance(output, DynamicsStateV2):
                raise ValueError("registered dynamics adapter returned an untyped state")
            after = snapshot()
            after_state_hash = _canonical_evidence_hash(
                {
                    "model_ref": after.model_ref,
                    "resource_ref": after.resource_ref,
                    "binding_identity_hash": after.binding_identity_hash,
                    "native_state": after.native_state,
                }
            )
            output_hash = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        output.model_dump(mode="json"),
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
            )
            artifact = manifest.get(binding.model_ref)
            if (
                artifact is None
                or not artifact.available
                or artifact.artifact_sha256 != binding.model_evidence.artifact_sha256
            ):
                raise ValueError("native artifact evidence differs from resolved model binding")
            manifest_hash = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        artifact.model_dump(mode="json"),
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
            )
            diagnostic = _entity_view(entity).adapter_diagnostics[resource_ref]
            candidates.append(
                MotionCandidateV2.from_adapter_output(
                    entity_id=entity_id,
                    position_m=output.position_m,
                    velocity_mps=output.velocity_mps,
                    heading_deg=output.heading_deg,
                    dynamics_resource_ref=resource_ref,
                    model_ref=binding.model_ref,
                    adapter_instance_id=diagnostic.instance_id,
                    resolved_hash=self._resolved_hash,
                    provider_receipt=diagnostic.last_output_receipt,
                )
            )
            receipts.append(
                DynamicsStepReceiptV2(
                    entity_id=entity_id,
                    tick=step_tick,
                    resource_ref=resource_ref,
                    model_ref=binding.model_ref,
                    adapter_instance_id=(f"native:{self.session_id}:{entity_id}:{resource_ref}"),
                    artifact_hash=artifact.artifact_sha256,
                    manifest_hash=manifest_hash,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    snapshot_hash=after_state_hash,
                )
            )
        provider_receipt = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    [_plain(item) for item in receipts],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )
        return tuple(candidates), provider_receipt, tuple(receipts)

    @staticmethod
    def _trigger_effect_parameters(
        binding: ResolvedResourceBindingV2,
    ) -> tuple[float, float | None]:
        magnitude = binding.normalized_content.get("magnitude")
        if (
            isinstance(magnitude, bool)
            or not isinstance(magnitude, (int, float))
            or not math.isfinite(float(magnitude))
            or float(magnitude) < 0.0
        ):
            raise ValueError("spatial trigger effect magnitude is invalid")
        radius = binding.normalized_content.get("detonation_radius_m")
        if radius is None:
            return float(magnitude), None
        if (
            isinstance(radius, bool)
            or not isinstance(radius, (int, float))
            or not math.isfinite(float(radius))
            or float(radius) < 0.0
        ):
            raise ValueError("spatial trigger effect radius is invalid")
        return float(magnitude), float(radius)

    def _arm_spatial_effect_trigger(self, event: ResolvedEventV2) -> None:
        """Freeze one resolved trigger into only primitive session-owned evidence."""

        values = event.payload.values
        effect = values["effect_binding"]
        damage = values["damage_binding"]
        if not isinstance(effect, ResolvedResourceBindingV2) or not isinstance(
            damage, ResolvedResourceBindingV2
        ):
            raise ValueError("spatial trigger omits its resolved primary effect chain")
        magnitude, radius = self._trigger_effect_parameters(effect)
        selector = values["target_selector"].values
        config: dict[str, Any] = {
            "trigger_event_id": event.id,
            "activation_tick": getattr(event.trigger, "tick", None),
            "priority": event.priority,
            "source_kind": values["source_kind"],
            "source_entity_ids": tuple(sorted(values["source_entity_ids"])),
            "zone_id": values.get("zone_id"),
            "source_lifecycle": values["source_lifecycle"],
            "effect_ref": effect.exact_ref,
            "damage_model_ref": damage.exact_ref,
            "magnitude": magnitude,
            "radius_m": radius,
            "target_selector": {
                "entity_ids": tuple(sorted(selector["entity_ids"])),
                "exclude_entity_ids": tuple(sorted(selector.get("exclude_entity_ids", ()))),
            },
        }
        secondary_effect = values.get("secondary_effect_binding")
        secondary_damage = values.get("secondary_damage_binding")
        if secondary_effect is not None or secondary_damage is not None:
            if not isinstance(secondary_effect, ResolvedResourceBindingV2) or not isinstance(
                secondary_damage, ResolvedResourceBindingV2
            ):
                raise ValueError("spatial trigger omits its resolved secondary effect chain")
            secondary_magnitude, secondary_radius = self._trigger_effect_parameters(
                secondary_effect
            )
            secondary_selector = values["secondary_target_selector"].values
            config["secondary"] = {
                "effect_ref": secondary_effect.exact_ref,
                "damage_model_ref": secondary_damage.exact_ref,
                "magnitude": secondary_magnitude,
                "radius_m": secondary_radius,
                "probability": float(values["secondary_probability"]),
                "target_selector": {
                    "entity_ids": tuple(sorted(secondary_selector["entity_ids"])),
                    "exclude_entity_ids": tuple(
                        sorted(secondary_selector.get("exclude_entity_ids", ()))
                    ),
                },
            }
        self._spatial_effect_triggers[event.id] = _frozen_mapping(config)

    def _spatial_trigger_targets(
        self,
        *,
        selector: Mapping[str, Any],
        source_position_m: tuple[float, float, float],
        radius_m: float | None,
    ) -> tuple[str, ...]:
        excluded = set(cast(Sequence[str], selector.get("exclude_entity_ids", ())))
        targets: list[str] = []
        for entity_id in cast(Sequence[str], selector["entity_ids"]):
            entity = self._entities.get(entity_id)
            if entity is None or entity_id in excluded or entity.state.lifecycle == "destroyed":
                continue
            if (
                radius_m is not None
                and math.dist(source_position_m, entity.state.position_m) > radius_m + 1e-9
            ):
                continue
            targets.append(entity_id)
        return tuple(sorted(targets))

    def _execute_armed_spatial_effect_triggers(
        self,
        *,
        motion_receipt: MotionReceiptV2,
        prior_motion_positions: Mapping[str, tuple[float, float, float]],
    ) -> tuple[
        dict[str, DamageIntentV2],
        tuple[tuple[str, str, str], ...],
        tuple[TypedEventExecutionReceiptV2, ...],
    ]:
        """Translate continuous source evidence into one-shot DamageIntent batches."""

        intents: dict[str, DamageIntentV2] = {}
        lifecycle_requests: list[tuple[str, str, str]] = []
        typed_receipts: list[TypedEventExecutionReceiptV2] = []
        current_transitions = tuple(
            transition
            for transition in self._mission_zone_transitions
            if transition.tick == motion_receipt.tick and transition.transition == "entered"
        )
        for trigger_id, config in sorted(self._spatial_effect_triggers.items()):
            activation_tick = config.get("activation_tick")
            if not isinstance(activation_tick, int) or isinstance(activation_tick, bool):
                raise ValueError("armed spatial trigger activation tick is invalid")
            if activation_tick > motion_receipt.tick:
                continue
            source_ids = frozenset(cast(Sequence[str], config["source_entity_ids"]))
            source_events: list[tuple[float, str, str, str, tuple[float, float, float]]] = []
            if config["source_kind"] == "zone_entry":
                for transition in current_transitions:
                    if (
                        transition.entity_id not in source_ids
                        or transition.zone_id != config["zone_id"]
                    ):
                        continue
                    start = prior_motion_positions.get(transition.entity_id)
                    entity = self._entities.get(transition.entity_id)
                    if start is None or entity is None:
                        continue
                    fraction = float(transition.time_fraction)
                    end = tuple(entity.state.position_m)
                    position = cast(
                        tuple[float, float, float],
                        tuple(
                            start[index] + (end[index] - start[index]) * fraction
                            for index in range(3)
                        ),
                    )
                    source_events.append(
                        (
                            fraction,
                            transition.entity_id,
                            transition.evidence_hash,
                            "zone_entry",
                            position,
                        )
                    )
            elif config["source_kind"] == "collision":
                for collision in motion_receipt.collision_events:
                    participants = frozenset((collision.entity_a_id, collision.entity_b_id))
                    for source_entity_id in sorted(participants & source_ids):
                        source_events.append(
                            (
                                collision.time_fraction,
                                source_entity_id,
                                collision.event_id,
                                "collision",
                                collision.position_m,
                            )
                        )
            else:
                raise ValueError("armed spatial trigger has an invalid source kind")

            for (
                fraction,
                source_entity_id,
                source_evidence_id,
                source_kind,
                source_position,
            ) in sorted(source_events, key=lambda item: (item[0], item[3], item[1], item[2])):
                consumption_key = (
                    "spatial-trigger-consumed:"
                    + hashlib.sha256(
                        json.dumps(
                            [self._resolved_hash, trigger_id, source_entity_id],
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                )
                if consumption_key in self._spatial_effect_trigger_consumption:
                    continue
                authority_event_id = (
                    "spatial-trigger:"
                    + hashlib.sha256(
                        json.dumps(
                            [
                                self._resolved_hash,
                                trigger_id,
                                source_entity_id,
                                source_evidence_id,
                            ],
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                )
                if authority_event_id in self._spatial_effect_trigger_ledger:
                    continue
                source_entity = self._entities.get(source_entity_id)
                if source_entity is None or source_entity.state.lifecycle == "destroyed":
                    continue
                owner_state_hash_before = _canonical_evidence_hash(self.event_state_snapshot())

                primary_targets = (
                    source_entity_id,
                    *self._spatial_trigger_targets(
                        selector=cast(Mapping[str, Any], config["target_selector"]),
                        source_position_m=source_position,
                        radius_m=cast(float | None, config["radius_m"]),
                    ),
                )
                applied_intent_ids: list[str] = []

                def add_effect(
                    *,
                    role: str,
                    effect_ref: str,
                    damage_model_ref: str,
                    magnitude: float,
                    targets: Sequence[str],
                    _authority_event_id: str = authority_event_id,
                    _trigger_id: str = trigger_id,
                    _source_evidence_id: str = source_evidence_id,
                    _source_kind: str = source_kind,
                    _source_position: tuple[float, float, float] = source_position,
                    _source_entity_id: str = source_entity_id,
                    _applied_intent_ids: list[str] = applied_intent_ids,
                ) -> None:
                    for target_id in sorted(set(targets)):
                        if target_id not in self._entities:
                            continue
                        intent_id = (
                            "spatial-damage:"
                            + hashlib.sha256(
                                json.dumps(
                                    [_authority_event_id, role, target_id], separators=(",", ":")
                                ).encode()
                            ).hexdigest()
                        )
                        evidence = {
                            "authority_event_id": _authority_event_id,
                            "trigger_event_id": _trigger_id,
                            "source_evidence_id": _source_evidence_id,
                            "source_kind": _source_kind,
                            "source_position_m": _source_position,
                            "role": role,
                        }
                        intent = DamageIntentV2(
                            schema_version="2.0",
                            intent_id=intent_id,
                            tick=motion_receipt.tick,
                            source_entity_id=_source_entity_id,
                            target_entity_id=target_id,
                            effect_ref=effect_ref,
                            damage_model_ref=damage_model_ref,
                            magnitude=magnitude,
                            parameters=evidence,
                            evidence_hash=_canonical_evidence_hash(evidence),
                            source_kind="environment",
                        )
                        intents[f"environment:{intent_id}"] = intent
                        _applied_intent_ids.append(intent_id)

                add_effect(
                    role="primary",
                    effect_ref=cast(str, config["effect_ref"]),
                    damage_model_ref=cast(str, config["damage_model_ref"]),
                    magnitude=float(config["magnitude"]),
                    targets=primary_targets,
                )
                secondary_evidence: Mapping[str, Any] | None = None
                secondary = config.get("secondary")
                if secondary is not None:
                    secondary = cast(Mapping[str, Any], secondary)
                    seed_payload = [
                        self._resolved_hash,
                        self._session_seed,
                        trigger_id,
                        authority_event_id,
                        "secondary",
                    ]
                    substream_seed = (
                        "sha256:"
                        + hashlib.sha256(
                            json.dumps(seed_payload, separators=(",", ":")).encode()
                        ).hexdigest()
                    )
                    sample = int(substream_seed.removeprefix("sha256:")[:16], 16) / float(2**64)
                    selected = sample < float(secondary["probability"])
                    secondary_targets = (
                        self._spatial_trigger_targets(
                            selector=cast(Mapping[str, Any], secondary["target_selector"]),
                            source_position_m=source_position,
                            radius_m=cast(float | None, secondary["radius_m"]),
                        )
                        if selected
                        else ()
                    )
                    if selected:
                        add_effect(
                            role="secondary",
                            effect_ref=cast(str, secondary["effect_ref"]),
                            damage_model_ref=cast(str, secondary["damage_model_ref"]),
                            magnitude=float(secondary["magnitude"]),
                            targets=secondary_targets,
                        )
                    secondary_evidence = _frozen_mapping(
                        {
                            "substream_seed": substream_seed,
                            "sample": sample,
                            "probability": float(secondary["probability"]),
                            "selected": selected,
                            "target_ids": secondary_targets,
                        }
                    )
                self._spatial_effect_trigger_ledger[authority_event_id] = _frozen_mapping(
                    {
                        "authority_event_id": authority_event_id,
                        "trigger_event_id": trigger_id,
                        "source_entity_id": source_entity_id,
                        "source_kind": source_kind,
                        "source_evidence_id": source_evidence_id,
                        "tick": motion_receipt.tick,
                        "time_fraction": fraction,
                        "source_position_m": source_position,
                        "primary_intent_ids": tuple(sorted(applied_intent_ids)),
                        "source_lifecycle": config["source_lifecycle"],
                        "secondary": secondary_evidence,
                        "lifecycle_status": "pending_damage_resolution",
                    }
                )
                self._spatial_effect_trigger_consumption[consumption_key] = _frozen_mapping(
                    {
                        "consumption_key": consumption_key,
                        "trigger_event_id": trigger_id,
                        "source_entity_id": source_entity_id,
                        "authority_event_id": authority_event_id,
                        "tick": motion_receipt.tick,
                        "source_evidence_id": source_evidence_id,
                    }
                )
                lifecycle_requests.append(
                    (authority_event_id, source_entity_id, cast(str, config["source_lifecycle"]))
                )
                if trigger_id not in self._applied_tick_event_ids:
                    resolved_event = next(
                        (event for event in self._resolved_events if event.id == trigger_id), None
                    )
                    if resolved_event is None:
                        raise ValueError("armed spatial trigger has no resolved event")
                    resolved_payload = _frozen_mapping(resolved_event.payload.values)
                    self._applied_tick_event_ids.add(trigger_id)
                    typed_receipts.append(
                        TypedEventExecutionReceiptV2(
                            event_id=trigger_id,
                            event_type="spatial_effect_trigger",
                            tick=motion_receipt.tick,
                            payload=resolved_payload,
                            payload_hash=_canonical_evidence_hash(resolved_payload),
                            owner_state_hash_before=owner_state_hash_before,
                            owner_state_hash_after=_canonical_evidence_hash(
                                self.event_state_snapshot()
                            ),
                        )
                    )
        return intents, tuple(lifecycle_requests), tuple(typed_receipts)

    def _is_static_wreck(self, entity_id: str) -> bool:
        """Return whether a destroyed entity is explicitly retained as an obstacle."""

        entity = self._entities.get(entity_id)
        record = self._destroyed_lifecycle_ledger.get(entity_id)
        return (
            entity is not None
            and entity.state.lifecycle == "destroyed"
            and record is not None
            and record.get("policy") == "wreck"
            and record.get("status") == "wreck"
        )

    def _destroyed_lifecycle_authority_id(
        self,
        *,
        entity_id: str,
        tick: int,
        intent_ids: Sequence[str],
    ) -> str:
        return (
            "damage-lifecycle:"
            + hashlib.sha256(
                json.dumps(
                    [self._resolved_hash, entity_id, tick, tuple(sorted(intent_ids))],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )

    def _finalize_destroyed_lifecycle(
        self,
        *,
        damage_receipt: DamageApplyReceiptV2,
        spatial_requests: Sequence[tuple[str, str, str]],
        expected_tick: int,
    ) -> None:
        """Apply the resolved per-entity destruction policy after one damage batch.

        A spatial trigger can supply a data-defined source policy for its own
        source.  All other destroyed entities use their immutable entity policy.
        This keeps weapon, collision, effect, and trigger destruction on the
        same lifecycle path while preserving one authoritative tombstone source.
        """

        requests_by_entity: dict[str, list[tuple[str, str]]] = {}
        for authority_event_id, entity_id, policy in sorted(spatial_requests):
            if policy not in {"wreck", "despawn"}:
                raise ValueError("spatial trigger lifecycle policy is invalid")
            requests_by_entity.setdefault(entity_id, []).append((authority_event_id, policy))

        newly_destroyed = {
            result.target_entity_id: result
            for result in damage_receipt.results
            if result.lifecycle_before != "destroyed" and result.lifecycle_after == "destroyed"
        }
        despawned = False
        for entity_id, result in sorted(newly_destroyed.items()):
            entity = self._entities.get(entity_id)
            if entity is None:
                raise ValueError("destroyed lifecycle target is unavailable")
            override = requests_by_entity.get(entity_id, ())
            source_event_id, policy = (
                override[0]
                if override
                else (
                    self._destroyed_lifecycle_authority_id(
                        entity_id=entity_id,
                        tick=expected_tick,
                        intent_ids=result.applied_intent_ids,
                    ),
                    entity.definition.destroyed_lifecycle,
                )
            )
            lifecycle_record: dict[str, Any] = {
                "entity_id": entity_id,
                "policy": policy,
                "source_event_id": source_event_id,
                "tick": expected_tick,
                "damage_intent_ids": tuple(sorted(result.applied_intent_ids)),
            }
            if policy == "wreck":
                lifecycle_record["status"] = "wreck"
            else:
                removed = self._entities.pop(entity_id)
                for key in tuple(self._combat_component_health):
                    if key.startswith(f"{entity_id}|"):
                        self._combat_component_health.pop(key)
                self._mission_zone_membership.pop(entity_id, None)
                self.contact_store = WorldContactStoreV2(
                    tuple(
                        contact
                        for records in self.contact_store.records.values()
                        for contact in records
                        if entity_id not in {contact.owner_entity_id, contact.target_entity_id}
                    )
                )
                entry = LifecycleScheduleEntryV2(
                    topological_index=-1,
                    tick=expected_tick,
                    priority=0,
                    event_type="despawn",
                    entity_id=entity_id,
                    source_event_id=source_event_id,
                )
                cleanup_errors = self._finalize_lifecycle_despawns(((entry, removed),))
                lifecycle_record["status"] = (
                    "despawned_with_cleanup_errors" if cleanup_errors else "despawned"
                )
                lifecycle_record["cleanup_errors"] = cleanup_errors
                despawned = True
            self._destroyed_lifecycle_ledger[entity_id] = _frozen_mapping(lifecycle_record)

        for authority_event_id, entity_id, _policy in sorted(spatial_requests):
            record = dict(self._spatial_effect_trigger_ledger[authority_event_id])
            lifecycle = self._destroyed_lifecycle_ledger.get(entity_id)
            entity = self._entities.get(entity_id)
            if lifecycle is not None:
                record["lifecycle_status"] = lifecycle["status"]
                record["lifecycle_source_event_id"] = lifecycle["source_event_id"]
            elif entity is None:
                record["lifecycle_status"] = "already_unavailable"
            elif entity.state.lifecycle != "destroyed":
                record["lifecycle_status"] = "not_destroyed"
            else:
                raise ValueError("destroyed entity has no lifecycle policy evidence")
            self._spatial_effect_trigger_ledger[authority_event_id] = _frozen_mapping(record)
        if despawned:
            self._rebuild_indexes()
            self._refresh_controller_ownership()
            self._rebuild_spatial_runtime_after_lifecycle()

    def _execute_typed_events(
        self,
        *,
        motion_receipt: MotionReceiptV2,
        prior_motion_positions: Mapping[str, tuple[float, float, float]],
        operation_id: str,
    ) -> tuple[WorldEventReceiptV2, dict[str, DamageIntentV2], tuple[tuple[str, str, str], ...]]:
        """Apply typed event payloads to their owning World state transactionally."""

        trusted: dict[str, DamageIntentV2] = {}
        for intent in motion_receipt.damage_intents:
            policy = self._spatial_effect_policy
            if policy is None:
                raise ValueError("spatial DamageIntent has no immutable resolved effect chain")
            raw_evidence = intent.parameters.get("impact_damage_evidence")
            if not isinstance(raw_evidence, Mapping):
                raise ValueError("spatial DamageIntent omits typed pre-impact evidence")
            impact_evidence = ImpactDamageEvidenceV2(**dict(raw_evidence))
            if (
                impact_evidence.effect_ref != policy.effect_binding.exact_ref
                or impact_evidence.damage_model_ref != policy.damage_binding.exact_ref
                or impact_evidence.magnitude_model != policy.magnitude_model
                or dict(impact_evidence.magnitude_parameters) != dict(policy.magnitude_parameters)
                or impact_evidence.output_unit != policy.output_unit
                or intent.effect_ref != impact_evidence.effect_ref
                or intent.damage_model_ref != impact_evidence.damage_model_ref
                or intent.magnitude != impact_evidence.magnitude
                or intent.evidence_hash != impact_evidence.evidence_hash
                or intent.source_kind not in {"collision", "environment"}
            ):
                raise ValueError("spatial DamageIntent differs from resolved impact evidence")
            trusted[f"{intent.source_kind}:{intent.intent_id}"] = intent
        trigger_damage, lifecycle_requests, trigger_receipts = (
            self._execute_armed_spatial_effect_triggers(
                motion_receipt=motion_receipt,
                prior_motion_positions=prior_motion_positions,
            )
        )
        trusted.update(trigger_damage)
        resolved_event_ids: list[str] = [item.event_id for item in trigger_receipts]
        typed_receipts: list[TypedEventExecutionReceiptV2] = list(trigger_receipts)
        due_events = tuple(
            event
            for event in self._resolved_events
            if event.event_type not in {"spawn", "despawn", "spatial_effect_trigger"}
            and event.id not in self._applied_tick_event_ids
            and getattr(event.trigger, "tick", None) == motion_receipt.next_tick
        )
        for event in due_events:
            if event.event_type not in SUPPORTED_TICK_EVENT_TYPES:
                raise ValueError("resolved tick event type has no runtime dispatcher")
            values = event.payload.values
            payload = _frozen_mapping(values)
            owner_state_hash_before = _canonical_evidence_hash(self.event_state_snapshot())
            if event.event_type == "zone_activation":
                self.set_zone_activation(
                    zone_id=str(values["zone_id"]),
                    active=True,
                    expected_tick=motion_receipt.next_tick,
                    operation_id=f"{operation_id}:{event.id}",
                )
            elif event.event_type == "apply_effect":
                effect = values["effect_binding"]
                damage = values["damage_binding"]
                selector = values["target_selector"].values
                magnitude = effect.normalized_content.get("magnitude")
                for target_id in tuple(selector["entity_ids"]):
                    intent_id = f"event-damage:{event.id}:{target_id}"
                    trusted[f"environment:{intent_id}"] = DamageIntentV2(
                        schema_version="2.0",
                        intent_id=intent_id,
                        tick=motion_receipt.tick,
                        source_entity_id="world-event-system",
                        target_entity_id=target_id,
                        effect_ref=effect.exact_ref,
                        damage_model_ref=damage.exact_ref,
                        magnitude=magnitude,
                        parameters={"resolved_event_id": event.id},
                    )
                self._effect_application_ledger[event.id] = {
                    "payload": payload,
                    "intent_ids": tuple(
                        sorted(
                            intent.intent_id
                            for key, intent in trusted.items()
                            if key.startswith("environment:event-damage:")
                            and intent.parameters.get("resolved_event_id") == event.id
                        )
                    ),
                }
            elif event.event_type == "weather_change":
                self._weather_state = {
                    "current": payload,
                    "event_id": event.id,
                    "active_from_tick": motion_receipt.next_tick,
                }
            elif event.event_type == "jamming_start":
                self._jamming_sessions[str(values["session_id"])] = payload
            elif event.event_type == "jamming_end":
                self._jamming_sessions.pop(str(values["session_id"]), None)
            elif event.event_type == "message":
                self._message_queue.append(payload)
            elif event.event_type == "component_suppression":
                suppression_key = f"{values['target_entity_id']}|{values['component_ref']}"
                self._component_suppressions[suppression_key] = {
                    "payload": payload,
                    "expires_tick": motion_receipt.next_tick + int(values["duration_ticks"]),
                    "active_from_tick": motion_receipt.next_tick,
                }
            elif event.event_type == "mission_marker":
                self._mission_marker_ledger[str(values["marker_id"])] = payload
            self._applied_tick_event_ids.update((event.id,))
            resolved_event_ids.append(event.id)
            typed_receipts.append(
                TypedEventExecutionReceiptV2(
                    event_id=event.id,
                    event_type=event.event_type,
                    tick=motion_receipt.next_tick,
                    payload=payload,
                    payload_hash=_canonical_evidence_hash(payload),
                    owner_state_hash_before=owner_state_hash_before,
                    owner_state_hash_after=_canonical_evidence_hash(self.event_state_snapshot()),
                )
            )
        event_receipt = WorldEventReceiptV2(
            tick=motion_receipt.tick,
            operation_id=operation_id,
            boundary_event_ids=tuple(item.event_id for item in motion_receipt.boundary_events),
            collision_event_ids=tuple(item.event_id for item in motion_receipt.collision_events),
            damage_intent_ids=tuple(sorted(item.intent_id for item in trusted.values())),
            resolved_event_ids=tuple(resolved_event_ids),
            typed_event_receipts=tuple(typed_receipts),
        )
        return event_receipt, trusted, lifecycle_requests

    def _evaluate_generic_subsystems(
        self, *, tick: int, dt_seconds: float
    ) -> GenericSubsystemTickReceiptV2:
        """Evaluate capability-bound subsystems and commit their typed state."""

        facts: list[SubsystemEntityFactV2] = []
        for entity in self.entities_stable():
            if entity.state.lifecycle not in {"active", "degraded"}:
                continue
            bindings = entity.definition.resource_bindings
            role_profiles = {
                role: tuple(
                    self._profile_with_capability_modifiers(
                        entity=self._entities[entity.id],
                        role=role,
                        binding=binding,
                        tick=tick,
                    )
                    for binding in bindings.get(role, ())
                )
                for role in ("sensors", "communications", "energy")
            }

            facts.append(
                SubsystemEntityFactV2(
                    entity_id=entity.id,
                    faction_id=entity.faction_id,
                    position_m=cast(tuple[float, float, float], tuple(entity.state.position_m)),
                    velocity_mps=cast(tuple[float, float, float], tuple(entity.state.velocity_mps)),
                    energy=entity.state.energy,
                    domain=entity.definition.domain,
                    sensors=role_profiles["sensors"],
                    communications=role_profiles["communications"],
                    energy_profiles=role_profiles["energy"],
                    surface_elevation_m=self._surface_elevation_or_none(
                        tuple(entity.state.position_m)
                    ),
                )
            )
        receipt = GenericSubsystemEngineV2().evaluate(
            entities=tuple(facts),
            tick=tick,
            dt_seconds=dt_seconds,
            seed=self._session_seed,
            queued_message_count=sum(
                1 for item in self._message_queue if item.get("transport_status") == "queued"
            ),
        )
        for energy in receipt.energy:
            runtime_entity = self._entities[energy.entity_id]
            runtime_entity.state.energy = energy.after
        detected_by_track: dict[tuple[str, str], list[SensorContactReceiptV2]] = {}
        for item in receipt.contacts:
            if (
                item.detected
                and item.measurement_position_m is not None
                and item.sample is not None
            ):
                detected_by_track.setdefault(
                    (item.owner_entity_id, item.target_entity_id), []
                ).append(item)
        generated_ids = {
            f"sensor.contact.{owner_entity_id}.{target_entity_id}"
            for owner_entity_id, target_entity_id in detected_by_track
        }
        retained = tuple(
            record
            for evidence_id, records in self.contact_store.records.items()
            for record in records
            if evidence_id not in generated_ids
            # Sensor-created contacts are refreshed from their configured sensor
            # cadence and therefore expire at the sensor's stale threshold.  An
            # explicitly installed authority contact has no sensor-refresh
            # provenance; dropping it at the incidental default stale threshold
            # would make a temporary presentation/communication filter destroy a
            # still-valid record.  Keep that record for its declared operational
            # validity window instead.  It is never replayed: the record ages on
            # every tick and is removed once this bound is reached.
            and tick - record.observed_tick
            < (
                record.stale_after_ticks
                if record.source_sensor_ref is not None
                else max(record.stale_after_ticks, record.max_age_ticks)
            )
        )
        generated: list[WorldContactEvidenceV2] = []
        for (owner_entity_id, target_entity_id), candidates in sorted(detected_by_track.items()):
            item = min(
                candidates,
                key=lambda candidate: (
                    -candidate.probability,
                    candidate.sample,
                    candidate.sensor_ref,
                ),
            )
            if item.sample is None:
                raise ValueError("detected sensor contact is missing its deterministic sample")
            evidence_id = f"sensor.contact.{owner_entity_id}.{target_entity_id}"
            prior = next(
                (
                    record
                    for record in self.contact_store.records.get(evidence_id, ())
                    if record.owner_entity_id == owner_entity_id
                    and record.target_entity_id == target_entity_id
                ),
                None,
            )
            confirmation_count = (
                prior.confirmation_count + 1
                if prior is not None
                and prior.source_sensor_ref == item.sensor_ref
                and tick - prior.observed_tick == item.update_ticks
                else 1
            )
            confirmed = confirmation_count >= item.confirmation_frames
            generated.append(
                WorldContactEvidenceV2(
                    evidence_id=evidence_id,
                    owner_entity_id=owner_entity_id,
                    target_entity_id=target_entity_id,
                    observed_tick=tick,
                    age_ticks=0,
                    max_age_ticks=item.engagement_max_age_ticks,
                    confidence=(1.0 - item.sample) if confirmed else 0.0,
                    minimum_confidence=item.minimum_contact_confidence,
                    quality=item.probability,
                    measurement_position_m=item.measurement_position_m,
                    confirmation_count=confirmation_count,
                    confirmation_frames=item.confirmation_frames,
                    stale_after_ticks=item.stale_after_ticks,
                    confirmed=confirmed,
                    source_sensor_ref=item.sensor_ref,
                )
            )
        self.contact_store = WorldContactStoreV2((*retained, *generated))
        self._enqueue_shared_contact_transport(generated, tick=tick, dt_seconds=dt_seconds)
        return receipt

    def _enqueue_shared_contact_transport(
        self,
        contacts: Sequence[WorldContactEvidenceV2],
        *,
        tick: int,
        dt_seconds: float,
    ) -> None:
        """Snapshot confirmed organic tracks into the common communication transport.

        A queue item is keyed by source contact and recipient controller slot.
        Re-observing that same track cannot mutate a queued/delivered snapshot or
        create a duplicate report.  Later receipt-side fusion is intentionally
        absent: each source report remains a ragged immutable observation.
        """

        existing_ids = {item.get("shared_contact_id") for item in self._shared_contact_queue}
        for contact in sorted(contacts, key=lambda item: item.evidence_id):
            if not contact.confirmed:
                continue
            sender = self._entities.get(contact.owner_entity_id)
            target = self._entities.get(contact.target_entity_id)
            if sender is None or target is None:
                continue
            sender_profile = self._communication_profile(entity=sender, tick=tick)
            if sender_profile is None:
                continue
            estimated_position = (
                contact.measurement_position_m
                if contact.measurement_position_m is not None
                else _estimated_contact_position_v2(
                    contact.evidence_id,
                    contact.observed_tick,
                    contact.confidence,
                    target.state.position_m,
                )
            )
            for slot_id in self.controller_ownership.slot_ids:
                claim = self.controller_ownership.by_slot(slot_id)
                endpoint_id = claim.endpoint_entity_id
                if (
                    claim.faction_id != sender.faction_id
                    or endpoint_id is None
                    or endpoint_id == sender.id
                ):
                    continue
                recipient = self._entities.get(endpoint_id)
                if recipient is None:
                    continue
                shared_contact_id = f"shared-contact:{contact.evidence_id}:{slot_id}"
                if shared_contact_id in existing_ids:
                    continue
                recipient_profile = self._communication_profile(entity=recipient, tick=tick)
                if recipient_profile is None:
                    continue
                delay_seconds_value = sender_profile.get("delay_s", 0.0)
                ttl_seconds_value = sender_profile.get("ttl_s", 0.0)
                loss_probability_value = sender_profile.get("loss_probability", 0.0)
                if (
                    any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        for value in (
                            delay_seconds_value,
                            ttl_seconds_value,
                            loss_probability_value,
                        )
                    )
                    or float(cast(float, delay_seconds_value)) < 0.0
                    or float(cast(float, ttl_seconds_value)) < 0.0
                    or not 0.0 <= float(cast(float, loss_probability_value)) <= 1.0
                ):
                    raise ValueError("shared contact transport profile is invalid")
                delay_seconds = float(cast(float, delay_seconds_value))
                ttl_seconds = float(cast(float, ttl_seconds_value))
                loss_probability = float(cast(float, loss_probability_value))
                ttl_ticks = 0 if ttl_seconds == 0.0 else max(1, math.ceil(ttl_seconds / dt_seconds))
                loss_substream = f"communication:{shared_contact_id}"
                digest = hashlib.sha256(
                    f"{self._session_seed}|{self._resolved_hash}|{tick}|{loss_substream}".encode()
                ).digest()
                loss_sample = int.from_bytes(digest[:8], "big") / float(2**64)
                route = self._communication_route(
                    sender=sender,
                    recipient=recipient,
                    sender_profile=sender_profile,
                    recipient_profile=recipient_profile,
                    tick=tick,
                )
                transport = schedule_transport_v2(
                    message_id=shared_contact_id,
                    origin_tick=tick,
                    ttl_ticks=ttl_ticks,
                    delay_seconds=delay_seconds,
                    physics_dt_seconds=dt_seconds,
                    link_available=route is not None,
                    dropped=loss_sample < loss_probability,
                )
                snapshot = _frozen_mapping(
                    {
                        "shared_contact_id": shared_contact_id,
                        "source_contact_id": contact.evidence_id,
                        "observer_entity_id": contact.owner_entity_id,
                        "estimated_position_m": tuple(estimated_position),
                        "observed_tick": contact.observed_tick,
                        "age_ticks": contact.age_ticks,
                        "confidence": contact.confidence,
                        "quality": contact.quality,
                        "source_sensor_ref": contact.source_sensor_ref,
                    }
                )
                self._shared_contact_queue.append(
                    _frozen_mapping(
                        {
                            "shared_contact_id": shared_contact_id,
                            "source_contact_id": contact.evidence_id,
                            "sender_entity_id": sender.id,
                            "recipient_entity_id": recipient.id,
                            "recipient_controller_slot": slot_id,
                            "generated_tick": tick,
                            "contact_snapshot": snapshot,
                            "sender_communication_ref": sender_profile["exact_ref"],
                            "recipient_communication_ref": recipient_profile["exact_ref"],
                            "delay_seconds": delay_seconds,
                            "delay_ticks": transport.delay_ticks,
                            "ttl_seconds": ttl_seconds,
                            "ttl_ticks": ttl_ticks,
                            "scheduled_delivery_tick": transport.delivery_tick,
                            "expiry_tick": transport.expiry_tick,
                            "transport_status": transport.status,
                            "link_available": route is not None,
                            "route": route or (),
                            "relay_hops": 0 if route is None else len(route) - 2,
                            "loss_probability": loss_probability,
                            "loss_sample": loss_sample,
                            "rng_substream": loss_substream,
                        }
                    )
                )
                existing_ids.add(shared_contact_id)

    def _advance_shared_contact_transport(self, *, tick: int) -> None:
        """Deliver only due snapshots and retain terminal transport evidence."""

        updated: list[Mapping[str, Any]] = []
        for item in self._shared_contact_queue:
            record = dict(item)
            if record.get("transport_status") != "queued":
                updated.append(_frozen_mapping(record))
                continue
            delivery_tick = record.get("scheduled_delivery_tick")
            expiry_tick = record.get("expiry_tick")
            recipient_id = record.get("recipient_entity_id")
            slot_id = record.get("recipient_controller_slot")
            route = record.get("route")
            if (
                not isinstance(delivery_tick, int)
                or not isinstance(expiry_tick, int)
                or not isinstance(recipient_id, str)
                or not isinstance(slot_id, str)
                or not isinstance(route, Sequence)
                or isinstance(route, (str, bytes, bytearray))
            ):
                raise ValueError("queued shared contact transport evidence is invalid")
            if delivery_tick > tick:
                updated.append(_frozen_mapping(record))
                continue
            if delivery_tick > expiry_tick:
                record["transport_status"] = "expired"
                record["resolved_tick"] = tick
            else:
                recipient = self._entities.get(recipient_id)
                if (
                    recipient is None
                    or recipient.state.lifecycle not in {"active", "degraded"}
                    or not self._communication_route_is_available(
                        route=cast(Sequence[str], route), tick=tick
                    )
                ):
                    record["transport_status"] = "blocked"
                    record["resolved_tick"] = tick
                else:
                    record["transport_status"] = "delivered"
                    record["delivered_tick"] = tick
                    snapshot = record.get("contact_snapshot")
                    if not isinstance(snapshot, Mapping):
                        raise ValueError("shared contact snapshot is invalid")
                    delivered = _frozen_mapping(
                        {
                            **dict(snapshot),
                            "recipient_controller_slot": slot_id,
                            "delivered_tick": tick,
                            "expiry_tick": expiry_tick,
                        }
                    )
                    self._shared_contacts_by_controller.setdefault(slot_id, {}).setdefault(
                        str(record["shared_contact_id"]), delivered
                    )
            updated.append(_frozen_mapping(record))
        self._shared_contact_queue = updated

    def enqueue_controller_action_transport(
        self,
        *,
        action: Any,
        action_kind: Literal["persistent", "discrete"],
        authority_token: str,
        controller_id: str,
        tick: int,
        dt_seconds: float,
    ) -> None:
        """Queue one accepted controller action for endpoint-backed delivery.

        This boundary deliberately holds serialized action data only.  It does
        not execute movement, fire, or message side effects; the session action
        pipeline claims a delivered record at its next authoritative boundary.
        """

        if action_kind not in {"persistent", "discrete"}:
            raise ValueError("controller action transport kind is invalid")
        action_id = getattr(action, "command_id", getattr(action, "action_id", None))
        entity_id = getattr(action, "entity_id", None)
        if not isinstance(action_id, str) or not action_id or not isinstance(entity_id, str):
            raise ValueError("controller action transport identity is invalid")
        transport_id = f"controller-command:{action_id}"
        if any(item.get("transport_id") == transport_id for item in self._command_queue):
            raise ValueError("controller action transport identity is already queued")
        try:
            claim = self.controller_ownership.by_controller(controller_id)
        except KeyError as error:
            raise ValueError("controller action transport controller is unknown") from error
        if entity_id not in claim.entity_ids:
            raise ValueError("controller action target is outside its claim")
        endpoint_id = claim.endpoint_entity_id
        recipient = self._entities.get(entity_id)
        if recipient is None:
            raise ValueError("controller action transport target is inactive")
        local = endpoint_id == entity_id
        legacy_adapter = endpoint_id is None
        if legacy_adapter:
            # Existing non-formal fixtures can only enter this path through the
            # explicit record marker. Formal V2 compilation requires an endpoint.
            endpoint_id = entity_id
            local = True
        route: tuple[str, ...]
        sender_profile: Mapping[str, object] | None = None
        recipient_profile: Mapping[str, object] | None = None
        if local:
            route = (entity_id,)
            delay_seconds = 0.0
            ttl_seconds = 0.0
            loss_probability = 0.0
            transport_status = "delivered"
            delivery_tick = tick
            expiry_tick = tick
            delay_ticks = 0
            loss_sample = 0.0
            loss_substream = f"communication:{transport_id}:zero-hop"
        else:
            if endpoint_id is None:
                raise ValueError("controller action endpoint is missing")
            sender = self._entities.get(endpoint_id)
            if sender is None:
                raise ValueError("controller action endpoint is inactive")
            sender_profile = self._communication_profile(entity=sender, tick=tick)
            recipient_profile = self._communication_profile(entity=recipient, tick=tick)
            if sender_profile is None or recipient_profile is None:
                raise ValueError("controller action transport requires communication endpoints")
            delay_seconds_value = sender_profile.get("delay_s", 0.0)
            ttl_seconds_value = sender_profile.get("ttl_s", 0.0)
            loss_probability_value = sender_profile.get("loss_probability", 0.0)
            if (
                any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    for value in (
                        delay_seconds_value,
                        ttl_seconds_value,
                        loss_probability_value,
                    )
                )
                or float(cast(float, delay_seconds_value)) < 0.0
                or float(cast(float, ttl_seconds_value)) < 0.0
                or not 0.0 <= float(cast(float, loss_probability_value)) <= 1.0
            ):
                raise ValueError("controller action transport profile is invalid")
            delay_seconds = float(cast(float, delay_seconds_value))
            ttl_seconds = float(cast(float, ttl_seconds_value))
            loss_probability = float(cast(float, loss_probability_value))
            ttl_ticks = 0 if ttl_seconds == 0.0 else max(1, math.ceil(ttl_seconds / dt_seconds))
            loss_substream = f"communication:{transport_id}"
            digest = hashlib.sha256(
                f"{self._session_seed}|{self._resolved_hash}|{tick}|{loss_substream}".encode()
            ).digest()
            loss_sample = int.from_bytes(digest[:8], "big") / float(2**64)
            route_value = self._communication_route(
                sender=sender,
                recipient=recipient,
                sender_profile=sender_profile,
                recipient_profile=recipient_profile,
                tick=tick,
            )
            scheduled = schedule_transport_v2(
                message_id=transport_id,
                origin_tick=tick,
                ttl_ticks=ttl_ticks,
                delay_seconds=delay_seconds,
                physics_dt_seconds=dt_seconds,
                link_available=route_value is not None,
                dropped=loss_sample < loss_probability,
            )
            route = route_value or ()
            transport_status = scheduled.status
            delivery_tick = scheduled.delivery_tick
            expiry_tick = scheduled.expiry_tick
            delay_ticks = scheduled.delay_ticks
        self._command_queue.append(
            _frozen_mapping(
                {
                    "transport_id": transport_id,
                    "action_id": action_id,
                    "action_kind": action_kind,
                    "action": action.model_dump(mode="json"),
                    "authority_token": authority_token,
                    "controller_id": controller_id,
                    "sender_entity_id": endpoint_id,
                    "recipient_entity_id": entity_id,
                    "generated_tick": tick,
                    "delay_seconds": delay_seconds,
                    "delay_ticks": delay_ticks,
                    "ttl_seconds": ttl_seconds,
                    "scheduled_delivery_tick": delivery_tick,
                    "expiry_tick": expiry_tick,
                    "transport_status": transport_status,
                    "route": route,
                    "relay_hops": 0 if len(route) < 2 else len(route) - 2,
                    "loss_probability": loss_probability,
                    "loss_sample": loss_sample,
                    "rng_substream": loss_substream,
                    "zero_hop": local,
                    "legacy_adapter_warning": (
                        "legacy-controller-endpoint@2.0" if legacy_adapter else None
                    ),
                    "execution_status": "pending",
                    "transport_receipt_version": "controller-command-transport@2.0",
                }
            )
        )

    def claim_resolved_controller_actions(self, *, tick: int) -> tuple[Mapping[str, Any], ...]:
        """Resolve due command transport and atomically claim each terminal record once."""

        updated: list[Mapping[str, Any]] = []
        claimed: list[Mapping[str, Any]] = []
        for item in self._command_queue:
            record = dict(item)
            if record.get("execution_status") != "pending":
                updated.append(_frozen_mapping(record))
                continue
            status = record.get("transport_status")
            if status == "queued":
                delivery_tick = record.get("scheduled_delivery_tick")
                expiry_tick = record.get("expiry_tick")
                route = record.get("route")
                recipient_id = record.get("recipient_entity_id")
                zero_hop = record.get("zero_hop")
                if (
                    not isinstance(delivery_tick, int)
                    or not isinstance(expiry_tick, int)
                    or not isinstance(recipient_id, str)
                    or not isinstance(zero_hop, bool)
                    or not isinstance(route, Sequence)
                    or isinstance(route, (str, bytes, bytearray))
                ):
                    raise ValueError("queued controller action transport evidence is invalid")
                if delivery_tick <= tick:
                    if delivery_tick > expiry_tick:
                        record["transport_status"] = "expired"
                        record["resolved_tick"] = tick
                    elif not zero_hop and (
                        recipient_id not in self._entities
                        or not self._communication_route_is_available(
                            route=cast(Sequence[str], route), tick=tick
                        )
                    ):
                        record["transport_status"] = "blocked"
                        record["resolved_tick"] = tick
                    else:
                        record["transport_status"] = "delivered"
                        record["delivered_tick"] = tick
            if record.get("transport_status") in {"delivered", "blocked", "dropped", "expired"}:
                record["execution_status"] = "claimed"
                record["claimed_tick"] = tick
                claimed.append(_frozen_mapping(record))
            updated.append(_frozen_mapping(record))
        self._command_queue = updated
        return tuple(sorted(claimed, key=lambda item: str(item["transport_id"])))

    def _surface_elevation_or_none(self, position_m: Sequence[float]) -> float | None:
        """Supply a geography-derived surface datum when a sensor explicitly needs AGL.

        ``None`` reaches the generic sensor boundary for worlds with no declared
        surface source; an AGL profile then fails closed there, while ordinary
        nominal-range sensors retain their established behavior.
        """

        try:
            return self._geography.surface_elevation_m(position_m)
        except GeographyErrorV2 as error:
            if error.code == "geography.surface_elevation_unavailable":
                return None
            raise

    def _advance_message_transport(self, *, tick: int) -> None:
        """Commit only due, non-expired transport records at an integer tick."""

        updated: list[Mapping[str, Any]] = []
        for item in self._message_queue:
            record = dict(item)
            if record.get("transport_status") != "queued":
                updated.append(_frozen_mapping(record))
                continue
            delivery_tick = record.get("scheduled_delivery_tick")
            expiry_tick = record.get("expiry_tick")
            recipient_id = record.get("recipient_entity_id")
            route = record.get("route")
            if (
                not isinstance(delivery_tick, int)
                or isinstance(delivery_tick, bool)
                or not isinstance(expiry_tick, int)
                or isinstance(expiry_tick, bool)
                or not isinstance(recipient_id, str)
                or not isinstance(route, Sequence)
                or isinstance(route, (str, bytes, bytearray))
            ):
                raise ValueError("queued communication transport evidence is invalid")
            if delivery_tick > tick:
                updated.append(_frozen_mapping(record))
                continue
            if delivery_tick > expiry_tick:
                record["transport_status"] = "expired"
                record["resolved_tick"] = tick
            else:
                recipient = self._entities.get(recipient_id)
                if (
                    recipient is None
                    or recipient.state.lifecycle not in {"active", "degraded"}
                    or (
                        not bool(record.get("zero_hop", False))
                        and not self._communication_route_is_available(
                            route=cast(Sequence[str], route), tick=tick
                        )
                    )
                ):
                    record["transport_status"] = "blocked"
                    record["resolved_tick"] = tick
                else:
                    record["transport_status"] = "delivered"
                    record["delivered_tick"] = tick
                    self._deliver_message_to_inboxes(record)
            updated.append(_frozen_mapping(record))
        self._message_queue = updated

    def _deliver_message_to_inboxes(self, record: Mapping[str, Any]) -> None:
        """Publish one delivered transport record to its explicit controller inboxes."""

        slots = record.get("recipient_controller_slots", ())
        if not isinstance(slots, (tuple, list)):
            raise ValueError("message recipient controller scope is invalid")
        delivered_tick = record.get("delivered_tick")
        expiry_tick = record.get("expiry_tick")
        message_id = record.get("message_id")
        if (
            not isinstance(delivered_tick, int)
            or not isinstance(expiry_tick, int)
            or not isinstance(message_id, str)
        ):
            raise ValueError("delivered message evidence is invalid")
        for slot_id in sorted(set(slots)):
            if not isinstance(slot_id, str):
                raise ValueError("message recipient controller slot is invalid")
            try:
                claim = self.controller_ownership.by_slot(slot_id)
            except KeyError as error:
                raise ValueError("message recipient controller slot is unknown") from error
            inbox = self._controller_inboxes.setdefault(slot_id, {})
            if message_id in inbox:
                continue
            for stale_id in tuple(
                key
                for key, message in inbox.items()
                if int(message.get("expiry_tick", -1)) < delivered_tick
            ):
                inbox.pop(stale_id)
            while len(inbox) >= claim.inbox_capacity:
                evicted_id = min(
                    inbox,
                    key=lambda key: (int(inbox[key].get("delivered_tick", -1)), key),
                )
                evicted = inbox.pop(evicted_id)
                self._inbox_evictions.append(
                    _frozen_mapping(
                        {
                            "event_type": "communication.inbox_evicted",
                            "controller_slot_id": slot_id,
                            "message_id": evicted_id,
                            "delivered_tick": evicted.get("delivered_tick"),
                            "evicted_at_tick": delivered_tick,
                        }
                    )
                )
            inbox[message_id] = _frozen_mapping(
                {
                    "message_id": message_id,
                    "origin_message_id": record.get("origin_message_id", message_id),
                    "sender_entity_id": record.get("sender_entity_id"),
                    "recipient_controller_slots": tuple(slots),
                    "sent_tick": record.get("generated_tick"),
                    "delivered_tick": delivered_tick,
                    "expiry_tick": expiry_tick,
                    "payload_type": "text/plain",
                    "payload": record.get("payload"),
                }
            )

    def _message_recipients(self, intent: MessageIntentV2) -> tuple[tuple[str | None, str], ...]:
        """Resolve only explicit controller/entity recipients at send time."""

        if intent.recipient_controller_slots:
            claims = []
            for slot_id in sorted(intent.recipient_controller_slots):
                try:
                    claims.append(self.controller_ownership.by_slot(slot_id))
                except KeyError as error:
                    raise ValueError("message controller recipient is unknown") from error
            recipients = []
            for claim in claims:
                if claim.endpoint_entity_id is None:
                    raise ValueError("message controller recipient lacks an explicit endpoint")
                recipients.append((claim.slot_id, claim.endpoint_entity_id))
            return tuple(recipients)
        if intent.broadcast_faction_id is not None:
            recipients = []
            for slot_id in self.controller_ownership.slot_ids:
                claim = self.controller_ownership.by_slot(slot_id)
                if claim.faction_id != intent.broadcast_faction_id:
                    continue
                if claim.endpoint_entity_id is None:
                    raise ValueError("broadcast recipient lacks an explicit endpoint")
                recipients.append((claim.slot_id, claim.endpoint_entity_id))
            if not recipients:
                raise ValueError("broadcast recipient faction has no controllers")
            return tuple(recipients)
        if intent.recipient_entity_id is None:
            raise ValueError("message recipient entity is missing")
        entity_claims = self.controller_ownership.by_entity(intent.recipient_entity_id)
        if not entity_claims:
            return ((None, intent.recipient_entity_id),)
        return tuple(
            (claim.slot_id, claim.endpoint_entity_id or intent.recipient_entity_id)
            for claim in entity_claims
        )

    def _apply_message_intents(
        self, intents: Sequence[MessageIntentV2], *, tick: int, dt_seconds: float
    ) -> None:
        for intent in intents:
            sender = self._entities.get(intent.sender_entity_id)
            if sender is None or intent.tick != tick:
                raise ValueError("communication intent references unavailable current entities")
            if sender.state.lifecycle not in {"active", "degraded"}:
                raise ValueError("communication intent references a lifecycle-inactive endpoint")
            if not sender.definition.resource_bindings.get("communications", ()):
                raise ValueError("communication intent requires endpoint capability")
            sender_profile = self._communication_profile(entity=sender, tick=tick)
            if sender_profile is None:
                raise ValueError("communication intent requires effective endpoint profiles")
            delay_seconds = sender_profile.get("delay_s", 0.0)
            ttl_seconds = sender_profile.get("ttl_s", 0.0)
            loss_probability = sender_profile.get("loss_probability", 0.0)
            if (
                isinstance(delay_seconds, bool)
                or not isinstance(delay_seconds, (int, float))
                or isinstance(ttl_seconds, bool)
                or not isinstance(ttl_seconds, (int, float))
                or isinstance(loss_probability, bool)
                or not isinstance(loss_probability, (int, float))
                or delay_seconds < 0.0
                or ttl_seconds < 0.0
                or not math.isfinite(float(delay_seconds))
                or not math.isfinite(float(ttl_seconds))
                or not math.isfinite(float(loss_probability))
            ):
                raise ValueError("communication delay, TTL, or loss profile is invalid")
            ttl_ticks = (
                0
                if float(ttl_seconds) == 0.0
                else max(1, math.ceil(float(ttl_seconds) / dt_seconds))
            )
            for slot_id, recipient_id in self._message_recipients(intent):
                recipient = self._entities.get(recipient_id)
                if recipient is None or recipient.state.lifecycle not in {"active", "degraded"}:
                    raise ValueError(
                        "communication intent references a lifecycle-inactive endpoint"
                    )
                if not recipient.definition.resource_bindings.get("communications", ()):
                    raise ValueError("communication intent requires endpoint capability")
                # A direct entity recipient has one controller claim under the
                # strict ownership contract, so its action identity remains the
                # transport identity.  Controller-slot and faction-broadcast
                # sends fan out and therefore receive one stable derived ID per
                # destination slot.
                message_id = (
                    intent.message_id
                    if intent.recipient_entity_id is not None or slot_id is None
                    else "message."
                    + hashlib.sha256(f"{intent.message_id}|{slot_id}".encode()).hexdigest()
                )
                if any(item.get("message_id") == message_id for item in self._message_queue):
                    raise ValueError("communication message identity is already used")
                recipient_profile = self._communication_profile(entity=recipient, tick=tick)
                if recipient_profile is None:
                    raise ValueError("communication intent requires effective endpoint profiles")
                loss_substream = f"communication:{message_id}"
                digest = hashlib.sha256(
                    f"{self._session_seed}|{self._resolved_hash}|{tick}|{loss_substream}".encode()
                ).digest()
                loss_sample = int.from_bytes(digest[:8], "big") / float(2**64)
                zero_hop = sender.id == recipient.id
                route = (
                    (sender.id,)
                    if zero_hop
                    else self._communication_route(
                        sender=sender,
                        recipient=recipient,
                        sender_profile=sender_profile,
                        recipient_profile=recipient_profile,
                        tick=tick,
                    )
                )
                transport = schedule_transport_v2(
                    message_id=message_id,
                    origin_tick=tick,
                    ttl_ticks=ttl_ticks,
                    delay_seconds=float(delay_seconds),
                    physics_dt_seconds=dt_seconds,
                    link_available=zero_hop or route is not None,
                    dropped=loss_sample < float(loss_probability),
                )
                self._message_queue.append(
                    _frozen_mapping(
                        {
                            "message_id": message_id,
                            "origin_message_id": intent.message_id,
                            "sender_entity_id": intent.sender_entity_id,
                            "recipient_entity_id": recipient_id,
                            "recipient_controller_slots": (() if slot_id is None else (slot_id,)),
                            "generated_tick": tick,
                            "payload": intent.payload,
                            "sender_communication_ref": sender_profile["exact_ref"],
                            "recipient_communication_ref": recipient_profile["exact_ref"],
                            "delay_seconds": float(delay_seconds),
                            "delay_ticks": transport.delay_ticks,
                            "ttl_seconds": float(ttl_seconds),
                            "ttl_ticks": ttl_ticks,
                            "scheduled_delivery_tick": transport.delivery_tick,
                            "expiry_tick": transport.expiry_tick,
                            "transport_status": transport.status,
                            "link_available": zero_hop or route is not None,
                            "route": route or (),
                            "relay_hops": 0 if route is None else len(route) - 2,
                            "zero_hop": zero_hop,
                            "loss_probability": float(loss_probability),
                            "loss_sample": loss_sample,
                            "rng_substream": loss_substream,
                        }
                    )
                )

    def _advance_missile_flights(
        self,
        *,
        tick: int,
        dt_seconds: float,
        prior_motion_positions: Mapping[str, tuple[float, float, float]],
    ) -> dict[str, DamageIntentV2]:
        """Integrate existing guided missiles after platform motion, before launch."""

        active: dict[str, MissileFlightV2] = {}
        damage: dict[str, DamageIntentV2] = {}
        for missile_id, flight in sorted(self._missile_flights.items()):
            target = self._entities.get(flight.target_id)
            target_start = (
                prior_motion_positions.get(flight.target_id) if target is not None else None
            )
            target_end = (
                cast(tuple[float, float, float], tuple(target.state.position_m))
                if target is not None
                else None
            )
            advance = advance_guided_missile_v2(
                flight,
                target_start_position_m=target_start,
                target_end_position_m=target_end,
                tick=tick,
                dt_seconds=dt_seconds,
            )
            if advance.status == "active":
                if advance.flight is None:
                    raise ValueError("active missile advance is missing flight state")
                active[missile_id] = advance.flight
                continue
            terminal_flight = flight.model_copy(
                update={
                    "seeker_state": "tracking" if advance.seeker_detected else flight.seeker_state,
                    "last_detection_tick": (
                        tick if advance.seeker_detected else flight.last_detection_tick
                    ),
                }
            )
            if advance.status == "fuse_candidate":
                combat_system = self._combat_system
                if combat_system is None:
                    raise ValueError("World missile resolution requires installed combat authority")
                if advance.closest_approach_m is None:
                    raise ValueError("missile terminal advance is missing closest approach")
                terminal, intent = combat_system.resolve_missile_terminal(
                    flight=terminal_flight,
                    tick=tick,
                    position_m=advance.position_m,
                    closest_approach_m=advance.closest_approach_m,
                    seeker_detected=advance.seeker_detected,
                    target_position_m=advance.target_position_m,
                    missile_velocity_mps=advance.missile_velocity_mps,
                    closest_approach_time_fraction=advance.closest_approach_time_fraction,
                    flight_evidence_hash=advance.evidence_hash,
                )
                if intent is not None:
                    damage[f"weapon:{intent.intent_id}"] = intent
            else:
                terminal = MissileTerminalReceiptV2(
                    missile_id=flight.missile_id,
                    request_id=flight.request_id,
                    launcher_id=flight.launcher_id,
                    target_id=flight.target_id,
                    tick=tick,
                    status=advance.status,
                    position_m=advance.position_m,
                    closest_approach_m=advance.closest_approach_m,
                    seeker_state=terminal_flight.seeker_state,
                    seeker_detected=advance.seeker_detected,
                    target_position_m=advance.target_position_m,
                    missile_velocity_mps=advance.missile_velocity_mps,
                    closest_approach_time_fraction=advance.closest_approach_time_fraction,
                    evidence_hash=advance.evidence_hash,
                )
            self._missile_terminal_receipts[missile_id] = terminal
        self._missile_flights = active
        return damage

    def _pending_lifecycle_entries(self) -> tuple[LifecycleScheduleEntryV2, ...]:
        """Return unresolved lifecycle entries in compiler-defined stable order."""

        return tuple(
            entry
            for entry in self.lifecycle_schedule
            if entry.source_event_id not in self._applied_lifecycle_event_ids
        )

    def _lifecycle_entries_at_pre_motion_boundary(
        self, *, expected_tick: int
    ) -> tuple[LifecycleScheduleEntryV2, ...]:
        """Project exactly the lifecycle batch ``advance_tick`` will apply first."""

        pending = self._pending_lifecycle_entries()
        if not pending or pending[0].tick > expected_tick + 1:
            return ()
        boundary_tick = pending[0].tick
        return tuple(entry for entry in pending if entry.tick == boundary_tick)

    @staticmethod
    def _fallback_controls_for_motion_binding(
        definition: ResolvedEntityV2,
        *,
        position_m: Sequence[float],
        heading_deg: float,
    ) -> Mapping[str, float]:
        dynamics_ref = definition.composition.dynamics_ref
        binding = next(
            (
                item
                for item in definition.resource_bindings.get("dynamics", ())
                if item.exact_ref == dynamics_ref
            ),
            None,
        )
        if dynamics_ref is None or binding is None:
            raise ValueError("motion-eligible entity has no exact dynamics binding")
        if binding.model_ref == FIXED_MODEL_REF:
            values: dict[str, float] = {}
        elif binding.model_ref == MMG_MODEL_REF:
            values = {"nps": 0.0, "rudder_rad": 0.0}
        else:
            values = {
                "target_speed_mps": 0.0,
                "target_heading_deg": float(heading_deg),
                "target_vertical_m": float(position_m[2]),
            }
        return MappingProxyType(dict(sorted(values.items())))

    @staticmethod
    def _has_motion_capability(
        tokens: Sequence[CapabilityTokenV2], *, dynamics_ref: str
    ) -> bool:
        return any(
            token.role == "dynamics"
            and token.operation == "move"
            and token.resource_ref == dynamics_ref
            for token in tokens
        )

    def _motion_eligibility_snapshot_locked(
        self, *, expected_tick: int
    ) -> MotionEligibilitySnapshotV2:
        """Build the sole lifecycle/capability-aware command projection.

        This is intentionally derived from current World state and the single
        next lifecycle batch; it is not saved in checkpoints and therefore
        cannot become a second mutable source of truth.
        """

        projected_runtime: dict[str, _RuntimeEntityV2] = dict(self._entities)
        projected_spawns: dict[str, ResolvedEntityV2] = {}
        for lifecycle_entry in self._lifecycle_entries_at_pre_motion_boundary(
            expected_tick=expected_tick
        ):
            if lifecycle_entry.event_type == "spawn":
                if lifecycle_entry.blueprint is None:
                    raise ValueError("scheduled spawn has no resolved entity blueprint")
                projected_runtime.pop(lifecycle_entry.entity_id, None)
                projected_spawns[lifecycle_entry.entity_id] = lifecycle_entry.blueprint
            elif lifecycle_entry.event_type == "despawn":
                projected_runtime.pop(lifecycle_entry.entity_id, None)
                projected_spawns.pop(lifecycle_entry.entity_id, None)
            else:
                raise ValueError("motion lifecycle projection has unsupported event type")

        active_entity_ids = tuple(
            sorted(
                (
                    *(
                        entity_id
                        for entity_id, entity in projected_runtime.items()
                        if entity.state.lifecycle in {"active", "degraded"}
                    ),
                    *projected_spawns,
                )
            )
        )
        entries: list[MotionEligibilityEntryV2] = []
        for entity_id, entity in sorted(projected_runtime.items()):
            dynamics_ref = entity.definition.composition.dynamics_ref
            if (
                entity.state.lifecycle not in {"active", "degraded"}
                or dynamics_ref is None
                or dynamics_ref not in entity.adapters
                or not self._has_motion_capability(
                    entity.capability_tokens, dynamics_ref=dynamics_ref
                )
            ):
                continue
            binding = next(
                (
                    item
                    for item in entity.definition.resource_bindings.get("dynamics", ())
                    if item.exact_ref == dynamics_ref
                ),
                None,
            )
            if binding is None:
                raise ValueError("motion-eligible entity has no exact dynamics binding")
            entries.append(
                MotionEligibilityEntryV2(
                    entity_id=entity_id,
                    dynamics_resource_ref=dynamics_ref,
                    model_ref=binding.model_ref,
                    fallback_controls=self._fallback_controls_for_motion_binding(
                        entity.definition,
                        position_m=entity.state.position_m,
                        heading_deg=entity.state.heading_deg,
                    ),
                )
            )
        for entity_id, definition in sorted(projected_spawns.items()):
            dynamics_ref = definition.composition.dynamics_ref
            tokens = capability_tokens_for_entity(definition)
            if dynamics_ref is None or not self._has_motion_capability(
                tokens, dynamics_ref=dynamics_ref
            ):
                continue
            binding = next(
                (
                    item
                    for item in definition.resource_bindings.get("dynamics", ())
                    if item.exact_ref == dynamics_ref
                ),
                None,
            )
            if binding is None:
                raise ValueError("scheduled motion entity has no exact dynamics binding")
            initial = definition.runtime_initial.initial_state
            entries.append(
                MotionEligibilityEntryV2(
                    entity_id=entity_id,
                    dynamics_resource_ref=dynamics_ref,
                    model_ref=binding.model_ref,
                    fallback_controls=self._fallback_controls_for_motion_binding(
                        definition,
                        position_m=initial.position_m,
                        heading_deg=initial.heading_deg,
                    ),
                )
            )
        entries.sort(key=lambda item: item.entity_id)
        payload = {
            "expected_tick": expected_tick,
            "world_tick": self.tick,
            "resolved_hash": self._resolved_hash,
            "active_entity_ids": active_entity_ids,
            "entries": tuple(
                {
                    "entity_id": item.entity_id,
                    "dynamics_resource_ref": item.dynamics_resource_ref,
                    "model_ref": item.model_ref,
                    "fallback_controls": dict(item.fallback_controls),
                }
                for item in entries
            ),
        }
        return MotionEligibilitySnapshotV2(
            expected_tick=expected_tick,
            world_tick=self.tick,
            resolved_hash=self._resolved_hash,
            active_entity_ids=active_entity_ids,
            entries=tuple(entries),
            fingerprint=_canonical_evidence_hash(payload),
        )

    def motion_eligibility_snapshot(self, *, expected_tick: int) -> MotionEligibilitySnapshotV2:
        """Return the immutable World-owned pre-motion eligibility projection."""

        with self._lock:
            if expected_tick != self.tick or self.tick != self._spatial_tick:
                raise ValueError("motion eligibility requires the current synchronized World tick")
            return self._motion_eligibility_snapshot_locked(expected_tick=expected_tick)

    def advance_tick(self, tick_input: WorldTickInputV2 | int) -> WorldTickReceiptV2:
        """Advance one append-only authoritative World tick.

        The competition runtime retains every successful tick receipt in
        memory and does not offer in-match rollback.  An unexpected pipeline
        failure therefore latches this World as failed; a caller must end the
        match rather than continue from a partially advanced state.
        """

        if isinstance(tick_input, int) and not isinstance(tick_input, bool):
            if tick_input != 0:
                raise ValueError("active World ticks require explicit WorldTickInputV2 evidence")
            return WorldTickReceiptV2(
                operation_id="world.tick.noop",
                start_tick=self.tick,
                tick=self.tick,
                steps=0,
                motion_receipts=(),
            )
        if not isinstance(tick_input, WorldTickInputV2):
            raise TypeError("World tick pipeline requires WorldTickInputV2")
        if tick_input.steps > 1:
            raise ValueError("multi-step World ticks require one command batch per tick")
        try:
            canonical_input = tick_input.model_dump(mode="json")
            fingerprint = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        canonical_input,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
            )
        except (TypeError, ValueError) as error:
            raise ValueError("World tick input is not canonical") from error
        with self._lock:
            prior_tick_receipt = self._world_tick_ledger.get(tick_input.operation_id)
            if prior_tick_receipt is not None:
                if prior_tick_receipt[0] != fingerprint:
                    raise ValueError("World tick operation identity conflicts with prior evidence")
                return prior_tick_receipt[1]
            if self._closed or self._transaction_active:
                raise ValueError("World tick cannot advance while a writer is active")
            if self._tick_failure_operation_id is not None:
                raise ValueError(
                    "World tick cannot continue after failed operation "
                    f"{self._tick_failure_operation_id}"
                )
            if tick_input.expected_tick != self.tick or self.tick != self._spatial_tick:
                raise ValueError("World tick input differs from the synchronized World clock")
            prior_tick = self.tick

            receipts: list[MotionReceiptV2] = []
            lifecycle_receipts: list[LifecycleReceiptV2] = []
            event_receipts: list[WorldEventReceiptV2] = []
            damage_receipts: list[Any] = []
            provider_receipts: list[str] = []
            dynamics_receipts: list[DynamicsStepReceiptV2] = []
            mission_receipts: list[Any] = []
            score_receipts: list[Any] = []
            combat_receipts: list[WorldCombatDispatchReceiptV2] = []
            subsystem_receipts: list[GenericSubsystemTickReceiptV2] = []
            self._deferred_lifecycle_despawns = []
            try:
                for offset in range(tick_input.steps):
                    step_tick = prior_tick + offset
                    spatial_entity_ids_before_lifecycle = frozenset(self._entities)
                    pending = self._pending_lifecycle_entries()
                    if not pending:
                        try:
                            self.advance_lifecycle(
                                expected_tick=step_tick + 1,
                                operation_id=f"{tick_input.operation_id}:lifecycle:{step_tick}",
                            )
                        except FactoryErrorV2 as error:
                            if error.code != "factory.lifecycle_no_pending_transition":
                                raise
                    elif self._lifecycle_entries_at_pre_motion_boundary(
                        expected_tick=step_tick
                    ):
                        lifecycle_receipts.append(
                            self.advance_lifecycle(
                                expected_tick=pending[0].tick,
                                operation_id=f"{tick_input.operation_id}:lifecycle:{step_tick}",
                            )
                        )
                        # The lifecycle boundary belongs to the end of this
                        # interval; damage still targets the interval's tick.
                        self.tick = step_tick
                    if frozenset(self._entities) != spatial_entity_ids_before_lifecycle:
                        self._rebuild_spatial_runtime_after_lifecycle()
                    active_dynamics_after_lifecycle = frozenset(
                        self._motion_eligibility_snapshot_locked(
                            expected_tick=step_tick
                        ).entity_ids
                    )
                    candidates, provider_receipt, step_dynamics_receipts = (
                        self._invoke_motion_provider(
                            tick_input=tick_input,
                            step_tick=step_tick,
                            expected_entity_ids=active_dynamics_after_lifecycle,
                        )
                    )
                    wreck_candidates = tuple(
                        KinematicMotionCandidateV2(
                            entity_id=entity_id,
                            position_m=cast(
                                tuple[float, float, float], tuple(entity.state.position_m)
                            ),
                            velocity_mps=(0.0, 0.0, 0.0),
                            resolved_hash=self._resolved_hash,
                            provenance_kind="lifecycle_wreck",
                        )
                        for entity_id, entity in sorted(self._entities.items())
                        if self._is_static_wreck(entity_id)
                    )
                    candidates = (*candidates, *wreck_candidates)
                    prior_motion_positions: dict[str, tuple[float, float, float]] = {
                        entity_id: cast(tuple[float, float, float], tuple(entity.state.position_m))
                        for entity_id, entity in self._entities.items()
                    }
                    dynamics_receipts.extend(step_dynamics_receipts)
                    self._active_motion_provider_receipt = provider_receipt
                    try:
                        receipt = self.apply_motion_candidates(
                            candidates,
                            expected_tick=step_tick,
                            operation_id=f"world.tick.{step_tick}",
                            dt_seconds=tick_input.dt_seconds,
                            tick_start_time_seconds=self._spatial_time_seconds,
                            _require_resolved_damage_evidence=True,
                        )
                    finally:
                        self._active_motion_provider_receipt = None
                    provider_receipts.append(provider_receipt)
                    receipts.append(receipt)
                    self._record_mission_zone_transitions(receipt, prior_motion_positions)
                    self._apply_message_intents(
                        tick_input.message_intents,
                        tick=step_tick,
                        dt_seconds=tick_input.dt_seconds,
                    )
                    self._advance_message_transport(tick=step_tick)
                    subsystem_receipts.append(
                        self._evaluate_generic_subsystems(
                            tick=step_tick, dt_seconds=tick_input.dt_seconds
                        )
                    )
                    self._advance_shared_contact_transport(tick=step_tick)
                    missile_damage = self._advance_missile_flights(
                        tick=step_tick,
                        dt_seconds=tick_input.dt_seconds,
                        prior_motion_positions=prior_motion_positions,
                    )
                    pending_impact_damage: dict[str, DamageIntentV2] = {}
                    if self._pending_impacts:
                        combat_system = self._combat_system
                        if combat_system is None:
                            raise ValueError(
                                "World delayed impact resolution requires "
                                "installed combat authority"
                            )
                        _pending_receipts, pending_impact_damage = (
                            combat_system.resolve_pending_impacts(expected_tick=step_tick)
                        )
                    if tick_input.engagement_requests:
                        combat_system = self._combat_system
                        if combat_system is None:
                            raise ValueError("World tick combat authority is not installed")
                        try:
                            executions = combat_system.execute_batch(
                                tick_input.engagement_requests,
                                expected_tick=step_tick,
                                operation_id=f"{tick_input.operation_id}:combat:{step_tick}",
                            )
                        except CombatErrorV2 as error:
                            combat_receipts.extend(
                                WorldCombatDispatchReceiptV2(
                                    request_id=request.request_id,
                                    tick=step_tick,
                                    status="rejected",
                                    error_code=error.code,
                                )
                                for request in tick_input.engagement_requests
                            )
                        else:
                            combat_receipts.extend(
                                WorldCombatDispatchReceiptV2(
                                    request_id=request.request_id,
                                    tick=step_tick,
                                    status="executed",
                                    execution=execution,
                                )
                                for request, execution in zip(
                                    tick_input.engagement_requests, executions, strict=True
                                )
                            )
                    event_receipt, trusted_damage, trigger_lifecycle_requests = (
                        self._execute_typed_events(
                            motion_receipt=receipt,
                            prior_motion_positions=prior_motion_positions,
                            operation_id=f"{tick_input.operation_id}:events:{step_tick}",
                        )
                    )
                    all_damage_sources = (missile_damage, pending_impact_damage, trusted_damage)
                    if sum(len(source) for source in all_damage_sources) != len(
                        set().union(*(set(source) for source in all_damage_sources))
                    ):
                        raise ValueError("World damage identities conflict")
                    trusted_damage = {
                        **missile_damage,
                        **pending_impact_damage,
                        **trusted_damage,
                    }
                    event_receipts.append(event_receipt)
                    self._active_typed_event_receipts = event_receipt.typed_event_receipts
                    try:
                        score_event_ids = set(self._mission_engine.event_score_policy_event_ids)
                        for typed_event_receipt in event_receipt.typed_event_receipts:
                            if typed_event_receipt.event_id in score_event_ids:
                                self._mission_engine.apply_authoritative_event(
                                    event_receipt=typed_event_receipt
                                )
                    finally:
                        self._active_typed_event_receipts = ()
                    damage_receipt = self.apply_damage_transaction(
                        intents=trusted_damage,
                        expected_tick=step_tick,
                        operation_id=f"{tick_input.operation_id}:damage:{step_tick}",
                    )
                    damage_receipts.append(damage_receipt)
                    self._finalize_destroyed_lifecycle(
                        damage_receipt=damage_receipt,
                        spatial_requests=trigger_lifecycle_requests,
                        expected_tick=step_tick,
                    )
                    # Mission and score conditions describe the state after
                    # this complete physical interval.  Advancing the World
                    # clock before evaluating them makes a duration of N
                    # one-second ticks observable as tick N, rather than
                    # leaving the final time condition at N - 1.
                    self.tick = receipt.next_tick
                    mission_receipts.append(
                        self._mission_engine.evaluate_tick(
                            expected_tick=receipt.next_tick,
                            operation_id=f"{tick_input.operation_id}:mission:{receipt.next_tick}",
                        )
                    )
                    score_receipts.append(
                        self._mission_engine.evaluate_scoring(
                            expected_tick=receipt.next_tick,
                            operation_id=f"{tick_input.operation_id}:scoring:{receipt.next_tick}",
                        )
                    )
                    self._combat_cooldowns = {
                        key: max(0, value - 1) for key, value in self._combat_cooldowns.items()
                    }
                    fault_after = self.lifecycle_fault_injector.fail_after_created_adapters
                    if fault_after is not None and len(receipts) >= fault_after:
                        raise RuntimeError("injected World tick pipeline failure")
                deferred_despawns = tuple(self._deferred_lifecycle_despawns)
                self._deferred_lifecycle_despawns = None
                cleanup_errors = self._finalize_lifecycle_despawns(deferred_despawns)
                if cleanup_errors:
                    lifecycle_receipts = [
                        (
                            LifecycleReceiptV2(
                                tick=item.tick,
                                operation_id=item.operation_id,
                                status="committed_with_cleanup_errors",
                                applied_event_ids=item.applied_event_ids,
                                spawned_entity_ids=item.spawned_entity_ids,
                                despawned_entity_ids=item.despawned_entity_ids,
                            )
                            if item.despawned_entity_ids
                            else item
                        )
                        for item in lifecycle_receipts
                    ]
                    for item in lifecycle_receipts:
                        self._lifecycle_ledger[item.operation_id] = item
                result = WorldTickReceiptV2(
                    operation_id=tick_input.operation_id,
                    start_tick=prior_tick,
                    tick=self.tick,
                    steps=tick_input.steps,
                    motion_receipts=tuple(receipts),
                    lifecycle_receipts=tuple(lifecycle_receipts),
                    event_receipts=tuple(event_receipts),
                    damage_receipts=tuple(damage_receipts),
                    provider_receipts=tuple(provider_receipts),
                    dynamics_receipts=tuple(dynamics_receipts),
                    mission_receipts=tuple(mission_receipts),
                    score_receipts=tuple(score_receipts),
                    combat_receipts=tuple(combat_receipts),
                    subsystem_receipts=tuple(subsystem_receipts),
                )
                self._world_tick_ledger[tick_input.operation_id] = (fingerprint, result)
                self._index_typed_event_receipts(result.event_receipts)
                self._world_adapter_transaction_audit.append(
                    WorldAdapterTransactionV2(
                        operation_id=tick_input.operation_id,
                        status="committed",
                    )
                )
                return result
            except Exception:
                self._deferred_lifecycle_despawns = None
                self._active_motion_provider_receipt = None
                self._active_typed_event_receipts = ()
                self._tick_failure_operation_id = tick_input.operation_id
                self._world_adapter_transaction_audit.append(
                    WorldAdapterTransactionV2(
                        operation_id=tick_input.operation_id,
                        status="failed_no_rollback",
                    )
                )
                raise

    @property
    def entity_ids(self) -> tuple[str, ...]:
        return tuple(self._entities)

    @property
    def failed_tick_operation_id(self) -> str | None:
        """Return the failed append-only tick that makes this World terminal."""

        return self._tick_failure_operation_id

    @property
    def missile_flights(self) -> tuple[MissileFlightV2, ...]:
        """Active guided missiles in stable launch identity order."""

        with self._lock:
            return tuple(self._missile_flights[key] for key in sorted(self._missile_flights))

    @property
    def pending_impacts(self) -> tuple[Any, ...]:
        """Queued delayed combat effects in stable identity order."""

        with self._lock:
            return tuple(self._pending_impacts[key] for key in sorted(self._pending_impacts))

    @property
    def pending_impact_receipts(self) -> tuple[Any, ...]:
        """Consumed delayed combat effects in stable identity order."""

        with self._lock:
            return tuple(
                self._pending_impact_receipts[key] for key in sorted(self._pending_impact_receipts)
            )

    @property
    def spatial_effect_trigger_ledger(self) -> Mapping[str, Mapping[str, Any]]:
        """Read-only authority evidence for one-shot spatial effect applications."""

        with self._lock:
            return MappingProxyType(dict(sorted(self._spatial_effect_trigger_ledger.items())))

    @property
    def spatial_effect_trigger_consumption(self) -> Mapping[str, Mapping[str, Any]]:
        """Read-only per-trigger/per-source consumption evidence."""

        with self._lock:
            return MappingProxyType(dict(sorted(self._spatial_effect_trigger_consumption.items())))

    @property
    def destroyed_lifecycle_ledger(self) -> Mapping[str, Mapping[str, Any]]:
        """Read-only generic destruction-policy evidence by entity identity."""

        with self._lock:
            return MappingProxyType(dict(sorted(self._destroyed_lifecycle_ledger.items())))

    @property
    def missile_terminal_receipts(self) -> tuple[MissileTerminalReceiptV2, ...]:
        """Terminal guided-missile evidence in stable missile identity order."""

        with self._lock:
            return tuple(
                self._missile_terminal_receipts[key]
                for key in sorted(self._missile_terminal_receipts)
            )

    @property
    def faction_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.factions)

    def _shared_observation_unavailable_entity_ids(self) -> frozenset[str]:
        """Return endpoints whose active jamming removes them from faction sharing."""

        unavailable: set[str] = set()
        for session in self._jamming_sessions.values():
            if not isinstance(session, Mapping):
                continue
            target_entity_id = session.get("target_entity_id")
            if isinstance(target_entity_id, str) and target_entity_id in self._entities:
                unavailable.add(target_entity_id)
        return frozenset(unavailable)

    def controller_observation_snapshot(self, *, controller_slot_id: str) -> ObservationV2:
        """Build the strict claim-scoped controller observation contract.

        A claim determines the only own-state and action targets exposed to a
        controller.  Endpoint reports are organic.  Transport-derived shared
        contacts and inbox records are added in EF-06B and EF-06D respectively.
        """

        with self._lock:
            try:
                claim = self.controller_ownership.by_slot(controller_slot_id)
            except KeyError as error:
                raise ValueError("controller slot is not part of the resolved World") from error
            controlled_ids = tuple(
                entity_id
                for entity_id in claim.entity_ids
                if (
                    (entity := self._entities.get(entity_id)) is not None
                    and entity.state.lifecycle in {"active", "degraded"}
                )
            )
            own_entities = tuple(
                {
                    "entity_id": entity.id,
                    "lifecycle_state": entity.state.lifecycle,
                    "position_m": tuple(entity.state.position_m),
                    "velocity_mps": tuple(entity.state.velocity_mps),
                    "heading_deg": entity.state.heading_deg,
                    "health": entity.state.health,
                    "energy": entity.state.energy,
                }
                for entity in self.entities_stable()
                if entity.id in controlled_ids
            )
            endpoint = claim.endpoint_entity_id
            organic_contacts = tuple(
                {
                    "contact_id": evidence_id,
                    "observer_entity_id": record.owner_entity_id,
                    "estimated_position_m": (
                        record.measurement_position_m
                        if record.measurement_position_m is not None
                        else _estimated_contact_position_v2(
                            evidence_id,
                            record.observed_tick,
                            record.confidence,
                            self._entities[record.target_entity_id].state.position_m,
                        )
                    ),
                    "observed_tick": record.observed_tick,
                    "age_ticks": max(record.age_ticks, self.tick - record.observed_tick),
                    "confidence": record.confidence,
                    "quality": record.quality,
                }
                for evidence_id, records in sorted(self.contact_store.records.items())
                for record in records
                if record.owner_entity_id == endpoint
                and record.target_entity_id in self._entities
                and record.confirmed
            )
            return ObservationV2(
                schema_version="2.0",
                session_id=self.session_id,
                tick=self.tick,
                observer_faction_id=claim.faction_id,
                controller_slot_id=claim.slot_id,
                controlled_entity_ids=controlled_ids,
                own_entities=own_entities,
                organic_contacts=organic_contacts,
                shared_contacts=tuple(
                    dict(records[contact_id])
                    for records in (self._shared_contacts_by_controller.get(claim.slot_id, {}),)
                    for contact_id in sorted(records)
                    if int(records[contact_id].get("expiry_tick", self.tick)) >= self.tick
                ),
                received_messages=tuple(
                    dict(messages[message_id])
                    for messages in (self._controller_inboxes.get(claim.slot_id, {}),)
                    for message_id in sorted(
                        messages,
                        key=lambda key: (
                            int(messages[key].get("delivered_tick", -1)),
                            key,
                        ),
                    )
                    if int(messages[message_id].get("expiry_tick", self.tick)) >= self.tick
                ),
                contacts_by_faction={},
                metadata={
                    "resolved_hash": self._resolved_hash,
                    "catalog_hash": self._catalog_hash,
                    "controller_scope_contract": "controller-scope@2.0",
                    "controller_endpoint_ref": endpoint,
                    "communication_schema_version": "communication@2.0",
                    "scope_is_not_authentication": True,
                },
            )

    def legacy_faction_observation_snapshot(self, *, observer_faction_id: str) -> ObservationV2:
        """Return the explicitly marked legacy faction-scoped adapter.

        It preserves the historical limited faction data shape for un-migrated
        clients.  It never impersonates a strict controller-scoped observation.
        """

        if observer_faction_id not in self.faction_ids:
            raise ValueError("observation faction is not part of the resolved World")
        with self._lock:
            owners = {
                entity.id
                for entity in self._entities.values()
                if entity.faction_id == observer_faction_id
            }
            shared_reporter_ids = owners - self._shared_observation_unavailable_entity_ids()
            own_entities = tuple(
                {
                    "entity_id": entity.id,
                    "lifecycle_state": entity.state.lifecycle,
                    "position_m": tuple(entity.state.position_m),
                    "velocity_mps": tuple(entity.state.velocity_mps),
                    "heading_deg": entity.state.heading_deg,
                    "health": entity.state.health,
                    "energy": entity.state.energy,
                }
                for entity in self.entities_stable()
                if entity.id in owners
            )
            contacts = tuple(
                {
                    "contact_id": evidence_id,
                    "observer_entity_id": record.owner_entity_id,
                    "estimated_position_m": (
                        record.measurement_position_m
                        if record.measurement_position_m is not None
                        else _estimated_contact_position_v2(
                            evidence_id,
                            record.observed_tick,
                            record.confidence,
                            self._entities[record.target_entity_id].state.position_m,
                        )
                    ),
                    "observed_tick": record.observed_tick,
                    "age_ticks": max(record.age_ticks, self.tick - record.observed_tick),
                    "confidence": record.confidence,
                    "quality": record.quality,
                }
                for evidence_id, records in sorted(self.contact_store.records.items())
                for record in records
                if record.owner_entity_id in shared_reporter_ids
                and record.target_entity_id in self._entities
                and record.confirmed
            )
            return ObservationV2(
                schema_version="2.0",
                session_id=self.session_id,
                tick=self.tick,
                observer_faction_id=observer_faction_id,
                own_entities=own_entities,
                contacts_by_faction={observer_faction_id: contacts},
                metadata={
                    "resolved_hash": self._resolved_hash,
                    "catalog_hash": self._catalog_hash,
                    "compatibility_adapter": "legacy-faction-observation@2.0",
                    "compatibility_warning": (
                        "faction-scoped observation is legacy; "
                        "use controller_observation_snapshot"
                    ),
                },
            )

    def observation_snapshot(self, *, observer_faction_id: str) -> ObservationV2:
        """Backward-compatible alias for the explicitly marked legacy adapter."""

        return self.legacy_faction_observation_snapshot(observer_faction_id=observer_faction_id)

    @property
    def used_entity_ids(self) -> frozenset[str]:
        return frozenset(self._used_entity_ids)

    @property
    def lifecycle_ledger(self) -> Mapping[str, LifecycleReceiptV2]:
        return frozen_ledger(self._lifecycle_ledger)

    @property
    def tombstones(self) -> Mapping[str, LifecycleTombstoneV2]:
        return frozen_tombstones(self._tombstones)

    @property
    def lifecycle_audit(self) -> tuple[LifecycleAuditRecordV2, ...]:
        return tuple(self._lifecycle_audit)

    @property
    def checkpoint_restore_audit(self) -> tuple[CheckpointRestoreAuditV2, ...]:
        return self._checkpoint_restore_audit

    @property
    def motion_ledger(self) -> Mapping[str, MotionReceiptV2]:
        return MappingProxyType(dict(self._motion_ledger))

    @property
    def boundary_topology_hash(self) -> str:
        return self._spatial_topology_hash

    @property
    def resolved_hash(self) -> str:
        return self._resolved_hash

    def zone_activation_snapshot(self) -> ZoneActivationSnapshotV2:
        with self._lock:
            return ZoneActivationSnapshotV2.build(
                self._zone_activation, self._zone_activation_ledger
            )

    def set_zone_activation(
        self,
        *,
        zone_id: str,
        active: bool,
        expected_tick: int,
        operation_id: str,
    ) -> ZoneActivationReceiptV2:
        with self._lock:
            if self._transaction_active:
                raise _motion_error(
                    "world.motion_writer_active",
                    ("world", "zone_activation"),
                    operation_id,
                    "zone activation cannot interleave with the World motion writer",
                    "retry after the active World transaction completes",
                )
            if expected_tick != self._spatial_tick:
                raise _motion_error(
                    "world.spatial_tick_conflict",
                    ("world", "spatial_tick"),
                    expected_tick,
                    "zone activation expected tick differs from the spatial clock",
                    "retry against the latest spatial tick",
                )
            if (
                not isinstance(zone_id, str)
                or not zone_id
                or not isinstance(active, bool)
                or not isinstance(operation_id, str)
                or not operation_id
            ):
                raise _motion_error(
                    "world.zone_activation_invalid",
                    ("world", "zone_activation"),
                    operation_id,
                    "zone activation requires bounded typed identities and boolean state",
                    "provide a nonempty zone and operation ID with a boolean active value",
                )
            previous = self._zone_activation_ledger.get(operation_id)
            if previous is not None:
                if (previous.zone_id, previous.active, previous.tick) != (
                    zone_id,
                    active,
                    expected_tick,
                ):
                    raise _motion_error(
                        "world.zone_operation_conflict",
                        ("world", "zone_activation", "operation_id"),
                        operation_id,
                        "zone operation identity was reused with different parameters",
                        "reuse it only for an identical retry",
                    )
                return previous
            changed = self._zone_activation.get(zone_id, True) != active
            receipt = ZoneActivationReceiptV2(
                operation_id=operation_id,
                zone_id=zone_id,
                active=active,
                tick=expected_tick,
                changed=changed,
            )
            self._zone_activation[zone_id] = active
            self._zone_activation_ledger[operation_id] = receipt
            if zone_id in getattr(self._boundary_system, "_zone_activation", {}):
                self._boundary_system.set_zone_activation(
                    zone_id=zone_id,
                    active=active,
                    tick=expected_tick,
                    operation_id=operation_id,
                )
            return receipt

    def entities_stable(self) -> tuple[EntityViewV2, ...]:
        with self._lock:
            return tuple(
                _entity_view(self._entities[identifier], adapters_closed=self._closed)
                for identifier in self.entity_ids
            )

    def get(self, entity_id: str) -> EntityViewV2:
        try:
            with self._lock:
                return _entity_view(self._entities[entity_id], adapters_closed=self._closed)
        except KeyError as error:
            raise _factory_error(
                "factory.entity_unknown",
                ("entities", entity_id),
                entity_id,
                "entity is not present in the current runtime world",
                "use get_optional or query a current stable entity identifier",
            ) from error

    def get_optional(self, entity_id: str) -> EntityViewV2 | None:
        with self._lock:
            entity = self._entities.get(entity_id)
            return None if entity is None else _entity_view(entity, adapters_closed=self._closed)

    def query(
        self,
        *,
        capability: str | None = None,
        domain: str | None = None,
        faction_id: str | None = None,
        tag: str | None = None,
        all_capabilities: Sequence[CapabilitySelectorV2] | None = None,
        any_capabilities: Sequence[CapabilitySelectorV2] | None = None,
    ) -> tuple[EntityViewV2, ...]:
        scalar_filters = {
            "capability": capability,
            "domain": domain,
            "faction_id": faction_id,
            "tag": tag,
        }
        selector_filters = {
            "all_capabilities": all_capabilities,
            "any_capabilities": any_capabilities,
        }
        invalid_scalar = next(
            (
                name
                for name, value in scalar_filters.items()
                if value is not None and not isinstance(value, str)
            ),
            None,
        )
        invalid_selectors = next(
            (
                name
                for name, value in selector_filters.items()
                if value is not None
                and (
                    not isinstance(value, Sequence)
                    or isinstance(value, (str, bytes, bytearray))
                    or any(not isinstance(item, CapabilitySelectorV2) for item in value)
                )
            ),
            None,
        )
        if invalid_scalar is not None or invalid_selectors is not None:
            field = invalid_scalar if invalid_scalar is not None else invalid_selectors
            if field is None:  # Defensive narrowing; condition above makes this unreachable.
                raise RuntimeError("query validation field is unavailable")
            raise _factory_error(
                "factory.query_invalid",
                ("world", "query", field),
                type((scalar_filters | selector_filters)[field]).__name__,
                "world query filters must use canonical string or typed selector values",
                "provide strings for scalar filters and sequences of CapabilitySelectorV2",
            )
        criteria = (
            ("capability", capability),
            ("domain", domain),
            ("faction", faction_id),
            ("tag", tag),
        )
        identifiers: set[str] | None = None
        for index_name, value in criteria:
            if value is None:
                continue
            matches = set(self._indexes[index_name].get(value, ()))
            identifiers = matches if identifiers is None else identifiers & matches
        selected = set(self.entity_ids) if identifiers is None else identifiers
        if all_capabilities is not None:
            selected = {
                identifier
                for identifier in selected
                if all(
                    any(
                        selector.matches(token)
                        for token in self._entities[identifier].capability_tokens
                    )
                    for selector in all_capabilities
                )
            }
        if any_capabilities is not None:
            selected = {
                identifier
                for identifier in selected
                if any(
                    selector.matches(token)
                    for selector in any_capabilities
                    for token in self._entities[identifier].capability_tokens
                )
            }
        with self._lock:
            return tuple(
                _entity_view(self._entities[key], adapters_closed=self._closed)
                for key in self.entity_ids
                if key in selected
            )

    def snapshot(self) -> WorldSnapshotV2:
        with self._lock:
            return WorldSnapshotV2(
                tick=self.tick,
                entities=tuple(
                    _entity_view(self._entities[identifier], adapters_closed=self._closed)
                    for identifier in self.entity_ids
                ),
            )

    def native_adapter_snapshots(
        self,
    ) -> Mapping[tuple[str, str], NativeDynamicsSnapshotV2]:
        with self._lock:
            snapshots: dict[tuple[str, str], NativeDynamicsSnapshotV2] = {}
            for entity_id, entity in self._entities.items():
                for resource_ref, adapter in entity.adapters.items():
                    snapshot = getattr(adapter, "snapshot", None)
                    if not callable(snapshot):
                        continue
                    value = snapshot()
                    if isinstance(value, NativeDynamicsSnapshotV2):
                        snapshots[(entity_id, resource_ref)] = value
            return MappingProxyType(dict(sorted(snapshots.items())))

    def apply_motion_candidates(
        self,
        candidates: Sequence[MotionCandidateV2 | KinematicMotionCandidateV2],
        *,
        expected_tick: int,
        operation_id: str,
        dt_seconds: float,
        tick_start_time_seconds: float | None = None,
        _require_resolved_damage_evidence: bool = False,
    ) -> MotionReceiptV2:
        """Adjudicate and atomically commit one deterministic spatial tick."""

        with self._lock:
            if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 256:
                raise _motion_error(
                    "world.motion_operation_invalid",
                    ("world", "motion", "operation_id"),
                    operation_id,
                    "motion operation identity must be a bounded nonempty string",
                    "provide one stable operation identity per spatial tick",
                )
            if not isinstance(candidates, Sequence) or isinstance(
                candidates, (str, bytes, bytearray)
            ):
                raise _motion_error(
                    "world.motion_candidate_invalid",
                    ("world", "motion", "candidates"),
                    type(candidates).__name__,
                    "motion candidates must be a typed finite sequence",
                    "provide MotionCandidateV2 values",
                )
            try:
                dt = float(dt_seconds)
            except (TypeError, ValueError) as error:
                raise _motion_error(
                    "world.motion_candidate_invalid",
                    ("world", "motion", "dt_seconds"),
                    dt_seconds,
                    "motion duration must be positive and finite",
                    "provide a positive finite duration in seconds",
                ) from error
            if (
                isinstance(dt_seconds, bool)
                or not math.isfinite(dt)
                or dt <= 0.0
                or not isinstance(expected_tick, int)
                or isinstance(expected_tick, bool)
                or expected_tick < 0
            ):
                raise _motion_error(
                    "world.motion_candidate_invalid",
                    ("world", "motion", "clock"),
                    (expected_tick, dt_seconds),
                    "motion clock requires a nonnegative exact tick and positive finite duration",
                    "provide the current spatial tick and a positive duration",
                )
            if tick_start_time_seconds is None:
                tick_start = self._spatial_time_seconds
            elif (
                isinstance(tick_start_time_seconds, bool)
                or not isinstance(tick_start_time_seconds, (int, float))
                or not math.isfinite(float(tick_start_time_seconds))
                or float(tick_start_time_seconds) < self._spatial_time_seconds
            ):
                raise _motion_error(
                    "world.motion_candidate_invalid",
                    ("world", "motion", "tick_start_time_seconds"),
                    tick_start_time_seconds,
                    "explicit tick start must be finite and monotonic",
                    "provide the authoritative start time for this spatial tick",
                )
            else:
                tick_start = float(tick_start_time_seconds)
            ordered = tuple(sorted(candidates, key=lambda item: getattr(item, "entity_id", "")))
            fingerprint_payload: list[object] = [expected_tick, dt, tick_start]
            staged_vectors: dict[
                str,
                tuple[
                    tuple[float, float, float],
                    tuple[float, float, float],
                    str | None,
                    float | None,
                ],
            ] = {}
            try:
                for index, candidate in enumerate(ordered):
                    if not isinstance(candidate, (MotionCandidateV2, KinematicMotionCandidateV2)):
                        raise TypeError(f"candidate {index} has an unsupported typed boundary")
                    if (
                        not candidate.entity_id
                        or candidate.entity_id not in self._entities
                        or len(candidate.position_m) != 3
                        or len(candidate.velocity_mps) != 3
                    ):
                        raise ValueError(f"candidate {index} identity or vector shape is invalid")
                    position = tuple(float(item) for item in candidate.position_m)
                    velocity = tuple(float(item) for item in candidate.velocity_mps)
                    if any(not math.isfinite(item) for item in (*position, *velocity)):
                        raise ValueError(f"candidate {index} contains a non-finite axis")
                    raw_heading = getattr(candidate, "heading_deg", None)
                    if raw_heading is None:
                        heading: float | None = None
                    elif isinstance(raw_heading, bool) or not isinstance(raw_heading, (int, float)):
                        raise ValueError(f"candidate {index} heading is invalid")
                    elif not math.isfinite(float(raw_heading)):
                        raise ValueError(f"candidate {index} heading is non-finite")
                    else:
                        heading = float(raw_heading) % 360.0
                    if candidate.entity_id in staged_vectors:
                        raise ValueError(f"candidate {index} duplicates an entity")
                    runtime_entity = self._entities[candidate.entity_id]
                    if isinstance(candidate, MotionCandidateV2):
                        runtime_entity = self._entities[candidate.entity_id]
                        resource_ref = cast(str, candidate.dynamics_resource_ref)
                        adapter = runtime_entity.adapters.get(resource_ref)
                        binding = next(
                            (
                                item
                                for item in runtime_entity.definition.resource_bindings.get(
                                    "dynamics", ()
                                )
                                if item.exact_ref == resource_ref
                            ),
                            None,
                        )
                        if adapter is None or binding is None:
                            raise ValueError(f"candidate {index} dynamics resource is not owned")
                        diagnostic = _entity_view(runtime_entity).adapter_diagnostics[resource_ref]
                        consumption_receipt = (
                            self._active_motion_provider_receipt or candidate.provider_receipt
                        )
                        if (
                            candidate.model_ref != binding.model_ref
                            or candidate.dynamics_model_ref != binding.model_ref
                            or candidate.adapter_instance_id != diagnostic.instance_id
                            or candidate.resolved_hash != self._resolved_hash
                            or candidate.provider_receipt != diagnostic.last_output_receipt
                            or (
                                consumption_receipt in self._consumed_provider_receipts
                                and operation_id not in self._motion_ledger
                            )
                        ):
                            raise ValueError(
                                f"candidate {index} provider evidence is forged or replayed"
                            )
                        dynamics_model_ref = candidate.model_ref
                        provenance_payload: object = [
                            "dynamics",
                            resource_ref,
                            dynamics_model_ref,
                            candidate.adapter_instance_id,
                            candidate.resolved_hash,
                            candidate.provider_receipt,
                        ]
                    else:
                        is_fixed_entity = (
                            runtime_entity.definition.composition.dynamics_ref is None
                            and not runtime_entity.definition.resource_bindings.get("dynamics", ())
                            and candidate.provenance_kind == "no_dynamics"
                        )
                        is_static_wreck = (
                            self._is_static_wreck(candidate.entity_id)
                            and candidate.provenance_kind == "lifecycle_wreck"
                            and position
                            == cast(
                                tuple[float, float, float], tuple(runtime_entity.state.position_m)
                            )
                            and velocity == (0.0, 0.0, 0.0)
                        )
                        if candidate.resolved_hash != self._resolved_hash or not (
                            is_fixed_entity or is_static_wreck
                        ):
                            raise ValueError(
                                f"candidate {index} kinematic provenance conflicts with dynamics"
                            )
                        dynamics_model_ref = None
                        provenance_payload = [candidate.provenance_kind, candidate.resolved_hash]
                    staged_vectors[candidate.entity_id] = (
                        cast(tuple[float, float, float], position),
                        cast(tuple[float, float, float], velocity),
                        dynamics_model_ref,
                        heading,
                    )
                    fingerprint_payload.append(
                        [
                            candidate.entity_id,
                            list(position),
                            list(velocity),
                            heading,
                            provenance_payload,
                        ]
                    )
            except (AttributeError, TypeError, ValueError) as error:
                raise _motion_error(
                    "world.motion_candidate_invalid",
                    ("world", "motion", "candidates"),
                    type(error).__name__,
                    "one motion candidate has invalid identity, shape, or finite numeric state",
                    "provide one finite MotionCandidateV2 per target entity",
                ) from error
            fingerprint = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
            )
            previous = self._motion_ledger.get(operation_id)
            if previous is not None:
                if self._motion_operation_fingerprints.get(operation_id) != fingerprint:
                    raise _motion_error(
                        "world.motion_operation_conflict",
                        ("world", "motion", "operation_id"),
                        operation_id,
                        "motion operation identity was reused with different candidates",
                        "reuse it only for an identical retry",
                    )
                return previous
            if expected_tick != self._spatial_tick:
                raise _motion_error(
                    "world.spatial_tick_conflict",
                    ("world", "spatial_tick"),
                    expected_tick,
                    "motion expected tick differs from the spatial clock",
                    "retry against the latest spatial tick",
                )
            if self._transaction_active:
                raise _motion_error(
                    "world.motion_writer_active",
                    ("world", "motion"),
                    operation_id,
                    "another World writer is active",
                    "retry after the current transaction completes",
                )
            self._transaction_active = True
            native_reconciliation_snapshots: list[tuple[object, Mapping[str, Any]]] = []
            try:
                segments = {
                    entity_id: MotionSegmentV2(
                        start_m=cast(
                            tuple[float, float, float],
                            tuple(self._entities[entity_id].state.position_m),
                        ),
                        end_m=values[0],
                        velocity_mps=values[1],
                        dt_seconds=dt,
                    )
                    for entity_id, values in staged_vectors.items()
                }
                evaluation = self._boundary_system.evaluate(
                    segments,
                    tick=expected_tick,
                    tick_start_time_seconds=tick_start,
                    emit_damage_intents=(
                        self._spatial_effect_policy is not None
                        if _require_resolved_damage_evidence
                        else None
                    ),
                )
                actions = {item.entity_id: item for item in evaluation.policy_actions}
                staged_states = {
                    entity_id: self._entities[entity_id].state.clone()
                    for entity_id in staged_vectors
                }
                for entity_id, (position, velocity, _model_ref, heading) in staged_vectors.items():
                    action = actions.get(entity_id)
                    committed_position = position if action is None else action.resolved_end_m
                    committed_velocity = (
                        velocity if action is None else action.resolved_velocity_mps
                    )
                    state = staged_states[entity_id]
                    state.position_m = list(committed_position)
                    state.velocity_mps = list(committed_velocity)
                    if heading is not None:
                        state.heading_deg = heading
                    elif committed_velocity[0] != 0.0 or committed_velocity[1] != 0.0:
                        state.heading_deg = (
                            math.degrees(math.atan2(committed_velocity[0], committed_velocity[1]))
                            % 360.0
                        )
                    _validate_state(state, entity_id)
                for entity_id in sorted(actions):
                    action = actions[entity_id]
                    position, velocity, model_ref, _heading = staged_vectors[entity_id]
                    if model_ref != MMG_MODEL_REF or (
                        action.resolved_end_m == position
                        and action.resolved_velocity_mps == velocity
                    ):
                        continue
                    runtime_entity = self._entities[entity_id]
                    dynamics_ref = runtime_entity.definition.composition.dynamics_ref
                    if dynamics_ref is None:
                        raise ValueError("boundary-corrected MMG entity has no dynamics resource")
                    adapter = runtime_entity.adapters.get(dynamics_ref)
                    snapshot = getattr(adapter, "snapshot", None)
                    reconcile = getattr(adapter, "_reconcile_authoritative_state", None)
                    restore = getattr(adapter, "_restore_native_state", None)
                    if not callable(snapshot) or not callable(reconcile) or not callable(restore):
                        raise ValueError(
                            "boundary-corrected MMG adapter lacks reconciliation protocol"
                        )
                    captured = snapshot()
                    if not isinstance(captured, NativeDynamicsSnapshotV2):
                        raise ValueError("boundary-corrected MMG adapter snapshot is invalid")
                    native_reconciliation_snapshots.append((adapter, captured.native_state))
                    state = staged_states[entity_id]
                    reconcile(
                        DynamicsStateV2(
                            position_m=cast(tuple[float, float, float], tuple(state.position_m)),
                            velocity_mps=cast(
                                tuple[float, float, float], tuple(state.velocity_mps)
                            ),
                            heading_deg=state.heading_deg,
                        )
                    )
                receipt = MotionReceiptV2(
                    tick=expected_tick,
                    next_tick=expected_tick + 1,
                    operation_id=operation_id,
                    dt_seconds=dt,
                    tick_start_time_seconds=tick_start,
                    candidate_entity_ids=tuple(staged_vectors),
                    boundary_events=evaluation.boundary_events,
                    collision_events=evaluation.collision_events,
                    damage_intents=evaluation.damage_intents,
                    policy_actions=evaluation.policy_actions,
                )
                for entity_id, state in staged_states.items():
                    self._entities[entity_id].state = state
                self._spatial_tick = expected_tick + 1
                self._last_spatial_tick_start_seconds = tick_start
                self._spatial_time_seconds = tick_start + dt
                self._motion_ledger[operation_id] = receipt
                self._motion_operation_fingerprints[operation_id] = fingerprint
                if self._active_motion_provider_receipt is not None:
                    self._consumed_provider_receipts.add(self._active_motion_provider_receipt)
                else:
                    self._consumed_provider_receipts.update(
                        candidate.provider_receipt
                        for candidate in ordered
                        if isinstance(candidate, MotionCandidateV2)
                        and candidate.provider_receipt is not None
                    )
                return receipt
            except MotionPipelineErrorV2:
                for adapter, native_state in reversed(native_reconciliation_snapshots):
                    restore = getattr(adapter, "_restore_native_state", None)
                    if callable(restore):
                        restore(native_state)
                raise
            except Exception as error:
                for adapter, native_state in reversed(native_reconciliation_snapshots):
                    restore = getattr(adapter, "_restore_native_state", None)
                    if callable(restore):
                        restore(native_state)
                raise _motion_error(
                    "world.motion_pipeline_failed",
                    ("world", "motion"),
                    type(error).__name__,
                    "boundary adjudication failed before atomic state commit",
                    "repair candidate or resolved spatial evidence and retry",
                ) from error
            finally:
                self._transaction_active = False

    def apply_damage_transaction(
        self,
        *,
        intents: Mapping[str, Any],
        expected_tick: int,
        operation_id: str,
    ) -> Any:
        """Validate, aggregate, and atomically commit one authoritative damage tick."""

        from openmdbench.combat.models_v2 import (
            CombatErrorV2,
            EntityDamageStateV2,
            combat_error,
        )
        from openmdbench.combat.models_v2 import (
            DamageIntentV2 as CombatDamageIntentV2,
        )
        from openmdbench.schemas.domain_v2 import DamageIntentV2 as DomainDamageIntentV2
        from openmdbench.schemas.domain_v2 import DamageResultV2, LifecycleStateV2

        if not isinstance(intents, Mapping):
            raise TypeError("World damage transaction requires a source-to-intent mapping")
        try:
            operation_payload = [
                expected_tick,
                [
                    [source, intent.model_dump(mode="json")]
                    for source, intent in sorted(intents.items())
                ],
            ]
            fingerprint = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        operation_payload,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise combat_error(
                "damage.transaction_invalid",
                "damage",
                type(error).__name__,
                "World damage input is not finite canonical domain evidence",
            ) from error
        with self._lock:
            previous = self._combat_ledger.get(operation_id)
            if previous is not None:
                if previous[0] != fingerprint:
                    raise combat_error(
                        "damage.operation_conflict",
                        "damage",
                        operation_id,
                        "damage operation identity was reused with different evidence",
                    )
                return previous[1]
            if (
                not isinstance(operation_id, str)
                or not operation_id
                or len(operation_id) > 256
                or not isinstance(expected_tick, int)
                or isinstance(expected_tick, bool)
                or expected_tick != self.tick
            ):
                raise combat_error(
                    "damage.tick_conflict",
                    "damage",
                    expected_tick,
                    "damage transaction must target the authoritative World tick",
                )
            if self._closed or self._transaction_active:
                raise combat_error(
                    "damage.writer_active",
                    "damage",
                    operation_id,
                    "damage cannot interleave with another World writer",
                )

            effect_bindings: dict[str, ResolvedResourceBindingV2] = {
                binding.exact_ref: binding
                for binding in self._world_resource_bindings
                if binding.resource_type == "effects"
            }
            damage_bindings: dict[str, ResolvedResourceBindingV2] = {
                binding.exact_ref: binding
                for binding in self._world_resource_bindings
                if binding.resource_type == "damage_models"
            }
            damage_adapters: dict[str, object] = {
                reference: adapter
                for reference, adapter in self._world_adapters.items()
                if reference in damage_bindings
            }
            for entity in self._entities.values():
                for binding in entity.definition.resource_bindings.get("effects", ()):
                    prior = effect_bindings.setdefault(binding.exact_ref, binding)
                    if prior.content_hash != binding.content_hash:
                        raise combat_error(
                            "damage.effect_binding_conflict",
                            "model_trust",
                            binding.exact_ref,
                            "resolved effect binding hashes conflict",
                        )
                for binding in entity.definition.resource_bindings.get("damage_models", ()):
                    prior = damage_bindings.setdefault(binding.exact_ref, binding)
                    if prior.content_hash != binding.content_hash:
                        raise combat_error(
                            "damage.model_binding_conflict",
                            "model_trust",
                            binding.exact_ref,
                            "resolved damage-model binding hashes conflict",
                        )
                    adapter = entity.adapters.get(binding.exact_ref)
                    if adapter is not None:
                        damage_adapters.setdefault(binding.exact_ref, adapter)

            adapter_states: dict[str, tuple[object, Any]] = {}

            def restore_damage_adapters() -> None:
                for _reference, (adapter, snapshot) in sorted(adapter_states.items()):
                    restore = getattr(adapter, "combat_restore", None)
                    if callable(restore):
                        restore(snapshot)

            typed: list[CombatDamageIntentV2] = []
            try:
                for source_key, intent in sorted(intents.items()):
                    source_kind = source_key.split(":", 1)[0]
                    if source_kind not in {"collision", "environment", "weapon"} or not isinstance(
                        intent, DomainDamageIntentV2
                    ):
                        raise ValueError("unsupported damage source or DTO")
                    source_kind = cast(Literal["collision", "environment", "weapon"], source_kind)
                    if (
                        intent.tick != expected_tick
                        or intent.target_entity_id not in self._entities
                    ):
                        raise ValueError("damage target or tick differs from World state")
                    effect = effect_bindings.get(intent.effect_ref)
                    if effect is None:
                        raise ValueError("damage effect is absent from resolved bindings")
                    resolved_damage_ref = effect.normalized_content.get("damage_model_ref")
                    if not isinstance(resolved_damage_ref, str):
                        raise ValueError("resolved effect omits its exact damage model")
                    damage = damage_bindings.get(resolved_damage_ref)
                    if damage is None or (
                        intent.damage_model_ref is not None
                        and intent.damage_model_ref != resolved_damage_ref
                    ):
                        raise ValueError("damage model differs from the resolved effect chain")
                    model = damage_adapters.get(resolved_damage_ref)
                    if model is None:
                        raise combat_error(
                            "combat.damage_adapter_missing",
                            "model_trust",
                            resolved_damage_ref,
                            "exact resolved damage adapter is absent from the World",
                        )
                    if resolved_damage_ref not in adapter_states:
                        snapshot = getattr(model, "combat_snapshot", None)
                        restore = getattr(model, "combat_restore", None)
                        if not callable(snapshot) or not callable(restore):
                            raise combat_error(
                                "combat.damage_adapter_missing",
                                "model_trust",
                                resolved_damage_ref,
                                "damage adapter lacks rollback snapshot protocol",
                            )
                        adapter_states[resolved_damage_ref] = (model, snapshot())
                    metadata = self._entity_factory._model_registry.metadata(damage.model_ref)
                    evidence = damage.model_evidence
                    if (
                        not metadata.trusted
                        or metadata.artifact_sha256 != evidence.artifact_sha256
                        or metadata.interface_version != evidence.interface_version
                        or not evidence.trusted
                    ):
                        raise ValueError("damage model registry evidence differs from Resolved")
                    raw_magnitude = (
                        intent.magnitude
                        if intent.magnitude is not None
                        else intent.parameters.get(
                            "magnitude", effect.normalized_content.get("magnitude")
                        )
                    )
                    if (
                        isinstance(raw_magnitude, bool)
                        or not isinstance(raw_magnitude, (int, float))
                        or not math.isfinite(float(raw_magnitude))
                        or float(raw_magnitude) < 0.0
                    ):
                        raise ValueError("damage magnitude is absent or non-finite")
                    payload = [
                        intent.intent_id,
                        intent.source_entity_id,
                        intent.target_entity_id,
                        intent.effect_ref,
                        resolved_damage_ref,
                        float(raw_magnitude),
                        expected_tick,
                        source_kind,
                        self._resolved_hash,
                    ]
                    evidence_hash = intent.evidence_hash or (
                        "sha256:"
                        + hashlib.sha256(
                            json.dumps(payload, separators=(",", ":")).encode()
                        ).hexdigest()
                    )
                    typed_intent = CombatDamageIntentV2(
                        schema_version="2.0",
                        intent_id=intent.intent_id,
                        tick=expected_tick,
                        source_entity_id=intent.source_entity_id,
                        target_entity_id=intent.target_entity_id,
                        effect_ref=intent.effect_ref,
                        damage_model_ref=resolved_damage_ref,
                        magnitude=float(raw_magnitude),
                        evidence_hash=evidence_hash,
                        source_kind=source_kind,
                        component_id=intent.component_id,
                        parameters=dict(intent.parameters),
                    )
                    execute = getattr(model, "magnitude", None)
                    if not callable(execute):
                        raise combat_error(
                            "combat.damage_adapter_missing",
                            "model_trust",
                            resolved_damage_ref,
                            "damage adapter lacks its trusted magnitude operation",
                        )
                    try:
                        modeled = execute(typed_intent)
                    except Exception as error:
                        restore_damage_adapters()
                        raise combat_error(
                            "combat.damage_adapter_failure",
                            "damage",
                            type(error).__name__,
                            "damage adapter failed before World commit",
                        ) from error
                    else:
                        if (
                            isinstance(modeled, bool)
                            or not isinstance(modeled, (int, float))
                            or not math.isfinite(float(modeled))
                            or float(modeled) < 0.0
                        ):
                            raise ValueError("damage model returned a non-finite magnitude")
                        typed_intent = typed_intent.model_copy(update={"magnitude": float(modeled)})
                    typed.append(typed_intent)
                typed.sort(
                    key=lambda item: (
                        item.target_entity_id,
                        item.tick,
                        item.source_kind,
                        item.intent_id,
                    )
                )
                if len({item.intent_id for item in typed}) != len(typed):
                    raise ValueError("damage intent identities are duplicated")
            except CombatErrorV2:
                restore_damage_adapters()
                raise
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                restore_damage_adapters()
                raise combat_error(
                    "damage.intent_invalid",
                    "damage",
                    type(error).__name__,
                    "damage evidence is not anchored to the resolved model chain",
                ) from error

            staged = {
                entity_id: (
                    entity.state.clone(),
                    entity.capabilities,
                    entity.capability_tokens,
                )
                for entity_id, entity in self._entities.items()
            }
            prior_runtime = {
                entity_id: (
                    entity.state,
                    entity.capabilities,
                    entity.capability_tokens,
                )
                for entity_id, entity in self._entities.items()
            }
            prior_controller_ownership = self.controller_ownership
            prior_indexes = self._indexes
            prior_capability_index = self.capability_index
            prior_component_health = dict(self._combat_component_health)
            staged_component_health = dict(self._combat_component_health)
            destroyed: list[EntityDamageStateV2] = []
            self._transaction_active = True
            try:
                grouped: dict[tuple[str, str | None], list[CombatDamageIntentV2]] = {}
                for intent in typed:
                    grouped.setdefault((intent.target_entity_id, intent.component_id), []).append(
                        intent
                    )
                for (entity_id, component_id), group in sorted(
                    grouped.items(), key=lambda item: (item[0][0], item[0][1] or "")
                ):
                    state, capabilities, tokens = staged[entity_id]
                    magnitude = math.fsum(
                        item.magnitude if item.magnitude is not None else 0.0 for item in group
                    )
                    if component_id is not None:
                        component_key = f"{entity_id}|{component_id}"
                        if component_key not in staged_component_health:
                            raise ValueError("damage component is absent from tick-start state")
                        profile = self.component_damage_profiles.get(component_id)
                        if profile is None:
                            raise ValueError("damage component profile is absent from World")
                        remaining = max(
                            profile.destroyed_at,
                            staged_component_health[component_key]
                            - magnitude * profile.damage_multiplier,
                        )
                        staged_component_health[component_key] = remaining
                        state.component_states[component_id] = (
                            "destroyed"
                            if remaining <= profile.destroyed_at
                            else "degraded"
                            if remaining < profile.degraded_below
                            else "operational"
                        )
                        if remaining <= profile.destroyed_at:
                            tokens = tuple(
                                token
                                for token in tokens
                                if token.resource_ref != component_id
                                and token.root_resource_ref != component_id
                            )
                            capabilities = coarse_capabilities(tokens)
                    else:
                        state.health = max(0.0, state.health - magnitude)
                        if state.health <= 0.0:
                            state.lifecycle = "destroyed"
                            capabilities = frozenset()
                            tokens = ()
                        elif state.health <= 0.5:
                            state.lifecycle = "disabled"
                            capabilities = frozenset()
                            tokens = ()
                        elif state.health < 1.0:
                            state.lifecycle = "degraded"
                    staged[entity_id] = (state, capabilities, tokens)
                for entity_id, (state, capabilities, tokens) in staged.items():
                    _validate_state(state, entity_id)
                    entity = self._entities[entity_id]
                    entity.state = state
                    entity.capabilities = capabilities
                    entity.capability_tokens = tokens
                    if state.lifecycle == "destroyed":
                        destroyed.append(
                            EntityDamageStateV2(
                                entity_id=entity_id,
                                health=0.0,
                                lifecycle="destroyed",
                                components={key: "destroyed" for key in state.component_states},
                                available_capabilities=(),
                            )
                        )
                self._rebuild_indexes()
                self._refresh_controller_ownership()
                self._combat_component_health = staged_component_health
                result_intents: dict[str, list[CombatDamageIntentV2]] = {}
                for intent in typed:
                    result_intents.setdefault(intent.target_entity_id, []).append(intent)
                results = tuple(
                    DamageResultV2(
                        schema_version="2.0",
                        target_entity_id=entity_id,
                        tick=expected_tick,
                        applied_intent_ids=tuple(
                            item.intent_id
                            for item in sorted(
                                intents_for_target,
                                key=lambda item: (item.source_kind or "", item.intent_id),
                            )
                        ),
                        health_before=float(prior_runtime[entity_id][0].health),
                        health_after=float(staged[entity_id][0].health),
                        component_health={
                            component_id: staged_component_health[f"{entity_id}|{component_id}"]
                            for component_id in sorted(staged[entity_id][0].component_states)
                            if f"{entity_id}|{component_id}" in staged_component_health
                        },
                        lifecycle_before=LifecycleStateV2(prior_runtime[entity_id][0].lifecycle),
                        lifecycle_after=LifecycleStateV2(staged[entity_id][0].lifecycle),
                    )
                    for entity_id, intents_for_target in sorted(result_intents.items())
                )
                receipt = DamageApplyReceiptV2(
                    tick=expected_tick,
                    applied_intents=tuple(typed),
                    destroyed_entities=tuple(sorted(destroyed, key=lambda item: item.entity_id)),
                    results=results,
                )
                self._combat_ledger[operation_id] = (fingerprint, receipt)
                self._combat_rng_state.extend(item.evidence_hash or "" for item in typed)
                return receipt
            except CombatErrorV2:
                for entity_id, (state, capabilities, tokens) in prior_runtime.items():
                    entity = self._entities[entity_id]
                    entity.state = state
                    entity.capabilities = capabilities
                    entity.capability_tokens = tokens
                self.controller_ownership = prior_controller_ownership
                self._indexes = prior_indexes
                self.capability_index = prior_capability_index
                self._combat_component_health = prior_component_health
                raise
            except Exception as error:
                for entity_id, (state, capabilities, tokens) in prior_runtime.items():
                    entity = self._entities[entity_id]
                    entity.state = state
                    entity.capabilities = capabilities
                    entity.capability_tokens = tokens
                self.controller_ownership = prior_controller_ownership
                self._indexes = prior_indexes
                self.capability_index = prior_capability_index
                self._combat_component_health = prior_component_health
                raise combat_error(
                    "damage.model_failure",
                    "damage",
                    type(error).__name__,
                    "damage batch failed before atomic World commit",
                ) from error
            finally:
                self._transaction_active = False

    def checkpoint(self) -> WorldCheckpointV2:
        with self._lock:
            entities: list[CheckpointEntityV2] = []
            for entity_id, entity in sorted(self._entities.items()):
                controller_state = _plain(entity.state.controller)
                if controller_state.get("binding") == entity.controller_binding:
                    controller_state.pop("binding", None)
                entities.append(
                    CheckpointEntityV2(
                        id=entity_id,
                        position_m=(
                            entity.state.position_m[0],
                            entity.state.position_m[1],
                            entity.state.position_m[2],
                        ),
                        velocity_mps=(
                            entity.state.velocity_mps[0],
                            entity.state.velocity_mps[1],
                            entity.state.velocity_mps[2],
                        ),
                        heading_deg=entity.state.heading_deg,
                        health=entity.state.health,
                        energy=entity.state.energy,
                        ammunition=dict(entity.state.ammunition),
                        component_states=_plain(entity.state.component_states),
                        lifecycle=cast(
                            Literal["active", "degraded", "disabled", "destroyed"],
                            entity.state.lifecycle,
                        ),
                        controller_state=controller_state,
                    )
                )
            applied = tuple(
                entry.source_event_id
                for entry in self.lifecycle_schedule
                if entry.source_event_id in self._applied_lifecycle_event_ids
            )
            native_snapshots_values: list[NativeDynamicsSnapshotV2] = []
            for key, snapshot in self.native_adapter_snapshots().items():
                identity_override = self._checkpoint_native_identity_overrides.get(key)
                if identity_override is not None:
                    snapshot = snapshot.model_copy(
                        update={
                            "instance_id": identity_override[0],
                            "restored_from_instance_id": identity_override[1],
                            "snapshot_hash": "sha256:" + "0" * 64,
                        }
                    )
                    snapshot = snapshot.model_copy(
                        update={
                            "snapshot_hash": NativeDynamicsSnapshotV2.compute_snapshot_hash(
                                snapshot
                            )
                        }
                    )
                native_snapshots_values.append(snapshot)
            native_snapshots = tuple(native_snapshots_values)
            return WorldCheckpointV2.create(
                {
                    "schema_version": "world-checkpoint@2.0",
                    "resolved_hash": self._resolved_hash,
                    "catalog_hash": self._catalog_hash,
                    "model_registry_hash": self._model_registry_hash,
                    "session_id": self.session_id,
                    "seed": self._session_seed,
                    "tick": self.tick,
                    "entities": entities,
                    "used_entity_ids": tuple(sorted(self._used_entity_ids)),
                    "schedule_cursor": len(applied),
                    "applied_lifecycle_event_ids": applied,
                    "lifecycle_ledger": tuple(
                        CheckpointLifecycleReceiptV2(
                            tick=item.tick,
                            operation_id=item.operation_id,
                            status=item.status,
                            applied_event_ids=item.applied_event_ids,
                            spawned_entity_ids=item.spawned_entity_ids,
                            despawned_entity_ids=item.despawned_entity_ids,
                        )
                        for item in self._lifecycle_ledger.values()
                    ),
                    "controller_ownership": self.controller_ownership.to_canonical_dict(),
                    "rng_state": self.rng.getstate(),
                    "native_adapter_snapshots": native_snapshots,
                    "tombstones": tuple(
                        CheckpointTombstoneV2(
                            entity_id=item.entity_id,
                            tick=item.tick,
                            source_event_id=item.source_event_id,
                            adapters_closed=item.adapters_closed,
                            cleanup_errors=item.cleanup_errors,
                        )
                        for _key, item in sorted(self._tombstones.items())
                    ),
                    "spatial_clock": CheckpointSpatialClockV2(
                        tick=self._spatial_tick,
                        tick_start_time_seconds=self._last_spatial_tick_start_seconds,
                        next_tick_time_seconds=self._spatial_time_seconds,
                    ),
                    "boundary_topology_hash": self._spatial_topology_hash,
                    "zone_activation_state": dict(sorted(self._zone_activation.items())),
                    "event_state": self.event_state_snapshot(),
                    "spatial_effect_policy": self._spatial_effect_policy,
                    "zone_activation_ledger": tuple(
                        CheckpointZoneActivationReceiptV2(
                            operation_id=self._zone_activation_ledger[key].operation_id,
                            zone_id=self._zone_activation_ledger[key].zone_id,
                            active=self._zone_activation_ledger[key].active,
                            tick=self._zone_activation_ledger[key].tick,
                            changed=self._zone_activation_ledger[key].changed,
                        )
                        for key in sorted(self._zone_activation_ledger)
                    ),
                    "motion_ledger": tuple(
                        CheckpointMotionReceiptV2(
                            tick=self._motion_ledger[key].tick,
                            next_tick=self._motion_ledger[key].next_tick,
                            operation_id=self._motion_ledger[key].operation_id,
                            dt_seconds=self._motion_ledger[key].dt_seconds,
                            tick_start_time_seconds=self._motion_ledger[
                                key
                            ].tick_start_time_seconds,
                            candidate_entity_ids=self._motion_ledger[key].candidate_entity_ids,
                            boundary_events=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in self._motion_ledger[key].boundary_events
                            ),
                            collision_events=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in self._motion_ledger[key].collision_events
                            ),
                            damage_intents=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in self._motion_ledger[key].damage_intents
                            ),
                            policy_actions=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in self._motion_ledger[key].policy_actions
                            ),
                            fingerprint=self._motion_operation_fingerprints[key],
                        )
                        for key in sorted(self._motion_ledger)
                    ),
                    "world_tick_ledger": tuple(
                        CheckpointWorldTickReceiptV2(
                            operation_id=operation_id,
                            fingerprint=fingerprint,
                            start_tick=receipt.start_tick,
                            tick=receipt.tick,
                            steps=receipt.steps,
                            motion_operation_ids=tuple(
                                item.operation_id for item in receipt.motion_receipts
                            ),
                            lifecycle_operation_ids=tuple(
                                item.operation_id for item in receipt.lifecycle_receipts
                            ),
                            event_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.event_receipts
                            ),
                            damage_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.damage_receipts
                            ),
                            provider_receipts=receipt.provider_receipts,
                            dynamics_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.dynamics_receipts
                            ),
                            mission_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.mission_receipts
                            ),
                            score_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.score_receipts
                            ),
                            combat_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.combat_receipts
                            ),
                            subsystem_receipts=tuple(
                                cast(dict[str, Any], _plain(item))
                                for item in receipt.subsystem_receipts
                            ),
                        )
                        for operation_id, (fingerprint, receipt) in sorted(
                            self._world_tick_ledger.items()
                        )
                    ),
                    "consumed_provider_receipts": tuple(sorted(self._consumed_provider_receipts)),
                    "combat_ledger": tuple(
                        {
                            "operation_id": operation_id,
                            "fingerprint": fingerprint,
                            "receipt": receipt.model_dump(mode="json"),
                        }
                        for operation_id, (fingerprint, receipt) in sorted(
                            self._combat_ledger.items()
                        )
                    ),
                    "combat_rng_state": tuple(self._combat_rng_state),
                    "combat_ammunition": {
                        f"{entity_id}|{reference}": count
                        for entity_id, entity in sorted(self._entities.items())
                        for reference, count in sorted(entity.state.ammunition.items())
                    },
                    "combat_energy": {
                        entity_id: entity.state.energy
                        for entity_id, entity in sorted(self._entities.items())
                        if entity.state.energy is not None
                    },
                    "combat_component_health": dict(sorted(self._combat_component_health.items())),
                    "combat_cooldowns": dict(sorted(self._combat_cooldowns.items())),
                    "combat_engagement_ledger": tuple(
                        self._combat_engagement_ledger[key]
                        for key in sorted(self._combat_engagement_ledger)
                    ),
                    "combat_profiles": self._combat_checkpoint_profiles(),
                    "combat_adapter_states": self._combat_adapter_states(),
                    "combat_contact_evidence": tuple(
                        CheckpointContactEvidenceV2(
                            schema_version=record.schema_version,
                            evidence_id=record.evidence_id,
                            owner_entity_id=record.owner_entity_id,
                            target_entity_id=record.target_entity_id,
                            observed_tick=record.observed_tick,
                            age_ticks=max(
                                record.age_ticks,
                                self.tick - record.observed_tick,
                            ),
                            max_age_ticks=record.max_age_ticks,
                            confidence=record.confidence,
                            minimum_confidence=record.minimum_confidence,
                            quality=record.quality,
                            measurement_position_m=record.measurement_position_m,
                            confirmation_count=record.confirmation_count,
                            confirmation_frames=record.confirmation_frames,
                            stale_after_ticks=record.stale_after_ticks,
                            confirmed=record.confirmed,
                            source_sensor_ref=record.source_sensor_ref,
                        )
                        for evidence_id in sorted(self.contact_store.records)
                        for record in self.contact_store.records[evidence_id]
                    ),
                    "combat_roe_rules": tuple(
                        CheckpointRoeRuleV2(
                            schema_version=policy.schema_version,
                            rule_id=policy.rule_id,
                            source_faction_id=policy.source_faction_id,
                            target_faction_id=policy.target_faction_id,
                            relationship=policy.relationship,
                            engagement_permitted=policy.engagement_permitted,
                        )
                        for policy in (self.roe_rules[key] for key in sorted(self.roe_rules))
                    ),
                    "combat_hit_model_state": (
                        CheckpointHitModelStateV2.model_validate(self._combat_hit_model_state)
                        if self._combat_hit_model_state
                        else None
                    ),
                    "missile_flights": tuple(
                        self._missile_flights[key] for key in sorted(self._missile_flights)
                    ),
                    "missile_terminal_receipts": tuple(
                        self._missile_terminal_receipts[key]
                        for key in sorted(self._missile_terminal_receipts)
                    ),
                    "pending_impacts": tuple(
                        self._pending_impacts[key] for key in sorted(self._pending_impacts)
                    ),
                    "pending_impact_receipts": tuple(
                        self._pending_impact_receipts[key]
                        for key in sorted(self._pending_impact_receipts)
                    ),
                    "world_adapter_snapshots": self.snapshot_world_adapters(),
                    "world_adapter_receipts": self._world_adapter_receipts(),
                    "world_adapter_ledger": tuple(
                        cast(dict[str, Any], _plain(item))
                        for item in self._world_adapter_checkpoint_ledger
                    ),
                    "mission_scoring_checkpoint": self._mission_engine.snapshot_state().model_dump(
                        mode="json"
                    ),
                    "mission_zone_membership": {
                        key: tuple(sorted(value))
                        for key, value in sorted(self._mission_zone_membership.items())
                    },
                    "mission_zone_transitions": tuple(
                        cast(dict[str, Any], _plain(item))
                        for item in self._mission_zone_transitions
                    ),
                }
            )

    def _combat_adapter_states(self) -> tuple[dict[str, Any], ...]:
        states: list[dict[str, Any]] = []
        world_damage_refs = {
            binding.exact_ref
            for binding in self._world_resource_bindings
            if binding.resource_type == "damage_models"
        }
        for resource_ref in sorted(world_damage_refs):
            adapter = self._world_adapters.get(resource_ref)
            snapshot = getattr(adapter, "combat_snapshot", None)
            if callable(snapshot):
                states.append(
                    {
                        "entity_id": "__world__",
                        "resource_ref": resource_ref,
                        "state": _plain(snapshot()),
                    }
                )
        for entity_id, entity in sorted(self._entities.items()):
            for binding in entity.definition.resource_bindings.get("damage_models", ()):
                adapter = entity.adapters.get(binding.exact_ref)
                snapshot = getattr(adapter, "combat_snapshot", None)
                if callable(snapshot):
                    states.append(
                        {
                            "entity_id": entity_id,
                            "resource_ref": binding.exact_ref,
                            "state": _plain(snapshot()),
                        }
                    )
        return tuple(states)

    def _combat_checkpoint_profiles(self) -> tuple[dict[str, Any], ...]:
        profiles: dict[tuple[str, str], dict[str, Any]] = {}
        binding_groups = [
            {
                "effects": tuple(
                    item
                    for item in self._world_resource_bindings
                    if item.resource_type == "effects"
                ),
                "damage_models": tuple(
                    item
                    for item in self._world_resource_bindings
                    if item.resource_type == "damage_models"
                ),
            },
            *(entity.definition.resource_bindings for entity in self._entities.values()),
        ]
        for resource_bindings in binding_groups:
            damage = {
                binding.exact_ref: binding for binding in resource_bindings.get("damage_models", ())
            }
            for effect in resource_bindings.get("effects", ()):
                damage_ref = effect.normalized_content.get("damage_model_ref")
                if not isinstance(damage_ref, str) or damage_ref not in damage:
                    continue
                binding = damage[damage_ref]
                metadata = self._entity_factory._model_registry.metadata(binding.model_ref)
                profiles[(effect.exact_ref, damage_ref)] = {
                    "effect_ref": effect.exact_ref,
                    "effect_content_hash": effect.content_hash,
                    "damage_model_ref": damage_ref,
                    "damage_content_hash": binding.content_hash,
                    "model_evidence": {
                        "model_ref": binding.model_ref,
                        "artifact_hash": binding.model_evidence.artifact_sha256,
                        "expected_artifact_hash": metadata.artifact_sha256,
                        "interface_version": binding.model_evidence.interface_version,
                    },
                }
        return tuple(profiles[key] for key in sorted(profiles))

    def advance_lifecycle(
        self,
        *,
        expected_tick: int,
        operation_id: str,
    ) -> LifecycleReceiptV2:
        if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 256:
            raise _factory_error(
                "factory.lifecycle_operation_invalid",
                ("world", "lifecycle", "operation_id"),
                operation_id,
                "lifecycle operation identity must be a bounded nonempty string",
                "provide a stable unique operation identifier up to 256 characters",
            )
        with self._lock:
            if self._closed:
                raise _factory_error(
                    "factory.world_closed",
                    ("world", "lifecycle"),
                    self.session_id,
                    "closed world cannot execute lifecycle transitions",
                    "create a new live session world",
                )
            if self._transaction_active:
                raise _factory_error(
                    "factory.lifecycle_transaction_active",
                    ("world", "lifecycle"),
                    operation_id,
                    "lifecycle authority cannot run inside an ordinary write transaction",
                    "finish or roll back the write transaction before advancing lifecycle",
                )
            existing = self._lifecycle_ledger.get(operation_id)
            if existing is not None:
                if existing.tick != expected_tick:
                    raise _factory_error(
                        "factory.lifecycle_operation_conflict",
                        ("world", "lifecycle", "operation_id"),
                        operation_id,
                        "operation identity is already committed for a different tick",
                        "reuse an operation identity only with its original expected tick",
                    )
                return existing
            pending = tuple(
                entry
                for entry in self.lifecycle_schedule
                if entry.source_event_id not in self._applied_lifecycle_event_ids
            )
            if not pending:
                raise _factory_error(
                    "factory.lifecycle_no_pending_transition",
                    ("world", "lifecycle", "tick"),
                    expected_tick,
                    "resolved lifecycle schedule has no pending transition",
                    "do not advance lifecycle after the resolved schedule is exhausted",
                )
            next_tick = pending[0].tick
            if (
                not isinstance(expected_tick, int)
                or isinstance(expected_tick, bool)
                or expected_tick < self.tick
                or expected_tick != next_tick
            ):
                raise _factory_error(
                    "factory.lifecycle_tick_conflict",
                    ("world", "lifecycle", "tick"),
                    expected_tick,
                    "expected lifecycle tick does not match the next resolved transition",
                    "retry with the next pending lifecycle schedule tick",
                )
            batch = tuple(entry for entry in pending if entry.tick == expected_tick)
            return self._apply_lifecycle_batch(
                batch=batch,
                expected_tick=expected_tick,
                operation_id=operation_id,
            )

    def _apply_lifecycle_batch(
        self,
        *,
        batch: tuple[LifecycleScheduleEntryV2, ...],
        expected_tick: int,
        operation_id: str,
    ) -> LifecycleReceiptV2:
        staged_entities: dict[str, _RuntimeEntityV2] = {}
        staged_adapters: list[object] = []
        staged_adapter_ids: list[str] = []
        despawned: list[tuple[LifecycleScheduleEntryV2, _RuntimeEntityV2]] = []
        working = dict(self._entities)
        working_used = set(self._used_entity_ids)
        adapter_instances = {
            id(adapter) for entity in working.values() for adapter in entity.adapters.values()
        }
        rng_state = self.rng.getstate()
        prior_entities = self._entities
        prior_used = self._used_entity_ids
        prior_applied = set(self._applied_lifecycle_event_ids)
        prior_tick = self.tick
        prior_indexes = self._indexes
        prior_capability_index = self.capability_index
        prior_controller_ownership = self.controller_ownership
        prior_component_health = self._combat_component_health
        working_component_health = dict(self._combat_component_health)
        try:
            for entry in batch:
                if entry.event_type == "spawn":
                    if entry.entity_id in working_used:
                        raise _factory_error(
                            "factory.lifecycle_entity_id_reused",
                            ("events", entry.source_event_id, "entity_id"),
                            entry.entity_id,
                            "entity identifiers remain permanently consumed after first use",
                            "declare a globally new entity identifier",
                        )
                    if not isinstance(entry.blueprint, ResolvedEntityV2):
                        raise ValueError("spawn blueprint is missing")
                    entity = self._entity_factory._build_owned(
                        entry.blueprint,
                        adapter_instances=adapter_instances,
                        session_seed=self._session_seed,
                    )
                    staged_entities[entry.entity_id] = entity
                    adapters = tuple(entity.adapters.values())
                    staged_adapters.extend(adapters)
                    staged_adapter_ids.extend(_adapter_instance_id(item) for item in adapters)
                    working[entry.entity_id] = entity
                    working_used.add(entry.entity_id)
                    for role in ("sensors", "communications", "weapons"):
                        for binding in entity.definition.resource_bindings.get(role, ()):
                            working_component_health[f"{entry.entity_id}|{binding.exact_ref}"] = 1.0
                    injector = self.lifecycle_fault_injector
                    if (
                        injector.fail_after_staged_entities is not None
                        and len(staged_entities) >= injector.fail_after_staged_entities
                    ) or (
                        injector.fail_after_staged_adapters is not None
                        and len(staged_adapters) >= injector.fail_after_staged_adapters
                    ):
                        raise RuntimeError("injected lifecycle staging failure")
                else:
                    try:
                        entity = working.pop(entry.entity_id)
                    except KeyError as error:
                        raise ValueError("despawn target is not active") from error
                    for key in tuple(working_component_health):
                        if key.startswith(f"{entry.entity_id}|"):
                            working_component_health.pop(key)
                    despawned.append((entry, entity))
            self._entities = dict(sorted(working.items()))
            self._used_entity_ids = working_used
            self._combat_component_health = working_component_health
            self._applied_lifecycle_event_ids.update(entry.source_event_id for entry in batch)
            self.tick = expected_tick
            self._rebuild_indexes()
            self._refresh_controller_ownership()
        except Exception as error:
            self.rng.setstate(rng_state)
            self._entities = prior_entities
            self._used_entity_ids = prior_used
            self._applied_lifecycle_event_ids = prior_applied
            self.tick = prior_tick
            self._indexes = prior_indexes
            self.capability_index = prior_capability_index
            self.controller_ownership = prior_controller_ownership
            self._combat_component_health = prior_component_health
            closed_ids, rollback_cleanup_errors = _cleanup_adapters_with_evidence(staged_adapters)
            self._lifecycle_audit.append(
                LifecycleAuditRecordV2(
                    operation_id=operation_id,
                    tick=expected_tick,
                    status="rolled_back",
                    staged_adapter_instance_ids=tuple(staged_adapter_ids),
                    closed_adapter_instance_ids=closed_ids,
                    cleanup_errors=rollback_cleanup_errors,
                )
            )
            if isinstance(error, FactoryErrorV2) and error.code == (
                "factory.lifecycle_entity_id_reused"
            ):
                raise
            raise _factory_error(
                "factory.lifecycle_batch_failed",
                ("world", "lifecycle", str(expected_tick)),
                type(error).__name__,
                "resolved lifecycle tick failed during atomic staging",
                "repair the failing entity factory or resolved lifecycle batch",
            ) from error

        cleanup_errors: list[str] = []
        if self._deferred_lifecycle_despawns is not None:
            self._deferred_lifecycle_despawns.extend(despawned)
        else:
            cleanup_errors.extend(self._finalize_lifecycle_despawns(despawned))
        status: Literal["committed", "committed_with_cleanup_errors"] = (
            "committed_with_cleanup_errors" if cleanup_errors else "committed"
        )
        receipt = LifecycleReceiptV2(
            tick=expected_tick,
            operation_id=operation_id,
            status=status,
            applied_event_ids=tuple(entry.source_event_id for entry in batch),
            spawned_entity_ids=tuple(
                entry.entity_id for entry in batch if entry.event_type == "spawn"
            ),
            despawned_entity_ids=tuple(
                entry.entity_id for entry in batch if entry.event_type == "despawn"
            ),
        )
        self._lifecycle_ledger[operation_id] = receipt
        self._lifecycle_audit.append(
            LifecycleAuditRecordV2(
                operation_id=operation_id,
                tick=expected_tick,
                status=status,
                staged_adapter_instance_ids=tuple(staged_adapter_ids),
                cleanup_errors=tuple(cleanup_errors),
            )
        )
        return receipt

    def _finalize_lifecycle_despawns(
        self,
        despawned: Sequence[tuple[LifecycleScheduleEntryV2, _RuntimeEntityV2]],
    ) -> tuple[str, ...]:
        cleanup_errors: list[str] = []
        for entry, entity in despawned:
            adapters = tuple(entity.adapters.values())
            _closed_ids, entity_errors = _cleanup_adapters_with_evidence(adapters)
            cleanup_errors.extend(entity_errors)
            if entry.entity_id in self.lifecycle_fault_injector.close_error_ids():
                cleanup_errors.append(f"{entry.entity_id}:injected_close_error")
            current_errors = tuple(
                item
                for item in cleanup_errors
                if item.startswith(f"{entry.entity_id}:") or item in entity_errors
            )
            self._tombstones[entry.entity_id] = LifecycleTombstoneV2(
                entity_id=entry.entity_id,
                tick=entry.tick,
                source_event_id=entry.source_event_id,
                adapters_closed=not current_errors,
                cleanup_errors=current_errors,
            )
        return tuple(cleanup_errors)

    def _refresh_controller_ownership(self) -> None:
        pending = tuple(
            entry
            for entry in self.lifecycle_schedule
            if entry.source_event_id not in self._applied_lifecycle_event_ids
        )
        for entity_id, entity in self._entities.items():
            if entity_id not in self._compiled_capability_tokens:
                self._compiled_capability_tokens[entity_id] = capability_tokens_for_entity(
                    entity.definition
                )
        base = build_controller_ownership(
            slots=self.controller_slots,
            uncontrolled_policy=self._controller_policy,
            entity_factions={key: entity.faction_id for key, entity in self._entities.items()},
            # Controller-slot capability evidence belongs to the immutable
            # compiled control contract.  Runtime component damage can remove
            # a capability from an active entity; commands are then rejected
            # by the action pipeline, but rebuilding the ownership index must
            # not turn that valid degradation into a World transaction error.
            entity_tokens={key: self._compiled_capability_tokens[key] for key in self._entities},
            lifecycle_schedule=pending,
        )
        claims = list(base.slot_to_claim.values())
        claimed = {entity_id for claim in claims for entity_id in claim.entity_ids}
        for entity_id, entity in sorted(self._entities.items()):
            binding = entity.controller_binding
            if binding is None or entity_id in claimed:
                continue
            claims.append(
                ControllerClaimV2(
                    slot_id=binding,
                    controller_id=binding,
                    faction_id=entity.faction_id,
                    entity_ids=(entity_id,),
                    action_schema_ref="action-batch@2.0",
                    observation_schema_ref="observation@2.0",
                    endpoint_entity_id=entity_id,
                    inbox_capacity=256,
                    exclusive=True,
                    required_coarse_capabilities=tuple(sorted(entity.capabilities)),
                    required_exact_capabilities=entity.capability_tokens,
                    required_exact_capabilities_by_entity=MappingProxyType(
                        {entity_id: entity.capability_tokens}
                    ),
                )
            )
            claimed.add(entity_id)
        slot_to_claim = {claim.slot_id: claim for claim in claims}
        controller_to_claim = {claim.controller_id: claim for claim in claims}
        entity_to_claims: dict[str, list[ControllerClaimV2]] = {
            entity_id: [] for entity_id in self._entities
        }
        for claim in claims:
            for entity_id in claim.entity_ids:
                if entity_id in entity_to_claims:
                    entity_to_claims[entity_id].append(claim)
        claimed_ids = tuple(sorted(key for key, value in entity_to_claims.items() if value))
        self.controller_ownership = ControllerOwnershipIndexV2(
            slot_ids=tuple(sorted(slot_to_claim)),
            controller_ids=tuple(sorted(controller_to_claim)),
            claimed_entity_ids=claimed_ids,
            uncontrolled_entity_ids=tuple(sorted(set(self._entities) - set(claimed_ids))),
            reserved_entity_ids=base.reserved_entity_ids,
            uncontrolled_policy=base.uncontrolled_policy,
            slot_to_claim=MappingProxyType(slot_to_claim),
            controller_to_claim=MappingProxyType(controller_to_claim),
            entity_to_claims=MappingProxyType(
                {
                    key: tuple(sorted(value, key=lambda item: item.slot_id))
                    for key, value in sorted(entity_to_claims.items())
                }
            ),
            reservation_by_entity=base.reservation_by_entity,
            reservations=base.reservations,
        )
        self.authority_tokens = build_world_authority_grants_v2(
            entity_factions={
                entity_id: entity.faction_id for entity_id, entity in self._entities.items()
            },
            controller_ownership=self.controller_ownership,
        )

    def semantic_snapshot(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {
            "tick": snapshot.tick,
            "spatial_tick": self._spatial_tick,
            "spatial_time_seconds": self._spatial_time_seconds,
            "spatial_topology_hash": self._spatial_topology_hash,
            "factions": [item.model_dump(mode="json") for item in self.factions],
            "relationships": [item.model_dump(mode="json") for item in self.relationships],
            "entities": [
                {
                    "id": entity.id,
                    "faction_id": entity.faction_id,
                    "tags": list(entity.tags),
                    "domain": entity.domain,
                    "controller_binding": entity.controller_binding,
                    "capabilities": sorted(entity.capabilities),
                    "state": {
                        "position_m": list(entity.state.position_m),
                        "velocity_mps": list(entity.state.velocity_mps),
                        "heading_deg": entity.state.heading_deg,
                        "health": entity.state.health,
                        "energy": entity.state.energy,
                        "ammunition": dict(entity.state.ammunition),
                        "component_states": _plain(entity.state.component_states),
                        "lifecycle": entity.state.lifecycle,
                        "controller": _plain(entity.state.controller),
                    },
                }
                for entity in snapshot.entities
            ],
            "lifecycle_schedule": [
                {
                    "topological_index": item.topological_index,
                    "tick": item.tick,
                    "priority": item.priority,
                    "event_type": item.event_type,
                    "entity_id": item.entity_id,
                    "source_event_id": item.source_event_id,
                    "blueprint_hash": item.blueprint_hash,
                }
                for item in self.lifecycle_schedule
            ],
            "used_entity_ids": sorted(self._used_entity_ids),
            "applied_lifecycle_event_ids": sorted(self._applied_lifecycle_event_ids),
            "lifecycle_ledger": [
                {
                    "tick": item.tick,
                    "operation_id": item.operation_id,
                    "status": item.status,
                    "applied_event_ids": list(item.applied_event_ids),
                    "spawned_entity_ids": list(item.spawned_entity_ids),
                    "despawned_entity_ids": list(item.despawned_entity_ids),
                }
                for item in self._lifecycle_ledger.values()
            ],
            "zone_activation": dict(sorted(self._zone_activation.items())),
            "zone_activation_ledger": [
                _plain(self._zone_activation_ledger[key])
                for key in sorted(self._zone_activation_ledger)
            ],
            "motion_ledger": [
                _plain(self._motion_ledger[key]) for key in sorted(self._motion_ledger)
            ],
            "consumed_provider_receipts": sorted(self._consumed_provider_receipts),
            "combat_ledger": [
                {
                    "operation_id": operation_id,
                    "fingerprint": fingerprint,
                    "receipt": receipt.model_dump(mode="json"),
                }
                for operation_id, (fingerprint, receipt) in sorted(self._combat_ledger.items())
            ],
            "combat_rng_state": list(self._combat_rng_state),
            "combat_cooldowns": dict(sorted(self._combat_cooldowns.items())),
            "missile_flights": [
                self._missile_flights[key].model_dump(mode="json")
                for key in sorted(self._missile_flights)
            ],
            "missile_terminal_receipts": [
                self._missile_terminal_receipts[key].model_dump(mode="json")
                for key in sorted(self._missile_terminal_receipts)
            ],
            "tombstones": [
                {
                    "entity_id": item.entity_id,
                    "tick": item.tick,
                    "source_event_id": item.source_event_id,
                    "adapters_closed": item.adapters_closed,
                    "cleanup_errors": list(item.cleanup_errors),
                }
                for _key, item in sorted(self._tombstones.items())
            ],
            "controller_ownership": self.controller_ownership.to_canonical_dict(),
            "capability_index": {key: list(value) for key, value in self.capability_index.items()},
            "rng_fingerprint": "sha256:"
            + hashlib.sha256(
                json.dumps(self.rng.getstate(), separators=(",", ":")).encode()
            ).hexdigest(),
            "lifecycle_audit": [
                {
                    "operation_id": item.operation_id,
                    "tick": item.tick,
                    "status": item.status,
                    "cleanup_errors": list(item.cleanup_errors),
                }
                for item in self._lifecycle_audit
                if item.status != "rolled_back"
            ],
        }

    def write_transaction(self, *, tick: int) -> _WriteTransactionV2:
        if self._closed:
            raise _factory_error(
                "factory.world_closed",
                ("world", "close"),
                self.session_id,
                "closed world cannot open a write transaction",
                "create a new session-owned runtime world",
            )
        return _WriteTransactionV2(self, tick)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            plugin_cleanup_errors = self._mission_engine.close_plugins()
            self._mission_plugin_cleanup_errors = plugin_cleanup_errors
            adapters = tuple(self._world_adapters.values()) + tuple(
                adapter
                for entity in self._entities.values()
                for adapter in entity.adapters.values()
            )
            closed_ids, failed_ids, cleanup_errors = _cleanup_adapters_with_details(adapters)
            self._world_adapter_transaction_audit.append(
                WorldAdapterTransactionV2(
                    closed_adapter_ids=closed_ids,
                    failed_adapter_ids=failed_ids,
                    cleanup_errors=cleanup_errors,
                    operation_id="world.adapters.close",
                    status=(
                        "closed"
                        if not plugin_cleanup_errors and not cleanup_errors
                        else "closed_with_cleanup_errors"
                    ),
                )
            )
            self._closed = True

    def _rebuild_indexes(self) -> None:
        indexes: dict[str, dict[str, list[str]]] = {
            "capability": {},
            "domain": {},
            "faction": {},
            "tag": {},
        }
        for identifier, entity in sorted(self._entities.items()):
            values = {
                "capability": entity.capabilities,
                "domain": (entity.domain,),
                "faction": (entity.faction_id,),
                "tag": entity.tags,
            }
            for index_name, keys in values.items():
                for key in keys:
                    indexes[index_name].setdefault(key, []).append(identifier)
        self._indexes = MappingProxyType(
            {
                index_name: MappingProxyType(
                    {key: tuple(values) for key, values in sorted(entries.items())}
                )
                for index_name, entries in indexes.items()
            }
        )
        self.capability_index = build_capability_index(
            {entity_id: entity.capability_tokens for entity_id, entity in self._entities.items()}
        )


def _schedule(events: Sequence[ResolvedEventV2]) -> tuple[LifecycleScheduleEntryV2, ...]:
    entries: list[LifecycleScheduleEntryV2] = []
    for topological_index, event in enumerate(events):
        if event.event_type not in {"spawn", "despawn"}:
            continue
        tick = getattr(event.trigger, "tick", None)
        if (
            not isinstance(tick, int)
            or isinstance(tick, bool)
            or tick < 0
            or not isinstance(event.priority, int)
            or isinstance(event.priority, bool)
        ):
            raise _factory_error(
                "factory.lifecycle_schedule_invalid",
                ("events", event.id, "trigger"),
                tick,
                "lifecycle event trigger or priority is not canonical",
                "recompile a typed tick-triggered lifecycle event",
            )
        if event.event_type == "spawn":
            blueprint = getattr(event.payload, "entity", None)
            if not isinstance(blueprint, ResolvedEntityV2):
                raise _factory_error(
                    "factory.lifecycle_schedule_invalid",
                    ("events", event.id, "payload", "entity"),
                    type(blueprint).__name__,
                    "spawn event has no immutable resolved entity blueprint",
                    "recompile the spawn declaration through resource closure",
                )
            entity_id = blueprint.id
        else:
            blueprint = None
            candidate = getattr(event.payload, "entity_id", None)
            if not isinstance(candidate, str):
                raise _factory_error(
                    "factory.lifecycle_schedule_invalid",
                    ("events", event.id, "payload", "entity_id"),
                    candidate,
                    "despawn event has no typed entity identifier",
                    "recompile the despawn declaration with a valid endpoint",
                )
            entity_id = candidate
        entries.append(
            LifecycleScheduleEntryV2(
                topological_index=topological_index,
                tick=tick,
                priority=event.priority,
                event_type=event.event_type,
                entity_id=entity_id,
                source_event_id=event.id,
                blueprint=blueprint,
            )
        )
    return tuple(entries)


def _spatial_runtime(
    resolved: ResolvedScenarioV2,
    definitions: Sequence[ResolvedEntityV2],
) -> tuple[BoundarySystemV2, str, GeographyServiceV2]:
    if resolved.world.coordinate_frame is None:
        geography = GeographyServiceV2.from_config(
            origin_wgs84=(0.0, 0.0, 0.0),
            axis_orientation="east_north_up",
            tolerance_m=1e-6,
            local_bounds_m=((-1e12, -1e12, -1e12), (1e12, 1e12, 1e12)),
        )
    else:
        geography = GeographyServiceV2.from_resolved_scenario(cast(Any, resolved))
    if all(hasattr(item, "geometry") for item in resolved.world.zones):
        boundary_system = BoundarySystemV2.from_resolved(
            cast(Any, resolved),
            geography=geography,
            enable_entity_collisions=True,
            emit_damage_intents=True,
        )
    else:
        boundary_system = BoundarySystemV2(
            geography=geography,
            enable_entity_collisions=True,
            emit_damage_intents=True,
            impact_damage_policy=cast(Any, resolved.spatial_effect_policy),
        )
    boundary_entities: list[BoundaryEntityV2] = []
    for definition in sorted(definitions, key=lambda item: item.id):
        exact_ref = definition.composition.collision_shape_ref
        bindings = definition.resource_bindings.get("collision_shapes", ())
        binding = next((item for item in bindings if item.exact_ref == exact_ref), None)
        shape = (
            CollisionShapeV2(
                exact_ref="builtin.point-sphere@2.0.0",
                content_hash="runtime-point-shape",
                shape="sphere",
                radius_m=1e-9,
                vertical_interval_m=(-1e-9, 1e-9),
            )
            if binding is None
            else CollisionShapeV2.from_profile(
                exact_ref=binding.exact_ref,
                content_hash=binding.content_hash,
                shape=str(binding.normalized_content.get("shape")),
                parameters=binding.normalized_content,
            )
        )
        deployment = definition.boundary_deployment
        mass_kg = math.fsum(
            float(value)
            for role in ("platforms", "loadouts")
            for item in definition.resource_bindings.get(role, ())
            if isinstance((value := item.normalized_content.get("mass_kg")), (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and float(value) >= 0.0
        )
        boundary_entities.append(
            BoundaryEntityV2(
                entity_id=definition.id,
                domain=definition.domain,
                radius_m=shape.radius_m,
                tags=definition.tags,
                collision_shape_ref=shape.exact_ref,
                shape=shape,
                allowed_zone_ids=(() if deployment is None else deployment.allowed_zone_ids),
                excluded_zone_ids=(() if deployment is None else deployment.excluded_zone_ids),
                mass_kg=mass_kg,
            )
        )
    boundary_system.register_entities(tuple(boundary_entities))
    topology_definitions = {
        item.id: item for item in resolved.entities if isinstance(item, ResolvedEntityV2)
    }
    for event in resolved.events:
        blueprint = getattr(event.payload, "entity", None)
        if isinstance(blueprint, ResolvedEntityV2):
            topology_definitions[blueprint.id] = blueprint
    topology_payload = {
        "resolved_hash": resolved.resolved_hash,
        "zones": _plain(getattr(resolved.world, "zones", ())),
        "boundaries": _plain(getattr(resolved.world, "boundaries", ())),
        "entities": [
            {
                "id": item.id,
                "collision_shape_ref": item.composition.collision_shape_ref,
                "boundary_deployment": _plain(item.boundary_deployment),
            }
            for item in sorted(topology_definitions.values(), key=lambda item: item.id)
        ],
    }
    topology_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(topology_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    return boundary_system, topology_hash, geography


class WorldFactoryV2:
    """Atomically construct a complete generic runtime world."""

    def __init__(
        self,
        *,
        model_registry: ModelRegistryV2,
        entity_factory: EntityFactoryV2 | None = None,
        native_dynamics_factory: NativeDynamicsAdapterFactoryV2 | None = None,
    ) -> None:
        self._model_registry = model_registry
        self._native_dynamics_factory = native_dynamics_factory or getattr(
            entity_factory, "_native_dynamics_factory", None
        )
        self._entity_factory = entity_factory or EntityFactoryV2(
            model_registry=model_registry,
            native_dynamics_factory=native_dynamics_factory,
        )
        self.checkpoint_fault_injector = CheckpointRestoreFaultInjectorV2()
        self._checkpoint_restore_audit: list[CheckpointRestoreAuditV2] = []

    @property
    def checkpoint_restore_audit(self) -> tuple[CheckpointRestoreAuditV2, ...]:
        return tuple(self._checkpoint_restore_audit)

    @staticmethod
    def _resolved_mission_plugin_factories(
        resolved: ResolvedScenarioV2,
        model_registry: ModelRegistryV2,
    ) -> Mapping[str, Any]:
        from openmdbench.missions.engine_v2 import TrustedMissionPluginFactoryV2

        metrics = () if resolved.scoring is None else resolved.scoring.metrics
        factories: dict[str, TrustedMissionPluginFactoryV2] = {}
        for metric in metrics:
            plugin_ref = metric.get("plugin_ref")
            if plugin_ref is None:
                continue
            raw_evidence = metric.get("plugin_evidence")
            raw_parameters = metric.get("plugin_parameters")
            evidence = _plain(getattr(raw_evidence, "values", raw_evidence))
            parameters = _plain(getattr(raw_parameters, "values", raw_parameters))
            if not isinstance(evidence, Mapping) or not isinstance(parameters, Mapping):
                raise ValueError("resolved mission plugin binding evidence is absent")
            metadata = model_registry.metadata(str(plugin_ref))
            if (
                metadata.exact_ref != evidence.get("model_ref")
                or metadata.artifact_sha256 != evidence.get("artifact_sha256")
                or metadata.interface_version != evidence.get("interface_version")
                or metadata.trusted is not True
                or metadata.deterministic is not True
            ):
                raise ValueError("resolved mission plugin differs from trusted Registry")

            def create_plugin(
                *,
                session_id: str,
                seed: int,
                model_ref: str = str(plugin_ref),
                plugin_parameters: Mapping[str, Any] = MappingProxyType(dict(parameters)),
            ) -> Any:
                plugin = model_registry.create(model_ref)
                bind_session = getattr(plugin, "bind_session", None)
                if callable(bind_session):
                    bound = bind_session(
                        session_id=session_id,
                        seed=seed,
                        parameters=_plain(plugin_parameters),
                    )
                    if bound is not None:
                        plugin = bound
                return plugin

            factories[str(metric.id)] = TrustedMissionPluginFactoryV2(
                plugin_ref=str(plugin_ref),
                artifact_sha256=str(evidence["artifact_sha256"]),
                interface_version=str(evidence["interface_version"]),
                deterministic=bool(evidence["deterministic"]),
                trusted=bool(evidence["trusted"]),
                factory=create_plugin,
            )
        return MappingProxyType(dict(sorted(factories.items())))

    def restore_checkpoint(
        self,
        checkpoint: WorldCheckpointV2,
        *,
        resolved: ResolvedScenarioV2,
        model_registry: ModelRegistryV2,
        expected_checkpoint_hash: str,
        expected_session_id: str | None = None,
        expected_seed: int | None = None,
        mission_plugin_factories: Mapping[str, Any] | None = None,
    ) -> WorldStateV2:
        if not isinstance(checkpoint, WorldCheckpointV2):
            raise _factory_error(
                "factory.checkpoint_integrity_invalid",
                ("checkpoint",),
                type(checkpoint).__name__,
                "restore requires the immutable canonical checkpoint DTO",
                "parse a trusted WorldCheckpointV2 before restore",
            )
        try:
            checkpoint.validate_integrity()
            resolved.validate_integrity()
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise _factory_error(
                "factory.checkpoint_integrity_invalid",
                ("checkpoint", "integrity"),
                type(error).__name__,
                "checkpoint or resolved scenario failed canonical integrity validation",
                "restore an unmodified checkpoint with an intact resolved scenario",
            ) from error
        registry_hash = getattr(model_registry, "snapshot_hash", None)
        if (
            checkpoint.checkpoint_hash != expected_checkpoint_hash
            or checkpoint.resolved_hash != resolved.resolved_hash
            or checkpoint.catalog_hash != resolved.catalog_hash
            or checkpoint.model_registry_hash != resolved.model_registry_hash
            or checkpoint.model_registry_hash != registry_hash
            or model_registry is not self._model_registry
            or checkpoint.spatial_effect_policy != resolved.spatial_effect_policy
            or (expected_session_id is not None and checkpoint.session_id != expected_session_id)
            or (expected_seed is not None and checkpoint.seed != expected_seed)
        ):
            raise _factory_error(
                "factory.checkpoint_anchor_mismatch",
                ("checkpoint", "anchors"),
                checkpoint.checkpoint_hash,
                "checkpoint identity differs from an explicit resolved, registry, "
                "or session anchor",
                "restore with the exact resolved scenario, registry, session, and seed evidence",
            )
        validator = WorldFactoryV2(
            model_registry=model_registry,
            native_dynamics_factory=self._native_dynamics_factory,
        )
        validator._validate_registry_snapshot(
            resolved.model_registry_snapshot,
            expected_hash=resolved.model_registry_hash,
        )
        schedule = _schedule(resolved.events)
        prefix = schedule[: checkpoint.schedule_cursor]
        lifecycle_clock = prefix[-1].tick if prefix else 0
        tick_ledger_clock = max(
            (item.tick for item in checkpoint.world_tick_ledger), default=lifecycle_clock
        )
        if (
            checkpoint.schedule_cursor > len(schedule)
            or tuple(item.source_event_id for item in prefix)
            != checkpoint.applied_lifecycle_event_ids
            or checkpoint.tick < lifecycle_clock
            or tick_ledger_clock != checkpoint.tick
        ):
            raise _factory_error(
                "factory.checkpoint_anchor_mismatch",
                ("checkpoint", "schedule_cursor"),
                checkpoint.schedule_cursor,
                "checkpoint cursor differs from the resolved lifecycle topology",
                "restore against the exact resolved event schedule",
            )

        definitions = {
            item.id: item for item in resolved.entities if isinstance(item, ResolvedEntityV2)
        }
        active = set(definitions)
        used = set(definitions)
        for entry in prefix:
            if entry.event_type == "spawn":
                if entry.blueprint is None or entry.entity_id in used:
                    raise _factory_error(
                        "factory.checkpoint_anchor_mismatch",
                        ("checkpoint", "schedule_cursor"),
                        entry.entity_id,
                        "resolved lifecycle prefix cannot reproduce checkpoint identity",
                        "restore an earlier checkpoint or repair the resolved topology",
                    )
                definitions[entry.entity_id] = entry.blueprint
                active.add(entry.entity_id)
                used.add(entry.entity_id)
            else:
                active.discard(entry.entity_id)
        trigger_ledger = _plain(checkpoint.event_state.spatial_effect_trigger_ledger)
        destroyed_lifecycle_ledger = _plain(checkpoint.event_state.destroyed_lifecycle_ledger)
        if not isinstance(trigger_ledger, Mapping) or not isinstance(
            destroyed_lifecycle_ledger, Mapping
        ):
            raise _factory_error(
                "factory.checkpoint_integrity_invalid",
                ("checkpoint", "event_state", "destroyed_lifecycle_ledger"),
                type(destroyed_lifecycle_ledger).__name__,
                "destroyed lifecycle evidence must be a canonical mapping",
                "restore an unmodified canonical checkpoint",
            )
        dynamic_despawned_ids: set[str] = set()
        for entity_id, record in destroyed_lifecycle_ledger.items():
            if not isinstance(entity_id, str) or not isinstance(record, Mapping):
                raise _factory_error(
                    "factory.checkpoint_integrity_invalid",
                    ("checkpoint", "event_state", "destroyed_lifecycle_ledger"),
                    entity_id,
                    "destroyed lifecycle evidence is malformed",
                    "restore an unmodified canonical checkpoint",
                )
            if record.get("status") in {"despawned", "despawned_with_cleanup_errors"}:
                if record.get("entity_id") != entity_id or entity_id not in active:
                    raise _factory_error(
                        "factory.checkpoint_integrity_invalid",
                        ("checkpoint", "event_state", "destroyed_lifecycle_ledger"),
                        entity_id,
                        "destroyed lifecycle despawn evidence differs from the active topology",
                        "restore an unmodified canonical checkpoint",
                    )
                dynamic_despawned_ids.add(entity_id)
        for authority_event_id, record in trigger_ledger.items():
            if not isinstance(authority_event_id, str) or not isinstance(record, Mapping):
                raise _factory_error(
                    "factory.checkpoint_integrity_invalid",
                    ("checkpoint", "event_state", "spatial_effect_trigger_ledger"),
                    authority_event_id,
                    "spatial trigger lifecycle evidence is malformed",
                    "restore an unmodified canonical checkpoint",
                )
            status = record.get("lifecycle_status")
            entity_id = record.get("source_entity_id")
            if status in {"despawned", "despawned_with_cleanup_errors"}:
                if not isinstance(entity_id, str) or entity_id not in active:
                    raise _factory_error(
                        "factory.checkpoint_integrity_invalid",
                        ("checkpoint", "event_state", "spatial_effect_trigger_ledger"),
                        entity_id,
                        "spatial trigger despawn evidence differs from the active topology",
                        "restore an unmodified canonical checkpoint",
                    )
                # Compatibility for checkpoints produced before generic
                # destruction-policy evidence was added. New checkpoints are
                # anchored by destroyed_lifecycle_ledger above.
                if entity_id not in destroyed_lifecycle_ledger:
                    dynamic_despawned_ids.add(entity_id)
        active.difference_update(dynamic_despawned_ids)
        checkpoint_entity_ids = {item.id for item in checkpoint.entities}
        if checkpoint_entity_ids != active or set(checkpoint.used_entity_ids) != used:
            raise _factory_error(
                "factory.checkpoint_anchor_mismatch",
                ("checkpoint", "entities"),
                tuple(sorted(checkpoint_entity_ids)),
                "checkpoint active or used identities differ from the resolved lifecycle prefix",
                "restore the checkpoint with the exact resolved scenario lifetime graph",
            )

        ledger_cursor = 0
        for receipt in checkpoint.lifecycle_ledger:
            count = len(receipt.applied_event_ids)
            receipt_entries = prefix[ledger_cursor : ledger_cursor + count]
            if (
                not receipt_entries
                or tuple(item.source_event_id for item in receipt_entries)
                != receipt.applied_event_ids
                or any(item.tick != receipt.tick for item in receipt_entries)
                or tuple(item.entity_id for item in receipt_entries if item.event_type == "spawn")
                != receipt.spawned_entity_ids
                or tuple(item.entity_id for item in receipt_entries if item.event_type == "despawn")
                != receipt.despawned_entity_ids
            ):
                raise _factory_error(
                    "factory.checkpoint_integrity_invalid",
                    ("checkpoint", "lifecycle_ledger", receipt.operation_id),
                    receipt.applied_event_ids,
                    "checkpoint receipt differs from the resolved schedule prefix",
                    "restore an unmodified receipt ledger for the anchored schedule",
                )
            ledger_cursor += count
        if ledger_cursor != len(prefix):
            raise _factory_error(
                "factory.checkpoint_integrity_invalid",
                ("checkpoint", "lifecycle_ledger"),
                ledger_cursor,
                "checkpoint receipt ledger does not cover the complete resolved cursor",
                "restore the complete idempotency ledger for all applied events",
            )

        native_models = frozenset({UAV_MODEL_REF, AUV_MODEL_REF, FIXED_MODEL_REF, MMG_MODEL_REF})
        native_bindings = {
            (entity_id, binding.exact_ref): binding
            for entity_id in active
            for bindings in definitions[entity_id].resource_bindings.values()
            for binding in bindings
            if binding.model_ref in native_models
        }
        snapshot_keys = {
            (snapshot.entity_id, snapshot.resource_ref)
            for snapshot in checkpoint.native_adapter_snapshots
        }
        snapshots_match_bindings = all(
            native_bindings.get((snapshot.entity_id, snapshot.resource_ref)) is not None
            and native_bindings[(snapshot.entity_id, snapshot.resource_ref)].model_ref
            == snapshot.model_ref
            for snapshot in checkpoint.native_adapter_snapshots
        )
        if snapshot_keys != set(native_bindings) or not snapshots_match_bindings:
            raise _factory_error(
                "factory.checkpoint_native_closure_mismatch",
                ("checkpoint", "native_adapter_snapshots"),
                tuple(sorted(snapshot_keys)),
                "checkpoint native snapshots do not exactly close active resolved bindings",
                "include exactly one snapshot for every active native resource binding",
            )

        entity_factory = EntityFactoryV2(
            model_registry=model_registry,
            native_dynamics_factory=self._native_dynamics_factory,
        )
        built: dict[str, _RuntimeEntityV2] = {}
        world_adapters: dict[str, object] = {}
        owned_adapters: list[object] = []
        created_ids: list[str] = []
        adapter_stages: list[Literal["initial", "native_replacement"]] = []
        failed_adapter_index: int | None = None
        failed_adapter_instance_id: str | None = None
        failed_stage: Literal["initial", "native_replacement"] | None = None
        replaced_ids: tuple[str, ...] = ()
        closed_replaced_ids: tuple[str, ...] = ()
        failed_replaced_ids: tuple[str, ...] = ()
        replacement_cleanup_errors: tuple[CheckpointAdapterCleanupErrorV2, ...] = ()
        adapter_instances: set[int] = set()

        def before_adapter_build(binding: ResolvedResourceBindingV2) -> None:
            nonlocal failed_adapter_index, failed_adapter_instance_id, failed_stage
            candidate_index = len(created_ids) + 1
            if self.checkpoint_fault_injector.fail_on_replacement_adapter_index == candidate_index:
                failed_adapter_index = candidate_index
                failed_adapter_instance_id = binding.exact_ref
                failed_stage = "initial"
                raise RuntimeError("injected checkpoint replacement adapter failure")

        def record_adapter(
            adapter: object,
            stage: Literal["initial", "native_replacement"] = "initial",
        ) -> None:
            nonlocal failed_adapter_index, failed_adapter_instance_id, failed_stage
            owned_adapters.append(adapter)
            created_ids.append(_adapter_instance_id(adapter))
            adapter_stages.append(stage)
            fault_limit = self.checkpoint_fault_injector.fail_after_restored_adapters
            if fault_limit is not None and len(created_ids) >= fault_limit:
                failed_adapter_index = len(created_ids)
                failed_adapter_instance_id = created_ids[-1]
                failed_stage = stage
                raise RuntimeError("injected checkpoint restore failure")

        def record_cleanup(adapters: Sequence[object]) -> None:
            nonlocal replaced_ids
            nonlocal closed_replaced_ids, failed_replaced_ids
            nonlocal replacement_cleanup_errors
            replaced_ids = tuple(_adapter_instance_id(item) for item in adapters)
            (
                closed_replaced_ids,
                failed_replaced_ids,
                replacement_cleanup_errors,
            ) = _cleanup_adapters_with_details(adapters)

        try:
            for binding in resolved.world_resource_bindings:
                before_adapter_build(binding)
                adapter = entity_factory._create_adapter(
                    binding,
                    entity_id="__world__",
                    session_seed=checkpoint.seed,
                    path=("world_resource_bindings", binding.exact_ref),
                )
                if id(adapter) in adapter_instances:
                    raise _factory_error(
                        "factory.adapter_instance_reused",
                        ("world_resource_bindings", binding.exact_ref, "adapter"),
                        binding.exact_ref,
                        "a model factory reused one mutable adapter instance",
                        "return a fresh independently owned adapter for every binding",
                    )
                adapter_instances.add(id(adapter))
                world_adapters[binding.exact_ref] = adapter
                record_adapter(adapter)
            for entity_id in sorted(active):
                entity = entity_factory._build_owned(
                    definitions[entity_id],
                    adapter_instances=adapter_instances,
                    session_seed=checkpoint.seed,
                    before_adapter_build=before_adapter_build,
                    adapter_created=record_adapter,
                )
                built[entity_id] = entity
            ownership = build_controller_ownership(
                slots=resolved.controller_slots,
                uncontrolled_policy=resolved.controller_policy,
                entity_factions={key: item.faction_id for key, item in built.items()},
                entity_tokens={key: item.capability_tokens for key, item in built.items()},
                lifecycle_schedule=tuple(schedule[checkpoint.schedule_cursor :]),
            )
            boundary_system, spatial_topology_hash, geography = _spatial_runtime(
                resolved, tuple(definitions[entity_id] for entity_id in sorted(active))
            )
            world = WorldStateV2(
                entities=built,
                world_resource_bindings=resolved.world_resource_bindings,
                world_adapters=world_adapters,
                factions=resolved.factions,
                relationships=resolved.relationships,
                controller_slots=resolved.controller_slots,
                controller_ownership=ownership,
                lifecycle_schedule=schedule,
                resolved_scenario=resolved,
                resolved_events=resolved.events,
                session_id=checkpoint.session_id,
                seed=checkpoint.seed,
                entity_factory=entity_factory,
                controller_policy=resolved.controller_policy,
                resolved_hash=resolved.resolved_hash,
                catalog_hash=resolved.catalog_hash,
                model_registry_hash=resolved.model_registry_hash,
                boundary_system=boundary_system,
                geography=geography,
                spatial_topology_hash=spatial_topology_hash,
            )
            if tuple(_plain(item) for item in checkpoint.world_adapter_receipts) != (
                world._world_adapter_receipts()
            ) or tuple(_plain(item) for item in checkpoint.world_adapter_ledger) != tuple(
                _plain(item) for item in world._world_adapter_checkpoint_ledger
            ):
                raise ValueError("checkpoint World adapter receipts or ledger differ from Resolved")
            world.restore_world_adapters_reverse(
                checkpoint.world_adapter_snapshots,
                operation_id="checkpoint.world_adapters.restore",
            )
            by_id = {item.id: item for item in checkpoint.entities}
            for entity_id, entity in world._entities.items():
                saved = by_id[entity_id]
                entity.state = _RuntimeEntityStateV2(
                    position_m=list(saved.position_m),
                    velocity_mps=list(saved.velocity_mps),
                    heading_deg=saved.heading_deg,
                    health=saved.health,
                    energy=saved.energy,
                    ammunition=dict(saved.ammunition),
                    component_states=_plain(saved.component_states),
                    lifecycle=saved.lifecycle,
                    controller={
                        "binding": entity.controller_binding,
                        **_plain(saved.controller_state),
                    },
                )
                _validate_state(entity.state, entity_id)
                if entity.state.lifecycle in {"disabled", "destroyed"}:
                    entity.capabilities = frozenset()
                    entity.capability_tokens = ()
            world._used_entity_ids = set(checkpoint.used_entity_ids)
            world._applied_lifecycle_event_ids = set(checkpoint.applied_lifecycle_event_ids)
            world._lifecycle_ledger = {
                item.operation_id: LifecycleReceiptV2(
                    tick=item.tick,
                    operation_id=item.operation_id,
                    status=item.status,
                    applied_event_ids=item.applied_event_ids,
                    spawned_entity_ids=item.spawned_entity_ids,
                    despawned_entity_ids=item.despawned_entity_ids,
                )
                for item in checkpoint.lifecycle_ledger
            }
            world._tombstones = {
                item.entity_id: LifecycleTombstoneV2(
                    entity_id=item.entity_id,
                    tick=item.tick,
                    source_event_id=item.source_event_id,
                    adapters_closed=item.adapters_closed,
                    cleanup_errors=item.cleanup_errors,
                )
                for item in checkpoint.tombstones
            }
            if checkpoint.boundary_topology_hash != world._spatial_topology_hash:
                raise ValueError("checkpoint spatial topology anchor differs from resolved world")
            world._spatial_tick = checkpoint.spatial_clock.tick
            world._last_spatial_tick_start_seconds = (
                checkpoint.spatial_clock.tick_start_time_seconds
            )
            world._spatial_time_seconds = checkpoint.spatial_clock.next_tick_time_seconds
            world._zone_activation = dict(checkpoint.zone_activation_state)
            world._zone_activation_ledger = {
                item.operation_id: ZoneActivationReceiptV2(
                    operation_id=item.operation_id,
                    zone_id=item.zone_id,
                    active=item.active,
                    tick=item.tick,
                    changed=item.changed,
                )
                for item in checkpoint.zone_activation_ledger
            }
            world._restore_event_state(checkpoint.event_state)
            for zone_id, active_state in world._zone_activation.items():
                if zone_id in getattr(world._boundary_system, "_zone_activation", {}):
                    operation_id = next(
                        (
                            receipt.operation_id
                            for receipt in world._zone_activation_ledger.values()
                            if receipt.zone_id == zone_id
                        ),
                        f"checkpoint-zone:{zone_id}",
                    )
                    world._boundary_system.set_zone_activation(
                        zone_id=zone_id,
                        active=active_state,
                        tick=checkpoint.spatial_clock.tick,
                        operation_id=operation_id,
                    )
            restored_motion = tuple(
                _motion_receipt_from_plain(item.model_dump(mode="json"))
                for item in checkpoint.motion_ledger
            )
            world._motion_ledger = {
                receipt.operation_id: receipt for receipt, _fingerprint in restored_motion
            }
            world._motion_operation_fingerprints = {
                receipt.operation_id: fingerprint for receipt, fingerprint in restored_motion
            }
            world._consumed_provider_receipts = set(checkpoint.consumed_provider_receipts)
            world._combat_ledger = {
                str(item["operation_id"]): (
                    str(item["fingerprint"]),
                    DamageApplyReceiptV2.model_validate(item["receipt"]),
                )
                for item in checkpoint.combat_ledger
            }
            motion_by_operation = world._motion_ledger
            lifecycle_by_operation = world._lifecycle_ledger
            world._world_tick_ledger = {}
            world._typed_event_receipt_index = {}
            for item in checkpoint.world_tick_ledger:
                event_receipts = tuple(
                    WorldEventReceiptV2(
                        tick=int(value["tick"]),
                        operation_id=str(value["operation_id"]),
                        boundary_event_ids=tuple(value["boundary_event_ids"]),
                        collision_event_ids=tuple(value["collision_event_ids"]),
                        damage_intent_ids=tuple(value["damage_intent_ids"]),
                        resolved_event_ids=tuple(value.get("resolved_event_ids", ())),
                        typed_event_receipts=tuple(
                            TypedEventExecutionReceiptV2(
                                event_id=str(typed["event_id"]),
                                event_type=str(typed["event_type"]),
                                tick=int(typed["tick"]),
                                payload=_frozen_mapping(typed["payload"]),
                                payload_hash=str(typed["payload_hash"]),
                                owner_state_hash_before=str(typed["owner_state_hash_before"]),
                                owner_state_hash_after=str(typed["owner_state_hash_after"]),
                            )
                            for typed in value.get("typed_event_receipts", ())
                        ),
                    )
                    for value in item.event_receipts
                )
                damage_receipts = tuple(
                    DamageApplyReceiptV2.model_validate(value) for value in item.damage_receipts
                )
                from openmdbench.missions.engine_v2 import (
                    MetricDataMissingReceiptV2,
                    MetricScoreReceiptV2,
                    MetricValueOutOfRangeReceiptV2,
                    MissionTickReceiptV2,
                    ScoreInputV2,
                    ScoreReceiptV2,
                    TerminalMissionResultV2,
                )

                mission_receipts = tuple(
                    MissionTickReceiptV2(
                        tick=int(value["tick"]),
                        operation_id=str(value["operation_id"]),
                        triggered_rule_ids=tuple(value["triggered_rule_ids"]),
                        mission_states=tuple(value["mission_states"]),
                        emitted_event_ids=tuple(value["emitted_event_ids"]),
                        terminal_result=(
                            None
                            if value.get("terminal_result") is None
                            else TerminalMissionResultV2(**value["terminal_result"])
                        ),
                        snapshot_hash=str(value["snapshot_hash"]),
                    )
                    for value in item.mission_receipts
                )
                score_receipts = tuple(
                    ScoreReceiptV2(
                        metrics=tuple(
                            ScoreInputV2.model_validate(metric) for metric in value["metrics"]
                        ),
                        total=value["total"],
                        effective_weights=MappingProxyType(dict(value["effective_weights"])),
                        aggregation=str(value["aggregation"]),
                        direction=str(value["direction"]),
                        aggregation_version=str(value.get("aggregation_version", "legacy-v1")),
                        metric_receipts=tuple(
                            MetricScoreReceiptV2(**metric)
                            for metric in value.get("metric_receipts", ())
                        ),
                        metric_data_missing=tuple(
                            MetricDataMissingReceiptV2(**metric)
                            for metric in value.get("metric_data_missing", ())
                        ),
                        metric_value_out_of_range=tuple(
                            MetricValueOutOfRangeReceiptV2(**metric)
                            for metric in value.get("metric_value_out_of_range", ())
                        ),
                        mission_outcome=(
                            None
                            if value.get("mission_outcome") is None
                            else TerminalMissionResultV2(**value["mission_outcome"])
                        ),
                        competition_scores=MappingProxyType(dict(value["competition_scores"])),
                        training_rewards=MappingProxyType(dict(value["training_rewards"])),
                        tick=value.get("tick"),
                        operation_id=value.get("operation_id"),
                    )
                    for value in item.score_receipts
                )
                tick_receipt = WorldTickReceiptV2(
                    operation_id=item.operation_id,
                    start_tick=item.start_tick,
                    tick=item.tick,
                    steps=item.steps,
                    motion_receipts=tuple(
                        motion_by_operation[value] for value in item.motion_operation_ids
                    ),
                    lifecycle_receipts=tuple(
                        lifecycle_by_operation[value] for value in item.lifecycle_operation_ids
                    ),
                    event_receipts=event_receipts,
                    damage_receipts=damage_receipts,
                    provider_receipts=item.provider_receipts,
                    dynamics_receipts=tuple(
                        DynamicsStepReceiptV2(**value) for value in item.dynamics_receipts
                    ),
                    mission_receipts=mission_receipts,
                    score_receipts=score_receipts,
                    combat_receipts=tuple(
                        WorldCombatDispatchReceiptV2(
                            request_id=str(value["request_id"]),
                            tick=int(value["tick"]),
                            status=cast(Literal["executed", "rejected"], value["status"]),
                            execution=value.get("execution"),
                            error_code=value.get("error_code"),
                        )
                        for value in item.combat_receipts
                    ),
                    subsystem_receipts=tuple(
                        GenericSubsystemTickReceiptV2(
                            tick=int(value["tick"]),
                            stage_order=tuple(value["stage_order"]),
                            contacts=tuple(
                                SensorContactReceiptV2(**contact)
                                for contact in value.get("contacts", ())
                            ),
                            energy=tuple(
                                EnergyTickReceiptV2(**energy) for energy in value.get("energy", ())
                            ),
                            communication=CommunicationTickReceiptV2(**value["communication"]),
                            receipt_hash=str(value["receipt_hash"]),
                        )
                        for value in item.subsystem_receipts
                    ),
                )
                world._world_tick_ledger[item.operation_id] = (
                    item.fingerprint,
                    tick_receipt,
                )
                world._index_typed_event_receipts(tick_receipt.event_receipts)
            world._applied_tick_event_ids = {
                event_id
                for _fingerprint, receipt in world._world_tick_ledger.values()
                for event_receipt in receipt.event_receipts
                for event_id in event_receipt.resolved_event_ids
            }
            world._combat_rng_state = list(checkpoint.combat_rng_state)
            world._combat_cooldowns = dict(checkpoint.combat_cooldowns)
            expected_component_keys = set(world._combat_component_health)
            if set(checkpoint.combat_component_health) != expected_component_keys:
                raise ValueError("checkpoint combat component ownership differs from World")
            world._combat_component_health = dict(checkpoint.combat_component_health)
            world._combat_engagement_ledger = {
                item.request_id: item for item in checkpoint.combat_engagement_ledger
            }
            world._pending_impacts = {item.impact_id: item for item in checkpoint.pending_impacts}
            world._pending_impact_receipts = {
                item.impact_id: item for item in checkpoint.pending_impact_receipts
            }
            current_ammunition = {
                f"{entity_id}|{reference}": count
                for entity_id, entity in sorted(world._entities.items())
                for reference, count in sorted(entity.state.ammunition.items())
            }
            current_energy = {
                entity_id: entity.state.energy
                for entity_id, entity in sorted(world._entities.items())
                if entity.state.energy is not None
            }
            if current_ammunition != dict(checkpoint.combat_ammunition) or current_energy != dict(
                checkpoint.combat_energy
            ):
                raise ValueError("checkpoint combat counters differ from entity state")
            if world._combat_checkpoint_profiles() != tuple(
                _plain(item) for item in checkpoint.combat_profiles
            ):
                raise ValueError("checkpoint combat profile evidence differs from Resolved")
            restored_adapter_keys: set[tuple[str, str]] = set()
            for adapter_state in checkpoint.combat_adapter_states:
                entity_id = str(adapter_state["entity_id"])
                resource_ref = str(adapter_state["resource_ref"])
                adapter = (
                    world._world_adapters.get(resource_ref)
                    if entity_id == "__world__"
                    else world._entities[entity_id].adapters.get(resource_ref)
                )
                restore = getattr(adapter, "combat_restore", None)
                if not callable(restore):
                    raise ValueError("checkpoint combat adapter restore protocol is absent")
                restore(adapter_state["state"])
                restored_adapter_keys.add((entity_id, resource_ref))
            expected_adapter_keys = {
                (str(item["entity_id"]), str(item["resource_ref"]))
                for item in world._combat_adapter_states()
            }
            if restored_adapter_keys != expected_adapter_keys:
                raise ValueError("checkpoint combat adapter ownership differs from World")
            world._lifecycle_audit = [
                LifecycleAuditRecordV2(
                    operation_id=item.operation_id,
                    tick=item.tick,
                    status=item.status,
                    cleanup_errors=tuple(
                        error
                        for tombstone in checkpoint.tombstones
                        if tombstone.tick == item.tick
                        for error in tombstone.cleanup_errors
                    ),
                )
                for item in checkpoint.lifecycle_ledger
            ]
            world.tick = checkpoint.tick
            if checkpoint.mission_scoring_checkpoint is None:
                raise ValueError("checkpoint mission scoring state is absent")
            from openmdbench.missions.engine_v2 import (
                MissionScoringCheckpointV2,
                ZoneTransitionEvidenceV2,
            )

            mission_checkpoint = MissionScoringCheckpointV2.model_validate(
                checkpoint.mission_scoring_checkpoint
            )
            plugin_ids = {
                str(plugin_record["plugin_id"])
                for plugin_record in mission_checkpoint.plugin_states
            }
            if plugin_ids:
                resolved_plugin_factories = (
                    self._resolved_mission_plugin_factories(resolved, model_registry)
                    if mission_plugin_factories is None
                    else mission_plugin_factories
                )
                if set(resolved_plugin_factories) != plugin_ids:
                    raise ValueError("checkpoint mission plugin factories are incomplete")
                world._mission_engine._bind_resolved_plugin_factories(resolved_plugin_factories)
                for plugin_record in mission_checkpoint.plugin_states:
                    plugin_id = str(plugin_record["plugin_id"])
                    factory = resolved_plugin_factories[plugin_id]
                    plugin_checkpoint = plugin_record["checkpoint"]
                    if (
                        plugin_checkpoint["plugin_ref"] != factory.plugin_ref
                        or plugin_checkpoint["artifact_sha256"] != factory.artifact_sha256
                    ):
                        raise ValueError("checkpoint mission plugin trust evidence differs")
                    world._mission_engine.install_plugin(
                        plugin_id=plugin_id,
                        factory=factory,
                        session_id=checkpoint.session_id,
                        seed=checkpoint.seed,
                    )
            world._mission_engine.restore_state(mission_checkpoint)
            world._mission_zone_membership = {
                key: set(value) for key, value in checkpoint.mission_zone_membership.items()
            }
            world._mission_zone_transitions = [
                ZoneTransitionEvidenceV2.model_validate(item)
                for item in checkpoint.mission_zone_transitions
            ]
            world.contact_store = WorldContactStoreV2(
                tuple(
                    WorldContactEvidenceV2(
                        schema_version=item.schema_version,
                        evidence_id=item.evidence_id,
                        owner_entity_id=item.owner_entity_id,
                        target_entity_id=item.target_entity_id,
                        observed_tick=item.observed_tick,
                        age_ticks=item.age_ticks,
                        max_age_ticks=item.max_age_ticks,
                        confidence=item.confidence,
                        minimum_confidence=item.minimum_confidence,
                        quality=item.quality,
                        measurement_position_m=item.measurement_position_m,
                        confirmation_count=item.confirmation_count,
                        confirmation_frames=item.confirmation_frames,
                        stale_after_ticks=item.stale_after_ticks,
                        confirmed=item.confirmed,
                        source_sensor_ref=item.source_sensor_ref,
                    )
                    for item in checkpoint.combat_contact_evidence
                )
            )
            world.roe_rules = MappingProxyType(
                {
                    item.rule_id: WorldRoeRuleV2(
                        schema_version=item.schema_version,
                        rule_id=item.rule_id,
                        source_faction_id=item.source_faction_id,
                        target_faction_id=item.target_faction_id,
                        relationship=item.relationship,
                        engagement_permitted=item.engagement_permitted,
                    )
                    for item in checkpoint.combat_roe_rules
                }
            )
            world._combat_hit_model_state = (
                checkpoint.combat_hit_model_state.model_dump(mode="python")
                if checkpoint.combat_hit_model_state is not None
                else {}
            )
            world._missile_flights = {
                flight.missile_id: flight for flight in checkpoint.missile_flights
            }
            world._missile_terminal_receipts = {
                receipt.missile_id: receipt for receipt in checkpoint.missile_terminal_receipts
            }
            world.rng.setstate(checkpoint.rng_state)
            self._restore_checkpoint_native_adapters(
                world,
                checkpoint=checkpoint,
                definitions=definitions,
                model_registry=model_registry,
                record_adapter=record_adapter,
                record_cleanup=record_cleanup,
            )
            owned_adapters = [
                adapter
                for entity in world._entities.values()
                for adapter in entity.adapters.values()
            ] + list(world._world_adapters.values())
            world._rebuild_indexes()
            world._refresh_controller_ownership()
            if world.controller_ownership.to_canonical_dict() != _plain(
                checkpoint.controller_ownership
            ):
                raise ValueError("checkpoint controller ownership differs after restore")
            if (
                world.mission_fact_snapshot(tick=world.tick).fact_hash
                != mission_checkpoint.fact_hash
            ):
                raise ValueError("checkpoint mission fact evidence differs after restore")
            committed_status: Literal["committed", "committed_with_cleanup_errors"] = (
                "committed_with_cleanup_errors" if replacement_cleanup_errors else "committed"
            )
            committed_audit = CheckpointRestoreAuditV2(
                status=committed_status,
                created_adapter_instance_ids=tuple(created_ids),
                closed_adapter_instance_ids=closed_replaced_ids,
                adapter_stages=tuple(adapter_stages),
                replaced_initial_adapter_instance_ids=replaced_ids,
                closed_replaced_initial_adapter_instance_ids=closed_replaced_ids,
                failed_replaced_initial_adapter_instance_ids=failed_replaced_ids,
                cleanup_errors=replacement_cleanup_errors,
            )
            self._checkpoint_restore_audit.append(committed_audit)
            world._checkpoint_restore_audit = (committed_audit,)
            world._checkpoint_native_identity_overrides = {
                (snapshot.entity_id, snapshot.resource_ref): (
                    snapshot.instance_id,
                    snapshot.restored_from_instance_id,
                )
                for snapshot in checkpoint.native_adapter_snapshots
            }
            return world
        except Exception as error:
            if isinstance(error, _CheckpointAdapterStageFailure):
                failed_adapter_index = error.index
                failed_adapter_instance_id = error.instance_id
                failed_stage = error.stage
            closed_ids, _failed_ids, cleanup_errors = _cleanup_adapters_with_details(owned_adapters)
            self._checkpoint_restore_audit.append(
                CheckpointRestoreAuditV2(
                    status="rolled_back",
                    created_adapter_instance_ids=tuple(created_ids),
                    closed_adapter_instance_ids=closed_ids,
                    failed_adapter_index=failed_adapter_index,
                    failed_adapter_instance_id=failed_adapter_instance_id,
                    failed_stage=failed_stage,
                    adapter_stages=tuple(adapter_stages),
                    cleanup_errors=cleanup_errors,
                )
            )
            if isinstance(error, FactoryErrorV2) and error.code == (
                "factory.checkpoint_anchor_mismatch"
            ):
                raise
            raise _factory_error(
                "factory.checkpoint_restore_failed",
                ("checkpoint", "restore"),
                type(error).__name__,
                "checkpoint restore failed during isolated adapter staging",
                "repair the trusted registry or restore an intact anchored checkpoint",
            ) from error

    def _restore_checkpoint_native_adapters(
        self,
        world: WorldStateV2,
        *,
        checkpoint: WorldCheckpointV2,
        definitions: Mapping[str, ResolvedEntityV2],
        model_registry: ModelRegistryV2,
        record_adapter: Callable[[object, Literal["initial", "native_replacement"]], None],
        record_cleanup: Callable[[Sequence[object]], None],
    ) -> None:
        restore_factory = WorldFactoryV2(
            model_registry=model_registry,
            native_dynamics_factory=self._native_dynamics_factory,
        )
        staged: list[tuple[str, str, object]] = []
        for replacement_index, snapshot in enumerate(checkpoint.native_adapter_snapshots, start=1):
            if self.checkpoint_fault_injector.fail_on_native_replacement_index == replacement_index:
                raise _CheckpointAdapterStageFailure(
                    stage="native_replacement",
                    index=replacement_index,
                    instance_id=snapshot.resource_ref,
                )
            definition = definitions[snapshot.entity_id]
            bindings = (
                binding for values in definition.resource_bindings.values() for binding in values
            )
            binding = next(
                (item for item in bindings if item.exact_ref == snapshot.resource_ref),
                None,
            )
            if binding is None:
                raise ValueError("native snapshot binding is absent from resolved entity")
            restored = restore_factory.restore_native_adapter(
                snapshot,
                expected_binding=binding,
                checkpoint_anchor=snapshot.snapshot_hash,
            )
            record_adapter(restored, "native_replacement")
            staged.append((snapshot.entity_id, snapshot.resource_ref, restored))

        replaced: list[object] = []
        replacements: dict[str, dict[str, object]] = {}
        for entity_id, resource_ref, restored in staged:
            entity = world._entities[entity_id]
            adapters = replacements.setdefault(entity_id, dict(entity.adapters))
            old = adapters.get(resource_ref)
            if old is not None:
                replaced.append(old)
            adapters[resource_ref] = restored
        for entity_id, adapters in replacements.items():
            world._entities[entity_id].adapters = MappingProxyType(adapters)
        record_cleanup(tuple(replaced))

    def restore_native_adapter(
        self,
        snapshot: NativeDynamicsSnapshotV2,
        *,
        expected_binding: ResolvedResourceBindingV2,
        checkpoint_anchor: str,
    ) -> object:
        if not isinstance(expected_binding, ResolvedResourceBindingV2):
            raise _factory_error(
                "factory.model_evidence_mismatch",
                ("native_restore", "binding"),
                type(expected_binding).__name__,
                "native restore requires a typed resolved resource binding anchor",
                "use the exact binding embedded in the resolved scenario",
            )
        metadata = _metadata_for(
            self._model_registry,
            expected_binding.model_ref,
            path=("native_restore", expected_binding.exact_ref),
        )
        _validate_evidence(
            metadata,
            expected_binding.model_evidence,
            resource_type=expected_binding.resource_type,
            path=("native_restore", expected_binding.exact_ref),
        )
        if (
            snapshot.model_ref != expected_binding.model_ref
            or snapshot.resource_ref != expected_binding.exact_ref
            or snapshot.artifact_sha256 != expected_binding.model_evidence.artifact_sha256
        ):
            raise _factory_error(
                "factory.model_evidence_mismatch",
                ("native_restore", expected_binding.exact_ref, "snapshot"),
                snapshot.resource_ref,
                "native checkpoint differs from the resolved binding identity",
                "restore a checkpoint created from this exact resolved resource",
            )
        try:
            expected_identity = compute_native_resolved_binding_identity_v2(
                model_ref=expected_binding.model_ref,
                resource_ref=expected_binding.exact_ref,
                model_metadata=metadata,
                normalized_content=expected_binding.normalized_content,
            )
            return (self._native_dynamics_factory or NativeDynamicsAdapterFactoryV2()).restore(
                snapshot,
                expected_binding_identity=expected_identity,
                checkpoint_anchor=checkpoint_anchor,
                model_metadata=metadata,
            )
        except NativeDynamicsErrorV2 as error:
            raise _factory_error(
                "factory.native_restore_failed",
                ("native_restore", expected_binding.exact_ref),
                error.code,
                "native checkpoint failed its anchored restore contract",
                "restore the unmodified checkpoint with the matching resolved binding",
            ) from error

    def build(
        self,
        resolved: ResolvedScenarioV2,
        *,
        session_id: str | None = None,
        seed: int | None = None,
    ) -> WorldStateV2:
        if not isinstance(resolved, ResolvedScenarioV2):
            raise _factory_error(
                "factory.definition_invalid",
                ("scenario",),
                type(resolved).__name__,
                "world factory requires a resolved v2 scenario",
                "compile and integrity-check the scenario before runtime construction",
            )
        if session_id is not None and (
            not isinstance(session_id, str) or not session_id or len(session_id) > 256
        ):
            raise _factory_error(
                "factory.session_id_invalid",
                ("session", "id"),
                session_id,
                "session identity must be a bounded nonempty string",
                "provide a unique nonempty session identifier up to 256 characters",
            )
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise _factory_error(
                "factory.seed_invalid",
                ("session", "seed"),
                seed,
                "runtime seed must be an exact integer",
                "provide an integer deterministic seed excluding booleans",
            )
        try:
            resolved.validate_integrity()
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise _factory_error(
                "factory.resolved_integrity_invalid",
                ("resolved", "integrity"),
                resolved.resolved_hash,
                "resolved scenario semantic or canonical hash integrity failed",
                "recompile the immutable scenario with the trusted v2 compiler",
            ) from error
        schedule = _schedule(resolved.events)
        self._validate_registry_snapshot(
            resolved.model_registry_snapshot,
            expected_hash=resolved.model_registry_hash,
        )
        built: dict[str, _RuntimeEntityV2] = {}
        world_adapters: dict[str, object] = {}
        owned_adapters: list[object] = []
        adapter_instances: set[int] = set()
        seed_text = resolved.catalog_hash.removeprefix("sha256:")
        effective_seed = int(seed_text[:16], 16) if seed is None and seed_text else seed or 0
        try:
            for binding in resolved.world_resource_bindings:
                adapter = self._entity_factory._create_adapter(
                    binding,
                    entity_id="__world__",
                    session_seed=effective_seed,
                    path=("world_resource_bindings", binding.exact_ref),
                )
                if id(adapter) in adapter_instances:
                    raise _factory_error(
                        "factory.adapter_instance_reused",
                        ("world_resource_bindings", binding.exact_ref, "adapter"),
                        binding.exact_ref,
                        "a model factory reused one mutable adapter instance",
                        "return a fresh independently owned adapter for every binding",
                    )
                adapter_instances.add(id(adapter))
                world_adapters[binding.exact_ref] = adapter
                owned_adapters.append(adapter)
            for definition in sorted(resolved.entities, key=lambda item: item.id):
                if not isinstance(definition, ResolvedEntityV2):
                    raise _factory_error(
                        "factory.definition_invalid",
                        ("entities", definition.id),
                        type(definition).__name__,
                        "scenario contains an entity without resolved resource bindings",
                        "compile through resource closure before building the runtime world",
                    )
                entity = self._entity_factory._build_owned(
                    definition,
                    adapter_instances=adapter_instances,
                    session_seed=effective_seed,
                )
                built[definition.id] = entity
                owned_adapters.extend(entity.adapters.values())
        except FactoryErrorV2:
            _cleanup_adapters(owned_adapters)
            raise
        except Exception as error:
            _cleanup_adapters(owned_adapters)
            raise _factory_error(
                "factory.adapter_creation_failed",
                ("entities", "construction"),
                type(error).__name__,
                "runtime entity construction failed at the trusted plugin boundary",
                "repair the registered factory and retry an atomic world build",
            ) from error
        try:
            controller_ownership = build_controller_ownership(
                slots=resolved.controller_slots,
                uncontrolled_policy=resolved.controller_policy,
                entity_factions={
                    entity_id: entity.faction_id for entity_id, entity in built.items()
                },
                entity_tokens={
                    entity_id: entity.capability_tokens for entity_id, entity in built.items()
                },
                lifecycle_schedule=schedule,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            _cleanup_adapters(owned_adapters)
            raise _factory_error(
                "factory.resolved_integrity_invalid",
                ("controller_slots", "ownership"),
                type(error).__name__,
                "resolved controller ownership or spawn reservation is inconsistent",
                "recompile valid controller claims and future spawn bindings",
            ) from error
        # Scenario display identity is deliberately absent from runtime behavior.
        boundary_system, spatial_topology_hash, geography = _spatial_runtime(
            resolved, tuple(item.definition for item in built.values())
        )
        world = WorldStateV2(
            entities=built,
            world_resource_bindings=resolved.world_resource_bindings,
            world_adapters=world_adapters,
            factions=resolved.factions,
            relationships=resolved.relationships,
            controller_slots=resolved.controller_slots,
            controller_ownership=controller_ownership,
            lifecycle_schedule=schedule,
            resolved_scenario=resolved,
            resolved_events=resolved.events,
            session_id=session_id or "session.default",
            seed=effective_seed,
            entity_factory=self._entity_factory,
            controller_policy=resolved.controller_policy,
            resolved_hash=resolved.resolved_hash,
            catalog_hash=resolved.catalog_hash,
            model_registry_hash=resolved.model_registry_hash,
            boundary_system=boundary_system,
            geography=geography,
            spatial_topology_hash=spatial_topology_hash,
        )
        for policy in resolved.world.roe_rules:
            world.install_roe_policy(
                WorldRoeRuleV2(
                    rule_id=policy.id,
                    source_faction_id=policy.source_faction_id,
                    target_faction_id=policy.target_faction_id,
                    relationship=policy.relationship,
                    engagement_permitted=policy.engagement_permitted,
                )
            )
        try:
            plugin_factories = self._resolved_mission_plugin_factories(
                resolved, self._model_registry
            )
            world._mission_engine._bind_resolved_plugin_factories(plugin_factories)
            for plugin_id, plugin_factory in plugin_factories.items():
                world._mission_engine.install_plugin(
                    plugin_id=plugin_id,
                    factory=plugin_factory,
                    session_id=world.session_id,
                    seed=effective_seed,
                )
        except Exception as error:
            world.close()
            raise _factory_error(
                "factory.mission_plugin_invalid",
                ("scoring", "plugins"),
                type(error).__name__,
                "resolved scoring plugin could not be materialized as session-owned state",
                "register a trusted fresh plugin with snapshot and restore protocols",
            ) from error
        return world

    def _validate_registry_snapshot(
        self,
        expected: Sequence[ModelFactoryMetadataV2],
        *,
        expected_hash: str,
    ) -> None:
        for evidence in expected:
            metadata = _metadata_for(
                self._model_registry,
                evidence.exact_ref,
                path=("model_registry_snapshot", evidence.exact_ref),
            )
            if not metadata.trusted or not evidence.trusted:
                raise _factory_error(
                    "factory.model_untrusted",
                    ("model_registry_snapshot", evidence.exact_ref, "trusted"),
                    metadata.trusted,
                    "runtime registry model is not trusted",
                    "install a trusted model factory matching the resolved snapshot",
                )
            interface_fields = (
                "interface_version",
                "input_schema",
                "output_schema",
                "resource_types",
            )
            if any(
                getattr(metadata, field) != getattr(evidence, field) for field in interface_fields
            ):
                raise _factory_error(
                    "factory.model_interface_incompatible",
                    ("model_registry_snapshot", evidence.exact_ref, "interface"),
                    metadata.exact_ref,
                    "runtime model interface differs from compiled registry evidence",
                    "restore the recorded interface or recompile with the new registry",
                )
            if metadata.model_dump(mode="json") != evidence.model_dump(mode="json"):
                raise _factory_error(
                    "factory.model_evidence_mismatch",
                    ("model_registry_snapshot", evidence.exact_ref, "metadata"),
                    metadata.exact_ref,
                    "runtime model metadata differs from complete compiled evidence",
                    "restore the exact metadata and artifact or recompile the scenario",
                )
        try:
            actual_hash = self._model_registry.content_hash
        except (AttributeError, TypeError, ValueError) as error:
            raise _factory_error(
                "factory.model_registry_hash_mismatch",
                ("model_registry", "content_hash"),
                type(error).__name__,
                "runtime model registry cannot produce canonical hash evidence",
                "freeze a valid canonical model registry before world construction",
            ) from error
        if actual_hash != expected_hash:
            raise _factory_error(
                "factory.model_registry_hash_mismatch",
                ("model_registry", "content_hash"),
                actual_hash,
                "runtime registry hash differs from the compiled registry snapshot",
                "restore the exact frozen registry or recompile against this registry",
            )


__all__ = [
    "AdapterDiagnosticV2",
    "CombatInventorySnapshotV2",
    "CapabilitySelectorV2",
    "CapabilityTokenV2",
    "ControllerClaimV2",
    "ControllerOwnershipIndexV2",
    "ControllerReservationV2",
    "CheckpointAdapterCleanupErrorV2",
    "CheckpointEntityV2",
    "CheckpointLifecycleReceiptV2",
    "CheckpointRestoreAuditV2",
    "CheckpointRestoreFaultInjectorV2",
    "CheckpointTombstoneV2",
    "EntityFactoryV2",
    "EntityControlCommandV2",
    "EntityViewV2",
    "FactoryErrorV2",
    "FrozenEntityStateV2",
    "ImpactDamageEvidenceV2",
    "ImpactMagnitudeModelV2",
    "LifecycleScheduleEntryV2",
    "MessageIntentV2",
    "LifecycleAuditRecordV2",
    "LifecycleFaultInjectorV2",
    "LifecycleReceiptV2",
    "LifecycleTombstoneV2",
    "KinematicMotionCandidateV2",
    "MotionCandidateV2",
    "MotionEligibilityEntryV2",
    "MotionEligibilitySnapshotV2",
    "MotionPipelineErrorV2",
    "MotionReceiptV2",
    "DynamicsStepReceiptV2",
    "SUPPORTED_TICK_EVENT_TYPES",
    "ResolvedSpatialEffectPolicyV2",
    "TypedEventExecutionReceiptV2",
    "WorldEventStateSnapshotV2",
    "WorldEventReceiptV2",
    "WorldPresentationSnapshotV2",
    "WorldPresentationTickReceiptV2",
    "WorldCombatDispatchReceiptV2",
    "WorldTickInputV2",
    "WorldTickReceiptV2",
    "WorldFactoryV2",
    "WorldCheckpointV2",
    "WorldAdapterTransactionV2",
    "WorldSnapshotV2",
    "WorldStateV2",
]

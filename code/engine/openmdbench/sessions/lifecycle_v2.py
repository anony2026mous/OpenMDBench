"""Schema-v2 session lifecycle and the sole action-to-World write boundary."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_serializer, model_validator

from openmdbench.catalog.v2 import ModelRegistryV2
from openmdbench.combat.models_v2 import EngagementRequestV2
from openmdbench.combat.system_v2 import CombatCatalogSnapshotV2, CombatSystemV2
from openmdbench.dynamics.native_v2 import FIXED_MODEL_REF, MMG_MODEL_REF
from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2
from openmdbench.schemas.core_v2 import ObservationV2
from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    DiscreteActionV2,
    PersistentCommandV2,
)
from openmdbench.world.factory_v2 import (
    EntityControlCommandV2,
    MessageIntentV2,
    MotionEligibilityEntryV2,
    MotionEligibilitySnapshotV2,
    WorldCheckpointV2,
    WorldFactoryV2,
    WorldStateV2,
    WorldTickInputV2,
)

_HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _ActionPayloadV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class NavigationPayloadV2(_ActionPayloadV2):
    speed_mps: float = Field(ge=0.0)
    heading_deg: float = Field(ge=0.0, lt=360.0)
    altitude_m: float | None = None
    depth_m: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def validate_vertical_target(self) -> Self:
        if self.altitude_m is not None and self.depth_m is not None:
            raise ValueError("navigation chooses altitude or depth, not both")
        return self


class PatrolPayloadV2(_ActionPayloadV2):
    speed_mps: float = Field(ge=0.0)
    waypoints_m: tuple[tuple[float, float, float], ...] = Field(min_length=1)


class HoldPayloadV2(_ActionPayloadV2):
    pass


class SensorModePayloadV2(_ActionPayloadV2):
    mode: str = Field(min_length=1, max_length=128)


class RelayModePayloadV2(_ActionPayloadV2):
    mode: str = Field(min_length=1, max_length=128)


class CiwsAutoPayloadV2(_ActionPayloadV2):
    enabled: bool


class FireWeaponPayloadV2(_ActionPayloadV2):
    weapon_ref: str = Field(min_length=1, max_length=256)
    target_id: str | None = Field(default=None, min_length=1, max_length=256)
    contact_id: str | None = Field(default=None, min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_target_reference(self) -> Self:
        if (self.target_id is None) == (self.contact_id is None):
            raise ValueError("fire action chooses exactly one target id or opaque contact id")
        return self


class ReleasePayloadV2(_ActionPayloadV2):
    payload_ref: str = Field(min_length=1, max_length=256)
    target_id: str | None = Field(default=None, min_length=1, max_length=256)


class SendMessagePayloadV2(_ActionPayloadV2):
    recipient_id: str | None = Field(default=None, min_length=1, max_length=256)
    recipient_controller_slots: tuple[str, ...] = ()
    broadcast_faction_id: str | None = Field(default=None, min_length=1, max_length=256)
    message: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def validate_recipient_scope(self) -> Self:
        selectors = (
            int(self.recipient_id is not None)
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
            raise ValueError("send_message requires exactly one explicit recipient scope")
        return self


class DeviceActionPayloadV2(_ActionPayloadV2):
    device_ref: str = Field(min_length=1, max_length=256)
    operation: str = Field(min_length=1, max_length=128)


class RamPayloadV2(_ActionPayloadV2):
    target_id: str = Field(min_length=1, max_length=256)


class ActionContractV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    action_type: str
    payload_model: type[BaseModel]
    world_intent_type: str
    receipt_type: str
    dispatch_available: bool


_PERSISTENT_ACTION_CONTRACTS: Mapping[str, ActionContractV2] = MappingProxyType(
    {
        "navigation": ActionContractV2(
            action_type="navigation",
            payload_model=NavigationPayloadV2,
            world_intent_type="EntityControlCommandV2",
            receipt_type="DynamicsStepReceiptV2",
            dispatch_available=True,
        ),
        "patrol": ActionContractV2(
            action_type="patrol",
            payload_model=PatrolPayloadV2,
            world_intent_type="PatrolRouteIntentV2",
            receipt_type="MotionReceiptV2",
            dispatch_available=False,
        ),
        "hold": ActionContractV2(
            action_type="hold",
            payload_model=HoldPayloadV2,
            world_intent_type="EntityControlCommandV2",
            receipt_type="DynamicsStepReceiptV2",
            dispatch_available=True,
        ),
        "sensor_mode": ActionContractV2(
            action_type="sensor_mode",
            payload_model=SensorModePayloadV2,
            world_intent_type="SensorModeIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=False,
        ),
        "relay_mode": ActionContractV2(
            action_type="relay_mode",
            payload_model=RelayModePayloadV2,
            world_intent_type="RelayModeIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=False,
        ),
        "ciws_auto": ActionContractV2(
            action_type="ciws_auto",
            payload_model=CiwsAutoPayloadV2,
            world_intent_type="CiwsPolicyIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=False,
        ),
    }
)

_DISCRETE_ACTION_CONTRACTS: Mapping[str, ActionContractV2] = MappingProxyType(
    {
        "fire_weapon": ActionContractV2(
            action_type="fire_weapon",
            payload_model=FireWeaponPayloadV2,
            world_intent_type="EngagementRequestV2",
            receipt_type="WorldCombatDispatchReceiptV2",
            dispatch_available=True,
        ),
        "release_payload": ActionContractV2(
            action_type="release_payload",
            payload_model=ReleasePayloadV2,
            world_intent_type="ReleasePayloadIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=False,
        ),
        "send_message": ActionContractV2(
            action_type="send_message",
            payload_model=SendMessagePayloadV2,
            world_intent_type="MessageIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=True,
        ),
        "device_action": ActionContractV2(
            action_type="device_action",
            payload_model=DeviceActionPayloadV2,
            world_intent_type="DeviceActionIntentV2",
            receipt_type="WorldEventReceiptV2",
            dispatch_available=False,
        ),
        "ram": ActionContractV2(
            action_type="ram",
            payload_model=RamPayloadV2,
            world_intent_type="RamMotionIntentV2",
            receipt_type="CollisionEventV2",
            dispatch_available=False,
        ),
    }
)


def persistent_action_contract_v2(kind: str) -> ActionContractV2:
    try:
        return _PERSISTENT_ACTION_CONTRACTS[kind]
    except KeyError as error:
        raise ValueError("unknown persistent schema-v2 action type") from error


def discrete_action_contract_v2(kind: str) -> ActionContractV2:
    try:
        return _DISCRETE_ACTION_CONTRACTS[kind]
    except KeyError as error:
        raise ValueError("unknown discrete schema-v2 action type") from error


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_plain(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {str(key): _plain(getattr(value, key)) for key in value.__dataclass_fields__}
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list, set, frozenset)):
        return tuple(_freeze(item) for item in value)
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        _plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class SessionStateV2(StrEnum):
    CREATED = "created"
    LOADED = "loaded"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    CLOSED = "closed"


SESSION_TRANSITIONS_V2: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "created": ("loaded", "closed"),
        "loaded": ("running", "stopped", "closed"),
        "running": ("paused", "stopped"),
        "paused": ("running", "stopped", "closed"),
        "stopped": ("closed",),
        "closed": (),
    }
)


class RunnerModeV2(StrEnum):
    CONTINUOUS = "continuous"
    LOCKSTEP = "lockstep"
    REPLAY = "replay"


REPLAY_INITIALIZES_WORLD = False


class PersistentCommandStatusV2(StrEnum):
    QUEUED = "queued"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    COMPLETED = "completed"
    REPLACED = "replaced"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DiscreteActionStatusV2(StrEnum):
    QUEUED = "queued"
    ACCEPTED = "accepted"
    APPLIED = "applied"
    EXECUTED = "executed"
    REJECTED = "rejected"


ACTION_VALIDATION_ORDER_V2 = (
    "session_state",
    "operation_fingerprint",
    "tick_window",
    "controller_authority",
    "entity_lifecycle",
    "faction_ownership",
    "action_schema",
    "required_capability",
    "payload",
)


class SessionErrorV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(pattern=r"^session\.[a-z][a-z0-9_]*$")
    message: str = Field(min_length=1)
    path: tuple[str, ...]
    value: Any = None
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class SessionFailureV2(ValueError):
    def __init__(self, error: SessionErrorV2) -> None:
        self.error = error
        self.code = error.code
        self.path = error.path
        self.value = error.value
        self.reason = error.reason
        self.suggestion = error.suggestion
        super().__init__(f"{error.code}: {error.message}")


def _fail(
    code: str,
    path: Sequence[str],
    value: Any,
    reason: str,
    suggestion: str,
) -> SessionFailureV2:
    return SessionFailureV2(
        SessionErrorV2(
            code=code,
            message=reason,
            path=tuple(path),
            value=_plain(value),
            reason=reason,
            suggestion=suggestion,
        )
    )


def action_batch_fingerprint_v2(batch: ActionBatchV2) -> str:
    if not isinstance(batch, ActionBatchV2):
        raise TypeError("action fingerprint requires ActionBatchV2")
    return _canonical_hash(batch.model_dump(mode="json"))


class ActionReceiptV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=256)
    batch_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=1, max_length=256)
    operation_id: str = Field(min_length=1, max_length=256)
    fingerprint: str = Field(pattern=_HASH_PATTERN)
    status: Literal["queued", "accepted", "applied", "rejected"]
    submitted_tick: StrictInt = Field(ge=0)
    scheduled_tick: StrictInt = Field(ge=0)
    persistent_command_ids: tuple[str, ...] = ()
    discrete_action_ids: tuple[str, ...] = ()


class ActionChildReceiptV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    child_id: str = Field(min_length=1, max_length=256)
    kind: Literal["persistent", "discrete", "fallback"]
    status: str = Field(min_length=1, max_length=64)
    tick: StrictInt = Field(ge=0)
    request_id: str | None = None
    error_code: str | None = None


class ActionApplyReceiptV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    session_id: str
    operation_id: str
    expected_tick: StrictInt = Field(ge=0)
    request_fingerprint: str = Field(pattern=_HASH_PATTERN)
    queue_fingerprint: str = Field(pattern=_HASH_PATTERN)
    tick: StrictInt = Field(ge=0)
    activated_command_ids: tuple[str, ...]
    consumed_discrete_action_ids: tuple[str, ...]
    expired_command_ids: tuple[str, ...]
    fallback_command_ids: tuple[str, ...] = ()
    child_receipts: tuple[ActionChildReceiptV2, ...] = ()
    world_receipt: Any
    receipt_hash: str = Field(pattern=_HASH_PATTERN)

    @field_serializer("world_receipt")
    def serialize_world_receipt(self, value: Any) -> Any:
        return _plain(value)

    @field_serializer("child_receipts")
    def serialize_child_receipts(self, value: Any) -> Any:
        return _plain(value)


class SessionWorldViewV2:
    """Read-only facade over the session-owned World authority."""

    def __init__(self, world: WorldStateV2) -> None:
        self._world = world
        self._checkpoint_cache: WorldCheckpointV2 | None = None

    @property
    def tick(self) -> int:
        return self._world.tick

    @property
    def session_id(self) -> str:
        return self._world.session_id

    @property
    def resolved_hash(self) -> str:
        return self._world.resolved_hash

    @property
    def authority_tokens(self) -> Mapping[str, Any]:
        return self._world.authority_tokens

    def get(self, entity_id: str) -> Any:
        return self._world.get(entity_id)

    def get_optional(self, entity_id: str) -> Any:
        return self._world.get_optional(entity_id)

    def entities_stable(self) -> tuple[Any, ...]:
        return self._world.entities_stable()

    def motion_eligibility_snapshot(
        self, *, expected_tick: int
    ) -> MotionEligibilitySnapshotV2:
        return self._world.motion_eligibility_snapshot(expected_tick=expected_tick)

    def checkpoint(self) -> WorldCheckpointV2:
        cached = self._checkpoint_cache
        if cached is not None and cached.tick == self._world.tick:
            return cached
        checkpoint = self._world.checkpoint()
        self._checkpoint_cache = checkpoint
        return checkpoint

    def presentation_snapshot(self) -> Any:
        """Return a lightweight display snapshot without creating a checkpoint."""

        return self._world.presentation_snapshot()

    def observation(self, *, observer_faction_id: str) -> ObservationV2:
        return self._world.observation_snapshot(observer_faction_id=observer_faction_id)

    def controller_observation(self, *, controller_slot_id: str) -> ObservationV2:
        return self._world.controller_observation_snapshot(controller_slot_id=controller_slot_id)


class SessionCheckpointV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    session_id: str = Field(min_length=1, max_length=256)
    session_state: SessionStateV2
    runner_mode: RunnerModeV2
    seed: StrictInt = Field(ge=0)
    resolved_hash: str = Field(pattern=_HASH_PATTERN)
    catalog_hash: str = Field(pattern=_HASH_PATTERN)
    model_registry_hash: str = Field(pattern=_HASH_PATTERN)
    physics_dt_seconds: float = Field(gt=0.0)
    decision_interval_ticks: StrictInt = Field(ge=1)
    world_checkpoint_hash: str = Field(pattern=_HASH_PATTERN)
    world_checkpoint: dict[str, Any]
    pending_batches: tuple[dict[str, Any], ...]
    batch_ledger: tuple[dict[str, Any], ...] = ()
    persistent_commands: tuple[dict[str, Any], ...]
    consumed_discrete_action_ids: tuple[str, ...]
    action_statuses: tuple[dict[str, Any], ...]
    operation_ledger: tuple[dict[str, Any], ...]
    child_ledger: tuple[dict[str, Any], ...] = ()
    rng_state_hash: str = Field(pattern=_HASH_PATTERN)
    checkpoint_hash: str = Field(pattern=_HASH_PATTERN)

    @model_validator(mode="after")
    def validate_semantics(self) -> Self:
        if not math.isfinite(self.physics_dt_seconds):
            raise ValueError("session physics duration must be finite")
        if self.consumed_discrete_action_ids != tuple(
            sorted(set(self.consumed_discrete_action_ids))
        ):
            raise ValueError("consumed discrete identities are not canonical")
        operation_ids = tuple(str(item.get("operation_id", "")) for item in self.operation_ledger)
        if (
            not all(operation_ids)
            or operation_ids != tuple(sorted(operation_ids))
            or len(operation_ids) != len(set(operation_ids))
        ):
            raise ValueError("session operation ledger is not canonical")
        persistent_ids = tuple(str(item.get("command_id", "")) for item in self.persistent_commands)
        if persistent_ids != tuple(sorted(set(persistent_ids))):
            raise ValueError("persistent command checkpoint is not canonical")
        child_ids = tuple(str(item.get("child_id", "")) for item in self.child_ledger)
        if child_ids != tuple(sorted(set(child_ids))):
            raise ValueError("session child ledger is not canonical")
        batch_ids = tuple(
            str(cast(Mapping[str, Any], item.get("batch", {})).get("idempotency_key", ""))
            for item in self.batch_ledger
        )
        if batch_ids != tuple(sorted(set(batch_ids))):
            raise ValueError("session batch ledger is not canonical")
        batches: dict[str, tuple[ActionBatchV2, str]] = {}
        for item in self.batch_ledger:
            batch = ActionBatchV2.model_validate(item.get("batch"))
            authority_token = item.get("authority_token")
            receipt = ActionReceiptV2.model_validate(item.get("receipt"))
            if (
                not isinstance(authority_token, str)
                or not authority_token
                or receipt.fingerprint != action_batch_fingerprint_v2(batch)
                or receipt.batch_id != batch.batch_id
                or receipt.idempotency_key != batch.idempotency_key
                or receipt.persistent_command_ids
                != tuple(item.command_id for item in batch.persistent_commands)
                or receipt.discrete_action_ids
                != tuple(item.action_id for item in batch.discrete_actions)
            ):
                raise ValueError("session batch ledger evidence is inconsistent")
            batches[batch.idempotency_key] = (batch, authority_token)
        status_by_id = {
            str(item.get("id", "")): str(item.get("status", "")) for item in self.action_statuses
        }
        for item in self.child_ledger:
            child = ActionChildReceiptV2.model_validate(item)
            if status_by_id.get(child.child_id) != child.status:
                raise ValueError("session child and status ledgers disagree")
        for item in self.operation_ledger:
            operation_id = str(item["operation_id"])
            fingerprint = str(item["fingerprint"])
            raw_receipt = cast(Mapping[str, Any], item["receipt"])
            if "batch_id" in raw_receipt:
                receipt = ActionReceiptV2.model_validate(raw_receipt)
                batch_record = batches.get(receipt.idempotency_key)
                if batch_record is None:
                    raise ValueError("session operation has no authoritative batch evidence")
                batch, authority_token = batch_record
                expected = _canonical_hash(
                    {
                        "operation_id": operation_id,
                        "batch_fingerprint": action_batch_fingerprint_v2(batch),
                        "authority_token": authority_token,
                        "expected_tick": receipt.submitted_tick,
                    }
                )
            else:
                apply_receipt = ActionApplyReceiptV2.model_validate(raw_receipt)
                receipt_payload = apply_receipt.model_dump(mode="json", exclude={"receipt_hash"})
                if apply_receipt.receipt_hash != _canonical_hash(receipt_payload):
                    raise ValueError("session apply receipt hash mismatch")
                expected = _canonical_hash(
                    {
                        "request_fingerprint": apply_receipt.request_fingerprint,
                        "queue_fingerprint": apply_receipt.queue_fingerprint,
                    }
                )
            if fingerprint != expected:
                raise ValueError("session operation fingerprint is inconsistent")
        payload = self.model_dump(mode="json", exclude={"checkpoint_hash"})
        if self.checkpoint_hash != _canonical_hash(payload):
            raise ValueError("session checkpoint hash mismatch")
        for name in (
            "world_checkpoint",
            "pending_batches",
            "batch_ledger",
            "persistent_commands",
            "action_statuses",
            "operation_ledger",
            "child_ledger",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        return self

    @field_serializer(
        "world_checkpoint",
        "pending_batches",
        "batch_ledger",
        "persistent_commands",
        "action_statuses",
        "operation_ledger",
        "child_ledger",
    )
    def serialize_evidence(self, value: Any) -> Any:
        return _plain(value)

    @staticmethod
    def compute_hash(value: Mapping[str, Any] | SessionCheckpointV2) -> str:
        payload = (
            value.model_dump(mode="json") if isinstance(value, SessionCheckpointV2) else dict(value)
        )
        payload.pop("checkpoint_hash", None)
        return _canonical_hash(payload)


class ActionPipelineV2:
    """Session-owned queue; submission never mutates World state."""

    def __init__(
        self,
        *,
        session_id: str,
        world: WorldStateV2,
        state_provider: Callable[[], SessionStateV2],
        physics_dt_seconds: float,
    ) -> None:
        self.session_id = session_id
        self._world = world
        self._world_view = SessionWorldViewV2(world)
        self._state_provider = state_provider
        self._physics_dt_seconds = physics_dt_seconds
        self._pending: dict[str, tuple[ActionBatchV2, int, ActionReceiptV2, str]] = {}
        self._active_persistent: dict[tuple[str, str], PersistentCommandV2] = {}
        self._consumed_discrete: set[str] = set()
        self._statuses: dict[str, str] = {}
        self._submit_ledger: dict[str, tuple[str, ActionReceiptV2]] = {}
        self._batch_ledger: dict[str, tuple[ActionBatchV2, str, ActionReceiptV2]] = {}
        self._operation_ledger: dict[str, tuple[str, Any]] = {}
        self._child_ledger: dict[str, ActionChildReceiptV2] = {}
        self._child_identity_ledger: dict[str, tuple[str, str]] = {}
        self._lock = RLock()

    def _replace_world_after_rollback(self, world: WorldStateV2) -> None:
        self._world = world
        self._world_view = SessionWorldViewV2(world)

    @property
    def world_view(self) -> SessionWorldViewV2:
        return self._world_view

    def owns_world_writer(self, writer: Callable[[WorldTickInputV2], Any]) -> bool:
        return getattr(writer, "__self__", None) is self._world

    @property
    def persistent_commands(self) -> tuple[PersistentCommandV2, ...]:
        return tuple(sorted(self._active_persistent.values(), key=lambda item: item.command_id))

    @property
    def consumed_discrete_action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._consumed_discrete))

    @property
    def operation_ledger(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "operation_id": operation_id,
                "fingerprint": fingerprint,
                "receipt": _plain(receipt),
            }
            for operation_id, (fingerprint, receipt) in sorted(self._operation_ledger.items())
        )

    @property
    def child_ledger(self) -> tuple[ActionChildReceiptV2, ...]:
        return tuple(self._child_ledger[key] for key in sorted(self._child_ledger))

    @property
    def status_snapshot(self) -> Mapping[str, str]:
        return MappingProxyType(dict(sorted(self._statuses.items())))

    def _authority_claim(self, authority_token: str, entity_id: str) -> Any:
        grant = self._world_view.authority_tokens.get(authority_token)
        if grant is None or entity_id not in grant.entity_ids:
            raise _fail(
                "session.controller_authority_invalid",
                ("actions", entity_id, "authority_token"),
                authority_token,
                "authority token does not grant this controller-owned entity",
                "use a World-owned entity or controller authority token",
            )
        claims = self._world.controller_ownership.by_entity(entity_id)
        claim = next((item for item in claims if item.controller_id == grant.controller_id), None)
        if claim is None:
            raise _fail(
                "session.controller_authority_invalid",
                ("actions", entity_id, "controller"),
                grant.controller_id,
                "controller grant differs from immutable ownership evidence",
                "rebuild the session from intact Resolved controller bindings",
            )
        return claim

    @staticmethod
    def _required_capability(item: PersistentCommandV2 | DiscreteActionV2) -> str | None:
        kind = getattr(item, "command_type", getattr(item, "action_type", ""))
        return {
            "navigation": "dynamics",
            "patrol": "dynamics",
            "sensor_mode": "sensor",
            "relay_mode": "communication",
            "fire_weapon": "weapon",
            "release_payload": "weapon",
            "send_message": "communication",
        }.get(str(kind))

    @classmethod
    def _capability_available(
        cls, entity: Any, item: PersistentCommandV2 | DiscreteActionV2
    ) -> bool:
        required = cls._required_capability(item)
        if required is not None and required not in entity.capabilities:
            return False
        if not isinstance(item, PersistentCommandV2) or item.command_type not in {
            "navigation",
            "patrol",
        }:
            return True
        bindings = entity.definition.resource_bindings.get("dynamics", ())
        return any(binding.model_ref != FIXED_MODEL_REF for binding in bindings)

    @staticmethod
    def _validate_payload(item: PersistentCommandV2 | DiscreteActionV2) -> None:
        if isinstance(item, PersistentCommandV2):
            contract = persistent_action_contract_v2(item.command_type)
        elif isinstance(item, DiscreteActionV2):
            contract = discrete_action_contract_v2(item.action_type)
        else:
            raise TypeError("action child must be a schema-v2 typed DTO")
        if not contract.dispatch_available:
            raise ValueError("action type has no authoritative World dispatcher")
        contract.payload_model.model_validate(item.payload)

    def submit(
        self,
        *,
        batch: ActionBatchV2,
        authority_token: str,
        operation_id: str,
        expected_tick: int,
    ) -> ActionReceiptV2:
        with self._lock:
            if self._state_provider() not in {
                SessionStateV2.LOADED,
                SessionStateV2.RUNNING,
                SessionStateV2.PAUSED,
            }:
                raise _fail(
                    "session.state_invalid",
                    ("session", "state"),
                    self._state_provider().value,
                    "session state does not accept actions",
                    "load, run, or pause the session before submitting actions",
                )
            if not isinstance(batch, ActionBatchV2):
                raise TypeError("action submission requires ActionBatchV2")
            batch_fingerprint = action_batch_fingerprint_v2(batch)
            fingerprint = _canonical_hash(
                {
                    "operation_id": operation_id,
                    "batch_fingerprint": batch_fingerprint,
                    "authority_token": authority_token,
                    "expected_tick": expected_tick,
                }
            )
            prior_operation = self._operation_ledger.get(operation_id)
            if prior_operation is not None:
                if prior_operation[0] != fingerprint:
                    raise _fail(
                        "session.operation_conflict",
                        ("actions", "operation_id"),
                        operation_id,
                        "operation identity was reused with different evidence",
                        "reuse an operation identity only for an identical retry",
                    )
                return cast(ActionReceiptV2, prior_operation[1])
            prior_submission = self._submit_ledger.get(batch.idempotency_key)
            if prior_submission is not None:
                if prior_submission[0] != batch_fingerprint:
                    raise _fail(
                        "session.idempotency_conflict",
                        ("actions", "idempotency_key"),
                        batch.idempotency_key,
                        "idempotency identity was reused with different batch content",
                        "reuse it only for a byte-equivalent canonical batch",
                    )
                receipt = prior_submission[1]
                self._operation_ledger[operation_id] = (fingerprint, receipt)
                return receipt
            if (
                expected_tick != self._world.tick
                or batch.session_id != self.session_id
                or batch.based_on_tick > expected_tick
                or batch.valid_until_tick < expected_tick
            ):
                raise _fail(
                    "session.tick_window_invalid",
                    ("actions", "tick_window"),
                    (batch.based_on_tick, batch.valid_until_tick, expected_tick),
                    "batch session or tick window differs from the authoritative World clock",
                    "submit a current batch for this session and World tick",
                )
            children = cast(
                tuple[PersistentCommandV2 | DiscreteActionV2, ...],
                (*batch.persistent_commands, *batch.discrete_actions),
            )
            for item in children:
                claim = self._authority_claim(authority_token, item.entity_id)
                entity = self._world.get_optional(item.entity_id)
                if entity is None or entity.state.lifecycle not in {"active", "degraded"}:
                    raise _fail(
                        "session.entity_lifecycle_invalid",
                        ("actions", item.entity_id, "lifecycle"),
                        None if entity is None else entity.state.lifecycle,
                        "action target is not an active World entity",
                        "target an active or degraded controlled entity",
                    )
                if entity.faction_id != batch.faction_id or item.faction_id != entity.faction_id:
                    raise _fail(
                        "session.faction_ownership_invalid",
                        ("actions", item.entity_id, "faction_id"),
                        item.faction_id,
                        "action faction differs from World ownership",
                        "submit through the owning faction controller",
                    )
                if claim.action_schema_ref != "action-batch@2.0":
                    raise _fail(
                        "session.action_schema_invalid",
                        ("actions", item.entity_id, "schema"),
                        claim.action_schema_ref,
                        "controller action schema is not schema v2",
                        "bind the controller to action-batch@2.0",
                    )
                required = self._required_capability(item)
                if not self._capability_available(entity, item):
                    raise _fail(
                        "session.capability_missing",
                        ("actions", item.entity_id, "capability"),
                        required,
                        "entity lacks the exact capability required by the action",
                        "use an action supported by the resolved entity composition",
                    )
                try:
                    self._validate_payload(item)
                except (TypeError, ValueError) as error:
                    raise _fail(
                        "session.payload_invalid",
                        ("actions", item.entity_id, "payload"),
                        item.payload,
                        str(error),
                        "provide the canonical typed action payload",
                    ) from error
            child_records = tuple(
                (
                    item.command_id,
                    _canonical_hash(item.model_dump(mode="json")),
                )
                for item in batch.persistent_commands
            ) + tuple(
                (
                    item.action_id,
                    _canonical_hash(item.model_dump(mode="json")),
                )
                for item in batch.discrete_actions
            )
            conflict = next(
                (
                    child_id
                    for child_id, _fingerprint in child_records
                    if child_id in self._child_identity_ledger
                ),
                None,
            )
            if conflict is not None:
                raise _fail(
                    "session.child_id_conflict",
                    ("actions", "children", conflict),
                    conflict,
                    "child identity is already owned by another submitted batch",
                    "use a globally unique command or action identity",
                )
            receipt = ActionReceiptV2(
                session_id=self.session_id,
                batch_id=batch.batch_id,
                idempotency_key=batch.idempotency_key,
                operation_id=operation_id,
                fingerprint=batch_fingerprint,
                status="queued",
                submitted_tick=expected_tick,
                scheduled_tick=expected_tick,
                persistent_command_ids=tuple(
                    sorted(item.command_id for item in batch.persistent_commands)
                ),
                discrete_action_ids=tuple(
                    sorted(item.action_id for item in batch.discrete_actions)
                ),
            )
            self._pending[batch.batch_id] = (batch, expected_tick, receipt, authority_token)
            self._submit_ledger[batch.idempotency_key] = (batch_fingerprint, receipt)
            self._batch_ledger[batch.idempotency_key] = (batch, authority_token, receipt)
            self._operation_ledger[operation_id] = (fingerprint, receipt)
            self._statuses.update(
                {
                    item.command_id: PersistentCommandStatusV2.QUEUED.value
                    for item in batch.persistent_commands
                }
            )
            self._statuses.update(
                {
                    item.action_id: DiscreteActionStatusV2.QUEUED.value
                    for item in batch.discrete_actions
                }
            )
            self._child_ledger.update(
                {
                    item.command_id: ActionChildReceiptV2(
                        child_id=item.command_id,
                        kind="persistent",
                        status=PersistentCommandStatusV2.QUEUED.value,
                        tick=expected_tick,
                    )
                    for item in batch.persistent_commands
                }
            )
            self._child_ledger.update(
                {
                    item.action_id: ActionChildReceiptV2(
                        child_id=item.action_id,
                        kind="discrete",
                        status=DiscreteActionStatusV2.QUEUED.value,
                        tick=expected_tick,
                        request_id=(item.action_id if item.action_type == "fire_weapon" else None),
                    )
                    for item in batch.discrete_actions
                }
            )
            self._child_identity_ledger.update(
                {
                    child_id: (batch.batch_id, child_fingerprint)
                    for child_id, child_fingerprint in child_records
                }
            )
            return receipt

    def _controls(self, command: PersistentCommandV2, tick: int) -> EntityControlCommandV2:
        values = command.payload
        entity = self._world_view.get(command.entity_id)
        dynamics_ref = entity.definition.composition.dynamics_ref
        binding = next(
            (
                item
                for item in entity.definition.resource_bindings.get("dynamics", ())
                if item.exact_ref == dynamics_ref
            ),
            None,
        )
        if binding is None:
            raise _fail(
                "session.capability_missing",
                ("actions", command.entity_id, "dynamics"),
                dynamics_ref,
                "controlled entity has no exact dynamics binding",
                "rebuild the session from intact Resolved composition evidence",
            )
        if binding.model_ref == FIXED_MODEL_REF:
            controls: dict[str, float] = {}
        elif binding.model_ref == MMG_MODEL_REF:
            from openmdbench.domains.surface.controller_v2 import mmg_navigation_action_v2

            try:
                action = mmg_navigation_action_v2(
                    current_heading_deg=float(entity.state.heading_deg),
                    target_speed_mps=(
                        0.0 if command.command_type == "hold" else float(values["speed_mps"])
                    ),
                    target_heading_deg=(
                        float(entity.state.heading_deg)
                        if command.command_type == "hold"
                        else float(values["heading_deg"])
                    ),
                    parameters=binding.normalized_content,
                )
            except (KeyError, TypeError, ValueError) as error:
                raise _fail(
                    "session.payload_invalid",
                    ("actions", command.entity_id, "payload"),
                    command.payload,
                    "MMG navigation could not be translated to legal actuator controls",
                    "provide a finite navigation speed and heading within the controller contract",
                ) from error
            controls = {"nps": action.nps, "rudder_rad": action.rudder_rad}
        else:
            vertical = float(entity.state.position_m[2])
            if "altitude_m" in values:
                vertical = float(values["altitude_m"])
            elif "depth_m" in values:
                vertical = -abs(float(values["depth_m"]))
            controls = {
                "target_speed_mps": (
                    0.0 if command.command_type == "hold" else float(values["speed_mps"])
                ),
                "target_heading_deg": (
                    float(entity.state.heading_deg)
                    if command.command_type == "hold"
                    else float(values["heading_deg"]) % 360.0
                ),
                "target_vertical_m": vertical,
            }
        return EntityControlCommandV2(entity_id=command.entity_id, tick=tick, controls=controls)

    def _safe_hold(self, entity_id: str, tick: int) -> PersistentCommandV2:
        entity = self._world_view.get(entity_id)
        return PersistentCommandV2(
            schema_version="2.0",
            command_id=f"fallback.safe_hold.{entity_id}",
            command_type="hold",
            entity_id=entity_id,
            faction_id=entity.faction_id,
            based_on_tick=tick,
            valid_until_tick=tick,
            payload={},
        )

    @staticmethod
    def _safe_hold_control(
        entry: MotionEligibilityEntryV2, *, tick: int
    ) -> EntityControlCommandV2:
        """Materialize the World-projected fallback without reselecting entities."""

        return EntityControlCommandV2(
            entity_id=entry.entity_id,
            tick=tick,
            controls=dict(entry.fallback_controls),
        )

    def _revalidate_child(
        self,
        item: PersistentCommandV2 | DiscreteActionV2,
        *,
        faction_id: str,
        authority_token: str,
    ) -> None:
        claim = self._authority_claim(authority_token, item.entity_id)
        entity = self._world_view.get_optional(item.entity_id)
        if entity is None or entity.state.lifecycle not in {"active", "degraded"}:
            raise _fail(
                "session.entity_lifecycle_invalid",
                ("actions", item.entity_id, "lifecycle"),
                None if entity is None else entity.state.lifecycle,
                "action target is not active at its apply boundary",
                "discard or resubmit the action for an active controlled entity",
            )
        if entity.faction_id != faction_id or item.faction_id != entity.faction_id:
            raise _fail(
                "session.faction_ownership_invalid",
                ("actions", item.entity_id, "faction_id"),
                item.faction_id,
                "action faction changed before its apply boundary",
                "resubmit through the current owning controller",
            )
        if claim.action_schema_ref != "action-batch@2.0":
            raise _fail(
                "session.action_schema_invalid",
                ("actions", item.entity_id, "schema"),
                claim.action_schema_ref,
                "controller schema changed before apply",
                "use the active schema-v2 controller binding",
            )
        required = self._required_capability(item)
        if not self._capability_available(entity, item):
            raise _fail(
                "session.capability_missing",
                ("actions", item.entity_id, "capability"),
                required,
                "required capability is unavailable at apply",
                "wait for capability recovery or submit a supported action",
            )

    def _engagement_request(
        self,
        action: DiscreteActionV2,
        *,
        authority_token: str,
        tick: int,
    ) -> EngagementRequestV2:
        entity = self._world_view.get(action.entity_id)
        weapon_ref = str(action.payload["weapon_ref"])
        ammunition = tuple(
            binding
            for binding in entity.definition.resource_bindings.get("ammunition", ())
            if binding.normalized_content.get("weapon_ref") == weapon_ref
        )
        if len(ammunition) != 1:
            raise _fail(
                "session.payload_invalid",
                ("actions", action.action_id, "weapon_ref"),
                weapon_ref,
                "fire action does not resolve one exact ammunition binding",
                "use a weapon with one compiled ammunition binding",
            )
        payload = FireWeaponPayloadV2.model_validate(action.payload)
        if payload.contact_id is not None:
            contact = self._world.contact_store.resolve_owned_observation(
                evidence_id=payload.contact_id,
                owner_entity_id=action.entity_id,
                current_tick=tick,
            )
            if contact is None:
                raise _fail(
                    "session.contact_invalid",
                    ("actions", action.action_id, "contact_id"),
                    payload.contact_id,
                    "opaque contact is not a current observation owned by the firing entity",
                    "fire only on a fresh contact published for the controlled weapon entity",
                )
            target_id = contact.target_entity_id
        else:
            target_id = str(payload.target_id)
            contact = self._world.contact_store.resolve(
                evidence_id=None,
                owner_entity_id=action.entity_id,
                target_entity_id=target_id,
                current_tick=tick,
            )
        contact_id = (
            contact.evidence_id
            if contact is not None
            else f"contact.unavailable.{action.entity_id}.{target_id}"
        )
        return EngagementRequestV2(
            schema_version="2.0",
            request_id=action.action_id,
            tick=tick,
            attacker_id=action.entity_id,
            target_id=target_id,
            weapon_ref=weapon_ref,
            ammunition_ref=ammunition[0].exact_ref,
            shots=1,
            authority_token=authority_token,
            contact_evidence_id=contact_id,
        )

    def _execution_queue_fingerprint(self) -> str:
        """Hash only the state that can alter the next tick's execution.

        ``_statuses`` and ``_child_ledger`` are append-only audit/query
        evidence.  Including their full history in every tick's operation
        fingerprint makes the scheduling path grow with elapsed simulation
        time, while it neither changes command activation nor exactly-once
        discrete-action semantics.  They remain in the durable Session
        checkpoint evidence.
        """

        return _canonical_hash(
            {
                "schema_version": "execution-queue@2.0",
                "pending": tuple(
                    {
                        "batch_fingerprint": action_batch_fingerprint_v2(batch),
                        "scheduled_tick": scheduled,
                        "authority_token": authority_token,
                    }
                    for _batch_id, (batch, scheduled, _receipt, authority_token) in sorted(
                        self._pending.items()
                    )
                ),
                "persistent": tuple(
                    item.model_dump(mode="json") for item in self.persistent_commands
                ),
                "consumed_discrete": self.consumed_discrete_action_ids,
            }
        )

    def apply_tick(
        self,
        *,
        expected_tick: int,
        world_tick_input: WorldTickInputV2,
        operation_id: str,
    ) -> ActionApplyReceiptV2:
        with self._lock:
            if not isinstance(world_tick_input, WorldTickInputV2):
                raise TypeError("session tick boundary requires WorldTickInputV2")
            request_fingerprint = _canonical_hash(
                {
                    "operation_id": operation_id,
                    "expected_tick": expected_tick,
                    "dt_seconds": self._physics_dt_seconds,
                }
            )
            prior = self._operation_ledger.get(operation_id)
            if prior is not None:
                if (
                    not isinstance(prior[1], ActionApplyReceiptV2)
                    or prior[1].request_fingerprint != request_fingerprint
                ):
                    raise _fail(
                        "session.operation_conflict",
                        ("actions", "operation_id"),
                        operation_id,
                        "tick operation identity conflicts with prior evidence",
                        "retry with the identical tick input",
                    )
                return prior[1]
            queue_fingerprint = self._execution_queue_fingerprint()
            fingerprint = _canonical_hash(
                {
                    "request_fingerprint": request_fingerprint,
                    "queue_fingerprint": queue_fingerprint,
                }
            )
            if self._state_provider() is not SessionStateV2.RUNNING:
                raise _fail(
                    "session.state_invalid",
                    ("session", "state"),
                    self._state_provider().value,
                    "only a running session may write a World tick",
                    "start or resume the session before stepping",
                )
            if expected_tick != self._world.tick:
                raise _fail(
                    "session.tick_conflict",
                    ("world", "tick"),
                    expected_tick,
                    "action tick differs from World CAS clock",
                    "retry against the latest World tick",
                )
            staged_active = dict(self._active_persistent)
            staged_consumed = set(self._consumed_discrete)
            staged_statuses = dict(self._statuses)
            staged_pending = dict(self._pending)
            staged_child_ledger = dict(self._child_ledger)
            activated: list[str] = []
            consumed: list[str] = []
            expired: list[str] = []
            fallback_ids: list[str] = []
            fallback_entities: set[str] = set()
            child_receipts: list[ActionChildReceiptV2] = []
            engagement_requests: list[EngagementRequestV2] = []
            message_intents: list[MessageIntentV2] = []
            eligibility = self._world_view.motion_eligibility_snapshot(
                expected_tick=expected_tick
            )
            active_entity_ids = frozenset(eligibility.active_entity_ids)
            motion_entity_ids = frozenset(eligibility.entity_ids)

            def cancel_persistent(command: PersistentCommandV2, *, error_code: str) -> None:
                staged_statuses[command.command_id] = PersistentCommandStatusV2.CANCELLED.value
                child_receipt = ActionChildReceiptV2(
                    child_id=command.command_id,
                    kind="persistent",
                    status=PersistentCommandStatusV2.CANCELLED.value,
                    tick=expected_tick,
                    error_code=error_code,
                )
                child_receipts.append(child_receipt)
                staged_child_ledger[command.command_id] = child_receipt

            def reject_discrete(
                action: DiscreteActionV2, *, error_code: str = "session.entity_lifecycle_invalid"
            ) -> None:
                staged_consumed.add(action.action_id)
                staged_statuses[action.action_id] = DiscreteActionStatusV2.REJECTED.value
                consumed.append(action.action_id)
                child_receipt = ActionChildReceiptV2(
                    child_id=action.action_id,
                    kind="discrete",
                    status=DiscreteActionStatusV2.REJECTED.value,
                    tick=expected_tick,
                    request_id=(action.action_id if action.action_type == "fire_weapon" else None),
                    error_code=error_code,
                )
                child_receipts.append(child_receipt)
                staged_child_ledger[action.action_id] = child_receipt

            for key, command in tuple(staged_active.items()):
                if expected_tick > command.valid_until_tick:
                    staged_active.pop(key)
                    staged_statuses[command.command_id] = PersistentCommandStatusV2.EXPIRED.value
                    prior_child = staged_child_ledger.get(command.command_id)
                    if prior_child is not None:
                        staged_child_ledger[command.command_id] = prior_child.model_copy(
                            update={
                                "status": PersistentCommandStatusV2.EXPIRED.value,
                                "tick": expected_tick,
                            }
                        )
                    expired.append(command.command_id)
                    fallback_entities.add(command.entity_id)
                elif command.entity_id not in active_entity_ids:
                    staged_active.pop(key)
                    cancel_persistent(command, error_code="session.entity_lifecycle_invalid")
                elif (
                    command.command_type in {"navigation", "patrol", "hold"}
                    and command.entity_id not in motion_entity_ids
                ):
                    staged_active.pop(key)
                    cancel_persistent(command, error_code="session.capability_missing")
            ready = tuple(
                sorted(
                    (
                        (batch_id, record)
                        for batch_id, record in staged_pending.items()
                        if record[1] <= expected_tick
                    ),
                    key=lambda item: item[0],
                )
            )
            for batch_id, (batch, _scheduled, _receipt, authority_token) in ready:
                for command in sorted(
                    batch.persistent_commands,
                    key=lambda item: (item.entity_id, item.command_type, item.command_id),
                ):
                    self._world.enqueue_controller_action_transport(
                        action=command,
                        action_kind="persistent",
                        authority_token=authority_token,
                        controller_id=self._world.authority_tokens[authority_token].controller_id,
                        tick=expected_tick,
                        dt_seconds=self._physics_dt_seconds,
                    )
                    staged_statuses[command.command_id] = PersistentCommandStatusV2.ACCEPTED.value
                    prior_child = staged_child_ledger.get(command.command_id)
                    if prior_child is not None:
                        staged_child_ledger[command.command_id] = prior_child.model_copy(
                            update={
                                "status": PersistentCommandStatusV2.ACCEPTED.value,
                                "tick": expected_tick,
                            }
                        )
                for action in sorted(batch.discrete_actions, key=lambda item: item.action_id):
                    self._world.enqueue_controller_action_transport(
                        action=action,
                        action_kind="discrete",
                        authority_token=authority_token,
                        controller_id=self._world.authority_tokens[authority_token].controller_id,
                        tick=expected_tick,
                        dt_seconds=self._physics_dt_seconds,
                    )
                    staged_statuses[action.action_id] = DiscreteActionStatusV2.ACCEPTED.value
                    prior_child = staged_child_ledger.get(action.action_id)
                    if prior_child is not None:
                        staged_child_ledger[action.action_id] = prior_child.model_copy(
                            update={
                                "status": DiscreteActionStatusV2.ACCEPTED.value,
                                "tick": expected_tick,
                            }
                        )
                staged_pending.pop(batch_id)

            delivered_records = self._world.claim_resolved_controller_actions(tick=expected_tick)
            for record in delivered_records:
                action_kind = record.get("action_kind")
                action_payload = record.get("action")
                transport_authority_token = record.get("authority_token")
                status = record.get("transport_status")
                if not isinstance(action_payload, Mapping) or not isinstance(
                    transport_authority_token, str
                ):
                    raise ValueError("controller command transport payload is invalid")
                if action_kind == "persistent":
                    command = PersistentCommandV2.model_validate(action_payload)
                    if status != "delivered":
                        cancel_persistent(command, error_code=f"communication.command_{status}")
                        continue
                    if command.entity_id not in active_entity_ids:
                        cancel_persistent(command, error_code="session.entity_lifecycle_invalid")
                        continue
                    self._revalidate_child(
                        command,
                        faction_id=command.faction_id,
                        authority_token=transport_authority_token,
                    )
                    if expected_tick > command.valid_until_tick:
                        staged_statuses[command.command_id] = (
                            PersistentCommandStatusV2.EXPIRED.value
                        )
                        expired.append(command.command_id)
                        continue
                    key = (command.entity_id, command.command_type)
                    previous = staged_active.get(key)
                    if previous is not None and previous.command_id != command.command_id:
                        staged_statuses[previous.command_id] = (
                            PersistentCommandStatusV2.REPLACED.value
                        )
                        previous_child = staged_child_ledger.get(previous.command_id)
                        if previous_child is not None:
                            staged_child_ledger[previous.command_id] = previous_child.model_copy(
                                update={
                                    "status": PersistentCommandStatusV2.REPLACED.value,
                                    "tick": expected_tick,
                                }
                            )
                    staged_active[key] = command
                    staged_statuses[command.command_id] = PersistentCommandStatusV2.ACTIVE.value
                    activated.append(command.command_id)
                    child_receipt = ActionChildReceiptV2(
                        child_id=command.command_id,
                        kind="persistent",
                        status=PersistentCommandStatusV2.ACTIVE.value,
                        tick=expected_tick,
                    )
                    child_receipts.append(child_receipt)
                    staged_child_ledger[command.command_id] = child_receipt
                elif action_kind == "discrete":
                    action = DiscreteActionV2.model_validate(action_payload)
                    if action.action_id in staged_consumed:
                        continue
                    if status != "delivered" or action.entity_id not in active_entity_ids:
                        reject_discrete(
                            action,
                            error_code=(
                                f"communication.command_{status}"
                                if status != "delivered"
                                else "session.entity_lifecycle_invalid"
                            ),
                        )
                        continue
                    self._revalidate_child(
                        action,
                        faction_id=action.faction_id,
                        authority_token=transport_authority_token,
                    )
                    if expected_tick > action.valid_until_tick:
                        staged_statuses[action.action_id] = DiscreteActionStatusV2.REJECTED.value
                        continue
                    staged_consumed.add(action.action_id)
                    staged_statuses[action.action_id] = DiscreteActionStatusV2.EXECUTED.value
                    consumed.append(action.action_id)
                    if action.action_type == "fire_weapon":
                        engagement_requests.append(
                            self._engagement_request(
                                # The token must be the one this exact delivered
                                # action travelled with.  ``authority_token`` here
                                # used to name the loop variable of the batch
                                # submission loop above, which by now holds the
                                # token of the *last* ready batch of the tick --
                                # so every engagement inherited one arbitrary
                                # grant and failed the ``authority`` stage with
                                # ``combat.authority_denied`` unless that batch
                                # happened to belong to the firing entity.
                                action,
                                authority_token=transport_authority_token,
                                tick=expected_tick,
                            )
                        )
                    elif action.action_type == "send_message":
                        payload = SendMessagePayloadV2.model_validate(action.payload)
                        message_intents.append(
                            MessageIntentV2(
                                message_id=action.action_id,
                                sender_entity_id=action.entity_id,
                                recipient_entity_id=payload.recipient_id,
                                recipient_controller_slots=payload.recipient_controller_slots,
                                broadcast_faction_id=payload.broadcast_faction_id,
                                tick=expected_tick,
                                payload=payload.message,
                            )
                        )
                    child_receipt = ActionChildReceiptV2(
                        child_id=action.action_id,
                        kind="discrete",
                        status=DiscreteActionStatusV2.EXECUTED.value,
                        tick=expected_tick,
                        request_id=(
                            action.action_id if action.action_type == "fire_weapon" else None
                        ),
                    )
                    child_receipts.append(child_receipt)
                    staged_child_ledger[action.action_id] = child_receipt
                else:
                    raise ValueError("controller command transport kind is invalid")
            active_by_entity = {
                command.entity_id: command
                for command in sorted(staged_active.values(), key=lambda item: item.command_id)
                if command.command_type in {"navigation", "patrol", "hold"}
            }
            generated_items: list[EntityControlCommandV2] = []
            for entry in eligibility.entries:
                effective_command = active_by_entity.get(entry.entity_id)
                if effective_command is None:
                    if entry.entity_id in fallback_entities:
                        fallback_command = self._safe_hold(entry.entity_id, expected_tick)
                        fallback_ids.append(fallback_command.command_id)
                        child_receipt = ActionChildReceiptV2(
                            child_id=fallback_command.command_id,
                            kind="fallback",
                            status=PersistentCommandStatusV2.ACTIVE.value,
                            tick=expected_tick,
                        )
                        child_receipts.append(child_receipt)
                        staged_statuses[fallback_command.command_id] = (
                            PersistentCommandStatusV2.ACTIVE.value
                        )
                        staged_child_ledger[fallback_command.command_id] = child_receipt
                    generated_items.append(self._safe_hold_control(entry, tick=expected_tick))
                else:
                    generated_items.append(self._controls(effective_command, expected_tick))
            generated = tuple(sorted(generated_items, key=lambda item: item.entity_id))
            merged_input = WorldTickInputV2(
                expected_tick=expected_tick,
                operation_id=operation_id,
                # The session owns every active-entity command. Caller
                # entity commands and timing are deliberately not forwarded.
                entity_commands=generated,
                engagement_requests=tuple(
                    sorted(engagement_requests, key=lambda item: item.request_id)
                ),
                message_intents=tuple(sorted(message_intents, key=lambda item: item.message_id)),
                dt_seconds=self._physics_dt_seconds,
            )
            world_receipt = self._world.advance_tick(merged_input)
            combat_by_request = {item.request_id: item for item in world_receipt.combat_receipts}
            normalized_children: list[ActionChildReceiptV2] = []
            for child in child_receipts:
                combat_receipt = (
                    None if child.request_id is None else combat_by_request.get(child.request_id)
                )
                if combat_receipt is None:
                    normalized = child
                else:
                    normalized = child.model_copy(
                        update={
                            "status": (
                                DiscreteActionStatusV2.EXECUTED.value
                                if combat_receipt.status == "executed"
                                else DiscreteActionStatusV2.REJECTED.value
                            ),
                            "error_code": combat_receipt.error_code,
                        }
                    )
                    staged_statuses[child.child_id] = normalized.status
                normalized_children.append(normalized)
                staged_child_ledger[normalized.child_id] = normalized
            child_receipts = normalized_children
            receipt_payload: dict[str, Any] = {
                "session_id": self.session_id,
                "operation_id": operation_id,
                "expected_tick": expected_tick,
                "request_fingerprint": request_fingerprint,
                "queue_fingerprint": queue_fingerprint,
                "tick": int(world_receipt.tick),
                "activated_command_ids": tuple(sorted(activated)),
                "consumed_discrete_action_ids": tuple(sorted(consumed)),
                "expired_command_ids": tuple(sorted(expired)),
                "fallback_command_ids": tuple(sorted(fallback_ids)),
                "child_receipts": tuple(sorted(child_receipts, key=lambda item: item.child_id)),
                "world_receipt": _plain(world_receipt),
            }
            receipt = ActionApplyReceiptV2(
                **(receipt_payload | {"world_receipt": world_receipt}),
                receipt_hash=_canonical_hash(receipt_payload),
            )
            self._active_persistent = staged_active
            self._consumed_discrete = staged_consumed
            self._statuses = staged_statuses
            self._pending = staged_pending
            self._child_ledger = staged_child_ledger
            self._operation_ledger[operation_id] = (fingerprint, receipt)
            return receipt

    def checkpoint_evidence(self) -> dict[str, Any]:
        return {
            "pending_batches": tuple(
                {
                    "batch": batch.model_dump(mode="json"),
                    "scheduled_tick": scheduled,
                    "receipt": receipt.model_dump(mode="json"),
                    "authority_token": authority_token,
                }
                for _batch_id, (batch, scheduled, receipt, authority_token) in sorted(
                    self._pending.items()
                )
            ),
            "batch_ledger": tuple(
                {
                    "batch": batch.model_dump(mode="json"),
                    "authority_token": authority_token,
                    "receipt": receipt.model_dump(mode="json"),
                }
                for _idempotency, (batch, authority_token, receipt) in sorted(
                    self._batch_ledger.items()
                )
            ),
            "persistent_commands": tuple(
                item.model_dump(mode="json") for item in self.persistent_commands
            ),
            "consumed_discrete_action_ids": self.consumed_discrete_action_ids,
            "action_statuses": tuple(
                {"id": key, "status": value} for key, value in sorted(self._statuses.items())
            ),
            "operation_ledger": self.operation_ledger,
            "child_ledger": tuple(item.model_dump(mode="json") for item in self.child_ledger),
        }

    def restore_evidence(self, checkpoint: SessionCheckpointV2) -> None:
        self._pending = {}
        for item in checkpoint.pending_batches:
            batch = ActionBatchV2.model_validate(item["batch"])
            pending_receipt = ActionReceiptV2.model_validate(item["receipt"])
            self._pending[batch.batch_id] = (
                batch,
                int(item["scheduled_tick"]),
                pending_receipt,
                str(item["authority_token"]),
            )
        self._active_persistent = {
            (command.entity_id, command.command_type): command
            for command in (
                PersistentCommandV2.model_validate(item) for item in checkpoint.persistent_commands
            )
        }
        self._consumed_discrete = set(checkpoint.consumed_discrete_action_ids)
        self._statuses = {
            str(item["id"]): str(item["status"]) for item in checkpoint.action_statuses
        }
        self._child_ledger = {
            receipt.child_id: receipt
            for receipt in (
                ActionChildReceiptV2.model_validate(item) for item in checkpoint.child_ledger
            )
        }
        self._operation_ledger = {}
        self._submit_ledger = {}
        self._batch_ledger = {}
        self._child_identity_ledger = {}
        for item in checkpoint.batch_ledger:
            batch = ActionBatchV2.model_validate(item["batch"])
            receipt = ActionReceiptV2.model_validate(item["receipt"])
            authority_token = str(item["authority_token"])
            self._batch_ledger[batch.idempotency_key] = (
                batch,
                authority_token,
                receipt,
            )
            self._submit_ledger[batch.idempotency_key] = (
                action_batch_fingerprint_v2(batch),
                receipt,
            )
            for child in (*batch.persistent_commands, *batch.discrete_actions):
                child_id = getattr(child, "command_id", getattr(child, "action_id", ""))
                child_fingerprint = _canonical_hash(child.model_dump(mode="json"))
                if child_id in self._child_identity_ledger:
                    raise ValueError("checkpoint reuses one child identity across batches")
                self._child_identity_ledger[child_id] = (
                    batch.batch_id,
                    child_fingerprint,
                )
        for item in checkpoint.operation_ledger:
            raw_receipt = item["receipt"]
            restored_receipt: Any
            if "batch_id" in raw_receipt:
                restored_receipt = ActionReceiptV2.model_validate(raw_receipt)
            else:
                restored_receipt = ActionApplyReceiptV2.model_validate(raw_receipt)
                world_record = self._world._world_tick_ledger.get(restored_receipt.operation_id)
                if world_record is not None:
                    restored_receipt = restored_receipt.model_copy(
                        update={"world_receipt": world_record[1]}
                    )
            self._operation_ledger[str(item["operation_id"])] = (
                str(item["fingerprint"]),
                restored_receipt,
            )


class ActionQueueViewV2:
    """Immutable public observation of one session-owned action queue."""

    def __init__(self, pipeline: ActionPipelineV2) -> None:
        self._pipeline = pipeline

    @property
    def persistent_commands(self) -> tuple[PersistentCommandV2, ...]:
        return self._pipeline.persistent_commands

    @property
    def consumed_discrete_action_ids(self) -> tuple[str, ...]:
        return self._pipeline.consumed_discrete_action_ids

    @property
    def operation_ledger(self) -> tuple[dict[str, Any], ...]:
        return cast(tuple[dict[str, Any], ...], _freeze(self._pipeline.operation_ledger))

    @property
    def child_ledger(self) -> tuple[ActionChildReceiptV2, ...]:
        return self._pipeline.child_ledger


class ActionStatusViewV2:
    """Immutable status index detached from the queue's mutation boundary."""

    def __init__(self, pipeline: ActionPipelineV2) -> None:
        self._pipeline = pipeline

    @property
    def statuses(self) -> Mapping[str, str]:
        return self._pipeline.status_snapshot


class SessionLifecycleV2:
    """Own one schema-v2 World and serialize every state-changing operation."""

    def __init__(
        self,
        *,
        session_id: str,
        seed: int,
        resolved: ResolvedScenarioV2,
        catalog_hash: str,
        model_registry_hash: str,
        world_factory: WorldFactoryV2,
        runner_mode: RunnerModeV2,
        physics_dt_seconds: float,
        decision_interval_ticks: int,
    ) -> None:
        self.session_id = session_id
        self.seed = seed
        self.resolved = resolved
        self.catalog_hash = catalog_hash
        self.model_registry_hash = model_registry_hash
        self.world_factory = world_factory
        self.runner_mode = runner_mode
        self.physics_dt_seconds = physics_dt_seconds
        self.decision_interval_ticks = decision_interval_ticks
        self._state = SessionStateV2.CREATED
        self._world: WorldStateV2 | None = None
        self._combat: CombatSystemV2 | None = None
        self._actions: ActionPipelineV2 | None = None
        self._lock = RLock()

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        seed: int,
        resolved: ResolvedScenarioV2,
        expected_resolved_hash: str,
        catalog_hash: str,
        model_registry_hash: str,
        world_factory: WorldFactoryV2,
        runner_mode: RunnerModeV2 | str,
        physics_dt_seconds: float,
        decision_interval_ticks: int,
    ) -> SessionLifecycleV2:
        if not isinstance(resolved, ResolvedScenarioV2):
            raise TypeError("session requires ResolvedScenarioV2")
        resolved.validate_integrity()
        registry_hash = getattr(
            getattr(world_factory, "_model_registry", None), "snapshot_hash", None
        )
        if (
            not isinstance(session_id, str)
            or not session_id
            or not isinstance(seed, int)
            or isinstance(seed, bool)
            or seed < 0
            or expected_resolved_hash != resolved.resolved_hash
            or catalog_hash != resolved.catalog_hash
            or model_registry_hash != resolved.model_registry_hash
            or registry_hash != model_registry_hash
            or isinstance(physics_dt_seconds, bool)
            or not isinstance(physics_dt_seconds, (int, float))
            or not math.isfinite(float(physics_dt_seconds))
            or float(physics_dt_seconds) <= 0.0
            or not isinstance(decision_interval_ticks, int)
            or isinstance(decision_interval_ticks, bool)
            or decision_interval_ticks <= 0
        ):
            raise _fail(
                "session.anchor_invalid",
                ("session", "anchors"),
                session_id,
                "session reproducibility, registry, or timing anchors are invalid",
                "provide exact Resolved, Registry, seed, and finite clock anchors",
            )
        return cls(
            session_id=session_id,
            seed=seed,
            resolved=resolved,
            catalog_hash=catalog_hash,
            model_registry_hash=model_registry_hash,
            world_factory=world_factory,
            runner_mode=RunnerModeV2(runner_mode),
            physics_dt_seconds=float(physics_dt_seconds),
            decision_interval_ticks=decision_interval_ticks,
        )

    @property
    def state(self) -> SessionStateV2:
        return self._state

    @property
    def world_view(self) -> SessionWorldViewV2:
        if self._world is None:
            raise _fail(
                "session.world_unavailable",
                ("session", "world"),
                self._state.value,
                "session has no initialized mutable World",
                "load a non-replay session first",
            )
        if self._actions is None:
            raise _fail(
                "session.world_unavailable",
                ("session", "world"),
                self._state.value,
                "session World view is not initialized",
                "load a non-replay session first",
            )
        return self._actions.world_view

    def _mutable_world(self) -> WorldStateV2:
        if self._world is None:
            raise _fail(
                "session.world_unavailable",
                ("session", "world"),
                self._state.value,
                "session has no initialized World authority",
                "load a non-replay session first",
            )
        return self._world

    def _require_actions(self) -> ActionPipelineV2:
        if self._actions is None:
            raise _fail(
                "session.actions_unavailable",
                ("session", "actions"),
                self._state.value,
                "action pipeline is not initialized",
                "load a mutable session first",
            )
        return self._actions

    @property
    def queue_view(self) -> ActionQueueViewV2:
        return ActionQueueViewV2(self._require_actions())

    @property
    def action_status_view(self) -> ActionStatusViewV2:
        return ActionStatusViewV2(self._require_actions())

    def _transition(self, target: SessionStateV2) -> None:
        if target.value not in SESSION_TRANSITIONS_V2[self._state.value]:
            raise _fail(
                "session.transition_invalid",
                ("session", "state"),
                (self._state.value, target.value),
                "session transition is not allowed",
                "follow the authoritative session transition table",
            )
        self._state = target

    def load(self) -> SessionLifecycleV2:
        with self._lock:
            if self._state is SessionStateV2.LOADED:
                return self
            if self.runner_mode is not RunnerModeV2.REPLAY:
                world = self.world_factory.build(
                    self.resolved, session_id=self.session_id, seed=self.seed
                )
                self._world = world
                self._bind_combat(world)
                self._actions = ActionPipelineV2(
                    session_id=self.session_id,
                    world=world,
                    state_provider=lambda: self._state,
                    physics_dt_seconds=self.physics_dt_seconds,
                )
            self._transition(SessionStateV2.LOADED)
            return self

    def _bind_combat(self, world: WorldStateV2) -> None:
        has_weapon = any(
            entity.definition.resource_bindings.get("weapons", ())
            for entity in world.entities_stable()
        )
        if not has_weapon:
            self._combat = None
            return
        combat = CombatSystemV2.from_world(
            resolved=self.resolved,
            catalog_snapshot=CombatCatalogSnapshotV2.from_resolved(self.resolved),
            model_registry=self.world_factory._model_registry,
            world=world,
            expected_resolved_hash=self.resolved.resolved_hash,
            expected_catalog_hash=self.catalog_hash,
            expected_registry_hash=self.model_registry_hash,
        )
        world.install_combat_system(combat)
        self._combat = combat

    def start(self) -> SessionLifecycleV2:
        with self._lock:
            self._transition(SessionStateV2.RUNNING)
            return self

    def pause(self) -> SessionLifecycleV2:
        with self._lock:
            self._transition(SessionStateV2.PAUSED)
            return self

    def resume(self) -> SessionLifecycleV2:
        return self.start()

    def stop(self) -> SessionLifecycleV2:
        with self._lock:
            self._transition(SessionStateV2.STOPPED)
            return self

    def submit_actions(
        self,
        *,
        batch: ActionBatchV2,
        authority_token: str,
        operation_id: str,
        expected_tick: int,
    ) -> ActionReceiptV2:
        with self._lock:
            return self._require_actions().submit(
                batch=batch,
                authority_token=authority_token,
                operation_id=operation_id,
                expected_tick=expected_tick,
            )

    def step(
        self,
        *,
        operation_id: str,
        expected_tick: int,
    ) -> ActionApplyReceiptV2:
        with self._lock:
            world = self._mutable_world()
            actions = self._require_actions()
            if not actions.owns_world_writer(world.advance_tick):
                raise _fail(
                    "session.world_unavailable",
                    ("session", "world", "writer"),
                    self.session_id,
                    "action pipeline is not bound to the session-owned World writer",
                    "reload or restore the session from intact anchors",
                )
            # Competition ticks are append-only in-memory evidence.  They do
            # not snapshot World/adapter state for rollback; an unexpected
            # failure ends this match instead of permitting a partially
            # advanced World to continue.  Durable checkpoints remain an
            # explicit operator-facing save/restore feature.
            try:
                return actions.apply_tick(
                    expected_tick=expected_tick,
                    world_tick_input=WorldTickInputV2(
                        expected_tick=expected_tick,
                        operation_id=f"{operation_id}:session-owned",
                        entity_commands=(),
                        dt_seconds=self.physics_dt_seconds,
                    ),
                    operation_id=operation_id,
                )
            except Exception:
                if self._state is SessionStateV2.RUNNING and (
                    world.failed_tick_operation_id == operation_id or world.tick != expected_tick
                ):
                    self._transition(SessionStateV2.STOPPED)
                raise

    def checkpoint(self) -> SessionCheckpointV2:
        with self._lock:
            world_checkpoint = self._mutable_world().checkpoint()
            evidence = self._require_actions().checkpoint_evidence()
            payload: dict[str, Any] = {
                "session_id": self.session_id,
                "session_state": self._state,
                "runner_mode": self.runner_mode,
                "seed": self.seed,
                "resolved_hash": self.resolved.resolved_hash,
                "catalog_hash": self.catalog_hash,
                "model_registry_hash": self.model_registry_hash,
                "physics_dt_seconds": self.physics_dt_seconds,
                "decision_interval_ticks": self.decision_interval_ticks,
                "world_checkpoint_hash": world_checkpoint.checkpoint_hash,
                "world_checkpoint": world_checkpoint.model_dump(mode="json"),
                **evidence,
                "rng_state_hash": _canonical_hash(
                    {"session_id": self.session_id, "seed": self.seed}
                ),
                "checkpoint_hash": "sha256:" + "0" * 64,
            }
            payload["checkpoint_hash"] = SessionCheckpointV2.compute_hash(payload)
            return SessionCheckpointV2.model_validate(payload)

    @classmethod
    def restore(
        cls,
        *,
        checkpoint: SessionCheckpointV2,
        expected_checkpoint_hash: str,
        resolved: ResolvedScenarioV2,
        expected_resolved_hash: str,
        model_registry: ModelRegistryV2,
        expected_model_registry_hash: str,
        world_factory: WorldFactoryV2,
    ) -> SessionLifecycleV2:
        checkpoint = SessionCheckpointV2.model_validate(checkpoint)
        resolved.validate_integrity()
        if (
            checkpoint.checkpoint_hash != expected_checkpoint_hash
            or resolved.resolved_hash != expected_resolved_hash
            or checkpoint.resolved_hash != resolved.resolved_hash
            or checkpoint.catalog_hash != resolved.catalog_hash
            or checkpoint.model_registry_hash != expected_model_registry_hash
            or model_registry.snapshot_hash != expected_model_registry_hash
            or getattr(world_factory, "_model_registry", None) is not model_registry
        ):
            raise _fail(
                "session.restore_anchor_invalid",
                ("checkpoint", "anchors"),
                checkpoint.session_id,
                "checkpoint differs from explicit Resolved or Registry anchors",
                "restore with the exact trusted session inputs",
            )
        session = cls(
            session_id=checkpoint.session_id,
            seed=checkpoint.seed,
            resolved=resolved,
            catalog_hash=checkpoint.catalog_hash,
            model_registry_hash=checkpoint.model_registry_hash,
            world_factory=world_factory,
            runner_mode=checkpoint.runner_mode,
            physics_dt_seconds=checkpoint.physics_dt_seconds,
            decision_interval_ticks=checkpoint.decision_interval_ticks,
        )
        world_checkpoint = WorldCheckpointV2.model_validate(_plain(checkpoint.world_checkpoint))
        world = world_factory.restore_checkpoint(
            world_checkpoint,
            resolved=resolved,
            model_registry=model_registry,
            expected_checkpoint_hash=checkpoint.world_checkpoint_hash,
            expected_session_id=checkpoint.session_id,
            expected_seed=checkpoint.seed,
        )
        session._world = world
        session._bind_combat(world)
        session._actions = ActionPipelineV2(
            session_id=session.session_id,
            world=world,
            state_provider=lambda: session._state,
            physics_dt_seconds=session.physics_dt_seconds,
        )
        session._actions.restore_evidence(checkpoint)
        session._state = checkpoint.session_state
        return session

    def close(self) -> SessionLifecycleV2:
        with self._lock:
            if self._state is SessionStateV2.CLOSED:
                return self
            if SessionStateV2.CLOSED.value not in SESSION_TRANSITIONS_V2[self._state.value]:
                raise _fail(
                    "session.transition_invalid",
                    ("session", "state"),
                    self._state.value,
                    "session cannot close directly from its current state",
                    "stop or pause before closing",
                )
            if self._world is not None:
                self._world.close()
            self._transition(SessionStateV2.CLOSED)
            return self


__all__ = [
    "ACTION_VALIDATION_ORDER_V2",
    "REPLAY_INITIALIZES_WORLD",
    "SESSION_TRANSITIONS_V2",
    "ActionApplyReceiptV2",
    "ActionChildReceiptV2",
    "ActionContractV2",
    "ActionPipelineV2",
    "ActionQueueViewV2",
    "ActionReceiptV2",
    "ActionStatusViewV2",
    "DiscreteActionStatusV2",
    "PersistentCommandStatusV2",
    "RunnerModeV2",
    "SessionCheckpointV2",
    "SessionErrorV2",
    "SessionFailureV2",
    "SessionLifecycleV2",
    "SessionStateV2",
    "SessionWorldViewV2",
    "action_batch_fingerprint_v2",
    "discrete_action_contract_v2",
    "persistent_action_contract_v2",
]

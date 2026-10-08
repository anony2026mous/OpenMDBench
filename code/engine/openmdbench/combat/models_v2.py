"""Immutable public DTOs for the generic v2 combat and damage pipeline."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self

from pydantic import Field, PrivateAttr, StrictInt, ValidationError, model_validator

from openmdbench.schemas.core_v2 import CoreModelV2
from openmdbench.schemas.domain_v2 import DamageIntentV2 as DomainDamageIntentV2

_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class CombatErrorV2(Exception):
    """Stable combat failure with typed stage and remediation evidence."""

    def __init__(
        self,
        *,
        code: str,
        stage: str,
        path: Sequence[str],
        value: object,
        reason: str,
        suggestion: str,
    ) -> None:
        self.code = code
        self.stage = stage
        self.path = tuple(path)
        self.value = value
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"{code} at {'/'.join(self.path)}: {reason}; suggestion: {suggestion}")


def combat_error(code: str, stage: str, value: object, reason: str) -> CombatErrorV2:
    return CombatErrorV2(
        code=code,
        stage=stage,
        path=("combat", stage),
        value=value,
        reason=reason,
        suggestion="repair the rejected evidence and retry without partial mutation",
    )


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class CombatModelV2(CoreModelV2):
    """Frozen JSON model with deterministic public round-trip helpers."""

    schema_version: Literal["2.0"] = "2.0"

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def to_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, encoded: str) -> Self:
        payload = json.loads(encoded)
        if not isinstance(payload, Mapping):
            raise ValueError("combat DTO JSON must contain an object")
        return cls.model_validate(payload)


class CombatModelEvidenceV2(CombatModelV2):
    model_ref: str = Field(min_length=1)
    registered_model_ref: str = Field(min_length=1)
    interface_version: str = Field(min_length=1)
    expected_interface_version: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=_SHA256_PATTERN)
    expected_artifact_hash: str = Field(pattern=_SHA256_PATTERN)
    trusted: bool


class EngagementRequestV2(CombatModelV2):
    _origin_fingerprint: str = PrivateAttr()

    request_id: str = Field(min_length=1, max_length=256)
    tick: StrictInt = Field(ge=0)
    attacker_id: str = Field(min_length=1, max_length=256)
    target_id: str = Field(min_length=1, max_length=256)
    weapon_ref: str = Field(min_length=1, max_length=256)
    ammunition_ref: str = Field(min_length=1, max_length=256)
    shots: StrictInt = Field(ge=0, le=10_000)
    authority_token: str = Field(min_length=1, max_length=256)
    contact_evidence_id: str = Field(min_length=1, max_length=256)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        object.__setattr__(
            self,
            "_origin_fingerprint",
            _canonical_hash(self.model_dump(mode="json")),
        )

    @property
    def origin_fingerprint(self) -> str:
        return self._origin_fingerprint


class ShotEvidenceV2(CombatModelV2):
    shot_index: StrictInt = Field(ge=0)
    seed: StrictInt = Field(ge=0)
    sample: float = Field(ge=0.0, lt=1.0)
    hit: bool
    effect_ref: str = Field(min_length=1)
    model_ref: str = Field(min_length=1)
    model_identity: str = Field(pattern=_SHA256_PATTERN)
    model_call_sequence: StrictInt = Field(ge=1)
    model_input_hash: str = Field(pattern=_SHA256_PATTERN)
    probability: float = Field(ge=0.0, le=1.0)
    evidence_hash: str = Field(pattern=_SHA256_PATTERN)


class WeaponExecutionV2(CombatModelV2):
    execution_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1)
    tick: StrictInt = Field(ge=0)
    attacker_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    weapon_ref: str = Field(min_length=1)
    ammunition_ref: str = Field(min_length=1)
    requested_shots: StrictInt = Field(ge=0)
    effect_ref: str | None = None
    shots: tuple[ShotEvidenceV2, ...] = ()
    launched_missile_ids: tuple[str, ...] = ()
    pending_impact_ids: tuple[str, ...] = ()
    launch_position_m: tuple[float, float, float] | None = None
    launch_velocity_mps: tuple[float, float, float] | None = None
    target_position_at_launch_m: tuple[float, float, float] | None = None
    target_velocity_at_launch_mps: tuple[float, float, float] | None = None

    @classmethod
    def from_request(cls, request: EngagementRequestV2, *, execution_id: str) -> WeaponExecutionV2:
        if not isinstance(request, EngagementRequestV2):
            raise TypeError("weapon execution requires EngagementRequestV2")
        return cls(
            execution_id=execution_id,
            request_id=request.request_id,
            tick=request.tick,
            attacker_id=request.attacker_id,
            target_id=request.target_id,
            weapon_ref=request.weapon_ref,
            ammunition_ref=request.ammunition_ref,
            requested_shots=request.shots,
        )


class PendingImpactV2(CombatModelV2):
    """One immutable, already-authorized delayed weapon outcome."""

    impact_id: str = Field(min_length=1, max_length=512)
    execution_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=256)
    launch_tick: StrictInt = Field(ge=0)
    scheduled_tick: StrictInt = Field(ge=1)
    source_entity_id: str = Field(min_length=1, max_length=256)
    target_entity_id: str = Field(min_length=1, max_length=256)
    weapon_ref: str = Field(min_length=1, max_length=256)
    ammunition_ref: str = Field(min_length=1, max_length=256)
    effect_ref: str = Field(min_length=1, max_length=256)
    damage_model_ref: str = Field(min_length=1, max_length=256)
    magnitude: float = Field(ge=0.0)
    shot: ShotEvidenceV2
    launch_position_m: tuple[float, float, float]
    target_position_at_launch_m: tuple[float, float, float]
    evidence_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if self.scheduled_tick <= self.launch_tick:
            raise ValueError("pending impact must resolve after its launch tick")
        return self


class PendingImpactReceiptV2(CombatModelV2):
    """Immutable evidence that a queued delayed impact was consumed exactly once."""

    impact_id: str = Field(min_length=1, max_length=512)
    execution_id: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=256)
    tick: StrictInt = Field(ge=0)
    source_entity_id: str = Field(min_length=1, max_length=256)
    target_entity_id: str = Field(min_length=1, max_length=256)
    status: Literal["hit", "miss", "target_unavailable"]
    effect_ref: str = Field(min_length=1, max_length=256)
    damage_model_ref: str = Field(min_length=1, max_length=256)
    impact_position_m: tuple[float, float, float] | None = None
    evidence_hash: str = Field(pattern=_SHA256_PATTERN)


class HitV2(CombatModelV2):
    hit_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    time_fraction: float = Field(ge=0.0, le=1.0)
    position_m: tuple[float, float, float]
    evidence_hash: str = Field(pattern=_SHA256_PATTERN)


class EffectApplicationV2(CombatModelV2):
    effect_id: str = Field(min_length=1)
    effect_ref: str = Field(min_length=1)
    hit_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    magnitude: float = Field(ge=0.0)


DamageIntentV2 = DomainDamageIntentV2


class EntityDamageStateV2(CombatModelV2):
    entity_id: str = Field(min_length=1)
    health: float = Field(ge=0.0, le=1.0)
    lifecycle: Literal["active", "degraded", "disabled", "destroyed"]
    components: dict[str, Literal["active", "degraded", "disabled", "destroyed"]] = Field(
        default_factory=dict
    )
    available_capabilities: tuple[str, ...] = ()


class DamageResolutionV2(CombatModelV2):
    entities: tuple[EntityDamageStateV2, ...]
    applied_intents: tuple[DamageIntentV2, ...]

    @classmethod
    def resolve(
        cls,
        intents: tuple[DamageIntentV2, ...],
        *,
        initial_health: float,
    ) -> DamageResolutionV2:
        from openmdbench.combat.damage_v2 import DamageSystemV2

        targets = {intent.target_entity_id for intent in intents}
        return DamageSystemV2().resolve(
            intents,
            initial_health={target_id: initial_health for target_id in targets},
        )


class CombatCheckpointV2(CombatModelV2):
    session_id: str = "session.combat"
    seed: StrictInt = 0
    resolved_hash: str = "sha256:" + "0" * 64
    tick: StrictInt = Field(default=0, ge=0)
    rng_state: tuple[str, ...]
    ammunition: dict[str, StrictInt]
    cooldowns: dict[str, StrictInt]
    lifecycle: Literal["active", "degraded", "disabled", "destroyed", "despawned"]
    request_ledger: dict[str, dict[str, Any]] = Field(default_factory=dict)
    weapon_profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    model_evidence: dict[str, Any] = Field(default_factory=dict)
    checkpoint_hash: str = "sha256:" + "0" * 64

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
            self.validate_integrity()
        except CombatErrorV2:
            raise
        except (TypeError, ValueError, ValidationError) as error:
            raise combat_error(
                "combat.checkpoint_integrity_invalid",
                "checkpoint",
                type(error).__name__,
                "combat checkpoint nested state is invalid",
            ) from error

    @staticmethod
    def compute_checkpoint_hash(checkpoint: CombatCheckpointV2 | Mapping[str, Any]) -> str:
        payload = (
            checkpoint.model_dump(mode="json")
            if isinstance(checkpoint, CombatCheckpointV2)
            else dict(checkpoint)
        )
        payload.pop("checkpoint_hash", None)
        payload.setdefault("schema_version", "2.0")
        return _canonical_hash(payload)

    @classmethod
    def create(cls, payload: Mapping[str, Any]) -> CombatCheckpointV2:
        value = dict(payload)
        value["checkpoint_hash"] = cls.compute_checkpoint_hash(value)
        return cls(**value)

    def validate_integrity(self) -> None:
        if self.checkpoint_hash != self.compute_checkpoint_hash(self):
            raise combat_error(
                "combat.checkpoint_integrity_invalid",
                "checkpoint",
                self.checkpoint_hash,
                "combat checkpoint canonical hash mismatch",
            )

    @model_validator(mode="after")
    def validate_runtime_state(self) -> Self:
        if any(value < 0 for value in self.ammunition.values()) or any(
            value < 0 for value in self.cooldowns.values()
        ):
            raise ValueError("combat checkpoint counters cannot be negative")
        if any(not value for value in self.rng_state):
            raise ValueError("combat checkpoint RNG evidence cannot be empty")
        return self


def require_finite(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


__all__ = [
    "CombatCheckpointV2",
    "CombatErrorV2",
    "CombatModelV2",
    "CombatModelEvidenceV2",
    "DamageIntentV2",
    "DamageResolutionV2",
    "EffectApplicationV2",
    "EngagementRequestV2",
    "EntityDamageStateV2",
    "HitV2",
    "ShotEvidenceV2",
    "WeaponExecutionV2",
]

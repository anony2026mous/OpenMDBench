"""Generic versioned domain contracts for platform schema v2.

The models define composition and authority evidence only; they do not execute
models or mutate runtime state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from openmdbench.schemas.core_v2 import CoreModelV2
from openmdbench.schemas.interface_v2 import CheckpointMetadataV2, StableErrorV2

SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
ENGINE_COMPATIBILITY_PATTERN = (
    r"^(?:(?:>=|>|<=|<|==)\d+\.\d+\.\d+)"
    r"(?:,(?:>=|>|<=|<|==)\d+\.\d+\.\d+)*$"
)


class _ResourceProfileV2(CoreModelV2):
    id: str = Field(min_length=1)
    version: str = Field(pattern=SEMVER_PATTERN)
    engine_compatibility: str = Field(pattern=ENGINE_COMPATIBILITY_PATTERN)


class PlatformProfileV2(_ResourceProfileV2):
    domain: str = Field(min_length=1)
    component_slots: tuple[str, ...] = ()
    allowed_dynamics: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_unique_composition(self) -> Self:
        if len(self.component_slots) != len(set(self.component_slots)):
            raise ValueError("duplicate component slot")
        if len(self.allowed_dynamics) != len(set(self.allowed_dynamics)):
            raise ValueError("duplicate allowed dynamics reference")
        return self


class DynamicsProfileV2(_ResourceProfileV2):
    model_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ComponentProfileV2(_ResourceProfileV2):
    capability: str = Field(min_length=1)
    slot_type: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class LoadoutProfileV2(_ResourceProfileV2):
    component_refs: tuple[str, ...] = ()
    ammunition: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_loadout(self) -> Self:
        if len(self.component_refs) != len(set(self.component_refs)):
            raise ValueError("duplicate loadout component reference")
        if any(count < 0 for count in self.ammunition.values()):
            raise ValueError("ammunition count cannot be negative")
        return self


class WeaponProfileV2(_ResourceProfileV2):
    target_domains: tuple[str, ...] = Field(min_length=1)
    minimum_range_m: float = Field(ge=0.0)
    maximum_range_m: float = Field(gt=0.0)
    hit_model_id: str = Field(min_length=1)
    effect_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.minimum_range_m > self.maximum_range_m:
            raise ValueError("minimum weapon range exceeds maximum range")
        if len(self.target_domains) != len(set(self.target_domains)):
            raise ValueError("duplicate target domain")
        return self


class EffectProfileV2(_ResourceProfileV2):
    damage_model_id: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class DamageIntentV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    intent_id: str = Field(min_length=1)
    tick: StrictInt = Field(ge=0)
    source_entity_id: str = Field(min_length=1)
    target_entity_id: str = Field(min_length=1)
    effect_ref: str = Field(min_length=1)
    damage_model_ref: str | None = Field(default=None, min_length=1)
    magnitude: float | None = Field(default=None, ge=0.0)
    evidence_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    source_kind: Literal["collision", "environment", "weapon"] | None = None
    component_id: str | None = Field(default=None, min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_damage_evidence(self) -> Self:
        evidence = (self.damage_model_ref, self.magnitude, self.evidence_hash, self.source_kind)
        if any(item is not None for item in evidence) and any(item is None for item in evidence):
            raise ValueError("damage execution evidence must be supplied as one complete set")
        return self

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
            raise ValueError("damage intent JSON must contain an object")
        return cls.model_validate(payload)


class LifecycleStateV2(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    DESTROYED = "destroyed"
    DESPAWNED = "despawned"


class DamageResultV2(CoreModelV2):
    target_entity_id: str = Field(min_length=1)
    tick: int = Field(ge=0)
    applied_intent_ids: tuple[str, ...] = Field(min_length=1)
    health_before: float = Field(ge=0.0, le=1.0)
    health_after: float = Field(ge=0.0, le=1.0)
    component_health: dict[str, float] = Field(default_factory=dict)
    lifecycle_before: LifecycleStateV2
    lifecycle_after: LifecycleStateV2

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if len(self.applied_intent_ids) != len(set(self.applied_intent_ids)):
            raise ValueError("duplicate applied damage intent id")
        if any(not 0.0 <= health <= 1.0 for health in self.component_health.values()):
            raise ValueError("component health must be within [0, 1]")
        return self


class BoundaryPolicyV2(CoreModelV2):
    id: str = Field(min_length=1)
    violation_actions: tuple[
        Literal[
            "reject_command",
            "constrain_motion",
            "stop",
            "reflect",
            "collision_effect",
            "deactivate",
            "mission_event",
            "emit_event",
            "apply_effect",
        ],
        ...,
    ] = Field(min_length=1)
    effect_ref: str | None = None
    tolerance_m: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_actions(self) -> Self:
        if len(self.violation_actions) != len(set(self.violation_actions)):
            raise ValueError("duplicate boundary violation action")
        if "apply_effect" in self.violation_actions and self.effect_ref is None:
            raise ValueError("apply_effect boundary action requires effect_ref")
        return self


class CheckpointEnvelopeV2(CoreModelV2):
    metadata: CheckpointMetadataV2
    world_state: dict[str, Any]
    command_state: dict[str, Any]
    system_state: dict[str, Any]
    rng_state: dict[str, Any]


class SchemaMigrationV2(BaseModel):
    """Data-only schema-version gate; actual transformations require a later ADR."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    current_version: str = Field(min_length=1)
    supported_sources: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_versions(self) -> Self:
        if len(self.supported_sources) != len(set(self.supported_sources)):
            raise ValueError("duplicate supported schema version")
        if self.current_version != "2.0" or self.supported_sources != ("2.0",):
            raise ValueError("only 2.0 identity migration is supported; 1.0 is unsupported")
        return self

    def migrate(self, payload: dict[str, Any]) -> dict[str, Any] | StableErrorV2:
        source = payload.get("schema_version")
        if not isinstance(source, str) or source not in self.supported_sources:
            return StableErrorV2(
                schema_version="2.0",
                code="schema.version_unsupported",
                message=f"schema version {source!r} is not supported",
                path=("schema_version",),
                value=source,
                suggestion=f"use one of: {', '.join(self.supported_sources)}",
            )
        return dict(payload)


__all__ = [
    "BoundaryPolicyV2",
    "CheckpointEnvelopeV2",
    "ComponentProfileV2",
    "DamageIntentV2",
    "DamageResultV2",
    "DynamicsProfileV2",
    "EffectProfileV2",
    "LifecycleStateV2",
    "LoadoutProfileV2",
    "PlatformProfileV2",
    "SchemaMigrationV2",
    "WeaponProfileV2",
]

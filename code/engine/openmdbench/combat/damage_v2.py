"""Stable simultaneous generic damage aggregation for RF-06."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from openmdbench.combat.models_v2 import (
    CombatErrorV2,
    CombatModelV2,
    DamageIntentV2,
    DamageResolutionV2,
    EntityDamageStateV2,
    combat_error,
)
from openmdbench.schemas.domain_v2 import DamageIntentV2 as DomainDamageIntentV2
from openmdbench.schemas.domain_v2 import DamageResultV2

_SOURCE_ORDER = {"collision": 0, "environment": 1, "weapon": 2}


@dataclass(slots=True)
class DamageRuntimeEntityV2:
    entity_id: str
    health: float
    lifecycle: str
    component_health: dict[str, float]
    component_capabilities: dict[str, tuple[str, ...]]
    component_damage_profiles: dict[str, str]
    capabilities: tuple[str, ...]
    controller_slot: str | None = None

    def clone(self) -> DamageRuntimeEntityV2:
        return DamageRuntimeEntityV2(
            entity_id=self.entity_id,
            health=self.health,
            lifecycle=self.lifecycle,
            component_health=dict(self.component_health),
            component_capabilities=dict(self.component_capabilities),
            component_damage_profiles=dict(self.component_damage_profiles),
            capabilities=tuple(self.capabilities),
            controller_slot=self.controller_slot,
        )


@dataclass(frozen=True, slots=True)
class ControllerDamageOwnershipV2:
    slot_id: str
    entity_id: str
    available_capabilities: tuple[str, ...]


class DamageStateV2:
    def __init__(self, entities: Mapping[str, DamageRuntimeEntityV2]) -> None:
        self.entities = dict(sorted(entities.items()))
        self.controller_ownership: dict[str, ControllerDamageOwnershipV2] = {}
        self._rebuild_controller_ownership()

    @classmethod
    def with_components(
        cls,
        *,
        entity_id: str,
        components: Mapping[str, Sequence[str]],
        component_health: Mapping[str, float] | None = None,
        component_damage_profiles: Mapping[str, str] | None = None,
        controller_slot: str | None = None,
    ) -> DamageStateV2:
        component_capabilities = {
            key: tuple(sorted(set(value))) for key, value in components.items()
        }
        capabilities = tuple(
            sorted(
                {capability for values in component_capabilities.values() for capability in values}
            )
        )
        profiles = {
            key: (
                component_damage_profiles[key]
                if component_damage_profiles is not None and key in component_damage_profiles
                else "damage.linear@2.0.0"
            )
            for key in component_capabilities
        }
        if any(not value or "@" not in value for value in profiles.values()):
            raise ValueError("component damage profiles require exact references")
        return cls(
            {
                entity_id: DamageRuntimeEntityV2(
                    entity_id=entity_id,
                    health=1.0,
                    lifecycle="active",
                    component_health={
                        key: (
                            float(component_health[key])
                            if component_health is not None and key in component_health
                            else 1.0
                        )
                        for key in component_capabilities
                    },
                    component_capabilities=component_capabilities,
                    component_damage_profiles=profiles,
                    capabilities=capabilities,
                    controller_slot=controller_slot,
                )
            }
        )

    def entity(self, entity_id: str) -> DamageRuntimeEntityV2:
        return self.entities[entity_id]

    def snapshot(self) -> tuple[object, ...]:
        return tuple(
            (
                key,
                entity.health,
                entity.lifecycle,
                tuple(sorted(entity.component_health.items())),
                tuple(sorted(entity.component_damage_profiles.items())),
                entity.capabilities,
                entity.controller_slot,
            )
            for key, entity in sorted(self.entities.items())
        )

    def clone(self) -> DamageStateV2:
        return DamageStateV2({key: value.clone() for key, value in self.entities.items()})

    def replace_from(self, staged: DamageStateV2) -> None:
        self.entities = {key: value.clone() for key, value in staged.entities.items()}
        self._rebuild_controller_ownership()

    def _rebuild_controller_ownership(self) -> None:
        self.controller_ownership = {
            entity.controller_slot: ControllerDamageOwnershipV2(
                slot_id=entity.controller_slot,
                entity_id=entity.entity_id,
                available_capabilities=entity.capabilities,
            )
            for entity in self.entities.values()
            if entity.controller_slot is not None
        }


class DamageApplyReceiptV2(CombatModelV2):
    tick: int
    applied_intents: tuple[DamageIntentV2, ...]
    destroyed_entities: tuple[EntityDamageStateV2, ...]
    results: tuple[DamageResultV2, ...] = ()


class FaultInjectingDamageModelV2:
    def __init__(self, *, fail_on_call: int) -> None:
        self.fail_on_call = fail_on_call
        self.calls = 0

    def magnitude(self, intent: DamageIntentV2) -> float:
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("injected damage model failure")
        if intent.magnitude is None:
            raise ValueError("damage magnitude is required")
        return intent.magnitude


class DamageSystemV2:
    """Aggregate every target's same-tick intents before applying any result."""

    @staticmethod
    def apply_health(
        *,
        entity_id: str,
        health: float,
        components: Sequence[str],
        capabilities: Sequence[str],
    ) -> EntityDamageStateV2:
        if (
            isinstance(health, bool)
            or not isinstance(health, (int, float))
            or not math.isfinite(float(health))
            or not 0.0 <= float(health) <= 1.0
        ):
            raise ValueError("health must be finite within [0, 1]")
        normalized_health = float(health)
        lifecycle: Literal["active", "degraded", "disabled", "destroyed"]
        if normalized_health <= 0.0:
            lifecycle = "destroyed"
        elif normalized_health <= 0.5:
            lifecycle = "disabled"
        elif normalized_health < 1.0:
            lifecycle = "degraded"
        else:
            lifecycle = "active"
        component_state = lifecycle
        normalized_components = tuple(sorted(set(components)))
        normalized_capabilities = tuple(sorted(set(capabilities)))
        return EntityDamageStateV2(
            entity_id=entity_id,
            health=normalized_health,
            lifecycle=lifecycle,
            components={item: component_state for item in normalized_components},
            available_capabilities=(
                normalized_capabilities if lifecycle in {"active", "degraded"} else ()
            ),
        )

    def __init__(
        self,
        *,
        known_entity_ids: Sequence[str] | None = None,
        model: FaultInjectingDamageModelV2 | None = None,
        known_damage_model_refs: Sequence[str] = (
            "damage.arbitrary@2.3.1",
            "damage.builtin-linear@2.0.0",
        ),
        chain: Any | None = None,
    ) -> None:
        self.known_entity_ids = None if known_entity_ids is None else frozenset(known_entity_ids)
        self.model = model
        self.chain = chain
        chain_ref = None if chain is None else getattr(chain, "damage_model_ref", None)
        self.known_damage_model_refs = frozenset((*known_damage_model_refs, chain_ref)) - {None}

    def intent_from_hit(self, hit: Any) -> DomainDamageIntentV2:
        if self.chain is None:
            raise combat_error(
                "damage.effect_chain_missing",
                "damage",
                None,
                "hit conversion requires an exact resolved effect-to-damage chain",
            )
        try:
            payload = [
                hit.hit_id,
                hit.target_id,
                self.chain.effect_ref,
                self.chain.damage_model_ref,
                self.chain.resolved_hash,
            ]
            return DamageIntentV2(
                intent_id=f"damage:{hit.hit_id}",
                tick=0,
                source_entity_id=hit.execution_id,
                target_entity_id=hit.target_id,
                effect_ref=self.chain.effect_ref,
                damage_model_ref=self.chain.damage_model_ref,
                magnitude=0.1,
                evidence_hash=(
                    "sha256:"
                    + hashlib.sha256(
                        json.dumps(payload, separators=(",", ":")).encode()
                    ).hexdigest()
                ),
                source_kind="weapon",
                parameters={"hit_evidence_hash": hit.evidence_hash},
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise combat_error(
                "damage.hit_invalid",
                "damage",
                type(error).__name__,
                "hit evidence cannot be converted through the resolved effect chain",
            ) from error

    def _coerce_intent(self, intent: DomainDamageIntentV2) -> DamageIntentV2:
        if not isinstance(intent, DomainDamageIntentV2):
            raise TypeError("damage intents must contain canonical domain DamageIntentV2")
        payload = intent.model_dump(mode="json")
        if self.chain is not None:
            if intent.effect_ref != self.chain.effect_ref or (
                intent.damage_model_ref is not None
                and intent.damage_model_ref != self.chain.damage_model_ref
            ):
                raise ValueError("damage intent effect or model differs from the resolved chain")
            payload["damage_model_ref"] = self.chain.damage_model_ref
        return DamageIntentV2.model_validate(payload)

    def _validate_intents(
        self, intents: Sequence[DomainDamageIntentV2]
    ) -> tuple[DamageIntentV2, ...]:
        try:
            if not isinstance(intents, Sequence) or isinstance(intents, (str, bytes, bytearray)):
                raise TypeError("damage intents must be a typed sequence")
            typed = tuple(self._coerce_intent(item) for item in intents)
            if any(item.magnitude is None or item.source_kind is None for item in typed):
                raise TypeError("damage intents require magnitude and source kind")
            ordered = tuple(
                sorted(
                    typed,
                    key=lambda item: (
                        item.target_entity_id,
                        item.tick,
                        _SOURCE_ORDER[item.source_kind or ""],
                        item.intent_id,
                    ),
                )
            )
            if any(not isinstance(item, DamageIntentV2) for item in ordered):
                raise TypeError("damage intents must contain DamageIntentV2")
            if len({item.intent_id for item in ordered}) != len(ordered):
                raise combat_error(
                    "damage.intent_duplicate",
                    "damage",
                    "duplicate",
                    "damage intent identities must be unique",
                )
            for intent in ordered:
                if (
                    intent.magnitude is None
                    or not math.isfinite(intent.magnitude)
                    or intent.magnitude < 0.0
                    or intent.evidence_hash is None
                    or intent.damage_model_ref is None
                    or intent.source_kind is None
                ):
                    raise combat_error(
                        "damage.intent_invalid",
                        "damage",
                        intent.intent_id,
                        "damage intent requires finite complete execution evidence",
                    )
                if (
                    self.known_entity_ids is not None
                    and intent.target_entity_id not in self.known_entity_ids
                ):
                    raise combat_error(
                        "damage.target_unknown",
                        "damage",
                        intent.target_entity_id,
                        "damage target is not present in the authoritative state",
                    )
                if intent.damage_model_ref not in self.known_damage_model_refs:
                    raise combat_error(
                        "damage.model_unknown",
                        "damage",
                        intent.damage_model_ref,
                        "damage model is absent from trusted exact evidence",
                    )
            return ordered
        except CombatErrorV2:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise combat_error(
                "damage.intent_invalid",
                "damage",
                type(error).__name__,
                "damage intent batch is not strict and canonical",
            ) from error

    def resolve(
        self,
        intents: Sequence[DamageIntentV2],
        *,
        initial_health: Mapping[str, float],
    ) -> DamageResolutionV2:
        ordered = self._validate_intents(intents)
        grouped: dict[str, list[DamageIntentV2]] = defaultdict(list)
        for intent in ordered:
            grouped[intent.target_entity_id].append(intent)
        states: list[EntityDamageStateV2] = []
        for target_id in sorted(grouped):
            if target_id not in initial_health:
                raise ValueError("initial health is missing for a damage target")
            before = initial_health[target_id]
            if (
                isinstance(before, bool)
                or not isinstance(before, (int, float))
                or not math.isfinite(float(before))
                or not 0.0 <= float(before) <= 1.0
            ):
                raise ValueError("initial health must be finite within [0, 1]")
            damage = math.fsum(
                intent.magnitude if intent.magnitude is not None else 0.0
                for intent in grouped[target_id]
            )
            states.append(
                self.apply_health(
                    entity_id=target_id,
                    health=max(0.0, float(before) - damage),
                    components=(),
                    capabilities=(),
                )
            )
        return DamageResolutionV2(entities=tuple(states), applied_intents=ordered)

    def apply_atomic(
        self,
        intents: Sequence[DamageIntentV2],
        *,
        state: DamageStateV2,
        expected_tick: int,
    ) -> DamageApplyReceiptV2:
        if not isinstance(state, DamageStateV2):
            raise TypeError("atomic damage application requires DamageStateV2")
        ordered = self._validate_intents(intents)
        if any(intent.tick != expected_tick for intent in ordered):
            raise combat_error(
                "damage.tick_conflict",
                "damage",
                expected_tick,
                "damage intent tick differs from the authoritative tick",
            )
        staged = state.clone()
        destroyed: list[EntityDamageStateV2] = []
        try:
            for intent in ordered:
                entity = staged.entities.get(intent.target_entity_id)
                if entity is None:
                    raise combat_error(
                        "damage.target_unknown",
                        "damage",
                        intent.target_entity_id,
                        "damage target is absent from the tick-start snapshot",
                    )
                if intent.magnitude is None:
                    raise ValueError("damage magnitude is required")
                magnitude = intent.magnitude if self.model is None else self.model.magnitude(intent)
                if intent.component_id is not None:
                    if intent.component_id not in entity.component_health:
                        raise combat_error(
                            "damage.component_unknown",
                            "damage",
                            intent.component_id,
                            "target component is absent from authoritative state",
                        )
                    entity.component_health[intent.component_id] = max(
                        0.0, entity.component_health[intent.component_id] - magnitude
                    )
                    if entity.component_health[intent.component_id] <= 0.0:
                        removed = set(entity.component_capabilities.get(intent.component_id, ()))
                        entity.capabilities = tuple(
                            item for item in entity.capabilities if item not in removed
                        )
                else:
                    entity.health = max(0.0, entity.health - magnitude)
                    if entity.health <= 0.0:
                        entity.lifecycle = "destroyed"
                        entity.capabilities = ()
                    elif entity.health <= 0.5:
                        entity.lifecycle = "disabled"
                        entity.capabilities = ()
                    elif entity.health < 1.0:
                        entity.lifecycle = "degraded"
            staged._rebuild_controller_ownership()
            destroyed = [
                EntityDamageStateV2(
                    entity_id=entity.entity_id,
                    health=entity.health,
                    lifecycle="destroyed",
                    components={key: "destroyed" for key in entity.component_health},
                    available_capabilities=(),
                )
                for entity in staged.entities.values()
                if entity.lifecycle == "destroyed"
            ]
        except CombatErrorV2:
            raise
        except Exception as error:
            raise combat_error(
                "damage.model_failure",
                "damage",
                type(error).__name__,
                "damage model failed before atomic commit",
            ) from error
        state.replace_from(staged)
        return DamageApplyReceiptV2(
            tick=expected_tick,
            applied_intents=ordered,
            destroyed_entities=tuple(sorted(destroyed, key=lambda item: item.entity_id)),
        )


__all__ = [
    "ControllerDamageOwnershipV2",
    "DamageApplyReceiptV2",
    "DamageRuntimeEntityV2",
    "DamageStateV2",
    "DamageSystemV2",
    "FaultInjectingDamageModelV2",
]

"""Trusted combat composition and authoritative damage-session integration."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel, Field, StrictInt

from openmdbench.combat.models_v2 import (
    CombatErrorV2,
    CombatModelV2,
    DamageIntentV2,
    PendingImpactReceiptV2,
    PendingImpactV2,
    combat_error,
)

_HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
_REF_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*@[0-9]+\.[0-9]+\.[0-9]+$")


def _canonical_hash(value: object) -> str:
    def plain(item: object) -> object:
        if isinstance(item, BaseModel):
            return item.model_dump(mode="json")
        if isinstance(item, Mapping):
            return {str(key): plain(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(child) for child in item]
        return item

    encoded = json.dumps(
        plain(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _combat_scope_entities(resolved: object) -> tuple[Any, ...]:
    """Every entity that can exist in the World, including spawn blueprints.

    Combat resolution collects every weapon, ammunition, effect, and damage
    binding reachable from an entity.  Entities introduced by
    ``event_type: spawn`` are compiled as immutable ``ResolvedEntityV2``
    blueprints inside the event payload -- the same objects the world factory
    later instantiates, and the same ones ``component_damage_profiles`` already
    includes.  Omitting them here makes a weapon carried *only* by a spawned
    force (the usual intruder composition) absent from the profile map, so
    every engagement against it is denied with ``combat.weapon_unknown`` -- and
    because that failure aborts the whole tick's combat transaction, it also
    vetoes the other side's already-legal shots in the same tick.
    """

    entities = list(getattr(resolved, "entities", ()) or ())
    seen = {str(getattr(entity, "id", "")) for entity in entities}
    for event in getattr(resolved, "events", ()) or ():
        if str(getattr(event, "event_type", "")) != "spawn":
            continue
        blueprint = getattr(getattr(event, "payload", None), "entity", None)
        if blueprint is None:
            continue
        entity_id = str(getattr(blueprint, "id", ""))
        if entity_id and entity_id in seen:
            continue
        seen.add(entity_id)
        entities.append(blueprint)
    return tuple(entities)


class CombatCatalogSnapshotV2(CombatModelV2):
    """The catalog portion actually embedded in a compiled scenario."""

    resolved_hash: str = Field(pattern=_HASH_PATTERN)
    catalog_hash: str = Field(pattern=_HASH_PATTERN)
    resource_evidence: tuple[tuple[str, str], ...]

    @classmethod
    def from_resolved(cls, resolved: Any) -> CombatCatalogSnapshotV2:
        try:
            resolved.validate_integrity()
            resources: dict[str, str] = {}
            for entity in _combat_scope_entities(resolved):
                for bindings in entity.resource_bindings.values():
                    for binding in bindings:
                        previous = resources.setdefault(binding.exact_ref, binding.content_hash)
                        if previous != binding.content_hash:
                            raise ValueError("resolved resource has conflicting hashes")
            return cls(
                resolved_hash=resolved.resolved_hash,
                catalog_hash=resolved.catalog_hash,
                resource_evidence=tuple(sorted(resources.items())),
            )
        except CombatErrorV2:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise combat_error(
                "combat.catalog_snapshot_invalid",
                "model_trust",
                type(error).__name__,
                "combat catalog snapshot requires an intact compiled resource closure",
            ) from error


class CombatSystemV2:
    """Combat authority bound to one validated Resolved/Catalog/Registry/World graph."""

    resolved_hash: str
    catalog_hash: str
    model_registry_hash: str
    catalog_snapshot: CombatCatalogSnapshotV2
    model_registry: Any
    world: Any
    _weapon_profiles: Mapping[str, Mapping[str, Any]]
    _effect_damage_chains: Mapping[str, EffectDamageChainV2]
    _hit_model: HitModelV2
    resolved: Any
    world_factory: Any
    _transaction_failure_stage: str | None
    _transaction_failure_adapter_index: int | None
    _capability_resolver: Callable[[str, str, float, int, str], float] | None

    def __init__(self, *, _authority: object | None = None) -> None:
        if _authority is None:
            raise combat_error(
                "combat.authority_missing",
                "model_trust",
                None,
                "combat cannot be constructed without compiled and runtime trust anchors",
            )

    @classmethod
    def from_world(
        cls,
        *,
        resolved: Any,
        catalog_snapshot: CombatCatalogSnapshotV2,
        model_registry: Any,
        world: Any,
        expected_resolved_hash: str,
        expected_catalog_hash: str,
        expected_registry_hash: str,
    ) -> CombatSystemV2:
        try:
            resolved.validate_integrity()
            actual = (
                resolved.resolved_hash,
                resolved.catalog_hash,
                resolved.model_registry_hash,
            )
            expected = (
                expected_resolved_hash,
                expected_catalog_hash,
                expected_registry_hash,
            )
            if actual != expected or (
                catalog_snapshot.resolved_hash != actual[0]
                or catalog_snapshot.catalog_hash != actual[1]
                or model_registry.content_hash != actual[2]
                or world.resolved_hash != actual[0]
            ):
                raise combat_error(
                    "combat.resolved_anchor_mismatch",
                    "model_trust",
                    expected,
                    "external combat anchors differ from validated runtime evidence",
                )
            catalog_resources = dict(catalog_snapshot.resource_evidence)
            bindings: dict[str, Any] = {}
            for entity in _combat_scope_entities(resolved):
                for group in entity.resource_bindings.values():
                    for binding in group:
                        if catalog_resources.get(binding.exact_ref) != binding.content_hash:
                            raise ValueError(
                                "compiled combat resource differs from catalog snapshot"
                            )
                        previous = bindings.setdefault(binding.exact_ref, binding)
                        if previous.content_hash != binding.content_hash:
                            raise ValueError("compiled combat resource evidence conflicts")
                        metadata = model_registry.metadata(binding.model_ref)
                        evidence = binding.model_evidence
                        if (
                            not metadata.trusted
                            or not evidence.trusted
                            or metadata.artifact_sha256 != evidence.artifact_sha256
                            or metadata.interface_version != evidence.interface_version
                        ):
                            raise ValueError("compiled combat model differs from Registry evidence")
            profiles: dict[str, dict[str, Any]] = {}
            chains: dict[str, EffectDamageChainV2] = {}
            ammunition = tuple(
                binding for binding in bindings.values() if binding.resource_type == "ammunition"
            )
            for weapon in sorted(
                (binding for binding in bindings.values() if binding.resource_type == "weapons"),
                key=lambda item: item.exact_ref,
            ):
                content = weapon.normalized_content
                effect_ref = content.get("effect_ref")
                effect = bindings.get(effect_ref)
                if effect is None or effect.resource_type != "effects":
                    raise ValueError("weapon effect binding is absent")
                damage_ref = effect.normalized_content.get("damage_model_ref")
                damage = bindings.get(damage_ref)
                if damage is None or damage.resource_type != "damage_models":
                    raise ValueError("effect damage-model binding is absent")
                ammunition_refs = tuple(
                    item.exact_ref
                    for item in ammunition
                    if item.normalized_content.get("weapon_ref") == weapon.exact_ref
                )
                maximum_range = content.get("max_range_m", content.get("range_m"))
                if not ammunition_refs or not isinstance(maximum_range, (int, float)):
                    raise ValueError("weapon ammunition or range evidence is incomplete")
                hit_probability = float(content.get("hit_probability", 1.0))
                if not math.isfinite(hit_probability) or not 0.0 <= hit_probability <= 1.0:
                    raise ValueError("weapon hit probability is not finite probability evidence")
                delivery_model = content.get("delivery_model", "instant")
                if delivery_model not in {
                    "instant",
                    "guided_missile",
                    "delayed_effect",
                    "contact_detonation",
                }:
                    raise ValueError("weapon delivery model is unsupported")
                impact_delay_ticks = content.get("impact_delay_ticks", 0)
                if (
                    isinstance(impact_delay_ticks, bool)
                    or not isinstance(impact_delay_ticks, int)
                    or impact_delay_ticks < 0
                    or (
                        delivery_model in {"delayed_effect", "contact_detonation"}
                        and impact_delay_ticks < 1
                    )
                    or (
                        delivery_model not in {"delayed_effect", "contact_detonation"}
                        and impact_delay_ticks != 0
                    )
                ):
                    raise ValueError("weapon impact delay is incompatible with delivery model")
                missile_profile = None
                if delivery_model == "guided_missile":
                    from openmdbench.world.missile_v2 import GuidedMissileProfileV2

                    missile_profile = GuidedMissileProfileV2.model_validate(content.get("missile"))
                profiles[weapon.exact_ref] = {
                    "ammunition_refs": ammunition_refs,
                    "target_domains": tuple(content.get("target_domains", ())),
                    "min_range_m": float(content.get("min_range_m", 0.0)),
                    "max_range_m": float(maximum_range),
                    "cooldown_ticks": int(content.get("cooldown_ticks", 0)),
                    "effect_ref": effect.exact_ref,
                    "hit_probability": hit_probability,
                    "energy_per_shot": float(content.get("energy_per_shot", 0.0)),
                    "model_ref": weapon.model_ref,
                    "delivery_model": delivery_model,
                    "impact_delay_ticks": impact_delay_ticks,
                    "missile_profile": missile_profile,
                }
                chains[effect.exact_ref] = EffectDamageChainV2.from_resolved_refs(
                    effect_ref=effect.exact_ref,
                    damage_model_ref=damage.exact_ref,
                    resolved_hash=actual[0],
                )
            value = cls(_authority=object())
            value.resolved_hash = actual[0]
            value.catalog_hash = actual[1]
            value.model_registry_hash = actual[2]
            value.catalog_snapshot = catalog_snapshot
            value.model_registry = model_registry
            value.world = world
            value._weapon_profiles = MappingProxyType(
                {
                    reference: MappingProxyType(dict(profile))
                    for reference, profile in sorted(profiles.items())
                }
            )
            value._effect_damage_chains = MappingProxyType(dict(sorted(chains.items())))
            value.resolved = resolved
            from openmdbench.catalog.v2 import CatalogResourceV2
            from openmdbench.world.factory_v2 import WorldFactoryV2

            if not profiles:
                raise ValueError("resolved scenario contains no combat model profile")
            hit_binding = next(
                weapon
                for weapon in sorted(
                    (
                        binding
                        for binding in bindings.values()
                        if binding.resource_type == "weapons"
                    ),
                    key=lambda item: item.exact_ref,
                )
            )
            hit_definition = CatalogResourceV2(
                schema_version=hit_binding.schema_version,
                resource_type=hit_binding.resource_type,
                id=hit_binding.id,
                version=hit_binding.version,
                engine_compatibility=hit_binding.engine_compatibility,
                model_id=hit_binding.model_ref,
                dependencies=hit_binding.dependencies,
                content=dict(hit_binding.content),
            )
            hit_metadata = model_registry.metadata(hit_binding.model_ref)
            hit_evidence = HitModelEvidenceV2(
                model_ref=hit_binding.model_ref,
                registered_model_ref=hit_binding.model_ref,
                interface_version=hit_metadata.interface_version,
                expected_interface_version=hit_metadata.interface_version,
                artifact_hash=hit_metadata.artifact_sha256,
                expected_artifact_hash=hit_metadata.artifact_sha256,
                registry_hash=model_registry.content_hash,
                trusted=hit_metadata.trusted,
            )

            def materialize_hit_model(factory_product: object, metadata: object) -> object:
                if not isinstance(factory_product, CatalogResourceV2):
                    raise ValueError("registered hit model factory returned an invalid adapter")
                if (
                    factory_product.exact_ref != hit_definition.exact_ref
                    or getattr(metadata, "exact_ref", None) != hit_binding.model_ref
                ):
                    raise ValueError("registered hit model factory evidence differs")
                return HitModelV2(
                    evidence=hit_evidence,
                )

            materialized = model_registry.materialize_runtime_adapter(
                hit_binding.model_ref,
                hit_definition,
                materialize_hit_model,
            )
            if not isinstance(materialized, HitModelV2):
                raise ValueError("Registry did not return its materialized hit model")
            value._hit_model = materialized
            saved_hit_state = world._combat_hit_model_state
            if saved_hit_state:
                value._hit_model.combat_restore(saved_hit_state)
            else:
                world._combat_hit_model_state = value._hit_model.combat_snapshot()
            value.world_factory = WorldFactoryV2(
                model_registry=model_registry,
                entity_factory=world._entity_factory,
            )
            value._transaction_failure_stage = None
            value._transaction_failure_adapter_index = None
            value._capability_resolver = None
            return value
        except CombatErrorV2:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise combat_error(
                "combat.resolved_binding_invalid",
                "model_trust",
                type(error).__name__,
                "combat requires intact Resolved, Catalog, Registry, and World evidence",
            ) from error

    @property
    def engagement_ledger(self) -> tuple[Any, ...]:
        return tuple(
            self.world._combat_engagement_ledger[key]
            for key in sorted(self.world._combat_engagement_ledger)
        )

    @property
    def hit_model(self) -> HitModelV2:
        return self._hit_model

    def set_capability_resolver(
        self, resolver: Callable[[str, str, float, int, str], float] | None
    ) -> None:
        """Install the World-owned, session-local capability authority.

        Resource identity and tick remain explicit inputs.  The combat model
        keeps no environment state, which preserves its reuse outside a World
        while making an installed World authoritative for environment effects.
        """

        self._capability_resolver = resolver

    def _effective_capability_value(
        self,
        *,
        attacker_id: str,
        component_ref: str,
        capability: str,
        base_value: float,
        tick: int,
    ) -> float:
        value = base_value
        if self._capability_resolver is not None:
            value = self._capability_resolver(
                attacker_id,
                capability,
                base_value,
                tick,
                component_ref,
            )
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise ValueError("World capability resolver returned an invalid capability value")
        return float(value)

    def _effective_hit_probability(
        self,
        *,
        attacker_id: str,
        weapon_ref: str,
        base_probability: float,
        tick: int,
    ) -> float:
        value = self._effective_capability_value(
            attacker_id=attacker_id,
            component_ref=weapon_ref,
            capability="weapon.hit_probability",
            base_value=base_probability,
            tick=tick,
        )
        return min(1.0, max(0.0, float(value)))

    @property
    def legality_stage_order(self) -> tuple[str, ...]:
        return EngagementLegalityV2.STAGE_ORDER

    def _first_legality_failure(
        self,
        *,
        request: Any,
        evidence: CombatWorldStateEvidenceV2,
        profile: Mapping[str, Any],
    ) -> str | None:
        metadata = self.model_registry.metadata(self._hit_model.model_ref)
        checks = {
            "authority": (
                evidence.controller_authorized
                and evidence.authority_token_owner_id == evidence.attacker_id
            ),
            "roe": (
                evidence.roe_rule_id in self.world.roe_rules
                and self.world.roe_rules[evidence.roe_rule_id].engagement_permitted
            ),
            "contact": (
                evidence.contact_quality > 0.0
                and evidence.contact_owner_id == evidence.attacker_id
                and evidence.contact_target_id == evidence.target_id
                and evidence.contact_age_ticks <= evidence.max_contact_age_ticks
                and evidence.contact_confidence >= evidence.minimum_contact_confidence
            ),
            "envelope": (
                float(profile["min_range_m"]) <= evidence.range_m <= float(profile["max_range_m"])
            ),
            "ammunition": (
                request.ammunition_ref in profile["ammunition_refs"]
                and evidence.ammunition_available >= request.shots
            ),
            "cooldown": evidence.cooldown_remaining == 0,
            "target_domain": evidence.target_domain in profile["target_domains"],
            "attacker_lifecycle": evidence.attacker_lifecycle in {"active", "degraded"},
            "capability": "engage" in evidence.capabilities,
            "relationship": evidence.relationship in {"hostile", "enemy"},
            "components": all(
                value not in {"disabled", "destroyed"}
                for value in evidence.component_states.values()
            ),
            "energy": evidence.energy_available
            >= (float(profile["energy_per_shot"]) * request.shots),
            "model_trust": (
                metadata.trusted
                and metadata.interface_version
                == self._hit_model.evidence.expected_interface_version
                and metadata.artifact_sha256 == self._hit_model.artifact_hash
                and self.model_registry.content_hash == self._hit_model.registry_hash
            ),
        }
        return next(
            (stage for stage in EngagementLegalityV2.STAGE_ORDER if not checks[stage]),
            None,
        )

    def derive_legality_evidence(
        self,
        *,
        attacker_id: str,
        target_id: str,
        authority_token: str,
        contact_evidence_id: str | None = None,
    ) -> CombatWorldStateEvidenceV2:
        try:
            attacker = self.world.get(attacker_id)
            target = self.world.get(target_id)
        except (KeyError, ValueError) as error:
            raise combat_error(
                "combat.entity_unknown",
                "authority",
                (attacker_id, target_id),
                "combat authority evidence requires two active World entities",
            ) from error
        relationship = next(
            (
                item.relation
                for item in self.world.relationships
                if item.source_faction_id == attacker.faction_id
                and item.target_faction_id == target.faction_id
            ),
            "neutral",
        )
        grant = self.world.authority_tokens.get(authority_token)
        claims = self.world.controller_ownership.by_entity(attacker_id)
        controller_authorized = (
            grant is not None
            and grant.entity_id == attacker_id
            and any(
                claim.controller_id == grant.controller_id and attacker_id in claim.entity_ids
                for claim in claims
            )
        )
        rule = next(
            (
                candidate
                for candidate in self.world.roe_rules.values()
                if candidate.source_faction_id == attacker.faction_id
                and candidate.target_faction_id == target.faction_id
                and candidate.relationship == relationship
            ),
            None,
        )
        contact = self.world.contact_store.resolve(
            evidence_id=contact_evidence_id,
            owner_entity_id=attacker_id,
            target_entity_id=target_id,
            current_tick=self.world.tick,
        )
        capabilities = tuple(sorted({token.operation for token in attacker.capability_tokens}))
        return CombatWorldStateEvidenceV2(
            attacker_id=attacker_id,
            target_id=target_id,
            attacker_lifecycle=attacker.state.lifecycle,
            controller_id=(grant.controller_id if grant is not None else "controller.uncontrolled"),
            controller_authorized=controller_authorized,
            relationship=relationship,
            contact_quality=0.0 if contact is None else contact.quality,
            capabilities=capabilities,
            component_states={
                str(key): str(value) for key, value in attacker.state.component_states.items()
            },
            energy_available=0.0 if attacker.state.energy is None else attacker.state.energy,
            cooldown_remaining=self.world._combat_cooldowns.get(
                f"{attacker_id}|{next(iter(self._weapon_profiles), '')}", 0
            ),
            ammunition_available=sum(attacker.state.ammunition.values()),
            world_snapshot_hash=self.world.snapshot().snapshot_hash,
            range_m=math.dist(attacker.state.position_m, target.state.position_m),
            target_domain=target.domain,
            authority_token=authority_token,
            authority_token_owner_id=(grant.entity_id if grant is not None else "unbound"),
            contact_evidence_id=(
                contact_evidence_id
                if contact is None and contact_evidence_id is not None
                else contact.evidence_id
                if contact is not None
                else "contact.unbound"
            ),
            contact_owner_id=contact.owner_entity_id if contact is not None else "unbound",
            contact_target_id=contact.target_entity_id if contact is not None else "unbound",
            contact_age_ticks=contact.age_ticks if contact is not None else 0,
            max_contact_age_ticks=contact.max_age_ticks if contact is not None else 0,
            contact_confidence=contact.confidence if contact is not None else 0.0,
            minimum_contact_confidence=(contact.minimum_confidence if contact is not None else 1.0),
            roe_rule_id=rule.rule_id if rule is not None else "roe.unbound",
        )

    def fault_inject_damage_adapter(self, *, fail_on_call: int) -> None:
        for entity in self.world._entities.values():
            for binding in entity.definition.resource_bindings.get("damage_models", ()):
                adapter = entity.adapters.get(binding.exact_ref)
                if adapter is not None:
                    adapter.fail_on_call = fail_on_call

    def remove_damage_adapter(self, damage_model_ref: str) -> None:
        for entity in self.world._entities.values():
            if damage_model_ref in entity.adapters:
                entity.adapters = MappingProxyType(
                    {
                        reference: adapter
                        for reference, adapter in entity.adapters.items()
                        if reference != damage_model_ref
                    }
                )

    def inject_transaction_failure(self, *, stage: str, adapter_index: int) -> None:
        if stage not in {
            "damage_adapter_1",
            "damage_adapter_n",
            "commit",
            "adapter_restore",
        }:
            raise ValueError("unsupported combat transaction failure stage")
        if (
            not isinstance(adapter_index, int)
            or isinstance(adapter_index, bool)
            or adapter_index < 1
        ):
            raise ValueError("adapter failure index must be a positive exact integer")
        self._transaction_failure_stage = stage
        self._transaction_failure_adapter_index = adapter_index
        if stage in {"damage_adapter_1", "damage_adapter_n"}:
            fail_on_call = 1 if stage == "damage_adapter_1" else adapter_index
            for entity in self.world._entities.values():
                for binding in entity.definition.resource_bindings.get("damage_models", ()):
                    adapter = entity.adapters.get(binding.exact_ref)
                    if adapter is not None and hasattr(adapter, "fail_on_call"):
                        adapter.fail_on_call = fail_on_call

    def adapter_state_snapshot(self) -> tuple[dict[str, Any], ...]:
        return cast(tuple[dict[str, Any], ...], self.world._combat_adapter_states())

    def execute(self, request: Any, *, expected_tick: int) -> Any:
        return self.execute_batch(
            (request,),
            expected_tick=expected_tick,
            operation_id=f"combat:{request.request_id}",
        )[0]

    def execute_batch(
        self,
        requests: Sequence[Any],
        *,
        expected_tick: int,
        operation_id: str,
    ) -> tuple[Any, ...]:
        from openmdbench.combat.models_v2 import (
            EngagementRequestV2,
            ShotEvidenceV2,
            WeaponExecutionV2,
        )
        from openmdbench.schemas.domain_v2 import DamageIntentV2
        from openmdbench.world.checkpoint_v2 import CheckpointCombatEngagementV2
        from openmdbench.world.missile_v2 import MissileFlightV2

        if (
            not isinstance(requests, Sequence)
            or isinstance(requests, (str, bytes, bytearray))
            or any(not isinstance(item, EngagementRequestV2) for item in requests)
        ):
            raise TypeError("combat batch requires typed engagement requests")
        typed_requests = tuple(requests)
        fingerprints = {
            request.request_id: _canonical_hash(request.model_dump(mode="json"))
            for request in typed_requests
        }
        if len(fingerprints) != len(typed_requests):
            raise combat_error(
                "combat.request_id_conflict",
                "request",
                tuple(request.request_id for request in typed_requests),
                "combat batch request identities must be unique",
            )

        with self.world._lock:
            replayed: dict[str, WeaponExecutionV2] = {}
            pending: list[Any] = []
            for request in typed_requests:
                previous = self.world._combat_engagement_ledger.get(request.request_id)
                if previous is None:
                    pending.append(request)
                    continue
                if previous.request_fingerprint != fingerprints[request.request_id]:
                    raise combat_error(
                        "combat.request_id_conflict",
                        "request",
                        request.request_id,
                        "combat request identity was reused with different evidence",
                    )
                replayed[request.request_id] = WeaponExecutionV2.model_validate(previous.execution)
            if not pending:
                return tuple(replayed[request.request_id] for request in typed_requests)
            if (
                not isinstance(expected_tick, int)
                or isinstance(expected_tick, bool)
                or expected_tick != self.world.tick
                or any(request.tick != expected_tick for request in pending)
            ):
                raise combat_error(
                    "combat.tick_conflict",
                    "tick",
                    (
                        tuple(request.tick for request in pending),
                        expected_tick,
                        self.world.tick,
                    ),
                    "pending request, expected, and authoritative World ticks must match exactly",
                )

            prior_runtime = {
                entity_id: (
                    entity.state.clone(),
                    entity.capabilities,
                    entity.capability_tokens,
                )
                for entity_id, entity in self.world._entities.items()
            }
            prior_damage_ledger = dict(self.world._combat_ledger)
            prior_engagement_ledger = dict(self.world._combat_engagement_ledger)
            prior_rng = list(self.world._combat_rng_state)
            prior_cooldowns = dict(self.world._combat_cooldowns)
            prior_component_health = dict(self.world._combat_component_health)
            prior_missile_flights = dict(self.world._missile_flights)
            prior_pending_impacts = dict(self.world._pending_impacts)
            prior_pending_impact_receipts = dict(self.world._pending_impact_receipts)
            prior_hit_model_state = dict(self.world._combat_hit_model_state)
            prior_hit_model_calls = self._hit_model.call_count
            prior_indexes = self.world._indexes
            prior_capability_index = self.world.capability_index
            prior_controller_ownership = self.world.controller_ownership
            adapter_states: list[tuple[object, Any]] = []
            seen_adapters: set[int] = set()
            for entity in self.world._entities.values():
                for adapter in entity.adapters.values():
                    identity = id(adapter)
                    snapshot_adapter = getattr(adapter, "combat_snapshot", None)
                    restore_adapter = getattr(adapter, "combat_restore", None)
                    if (
                        identity not in seen_adapters
                        and callable(snapshot_adapter)
                        and callable(restore_adapter)
                    ):
                        seen_adapters.add(identity)
                        adapter_states.append((adapter, snapshot_adapter()))

            def rollback() -> tuple[str, ...]:
                cleanup_errors: list[str] = []
                for index, (adapter, state) in enumerate(reversed(adapter_states), start=1):
                    restore_adapter = getattr(adapter, "combat_restore", None)
                    if not callable(restore_adapter):
                        cleanup_errors.append("TypeError:combat restore protocol disappeared")
                        continue
                    try:
                        if (
                            self._transaction_failure_stage == "adapter_restore"
                            and self._transaction_failure_adapter_index == index
                        ):
                            raise RuntimeError("injected combat adapter restore failure")
                        restore_adapter(state)
                    except Exception as error:
                        cleanup_errors.append(f"{type(error).__name__}:{error}")
                        try:
                            restore_adapter(state)
                        except Exception as retry_error:
                            cleanup_errors.append(f"{type(retry_error).__name__}:{retry_error}")
                for entity_id, (state, capabilities, tokens) in prior_runtime.items():
                    entity = self.world._entities[entity_id]
                    entity.state = state
                    entity.capabilities = capabilities
                    entity.capability_tokens = tokens
                self.world._combat_ledger = prior_damage_ledger
                self.world._combat_engagement_ledger = prior_engagement_ledger
                self.world._combat_rng_state = prior_rng
                self.world._combat_cooldowns = prior_cooldowns
                self.world._combat_component_health = prior_component_health
                self.world._missile_flights = prior_missile_flights
                self.world._pending_impacts = prior_pending_impacts
                self.world._pending_impact_receipts = prior_pending_impact_receipts
                self.world._combat_hit_model_state = prior_hit_model_state
                self.world._indexes = prior_indexes
                self.world.capability_index = prior_capability_index
                self.world.controller_ownership = prior_controller_ownership
                self._hit_model.call_count = prior_hit_model_calls
                return tuple(cleanup_errors)

            executions: list[WeaponExecutionV2] = []
            intents: dict[str, DamageIntentV2] = {}
            staged_missiles: dict[str, MissileFlightV2] = {}
            staged_pending_impacts: dict[str, PendingImpactV2] = {}
            staged_ammunition: dict[tuple[str, str], int] = {}
            staged_energy: dict[str, float | None] = {}
            rng_evidence: list[str] = []
            try:
                for request in pending:
                    try:
                        attacker = self.world.get(request.attacker_id)
                        target = self.world.get(request.target_id)
                        profile = self._weapon_profiles[request.weapon_ref]
                    except (KeyError, ValueError) as error:
                        raise combat_error(
                            "combat.weapon_unknown",
                            "model_trust",
                            request.weapon_ref,
                            "engagement resource is absent from the resolved World",
                        ) from error
                    cooldown_key = f"{request.attacker_id}|{request.weapon_ref}"
                    ammunition_key = (request.attacker_id, request.ammunition_ref)
                    ammunition_available = staged_ammunition.get(
                        ammunition_key,
                        attacker.state.ammunition.get(request.ammunition_ref, 0),
                    )
                    energy_available = staged_energy.get(request.attacker_id, attacker.state.energy)
                    evidence = self.derive_legality_evidence(
                        attacker_id=request.attacker_id,
                        target_id=request.target_id,
                        authority_token=request.authority_token,
                        contact_evidence_id=request.contact_evidence_id,
                    ).model_copy(
                        update={
                            "energy_available": (
                                0.0 if energy_available is None else energy_available
                            ),
                            "cooldown_remaining": self.world._combat_cooldowns.get(cooldown_key, 0),
                            "ammunition_available": ammunition_available,
                        }
                    )
                    failure_stage = self._first_legality_failure(
                        request=request,
                        evidence=evidence,
                        profile=profile,
                    )
                    if failure_stage is not None:
                        raise combat_error(
                            f"combat.{failure_stage}_denied",
                            failure_stage,
                            request.request_id,
                            "authoritative World legality evidence denies engagement "
                            "at its first stage",
                        )
                    if request.ammunition_ref not in profile["ammunition_refs"] or (
                        ammunition_available < request.shots
                    ):
                        raise combat_error(
                            "combat.ammunition_unavailable",
                            "ammunition",
                            ammunition_available,
                            "insufficient exact ammunition is available",
                        )
                    range_m = evidence.range_m
                    if not profile["min_range_m"] <= range_m <= profile["max_range_m"]:
                        raise combat_error(
                            "combat.envelope_invalid",
                            "envelope",
                            range_m,
                            "target is outside the resolved weapon envelope",
                        )
                    energy_cost = (
                        max(
                            0.0,
                            self._effective_capability_value(
                                attacker_id=request.attacker_id,
                                component_ref=request.weapon_ref,
                                capability="energy.consumption",
                                base_value=float(profile["energy_per_shot"]),
                                tick=expected_tick,
                            ),
                        )
                        * request.shots
                    )
                    if energy_available is None or energy_available < energy_cost:
                        raise combat_error(
                            "combat.energy_unavailable",
                            "energy",
                            energy_available,
                            "insufficient authoritative energy is available",
                        )
                    effective_hit_probability = self._effective_hit_probability(
                        attacker_id=request.attacker_id,
                        weapon_ref=request.weapon_ref,
                        base_probability=float(profile["hit_probability"]),
                        tick=expected_tick,
                    )
                    shots: list[ShotEvidenceV2] = []
                    launched_missile_ids: list[str] = []
                    pending_impact_ids: list[str] = []
                    if profile["delivery_model"] == "guided_missile":
                        missile_profile = profile["missile_profile"]
                        if missile_profile is None:
                            raise ValueError("guided missile profile is absent")
                        chain = self._effect_damage_chains[str(profile["effect_ref"])]
                        effect_binding = next(
                            binding
                            for binding in attacker.definition.resource_bindings["effects"]
                            if binding.exact_ref == chain.effect_ref
                        )
                        magnitude = float(effect_binding.normalized_content.get("magnitude", 0.0))
                        heading_rad = math.radians(attacker.state.heading_deg)
                        velocity = (
                            missile_profile.launch_speed_mps * math.sin(heading_rad),
                            missile_profile.launch_speed_mps * math.cos(heading_rad),
                            0.0,
                        )
                        for index in range(request.shots):
                            missile_id = f"missile:{request.request_id}:{index:03d}"
                            if (
                                missile_id in self.world._missile_flights
                                or missile_id in staged_missiles
                            ):
                                raise combat_error(
                                    "combat.missile_identity_conflict",
                                    "request",
                                    missile_id,
                                    "guided missile identity was already launched",
                                )
                            staged_missiles[missile_id] = MissileFlightV2(
                                missile_id=missile_id,
                                request_id=request.request_id,
                                launcher_id=request.attacker_id,
                                faction_id=attacker.faction_id,
                                target_id=request.target_id,
                                weapon_ref=request.weapon_ref,
                                ammunition_ref=request.ammunition_ref,
                                effect_ref=chain.effect_ref,
                                damage_model_ref=chain.damage_model_ref,
                                magnitude=magnitude,
                                hit_probability=effective_hit_probability,
                                launch_tick=expected_tick,
                                flight_ticks=0,
                                position_m=tuple(attacker.state.position_m),
                                velocity_mps=velocity,
                                heading_deg=attacker.state.heading_deg,
                                last_known_target_position_m=tuple(target.state.position_m),
                                profile=missile_profile,
                            )
                            launched_missile_ids.append(missile_id)
                    else:
                        for index in range(request.shots):
                            seed_payload = [
                                self.resolved_hash,
                                self.world.session_id,
                                request.request_id,
                                expected_tick,
                                index,
                            ]
                            shot_seed = int(
                                hashlib.sha256(json.dumps(seed_payload).encode()).hexdigest()[:16],
                                16,
                            )
                            result = self._hit_model.evaluate(
                                shot_seed=shot_seed,
                                range_m=range_m,
                                target_domain=target.domain,
                                probability=effective_hit_probability,
                            )
                            evidence_hash = _canonical_hash(
                                [*seed_payload, result.receipt.model_dump(mode="json")]
                            )
                            shots.append(
                                ShotEvidenceV2(
                                    shot_index=index,
                                    seed=shot_seed,
                                    sample=result.sample,
                                    hit=result.hit,
                                    effect_ref=str(profile["effect_ref"]),
                                    model_ref=result.receipt.model_ref,
                                    model_identity=result.receipt.model_identity,
                                    model_call_sequence=result.receipt.call_sequence,
                                    model_input_hash=result.receipt.input_hash,
                                    probability=result.receipt.probability,
                                    evidence_hash=evidence_hash,
                                )
                            )
                            rng_evidence.append(evidence_hash)
                            if profile["delivery_model"] in {
                                "delayed_effect",
                                "contact_detonation",
                            }:
                                chain = self._effect_damage_chains[str(profile["effect_ref"])]
                                effect_binding = next(
                                    binding
                                    for binding in attacker.definition.resource_bindings["effects"]
                                    if binding.exact_ref == chain.effect_ref
                                )
                                impact_id = f"impact:{request.request_id}:{index:03d}"
                                if (
                                    impact_id in self.world._pending_impacts
                                    or impact_id in self.world._pending_impact_receipts
                                    or impact_id in staged_pending_impacts
                                ):
                                    raise combat_error(
                                        "combat.pending_impact_identity_conflict",
                                        "request",
                                        impact_id,
                                        "delayed impact identity was already consumed or queued",
                                    )
                                staged_pending_impacts[impact_id] = PendingImpactV2(
                                    impact_id=impact_id,
                                    execution_id=f"execution:{request.request_id}",
                                    request_id=request.request_id,
                                    launch_tick=expected_tick,
                                    scheduled_tick=(
                                        expected_tick + int(profile["impact_delay_ticks"])
                                    ),
                                    source_entity_id=request.attacker_id,
                                    target_entity_id=request.target_id,
                                    weapon_ref=request.weapon_ref,
                                    ammunition_ref=request.ammunition_ref,
                                    effect_ref=chain.effect_ref,
                                    damage_model_ref=chain.damage_model_ref,
                                    magnitude=float(
                                        effect_binding.normalized_content.get("magnitude", 0.0)
                                    ),
                                    shot=shots[-1],
                                    launch_position_m=tuple(attacker.state.position_m),
                                    target_position_at_launch_m=tuple(target.state.position_m),
                                    evidence_hash=_canonical_hash(
                                        [
                                            impact_id,
                                            chain.chain_hash,
                                            shots[-1].evidence_hash,
                                            expected_tick,
                                        ]
                                    ),
                                )
                                pending_impact_ids.append(impact_id)
                            elif result.hit:
                                chain = self._effect_damage_chains[str(profile["effect_ref"])]
                                effect_binding = next(
                                    binding
                                    for binding in attacker.definition.resource_bindings["effects"]
                                    if binding.exact_ref == chain.effect_ref
                                )
                                magnitude = float(
                                    effect_binding.normalized_content.get("magnitude", 0.0)
                                )
                                intent_id = f"damage:{request.request_id}:{index}"
                                intents[f"weapon:{intent_id}"] = DamageIntentV2(
                                    schema_version="2.0",
                                    intent_id=intent_id,
                                    tick=expected_tick,
                                    source_entity_id=request.attacker_id,
                                    target_entity_id=request.target_id,
                                    effect_ref=chain.effect_ref,
                                    damage_model_ref=chain.damage_model_ref,
                                    magnitude=magnitude,
                                    evidence_hash=_canonical_hash(
                                        [intent_id, chain.chain_hash, evidence_hash]
                                    ),
                                    source_kind="weapon",
                                    parameters={
                                        "shot_evidence_hash": evidence_hash,
                                        "impact_position_m": tuple(target.state.position_m),
                                        "coordinate_frame": "local-m",
                                    },
                                )
                    execution = WeaponExecutionV2(
                        execution_id=f"execution:{request.request_id}",
                        request_id=request.request_id,
                        tick=expected_tick,
                        attacker_id=request.attacker_id,
                        target_id=request.target_id,
                        weapon_ref=request.weapon_ref,
                        ammunition_ref=request.ammunition_ref,
                        requested_shots=request.shots,
                        effect_ref=str(profile["effect_ref"]),
                        shots=tuple(shots),
                        launched_missile_ids=tuple(launched_missile_ids),
                        pending_impact_ids=tuple(pending_impact_ids),
                        launch_position_m=tuple(attacker.state.position_m),
                        launch_velocity_mps=tuple(attacker.state.velocity_mps),
                        target_position_at_launch_m=tuple(target.state.position_m),
                        target_velocity_at_launch_mps=tuple(target.state.velocity_mps),
                    )
                    executions.append(execution)
                    staged_ammunition[ammunition_key] = ammunition_available - request.shots
                    staged_energy[request.attacker_id] = energy_available - energy_cost

                self.world.apply_damage_transaction(
                    intents=intents,
                    expected_tick=expected_tick,
                    operation_id=f"{operation_id}:damage",
                )
                if self._transaction_failure_stage in {"commit", "adapter_restore"}:
                    raise RuntimeError("injected staged combat transaction failure")
                for (entity_id, ammunition_ref), count in staged_ammunition.items():
                    self.world._entities[entity_id].state.ammunition[ammunition_ref] = count
                for entity_id, energy in staged_energy.items():
                    self.world._entities[entity_id].state.energy = energy
                self.world._missile_flights.update(staged_missiles)
                self.world._pending_impacts.update(staged_pending_impacts)
                self.world._combat_rng_state.extend(rng_evidence)
                for request, execution in zip(pending, executions, strict=True):
                    cooldown_key = f"{request.attacker_id}|{request.weapon_ref}"
                    self.world._combat_cooldowns[cooldown_key] = int(
                        self._weapon_profiles[request.weapon_ref]["cooldown_ticks"]
                    )
                    execution_payload = execution.model_dump(mode="json")
                    self.world._combat_engagement_ledger[request.request_id] = (
                        CheckpointCombatEngagementV2(
                            request_id=request.request_id,
                            request_fingerprint=fingerprints[request.request_id],
                            operation_id=operation_id,
                            tick=expected_tick,
                            attacker_id=request.attacker_id,
                            target_id=request.target_id,
                            execution_hash=_canonical_hash(execution_payload),
                            execution=execution_payload,
                        )
                    )
            except Exception as error:
                cleanup_errors = rollback()
                self._transaction_failure_stage = None
                self._transaction_failure_adapter_index = None
                if isinstance(error, CombatErrorV2):
                    raise
                raise combat_error(
                    "combat.transaction_failure",
                    "commit",
                    cleanup_errors or type(error).__name__,
                    "staged World combat transaction failed and was rolled back",
                ) from error
            finally:
                if self._transaction_failure_stage is None:
                    self._transaction_failure_adapter_index = None

            result_by_id = dict(replayed)
            result_by_id.update({execution.request_id: execution for execution in executions})
            self.world._combat_hit_model_state = self._hit_model.combat_snapshot()
            return tuple(result_by_id[request.request_id] for request in typed_requests)

    def resolve_pending_impacts(
        self, *, expected_tick: int
    ) -> tuple[tuple[PendingImpactReceiptV2, ...], dict[str, DamageIntentV2]]:
        """Consume due delayed weapon outcomes once and return canonical damage intents."""

        if (
            not isinstance(expected_tick, int)
            or isinstance(expected_tick, bool)
            or expected_tick != self.world.tick
        ):
            raise combat_error(
                "combat.pending_impact_tick_conflict",
                "tick",
                expected_tick,
                "pending impact resolution must use the authoritative World tick",
            )
        with self.world._lock:
            due = tuple(
                impact
                for _impact_id, impact in sorted(self.world._pending_impacts.items())
                if impact.scheduled_tick <= expected_tick
            )
            receipts: list[PendingImpactReceiptV2] = []
            intents: dict[str, DamageIntentV2] = {}
            for impact in due:
                if impact.impact_id in self.world._pending_impact_receipts:
                    raise combat_error(
                        "combat.pending_impact_replayed",
                        "request",
                        impact.impact_id,
                        "a delayed impact cannot be consumed more than once",
                    )
                target = self.world._entities.get(impact.target_entity_id)
                if not impact.shot.hit:
                    status: Literal["hit", "miss", "target_unavailable"] = "miss"
                    impact_position_m: tuple[float, float, float] | None = None
                elif target is None:
                    status = "target_unavailable"
                    impact_position_m = None
                else:
                    status = "hit"
                    impact_position_m = tuple(target.state.position_m)
                    intent_id = f"damage:{impact.impact_id}"
                    intents[f"weapon:{intent_id}"] = DamageIntentV2(
                        schema_version="2.0",
                        intent_id=intent_id,
                        tick=expected_tick,
                        source_entity_id=impact.source_entity_id,
                        target_entity_id=impact.target_entity_id,
                        effect_ref=impact.effect_ref,
                        damage_model_ref=impact.damage_model_ref,
                        magnitude=impact.magnitude,
                        evidence_hash=_canonical_hash(
                            [intent_id, impact.evidence_hash, expected_tick, impact_position_m]
                        ),
                        source_kind="weapon",
                        parameters={
                            "pending_impact_id": impact.impact_id,
                            "shot_evidence_hash": impact.shot.evidence_hash,
                            "impact_position_m": impact_position_m,
                            "target_position_at_launch_m": impact.target_position_at_launch_m,
                            "coordinate_frame": "local-m",
                        },
                    )
                receipt = PendingImpactReceiptV2(
                    impact_id=impact.impact_id,
                    execution_id=impact.execution_id,
                    request_id=impact.request_id,
                    tick=expected_tick,
                    source_entity_id=impact.source_entity_id,
                    target_entity_id=impact.target_entity_id,
                    status=status,
                    effect_ref=impact.effect_ref,
                    damage_model_ref=impact.damage_model_ref,
                    impact_position_m=impact_position_m,
                    evidence_hash=_canonical_hash(
                        [impact.evidence_hash, expected_tick, status, impact_position_m]
                    ),
                )
                receipts.append(receipt)
            for receipt in receipts:
                self.world._pending_impacts.pop(receipt.impact_id)
                self.world._pending_impact_receipts[receipt.impact_id] = receipt
            return tuple(receipts), intents

    def resolve_missile_terminal(
        self,
        *,
        flight: Any,
        tick: int,
        position_m: tuple[float, float, float],
        closest_approach_m: float,
        seeker_detected: bool,
        target_position_m: tuple[float, float, float] | None,
        missile_velocity_mps: tuple[float, float, float] | None,
        closest_approach_time_fraction: float | None,
        flight_evidence_hash: str,
    ) -> tuple[Any, DamageIntentV2 | None]:
        """Sample terminal hit probability only after a physical fuse encounter."""

        from openmdbench.world.missile_v2 import MissileFlightV2, MissileTerminalReceiptV2

        if not isinstance(flight, MissileFlightV2):
            raise TypeError("missile terminal resolution requires a typed missile flight")
        if tick != self.world.tick or not math.isfinite(closest_approach_m):
            raise combat_error(
                "combat.missile_terminal_invalid",
                "tick",
                (tick, closest_approach_m),
                "missile terminal resolution differs from authoritative World time",
            )
        target = self.world._entities.get(flight.target_id)
        # A target that still exists and is not already destroyed is a physical
        # object the missile can hit.  Treating ``disabled`` as unavailable threw
        # away every fuzed finishing hit (status ``target_unavailable`` with
        # closest_approach 0.0), so a unit could only ever be reduced to
        # ``disabled`` and never to ``destroyed`` -- no engagement in any scenario
        # could produce a kill.
        if target is None or target.state.lifecycle in {"destroyed", "wreck", "despawned"}:
            receipt = MissileTerminalReceiptV2(
                missile_id=flight.missile_id,
                request_id=flight.request_id,
                launcher_id=flight.launcher_id,
                target_id=flight.target_id,
                tick=tick,
                status="target_unavailable",
                position_m=position_m,
                closest_approach_m=closest_approach_m,
                seeker_state=flight.seeker_state,
                seeker_detected=seeker_detected,
                target_position_m=target_position_m,
                missile_velocity_mps=missile_velocity_mps,
                closest_approach_time_fraction=closest_approach_time_fraction,
                evidence_hash=_canonical_hash(
                    [flight_evidence_hash, flight.missile_id, tick, "target_unavailable"]
                ),
            )
            return receipt, None
        seed_payload = [
            self.resolved_hash,
            self.world.session_id,
            flight.missile_id,
            tick,
            "terminal",
        ]
        seed = int(hashlib.sha256(json.dumps(seed_payload).encode()).hexdigest()[:16], 16)
        result = self._hit_model.evaluate(
            shot_seed=seed,
            range_m=closest_approach_m,
            target_domain=target.domain,
            probability=flight.hit_probability,
        )
        hit_evidence_hash = _canonical_hash(
            [*seed_payload, flight_evidence_hash, result.receipt.model_dump(mode="json")]
        )
        self.world._combat_rng_state.append(hit_evidence_hash)
        self.world._combat_hit_model_state = self._hit_model.combat_snapshot()
        status: Literal["hit", "fuse_miss"] = "hit" if result.hit else "fuse_miss"
        receipt = MissileTerminalReceiptV2(
            missile_id=flight.missile_id,
            request_id=flight.request_id,
            launcher_id=flight.launcher_id,
            target_id=flight.target_id,
            tick=tick,
            status=status,
            position_m=position_m,
            closest_approach_m=closest_approach_m,
            seeker_state=flight.seeker_state,
            seeker_detected=seeker_detected,
            target_position_m=target_position_m,
            missile_velocity_mps=missile_velocity_mps,
            closest_approach_time_fraction=closest_approach_time_fraction,
            impact_position_m=position_m if result.hit else None,
            evidence_hash=hit_evidence_hash,
        )
        if not result.hit:
            return receipt, None
        intent_id = f"damage:{flight.missile_id}"
        return receipt, DamageIntentV2(
            schema_version="2.0",
            intent_id=intent_id,
            tick=tick,
            source_entity_id=flight.launcher_id,
            target_entity_id=flight.target_id,
            effect_ref=flight.effect_ref,
            damage_model_ref=flight.damage_model_ref,
            magnitude=flight.magnitude,
            evidence_hash=_canonical_hash([intent_id, hit_evidence_hash]),
            source_kind="weapon",
            parameters={
                "missile_id": flight.missile_id,
                "closest_approach_m": closest_approach_m,
                "seeker_detected": seeker_detected,
                "impact_position_m": position_m,
                "target_position_m": target_position_m,
                "closest_approach_time_fraction": closest_approach_time_fraction,
                "coordinate_frame": "local-m",
            },
        )

    def advance_tick(self, ticks: int) -> None:
        self.world.advance_tick(ticks)

    @classmethod
    def restore(
        cls,
        *,
        checkpoint: Any,
        resolved: Any | None = None,
        catalog_snapshot: CombatCatalogSnapshotV2 | None = None,
        model_registry: Any | None = None,
        world_factory: Any | None = None,
        expected_checkpoint_hash: str | None = None,
        expected_resolved_hash: str | None = None,
        expected_catalog_hash: str | None = None,
        expected_registry_hash: str | None = None,
    ) -> CombatSystemV2:
        if (
            resolved is None
            or catalog_snapshot is None
            or model_registry is None
            or world_factory is None
            or expected_checkpoint_hash is None
            or expected_resolved_hash is None
            or expected_catalog_hash is None
            or expected_registry_hash is None
        ):
            raise combat_error(
                "combat.checkpoint_anchor_missing",
                "checkpoint",
                None,
                "combat restore requires original Resolved, Catalog, Registry, and hash anchors",
            )
        if (
            checkpoint.checkpoint_hash != expected_checkpoint_hash
            or checkpoint.resolved_hash != expected_resolved_hash
            or checkpoint.catalog_hash != expected_catalog_hash
            or checkpoint.model_registry_hash != expected_registry_hash
        ):
            raise combat_error(
                "combat.checkpoint_anchor_mismatch",
                "checkpoint",
                expected_checkpoint_hash,
                "combat checkpoint differs from its independent external anchors",
            )
        try:
            checkpoint.validate_integrity()
            restored_world = world_factory.restore_checkpoint(
                checkpoint,
                resolved=resolved,
                model_registry=model_registry,
                expected_checkpoint_hash=expected_checkpoint_hash,
            )
            return cls.from_world(
                resolved=resolved,
                catalog_snapshot=catalog_snapshot,
                model_registry=model_registry,
                world=restored_world,
                expected_resolved_hash=expected_resolved_hash,
                expected_catalog_hash=expected_catalog_hash,
                expected_registry_hash=expected_registry_hash,
            )
        except CombatErrorV2:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise combat_error(
                "combat.checkpoint_restore_invalid",
                "checkpoint",
                type(error).__name__,
                "combat checkpoint failed validated external-anchor restoration",
            ) from error


class CombatWorldStateEvidenceV2(CombatModelV2):
    attacker_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    attacker_lifecycle: Literal["active", "degraded", "disabled", "destroyed", "despawned"]
    controller_id: str = Field(min_length=1)
    controller_authorized: bool
    relationship: str = Field(min_length=1)
    contact_quality: float = Field(ge=0.0, le=1.0)
    capabilities: tuple[str, ...]
    component_states: dict[str, str]
    energy_available: float = Field(ge=0.0)
    cooldown_remaining: StrictInt = Field(ge=0)
    ammunition_available: StrictInt = Field(ge=0)
    world_snapshot_hash: str = Field(default="sha256:" + "0" * 64, pattern=_HASH_PATTERN)
    range_m: float = Field(default=0.0, ge=0.0)
    target_domain: str = Field(default="unknown", min_length=1)
    authority_token: str = Field(default="authority.unbound", min_length=1)
    authority_token_owner_id: str = Field(default="unbound", min_length=1)
    contact_evidence_id: str = Field(default="contact.unbound", min_length=1)
    contact_owner_id: str = Field(default="unbound", min_length=1)
    contact_target_id: str = Field(default="unbound", min_length=1)
    contact_age_ticks: StrictInt = Field(default=0, ge=0)
    max_contact_age_ticks: StrictInt = Field(default=1, ge=0)
    contact_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_contact_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    roe_rule_id: str = Field(default="roe.default", min_length=1)


class EngagementLegalityV2(CombatModelV2):
    STAGE_ORDER: ClassVar[tuple[str, ...]] = (
        "authority",
        "roe",
        "contact",
        "envelope",
        "ammunition",
        "cooldown",
        "target_domain",
        "attacker_lifecycle",
        "capability",
        "relationship",
        "components",
        "energy",
        "model_trust",
    )

    allowed: bool
    stage_evidence: tuple[str, ...]

    @classmethod
    def derive(cls, state: CombatWorldStateEvidenceV2) -> EngagementLegalityV2:
        if not isinstance(state, CombatWorldStateEvidenceV2):
            raise TypeError("combat legality requires typed World state evidence")
        allowed = (
            state.controller_authorized
            and state.authority_token_owner_id == state.attacker_id
            and state.contact_owner_id == state.attacker_id
            and state.contact_target_id == state.target_id
            and state.contact_age_ticks <= state.max_contact_age_ticks
            and state.contact_confidence >= state.minimum_contact_confidence
            and state.contact_quality > 0.0
            and state.attacker_lifecycle in {"active", "degraded"}
            and "engage" in state.capabilities
            and state.relationship in {"hostile", "enemy"}
            and all(
                value not in {"disabled", "destroyed"} for value in state.component_states.values()
            )
            and state.energy_available > 0.0
            and state.cooldown_remaining == 0
            and state.ammunition_available > 0
        )
        return cls(allowed=allowed, stage_evidence=cls.STAGE_ORDER)


class HitModelEvidenceV2(CombatModelV2):
    model_ref: str = Field(min_length=1)
    registered_model_ref: str = Field(min_length=1)
    interface_version: str = Field(min_length=1)
    expected_interface_version: str = Field(min_length=1)
    artifact_hash: str = Field(pattern=_HASH_PATTERN)
    expected_artifact_hash: str = Field(pattern=_HASH_PATTERN)
    registry_hash: str = Field(pattern=_HASH_PATTERN)
    trusted: bool

    @classmethod
    def from_registry(
        cls,
        *,
        model_ref: str,
        interface_version: str,
        artifact_hash: str,
        registry_hash: str,
    ) -> HitModelEvidenceV2:
        if _REF_PATTERN.fullmatch(model_ref) is None or interface_version != "hit-model@2.0":
            raise combat_error(
                "combat.hit_model_evidence_invalid",
                "model_trust",
                model_ref,
                "hit model evidence requires an exact registered interface identity",
            )
        return cls(
            model_ref=model_ref,
            registered_model_ref=model_ref,
            interface_version=interface_version,
            expected_interface_version=interface_version,
            artifact_hash=artifact_hash,
            expected_artifact_hash=artifact_hash,
            registry_hash=registry_hash,
            trusted=True,
        )


class HitModelReceiptV2(CombatModelV2):
    model_ref: str = Field(min_length=1)
    model_identity: str = Field(pattern=_HASH_PATTERN)
    call_sequence: StrictInt = Field(ge=1)
    input_hash: str = Field(pattern=_HASH_PATTERN)
    probability: float = Field(ge=0.0, le=1.0)
    sample: float = Field(ge=0.0, lt=1.0)
    hit: bool


class HitModelResultV2(CombatModelV2):
    probability: float = Field(ge=0.0, le=1.0)
    sample: float = Field(ge=0.0, lt=1.0)
    hit: bool
    model_evidence: HitModelEvidenceV2
    receipt: HitModelReceiptV2


class HitModelV2:
    def __init__(self, *, evidence: HitModelEvidenceV2) -> None:
        if not isinstance(evidence, HitModelEvidenceV2):
            raise TypeError("hit model requires registry evidence")
        if (
            not evidence.trusted
            or evidence.model_ref != evidence.registered_model_ref
            or evidence.interface_version != evidence.expected_interface_version
            or evidence.artifact_hash != evidence.expected_artifact_hash
        ):
            raise combat_error(
                "combat.hit_model_evidence_invalid",
                "model_trust",
                evidence.model_ref,
                "hit model identity differs from its complete Registry evidence",
            )
        self.evidence = evidence
        self.identity = _canonical_hash(
            [evidence.model_ref, evidence.registry_hash, evidence.artifact_hash]
        )
        self.call_count = 0

    @property
    def model_ref(self) -> str:
        return self.evidence.model_ref

    @property
    def interface_version(self) -> str:
        return "hit-model@2.0"

    @property
    def artifact_hash(self) -> str:
        return self.evidence.artifact_hash

    @property
    def registry_hash(self) -> str:
        return self.evidence.registry_hash

    def combat_snapshot(self) -> dict[str, object]:
        return {
            "schema_version": "hit-model-state@2.0",
            "model_ref": self.model_ref,
            "model_identity": self.identity,
            "call_count": self.call_count,
        }

    def combat_restore(self, snapshot: Mapping[str, object]) -> None:
        if (
            not isinstance(snapshot, Mapping)
            or snapshot.get("schema_version") != "hit-model-state@2.0"
            or snapshot.get("model_ref") != self.model_ref
            or snapshot.get("model_identity") != self.identity
            or not isinstance(snapshot.get("call_count"), int)
            or isinstance(snapshot.get("call_count"), bool)
            or cast(int, snapshot["call_count"]) < 0
        ):
            raise combat_error(
                "combat.hit_model_state_invalid",
                "checkpoint",
                snapshot,
                "hit model state differs from its fresh Registry-created identity",
            )
        self.call_count = cast(int, snapshot["call_count"])

    def evaluate(
        self,
        *,
        shot_seed: int,
        range_m: float,
        target_domain: str,
        probability: float,
    ) -> HitModelResultV2:
        if (
            not isinstance(shot_seed, int)
            or isinstance(shot_seed, bool)
            or shot_seed < 0
            or isinstance(range_m, bool)
            or not isinstance(range_m, (int, float))
            or not math.isfinite(float(range_m))
            or float(range_m) < 0.0
            or not isinstance(target_domain, str)
            or not target_domain
            or isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(float(probability))
            or not 0.0 <= float(probability) <= 1.0
        ):
            raise combat_error(
                "combat.hit_model_input_invalid",
                "model_trust",
                (shot_seed, range_m, target_domain, probability),
                "hit model input must be finite and typed",
            )
        self.call_count += 1
        probability = float(probability)
        # This is a reproducible simulation substream, never a security secret.
        sample = random.Random(shot_seed).random()  # nosec B311
        hit = sample < probability
        input_hash = _canonical_hash(
            [self.identity, shot_seed, float(range_m), target_domain, probability]
        )
        return HitModelResultV2(
            probability=probability,
            sample=sample,
            hit=hit,
            model_evidence=self.evidence,
            receipt=HitModelReceiptV2(
                model_ref=self.model_ref,
                model_identity=self.identity,
                call_sequence=self.call_count,
                input_hash=input_hash,
                probability=probability,
                sample=sample,
                hit=hit,
            ),
        )


class EffectDamageChainV2(CombatModelV2):
    effect_ref: str = Field(min_length=1)
    damage_model_ref: str = Field(min_length=1)
    resolved_hash: str = Field(pattern=_HASH_PATTERN)
    chain_hash: str = Field(pattern=_HASH_PATTERN)

    @classmethod
    def from_resolved_refs(
        cls, *, effect_ref: str, damage_model_ref: str, resolved_hash: str
    ) -> EffectDamageChainV2:
        if (
            _REF_PATTERN.fullmatch(effect_ref) is None
            or _REF_PATTERN.fullmatch(damage_model_ref) is None
        ):
            raise combat_error(
                "combat.effect_chain_invalid",
                "model_trust",
                (effect_ref, damage_model_ref),
                "effect and damage model require exact resolved references",
            )
        return cls(
            effect_ref=effect_ref,
            damage_model_ref=damage_model_ref,
            resolved_hash=resolved_hash,
            chain_hash=_canonical_hash([effect_ref, damage_model_ref, resolved_hash]),
        )


def domain_component_damage_intent(
    intent_id: str,
    target_entity_id: str,
    component_id: str,
    magnitude: float,
    *,
    tick: int,
) -> DamageIntentV2:
    return DamageIntentV2(
        schema_version="2.0",
        intent_id=intent_id,
        tick=tick,
        source_entity_id="entity.component-effect-source",
        target_entity_id=target_entity_id,
        effect_ref="effect.arbitrary@2.3.1",
        damage_model_ref="damage.arbitrary@2.3.1",
        magnitude=magnitude,
        evidence_hash=_canonical_hash([intent_id, target_entity_id, component_id, magnitude, tick]),
        source_kind="weapon",
        component_id=component_id,
    )


__all__ = [
    "CombatCatalogSnapshotV2",
    "CombatSystemV2",
    "CombatWorldStateEvidenceV2",
    "EffectDamageChainV2",
    "EngagementLegalityV2",
    "HitModelEvidenceV2",
    "HitModelReceiptV2",
    "HitModelResultV2",
    "HitModelV2",
    "domain_component_damage_intent",
]

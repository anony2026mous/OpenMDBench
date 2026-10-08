"""RF-06 authoritative CombatSystem/World contracts (82 behavior nodes)."""

from __future__ import annotations

import importlib
import inspect
from typing import Any

import pytest


def _api() -> Any:
    return importlib.import_module("openmdbench.combat.v2")


def _system(
    *, hit_probability: float = 1.0, trusted_evidence: bool = True, guided_missile: bool = False
) -> Any:
    from openmdbench.catalog.v2 import (
        CatalogResourceV2,
        CatalogV2,
        ModelFactoryMetadataV2,
        ModelRegistryV2,
    )
    from openmdbench.dynamics.native_v2 import (
        UAV_MODEL_REF,
        register_native_dynamics_models_v2,
    )
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
    from tests.contract import test_world_entity_factory_v2 as world_fixture

    api = _api()

    def compatible_weapon(resources: dict[str, Any]) -> None:
        weapon = resources["weapons"]
        data = weapon.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
        data["content"] = {
            **data["content"],
            "target_domains": ["upper-atmosphere"],
            "hit_probability": hit_probability,
            **(
                {
                    "delivery_model": "guided_missile",
                    "missile": {
                        "launch_speed_mps": 20.0,
                        "cruise_speed_mps": 100.0,
                        "max_acceleration_mps2": 100.0,
                        "max_turn_rate_deg_s": 180.0,
                        "max_vertical_speed_mps": 20.0,
                        "seeker_range_m": 100.0,
                        "seeker_fov_deg": 360.0,
                        "seeker_detection_probability": 1.0,
                        "fuse_radius_m": 2.0,
                        "max_flight_ticks": 10,
                    },
                }
                if guided_missile
                else {}
            ),
        }
        resources["weapons"] = CatalogResourceV2(**data)
        if guided_missile:
            effect = resources["effects"]
            effect_data = effect.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
            effect_data["content"] = {**effect_data["content"], "magnitude": 1.0}
            resources["effects"] = CatalogResourceV2(**effect_data)
        ammunition = resources["ammunition"]
        ammo_data = ammunition.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
        ammo_data["content"] = {**ammo_data["content"], "mass_per_round_kg": 0.01}
        resources["ammunition"] = CatalogResourceV2(**ammo_data)

        dynamics = resources["dynamics"]
        dynamics_data = dynamics.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
        dynamics_data["model_id"] = UAV_MODEL_REF
        dynamics_data["content"] = {
            **dynamics_data["content"],
            "max_speed_mps": 80.0,
            "max_turn_rate_deg_s": 30.0,
            "max_vertical_speed_mps": 20.0,
            "max_acceleration_mps2": 8.0,
            "max_deceleration_mps2": 10.0,
            "min_altitude_m": 0.0,
            "max_altitude_m": 3000.0,
        }
        resources["dynamics"] = CatalogResourceV2(**dynamics_data)

    resources = resource_fixture._resources()
    compatible_weapon(resources)
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.runtime-binding",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position_m": "m", "speed_mps": "m/s"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + "a" * 64,
            resource_types=tuple(item for item in resource_fixture.ALL_TYPES if item != "dynamics"),
            field_units={"position_m": "m", "speed_mps": "m/s", "mode": "1"},
        ),
        lambda definition: definition,
    )
    register_native_dynamics_models_v2(registry)
    registry.freeze()
    catalog = CatalogV2(resources.values(), engine_version="2.0.0", model_registry=registry)
    payload = resource_fixture._scenario()
    payload["factions"] = [
        {"schema_version": "2.0", "id": "coalition.alpha"},
        {"schema_version": "2.0", "id": "coalition.beta"},
    ]
    payload["relationships"] = [
        {
            "schema_version": "2.0",
            "source_faction_id": "coalition.alpha",
            "target_faction_id": "coalition.beta",
            "relation": "hostile",
        }
    ]
    entities = []
    for index in range(2):
        entity = resource_fixture._entity(rounds=100)
        entity["id"] = f"asset.{index:03d}"
        entity["faction_id"] = ("coalition.alpha", "coalition.beta")[index]
        entity["controller_slot"] = f"controller.slot.{index:03d}"
        entity["target_domains"] = ["upper-atmosphere"]
        entity["initial_state"]["position_m"] = [float(index), 2.0, 3.0]
        entity["initial_state"]["energy"] = 0.75
        entity["initial_state"]["component_states"] = {"mode": "ready"}
        entities.append(entity)
    payload["entities"] = entities
    resolved = resource_fixture._compile(catalog, payload)
    registry = catalog.model_registry
    world = world_fixture._factories(registry)[1].build(resolved)
    system = api.CombatSystemV2.from_world(
        resolved=resolved,
        catalog_snapshot=api.CombatCatalogSnapshotV2.from_resolved(resolved),
        model_registry=registry,
        world=world,
        expected_resolved_hash=resolved.resolved_hash,
        expected_catalog_hash=resolved.catalog_hash,
        expected_registry_hash=resolved.model_registry_hash,
    )
    if trusted_evidence:
        evidence_api = importlib.import_module("openmdbench.world.combat_evidence_v2")
        system.world.install_contact_evidence(
            evidence_api.WorldContactEvidenceV2(
                evidence_id="contact.asset.001",
                owner_entity_id="asset.000",
                target_entity_id="asset.001",
                observed_tick=0,
                age_ticks=0,
                max_age_ticks=1,
                confidence=1.0,
                minimum_confidence=0.5,
                quality=1.0,
            )
        )
        system.world.install_roe_policy(
            evidence_api.WorldRoeRuleV2(
                rule_id="roe.explicit.alpha-beta",
                source_faction_id="coalition.alpha",
                target_faction_id="coalition.beta",
                relationship="hostile",
                engagement_permitted=True,
            )
        )
    return system


def _request(**changes: Any) -> Any:
    values = {
        "request_id": "engagement.authoritative.001",
        "tick": 0,
        "attacker_id": "asset.000",
        "target_id": "asset.001",
        "weapon_ref": "weapon.arbitrary@2.4.1",
        "ammunition_ref": "round.arbitrary@2.4.1",
        "shots": 1,
        "authority_token": "authority.asset.000",
        "contact_evidence_id": "contact.asset.001",
    }
    values.update(changes)
    return _api().EngagementRequestV2(**values)


def _intent(index: int = 0, **changes: Any) -> Any:
    values = {
        "intent_id": f"intent.{index:03d}",
        "tick": 0,
        "source_entity_id": "asset.000",
        "target_entity_id": "asset.001",
        "effect_ref": "effect.arbitrary@2.4.1",
        "damage_model_ref": "damage.arbitrary@2.4.1",
        "magnitude": 0.01,
        "evidence_hash": "sha256:" + f"{index + 1:064x}",
        "source_kind": "weapon",
    }
    values.update(changes)
    return _api().DamageIntentV2(**values)


def _dto(dto_name: str) -> Any:
    api = _api()
    request = _request()
    execution = api.WeaponExecutionV2.from_request(request, execution_id="execution.001")
    examples = {
        "EngagementRequestV2": request,
        "WeaponExecutionV2": execution,
        "HitV2": api.HitV2(
            hit_id="hit.001",
            execution_id=execution.execution_id,
            target_id=request.target_id,
            time_fraction=0.5,
            position_m=(0.0, 0.0, 0.0),
            evidence_hash="sha256:" + "1" * 64,
        ),
        "EffectApplicationV2": api.EffectApplicationV2(
            effect_id="application.001",
            effect_ref="effect.arbitrary@2.4.1",
            hit_id="hit.001",
            target_id=request.target_id,
            magnitude=0.1,
        ),
        "DamageIntentV2": _intent(),
        "DamageResolutionV2": api.DamageSystemV2(
            known_entity_ids=(request.target_id,),
            known_damage_model_refs=("damage.arbitrary@2.4.1",),
        ).resolve((_intent(),), initial_health={request.target_id: 1.0}),
    }
    return examples[dto_name]


@pytest.mark.parametrize(
    "dto_name",
    (
        "EngagementRequestV2",
        "WeaponExecutionV2",
        "HitV2",
        "EffectApplicationV2",
        "DamageIntentV2",
        "DamageResolutionV2",
    ),
)
def test_public_dto_is_frozen_strict_and_roundtrips(dto_name: str) -> None:
    dto = _dto(dto_name)
    recovered = type(dto).from_json(dto.to_json())
    assert recovered == dto
    with pytest.raises((AttributeError, TypeError)):
        recovered.tick = 999


@pytest.mark.parametrize(
    "stage",
    (
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
    ),
)
def test_legality_stage_order_first_error_and_zero_side_effect(stage: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    evidence = system.derive_legality_evidence(
        attacker_id="asset.000", target_id="asset.001", authority_token="authority.asset.000"
    )
    field = {
        "authority": "controller_authorized",
        "roe": "relationship",
        "contact": "contact_quality",
        "envelope": "contact_quality",
        "ammunition": "ammunition_available",
        "cooldown": "cooldown_remaining",
        "target_domain": "contact_quality",
        "attacker_lifecycle": "attacker_lifecycle",
        "capability": "capabilities",
        "relationship": "relationship",
        "components": "component_states",
        "energy": "energy_available",
        "model_trust": "contact_quality",
    }[stage]
    values: dict[str, object] = {
        "ammunition_available": 0,
        "energy_available": 0.0,
        "cooldown_remaining": 1,
        "controller_authorized": False,
        "relationship": "neutral",
        "contact_quality": 0.0,
        "attacker_lifecycle": "destroyed",
        "capabilities": (),
        "component_states": {"mode": "disabled"},
    }
    value = values[field]
    denied = _api().EngagementLegalityV2.derive(evidence.model_copy(update={field: value}))
    assert not denied.allowed
    assert system.world.checkpoint() == before


@pytest.mark.parametrize("shots", (0, 1, 10, 100))
def test_shot_substreams_are_ordered_unique_and_deterministic(shots: int) -> None:
    effective = shots
    first = _system().execute_batch(
        (_request(shots=effective),), expected_tick=0, operation_id=f"combat.shots.{shots}"
    )[0]
    second = _system().execute_batch(
        (_request(shots=effective),), expected_tick=0, operation_id=f"combat.shots.{shots}"
    )[0]
    assert first == second
    assert tuple(item.shot_index for item in first.shots) == tuple(range(effective))
    assert len({item.seed for item in first.shots}) == effective
    assert len({item.evidence_hash for item in first.shots}) == effective


@pytest.mark.parametrize("mode", ("same", "different_target", "different_shots", "checkpoint"))
def test_request_fingerprint_idempotency_and_conflict(mode: str) -> None:
    system = _system()
    request = _request(request_id=f"engagement.idempotent.{mode}")
    original = system.execute_batch(
        (request,), expected_tick=0, operation_id=f"combat.first.{mode}"
    )
    checkpoint = system.world.checkpoint()
    if mode == "checkpoint":
        system = _api().CombatSystemV2.restore(
            checkpoint=checkpoint,
            resolved=system.resolved,
            catalog_snapshot=system.catalog_snapshot,
            model_registry=system.model_registry,
            world_factory=system.world_factory,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            expected_resolved_hash=checkpoint.resolved_hash,
            expected_catalog_hash=checkpoint.catalog_hash,
            expected_registry_hash=checkpoint.model_registry_hash,
        )
    changed = request
    if mode == "different_target":
        changed = request.model_copy(update={"target_id": "asset.other"})
    elif mode == "different_shots":
        changed = request.model_copy(update={"shots": 2})
    if mode in {"same", "checkpoint"}:
        assert (
            system.execute_batch((changed,), expected_tick=0, operation_id=f"combat.replay.{mode}")
            == original
        )
        assert system.world.checkpoint() == checkpoint
    else:
        with pytest.raises(_api().CombatErrorV2) as captured:
            system.execute_batch(
                (changed,), expected_tick=0, operation_id=f"combat.conflict.{mode}"
            )
        assert captured.value.code == "combat.request_id_conflict"
        assert system.world.checkpoint() == checkpoint


@pytest.mark.parametrize(
    "attack",
    (
        "nan",
        "negative",
        "bool_tick",
        "unknown_target",
        "bad_hash",
        "wrong_model",
        "duplicate",
        "wrong_tick",
        "partial_evidence",
        "unknown_effect",
    ),
)
def test_domain_damage_intent_is_strict_and_integrity_bound(attack: str) -> None:
    api = _api()
    changes: dict[str, Any] = (
        {"magnitude": float("nan")} if attack == "nan" else {"magnitude": -1.0}
    )
    if attack == "bool_tick":
        changes = {"tick": True}
    elif attack == "unknown_target":
        changes = {"target_entity_id": "missing"}
    elif attack == "bad_hash":
        changes = {"evidence_hash": "bad"}
    elif attack == "wrong_model":
        changes = {"damage_model_ref": "damage.missing@2.4.1"}
    elif attack == "partial_evidence":
        changes = {"magnitude": None}
    elif attack == "unknown_effect":
        changes = {"effect_ref": "effect.missing@2.4.1"}
    with pytest.raises((api.CombatErrorV2, ValueError)):
        intent = _intent(**changes)
        chain = None
        if attack == "unknown_effect":
            chain = api.EffectDamageChainV2.from_resolved_refs(
                effect_ref="effect.arbitrary@2.4.1",
                damage_model_ref="damage.arbitrary@2.4.1",
                resolved_hash=_system().resolved_hash,
            )
        api.DamageSystemV2(
            known_entity_ids=("asset.001",),
            known_damage_model_refs=("damage.arbitrary@2.4.1",),
            chain=chain,
        ).resolve(
            (intent, intent) if attack == "duplicate" else (intent,),
            initial_health={"asset.001": 1.0},
        )


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_damage_aggregation_is_order_independent_and_simultaneous(count: int) -> None:
    intents = tuple(_intent(index) for index in range(count))
    damage = _api().DamageSystemV2(
        known_entity_ids=("asset.001",), known_damage_model_refs=("damage.arbitrary@2.4.1",)
    )
    forward = damage.resolve(intents, initial_health={"asset.001": 1.0})
    reverse = damage.resolve(tuple(reversed(intents)), initial_health={"asset.001": 1.0})
    assert forward == reverse
    assert tuple(item.intent_id for item in forward.applied_intents) == tuple(
        sorted(item.intent_id for item in intents)
    )


@pytest.mark.parametrize(
    ("magnitude", "health", "capabilities"),
    ((0.0, 1.0, ("sense",)), (0.25, 0.75, ("sense",)), (1.0, 0.0, ())),
)
def test_component_damage_profile_zero_partial_full(
    magnitude: float, health: float, capabilities: tuple[str, ...]
) -> None:
    api = _api()
    state = api.DamageStateV2.with_components(
        entity_id="asset.000", components={"sensor": ("sense",)}
    )
    api.DamageSystemV2(
        known_entity_ids=("asset.000",), known_damage_model_refs=("damage.arbitrary@2.4.1",)
    ).apply_atomic(
        (_intent(component_id="sensor", target_entity_id="asset.000", magnitude=magnitude),),
        state=state,
        expected_tick=0,
    )
    entity = state.entity("asset.000")
    assert entity.component_health["sensor"] == pytest.approx(health)
    assert entity.capabilities == capabilities


@pytest.mark.parametrize("stage", ("commit", "adapter_restore", "commit", "adapter_restore"))
def test_world_transaction_failure_rolls_back_every_combat_state(stage: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    system.inject_transaction_failure(stage=stage, adapter_index=2)
    with pytest.raises(_api().CombatErrorV2):
        system.execute_batch(
            (_request(),), expected_tick=0, operation_id=f"combat.rollback.{stage}"
        )
    assert system.world.checkpoint() == before
    assert system.adapter_state_snapshot() == before.combat_adapter_states


@pytest.mark.parametrize(
    "attack",
    (
        "ammo",
        "cooldown",
        "rng",
        "ledger",
        "profiles",
        "model_evidence",
        "resolved_anchor",
        "registry_anchor",
    ),
)
def test_checkpoint_tamper_and_anchor_mismatch_fail_closed(attack: str) -> None:
    system = _system()
    checkpoint = system.world.checkpoint()
    kwargs = dict(
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world_factory=system.world_factory,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_resolved_hash=checkpoint.resolved_hash,
        expected_catalog_hash=checkpoint.catalog_hash,
        expected_registry_hash=checkpoint.model_registry_hash,
    )
    key = {
        "ammo": "expected_checkpoint_hash",
        "cooldown": "expected_checkpoint_hash",
        "rng": "expected_checkpoint_hash",
        "ledger": "expected_checkpoint_hash",
        "profiles": "expected_catalog_hash",
        "model_evidence": "expected_registry_hash",
        "resolved_anchor": "expected_resolved_hash",
        "registry_anchor": "expected_registry_hash",
    }[attack]
    kwargs[key] = "sha256:" + "f" * 64
    with pytest.raises(_api().CombatErrorV2):
        _api().CombatSystemV2.restore(checkpoint=checkpoint, **kwargs)


@pytest.mark.parametrize("anchor", ("resolved", "catalog", "registry", "world"))
def test_from_world_requires_all_exact_external_anchors(anchor: str) -> None:
    system = _system()
    kwargs = dict(
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world=system.world,
        expected_resolved_hash=system.resolved.resolved_hash,
        expected_catalog_hash=system.resolved.catalog_hash,
        expected_registry_hash=system.resolved.model_registry_hash,
    )
    key = {
        "resolved": "expected_resolved_hash",
        "catalog": "expected_catalog_hash",
        "registry": "expected_registry_hash",
        "world": "expected_resolved_hash",
    }[anchor]
    kwargs[key] = "sha256:" + "f" * 64
    with pytest.raises(_api().CombatErrorV2):
        _api().CombatSystemV2.from_world(**kwargs)


@pytest.mark.parametrize(
    "token",
    (
        "CombatExecutorV2",
        "CombatWorldIntegrationV2",
        "CombatWorldHarnessV2",
        "synthetic_trusted",
        "from_world_fixture",
        "domain_damage_intent",
        "__getattr__",
        "effect.synthetic",
        "_ALLOWED_EFFECT_REFS",
        "scenarios.legacy",
    ),
)
def test_public_production_source_has_no_legacy_or_synthetic_bypass(token: str) -> None:
    api = _api()
    source = inspect.getsource(api) + inspect.getsource(
        importlib.import_module("openmdbench.combat")
    )
    assert token not in source


@pytest.mark.parametrize("attack", ("unknown", "untrusted", "interface", "artifact_hash"))
def test_hit_and_damage_models_require_exact_registry_factory_evidence(attack: str) -> None:
    system = _system()
    evidence = system.hit_model.evidence.model_copy(
        update={
            "unknown": {"model_ref": "missing@2.0.0"},
            "untrusted": {"trusted": False},
            "interface": {"interface_version": "wrong"},
            "artifact_hash": {"artifact_hash": "sha256:" + "f" * 64},
        }[attack]
    )
    with pytest.raises(_api().CombatErrorV2):
        _api().HitModelV2(evidence=evidence)


@pytest.mark.parametrize("resource", ("weapon", "ammunition", "effect", "damage_model"))
def test_missing_or_wrong_combat_resource_fails_before_mutation(resource: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    request = _request(
        **(
            {"weapon_ref": "weapon.missing@2.4.1"}
            if resource == "weapon"
            else {"ammunition_ref": "round.missing@2.4.1"}
            if resource == "ammunition"
            else {}
        )
    )
    if resource in {"effect", "damage_model"}:
        system.remove_damage_adapter("damage.arbitrary@2.4.1")
    with pytest.raises(_api().CombatErrorV2):
        system.execute(request, expected_tick=0)
    assert system.world.checkpoint().tick == before.tick


@pytest.mark.parametrize(
    "case", ("partial_ammo", "destroyed_attacker", "disabled_attacker", "cooldown_expiry")
)
def test_runtime_resource_lifecycle_and_cooldown_contract(case: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    if case == "cooldown_expiry":
        system.execute(_request(request_id="cooldown.first"), expected_tick=0)
        _advance_world(system.world, 10)
        assert system.world._combat_cooldowns["asset.000|weapon.arbitrary@2.4.1"] == 0
    else:
        request = _request(
            shots=101 if case == "partial_ammo" else 1,
            attacker_id="missing" if case == "destroyed_attacker" else "asset.000",
            authority_token="invalid" if case == "disabled_attacker" else "authority.asset.000",
        )
        if case == "disabled_attacker":
            system.world._entities["asset.000"].state.lifecycle = "disabled"
            before = system.world.checkpoint()
        with pytest.raises(_api().CombatErrorV2):
            system.execute(request, expected_tick=0)
        assert system.world.checkpoint() == before


@pytest.mark.parametrize(
    "order", (("collision", "environment", "weapon"), ("weapon", "collision", "environment"))
)
def test_three_damage_sources_same_tick_are_canonical_and_simultaneous(
    order: tuple[str, ...],
) -> None:
    intents = tuple(
        _intent(index, source_kind=kind, magnitude=0.1) for index, kind in enumerate(order)
    )
    result = (
        _api()
        .DamageSystemV2(
            known_entity_ids=("asset.001",), known_damage_model_refs=("damage.arbitrary@2.4.1",)
        )
        .resolve(intents, initial_health={"asset.001": 1.0})
    )
    assert result.entities[0].health == pytest.approx(0.7)
    assert tuple(item.source_kind for item in result.applied_intents) == (
        "collision",
        "environment",
        "weapon",
    )


@pytest.mark.parametrize("case", ("mutual", "multi_attacker", "reversed"))
def test_multi_party_damage_uses_tick_start_snapshot(case: str) -> None:
    intents: tuple[Any, ...] = (
        _intent(1, source_entity_id="asset.000", target_entity_id="asset.001", magnitude=1.0),
        _intent(2, source_entity_id="asset.001", target_entity_id="asset.000", magnitude=1.0),
    )
    if case == "multi_attacker":
        intents = intents + (
            _intent(3, source_entity_id="asset.002", target_entity_id="asset.001", magnitude=0.1),
        )
    if case == "reversed":
        intents = tuple(reversed(intents))
    result = (
        _api()
        .DamageSystemV2(
            known_entity_ids=("asset.000", "asset.001"),
            known_damage_model_refs=("damage.arbitrary@2.4.1",),
        )
        .resolve(intents, initial_health={"asset.000": 1.0, "asset.001": 1.0})
    )
    states = {item.entity_id: item for item in result.entities}
    assert states["asset.000"].lifecycle == "destroyed"
    assert states["asset.001"].lifecycle == "destroyed"


@pytest.mark.parametrize("valid", (True, False))
def test_explicit_effect_to_damage_chain_is_integrity_bound(valid: bool) -> None:
    system = _system()
    effect = "effect.arbitrary@2.4.1" if valid else "effect.missing@2.4.1"
    if valid:
        chain = _api().EffectDamageChainV2.from_resolved_refs(
            effect_ref=effect,
            damage_model_ref="damage.arbitrary@2.4.1",
            resolved_hash=system.resolved_hash,
        )
        assert chain.effect_ref == effect
        assert chain.chain_hash.startswith("sha256:")
    else:
        chain = _api().EffectDamageChainV2.from_resolved_refs(
            effect_ref="effect.arbitrary@2.4.1",
            damage_model_ref="damage.arbitrary@2.4.1",
            resolved_hash=system.resolved_hash,
        )
        with pytest.raises(_api().CombatErrorV2):
            _api().DamageSystemV2(chain=chain).resolve(
                (_intent(effect_ref=effect),), initial_health={"asset.001": 1.0}
            )


@pytest.mark.parametrize("session_delta", (0, 1))
def test_checkpoint_n_plus_m_preserves_execution_shots_and_ledger(session_delta: int) -> None:
    system = _system()
    first = system.execute(_request(request_id="timeline.first"), expected_tick=0)
    checkpoint = system.world.checkpoint()
    restored = _api().CombatSystemV2.restore(
        checkpoint=checkpoint,
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world_factory=system.world_factory,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_resolved_hash=checkpoint.resolved_hash,
        expected_catalog_hash=checkpoint.catalog_hash,
        expected_registry_hash=checkpoint.model_registry_hash,
    )
    if session_delta:
        assert restored.world.session_id == system.world.session_id
    replay = restored.execute(_request(request_id="timeline.first"), expected_tick=0)
    assert replay == first
    assert restored.engagement_ledger == system.engagement_ledger


@pytest.mark.parametrize("state", ("disabled", "destroyed", "despawned"))
def test_non_operational_attacker_cannot_engage(state: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    if state == "despawned":
        system.world._entities.pop("asset.000")
    else:
        system.world._entities["asset.000"].state.lifecycle = state
        before = system.world.checkpoint()
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_request(request_id=f"lifecycle.{state}"), expected_tick=0)
    assert captured.value.stage in {"attacker_lifecycle", "model_trust"}
    if state != "despawned":
        assert system.world.checkpoint() == before


def test_generic_production_requires_no_implicit_compat_import() -> None:
    production = inspect.getsource(importlib.import_module("openmdbench.combat.v2"))
    package = inspect.getsource(importlib.import_module("openmdbench.combat"))
    assert "combat.legacy" not in production + package
    legacy = importlib.import_module("openmdbench.combat.legacy.compat")
    assert legacy.__name__.endswith("legacy.compat")


@pytest.mark.parametrize(
    "token", ("", "arbitrary", "authority.asset.001", "authority.asset.000.extra")
)
def test_authority_token_must_match_world_controller_ownership_exactly(token: str) -> None:
    system = _system()
    before = system.world.checkpoint()
    request_data = _request().model_dump(mode="python")
    request_data["authority_token"] = token
    if not token:
        with pytest.raises(ValueError):
            _api().EngagementRequestV2(**request_data)
        return
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_api().EngagementRequestV2(**request_data), expected_tick=0)
    assert captured.value.stage == "authority"
    assert system.world.checkpoint() == before


@pytest.mark.parametrize(
    "fault", ("missing", "wrong_owner", "wrong_target", "stale", "low_confidence")
)
def test_contact_must_come_from_authoritative_world_store(fault: str) -> None:
    system = _system()
    assert hasattr(system.world, "contact_store"), "World requires an authoritative contact store"
    store = system.world.contact_store
    store.inject_fault("contact.asset.001", fault=fault)
    before = system.world.checkpoint()
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_request(contact_evidence_id="contact.asset.001"), expected_tick=0)
    assert captured.value.stage == "contact"
    assert system.world.checkpoint() == before


def test_roe_is_resolved_typed_world_evidence_not_synthesized() -> None:
    system = _system()
    assert hasattr(system.world, "roe_rules"), "World requires resolved typed ROE rules"
    assert system.world.roe_rules
    evidence = system.derive_legality_evidence(
        attacker_id="asset.000", target_id="asset.001", authority_token="authority.asset.000"
    )
    assert evidence.roe_rule_id in system.world.roe_rules


@pytest.mark.parametrize(
    ("request_tick", "expected_tick", "world_tick"), ((1, 0, 0), (0, 1, 0), (0, 0, 1))
)
def test_request_expected_and_world_tick_are_one_cas(
    request_tick: int, expected_tick: int, world_tick: int
) -> None:
    system = _system()
    system.world.tick = world_tick
    before = system.world.checkpoint()
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_request(tick=request_tick), expected_tick=expected_tick)
    assert captured.value.stage in {"tick", "request"}
    assert system.world.checkpoint() == before


def test_combat_source_has_no_synthetic_authority_contact_roe_or_fixed_hit_formula() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.combat.system_v2"))
    for forbidden in (
        "authority_prefix",
        "contact_quality=1.0",
        'roe_rule_id=f"roe.',
        "1.0 / (1.0 +",
    ):
        assert forbidden not in source


@pytest.mark.parametrize("probability", (0.0, 0.5, 1.0))
def test_registry_created_hit_model_drives_probability_and_evidence(probability: float) -> None:
    system = _system(hit_probability=probability)
    adapter = system.model_registry.create(system.hit_model.model_ref)
    assert adapter is not system.hit_model
    assert adapter.interface_version == system.hit_model.interface_version
    assert adapter.artifact_hash == system.hit_model.artifact_hash
    before_calls = system.hit_model.call_count
    result = system.execute(_request(request_id="probability.explicit-profile"), expected_tick=0)
    assert system.hit_model.call_count == before_calls + 1
    assert all(shot.effect_ref == "effect.arbitrary@2.4.1" for shot in result.shots)
    assert all(shot.model_ref == system.hit_model.model_ref for shot in result.shots)
    assert all(shot.model_call_sequence == before_calls + 1 for shot in result.shots)
    assert (
        all(shot.hit is (probability == 1.0) for shot in result.shots)
        if probability in {0.0, 1.0}
        else result.shots
    )


def test_combat_profiles_are_deeply_immutable_and_tamper_rejected() -> None:
    system = _system()
    profile = system._weapon_profiles["weapon.arbitrary@2.4.1"]
    with pytest.raises((AttributeError, TypeError)):
        profile["target_domains"] = ("forged-domain",)
    with pytest.raises((AttributeError, TypeError)):
        system._weapon_profiles["weapon.arbitrary@2.4.1"] = {}


@pytest.mark.parametrize("ticks", (0, 1, 10))
def test_combat_advance_tick_uses_the_authoritative_world_clock(ticks: int) -> None:
    system = _system()
    before = system.world.tick
    if ticks == 0:
        system.advance_tick(ticks)
        assert system.world.tick == before
    else:
        with pytest.raises((ValueError, _api().CombatErrorV2)):
            system.advance_tick(ticks)
        assert system.world.tick == before


def test_world_does_not_synthesize_contacts_or_roe_from_relationship_cartesian_product() -> None:
    system = _system(trusted_evidence=False)
    assert not system.world.contact_store.records
    assert not system.world.roe_rules
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_request(), expected_tick=0)
    assert captured.value.stage in {"contact", "roe"}


def test_hit_model_instances_are_fresh_per_world_and_interleaving_isolated() -> None:
    first = _system(hit_probability=0.5)
    second = _system(hit_probability=0.5)
    assert first.hit_model is not second.hit_model
    first_result = first.execute(_request(request_id="session.first"), expected_tick=0)
    second_result = second.execute(_request(request_id="session.second"), expected_tick=0)
    assert first.hit_model.call_count == 1
    assert second.hit_model.call_count == 1
    assert first.hit_model.evidence == second.hit_model.evidence
    assert first_result.shots[0].evidence_hash != second_result.shots[0].evidence_hash


def test_checkpoint_restores_hit_model_state_and_call_receipt() -> None:
    system = _system()
    system.execute(_request(request_id="checkpoint.model.first"), expected_tick=0)
    checkpoint = system.world.checkpoint()
    restored = _api().CombatSystemV2.restore(
        checkpoint=checkpoint,
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world_factory=system.world_factory,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_resolved_hash=checkpoint.resolved_hash,
        expected_catalog_hash=checkpoint.catalog_hash,
        expected_registry_hash=checkpoint.model_registry_hash,
    )
    assert restored.hit_model.call_count == system.hit_model.call_count


def test_combat_clock_cannot_diverge_from_spatial_lifecycle_and_event_clock() -> None:
    system = _system()
    system.world.advance_tick(_tick_input(system.world, 0))
    assert system.world.tick == system.world._spatial_tick
    assert all(item.tick <= system.world.tick for item in system.world.lifecycle_schedule)


def test_replay_precedes_tick_cas_but_fingerprint_conflict_remains_strict() -> None:
    system = _system()
    request = _request(request_id="replay.before.tick-cas")
    receipt = system.execute(request, expected_tick=0)
    _advance_world(system.world, 5)
    before = system.world.checkpoint()
    assert system.execute(request, expected_tick=0) == receipt
    assert system.world.checkpoint() == before
    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(request.model_copy(update={"shots": 2}), expected_tick=0)
    assert captured.value.code == "combat.request_id_conflict"


def test_sources_forbid_relationship_derived_combat_evidence() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    assert "build_world_combat_evidence_v2" not in source
    assert "for target_id, target_faction" not in source


def _second_system(first: Any) -> Any:
    from tests.contract import test_world_entity_factory_v2 as world_fixture

    world_factory = world_fixture._factories(first.model_registry)[1]
    world = world_factory.build(first.resolved)
    evidence_api = importlib.import_module("openmdbench.world.combat_evidence_v2")
    world.install_contact_evidence(
        evidence_api.WorldContactEvidenceV2(
            evidence_id="contact.asset.001",
            owner_entity_id="asset.000",
            target_entity_id="asset.001",
            observed_tick=0,
            age_ticks=0,
            max_age_ticks=1,
            confidence=1.0,
            minimum_confidence=0.5,
            quality=1.0,
        )
    )
    world.install_roe_policy(
        evidence_api.WorldRoeRuleV2(
            rule_id="roe.explicit.alpha-beta",
            source_faction_id="coalition.alpha",
            target_faction_id="coalition.beta",
            relationship="hostile",
            engagement_permitted=True,
        )
    )
    return _api().CombatSystemV2.from_world(
        resolved=first.resolved,
        catalog_snapshot=first.catalog_snapshot,
        model_registry=first.model_registry,
        world=world,
        expected_resolved_hash=first.resolved_hash,
        expected_catalog_hash=first.catalog_hash,
        expected_registry_hash=first.model_registry_hash,
    )


@pytest.mark.parametrize("order", (("first", "second"), ("second", "first")))
def test_same_registry_worlds_have_fresh_hit_models_and_interleaving_isolated(
    order: tuple[str, str],
) -> None:
    first = _system(hit_probability=0.5)
    second = _second_system(first)
    assert first.hit_model is not second.hit_model
    systems = {"first": first, "second": second}
    receipts = {}
    for name in order:
        receipts[name] = systems[name].execute(
            _request(request_id="same.timeline"), expected_tick=0
        )
    assert receipts["first"] == receipts["second"]
    assert first.hit_model.call_count == second.hit_model.call_count == 1


def test_registry_factory_returns_fresh_executable_hit_model_protocol() -> None:
    system = _system()
    first = system.model_registry.create(system.hit_model.model_ref)
    second = system.model_registry.create(system.hit_model.model_ref)
    assert first is not second
    for adapter in (first, second):
        assert callable(adapter.evaluate)
        assert adapter.interface_version == "hit-model@2.0"


def test_checkpoint_restore_uses_fresh_model_and_preserves_n_plus_m_behavior() -> None:
    system = _system(hit_probability=0.5)
    first_receipt = system.execute(_request(request_id="fresh.restore.n"), expected_tick=0)
    checkpoint = system.world.checkpoint()
    original_model = system.hit_model
    restored = _api().CombatSystemV2.restore(
        checkpoint=checkpoint,
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world_factory=system.world_factory,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_resolved_hash=checkpoint.resolved_hash,
        expected_catalog_hash=checkpoint.catalog_hash,
        expected_registry_hash=checkpoint.model_registry_hash,
    )
    assert restored.hit_model is not original_model
    assert (
        restored.execute(_request(request_id="fresh.restore.n"), expected_tick=0) == first_receipt
    )


@pytest.mark.parametrize("ticks", (0, 1, 10))
def test_unified_world_advance_tick_synchronizes_all_clocks(ticks: int) -> None:
    system = _system()
    if ticks == 0:
        system.world.advance_tick(ticks)
        assert system.world.tick == system.world._spatial_tick == 0
    else:
        with pytest.raises(ValueError):
            system.world.advance_tick(ticks)
        assert system.world.tick == system.world._spatial_tick == 0


def test_combat_cannot_jump_tick_when_unprocessed_world_work_is_pending() -> None:
    system = _system()
    system.world._spatial_tick = system.world.tick - 1
    with pytest.raises((ValueError, _api().CombatErrorV2)):
        system.advance_tick(1)


def test_source_has_no_global_adapter_reuse_or_direct_combat_clock_assignment() -> None:
    combat = inspect.getsource(importlib.import_module("openmdbench.combat.system_v2"))
    world = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    assert "runtime_adapters" not in combat
    assert "def advance_combat_clock" not in world


def _tick_input(world: Any, tick: int) -> Any:
    import math

    api = importlib.import_module("openmdbench.world.factory_v2")
    commands = []
    for view in world.entities_stable():
        reference = view.definition.composition.dynamics_ref
        assert reference is not None
        assert reference in view.adapter_diagnostics
        velocity = tuple(view.state.velocity_mps)
        commands.append(
            api.EntityControlCommandV2(
                entity_id=view.id,
                tick=tick,
                controls={
                    "target_speed_mps": math.hypot(*velocity),
                    "target_heading_deg": float(view.state.heading_deg),
                    "target_vertical_m": float(view.state.position_m[2]),
                },
            )
        )
    return api.WorldTickInputV2(
        expected_tick=tick,
        operation_id=f"world.tick.{tick}",
        entity_commands=tuple(commands),
        dt_seconds=1.0,
    )


def _advance_world(world: Any, ticks: int) -> None:
    for tick in range(world.tick, world.tick + ticks):
        world.advance_tick(_tick_input(world, tick))


def test_guided_missile_launches_then_moves_and_resolves_terminal_damage() -> None:
    system = _system(guided_missile=True, hit_probability=1.0)
    world = system.world
    world.install_combat_system(system)

    execution = system.execute(_request(), expected_tick=0)

    assert execution.shots == ()
    assert execution.launched_missile_ids == ("missile:engagement.authoritative.001:000",)
    assert execution.launch_position_m == (0.0, 2.0, 3.0)
    assert execution.target_position_at_launch_m is not None
    assert world.get("asset.001").state.health == pytest.approx(1.0)
    flight = world.missile_flights[0]
    assert flight.position_m == (0.0, 2.0, 3.0)
    assert flight.seeker_state == "searching"

    world.advance_tick(_tick_input(world, 0))

    assert world.missile_flights == ()
    assert world.missile_terminal_receipts[0].status == "hit"
    assert world.missile_terminal_receipts[0].closest_approach_m == pytest.approx(0.0)
    assert world.missile_terminal_receipts[0].impact_position_m is not None
    assert world.missile_terminal_receipts[0].target_position_m is not None
    assert world.missile_terminal_receipts[0].coordinate_frame == "local-m"
    assert world.get("asset.001").state.health < 1.0
    damage = world._world_tick_ledger["world.tick.0"][1].damage_receipts[0]
    assert damage.results[0].health_before == pytest.approx(1.0)
    assert damage.results[0].health_after < 1.0
    assert damage.applied_intents[0].parameters["impact_position_m"] == (
        world.missile_terminal_receipts[0].impact_position_m
    )


def test_guided_missile_checkpoint_restores_inflight_state_and_terminal_result() -> None:
    system = _system(guided_missile=True, hit_probability=1.0)
    world = system.world
    world.install_combat_system(system)
    system.execute(_request(), expected_tick=0)
    checkpoint = world.checkpoint()
    assert checkpoint.missile_flights == world.missile_flights

    restored = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    restored_system = _api().CombatSystemV2.from_world(
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world=restored,
        expected_resolved_hash=system.resolved_hash,
        expected_catalog_hash=system.catalog_hash,
        expected_registry_hash=system.model_registry_hash,
    )
    restored.install_combat_system(restored_system)

    original_receipt = world.advance_tick(_tick_input(world, 0))
    restored_receipt = restored.advance_tick(_tick_input(restored, 0))

    assert restored_receipt == original_receipt
    assert restored.semantic_snapshot() == world.semantic_snapshot()


@pytest.mark.parametrize("ticks", (1, 10))
def test_world_tick_pipeline_consumes_explicit_motion_per_tick(ticks: int) -> None:
    world = _system().world
    for tick in range(ticks):
        receipt = world.advance_tick(_tick_input(world, tick))
        assert receipt.tick == tick + 1
        assert tuple(item.tick for item in receipt.dynamics_receipts) == (tick, tick)
        assert len({item.input_hash for item in receipt.dynamics_receipts}) == 2
    assert world.tick == world._spatial_tick == ticks
    assert world._spatial_time_seconds == pytest.approx(float(ticks))
    assert len(world.motion_ledger) == ticks


def test_big_tick_and_substeps_are_semantically_equivalent() -> None:
    big = _system().world
    small = _system().world
    with pytest.raises(ValueError):
        big.advance_tick(_tick_input(big, 0).model_copy(update={"steps": 10}))
    for tick in range(10):
        small.advance_tick(_tick_input(small, tick))
    assert big.tick == 0
    assert small.tick == 10
    assert len(small.motion_ledger) == 10


def test_tick_pipeline_failure_latches_append_only_world() -> None:
    world = _system().world
    tick_input = _tick_input(world, 0)
    world.lifecycle_fault_injector.fail_after_created_adapters = 1
    with pytest.raises(RuntimeError, match="injected World tick pipeline failure"):
        world.advance_tick(tick_input)
    assert world.failed_tick_operation_id == tick_input.operation_id


def test_world_tick_source_does_not_directly_assign_clocks_without_pipeline_work() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    assert "self.tick = target_tick" not in source
    assert "self._spatial_tick = target_tick" not in source


def test_multistep_tick_requires_fresh_provider_output_for_every_step() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert "motion_provider" not in api.WorldTickInputV2.model_fields
    assert "motion_candidates" not in api.WorldTickInputV2.model_fields
    assert "entity_commands" in api.WorldTickInputV2.model_fields
    world = _system().world
    receipts = [world.advance_tick(_tick_input(world, tick)) for tick in range(10)]
    assert [item.tick for receipt in receipts for item in receipt.dynamics_receipts] == [
        tick for tick in range(10) for _entity in range(2)
    ]
    assert (
        len({item.snapshot_hash for receipt in receipts for item in receipt.dynamics_receipts})
        == 20
    )


def test_tick_source_forbids_provider_receipt_reuse_escape_hatch() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    assert "_allow_tick_pipeline_provider_reuse" not in source


def test_world_tick_receipt_exposes_all_authoritative_stage_receipts() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    required = {
        "stage_order",
        "lifecycle_receipts",
        "motion_receipts",
        "event_receipts",
        "damage_receipts",
    }
    assert required.issubset(api.WorldTickReceiptV2.__annotations__)
    world = _system().world
    receipt = world.advance_tick(_tick_input(world, 0))
    assert receipt.stage_order == (
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


def _native_lifecycle_world(events: list[dict[str, Any]]) -> Any:
    from openmdbench.catalog.v2 import (
        CatalogResourceV2,
        CatalogV2,
        ModelFactoryMetadataV2,
        ModelRegistryV2,
    )
    from openmdbench.dynamics.native_v2 import (
        UAV_MODEL_REF,
        register_native_dynamics_models_v2,
    )
    from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
    from tests.contract import test_declarative_events_v2 as event_fixture

    resources = event_fixture._resources()
    dynamics = resources["dynamics"]
    data = dynamics.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
    data["model_id"] = UAV_MODEL_REF
    data["content"] = {
        **data["content"],
        "max_speed_mps": 80.0,
        "max_turn_rate_deg_s": 30.0,
        "max_vertical_speed_mps": 20.0,
        "max_acceleration_mps2": 8.0,
        "max_deceleration_mps2": 10.0,
        "min_altitude_m": 0.0,
        "max_altitude_m": 3000.0,
    }
    resources["dynamics"] = CatalogResourceV2(**data)
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.event-contract",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position_m": "m"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + "b" * 64,
            resource_types=(
                "platforms",
                "sensors",
                "effects",
                "damage_models",
                "environments",
            ),
            field_units={"position_m": "m"},
        ),
        lambda definition: definition,
    )
    register_native_dynamics_models_v2(registry)
    registry.freeze()
    catalog = CatalogV2(resources.values(), engine_version="2.0.0", model_registry=registry)
    package = ScenarioPackageV2.from_mapping(
        {
            "schema_version": "package@2.0",
            "scenario": event_fixture._scenario(events),
        }
    )
    resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
    return (
        importlib.import_module("openmdbench.world.factory_v2")
        .WorldFactoryV2(model_registry=registry)
        .build(resolved, session_id="session.lifecycle.native", seed=73)
    )


def test_tick_pipeline_consumes_pending_lifecycle_instead_of_rejecting() -> None:
    from tests.contract import test_world_lifecycle_v2 as lifecycle_fixture

    world = _native_lifecycle_world(lifecycle_fixture._spawn_events(1, tick=1))
    api = importlib.import_module("openmdbench.world.factory_v2")
    commands = list(_tick_input(world, 0).entity_commands)
    commands.append(
        api.EntityControlCommandV2(
            entity_id="future.asset.000",
            tick=0,
            controls={
                "target_speed_mps": 0.0,
                "target_heading_deg": 0.0,
                "target_vertical_m": 0.0,
            },
        )
    )
    tick_input = api.WorldTickInputV2(
        expected_tick=0,
        operation_id="world.tick.lifecycle-spawn",
        entity_commands=tuple(sorted(commands, key=lambda item: item.entity_id)),
        dt_seconds=1.0,
        steps=1,
    )
    receipt = world.advance_tick(tick_input)
    assert "future.asset.000" in world.entity_ids
    assert receipt.lifecycle_receipts[0].applied_event_ids == ("event.spawn.000",)
    assert world.controller_ownership is not None and world.capability_index is not None


def test_tick_checkpoint_roundtrip_preserves_tick_ledger_and_replay() -> None:
    system = _system()
    world = system.world
    tick_input = _tick_input(world, 0)
    receipt = world.advance_tick(tick_input)
    checkpoint = world.checkpoint()
    assert checkpoint.world_tick_ledger
    restored = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.advance_tick(tick_input) == receipt
    assert restored.checkpoint() == checkpoint


def test_tick_pipeline_source_executes_events_and_damage_in_one_transaction() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    for required in (
        "advance_lifecycle",
        "apply_damage_transaction",
        "event_receipts",
        "damage_receipts",
    ):
        assert required in source
    assert "omits pending lifecycle/event transition evidence" not in source


@pytest.mark.parametrize("stage", ("provider", "lifecycle", "event", "damage"))
def test_tick_stage_failure_latches_complete_world(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = _system().world
    tick_input = _tick_input(world, 0)
    method_name = {
        "provider": "_invoke_motion_provider",
        "lifecycle": "advance_lifecycle",
        "event": "_execute_typed_events",
        "damage": "apply_damage_transaction",
    }[stage]
    assert hasattr(type(world), method_name)

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(f"injected {stage} stage failure")

    monkeypatch.setattr(type(world), method_name, fail)
    with pytest.raises(RuntimeError, match=f"injected {stage} stage failure"):
        world.advance_tick(tick_input)
    assert world.failed_tick_operation_id == tick_input.operation_id


def test_world_tick_accepts_typed_controls_not_external_motion_authority() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    fields = api.WorldTickInputV2.model_fields
    assert "entity_commands" in fields
    assert "motion_provider" not in fields
    assert "motion_candidates" not in fields
    command_type = api.EntityControlCommandV2
    command = command_type(entity_id="asset.000", tick=0, controls={"throttle": 0.5})
    assert command.entity_id == "asset.000"


def test_native_step_receipt_binds_complete_adapter_and_tick_evidence() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    required = {
        "entity_id",
        "tick",
        "resource_ref",
        "model_ref",
        "adapter_instance_id",
        "artifact_hash",
        "manifest_hash",
        "input_hash",
        "output_hash",
        "snapshot_hash",
    }
    assert required.issubset(api.DynamicsStepReceiptV2.__annotations__)


@pytest.mark.parametrize(
    "tamper", ("entity", "tick", "resource", "model", "instance", "input", "output")
)
def test_forged_external_motion_or_receipt_is_rejected_before_clock(tamper: str) -> None:
    world = _system().world
    before = world.checkpoint()
    tick_input = _tick_input(world, 0)
    payload = tick_input.model_dump(mode="python")
    commands = [item.model_dump(mode="python") for item in tick_input.entity_commands]
    if tamper == "entity":
        commands[0]["entity_id"] = "asset.unknown"
    elif tamper == "tick":
        commands[0]["tick"] = 1
    else:
        commands[0][tamper + "_receipt"] = "sha256:" + "f" * 64
    payload["entity_commands"] = tuple(commands)
    with pytest.raises(
        (ValueError, importlib.import_module("openmdbench.world.factory_v2").FactoryErrorV2)
    ):
        world.advance_tick(tick_input.__class__(**payload))
    assert world.checkpoint() == before


def test_unknown_spatial_effect_chain_fails_before_tick_or_ledger_commit() -> None:
    world = _system().world
    before = world.checkpoint()
    assert hasattr(world, "spatial_effect_policy")
    with pytest.raises((AttributeError, TypeError)):
        world.spatial_effect_policy = "effect.unknown@2.0.0"
    assert world.checkpoint() == before


def test_tick_receipt_executes_all_typed_non_lifecycle_event_kinds() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert set(api.SUPPORTED_TICK_EVENT_TYPES) >= {
        "weather_change",
        "jamming_start",
        "jamming_end",
        "message",
        "apply_effect",
        "mission_marker",
    }
    assert "event_receipts" in api.WorldTickReceiptV2.__annotations__


def test_tick_pipeline_recomputes_active_dynamics_after_lifecycle_stage() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.world.factory_v2"))
    assert "active_dynamics_after_lifecycle" in source
    assert source.index("advance_lifecycle") < source.index("active_dynamics_after_lifecycle")
    assert "failed_no_rollback" in source


@pytest.mark.parametrize(
    ("event_type", "state_field"),
    (
        ("weather_change", "weather_state"),
        ("jamming_start", "jamming_sessions"),
        ("jamming_end", "jamming_sessions"),
        ("message", "message_queue"),
        ("component_suppression", "component_suppressions"),
        ("mission_marker", "mission_marker_ledger"),
        ("zone_activation", "zone_activation_state"),
        ("apply_effect", "effect_application_ledger"),
    ),
)
def test_typed_events_have_queryable_frozen_owner_state(event_type: str, state_field: str) -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert hasattr(api, "WorldEventStateSnapshotV2")
    assert state_field in api.WorldEventStateSnapshotV2.__annotations__
    world = _system().world
    assert hasattr(world, "event_state_snapshot")
    snapshot = world.event_state_snapshot()
    assert hasattr(snapshot, state_field)
    with pytest.raises((AttributeError, TypeError)):
        setattr(snapshot, state_field, {event_type: "forged"})


def test_event_dispatch_source_cannot_reduce_typed_payloads_to_identity_only() -> None:
    source = inspect.getsource(
        importlib.import_module("openmdbench.world.factory_v2").WorldStateV2._execute_typed_events
    )
    assert "_applied_tick_event_ids.add" not in source
    for owner in (
        "weather_state",
        "jamming_sessions",
        "message_queue",
        "component_suppressions",
        "mission_marker_ledger",
        "zone_activation",
        "effect_application_ledger",
    ):
        assert owner in source


def test_event_state_and_spatial_policy_are_checkpoint_integrity_bound() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    checkpoint_fields = api.WorldCheckpointV2.__annotations__
    assert "event_state" in checkpoint_fields
    assert "spatial_effect_policy" in checkpoint_fields
    world = _system().world
    checkpoint = world.checkpoint()
    assert checkpoint.event_state == world.event_state_snapshot()
    assert checkpoint.spatial_effect_policy == world.spatial_effect_policy


def test_spatial_effect_policy_is_resolved_typed_and_not_a_mutable_world_string() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert hasattr(api, "ResolvedSpatialEffectPolicyV2")
    world = _system().world
    policy = world.spatial_effect_policy
    assert policy is None or isinstance(policy, api.ResolvedSpatialEffectPolicyV2)
    if policy is not None:
        assert policy.effect_binding.exact_ref
        assert policy.damage_binding.exact_ref
        with pytest.raises((AttributeError, TypeError)):
            policy.effect_binding = None


def test_unresolved_spatial_damage_chain_fails_before_any_tick_commit() -> None:
    source = inspect.getsource(
        importlib.import_module("openmdbench.world.factory_v2").WorldStateV2._execute_typed_events
    )
    assert "unresolved.append" not in source
    assert "unresolved_damage_intent_ids" not in source
    assert "continue" not in source[source.index("for intent in motion_receipt.damage_intents") :]


def test_event_replay_duplicate_and_faults_are_transactionally_owned() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    receipt_fields = api.WorldTickReceiptV2.__annotations__
    assert "event_receipts" in receipt_fields
    assert hasattr(api, "TypedEventExecutionReceiptV2")
    annotations = api.TypedEventExecutionReceiptV2.__annotations__
    assert {
        "event_id",
        "event_type",
        "tick",
        "payload_hash",
        "owner_state_hash_before",
        "owner_state_hash_after",
    }.issubset(annotations)


def _scenario_with_spatial_damage_policy() -> tuple[Any, dict[str, Any]]:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog = resource_fixture._catalog()
    payload = resource_fixture._scenario()
    resources = resource_fixture._resources()
    payload["world"]["spatial_damage_policy"] = {
        "schema_version": "2.0",
        "collision_effect_ref": resources["effects"].exact_ref,
        "magnitude_model": "constant",
        "magnitude_parameters": {"value": 0.25},
        "output_unit": "1",
    }
    return catalog, payload


def test_spatial_damage_policy_must_be_explicit_not_inferred_from_unique_chain() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog = resource_fixture._catalog()
    implicit = resource_fixture._compile(catalog, resource_fixture._scenario())
    assert implicit.spatial_effect_policy is None
    source = inspect.getsource(importlib.import_module("openmdbench.scenarios.declarative_v2"))
    assert "_derive_spatial_effect_policy" not in source
    assert "if len(chains) != 1" not in source


def test_explicit_spatial_damage_policy_resolves_exact_typed_chain_and_roundtrips() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _scenario_with_spatial_damage_policy()
    resolved = resource_fixture._compile(catalog, payload)
    policy = resolved.spatial_effect_policy
    assert policy is not None
    assert (
        policy.effect_binding.exact_ref
        == payload["world"]["spatial_damage_policy"]["collision_effect_ref"]
    )
    assert policy.damage_binding.exact_ref == "damage.arbitrary@2.4.1"
    assert policy.magnitude_model == "constant"
    assert policy.magnitude_parameters == {"value": 0.25}
    assert policy.output_unit == "1"
    recovered = type(resolved).from_json(resolved.to_json())
    assert recovered == resolved
    assert recovered.resolved_hash == resolved.resolved_hash


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("collision_effect_ref", "effect.unknown@2.4.1"),
        ("collision_effect_ref", "damage.arbitrary@2.4.1"),
        ("magnitude_model", "speed_mps_as_damage"),
        ("magnitude_parameters", {"value": float("nan")}),
        ("output_unit", "m/s"),
    ),
)
def test_spatial_damage_policy_rejects_wrong_ref_type_model_unit_and_nonfinite(
    field: str, value: Any
) -> None:
    from openmdbench.scenarios.declarative_v2 import CompilerErrorV2
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _scenario_with_spatial_damage_policy()
    payload["world"]["spatial_damage_policy"][field] = value
    with pytest.raises(CompilerErrorV2):
        resource_fixture._compile(catalog, payload)


def test_impact_damage_evidence_is_typed_frozen_and_pre_response() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert hasattr(api, "ImpactDamageEvidenceV2")
    required = {
        "effect_ref",
        "damage_model_ref",
        "magnitude_model",
        "magnitude_parameters",
        "output_unit",
        "pre_impact_relative_velocity_mps",
        "source_mass_kg",
        "target_mass_kg",
        "time_fraction",
        "magnitude",
        "evidence_hash",
    }
    assert required.issubset(api.ImpactDamageEvidenceV2.__annotations__)


@pytest.mark.parametrize(
    ("model", "parameters", "relative_velocity", "expected"),
    (
        ("constant", {"value": 0.25}, (0.0, 0.0, 0.0), 0.25),
        ("scaled_relative_speed", {"scale": 0.1}, (3.0, 4.0, 0.0), 0.5),
        (
            "relative_kinetic_energy",
            {"scale": 0.01},
            (3.0, 4.0, 0.0),
            0.125,
        ),
    ),
)
def test_typed_impact_magnitude_models_use_pre_impact_inputs_and_canonical_units(
    model: str,
    parameters: dict[str, float],
    relative_velocity: tuple[float, float, float],
    expected: float,
) -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert hasattr(api, "ImpactMagnitudeModelV2")
    result = api.ImpactMagnitudeModelV2.evaluate(
        model=model,
        parameters=parameters,
        relative_velocity_mps=relative_velocity,
        source_mass_kg=1.0,
        target_mass_kg=1.0,
        output_unit="1",
    )
    assert result == pytest.approx(expected)


def test_collision_damage_source_uses_pre_impact_velocity_not_policy_response_velocity() -> None:
    boundary_source = inspect.getsource(
        importlib.import_module("openmdbench.world.boundary_v2").BoundarySystemV2.evaluate
    )
    assert "pre_impact_relative_velocity_mps" in boundary_source
    assert "ImpactMagnitudeModelV2" in boundary_source
    assert (
        "resolved_velocity_mps" not in boundary_source[boundary_source.index("DamageIntentV2(") :]
    )


def test_world_spatial_policy_owns_global_resource_closure_without_entities() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _scenario_with_spatial_damage_policy()
    payload["entities"] = []
    payload["formations"] = []
    resolved = resource_fixture._compile(catalog, payload)
    assert resolved.entities == ()
    assert hasattr(resolved, "world_resource_bindings")
    closure = resolved.world_resource_bindings
    assert tuple(item.exact_ref for item in closure) == (
        "damage.arbitrary@2.4.1",
        "effect.arbitrary@2.4.1",
    )
    assert resolved.spatial_effect_policy is not None
    assert resolved.spatial_effect_policy.effect_binding is closure[1]
    assert resolved.spatial_effect_policy.damage_binding is closure[0]


def test_zero_entity_collision_policy_builds_world_owned_combat_inventory_and_adapters() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _scenario_with_spatial_damage_policy()
    payload["entities"] = []
    payload["formations"] = []
    resolved = resource_fixture._compile(catalog, payload)
    world_api: Any = importlib.import_module("openmdbench.world.factory_v2")
    world = world_api.WorldFactoryV2(model_registry=catalog.model_registry).build(resolved)
    inventory = world.combat_inventory_snapshot()
    assert inventory.entity_ids == ()
    assert inventory.effect_refs == ("effect.arbitrary@2.4.1",)
    assert inventory.damage_model_refs == ("damage.arbitrary@2.4.1",)
    assert inventory.adapter_diagnostics["damage.arbitrary@2.4.1"].model_ref


@pytest.mark.parametrize(
    ("binding_name", "field", "value"),
    (
        ("effect_binding", "content_hash", "sha256:" + "0" * 64),
        ("effect_binding", "normalized_content", {"damage_model_ref": "damage.fake@2.0.0"}),
        ("effect_binding", "defaults", {"gain": {"value": 1.0}}),
        ("effect_binding", "units", {"magnitude": "m/s"}),
        ("effect_binding", "dependencies", []),
        ("effect_binding", "exact_ref", "effect.forged@2.4.1"),
        ("damage_binding", "resource_type", "effects"),
        ("damage_binding", "content", {"effect_types": ["forged"]}),
        (
            "damage_binding",
            "model_evidence",
            {"artifact_sha256": "sha256:" + "f" * 64},
        ),
    ),
)
def test_outer_rehash_cannot_forge_world_policy_resource_bindings(
    binding_name: str, field: str, value: Any
) -> None:
    import json

    from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _scenario_with_spatial_damage_policy()
    resolved = resource_fixture._compile(catalog, payload)
    encoded = json.loads(resolved.to_json())
    encoded["spatial_effect_policy"][binding_name][field] = value
    encoded["resolved_hash"] = ResolvedScenarioV2.compute_resolved_hash(encoded)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(json.dumps(encoded, sort_keys=True))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_world_resource_closure_rejects_duplicate_or_orphan_policy_bindings() -> None:
    source = inspect.getsource(importlib.import_module("openmdbench.scenarios.declarative_v2"))
    assert "world_resource_bindings" in source
    assert "duplicate world resource binding" in source
    assert "orphan world resource binding" in source
    assert "_validate_resource_binding_integrity" in source


def _zero_entity_policy_with_extra_dependency() -> tuple[Any, dict[str, Any]]:
    from openmdbench.catalog.v2 import CatalogResourceV2
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    def add_dependency(resources: dict[str, Any]) -> None:
        effect = resources["effects"]
        values = effect.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
        values["dependencies"] = (
            resources["damage_models"].exact_ref,
            resources["sensors"].exact_ref,
        )
        resources["effects"] = CatalogResourceV2(**values)

    catalog = resource_fixture._catalog(mutate=add_dependency)
    payload = resource_fixture._scenario()
    payload["entities"] = []
    payload["formations"] = []
    resources = resource_fixture._resources()
    payload["world"]["spatial_damage_policy"] = {
        "schema_version": "2.0",
        "collision_effect_ref": resources["effects"].exact_ref,
        "magnitude_model": "constant",
        "magnitude_parameters": {"value": 0.25},
        "output_unit": "1",
    }
    return catalog, payload


def test_world_resource_closure_recurses_all_catalog_dependencies_in_stable_order() -> None:
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    catalog, payload = _zero_entity_policy_with_extra_dependency()
    resolved = resource_fixture._compile(catalog, payload)
    assert tuple(item.exact_ref for item in resolved.world_resource_bindings) == (
        "damage.arbitrary@2.4.1",
        "effect.arbitrary@2.4.1",
        "sensor.arbitrary@2.4.1",
    )
    recovered = type(resolved).from_json(resolved.to_json())
    assert recovered.world_resource_bindings == resolved.world_resource_bindings
    assert recovered.resolved_hash == resolved.resolved_hash


def test_world_resource_closure_is_a_real_dependency_graph_not_two_hardcoded_bindings() -> None:
    module = importlib.import_module("openmdbench.scenarios.declarative_v2")
    assert hasattr(module, "resolve_world_resource_closure_v2")
    source = inspect.getsource(module.resolve_world_resource_closure_v2)
    for evidence in ("dependencies", "visiting", "visited", "cycle", "missing"):
        assert evidence in source
    assert "effect_binding, damage_binding" not in source


@pytest.mark.parametrize(
    "corruption",
    ("duplicate", "missing", "cycle", "orphan", "wrong_type", "model", "unit"),
)
def test_world_resource_closure_integrity_rejects_graph_corruption(corruption: str) -> None:
    import json

    module = importlib.import_module("openmdbench.scenarios.declarative_v2")
    catalog, payload = _scenario_with_spatial_damage_policy()
    payload["entities"] = []
    payload["formations"] = []
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    resolved = resource_fixture._compile(catalog, payload)
    encoded = json.loads(resolved.to_json())
    closure = encoded["world_resource_bindings"]
    if corruption == "duplicate":
        closure.append(dict(closure[0]))
    elif corruption == "missing":
        closure.pop(0)
    elif corruption == "cycle":
        closure[0]["dependencies"] = [closure[1]["exact_ref"]]
        closure[1]["dependencies"] = [closure[0]["exact_ref"]]
    elif corruption == "orphan":
        orphan = dict(closure[0])
        orphan["exact_ref"] = "damage.orphan@2.4.1"
        orphan["id"] = "damage.orphan"
        closure.append(orphan)
    elif corruption == "wrong_type":
        closure[0]["resource_type"] = "effects"
    elif corruption == "model":
        closure[0]["model_ref"] = "models.forged@2.0.0"
    else:
        closure[0]["units"] = {"magnitude": "fortnight"}
    encoded["resolved_hash"] = module.ResolvedScenarioV2.compute_resolved_hash(encoded)
    with pytest.raises(ValueError) as captured:
        module.ResolvedScenarioV2.from_json(json.dumps(encoded, sort_keys=True))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_world_checkpoint_owns_world_adapter_snapshots_receipts_and_ledger() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    fields = api.WorldCheckpointV2.__annotations__
    assert {
        "world_adapter_snapshots",
        "world_adapter_receipts",
        "world_adapter_ledger",
    }.issubset(fields)
    catalog, payload = _zero_entity_policy_with_extra_dependency()
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    resolved = resource_fixture._compile(catalog, payload)
    world = api.WorldFactoryV2(model_registry=catalog.model_registry).build(resolved)
    diagnostics = world.world_adapter_diagnostics
    assert tuple(diagnostics) == tuple(
        item.exact_ref for item in resolved.world_resource_bindings if item.model_ref
    )
    assert world.checkpoint().world_adapter_snapshots


def test_unified_tick_latches_stateful_world_adapter_failures_without_retry() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    assert hasattr(api, "WorldAdapterTransactionV2")
    source = inspect.getsource(api.WorldStateV2.advance_tick)
    assert "snapshot_world_adapters" not in source
    assert "restore_world_adapters_reverse" not in source
    assert "failed_no_rollback" in source
    assert "_tick_failure_operation_id" in source


def test_multiple_world_adapters_cleanup_and_restore_in_actual_reverse_creation_order() -> None:
    api = importlib.import_module("openmdbench.world.factory_v2")
    transaction = api.WorldAdapterTransactionV2.__annotations__
    assert {
        "created_adapter_ids",
        "restored_adapter_ids",
        "closed_adapter_ids",
        "failed_adapter_ids",
        "cleanup_errors",
    }.issubset(transaction)
    assert hasattr(api.WorldStateV2, "world_adapter_transaction_audit")

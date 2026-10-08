"""MD3-03 generic delayed surface-combat contract tests."""

from __future__ import annotations

import importlib
from typing import Any

import pytest


def _api() -> Any:
    return importlib.import_module("openmdbench.combat.v2")


def _surface_system(
    *,
    delivery_model: str = "delayed_effect",
    impact_delay_ticks: int = 1,
    energy_per_shot: float = 0.0,
) -> Any:
    """Build a synthetic, renamed surface case through the normal V2 compiler."""

    from openmdbench.catalog.v2 import (
        CatalogResourceV2,
        CatalogV2,
        ModelFactoryMetadataV2,
        ModelRegistryV2,
    )
    from openmdbench.dynamics.native_v2 import UAV_MODEL_REF, register_native_dynamics_models_v2
    from openmdbench.world.combat_evidence_v2 import WorldContactEvidenceV2, WorldRoeRuleV2
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
    from tests.contract import test_world_entity_factory_v2 as world_fixture

    resources = resource_fixture._resources()

    def replace(
        resource_type: str, content: dict[str, Any], *, model_id: str | None = None
    ) -> None:
        resource = resources[resource_type]
        data = resource.model_dump(mode="python", exclude={"exact_ref", "content_hash"})
        data["content"] = content
        if model_id is not None:
            data["model_id"] = model_id
        resources[resource_type] = CatalogResourceV2(**data)

    replace(
        "weapons",
        {
            **resources["weapons"].content,
            "target_domains": ["surface"],
            "hit_probability": 1.0,
            "delivery_model": delivery_model,
            "impact_delay_ticks": impact_delay_ticks,
            "cooldown_ticks": 2,
            "energy_per_shot": energy_per_shot,
        },
    )
    replace(
        "effects",
        {**resources["effects"].content, "magnitude": 0.4},
    )
    replace(
        "ammunition",
        {**resources["ammunition"].content, "mass_per_round_kg": 0.01},
    )
    replace(
        "dynamics",
        {
            "compatible_platform_types": ["stratospheric-relay"],
            "mobile": True,
            "max_speed_mps": 80.0,
            "max_turn_rate_deg_s": 30.0,
            "max_vertical_speed_mps": 20.0,
            "max_acceleration_mps2": 8.0,
            "max_deceleration_mps2": 10.0,
            "min_altitude_m": 0.0,
            "max_altitude_m": 3000.0,
        },
        model_id=UAV_MODEL_REF,
    )
    replace(
        "collision_shapes",
        {**resources["collision_shapes"].content, "compatible_domains": ["surface"]},
    )
    replace(
        "visualization_assets",
        {**resources["visualization_assets"].content, "compatible_domains": ["surface"]},
    )
    replace(
        "platforms",
        {**resources["platforms"].content, "domain": "surface"},
    )

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
        {"schema_version": "2.0", "id": "faction.defender"},
        {"schema_version": "2.0", "id": "faction.attacker"},
    ]
    payload["relationships"] = [
        {
            "schema_version": "2.0",
            "source_faction_id": "faction.defender",
            "target_faction_id": "faction.attacker",
            "relation": "hostile",
        }
    ]
    payload["entities"] = []
    for index in range(2):
        entity = resource_fixture._entity(rounds=10)
        entity["id"] = f"renamed.surface.{index:03d}"
        entity["faction_id"] = ("faction.defender", "faction.attacker")[index]
        entity["controller_slot"] = f"controller.renamed.{index:03d}"
        entity["target_domains"] = ["surface"]
        entity["initial_state"]["position_m"] = [float(index), 2.0, 3.0]
        entity["initial_state"]["energy"] = 1.0
        entity["initial_state"]["component_states"] = {"mode": "ready"}
        payload["entities"].append(entity)

    resolved = resource_fixture._compile(catalog, payload)
    world_factory = world_fixture._factories(catalog.model_registry)[1]
    world = world_factory.build(resolved)
    system = _api().CombatSystemV2.from_world(
        resolved=resolved,
        catalog_snapshot=_api().CombatCatalogSnapshotV2.from_resolved(resolved),
        model_registry=catalog.model_registry,
        world=world,
        expected_resolved_hash=resolved.resolved_hash,
        expected_catalog_hash=resolved.catalog_hash,
        expected_registry_hash=resolved.model_registry_hash,
    )
    world.install_contact_evidence(
        WorldContactEvidenceV2(
            evidence_id="contact.renamed.surface",
            owner_entity_id="renamed.surface.000",
            target_entity_id="renamed.surface.001",
            observed_tick=0,
            age_ticks=0,
            max_age_ticks=1,
            confidence=1.0,
            minimum_confidence=0.5,
            quality=1.0,
        )
    )
    world.install_roe_policy(
        WorldRoeRuleV2(
            rule_id="roe.renamed.surface",
            source_faction_id="faction.defender",
            target_faction_id="faction.attacker",
            relationship="hostile",
            engagement_permitted=True,
        )
    )
    world.install_combat_system(system)
    return system


def _request(**changes: Any) -> Any:
    values = {
        "request_id": "surface.request.001",
        "tick": 0,
        "attacker_id": "renamed.surface.000",
        "target_id": "renamed.surface.001",
        "weapon_ref": "weapon.arbitrary@2.4.1",
        "ammunition_ref": "round.arbitrary@2.4.1",
        "shots": 1,
        "authority_token": "authority.renamed.surface.000",
        "contact_evidence_id": "contact.renamed.surface",
    }
    values.update(changes)
    return _api().EngagementRequestV2(**values)


def _tick_input(world: Any, tick: int, *, requests: tuple[Any, ...] = ()) -> Any:
    from tests.contract.test_combat_damage_v2 import _tick_input as base_tick_input

    return base_tick_input(world, tick).model_copy(update={"engagement_requests": requests})


def _restore(system: Any, checkpoint: Any) -> Any:
    world = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    restored = _api().CombatSystemV2.from_world(
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world=world,
        expected_resolved_hash=system.resolved_hash,
        expected_catalog_hash=system.catalog_hash,
        expected_registry_hash=system.model_registry_hash,
    )
    world.install_combat_system(restored)
    return restored


def test_surface_delayed_effect_is_queued_at_launch_and_consumed_once_on_next_tick() -> None:
    system = _surface_system()
    world = system.world

    launch = world.advance_tick(_tick_input(world, 0, requests=(_request(),)))

    assert launch.combat_receipts[0].status == "executed"
    execution = launch.combat_receipts[0].execution
    assert execution.pending_impact_ids == ("impact:surface.request.001:000",)
    assert world.get("renamed.surface.001").domain == "surface"
    assert world.get("renamed.surface.001").state.health == pytest.approx(1.0)
    assert len(world.pending_impacts) == 1
    assert world.get("renamed.surface.000").state.ammunition["round.arbitrary@2.4.1"] == 9


def test_normalized_weapon_energy_allows_one_valid_shot_and_consumes_fraction() -> None:
    system = _surface_system(energy_per_shot=0.25)
    world = system.world

    receipt = world.advance_tick(_tick_input(world, 0, requests=(_request(),)))

    assert receipt.combat_receipts[0].status == "executed"
    assert world.get("renamed.surface.000").state.energy == pytest.approx(0.75)
    assert world.get("renamed.surface.000").state.ammunition["round.arbitrary@2.4.1"] == 9

    resolution = world.advance_tick(_tick_input(world, 1))

    assert world.pending_impacts == ()
    assert world.pending_impact_receipts[0].status == "hit"
    assert world.pending_impact_receipts[0].tick == 1
    assert world.get("renamed.surface.001").state.health == pytest.approx(0.6)
    assert resolution.damage_receipts[0].applied_intents[0].parameters["pending_impact_id"] == (
        "impact:surface.request.001:000"
    )

    repeated = world.advance_tick(_tick_input(world, 2))
    assert repeated.damage_receipts[0].applied_intents == ()
    assert len(world.pending_impact_receipts) == 1


def test_contact_detonation_uses_the_same_generic_pending_damage_authority() -> None:
    system = _surface_system(delivery_model="contact_detonation", impact_delay_ticks=1)
    world = system.world

    launch = world.advance_tick(_tick_input(world, 0, requests=(_request(),)))
    assert launch.combat_receipts[0].status == "executed"
    assert launch.combat_receipts[0].execution.pending_impact_ids == (
        "impact:surface.request.001:000",
    )
    assert world.pending_impacts[0].scheduled_tick == 1
    assert world.get("renamed.surface.001").state.health == pytest.approx(1.0)

    resolution = world.advance_tick(_tick_input(world, 1))
    assert world.pending_impacts == ()
    assert world.pending_impact_receipts[0].status == "hit"
    assert resolution.damage_receipts[0].applied_intents[0].source_kind == "weapon"


def test_delayed_impact_checkpoint_restore_preserves_single_future_resolution() -> None:
    system = _surface_system()
    execution = system.execute(_request(), expected_tick=0)
    checkpoint = system.world.checkpoint()

    assert execution.pending_impact_ids == ("impact:surface.request.001:000",)
    assert checkpoint.pending_impacts == system.world.pending_impacts
    restored = _restore(system, checkpoint)

    system.world.advance_tick(_tick_input(system.world, 0))
    restored.world.advance_tick(_tick_input(restored.world, 0))
    original_receipt = system.world.advance_tick(_tick_input(system.world, 1))
    restored_receipt = restored.world.advance_tick(_tick_input(restored.world, 1))

    assert original_receipt == restored_receipt
    assert system.world.pending_impacts == restored.world.pending_impacts == ()
    assert system.world.pending_impact_receipts == restored.world.pending_impact_receipts
    assert system.world.semantic_snapshot() == restored.world.semantic_snapshot()


def test_illegal_delayed_request_has_no_weapon_rng_or_pending_queue_side_effect() -> None:
    system = _surface_system()
    before = system.world.checkpoint()

    with pytest.raises(_api().CombatErrorV2) as captured:
        system.execute(_request(shots=11), expected_tick=0)

    assert captured.value.code == "combat.ammunition_denied"
    assert system.world.pending_impacts == ()
    assert system.world.pending_impact_receipts == ()
    assert system.world.checkpoint() == before

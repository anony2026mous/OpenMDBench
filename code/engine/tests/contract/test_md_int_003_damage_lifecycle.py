"""MD3-04 generic spatial trigger, wreck, and checkpoint contract tests."""

from __future__ import annotations

import importlib
import math
from typing import Any

import pytest


def _api() -> Any:
    return importlib.import_module("openmdbench.world.factory_v2")


def _trigger_system(
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_kind: str = "collision",
    source_lifecycle: str = "wreck",
    source_health: float = 0.4,
    exclude_secondary_target: bool = True,
) -> Any:
    """Compile a renamed collision trigger through the ordinary scenario path."""

    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
    from tests.contract import test_md_int_003_surface_combat as surface_fixture

    original_scenario = resource_fixture._scenario

    def scenario_with_trigger() -> dict[str, Any]:
        payload = original_scenario()
        payload["world"]["duration_ticks"] = 5
        trigger_payload: dict[str, Any] = {
            "source_kind": source_kind,
            "source_entity_ids": ["renamed.surface.000"],
            "effect_ref": "effect.arbitrary@2.4.1",
            "target_selector": {"entity_ids": ["renamed.surface.001"]},
            "source_lifecycle": source_lifecycle,
            "secondary_effect_ref": "effect.arbitrary@2.4.1",
            "secondary_probability": 1.0,
            "secondary_target_selector": (
                {
                    "entity_ids": ["renamed.surface.001"],
                    "exclude_entity_ids": ["renamed.surface.001"],
                }
                if exclude_secondary_target
                else {"entity_ids": ["renamed.surface.001"]}
            ),
        }
        if source_kind == "zone_entry":
            payload["world"]["zones"] = [
                {
                    "schema_version": "2.0",
                    "id": "zone.generic-core",
                    "geometry_type": "polygon",
                    "coordinates_m": [[2.5, 6.0], [3.5, 6.0], [3.5, 8.0], [2.5, 8.0]],
                }
            ]
            trigger_payload["zone_id"] = "zone.generic-core"
        payload["events"] = [
            {
                "schema_version": "2.0",
                "id": "event.arm.generic-collision-trigger",
                "event_type": "spatial_effect_trigger",
                "trigger": {"kind": "tick", "tick": 1},
                "payload": trigger_payload,
            }
        ]
        return payload

    monkeypatch.setattr(resource_fixture, "_scenario", scenario_with_trigger)
    system = surface_fixture._surface_system()
    # The trigger still uses an Effect/DamageIntent to destroy the source; this
    # lower initial health makes that data-defined effect terminal in the fixture.
    system.world._entities["renamed.surface.000"].state.health = source_health
    if source_kind == "zone_entry":
        system.world._entities["renamed.surface.001"].state.position_m = [100.0, 2.0, 3.0]
    return system


def _build_equivalent_system(system: Any, *, session_id: str, seed: int) -> Any:
    """Build the same resolved scenario with a distinct transport identity."""

    from openmdbench.combat.v2 import CombatSystemV2

    world = system.world_factory.build(
        system.resolved,
        session_id=session_id,
        seed=seed,
    )
    rebuilt = CombatSystemV2.from_world(
        resolved=system.resolved,
        catalog_snapshot=system.catalog_snapshot,
        model_registry=system.model_registry,
        world=world,
        expected_resolved_hash=system.resolved_hash,
        expected_catalog_hash=system.catalog_hash,
        expected_registry_hash=system.model_registry_hash,
    )
    world.install_combat_system(rebuilt)
    return rebuilt


def _surface_system_with_destroyed_policy(
    monkeypatch: pytest.MonkeyPatch,
    *,
    policy: str,
) -> Any:
    """Compile a normal weapon case whose entity policy is data-defined."""

    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
    from tests.contract import test_md_int_003_surface_combat as surface_fixture

    original_entity = resource_fixture._entity

    with monkeypatch.context() as scoped:

        def entity_with_policy(*args: Any, **kwargs: Any) -> dict[str, Any]:
            entity = original_entity(*args, **kwargs)
            entity["destroyed_lifecycle"] = policy
            return entity

        scoped.setattr(resource_fixture, "_entity", entity_with_policy)
        return surface_fixture._surface_system()


def _tick_input(world: Any, tick: int) -> Any:
    api = _api()
    commands = []
    for entity in world.entities_stable():
        if entity.state.lifecycle not in {"active", "degraded"}:
            continue
        reference = entity.definition.composition.dynamics_ref
        assert reference is not None
        velocity = tuple(entity.state.velocity_mps)
        commands.append(
            api.EntityControlCommandV2(
                entity_id=entity.id,
                tick=tick,
                controls={
                    "target_speed_mps": math.hypot(*velocity),
                    "target_heading_deg": float(entity.state.heading_deg),
                    "target_vertical_m": float(entity.state.position_m[2]),
                },
            )
        )
    return api.WorldTickInputV2(
        expected_tick=tick,
        operation_id=f"trigger.tick.{tick}",
        entity_commands=tuple(commands),
        dt_seconds=1.0,
    )


def _crossing_tick_input(world: Any, tick: int) -> Any:
    payload = _tick_input(world, tick)
    commands = []
    for command in payload.entity_commands:
        if command.entity_id == "renamed.surface.000":
            commands.append(
                command.model_copy(
                    update={
                        "controls": {
                            "target_speed_mps": 80.0,
                            "target_heading_deg": 90.0,
                            "target_vertical_m": 3.0,
                        }
                    }
                )
            )
        else:
            commands.append(command)
    return payload.model_copy(update={"entity_commands": tuple(commands)})


def _force_collision_start_state(world: Any) -> None:
    """Place the synthetic fixtures in an overlapping, zero-speed state.

    This is a contract fixture setup, not scenario-side state mutation: the
    following World tick remains the authority that produces collision evidence
    and applies damage.
    """

    for entity_id in ("renamed.surface.000", "renamed.surface.001"):
        entity = world._entities[entity_id]
        entity.state.position_m = [0.0, 2.0, 3.0]
        entity.state.velocity_mps = [0.0, 0.0, 0.0]


def _restore(system: Any, checkpoint: Any) -> Any:
    from openmdbench.combat.v2 import CombatSystemV2

    world = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    restored = CombatSystemV2.from_world(
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


def test_collision_trigger_is_one_shot_filters_secondary_and_creates_static_wreck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _trigger_system(monkeypatch)
    world = system.world

    arming = world.advance_tick(_tick_input(world, 0))
    assert arming.event_receipts[0].resolved_event_ids == ()
    assert world.spatial_effect_trigger_ledger == {}

    detonation = world.advance_tick(_tick_input(world, 1))
    ledger = world.spatial_effect_trigger_ledger
    assert len(ledger) == 1
    record = next(iter(ledger.values()))
    assert record["source_kind"] == "collision"
    assert record["lifecycle_status"] == "wreck"
    assert record["secondary"]["selected"] is True
    assert record["secondary"]["target_ids"] == ()
    assert len(record["primary_intent_ids"]) == 2
    assert world.get("renamed.surface.000").state.lifecycle == "destroyed"
    assert world.get("renamed.surface.001").state.health == pytest.approx(0.6)
    assert detonation.event_receipts[0].resolved_event_ids == (
        "event.arm.generic-collision-trigger",
    )
    assert (
        "event.arm.generic-collision-trigger"
        in world.mission_fact_snapshot(tick=world.tick).event_ids
    )
    assert any(
        intent.parameters["source_kind"] == "collision"
        for intent in detonation.damage_receipts[0].applied_intents
    )

    wreck_tick = world.advance_tick(_tick_input(world, 2))
    assert tuple(world.get("renamed.surface.000").state.position_m) == pytest.approx(
        (0.0, 2.0, 3.0)
    )
    assert any(
        {event.entity_a_id, event.entity_b_id} == {"renamed.surface.000", "renamed.surface.001"}
        for event in wreck_tick.motion_receipts[0].collision_events
    )
    subsystem = wreck_tick.subsystem_receipts[0]
    assert "renamed.surface.000" not in subsystem.communication.endpoint_ids
    assert all(contact.owner_entity_id != "renamed.surface.000" for contact in subsystem.contacts)
    assert len(world.spatial_effect_trigger_ledger) == 1


def test_checkpoint_restore_does_not_repeat_consumed_spatial_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _trigger_system(monkeypatch)
    world = system.world
    world.advance_tick(_tick_input(world, 0))
    world.advance_tick(_tick_input(world, 1))
    checkpoint = world.checkpoint()
    restored = _restore(system, checkpoint)

    original_receipt = world.advance_tick(_tick_input(world, 2))
    restored_receipt = restored.world.advance_tick(_tick_input(restored.world, 2))

    assert original_receipt == restored_receipt
    assert world.spatial_effect_trigger_ledger == restored.world.spatial_effect_trigger_ledger
    assert len(restored.world.spatial_effect_trigger_ledger) == 1
    assert restored.world.get("renamed.surface.000").state.lifecycle == "destroyed"


def test_nonterminal_collision_trigger_is_consumed_once_and_remains_consumed_after_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _trigger_system(monkeypatch, source_health=1.0)
    world = system.world

    world.advance_tick(_tick_input(world, 0))
    first = world.advance_tick(_tick_input(world, 1))
    assert first.motion_receipts[0].collision_events
    assert world.get("renamed.surface.000").state.lifecycle != "destroyed"
    assert len(world.spatial_effect_trigger_ledger) == 1
    assert len(world.spatial_effect_trigger_consumption) == 1

    _force_collision_start_state(world)
    repeated = world.advance_tick(_tick_input(world, 2))
    assert repeated.motion_receipts[0].collision_events
    assert len(world.spatial_effect_trigger_ledger) == 1
    assert len(world.spatial_effect_trigger_consumption) == 1

    restored = _restore(system, world.checkpoint())
    _force_collision_start_state(restored.world)
    after_restore = restored.world.advance_tick(_tick_input(restored.world, 3))
    assert after_restore.motion_receipts[0].collision_events
    assert len(restored.world.spatial_effect_trigger_ledger) == 1
    assert len(restored.world.spatial_effect_trigger_consumption) == 1


def test_secondary_sampling_is_session_identity_independent_and_checkpoint_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = _trigger_system(monkeypatch, exclude_secondary_target=False)
    first = _build_equivalent_system(template, session_id="session.alpha", seed=73)
    second = _build_equivalent_system(template, session_id="session.bravo", seed=73)
    for system in (first, second):
        system.world._entities["renamed.surface.000"].state.health = 0.4
        system.world.advance_tick(_tick_input(system.world, 0))

    first_receipt = first.world.advance_tick(_tick_input(first.world, 1))
    second_receipt = second.world.advance_tick(_tick_input(second.world, 1))
    # Provider receipts intentionally anchor a transport/session identity.  The
    # authoritative trigger/DamageIntent result and its own audit evidence must
    # nevertheless depend only on seed plus resolved source identity.
    assert first_receipt.damage_receipts == second_receipt.damage_receipts
    assert first_receipt.event_receipts == second_receipt.event_receipts
    assert first.world.spatial_effect_trigger_ledger == second.world.spatial_effect_trigger_ledger

    restored = _restore(first, first.world.checkpoint())
    assert restored.world.spatial_effect_trigger_ledger == first.world.spatial_effect_trigger_ledger
    assert (
        restored.world.spatial_effect_trigger_consumption
        == first.world.spatial_effect_trigger_consumption
    )


@pytest.mark.parametrize("policy", ("wreck", "despawn"))
def test_weapon_destroyed_lifecycle_follows_the_resolved_entity_policy(
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
) -> None:
    from tests.contract import test_md_int_003_surface_combat as surface_fixture

    system = _surface_system_with_destroyed_policy(monkeypatch, policy=policy)
    world = system.world
    target_id = "renamed.surface.001"
    world._entities[target_id].state.health = 0.4

    world.advance_tick(
        surface_fixture._tick_input(
            world,
            0,
            requests=(surface_fixture._request(),),
        )
    )
    impact = world.advance_tick(surface_fixture._tick_input(world, 1))
    assert impact.damage_receipts[0].results[0].lifecycle_after == "destroyed"
    record = world.destroyed_lifecycle_ledger[target_id]
    assert record["policy"] == policy
    if policy == "wreck":
        assert target_id in world.entity_ids
        assert world.get(target_id).state.lifecycle == "destroyed"
        assert record["status"] == "wreck"
    else:
        assert target_id not in world.entity_ids
        assert record["status"] == "despawned"
        assert world.tombstones[target_id].source_event_id == record["source_event_id"]

    restored = _restore(system, world.checkpoint())
    assert restored.world.destroyed_lifecycle_ledger == world.destroyed_lifecycle_ledger
    if policy == "wreck":
        assert restored.world.get(target_id).state.lifecycle == "destroyed"
        position = tuple(world.get(target_id).state.position_m)
        world.advance_tick(_tick_input(world, 2))
        assert tuple(world.get(target_id).state.position_m) == pytest.approx(position)
    else:
        assert target_id not in restored.world.entity_ids
        assert restored.world.tombstones[target_id].source_event_id == record["source_event_id"]


def test_high_speed_zone_entry_trigger_uses_continuous_crossing_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _trigger_system(monkeypatch, source_kind="zone_entry")
    world = system.world
    world.advance_tick(_tick_input(world, 0))

    detonation = world.advance_tick(_crossing_tick_input(world, 1))

    record = next(iter(world.spatial_effect_trigger_ledger.values()))
    assert record["source_kind"] == "zone_entry"
    assert 0.0 < record["time_fraction"] < 1.0
    assert tuple(record["source_position_m"]) == pytest.approx((2.5, 6.3301270189, 3.0))
    assert world.get("renamed.surface.000").state.lifecycle == "destroyed"
    assert any(
        transition.zone_id == "zone.generic-core" and transition.transition == "entered"
        for transition in world._mission_zone_transitions
    )
    assert detonation.damage_receipts[0].results


def test_spatial_trigger_data_can_despawn_a_destroyed_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system = _trigger_system(monkeypatch, source_lifecycle="despawn")
    world = system.world
    world.advance_tick(_tick_input(world, 0))
    world.advance_tick(_tick_input(world, 1))

    record = next(iter(world.spatial_effect_trigger_ledger.values()))
    assert record["lifecycle_status"] == "despawned"
    assert "renamed.surface.000" not in world.entity_ids
    assert world.tombstones["renamed.surface.000"].source_event_id == record["authority_event_id"]

    restored = _restore(system, world.checkpoint())
    assert "renamed.surface.000" not in restored.world.entity_ids
    assert restored.world.spatial_effect_trigger_ledger == world.spatial_effect_trigger_ledger

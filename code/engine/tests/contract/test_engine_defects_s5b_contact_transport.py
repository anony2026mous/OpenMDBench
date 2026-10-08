"""EF-06B contracts for transport-backed shared sensor tracks."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Any

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.world.combat_evidence_v2 import WorldContactEvidenceV2
from openmdbench.world.factory_v2 import WorldFactoryV2


def _world() -> tuple[Any, Any, Any, Any]:
    resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    factory = WorldFactoryV2(model_registry=catalog.model_registry)
    world = factory.build(resolved, session_id="session.s5b", seed=29)
    return world, factory, resolved, catalog


def _configure_transport(world: Any, *, range_m: float = 100_000.0, loss: float = 0.0) -> None:
    profile = {
        "compatible_platform_types": ["generic"],
        "slot_type": "communication",
        "range_m": range_m,
        "delay_s": 0.5,
        "ttl_s": 2.0,
        "loss_probability": loss,
        "max_relay_hops": 0,
    }
    for entity in world._entities.values():
        binding = entity.definition.resource_bindings["communications"][0]
        effective = replace(
            binding,
            content=MappingProxyType(dict(profile)),
            normalized_content=MappingProxyType(dict(profile)),
        )
        groups = dict(entity.definition.resource_bindings)
        groups["communications"] = (effective,)
        entity.definition = replace(entity.definition, resource_bindings=MappingProxyType(groups))


def _contact(world: Any) -> WorldContactEvidenceV2:
    return WorldContactEvidenceV2(
        evidence_id="sensor.contact.unit.guard.shore.01.unit.raid.usv.01",
        owner_entity_id="unit.guard.shore.01",
        target_entity_id="unit.raid.usv.01",
        observed_tick=0,
        age_ticks=0,
        max_age_ticks=10,
        confidence=0.9,
        minimum_confidence=0.5,
        quality=0.8,
        measurement_position_m=tuple(world.get("unit.raid.usv.01").state.position_m),
        source_sensor_ref="sensor.shore-surface-radar@2.1.0",
    )


def test_shared_track_is_delayed_snapshot_idempotent_and_checkpointed() -> None:
    world, factory, resolved, catalog = _world()
    _configure_transport(world)
    contact = _contact(world)
    world._enqueue_shared_contact_transport((contact,), tick=0, dt_seconds=1.0)
    world._enqueue_shared_contact_transport((contact,), tick=0, dt_seconds=1.0)

    queue = world.event_state_snapshot().shared_contact_queue
    assert len(queue) == 1
    assert queue[0]["transport_status"] == "queued"
    assert queue[0]["scheduled_delivery_tick"] == 1
    snapshot_position = tuple(queue[0]["contact_snapshot"]["estimated_position_m"])
    target = world._entities["unit.raid.usv.01"]
    target.state = replace(target.state, position_m=(99_999.0, 99_999.0, 0.0))

    checkpoint = world.checkpoint()
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=catalog.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_session_id=world.session_id,
        expected_seed=29,
    )
    _configure_transport(restored)
    restored._advance_shared_contact_transport(tick=1)
    observation = restored.controller_observation_snapshot(controller_slot_id="controller.defence")

    assert len(observation.shared_contacts) == 1
    assert tuple(observation.shared_contacts[0]["estimated_position_m"]) == snapshot_position
    assert observation.shared_contacts[0]["delivered_tick"] == 1
    assert (
        restored.event_state_snapshot().shared_contact_queue[0]["transport_status"] == "delivered"
    )


def test_missing_route_loss_and_jamming_never_publish_shared_tracks() -> None:
    world, _factory, _resolved, _catalog = _world()
    contact = _contact(world)

    _configure_transport(world, range_m=1.0)
    world._enqueue_shared_contact_transport((contact,), tick=0, dt_seconds=1.0)
    assert all(
        item["transport_status"] == "blocked"
        for item in world.event_state_snapshot().shared_contact_queue
    )
    assert (
        world.controller_observation_snapshot(
            controller_slot_id="controller.defence"
        ).shared_contacts
        == ()
    )

    world, _factory, _resolved, _catalog = _world()
    _configure_transport(world, loss=1.0)
    world._enqueue_shared_contact_transport((contact,), tick=0, dt_seconds=1.0)
    assert all(
        item["transport_status"] == "dropped"
        for item in world.event_state_snapshot().shared_contact_queue
    )

    world, _factory, _resolved, _catalog = _world()
    _configure_transport(world)
    world._enqueue_shared_contact_transport((contact,), tick=0, dt_seconds=1.0)
    endpoint = "unit.guard.usv.01"
    world._jamming_sessions["jam.receiver"] = MappingProxyType({"target_entity_id": endpoint})
    world._advance_shared_contact_transport(tick=1)
    assert all(
        item["transport_status"] == "blocked"
        for item in world.event_state_snapshot().shared_contact_queue
    )
    assert (
        world.controller_observation_snapshot(
            controller_slot_id="controller.defence"
        ).shared_contacts
        == ()
    )

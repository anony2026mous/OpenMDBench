"""MD3-06 generic modifier and tick-quantized transport contracts."""

from __future__ import annotations

import importlib
import math
from dataclasses import replace
from types import MappingProxyType
from typing import Any

import pytest


def test_capability_modifier_order_expiry_and_availability_clamp() -> None:
    api = importlib.import_module("openmdbench.world.capability_modifier_v2")
    modifiers = (
        api.CapabilityModifierV2("modifier.multiply", "sensor.range", "multiply", 0.5, priority=1),
        api.CapabilityModifierV2(
            "modifier.add", "sensor.range", "add", 2.0, priority=2, inactive_from_tick=3
        ),
        api.CapabilityModifierV2(
            "modifier.floor", "sensor.range", "multiply", 0.1, priority=3, floor=1.0
        ),
    )
    resolved = api.resolve_capability_v2(
        capability="sensor.range", base_value=10.0, tick=2, modifiers=modifiers
    )
    assert resolved.value == pytest.approx(1.0)
    assert resolved.applied_modifier_ids == ("modifier.multiply", "modifier.add", "modifier.floor")
    assert api.resolve_capability_v2(
        capability="sensor.range", base_value=10.0, tick=3, modifiers=modifiers
    ).value == pytest.approx(1.0)
    assert (
        api.resolve_capability_v2(
            capability="sensor.range", base_value=10.0, tick=2, modifiers=modifiers, suppressed=True
        ).value
        == 0.0
    )


def test_transport_quantizes_nonzero_delay_and_preserves_ttl_boundary() -> None:
    api = importlib.import_module("openmdbench.world.communication_transport_v2")
    assert api.quantize_delay_ticks_v2(delay_seconds=0.0, physics_dt_seconds=1.0) == 0
    assert api.quantize_delay_ticks_v2(delay_seconds=0.001, physics_dt_seconds=1.0) == 1
    delivered = api.schedule_transport_v2(
        message_id="message.any",
        origin_tick=5,
        ttl_ticks=1,
        delay_seconds=0.5,
        physics_dt_seconds=1.0,
        link_available=True,
    )
    assert delivered.status == "queued"
    assert delivered.delivery_tick == delivered.expiry_tick == 6
    assert (
        api.schedule_transport_v2(
            message_id="message.expired",
            origin_tick=5,
            ttl_ticks=0,
            delay_seconds=0.5,
            physics_dt_seconds=1.0,
            link_available=True,
        ).status
        == "expired"
    )
    assert (
        api.schedule_transport_v2(
            message_id="message.blocked",
            origin_tick=5,
            ttl_ticks=5,
            delay_seconds=0.0,
            physics_dt_seconds=1.0,
            link_available=False,
        ).status
        == "blocked"
    )


def _configure_effective_communication_profile(world: Any) -> None:
    profile = {
        "compatible_platform_types": ["stratospheric-relay"],
        "slot_type": "communication",
        "range_m": 100.0,
        "delay_s": 0.5,
        "ttl_s": 1.0,
        "loss_probability": 0.0,
    }
    for entity in world._entities.values():
        binding = entity.definition.resource_bindings["communications"][0]
        effective_binding = replace(
            binding,
            content=MappingProxyType(dict(profile)),
            normalized_content=MappingProxyType(dict(profile)),
        )
        groups = dict(entity.definition.resource_bindings)
        groups["communications"] = (effective_binding,)
        entity.definition = replace(
            entity.definition,
            resource_bindings=MappingProxyType(groups),
        )
    return None


def _world_with_effective_communication_profile() -> Any:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    system = combat_fixture._system(trusted_evidence=False)
    _configure_effective_communication_profile(system.world)
    return system


def test_world_transport_is_checkpointed_and_delivers_only_at_quantized_tick() -> None:
    system = _world_with_effective_communication_profile()
    world = system.world
    api = importlib.import_module("openmdbench.world.factory_v2")
    world._apply_message_intents(
        (
            api.MessageIntentV2(
                message_id="message.delayed",
                sender_entity_id="asset.000",
                recipient_entity_id="asset.001",
                tick=0,
                payload="audit-only payload",
            ),
        ),
        tick=0,
        dt_seconds=1.0,
    )
    queued = world.event_state_snapshot().message_queue[-1]
    assert queued["transport_status"] == "queued"
    assert queued["route"] == ("asset.000", "asset.001")
    assert queued["relay_hops"] == 0
    checkpoint = world.checkpoint()
    restored = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_session_id=world.session_id,
        expected_seed=world._session_seed,
    )
    _configure_effective_communication_profile(restored)
    assert restored.event_state_snapshot().message_queue[-1]["transport_status"] == "queued"
    restored._advance_message_transport(tick=1)
    delivered = restored.event_state_snapshot().message_queue[-1]
    assert delivered["transport_status"] == "delivered"
    assert delivered["delivered_tick"] == 1


def test_world_capability_pipeline_reaches_weapon_and_suppression_without_scenario_branch() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    system = combat_fixture._system(hit_probability=0.8)
    world = system.world
    weapon_ref = world._entities["asset.000"].definition.resource_bindings["weapons"][0].exact_ref
    world._weather_state = {
        "current": MappingProxyType(
            {
                "environment_binding": MappingProxyType(
                    {
                        "exact_ref": "environment.generic-weather@2.0.0",
                        "normalized_content": MappingProxyType(
                            {"weapon_hit_probability_multiplier": 0.5}
                        ),
                    }
                )
            }
        ),
        "event_id": "event.environment.any",
        "active_from_tick": 0,
    }
    world.install_combat_system(system)
    assert system._effective_hit_probability(
        attacker_id="asset.000",
        weapon_ref=weapon_ref,
        base_probability=0.8,
        tick=0,
    ) == pytest.approx(0.4)
    world._component_suppressions[f"asset.000|{weapon_ref}"] = {
        "active_from_tick": 0,
        "expires_tick": 1,
        "payload": MappingProxyType({}),
    }
    assert (
        system._effective_hit_probability(
            attacker_id="asset.000",
            weapon_ref=weapon_ref,
            base_probability=0.8,
            tick=0,
        )
        == 0.0
    )


def test_queued_transport_is_not_delivered_after_route_is_jammed() -> None:
    system = _world_with_effective_communication_profile()
    world = system.world
    api = importlib.import_module("openmdbench.world.factory_v2")
    world._apply_message_intents(
        (
            api.MessageIntentV2(
                message_id="message.jammed-before-delivery",
                sender_entity_id="asset.000",
                recipient_entity_id="asset.001",
                tick=0,
                payload="must not replay",
            ),
        ),
        tick=0,
        dt_seconds=1.0,
    )
    world._jamming_sessions["jam.generic"] = MappingProxyType({"target_entity_id": "asset.001"})
    world._advance_message_transport(tick=1)
    assert world.event_state_snapshot().message_queue[-1]["transport_status"] == "blocked"


def test_generic_sensor_profile_enforces_period_domain_and_named_measurement_noise() -> None:
    api = importlib.import_module("openmdbench.systems.generic_v2")
    sensor = {
        "exact_ref": "sensor.generic-surface@2.1.0",
        "range_m": 200.0,
        "detection_probability": 1.0,
        "range_noise_fraction": 0.10,
        "bearing_noise_deg": 3.0,
        "update_ticks": 2,
        "confirmation_frames": 2,
        "stale_after_ticks": 3,
        "engagement_max_age_ticks": 10,
        "minimum_contact_confidence": 0.70,
        "target_domains": ("surface",),
    }
    owner = api.SubsystemEntityFactV2(
        entity_id="entity.owner",
        faction_id="faction.alpha",
        position_m=(0.0, 0.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
        energy=None,
        domain="surface",
        sensors=(sensor,),
    )
    target = api.SubsystemEntityFactV2(
        entity_id="entity.target",
        faction_id="faction.beta",
        position_m=(0.0, 100.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
        energy=None,
        domain="surface",
    )
    engine = api.GenericSubsystemEngineV2()

    assert (
        engine.evaluate(
            entities=(owner, target), tick=1, dt_seconds=1.0, seed=11, queued_message_count=0
        ).contacts
        == ()
    )
    first = engine.evaluate(
        entities=(owner, target), tick=2, dt_seconds=1.0, seed=11, queued_message_count=0
    )
    reordered = engine.evaluate(
        entities=(target, owner), tick=2, dt_seconds=1.0, seed=11, queued_message_count=0
    )
    assert first == reordered
    contact = first.contacts[0]
    assert contact.detected
    assert contact.update_ticks == 2
    assert contact.confirmation_frames == 2
    assert contact.stale_after_ticks == 3
    assert contact.engagement_max_age_ticks == 10
    assert contact.minimum_contact_confidence == pytest.approx(0.70)
    assert contact.measurement_rng_substream == contact.rng_substream + ":measurement"
    assert contact.measurement_position_m is not None
    assert contact.measurement_position_m != contact.target_position_m
    assert contact.measurement_range_m is not None
    assert abs(contact.measurement_range_m - contact.distance_m) <= 10.0

    non_surface = replace(target, domain="air")
    assert (
        engine.evaluate(
            entities=(owner, non_surface), tick=2, dt_seconds=1.0, seed=11, queued_message_count=0
        ).contacts
        == ()
    )
    with pytest.raises(ValueError, match="update_ticks"):
        engine.evaluate(
            entities=(replace(owner, sensors=({**sensor, "update_ticks": 0},)), target),
            tick=2,
            dt_seconds=1.0,
            seed=11,
            queued_message_count=0,
        )


def _configure_effective_sensor_profile(world: Any) -> None:
    profile = {
        "compatible_platform_types": ["stratospheric-relay"],
        "slot_type": "sensor",
        "range_m": 100.0,
        "detection_probability": 1.0,
        "range_noise_fraction": 0.10,
        "bearing_noise_deg": 3.0,
        "update_ticks": 1,
        "confirmation_frames": 2,
        "stale_after_ticks": 3,
        "engagement_max_age_ticks": 10,
        "minimum_contact_confidence": 0.70,
        "target_domains": ["upper-atmosphere"],
        "high_sea_range_multiplier": 0.75,
    }
    for entity in world._entities.values():
        binding = entity.definition.resource_bindings["sensors"][0]
        effective_binding = replace(
            binding,
            content=MappingProxyType(dict(profile)),
            normalized_content=MappingProxyType(dict(profile)),
        )
        groups = dict(entity.definition.resource_bindings)
        groups["sensors"] = (effective_binding,)
        entity.definition = replace(
            entity.definition,
            resource_bindings=MappingProxyType(groups),
        )
    return None


def test_environment_data_applies_profile_specific_range_and_generic_loss_additive() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    system = combat_fixture._system(trusted_evidence=False)
    world = system.world
    _configure_effective_sensor_profile(world)
    _configure_effective_communication_profile(world)
    world._weather_state = {
        "current": MappingProxyType(
            {
                "environment_binding": MappingProxyType(
                    {
                        "exact_ref": "environment.any@2.1.0",
                        "normalized_content": MappingProxyType(
                            {
                                "sensor_range_multiplier": 1.0,
                                "communication_loss_multiplier": 1.0,
                                "communication_loss_additive": 0.05,
                                "sensor_profile_multiplier_keys": MappingProxyType(
                                    {"sensor.range": "high_sea_range_multiplier"}
                                ),
                            }
                        ),
                    }
                )
            }
        ),
        "event_id": "event.environment.any",
        "active_from_tick": 0,
    }
    entity = world._entities["asset.000"]
    sensor = world._profile_with_capability_modifiers(
        entity=entity,
        role="sensors",
        binding=entity.definition.resource_bindings["sensors"][0],
        tick=0,
    )
    communication = world._communication_profile(entity=entity, tick=0)
    assert sensor["range_m"] == pytest.approx(75.0)
    assert communication is not None
    assert communication["loss_probability"] == pytest.approx(0.05)


def _world_tick_input(world: Any, *, operation_id: str) -> Any:
    api = importlib.import_module("openmdbench.world.factory_v2")
    commands = tuple(
        api.EntityControlCommandV2(
            entity_id=entity.id,
            tick=world.tick,
            controls={
                "target_speed_mps": math.hypot(*entity.state.velocity_mps),
                "target_heading_deg": float(entity.state.heading_deg),
                "target_vertical_m": float(entity.state.position_m[2]),
            },
        )
        for entity in world.entities_stable()
        if entity.state.lifecycle in {"active", "degraded"}
        and entity.definition.composition.dynamics_ref is not None
    )
    return api.WorldTickInputV2(
        expected_tick=world.tick,
        operation_id=operation_id,
        entity_commands=commands,
        dt_seconds=1.0,
    )


def test_world_fuses_measurements_before_publication_and_restores_pending_confirmation() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    system = combat_fixture._system(trusted_evidence=False)
    world = system.world
    _configure_effective_sensor_profile(world)
    world.advance_tick(_world_tick_input(world, operation_id="sensor.tick.0"))
    first_record = next(iter(world.contact_store.records.values()))[0]
    assert not first_record.confirmed
    assert (
        world.observation_snapshot(observer_faction_id="coalition.alpha").contacts_by_faction[
            "coalition.alpha"
        ]
        == ()
    )

    checkpoint = world.checkpoint()
    restored = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_session_id=world.session_id,
        expected_seed=world._session_seed,
    )
    _configure_effective_sensor_profile(restored)
    world.advance_tick(_world_tick_input(world, operation_id="sensor.tick.1"))
    restored.advance_tick(_world_tick_input(restored, operation_id="sensor.tick.1"))

    assert restored.contact_store.records == world.contact_store.records
    record = next(iter(world.contact_store.records.values()))[0]
    assert record.confirmed and record.confirmation_count == 2
    observation = world.observation_snapshot(observer_faction_id="coalition.alpha")
    contact = observation.contacts_by_faction["coalition.alpha"][0]
    assert contact["estimated_position_m"] == record.measurement_position_m
    encoded = observation.model_dump_json()
    assert "target_entity_id" not in encoded
    assert "measurement_rng_substream" not in encoded

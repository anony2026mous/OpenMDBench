"""EF-06D contracts for bounded, controller-scoped delivered-message inboxes."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Any, cast

import pytest
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.sessions.lifecycle_v2 import SendMessagePayloadV2, SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from pydantic import ValidationError


def _session() -> Any:
    return (
        create_formal_session_v2("MD-INT-003-EASY", session_id="session.s5d", seed=37)
        .load()
        .start()
    )


def _configure_transport(world: Any) -> None:
    profile = {
        "compatible_platform_types": ["generic"],
        "slot_type": "communication",
        "range_m": 100_000.0,
        "delay_s": 0.5,
        "ttl_s": 2.0,
        "loss_probability": 0.0,
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


def _defence_authority(session: Any) -> str:
    return cast(
        str,
        next(
            token
            for token, grant in session.world_view.authority_tokens.items()
            if grant.controller_id == "agent.defence" and len(grant.entity_ids) > 1
        ),
    )


def test_send_message_reaches_only_explicit_controller_inbox_after_transport_delay() -> None:
    session = _session()
    try:
        _configure_transport(session._world)
        action = DiscreteActionV2(
            schema_version="2.0",
            action_id="message.private",
            action_type="send_message",
            entity_id="unit.guard.usv.01",
            faction_id="faction.defender",
            based_on_tick=0,
            valid_until_tick=1,
            payload={
                "recipient_controller_slots": ["controller.attack"],
                "message": "private transport payload",
            },
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.message.private",
                idempotency_key="idem.message.private",
                faction_id="faction.defender",
                based_on_tick=0,
                valid_until_tick=1,
                discrete_actions=(action,),
            ),
            authority_token=_defence_authority(session),
            operation_id="submit.message.private",
            expected_tick=0,
        )
        session.step(operation_id="tick.message.0", expected_tick=0)
        assert (
            session.world_view.controller_observation(
                controller_slot_id="controller.attack"
            ).received_messages
            == ()
        )
        session.step(operation_id="tick.message.1", expected_tick=1)
        received = session.world_view.controller_observation(
            controller_slot_id="controller.attack"
        ).received_messages
        assert len(received) == 1
        assert received[0]["origin_message_id"] == "message.private"
        assert received[0]["payload"] == "private transport payload"
        assert received[0]["delivered_tick"] == 1
        assert (
            session.world_view.controller_observation(
                controller_slot_id="controller.defence"
            ).received_messages
            == ()
        )
        checkpoint = session.checkpoint()
        resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
        restored = SessionLifecycleV2.restore(
            checkpoint=checkpoint,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=resolved,
            expected_resolved_hash=resolved.resolved_hash,
            model_registry=catalog.model_registry,
            expected_model_registry_hash=resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        )
        assert (
            restored.world_view.controller_observation(
                controller_slot_id="controller.attack"
            ).received_messages
            == received
        )
        restored.stop().close()
    finally:
        session.stop().close()


def test_sender_receives_message_only_when_explicitly_listed_as_recipient() -> None:
    session = _session()
    try:
        _configure_transport(session._world)
        action = DiscreteActionV2(
            schema_version="2.0",
            action_id="message.self-explicit",
            action_type="send_message",
            entity_id="unit.guard.usv.01",
            faction_id="faction.defender",
            based_on_tick=0,
            valid_until_tick=1,
            payload={
                "recipient_controller_slots": ["controller.defence"],
                "message": "explicit self delivery",
            },
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.message.self-explicit",
                idempotency_key="idem.message.self-explicit",
                faction_id="faction.defender",
                based_on_tick=0,
                valid_until_tick=1,
                discrete_actions=(action,),
            ),
            authority_token=_defence_authority(session),
            operation_id="submit.message.self-explicit",
            expected_tick=0,
        )
        session.step(operation_id="tick.message.self-explicit.0", expected_tick=0)
        session.step(operation_id="tick.message.self-explicit.1", expected_tick=1)
        received = session.world_view.controller_observation(
            controller_slot_id="controller.defence"
        ).received_messages
        assert len(received) == 1
        assert received[0]["payload"] == "explicit self delivery"
        transport = session._world.event_state_snapshot().message_queue[0]
        assert transport["zero_hop"] is True
        assert transport["route"] == ("unit.guard.usv.01",)
    finally:
        session.stop().close()


def test_inbox_is_read_only_idempotent_and_evicts_stably_at_declared_capacity() -> None:
    session = _session()
    try:
        world = session._world
        _configure_transport(world)
        for index in range(257):
            world._deliver_message_to_inboxes(
                {
                    "message_id": f"message.{index:03d}",
                    "origin_message_id": f"origin.{index:03d}",
                    "sender_entity_id": "unit.guard.usv.01",
                    "recipient_controller_slots": ("controller.attack",),
                    "generated_tick": 0,
                    "delivered_tick": 1,
                    "expiry_tick": 100,
                    "payload": str(index),
                }
            )
        first = world.controller_observation_snapshot(controller_slot_id="controller.attack")
        second = world.controller_observation_snapshot(controller_slot_id="controller.attack")
        assert first.received_messages == second.received_messages
        assert len(first.received_messages) == 256
        assert first.received_messages[0]["message_id"] == "message.001"
        assert (
            world.event_state_snapshot().inbox_evictions[-1]["event_type"]
            == "communication.inbox_evicted"
        )
        before = len(first.received_messages)
        world._deliver_message_to_inboxes(
            {
                "message_id": "message.256",
                "origin_message_id": "origin.256",
                "sender_entity_id": "unit.guard.usv.01",
                "recipient_controller_slots": ("controller.attack",),
                "generated_tick": 0,
                "delivered_tick": 1,
                "expiry_tick": 100,
                "payload": "duplicate",
            }
        )
        assert (
            len(
                world.controller_observation_snapshot(
                    controller_slot_id="controller.attack"
                ).received_messages
            )
            == before
        )
    finally:
        session.stop().close()


def test_message_payload_and_scope_are_schema_bounded() -> None:
    with pytest.raises(ValidationError):
        SendMessagePayloadV2(recipient_id="entity.any", message="x" * 4097)
    with pytest.raises(ValidationError):
        SendMessagePayloadV2(
            recipient_id="entity.any",
            recipient_controller_slots=("controller.any",),
            message="ambiguous",
        )

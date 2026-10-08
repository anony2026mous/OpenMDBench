"""EF-06C contracts for controller command delivery through transport."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Any, cast

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2, PersistentCommandV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2


def _session() -> Any:
    return (
        create_formal_session_v2("MD-INT-003-EASY", session_id="session.s5c", seed=31)
        .load()
        .start()
    )


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


def _authority(session: Any) -> str:
    return cast(
        str,
        next(
            token
            for token, grant in session.world_view.authority_tokens.items()
            if grant.controller_id == "agent.defence" and len(grant.entity_ids) > 1
        ),
    )


def _navigation(session: Any, *, entity_id: str, command_id: str) -> ActionBatchV2:
    command = PersistentCommandV2(
        schema_version="2.0",
        command_id=command_id,
        command_type="navigation",
        entity_id=entity_id,
        faction_id="faction.defender",
        based_on_tick=0,
        valid_until_tick=2,
        payload={"speed_mps": 8.0, "heading_deg": 90.0},
    )
    return ActionBatchV2(
        schema_version="2.0",
        session_id=session.session_id,
        batch_id=f"batch.{command_id}",
        idempotency_key=f"idem.{command_id}",
        faction_id="faction.defender",
        based_on_tick=0,
        valid_until_tick=2,
        persistent_commands=(command,),
    )


def test_remote_navigation_waits_for_delayed_delivery_while_zero_hop_applies_at_boundary() -> None:
    session = _session()
    try:
        _configure_transport(session._world)
        remote = _navigation(session, entity_id="unit.guard.usv.02", command_id="remote.delay")
        session.submit_actions(
            batch=remote,
            authority_token=_authority(session),
            operation_id="submit.remote",
            expected_tick=0,
        )
        first = session.step(operation_id="tick.remote.0", expected_tick=0)
        assert first.activated_command_ids == ()
        assert (
            session._world.event_state_snapshot().command_queue[0]["transport_status"] == "queued"
        )

        second = session.step(operation_id="tick.remote.1", expected_tick=1)
        assert second.activated_command_ids == ("remote.delay",)
        assert (
            session._world.event_state_snapshot().command_queue[0]["transport_status"]
            == "delivered"
        )

        local = _navigation(session, entity_id="unit.guard.usv.01", command_id="local.zero-hop")
        # Submit at the current CAS tick and prove the declared endpoint controls itself zero-hop.
        local = local.model_copy(
            update={
                "based_on_tick": 2,
                "valid_until_tick": 3,
                "persistent_commands": (
                    local.persistent_commands[0].model_copy(
                        update={"based_on_tick": 2, "valid_until_tick": 3}
                    ),
                ),
            }
        )
        session.submit_actions(
            batch=local,
            authority_token=_authority(session),
            operation_id="submit.local",
            expected_tick=2,
        )
        third = session.step(operation_id="tick.local.2", expected_tick=2)
        assert third.activated_command_ids == ("local.zero-hop",)
        assert any(item["zero_hop"] for item in session._world.event_state_snapshot().command_queue)
    finally:
        session.stop().close()


def test_blocked_and_dropped_remote_commands_do_not_apply_side_effects() -> None:
    session = _session()
    try:
        _configure_transport(session._world, range_m=1.0)
        batch = _navigation(session, entity_id="unit.guard.usv.02", command_id="remote.blocked")
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id="submit.blocked",
            expected_tick=0,
        )
        blocked = session.step(operation_id="tick.blocked", expected_tick=0)
        assert blocked.activated_command_ids == ()
        child = next(item for item in blocked.child_receipts if item.child_id == "remote.blocked")
        assert child.error_code == "communication.command_blocked"

        session.stop().close()
        session = _session()
        _configure_transport(session._world, loss=1.0)
        attacker = "unit.guard.usv.02"
        weapon_ref = (
            session.world_view.get(attacker).definition.resource_bindings["weapons"][0].exact_ref
        )
        before_ammunition = dict(session.world_view.get(attacker).state.ammunition)
        before_rng = tuple(session._world._combat_rng_state)
        fire = DiscreteActionV2(
            schema_version="2.0",
            action_id="remote.dropped.fire",
            action_type="fire_weapon",
            entity_id=attacker,
            faction_id="faction.defender",
            based_on_tick=0,
            valid_until_tick=1,
            payload={"weapon_ref": weapon_ref, "target_id": "unit.raid.usv.01"},
        )
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id="batch.remote.dropped.fire",
                idempotency_key="idem.remote.dropped.fire",
                faction_id="faction.defender",
                based_on_tick=0,
                valid_until_tick=1,
                discrete_actions=(fire,),
            ),
            authority_token=_authority(session),
            operation_id="submit.dropped.fire",
            expected_tick=0,
        )
        dropped = session.step(operation_id="tick.dropped.fire", expected_tick=0)
        assert (
            session._world.event_state_snapshot().command_queue[0]["transport_status"] == "dropped"
        )
        child = next(item for item in dropped.child_receipts if item.child_id == fire.action_id)
        assert child.error_code == "communication.command_dropped"
        assert dict(session.world_view.get(attacker).state.ammunition) == before_ammunition
        assert tuple(session._world._combat_rng_state) == before_rng
    finally:
        if session.state.value in {"loaded", "running", "paused"}:
            session.stop().close()


def test_pending_remote_command_survives_checkpoint_without_duplicate_delivery() -> None:
    session = _session()
    try:
        _configure_transport(session._world)
        batch = _navigation(session, entity_id="unit.guard.usv.02", command_id="remote.restore")
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id="submit.restore",
            expected_tick=0,
        )
        before = session.step(operation_id="tick.restore.0", expected_tick=0)
        assert before.activated_command_ids == ()
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
        assert restored._world is not None
        _configure_transport(restored._world)
        after = restored.step(operation_id="tick.restore.1", expected_tick=1)
        assert after.activated_command_ids == ("remote.restore",)
        assert len(restored._world.event_state_snapshot().command_queue) == 1
        restored.stop().close()
    finally:
        if session.state.value in {"loaded", "running", "paused"}:
            session.stop().close()

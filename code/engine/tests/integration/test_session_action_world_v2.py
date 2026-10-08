"""RF-08 real Resolved -> Session -> World action-pipeline integration contracts."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2, PersistentCommandV2
from openmdbench.sessions.lifecycle_v2 import (
    ActionChildReceiptV2,
    RunnerModeV2,
    SessionCheckpointV2,
    SessionFailureV2,
    SessionLifecycleV2,
    SessionStateV2,
)


def _session(identifier: str = "session.arbitrary", *, seed: int = 41) -> SessionLifecycleV2:
    from tests.contract import test_combat_damage_v2 as fixture

    system = fixture._system()
    return SessionLifecycleV2.create(
        session_id=identifier,
        seed=seed,
        resolved=system.resolved,
        expected_resolved_hash=system.resolved_hash,
        catalog_hash=system.catalog_hash,
        model_registry_hash=system.model_registry_hash,
        world_factory=system.world_factory,
        runner_mode=RunnerModeV2.LOCKSTEP,
        physics_dt_seconds=1.0,
        decision_interval_ticks=1,
    )


def _authority(session: SessionLifecycleV2, entity_id: str = "asset.000") -> str:
    return next(
        token
        for token, grant in session.world_view.authority_tokens.items()
        if grant.entity_id == entity_id
    )


def _batch(
    session: SessionLifecycleV2,
    *,
    batch_id: str = "batch.001",
    idempotency_key: str = "idem.001",
    command_id: str = "command.navigation.001",
    action_id: str = "action.fire.001",
    valid_until_tick: int = 2,
) -> ActionBatchV2:
    return ActionBatchV2(
        schema_version="2.0",
        session_id=session.session_id,
        batch_id=batch_id,
        idempotency_key=idempotency_key,
        faction_id="coalition.alpha",
        based_on_tick=session.world_view.tick,
        valid_until_tick=valid_until_tick,
        persistent_commands=(
            PersistentCommandV2(
                schema_version="2.0",
                command_id=command_id,
                command_type="navigation",
                entity_id="asset.000",
                faction_id="coalition.alpha",
                based_on_tick=session.world_view.tick,
                valid_until_tick=valid_until_tick,
                payload={"speed_mps": 20.0, "heading_deg": 45.0},
            ),
        ),
        discrete_actions=(
            DiscreteActionV2(
                schema_version="2.0",
                action_id=action_id,
                action_type="fire_weapon",
                entity_id="asset.000",
                faction_id="coalition.alpha",
                based_on_tick=session.world_view.tick,
                valid_until_tick=valid_until_tick,
                payload={
                    "weapon_ref": "weapon.arbitrary@2.4.1",
                    "target_id": "asset.001",
                },
            ),
        ),
    )


def _tick(session: SessionLifecycleV2, operation_id: str) -> Any:
    tick = session.world_view.tick
    return session.step(
        operation_id=operation_id,
        expected_tick=tick,
    )


def test_real_session_lifecycle_state_version_and_invalid_transitions() -> None:
    session = _session().load()
    assert session.state is SessionStateV2.LOADED
    session.start().pause().resume().stop().close()
    assert session.state.value == SessionStateV2.CLOSED.value
    with pytest.raises(SessionFailureV2) as captured:
        session.start()
    assert captured.value.code == "session.transition_invalid"


def test_submit_idempotency_and_operation_fingerprint_conflicts_are_state_neutral() -> None:
    session = _session().load().start()
    batch = _batch(session)
    token = _authority(session)
    first = session.submit_actions(
        batch=batch, authority_token=token, operation_id="submit.001", expected_tick=0
    )
    before = session.world_view.checkpoint()
    assert (
        session.submit_actions(
            batch=batch, authority_token=token, operation_id="submit.001", expected_tick=0
        )
        is first
    )
    with pytest.raises(SessionFailureV2) as captured:
        session.submit_actions(
            batch=batch.model_copy(update={"batch_id": "batch.changed"}),
            authority_token=token,
            operation_id="submit.001",
            expected_tick=0,
        )
    assert captured.value.code == "session.operation_conflict"
    assert session.world_view.checkpoint() == before


def test_concurrent_identical_submissions_have_one_fingerprint_and_receipt() -> None:
    session = _session().load().start()
    batch = _batch(session)
    token = _authority(session)

    def submit(_index: int) -> Any:
        return session.submit_actions(
            batch=batch,
            authority_token=token,
            operation_id="submit.concurrent",
            expected_tick=0,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        receipts = tuple(executor.map(submit, range(100)))
    assert all(item is receipts[0] for item in receipts)
    assert len(session.queue_view.operation_ledger) == 1


def test_batch_with_one_invalid_child_is_atomically_rejected_without_partial_queue() -> None:
    session = _session().load().start()
    batch = _batch(session)
    invalid = batch.discrete_actions[0].model_copy(update={"entity_id": "entity.unknown"})
    batch = batch.model_copy(update={"discrete_actions": (invalid,)})
    with pytest.raises(SessionFailureV2):
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id="submit.partial-invalid",
            expected_tick=0,
        )
    assert session.queue_view.operation_ledger == ()
    assert session.queue_view.persistent_commands == ()


def test_persistent_command_survives_empty_ticks_and_discrete_action_executes_once() -> None:
    session = _session().load().start()
    session.submit_actions(
        batch=_batch(session),
        authority_token=_authority(session),
        operation_id="submit.persist-fire",
        expected_tick=0,
    )
    first = _tick(session, "tick.000")
    second = _tick(session, "tick.001")
    assert first.activated_command_ids == ("command.navigation.001",)
    assert first.consumed_discrete_action_ids == ("action.fire.001",)
    assert second.consumed_discrete_action_ids == ()
    assert tuple(item.command_id for item in session.queue_view.persistent_commands) == (
        "command.navigation.001",
    )


def test_discrete_fire_is_dispatched_to_world_combat_not_only_marked_consumed() -> None:
    session = _session().load().start()
    session.submit_actions(
        batch=_batch(session),
        authority_token=_authority(session),
        operation_id="submit.combat",
        expected_tick=0,
    )
    receipt = _tick(session, "tick.combat")
    assert receipt.consumed_discrete_action_ids == ("action.fire.001",)
    assert receipt.world_receipt.combat_receipts
    assert receipt.world_receipt.damage_receipts


def test_expired_command_falls_back_to_explicit_safe_hold() -> None:
    session = _session().load().start()
    session.submit_actions(
        batch=_batch(session, valid_until_tick=0),
        authority_token=_authority(session),
        operation_id="submit.expiring",
        expected_tick=0,
    )
    _tick(session, "tick.expiring.0")
    receipt = _tick(session, "tick.expiring.1")
    assert receipt.expired_command_ids == ("command.navigation.001",)
    assert receipt.fallback_command_ids == ("fallback.safe_hold.asset.000",)


def test_controller_and_entity_lifecycle_are_revalidated_at_apply_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session().load().start()
    batch = _batch(session)
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session),
        operation_id="submit.lifecycle",
        expected_tick=0,
    )
    before = session.world_view.checkpoint()
    original_get = session.world_view.get_optional
    monkeypatch.setattr(
        session.world_view,
        "get_optional",
        lambda entity_id: None if entity_id == "asset.000" else original_get(entity_id),
    )
    with pytest.raises(SessionFailureV2) as captured:
        _tick(session, "tick.lifecycle")
    assert captured.value.code in {
        "session.entity_lifecycle_invalid",
        "session.controller_authority_invalid",
    }
    assert session.world_view.checkpoint() == before


def test_world_failure_does_not_snapshot_and_ends_append_only_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected tick failure is terminal instead of restoring prior state."""

    session = _session().load().start()
    world = session._mutable_world()

    def fail_subsystems(*, tick: int, dt_seconds: float) -> Any:
        raise RuntimeError(f"injected generic-subsystem failure at tick {tick} / {dt_seconds}")

    with monkeypatch.context() as patch:
        patch.setattr(world, "checkpoint", lambda: (_ for _ in ()).throw(AssertionError()))
        patch.setattr(
            world,
            "snapshot_world_adapters",
            lambda: (_ for _ in ()).throw(AssertionError()),
        )
        patch.setattr(world, "_evaluate_generic_subsystems", fail_subsystems)
        with pytest.raises(RuntimeError, match="injected generic-subsystem failure"):
            _tick(session, "tick.world-no-rollback")

    assert world.failed_tick_operation_id == "tick.world-no-rollback"
    assert session.state is SessionStateV2.STOPPED


def test_post_mission_failure_latches_world_without_runtime_rollback_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late pipeline failure cannot permit a partially advanced World to resume."""

    session = _session().load().start()
    world = session._mutable_world()
    world.lifecycle_fault_injector.fail_after_created_adapters = 1
    try:
        with monkeypatch.context() as patch:
            patch.setattr(world, "checkpoint", lambda: (_ for _ in ()).throw(AssertionError()))
            with pytest.raises(RuntimeError, match="injected World tick pipeline failure"):
                _tick(session, "tick.post-mission-no-rollback")
    finally:
        world.lifecycle_fault_injector.fail_after_created_adapters = None

    assert world.failed_tick_operation_id == "tick.post-mission-no-rollback"
    assert session.state is SessionStateV2.STOPPED


def test_runtime_capability_loss_keeps_control_contract_but_rejects_future_actions() -> None:
    """Damage-induced degradation must not invalidate immutable controller evidence."""

    session = _session().load().start()
    world = session._mutable_world()
    entity = world._entities["asset.000"]
    entity.capabilities = frozenset()
    entity.capability_tokens = ()

    world._refresh_controller_ownership()

    assert world.controller_ownership.by_entity("asset.000")
    with pytest.raises(SessionFailureV2) as captured:
        session.submit_actions(
            batch=_batch(session),
            authority_token=_authority(session),
            operation_id="submit.degraded-capability",
            expected_tick=0,
        )
    assert captured.value.code == "session.capability_missing"


def test_execution_queue_fingerprint_excludes_append_only_audit_history() -> None:
    session = _session().load().start()
    actions = session._require_actions()
    before = actions._execution_queue_fingerprint()

    actions._statuses["audit-only"] = "executed"
    actions._child_ledger["audit-only"] = ActionChildReceiptV2(
        child_id="audit-only",
        kind="fallback",
        status="active",
        tick=0,
    )

    assert actions._execution_queue_fingerprint() == before
    assert actions.checkpoint_evidence()["child_ledger"]


def test_checkpoint_restore_n_plus_m_preserves_actions_and_exactly_once_ledger() -> None:
    session = _session().load().start()
    batch = _batch(session)
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session),
        operation_id="submit.checkpoint",
        expected_tick=0,
    )
    _tick(session, "tick.checkpoint.0")
    checkpoint = session.checkpoint()
    restored = SessionLifecycleV2.restore(
        checkpoint=checkpoint,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        resolved=session.resolved,
        expected_resolved_hash=session.resolved.resolved_hash,
        model_registry=session.world_factory._model_registry,
        expected_model_registry_hash=session.model_registry_hash,
        world_factory=session.world_factory,
    )
    assert restored.queue_view.consumed_discrete_action_ids == ("action.fire.001",)
    assert _tick(restored, "tick.checkpoint.1") == _tick(session, "tick.checkpoint.1")


def test_checkpoint_nested_tamper_and_outer_rehash_still_requires_external_anchor() -> None:
    session = _session().load().start()
    checkpoint = session.checkpoint()
    payload = json.loads(checkpoint.model_dump_json())
    payload["consumed_discrete_action_ids"] = ["action.forged"]
    payload["checkpoint_hash"] = SessionCheckpointV2.compute_hash(payload)
    forged = SessionCheckpointV2.model_validate(payload)
    with pytest.raises(SessionFailureV2) as captured:
        SessionLifecycleV2.restore(
            checkpoint=forged,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=session.resolved,
            expected_resolved_hash=session.resolved.resolved_hash,
            model_registry=session.world_factory._model_registry,
            expected_model_registry_hash=session.model_registry_hash,
            world_factory=session.world_factory,
        )
    assert captured.value.code == "session.restore_anchor_invalid"


def test_two_sessions_are_isolated_by_session_id_seed_world_and_action_ledgers() -> None:
    first = _session("session.first", seed=11).load().start()
    second = _session("session.second", seed=12).load().start()
    first.submit_actions(
        batch=_batch(first),
        authority_token=_authority(first),
        operation_id="submit.first",
        expected_tick=0,
    )
    _tick(first, "tick.first")
    assert second.world_view.tick == 0
    assert second.queue_view.consumed_discrete_action_ids == ()
    assert first.world_view.session_id != second.world_view.session_id
    first.stop().close()
    assert second.state is SessionStateV2.RUNNING


def test_replay_load_is_read_only_and_does_not_initialize_world_or_actions() -> None:
    session = _session()
    session.runner_mode = RunnerModeV2.REPLAY
    session.load()
    assert session.state is SessionStateV2.LOADED
    with pytest.raises(SessionFailureV2) as world_error:
        _ = session.world_view
    with pytest.raises(SessionFailureV2) as action_error:
        _ = session.queue_view
    assert world_error.value.code == "session.world_unavailable"
    assert action_error.value.code == "session.actions_unavailable"


def test_child_identity_is_session_global_and_binds_content_across_batches() -> None:
    session = _session().load().start()
    token = _authority(session)
    first = _batch(session, batch_id="batch.first", idempotency_key="idem.first")
    session.submit_actions(
        batch=first,
        authority_token=token,
        operation_id="submit.child.first",
        expected_tick=0,
    )
    same_child_changed_batch = _batch(
        session,
        batch_id="batch.second",
        idempotency_key="idem.second",
    )
    with pytest.raises(SessionFailureV2) as captured:
        session.submit_actions(
            batch=same_child_changed_batch,
            authority_token=token,
            operation_id="submit.child.second",
            expected_tick=0,
        )
    assert captured.value.code == "session.child_id_conflict"


@pytest.mark.parametrize(
    ("command_type", "payload"),
    (
        ("sensor_mode", {}),
        ("relay_mode", {}),
        ("ciws_auto", {"enabled": True}),
    ),
)
def test_unwired_persistent_type_fails_at_submit_never_becomes_active(
    command_type: str, payload: dict[str, Any]
) -> None:
    session = _session().load().start()
    batch = _batch(session)
    command = batch.persistent_commands[0].model_copy(
        update={"command_type": command_type, "payload": payload}
    )
    batch = batch.model_copy(update={"persistent_commands": (command,), "discrete_actions": ()})
    with pytest.raises(SessionFailureV2):
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id=f"submit.unwired.{command_type}",
            expected_tick=0,
        )
    assert session.queue_view.persistent_commands == ()


@pytest.mark.parametrize(
    ("action_type", "payload"),
    (
        ("release_payload", {}),
        ("device_action", {}),
        ("ram", {}),
    ),
)
def test_unwired_discrete_type_fails_at_submit_never_becomes_executed(
    action_type: str, payload: dict[str, Any]
) -> None:
    session = _session().load().start()
    batch = _batch(session)
    action = batch.discrete_actions[0].model_copy(
        update={"action_type": action_type, "payload": payload}
    )
    batch = batch.model_copy(update={"persistent_commands": (), "discrete_actions": (action,)})
    with pytest.raises(SessionFailureV2):
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id=f"submit.unwired.{action_type}",
            expected_tick=0,
        )
    assert session.queue_view.consumed_discrete_action_ids == ()


def test_send_message_dispatches_to_world_communication_stage_exactly_once() -> None:
    session = _session("session.message").load().start()
    batch = _batch(session)
    action = batch.discrete_actions[0].model_copy(
        update={
            "action_type": "send_message",
            "payload": {"recipient_id": "asset.001", "message": "status"},
        }
    )
    batch = batch.model_copy(update={"persistent_commands": (), "discrete_actions": (action,)})
    session.submit_actions(
        batch=batch,
        authority_token=_authority(session),
        operation_id="submit.message",
        expected_tick=0,
    )
    first = _tick(session, "tick.message.0")
    second = _tick(session, "tick.message.1")
    assert first.consumed_discrete_action_ids == ("action.fire.001",)
    messages = session.world_view.checkpoint().event_state.message_queue
    assert len(messages) == 1
    assert messages[0]["message_id"] == "action.fire.001"
    assert messages[0]["link_available"] is False
    assert messages[0]["transport_status"] == "blocked"
    assert second.consumed_discrete_action_ids == ()


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"speed_mps": float("nan")},
        {"speed_mps": 10.0, "heading_deg": 0.0, "fortnight": 1.0},
        {"speed_mps": "fast", "heading_deg": 0.0},
    ),
)
def test_navigation_payload_missing_nonfinite_extra_or_wrong_unit_type_rejects(
    payload: dict[str, Any],
) -> None:
    session = _session().load().start()
    batch = _batch(session)
    command = batch.persistent_commands[0].model_copy(update={"payload": payload})
    batch = batch.model_copy(update={"persistent_commands": (command,), "discrete_actions": ()})
    with pytest.raises(SessionFailureV2) as captured:
        session.submit_actions(
            batch=batch,
            authority_token=_authority(session),
            operation_id="submit.bad-payload",
            expected_tick=0,
        )
    assert captured.value.code == "session.payload_invalid"

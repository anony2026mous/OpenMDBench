"""RF-08 generic SessionLifecycleV2 and authoritative action-pipeline contracts."""

from __future__ import annotations

import importlib
import inspect
from typing import Any

import pytest
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2, PersistentCommandV2
from pydantic import ValidationError


def _api() -> Any:
    return importlib.import_module("openmdbench.sessions.lifecycle_v2")


def _persistent(index: int, *, tick: int = 0, ttl: int = 2) -> PersistentCommandV2:
    return PersistentCommandV2(
        schema_version="2.0",
        command_id=f"command.{index:03d}",
        command_type="navigation",
        entity_id=f"entity.{index:03d}",
        faction_id="faction.arbitrary",
        based_on_tick=tick,
        valid_until_tick=tick + ttl,
        payload={"speed_mps": 10.0, "heading_deg": 90.0},
    )


def _discrete(index: int, *, tick: int = 0, ttl: int = 1) -> DiscreteActionV2:
    return DiscreteActionV2(
        schema_version="2.0",
        action_id=f"action.{index:03d}",
        action_type="fire_weapon",
        entity_id=f"entity.{index:03d}",
        faction_id="faction.arbitrary",
        based_on_tick=tick,
        valid_until_tick=tick + ttl,
        payload={"weapon_ref": "weapon.arbitrary@2.0.0", "target_id": "target.any"},
    )


def _batch(count: int, *, tick: int = 0) -> ActionBatchV2:
    return ActionBatchV2(
        schema_version="2.0",
        session_id="session.arbitrary",
        batch_id=f"batch.{count:03d}",
        idempotency_key=f"idempotency.{count:03d}",
        faction_id="faction.arbitrary",
        based_on_tick=tick,
        valid_until_tick=tick + 2,
        persistent_commands=tuple(_persistent(index, tick=tick) for index in range(count)),
        discrete_actions=tuple(_discrete(index, tick=tick) for index in range(count)),
    )


def test_public_session_v2_exports_state_machine_queue_runner_and_checkpoint() -> None:
    api = _api()
    assert {
        "SessionLifecycleV2",
        "SessionStateV2",
        "ActionPipelineV2",
        "ActionReceiptV2",
        "SessionCheckpointV2",
        "SessionErrorV2",
        "RunnerModeV2",
    }.issubset(set(api.__all__))


def test_session_state_machine_has_exact_authoritative_transitions() -> None:
    api = _api()
    expected = {
        "created": ("loaded", "closed"),
        "loaded": ("running", "stopped", "closed"),
        "running": ("paused", "stopped"),
        "paused": ("running", "stopped", "closed"),
        "stopped": ("closed",),
        "closed": (),
    }
    assert expected == api.SESSION_TRANSITIONS_V2
    assert tuple(item.value for item in api.SessionStateV2) == tuple(expected)


def test_session_constructor_requires_all_reproducibility_and_trust_anchors() -> None:
    api = _api()
    parameters = inspect.signature(api.SessionLifecycleV2.create).parameters
    assert {
        "session_id",
        "seed",
        "resolved",
        "expected_resolved_hash",
        "catalog_hash",
        "model_registry_hash",
        "world_factory",
        "runner_mode",
        "physics_dt_seconds",
        "decision_interval_ticks",
    }.issubset(parameters)


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_action_batch_supports_arbitrary_cardinality_and_canonical_order(count: int) -> None:
    batch = _batch(count)
    assert len(batch.persistent_commands) == count
    assert len(batch.discrete_actions) == count
    assert tuple(item.command_id for item in batch.persistent_commands) == tuple(
        f"command.{index:03d}" for index in range(count)
    )


def test_action_batch_rejects_duplicate_cross_kind_ids_and_invalid_child_window() -> None:
    command = _persistent(0)
    action = _discrete(0).model_copy(update={"action_id": command.command_id})
    with pytest.raises(ValidationError):
        ActionBatchV2(
            schema_version="2.0",
            session_id="session.arbitrary",
            batch_id="batch.duplicate",
            idempotency_key="idem.duplicate",
            faction_id="faction.arbitrary",
            based_on_tick=0,
            valid_until_tick=2,
            persistent_commands=(command,),
            discrete_actions=(action,),
        )
    with pytest.raises(ValidationError):
        _batch(1).model_copy(
            update={"persistent_commands": (_persistent(0, tick=3),)}
        ).model_validate(
            _batch(1).model_dump(mode="json")
            | {"persistent_commands": [_persistent(0, tick=3).model_dump(mode="json")]}
        )


def test_action_pipeline_submit_is_enqueue_only_and_tick_writer_is_explicit() -> None:
    api = _api()
    submit = inspect.signature(api.ActionPipelineV2.submit).parameters
    apply_tick = inspect.signature(api.ActionPipelineV2.apply_tick).parameters
    assert {"batch", "authority_token", "operation_id", "expected_tick"}.issubset(submit)
    assert {"expected_tick", "world_tick_input", "operation_id"}.issubset(apply_tick)
    assert "world" not in submit


def test_pipeline_freezes_controller_schema_capability_lifecycle_and_faction_checks() -> None:
    api = _api()
    assert api.ACTION_VALIDATION_ORDER_V2 == (
        "session_state",
        "operation_fingerprint",
        "tick_window",
        "controller_authority",
        "entity_lifecycle",
        "faction_ownership",
        "action_schema",
        "required_capability",
        "payload",
    )


def test_persistent_and_discrete_lifecycle_statuses_are_controlled() -> None:
    api = _api()
    assert tuple(item.value for item in api.PersistentCommandStatusV2) == (
        "queued",
        "accepted",
        "active",
        "completed",
        "replaced",
        "expired",
        "cancelled",
        "failed",
    )
    assert tuple(item.value for item in api.DiscreteActionStatusV2) == (
        "queued",
        "accepted",
        "applied",
        "executed",
        "rejected",
    )


def test_idempotency_fingerprint_binds_batch_session_tick_and_payload() -> None:
    api = _api()
    fingerprint = api.action_batch_fingerprint_v2(_batch(1))
    assert fingerprint.startswith("sha256:") and len(fingerprint) == 71
    assert api.action_batch_fingerprint_v2(_batch(1)) == fingerprint
    changed = _batch(1).model_copy(update={"idempotency_key": "different"})
    assert api.action_batch_fingerprint_v2(changed) != fingerprint


def test_session_step_uses_only_world_unified_append_only_tick() -> None:
    api = _api()
    source = inspect.getsource(api.SessionLifecycleV2.step)
    assert "actions.apply_tick" in source
    assert "append-only in-memory" in source
    assert "ends this match" in source
    assert "world.tick =" not in source
    assert "_spatial_tick =" not in source


def test_checkpoint_contains_command_ledgers_persistent_state_and_consumed_discrete_ids() -> None:
    api = _api()
    fields = api.SessionCheckpointV2.model_fields
    assert {
        "session_id",
        "session_state",
        "seed",
        "resolved_hash",
        "catalog_hash",
        "model_registry_hash",
        "world_checkpoint_hash",
        "persistent_commands",
        "consumed_discrete_action_ids",
        "operation_ledger",
        "rng_state_hash",
        "checkpoint_hash",
    }.issubset(fields)


def test_restore_requires_external_resolved_registry_world_and_checkpoint_anchors() -> None:
    api = _api()
    parameters = inspect.signature(api.SessionLifecycleV2.restore).parameters
    assert {
        "checkpoint",
        "expected_checkpoint_hash",
        "resolved",
        "expected_resolved_hash",
        "model_registry",
        "expected_model_registry_hash",
        "world_factory",
    }.issubset(parameters)


def test_runner_modes_separate_continuous_lockstep_and_read_only_replay() -> None:
    api = _api()
    assert tuple(item.value for item in api.RunnerModeV2) == (
        "continuous",
        "lockstep",
        "replay",
    )
    assert api.REPLAY_INITIALIZES_WORLD is False


def test_session_errors_are_stable_structured_and_path_precise() -> None:
    api = _api()
    fields = api.SessionErrorV2.model_fields
    assert {"code", "message", "path", "value", "reason", "suggestion"}.issubset(fields)
    assert api.SessionErrorV2.model_fields["code"].metadata


def test_generic_session_source_has_no_fixed_side_scenario_or_legacy_dispatch() -> None:
    source = inspect.getsource(_api())
    for forbidden in (
        "MD-AD",
        "MD_AD",
        "MD-INT",
        "MD_INT",
        '"red"',
        '"blue"',
        "scenario_id ==",
        "actor_side",
        "schemas.platform",
        "legacy",
    ):
        assert forbidden not in source


def test_public_session_exposes_only_readonly_world_queue_and_status_views() -> None:
    api = _api()
    public = set(dir(api.SessionLifecycleV2))
    assert "actions" not in public
    assert "world" not in public
    assert {"world_view", "queue_view", "action_status_view"}.issubset(public)
    assert "apply_tick" not in set(dir(api.ActionQueueViewV2))
    assert "rebind_world" not in set(dir(api.ActionQueueViewV2))


def test_session_step_owns_tick_input_and_accepts_typed_actions_not_world_commands() -> None:
    api = _api()
    parameters = inspect.signature(api.SessionLifecycleV2.step).parameters
    assert "world_tick_input" not in parameters
    assert {"expected_tick", "operation_id"}.issubset(parameters)


@pytest.mark.parametrize(
    "kind",
    ("navigation", "patrol", "hold", "sensor_mode", "relay_mode", "ciws_auto"),
)
def test_every_persistent_kind_has_typed_payload_schema_and_world_intent(kind: str) -> None:
    api = _api()
    contract = api.persistent_action_contract_v2(kind)
    assert contract.payload_model.model_config["extra"] == "forbid"
    assert contract.world_intent_type
    assert contract.receipt_type


@pytest.mark.parametrize(
    "kind",
    ("fire_weapon", "release_payload", "send_message", "device_action", "ram"),
)
def test_every_discrete_kind_has_typed_payload_schema_and_world_intent(kind: str) -> None:
    api = _api()
    contract = api.discrete_action_contract_v2(kind)
    assert contract.payload_model.model_config["extra"] == "forbid"
    assert contract.world_intent_type
    assert contract.receipt_type

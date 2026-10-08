"""RF-04 checkpoint continuation and lifecycle replay determinism."""

from __future__ import annotations

from typing import Any

import pytest
from tests.contract import test_declarative_events_v2 as event_fixture
from tests.contract import test_world_checkpoint_v2 as checkpoint_fixture


def _lifecycle_world() -> tuple[Any, Any, Any, Any]:
    resolved = event_fixture._compile(event_fixture._scenario())
    registry = event_fixture._catalog().model_registry
    factory = checkpoint_fixture._api().WorldFactoryV2(model_registry=registry)
    world = factory.build(resolved, session_id="session.checkpoint.lifecycle", seed=991)
    return world, resolved, registry, factory


@pytest.mark.parametrize("checkpoint_tick", (0, 10, 19))
def test_checkpoint_restore_at_tick_zero_spawn_and_despawn_is_exact(checkpoint_tick: int) -> None:
    world, resolved, registry, factory = _lifecycle_world()
    if checkpoint_tick >= 10:
        world.advance_lifecycle(expected_tick=10, operation_id="spawn")
    if checkpoint_tick >= 19:
        world.advance_lifecycle(expected_tick=19, operation_id="despawn")
    checkpoint = world.checkpoint()
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.semantic_snapshot() == world.semantic_snapshot()
    assert restored.checkpoint() == checkpoint


def test_n_plus_m_matches_checkpoint_at_n_restore_then_m() -> None:
    continuous, resolved, registry, factory = _lifecycle_world()
    continuous.advance_lifecycle(expected_tick=10, operation_id="spawn")
    at_n = continuous.checkpoint()
    continuous.advance_lifecycle(expected_tick=19, operation_id="despawn")

    resumed = factory.restore_checkpoint(
        at_n,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=at_n.checkpoint_hash,
    )
    resumed.advance_lifecycle(expected_tick=19, operation_id="despawn")
    assert resumed.semantic_snapshot() == continuous.semantic_snapshot()
    assert resumed.checkpoint().semantic_hash == continuous.checkpoint().semantic_hash


def test_restored_rng_and_idempotency_ledger_continue_without_double_application() -> None:
    world, resolved, registry, factory = _lifecycle_world()
    receipt = world.advance_lifecycle(expected_tick=10, operation_id="spawn.once")
    checkpoint = world.checkpoint()
    expected_random = world.rng.random()
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.rng.random() == expected_random
    assert restored.advance_lifecycle(expected_tick=10, operation_id="spawn.once") == receipt
    assert tuple(entity for entity in restored.entity_ids if entity == "entity.spawned") == (
        "entity.spawned",
    )


def test_input_order_independent_sessions_emit_identical_checkpoint_semantics() -> None:
    first, _resolved_a, _registry_a, _factory_a = _lifecycle_world()
    second, _resolved_b, _registry_b, _factory_b = _lifecycle_world()
    first.advance_lifecycle(expected_tick=10, operation_id="spawn")
    _ = second.semantic_snapshot()
    second.advance_lifecycle(expected_tick=10, operation_id="spawn")
    assert first.checkpoint().semantic_hash == second.checkpoint().semantic_hash


def test_ledger_receipt_semantics_must_match_applied_ids_and_schedule_cursor() -> None:
    world, resolved, registry, factory = _lifecycle_world()
    world.advance_lifecycle(expected_tick=10, operation_id="spawn.ledger")
    checkpoint = world.checkpoint()
    payload = checkpoint.model_dump(mode="json")
    payload["lifecycle_ledger"][0]["applied_event_ids"] = ["event.despawn"]
    payload["checkpoint_hash"] = (
        checkpoint_fixture._api().WorldCheckpointV2.compute_checkpoint_hash(payload)
    )
    forged = checkpoint_fixture._api().WorldCheckpointV2.model_validate(payload)
    with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
        factory.restore_checkpoint(
            forged,
            resolved=resolved,
            model_registry=registry,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        )
    assert captured.value.code in {
        "factory.checkpoint_anchor_mismatch",
        "factory.checkpoint_integrity_invalid",
    }

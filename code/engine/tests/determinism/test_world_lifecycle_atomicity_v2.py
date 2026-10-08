"""RF-04 lifecycle rollback, cleanup, and deterministic receipt contracts."""

from __future__ import annotations

from typing import Any

import pytest
from tests.contract import test_declarative_events_v2 as event_fixture
from tests.contract import test_world_lifecycle_v2 as lifecycle_fixture


def _api() -> Any:
    return lifecycle_fixture._api()


def test_failed_same_tick_batch_rolls_back_entities_indexes_ledger_tick_and_rng() -> None:
    world = lifecycle_fixture._world(lifecycle_fixture._spawn_events(2))
    before = world.semantic_snapshot()
    rng_before = world.rng.getstate()
    world.lifecycle_fault_injector.fail_after_staged_entities = 1
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=10, operation_id="batch.must.rollback")
    assert captured.value.code == "factory.lifecycle_batch_failed"
    assert world.semantic_snapshot() == before
    assert world.rng.getstate() == rng_before
    assert world.entity_ids == ("entity.existing",)
    assert "batch.must.rollback" not in world.lifecycle_ledger


def test_failed_spawn_closes_all_staged_adapters_in_reverse_order() -> None:
    world = lifecycle_fixture._world(lifecycle_fixture._spawn_events(2))
    world.lifecycle_fault_injector.fail_after_staged_adapters = 2
    with pytest.raises(_api().FactoryErrorV2):
        world.advance_lifecycle(expected_tick=10, operation_id="spawn.cleanup")
    audit = world.lifecycle_audit
    assert audit[-1].status == "rolled_back"
    assert audit[-1].closed_adapter_instance_ids == tuple(
        reversed(audit[-1].staged_adapter_instance_ids)
    )


def test_despawn_close_error_is_audited_without_resurrecting_entity() -> None:
    world = lifecycle_fixture._world()
    world.advance_lifecycle(expected_tick=10, operation_id="spawn.for-close-error")
    world.lifecycle_fault_injector.close_error_entity_ids = {"entity.spawned"}
    receipt = world.advance_lifecycle(expected_tick=19, operation_id="despawn.close-error")
    assert receipt.status == "committed_with_cleanup_errors"
    assert world.get_optional("entity.spawned") is None
    assert world.tombstones["entity.spawned"].cleanup_errors
    assert world.lifecycle_audit[-1].operation_id == "despawn.close-error"
    assert world.lifecycle_audit[-1].cleanup_errors


def test_expected_tick_is_compare_and_swap_and_does_not_advance_on_conflict() -> None:
    world = lifecycle_fixture._world(lifecycle_fixture._spawn_events(1))
    before = world.semantic_snapshot()
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=9, operation_id="wrong.tick")
    assert captured.value.code == "factory.lifecycle_tick_conflict"
    assert world.semantic_snapshot() == before


def test_identical_sessions_and_interleavings_produce_identical_receipts_and_snapshots() -> None:
    events = lifecycle_fixture._spawn_events(10)
    first = lifecycle_fixture._world(events)
    second = lifecycle_fixture._world(list(reversed(events)))
    first_receipt = first.advance_lifecycle(expected_tick=10, operation_id="same.operation")
    _ = second.semantic_snapshot()
    second_receipt = second.advance_lifecycle(expected_tick=10, operation_id="same.operation")
    assert first_receipt == second_receipt
    assert first.semantic_snapshot() == second.semantic_snapshot()


class _RaisingCloseAdapter:
    def __init__(self, instance_id: str) -> None:
        self.instance_id = instance_id
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        raise RuntimeError(f"close failed for {self.instance_id}")


def test_real_despawn_adapter_close_exception_is_audited_and_tombstone_is_not_false_green() -> None:
    world = lifecycle_fixture._world()
    world.advance_lifecycle(expected_tick=10, operation_id="spawn.real-close")
    adapter = _RaisingCloseAdapter("adapter.real-despawn")
    runtime_world: Any = world
    runtime_world._entities["entity.spawned"].adapters = {"adapter.synthetic@2.0.0": adapter}
    receipt = world.advance_lifecycle(expected_tick=19, operation_id="despawn.real-close")
    assert receipt.status == "committed_with_cleanup_errors"
    assert world.get_optional("entity.spawned") is None
    tombstone = world.tombstones["entity.spawned"]
    assert tombstone.adapters_closed is False
    assert tombstone.cleanup_errors == ("adapter.real-despawn:RuntimeError",)
    assert world.lifecycle_audit[-1].cleanup_errors == tombstone.cleanup_errors
    assert adapter.close_calls == 1


def test_real_rollback_adapter_close_exception_has_truthful_cleanup_evidence() -> None:
    resolved = event_fixture._compile(event_fixture._scenario(lifecycle_fixture._spawn_events(1)))
    registry = event_fixture._catalog().model_registry
    entity_factory = _api().EntityFactoryV2(model_registry=registry)
    original = entity_factory._build_owned
    adapter = _RaisingCloseAdapter("adapter.real-rollback")

    def build_with_failing_cleanup(definition: Any, **kwargs: Any) -> Any:
        entity = original(definition, **kwargs)
        if definition.id.startswith("future.asset"):
            entity.adapters = {"adapter.synthetic@2.0.0": adapter}
        return entity

    entity_factory_api: Any = entity_factory
    entity_factory_api._build_owned = build_with_failing_cleanup
    world = (
        _api()
        .WorldFactoryV2(
            model_registry=registry,
            entity_factory=entity_factory,
        )
        .build(resolved, session_id="session.rollback-real-cleanup", seed=73)
    )
    world.lifecycle_fault_injector.fail_after_staged_entities = 1
    with pytest.raises(_api().FactoryErrorV2):
        world.advance_lifecycle(expected_tick=10, operation_id="rollback.real-close")
    audit = world.lifecycle_audit[-1]
    assert audit.status == "rolled_back"
    assert audit.cleanup_errors == ("adapter.real-rollback:RuntimeError",)
    assert audit.closed_adapter_instance_ids == ()
    assert audit.staged_adapter_instance_ids == ("adapter.real-rollback",)
    assert adapter.close_calls == 1

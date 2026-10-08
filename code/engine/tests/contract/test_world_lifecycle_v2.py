"""RF-04 deterministic, atomic lifecycle execution contracts."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from tests.contract import test_declarative_events_v2 as event_fixture


def _api() -> Any:
    from openmdbench.world import factory_v2

    return factory_v2


def _world(events: list[dict[str, Any]] | None = None) -> Any:
    scenario = event_fixture._scenario(events)
    resolved = event_fixture._compile(scenario)
    return (
        _api()
        .WorldFactoryV2(model_registry=event_fixture._catalog().model_registry)
        .build(
            resolved,
            session_id="session.lifecycle.synthetic",
            seed=73,
        )
    )


def _spawn_events(count: int, *, tick: int = 10) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index in range(count):
        entity = event_fixture._entity(f"future.asset.{index:03d}")
        entity["controller_slot"] = None
        events.append(
            event_fixture._event(
                f"event.spawn.{index:03d}",
                "spawn",
                tick,
                {"entity": entity},
                priority=100 - index,
            )
        )
    return events


@pytest.mark.parametrize("count", (1, 10, 100))
def test_advance_lifecycle_scales_and_uses_resolved_topological_priority_order(
    count: int,
) -> None:
    world = _world(_spawn_events(count))
    receipt = world.advance_lifecycle(expected_tick=10, operation_id=f"advance.spawn.{count}")
    assert receipt.tick == 10
    assert receipt.operation_id == f"advance.spawn.{count}"
    assert receipt.applied_event_ids == tuple(
        entry.source_event_id for entry in world.lifecycle_schedule if entry.tick == 10
    )
    assert world.entity_ids == ("entity.existing",) + tuple(
        f"future.asset.{index:03d}" for index in range(count)
    )


def test_no_pending_transition_cannot_be_used_to_jump_to_an_arbitrary_tick() -> None:
    world = _world(_spawn_events(0))
    before = world.semantic_snapshot()
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=10, operation_id="advance.without-transition")
    assert captured.value.code == "factory.lifecycle_no_pending_transition"
    assert world.semantic_snapshot() == before


def test_spawn_then_despawn_updates_capability_controller_and_tombstone_atomically() -> None:
    world = _world()
    spawned = world.advance_lifecycle(expected_tick=10, operation_id="spawn.once")
    assert spawned.spawned_entity_ids == ("entity.spawned",)
    assert world.get("entity.spawned").capability_tokens
    assert world.controller_ownership.by_reserved_entity("entity.spawned") is None
    assert world.controller_ownership.by_entity("entity.spawned")

    despawned = world.advance_lifecycle(expected_tick=19, operation_id="despawn.once")
    assert despawned.despawned_entity_ids == ("entity.spawned",)
    assert world.get_optional("entity.spawned") is None
    assert world.tombstones["entity.spawned"].source_event_id == "event.despawn"
    assert world.tombstones["entity.spawned"].adapters_closed is True
    assert "entity.spawned" not in world.capability_index
    assert world.controller_ownership.by_entity("entity.spawned") == ()


def test_spawn_reuses_session_entity_factory_and_stages_full_adapter_construction() -> None:
    resolved = event_fixture._compile(event_fixture._scenario(_spawn_events(1)))
    registry = event_fixture._catalog().model_registry
    entity_factory = _api().EntityFactoryV2(model_registry=registry)
    original = entity_factory._build_owned
    built_ids: list[str] = []

    def recording_build(definition: Any, **kwargs: Any) -> Any:
        built_ids.append(definition.id)
        return original(definition, **kwargs)

    entity_factory_api: Any = entity_factory
    entity_factory_api._build_owned = recording_build
    world = (
        _api()
        .WorldFactoryV2(
            model_registry=registry,
            entity_factory=entity_factory,
        )
        .build(resolved, session_id="session.lifecycle.factory-reuse", seed=73)
    )
    assert built_ids == ["entity.existing"]
    world.advance_lifecycle(expected_tick=10, operation_id="spawn.via-entity-factory")
    assert built_ids == ["entity.existing", "future.asset.000"]
    assert world.get("future.asset.000").adapter_diagnostics


def test_operation_id_is_idempotent_and_receipt_is_deeply_immutable() -> None:
    world = _world(_spawn_events(1))
    first = world.advance_lifecycle(expected_tick=10, operation_id="operation.same")
    second = world.advance_lifecycle(expected_tick=10, operation_id="operation.same")
    assert second is first
    assert world.lifecycle_ledger["operation.same"] is first
    with pytest.raises((AttributeError, TypeError)):
        first.applied_event_ids += ("forged",)


def test_operation_identity_is_bound_to_expected_tick_fingerprint() -> None:
    world = _world(_spawn_events(1))
    first = world.advance_lifecycle(expected_tick=10, operation_id="operation.bound")
    assert first.tick == 10
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=11, operation_id="operation.bound")
    assert captured.value.code == "factory.lifecycle_operation_conflict"
    assert world.lifecycle_ledger["operation.bound"] is first


def test_closed_world_rejects_new_and_replayed_lifecycle_operations() -> None:
    world = _world(_spawn_events(1))
    world.advance_lifecycle(expected_tick=10, operation_id="operation.before-close")
    before = world.semantic_snapshot()
    world.close()
    for operation_id, tick in (
        ("operation.before-close", 10),
        ("operation.after-close", 10),
    ):
        with pytest.raises(_api().FactoryErrorV2) as captured:
            world.advance_lifecycle(expected_tick=tick, operation_id=operation_id)
        assert captured.value.code == "factory.world_closed"
    assert world.semantic_snapshot() == before


@pytest.mark.parametrize("operation_id", ("", 3, True, "x" * 257))
def test_advance_rejects_invalid_operation_identity(operation_id: Any) -> None:
    world = _world(_spawn_events(1))
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=10, operation_id=operation_id)
    assert captured.value.code == "factory.lifecycle_operation_invalid"


def test_used_entity_ids_are_permanent_and_prevent_respawn_after_despawn() -> None:
    events = event_fixture._events()
    duplicate = copy.deepcopy(next(item for item in events if item["event_type"] == "spawn"))
    duplicate["id"] = "event.spawn.reuse"
    duplicate["trigger"]["tick"] = 20
    duplicate["depends_on"] = ["event.despawn"]
    events.append(duplicate)
    world = _world(events)
    world.advance_lifecycle(expected_tick=10, operation_id="spawn.original")
    world.advance_lifecycle(expected_tick=19, operation_id="despawn.original")
    with pytest.raises(_api().FactoryErrorV2) as captured:
        world.advance_lifecycle(expected_tick=20, operation_id="spawn.reused-id")
    assert captured.value.code == "factory.lifecycle_entity_id_reused"
    assert "entity.spawned" in world.used_entity_ids
    assert world.get_optional("entity.spawned") is None


def test_write_transaction_cannot_directly_change_lifecycle() -> None:
    world = _world([])
    with (
        pytest.raises(_api().FactoryErrorV2) as captured,
        world.write_transaction(tick=0) as writer,
    ):
        writer.entity("entity.existing").lifecycle = "despawned"
    assert captured.value.code == "factory.lifecycle_write_forbidden"
    assert world.get("entity.existing").state.lifecycle == "active"


def test_write_transaction_rejects_reentrant_lifecycle_advance_without_mutating_either_side() -> (
    None
):
    world = _world(_spawn_events(1))
    before = world.semantic_snapshot()
    with (
        pytest.raises(_api().FactoryErrorV2) as captured,
        world.write_transaction(tick=0) as writer,
    ):
        writer.entity("entity.existing").health = 0.75
        world.advance_lifecycle(expected_tick=10, operation_id="reentrant.advance")
    assert captured.value.code == "factory.lifecycle_transaction_active"
    assert world.semantic_snapshot() == before
    assert "reentrant.advance" not in world.lifecycle_ledger


def test_semantic_snapshot_records_complete_schedule_and_ledger_semantics() -> None:
    world = _world(_spawn_events(1))
    world.advance_lifecycle(expected_tick=10, operation_id="snapshot.advance")
    snapshot = world.semantic_snapshot()
    assert snapshot["lifecycle_schedule"] == [
        {
            "topological_index": 0,
            "tick": 10,
            "priority": 100,
            "event_type": "spawn",
            "entity_id": "future.asset.000",
            "source_event_id": "event.spawn.000",
            "blueprint_hash": world.lifecycle_schedule[0].blueprint_hash,
        }
    ]
    assert snapshot["used_entity_ids"] == ["entity.existing", "future.asset.000"]
    assert snapshot["lifecycle_ledger"][0]["operation_id"] == "snapshot.advance"
    assert snapshot["tombstones"] == []
    assert snapshot["applied_lifecycle_event_ids"] == ["event.spawn.000"]
    assert snapshot["controller_ownership"] == world.controller_ownership.to_canonical_dict()
    assert snapshot["capability_index"] == {
        key: list(value) for key, value in world.capability_index.items()
    }
    assert snapshot["rng_fingerprint"].startswith("sha256:")
    assert snapshot["lifecycle_audit"][0]["operation_id"] == "snapshot.advance"

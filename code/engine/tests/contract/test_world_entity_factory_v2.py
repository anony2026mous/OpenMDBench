"""RF-04 contracts for generic runtime world and entity construction."""

from __future__ import annotations

import copy
import importlib
import importlib.util
import inspect
import math
from dataclasses import replace
from types import MappingProxyType
from typing import Any

import pytest
from openmdbench.catalog.v2 import ModelFactoryMetadataV2, ModelRegistryV2
from tests.contract import test_declarative_events_v2 as event_fixture
from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture


def _api() -> Any:
    module_name = "openmdbench.world.factory_v2"
    try:
        specification = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        specification = None
    assert specification is not None, (
        "RF-04 requires the public openmdbench.world.factory_v2 module"
    )
    return importlib.import_module(module_name)


def _resolved(
    count: int,
    *,
    components: bool = True,
    scenario_id: str = "scenario.factory-arbitrary",
) -> tuple[Any, Any]:
    catalog = resource_fixture._catalog()
    payload = resource_fixture._scenario(components=components)
    payload["scenario_id"] = scenario_id
    payload["factions"] = [
        {"schema_version": "2.0", "id": "coalition.alpha"},
        {"schema_version": "2.0", "id": "coalition.beta"},
        {"schema_version": "2.0", "id": "coalition.neutral"},
    ]
    payload["relationships"] = [
        {
            "schema_version": "2.0",
            "source_faction_id": "coalition.alpha",
            "target_faction_id": "coalition.beta",
            "relation": "hostile",
        },
        {
            "schema_version": "2.0",
            "source_faction_id": "coalition.alpha",
            "target_faction_id": "coalition.neutral",
            "relation": "protected",
        },
    ]
    entities: list[dict[str, Any]] = []
    for index in range(count):
        entity = resource_fixture._entity(components=components, rounds=index % 4 + 1)
        entity["id"] = f"asset.{index:03d}"
        entity["faction_id"] = ("coalition.alpha", "coalition.beta", "coalition.neutral")[index % 3]
        entity["controller_slot"] = f"controller.slot.{index:03d}"
        entity["tags"] = ["generic", f"batch-{index % 2}"]
        entity["initial_state"]["position_m"] = [float(index), 2.0, 3.0]
        entity["initial_state"]["velocity_mps"] = [float(index % 5), 0.0, 0.0]
        entity["initial_state"]["health"] = 1.0 - index / max(count * 2, 1)
        entity["initial_state"]["energy"] = 0.75
        entity["initial_state"]["component_states"] = {"mode": "ready"}
        entities.append(entity)
    payload["entities"] = entities
    resolved = resource_fixture._compile(catalog, payload)
    return resolved, catalog.model_registry


def _factories(registry: Any) -> tuple[Any, Any]:
    api = _api()
    entity_factory = api.EntityFactoryV2(model_registry=registry)
    world_factory = api.WorldFactoryV2(
        model_registry=registry,
        entity_factory=entity_factory,
    )
    return entity_factory, world_factory


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_world_factory_builds_arbitrary_counts_with_stable_dynamic_identity(count: int) -> None:
    resolved, registry = _resolved(count)
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    assert world.entity_ids == tuple(f"asset.{index:03d}" for index in range(count))
    assert tuple(entity.id for entity in world.entities_stable()) == world.entity_ids
    assert world.faction_ids == ("coalition.alpha", "coalition.beta", "coalition.neutral")
    assert tuple(
        (item.source_faction_id, item.target_faction_id) for item in world.relationships
    ) == (
        ("coalition.alpha", "coalition.beta"),
        ("coalition.alpha", "coalition.neutral"),
    )
    assert tuple(entity.controller_binding for entity in world.entities_stable()) == tuple(
        f"controller.slot.{index:03d}" for index in range(count)
    )


def test_factory_is_scenario_name_independent_and_uses_no_catalog_or_source() -> None:
    first, registry = _resolved(3, scenario_id="scenario.name-one")
    second, _ = _resolved(3, scenario_id="scenario.renamed-completely")
    _entity_factory, factory = _factories(registry)
    first_world = factory.build(first)
    second_world = factory.build(second)
    assert first_world.semantic_snapshot() == second_world.semantic_snapshot()
    source = inspect.getsource(type(factory)) + inspect.getsource(type(first_world))
    assert "CatalogV2" not in source
    assert "source_yaml" not in source and "source_path" not in source


def test_entity_factory_derives_capabilities_and_supports_generic_queries() -> None:
    resolved, registry = _resolved(4)
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    first = world.get("asset.000")
    assert first.capabilities == frozenset(
        {
            "dynamics",
            "sensor",
            "communication",
            "weapon",
            "energy",
            "collision",
            "visualization",
        }
    )
    assert tuple(item.id for item in world.query(capability="sensor")) == world.entity_ids
    assert tuple(item.id for item in world.query(faction_id="coalition.beta")) == ("asset.001",)
    assert tuple(item.id for item in world.query(domain="upper-atmosphere")) == world.entity_ids
    assert tuple(item.id for item in world.query(tag="batch-1")) == (
        "asset.001",
        "asset.003",
    )


def test_optional_sensor_weapon_and_dynamics_are_legal() -> None:
    resolved, registry = _resolved(1, components=False)
    payload = resource_fixture._scenario(components=False)
    payload["entities"][0]["dynamics_ref"] = None
    resolved = resource_fixture._compile(resource_fixture._catalog(), payload)
    _entity_factory, world_factory = _factories(registry)
    entity = world_factory.build(resolved).entities_stable()[0]
    assert "sensor" not in entity.capabilities
    assert "weapon" not in entity.capabilities
    assert "dynamics" not in entity.capabilities
    assert "energy" in entity.capabilities


def test_runtime_state_is_separate_from_frozen_definitions_and_fully_materialized() -> None:
    resolved, registry = _resolved(2)
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    first, second = world.entities_stable()
    assert first.definition is not first.state
    assert isinstance(first.definition.resource_bindings, MappingProxyType)
    assert tuple(first.state.position_m) == (0.0, 2.0, 3.0)
    assert tuple(second.state.velocity_mps) == (1.0, 0.0, 0.0)
    assert first.state.health == 1.0
    assert first.state.energy == 0.75
    assert dict(first.state.ammunition)
    assert first.state.component_states == {"mode": "ready"}
    assert first.state.lifecycle == "active"
    bindings: Any = first.definition.resource_bindings
    with pytest.raises((AttributeError, TypeError)):
        bindings["injected"] = ()


def test_same_platform_with_distinct_loadouts_and_initial_dynamics_is_independent() -> None:
    catalog = resource_fixture._catalog()
    payload = resource_fixture._scenario()
    equipped = resource_fixture._entity(components=True, rounds=7)
    equipped["id"] = "vehicle.equipped"
    equipped["initial_state"]["velocity_mps"] = [30.0, 0.0, 0.0]
    bare = resource_fixture._entity(components=False)
    bare["id"] = "vehicle.bare"
    bare["initial_state"]["velocity_mps"] = [5.0, 0.0, 0.0]
    payload["entities"] = [bare, equipped]
    resolved = resource_fixture._compile(catalog, payload)
    _entity_factory, world_factory = _factories(catalog.model_registry)
    world = world_factory.build(resolved)
    assert (
        world.get("vehicle.bare").definition.platform_ref
        == world.get("vehicle.equipped").definition.platform_ref
    )
    assert "weapon" not in world.get("vehicle.bare").capabilities
    assert "weapon" in world.get("vehicle.equipped").capabilities
    assert tuple(world.get("vehicle.bare").state.velocity_mps) == (5.0, 0.0, 0.0)
    assert tuple(world.get("vehicle.equipped").state.velocity_mps) == (30.0, 0.0, 0.0)


def test_repeated_builds_have_no_shared_runtime_adapters_state_or_rng() -> None:
    resolved, registry = _resolved(2)
    _entity_factory, world_factory = _factories(registry)
    first = world_factory.build(resolved)
    second = world_factory.build(resolved)
    first_entity = first.get("asset.000")
    second_entity = second.get("asset.000")
    assert first is not second and first_entity is not second_entity
    assert first_entity.state is not second_entity.state
    assert first_entity.adapter_diagnostics is not second_entity.adapter_diagnostics
    assert first_entity.adapter_diagnostics.keys() == second_entity.adapter_diagnostics.keys()
    assert all(
        first_entity.adapter_diagnostics[key].instance_id
        != second_entity.adapter_diagnostics[key].instance_id
        for key in first_entity.adapter_diagnostics
    )
    assert first.rng is not second.rng
    with first.write_transaction(tick=0) as writer:
        draft = writer.entity("asset.000")
        draft.health = 0.25
        draft.ammunition.clear()
        draft.position_m[0] = 999.0
    assert second_entity.state.health == 1.0
    assert second_entity.state.ammunition
    assert second_entity.state.position_m[0] == 0.0


def test_spawn_and_despawn_remain_in_a_stable_unexecuted_lifecycle_schedule() -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    registry = event_fixture._catalog().model_registry
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    assert world.entity_ids == ("entity.existing",)
    assert tuple(
        (item.tick, item.event_type, item.entity_id) for item in world.lifecycle_schedule
    ) == (
        (10, "spawn", "entity.spawned"),
        (19, "despawn", "entity.spawned"),
    )
    assert world.tick == 0
    assert world.get_optional("entity.spawned") is None


def test_registry_evidence_mismatch_and_unknown_model_fail_with_stable_error() -> None:
    api = _api()
    resolved, registry = _resolved(1)
    metadata = registry.snapshot()[0]
    mismatched = ModelRegistryV2(interface_version="2.0")
    mismatched.register(
        ModelFactoryMetadataV2.model_validate(
            metadata.model_dump() | {"artifact_sha256": "sha256:" + "f" * 64}
        ),
        lambda definition: definition,
    )
    mismatched.freeze()
    with pytest.raises(api.FactoryErrorV2) as captured:
        api.WorldFactoryV2(model_registry=mismatched).build(resolved)
    error = captured.value
    assert error.code == "factory.model_evidence_mismatch"
    assert error.path and error.value is not None and error.reason and error.suggestion

    empty = ModelRegistryV2(interface_version="2.0")
    empty.freeze()
    with pytest.raises(api.FactoryErrorV2) as unknown:
        api.WorldFactoryV2(model_registry=empty).build(resolved)
    assert unknown.value.code == "factory.model_unknown"


def test_snapshot_is_deeply_frozen_and_world_mutation_uses_controlled_boundary() -> None:
    resolved, registry = _resolved(1)
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    snapshot = world.snapshot()
    with pytest.raises((AttributeError, TypeError)):
        snapshot.entities[0].state.health = 0.0
    with world.write_transaction(tick=0) as writer:
        writer.entity("asset.000").health = 0.5
    assert world.get("asset.000").state.health == 0.5
    assert snapshot.entities[0].state.health == 1.0


@pytest.mark.parametrize(
    "forbidden",
    ("Side", "red_force", "blue_force", "MD-AD", "MD-INT", "scenario_id =="),
)
def test_generic_factory_source_has_no_fixed_sides_scenarios_or_counts(forbidden: str) -> None:
    api = _api()
    source = inspect.getsource(api)
    assert forbidden not in source
    assert "range(15)" not in source and "range(7)" not in source


def test_runtime_definition_is_not_a_mutable_copy_of_resolved_input() -> None:
    resolved, registry = _resolved(1)
    _entity_factory, world_factory = _factories(registry)
    world = world_factory.build(resolved)
    original = copy.deepcopy(world.semantic_snapshot())
    with world.write_transaction(tick=0) as writer:
        writer.entity("asset.000").component_states["mode"] = "degraded"
    assert world.semantic_snapshot() != original
    assert resolved.entities[0].runtime_initial.initial_state.component_states == {"mode": "ready"}


def test_entity_factory_accepts_resolved_entity_without_scenario_context() -> None:
    resolved, registry = _resolved(1)
    entity_factory, _world_factory = _factories(registry)
    built = entity_factory.build(resolved.entities[0])
    assert built.id == "asset.000"
    assert built.definition == resolved.entities[0]
    assert built.state.position_m == [0.0, 2.0, 3.0]


def _assert_factory_error(call: Any, expected_codes: set[str]) -> Any:
    api = _api()
    with pytest.raises(api.FactoryErrorV2) as captured:
        call()
    error = captured.value
    assert error.code in expected_codes
    assert error.path and error.value is not None and error.reason and error.suggestion
    return error


def _rehash(resolved: Any) -> Any:
    payload = resolved._payload(include_hash=False)
    return replace(
        resolved,
        resolved_hash=type(resolved).compute_resolved_hash(payload),
    )


def test_build_revalidates_complete_resolved_integrity_and_hash() -> None:
    resolved, registry = _resolved(1)
    _entity_factory, factory = _factories(registry)
    corrupted = replace(resolved, resolved_hash="sha256:" + "0" * 64)
    _assert_factory_error(
        lambda: factory.build(corrupted),
        {"factory.resolved_integrity_invalid"},
    )
    bad_registry_hash = replace(resolved, model_registry_hash="sha256:" + "1" * 64)
    _assert_factory_error(
        lambda: factory.build(bad_registry_hash),
        {"factory.resolved_integrity_invalid", "factory.model_registry_hash_mismatch"},
    )


def test_build_rejects_rehashed_nested_binding_corruption() -> None:
    resolved, registry = _resolved(1)
    entity = resolved.entities[0]
    bindings = dict(entity.resource_bindings)
    platform = bindings["platforms"][0]
    bindings["platforms"] = (replace(platform, content_hash="sha256:" + "0" * 64),)
    corrupted_entity = replace(entity, resource_bindings=MappingProxyType(bindings))
    corrupted = _rehash(replace(resolved, entities=(corrupted_entity,)))
    _assert_factory_error(
        lambda: _factories(registry)[1].build(corrupted),
        {"factory.resolved_integrity_invalid"},
    )


def test_build_rejects_rehashed_nested_event_and_controller_corruption() -> None:
    event_resolved = event_fixture._compile(event_fixture._scenario())
    bad_event = replace(event_resolved.events[0], priority="highest")
    corrupted_event = _rehash(
        replace(event_resolved, events=(bad_event, *event_resolved.events[1:]))
    )
    _assert_factory_error(
        lambda: _factories(event_fixture._catalog().model_registry)[1].build(corrupted_event),
        {"factory.resolved_integrity_invalid"},
    )

    from tests.contract import test_declarative_mission_control_v2 as mission_fixture

    mission_resolved = mission_fixture._compile(mission_fixture._scenario())
    controller = mission_resolved.controller_slots[0]
    controller_values = dict(controller.values)
    controller_values["resolved_entity_ids"] = ("entity.does-not-exist",)
    bad_controller = replace(controller, values=MappingProxyType(controller_values))
    corrupted_controller = _rehash(
        replace(
            mission_resolved,
            controller_slots=(bad_controller, *mission_resolved.controller_slots[1:]),
        )
    )
    _assert_factory_error(
        lambda: _factories(mission_fixture._catalog().model_registry)[1].build(
            corrupted_controller
        ),
        {"factory.resolved_integrity_invalid"},
    )


def test_public_entity_accessors_return_immutable_views_only() -> None:
    resolved, registry = _resolved(2)
    world = _factories(registry)[1].build(resolved)
    views = (
        world.get("asset.000"),
        world.entities_stable()[0],
        world.query(capability="sensor")[0],
    )
    for view in views:
        with pytest.raises((AttributeError, TypeError)):
            view.state.health = 0.0
        with pytest.raises((AttributeError, TypeError)):
            view.state.position_m[0] = 999.0
        with pytest.raises((AttributeError, TypeError)):
            view.state.ammunition.clear()


@pytest.mark.parametrize(
    "mutate",
    (
        lambda state: setattr(state, "health", math.nan),
        lambda state: setattr(state, "lifecycle", "teleported"),
        lambda state: state.ammunition.update({"round.arbitrary@2.4.1": True}),
        lambda state: state.ammunition.update({"round.arbitrary@2.4.1": 1.5}),
        lambda state: state.ammunition.update({"not-an-exact-ref": 1}),
        lambda state: state.ammunition.update({"round.arbitrary@2.4.1": -1}),
    ),
)
def test_invalid_transaction_state_rolls_back_atomically(mutate: Any) -> None:
    resolved, registry = _resolved(1)
    world = _factories(registry)[1].build(resolved)
    before = world.snapshot()

    def transact() -> None:
        with world.write_transaction(tick=0) as writer:
            mutate(writer.entity("asset.000"))

    _assert_factory_error(transact, {"factory.state_invalid"})
    assert world.snapshot() == before


def test_snapshot_remains_immutable_and_consistent_across_committed_transaction() -> None:
    resolved, registry = _resolved(2)
    world = _factories(registry)[1].build(resolved)
    before = world.snapshot()
    with world.write_transaction(tick=0) as writer:
        writer.entity("asset.000").health = 0.4
        writer.entity("asset.001").health = 0.6
    after = world.snapshot()
    assert tuple(item.state.health for item in before.entities) == (1.0, 0.75)
    assert tuple(item.state.health for item in after.entities) == (0.4, 0.6)
    assert before.tick == after.tick == 0


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("units", {"foreign": "fortnight"}),
        ("field_units", {"foreign": "league"}),
        ("deterministic", False),
        ("thread_safe", False),
        ("process_safe", False),
        ("trusted", False),
        ("interface_version", "9.0"),
        ("artifact_sha256", "sha256:" + "f" * 64),
        ("resource_types", ("platforms",)),
    ),
)
def test_registry_metadata_requires_full_canonical_equality(field: str, replacement: Any) -> None:
    resolved, registry = _resolved(1)
    evidence = resolved.model_registry_snapshot[0]
    altered = evidence.model_copy(update={field: replacement})
    corrupted = _rehash(replace(resolved, model_registry_snapshot=(altered,)))
    _assert_factory_error(
        lambda: _factories(registry)[1].build(corrupted),
        {
            "factory.resolved_integrity_invalid",
            "factory.model_evidence_mismatch",
            "factory.model_interface_incompatible",
            "factory.model_untrusted",
        },
    )


class _TrackedAdapter:
    created: list[_TrackedAdapter] = []
    closed: list[int] = []

    def __init__(self, ordinal: int) -> None:
        self.ordinal = ordinal
        type(self).created.append(self)

    def __deepcopy__(self, memo: dict[int, Any]) -> _TrackedAdapter:
        del memo
        return self

    def close(self) -> None:
        type(self).closed.append(self.ordinal)


def _tracking_registry(*, fail_at: int | None = None, singleton: bool = False) -> Any:
    source = resource_fixture._catalog().model_registry.snapshot()[0]
    registry = ModelRegistryV2(interface_version="2.0")
    calls = 0
    shared = _TrackedAdapter(-1)

    def create(_definition: Any) -> Any:
        nonlocal calls
        calls += 1
        if fail_at is not None and calls == fail_at:
            raise RuntimeError("synthetic adapter failure")
        return shared if singleton else _TrackedAdapter(calls)

    registry.register(source, create)
    registry.freeze()
    return registry


def test_adapter_failure_is_stable_and_cleans_partial_resources_in_reverse_order() -> None:
    api = _api()
    resolved, _registry = _resolved(1)
    _TrackedAdapter.created.clear()
    _TrackedAdapter.closed.clear()
    registry = _tracking_registry(fail_at=4)
    with pytest.raises(api.FactoryErrorV2) as captured:
        api.WorldFactoryV2(model_registry=registry).build(resolved)
    assert captured.value.code == "factory.adapter_creation_failed"
    assert _TrackedAdapter.closed == [3, 2, 1]


def test_factory_rejects_singleton_adapter_reuse_with_stable_cleanup() -> None:
    resolved, _registry = _resolved(1)
    _TrackedAdapter.created.clear()
    _TrackedAdapter.closed.clear()
    registry = _tracking_registry(singleton=True)
    _assert_factory_error(
        lambda: _api().WorldFactoryV2(model_registry=registry).build(resolved),
        {"factory.adapter_instance_reused"},
    )
    assert _TrackedAdapter.closed


def test_lifecycle_schedule_preserves_resolved_order_priority_and_topology() -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    world = _factories(event_fixture._catalog().model_registry)[1].build(resolved)
    lifecycle_events = [
        (index, event)
        for index, event in enumerate(resolved.events)
        if event.event_type in {"spawn", "despawn"}
    ]
    assert tuple(
        (
            item.topological_index,
            item.tick,
            item.priority,
            item.event_type,
            item.source_event_id,
        )
        for item in world.lifecycle_schedule
    ) == tuple(
        (index, event.trigger.tick, event.priority, event.event_type, event.id)
        for index, event in lifecycle_events
    )


@pytest.mark.parametrize(
    "corrupt_event",
    (
        lambda event: replace(
            event,
            trigger=replace(
                event.trigger,
                values=MappingProxyType({"kind": "tick", "tick": "ten"}),
            ),
        ),
        lambda event: replace(
            event,
            payload=replace(event.payload, values=MappingProxyType({})),
        ),
    ),
)
def test_malformed_lifecycle_event_fails_closed_without_silent_continue(
    corrupt_event: Any,
) -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    event = next(item for item in resolved.events if item.event_type == "spawn")
    replacement = corrupt_event(event)
    events = tuple(replacement if item.id == event.id else item for item in resolved.events)
    corrupted = _rehash(replace(resolved, events=events))
    _assert_factory_error(
        lambda: _factories(event_fixture._catalog().model_registry)[1].build(corrupted),
        {"factory.resolved_integrity_invalid", "factory.lifecycle_schedule_invalid"},
    )


def test_build_session_and_seed_contract_is_deterministic_and_rename_independent() -> None:
    first, registry = _resolved(1, scenario_id="scenario.seed-name-a")
    renamed, _ = _resolved(1, scenario_id="scenario.seed-name-b")
    factory = _factories(registry)[1]
    one = factory.build(first, session_id="session.one", seed=73)
    repeated = factory.build(first, session_id="session.two", seed=73)
    renamed_world = factory.build(renamed, session_id="session.three", seed=73)
    different = factory.build(first, session_id="session.four", seed=74)
    assert one.session_id == "session.one"
    assert one.rng.random() == repeated.rng.random() == renamed_world.rng.random()
    assert (
        different.rng.random()
        != _factories(registry)[1].build(first, session_id="session.five", seed=73).rng.random()
    )


@pytest.mark.parametrize(
    ("session_id", "seed"),
    (
        ("", 1),
        (17, 1),
        ("session.valid", True),
        ("session.valid", 1.5),
        ("session.valid", math.nan),
    ),
)
def test_build_rejects_invalid_session_id_and_seed(session_id: Any, seed: Any) -> None:
    resolved, registry = _resolved(1)
    _assert_factory_error(
        lambda: _factories(registry)[1].build(
            resolved,
            session_id=session_id,
            seed=seed,
        ),
        {"factory.session_id_invalid", "factory.seed_invalid"},
    )

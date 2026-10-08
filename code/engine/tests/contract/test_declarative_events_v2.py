"""RF-03 RED contracts for typed declarative events and dependency resolution."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
    ResourceTypeV2,
)
from openmdbench.scenarios import declarative_v2 as declarative_module
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)

PLUGIN_HASH = "sha256:" + "9" * 64
RESOURCE_TYPES: tuple[ResourceTypeV2, ...] = (
    "platforms",
    "dynamics",
    "sensors",
    "effects",
    "damage_models",
    "environments",
)


def _resource(
    resource_type: ResourceTypeV2,
    identifier: str,
    content: dict[str, Any],
    dependencies: tuple[str, ...] = (),
) -> CatalogResourceV2:
    return CatalogResourceV2(
        schema_version="2.0",
        resource_type=resource_type,
        id=identifier,
        version="2.1.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.event-contract@2.0.0",
        dependencies=dependencies,
        content=content,
    )


def _resources() -> dict[str, CatalogResourceV2]:
    damage = _resource("damage_models", "damage.arbitrary", {"effect_types": ["thermal"]})
    effect = _resource(
        "effects",
        "effect.arbitrary",
        {"effect_type": "thermal", "damage_model_ref": damage.exact_ref},
        (damage.exact_ref,),
    )
    dynamics = _resource(
        "dynamics",
        "dynamics.arbitrary",
        {"compatible_platform_types": ["generic-mobile"], "mobile": True},
    )
    sensor = _resource(
        "sensors",
        "sensor.arbitrary",
        {"compatible_platform_types": ["generic-mobile"], "slot_type": "sensor"},
    )
    platform = _resource(
        "platforms",
        "platform.arbitrary",
        {
            "platform_type": "generic-mobile",
            "domain": "synthetic-domain",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": ["sensor"],
            "payload_capacity_kg": 0.0,
        },
    )
    environment = _resource("environments", "weather.arbitrary", {"state": "synthetic"})
    return {
        item.resource_type: item
        for item in (platform, dynamics, sensor, effect, damage, environment)
    }


def _catalog() -> CatalogV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.event-contract",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256=PLUGIN_HASH,
            resource_types=RESOURCE_TYPES,
            field_units={},
        ),
        lambda definition: definition,
    )
    registry.freeze()
    return CatalogV2(_resources().values(), engine_version="2.0.0", model_registry=registry)


def _entity(identifier: str) -> dict[str, Any]:
    resources = _resources()
    return {
        "schema_version": "2.0",
        "id": identifier,
        "faction_id": "faction.arbitrary",
        "platform_ref": resources["platforms"].exact_ref,
        "dynamics_ref": resources["dynamics"].exact_ref,
        "component_refs": [resources["sensors"].exact_ref],
        "initial_state": {
            "schema_version": "2.0",
            "position_m": [10.0, 20.0, 30.0],
            "velocity_mps": [0.0, 0.0, 0.0],
            "heading_deg": 0.0,
        },
        "controller_slot": f"controller/{identifier}",
    }


def _event(
    identifier: str,
    event_type: str,
    tick: int,
    payload: dict[str, Any],
    *,
    priority: int = 0,
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "id": identifier,
        "event_type": event_type,
        "trigger": {"kind": "tick", "tick": tick},
        "priority": priority,
        "depends_on": depends_on or [],
        "payload": payload,
    }


def _events() -> list[dict[str, Any]]:
    resources = _resources()
    spawned = _entity("entity.spawned")
    return [
        _event("event.spawn", "spawn", 10, {"entity": spawned}, priority=20),
        _event(
            "event.message",
            "message",
            11,
            {
                "sender_entity_id": "entity.existing",
                "recipient_entity_ids": ["entity.spawned"],
                "visibility": "recipients",
                "body": "synthetic message",
            },
            depends_on=["event.spawn"],
        ),
        _event(
            "event.weather",
            "weather_change",
            12,
            {"environment_ref": resources["environments"].exact_ref},
        ),
        _event("event.zone", "zone_activation", 13, {"zone_id": "zone.arbitrary"}),
        _event(
            "event.jam.start",
            "jamming_start",
            14,
            {
                "session_id": "jam/session-arbitrary",
                "source_entity_id": "entity.existing",
                "target_entity_id": "entity.spawned",
            },
            depends_on=["event.spawn"],
        ),
        _event(
            "event.jam.end",
            "jamming_end",
            15,
            {"session_id": "jam/session-arbitrary"},
            depends_on=["event.jam.start"],
        ),
        _event(
            "event.suppress",
            "component_suppression",
            16,
            {
                "target_entity_id": "entity.existing",
                "component_ref": resources["sensors"].exact_ref,
                "duration_ticks": 2,
            },
        ),
        _event(
            "event.effect",
            "apply_effect",
            17,
            {
                "effect_ref": resources["effects"].exact_ref,
                "target_selector": {"entity_ids": ["entity.existing"]},
            },
        ),
        _event(
            "event.marker",
            "mission_marker",
            18,
            {"marker_id": "marker.arbitrary", "zone_id": "zone.arbitrary"},
        ),
        _event("event.despawn", "despawn", 19, {"entity_id": "entity.spawned"}),
    ]


def _scenario(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "scenario_id": "scenario.typed-events",
        "factions": [{"schema_version": "2.0", "id": "faction.arbitrary"}],
        "relationships": [],
        "entities": [_entity("entity.existing")],
        "formations": [],
        "world": {
            "schema_version": "2.0",
            "coordinate_system": "local_m",
            "duration_ticks": 100,
            "tick_seconds": 0.5,
            "zones": [
                {
                    "schema_version": "2.0",
                    "id": "zone.arbitrary",
                    "geometry_type": "polygon",
                    "coordinates_m": [[0.0, 0.0], [100.0, 0.0], [0.0, 100.0]],
                }
            ],
        },
        "events": events if events is not None else _events(),
        "mission_rules": [],
        "score_metrics": [],
    }


def _compile(payload: dict[str, Any]) -> Any:
    package = ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": payload})
    return ScenarioCompilerV2(catalog=_catalog()).compile(package)


def _assert_error(payload: dict[str, Any], code: str, path: tuple[str, ...]) -> None:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(payload)
    error = captured.value
    assert error.code == code
    assert all(item in error.path for item in path)
    assert error.file == "events.yaml"
    assert error.value is not None and error.reason and error.suggestion


def test_all_whitelisted_events_are_fully_typed_resolved_and_frozen() -> None:
    resolved = _compile(_scenario())
    assert {event.event_type for event in resolved.events} == {
        "spawn",
        "despawn",
        "weather_change",
        "zone_activation",
        "jamming_start",
        "jamming_end",
        "component_suppression",
        "message",
        "mission_marker",
        "apply_effect",
    }
    spawn = next(event for event in resolved.events if event.event_type == "spawn")
    assert spawn.trigger.kind == "tick" and spawn.trigger.tick == 10
    assert spawn.payload.entity.id == "entity.spawned"
    effect = next(event for event in resolved.events if event.event_type == "apply_effect")
    assert effect.payload.effect_binding.resource_type == "effects"
    assert effect.payload.effect_binding.exact_ref == _resources()["effects"].exact_ref
    with pytest.raises((TypeError, AttributeError)):
        effect.payload.target_selector.entity_ids += ("injected",)


def test_event_topological_order_is_tick_then_priority_then_id_and_input_independent() -> None:
    events = _events()
    events.extend(
        [
            _event("event.same.c", "message", 20, {"body": "c", "visibility": "public"}),
            _event(
                "event.same.a",
                "message",
                20,
                {"body": "a", "visibility": "public"},
                priority=5,
            ),
            _event("event.same.b", "message", 20, {"body": "b", "visibility": "public"}),
        ]
    )
    first = _compile(_scenario(events))
    second = _compile(_scenario(list(reversed(events))))
    same_tick = tuple(event.id for event in first.events if event.trigger.tick == 20)
    assert same_tick == ("event.same.a", "event.same.b", "event.same.c")
    assert first.resolved_hash == second.resolved_hash


@pytest.mark.parametrize(
    ("mutate", "code"),
    (
        (lambda events: events[0].update(event_type="run_python"), "scenario.event_type_invalid"),
        (lambda events: events[0].update(untrusted_field=True), "scenario.event_payload_invalid"),
        (lambda events: events[0].update(payload={}), "scenario.event_payload_invalid"),
        (
            lambda events: events[0].update(trigger={"kind": "tick", "tick": 101}),
            "scenario.event_tick_invalid",
        ),
        (
            lambda events: events[0].update(depends_on=["event.missing"]),
            "scenario.event_dependency_missing",
        ),
        (
            lambda events: events[0].update(depends_on=["event.spawn"]),
            "scenario.event_dependency_self",
        ),
    ),
)
def test_unknown_extra_missing_tick_and_dependency_errors_are_stable(
    mutate: Any, code: str
) -> None:
    events = _events()
    mutate(events)
    _assert_error(_scenario(events), code, ("events", "0"))


def test_duplicate_event_ids_and_dependency_cycles_are_rejected() -> None:
    events = _events()
    events[1]["id"] = events[0]["id"]
    _assert_error(_scenario(events), "scenario.event_duplicate", ("events",))
    events = _events()
    events[0]["depends_on"] = ["event.message"]
    _assert_error(_scenario(events), "scenario.event_dependency_cycle", ("events",))


@pytest.mark.parametrize(
    ("event_id", "field", "value", "code"),
    (
        (
            "event.message",
            "recipient_entity_ids",
            ["entity.missing"],
            "scenario.event_reference_missing",
        ),
        ("event.zone", "zone_id", "zone.missing", "scenario.event_reference_missing"),
        (
            "event.suppress",
            "component_ref",
            "sensor.missing@2.1.0",
            "scenario.event_component_invalid",
        ),
        ("event.effect", "effect_ref", "effect.missing@2.1.0", "scenario.event_effect_invalid"),
        ("event.marker", "zone_id", "zone.missing", "scenario.event_reference_missing"),
    ),
)
def test_entity_zone_component_effect_and_marker_references_are_validated(
    event_id: str, field: str, value: Any, code: str
) -> None:
    events = _events()
    event = next(item for item in events if item["id"] == event_id)
    event["payload"][field] = value
    _assert_error(_scenario(events), code, ("events",))


def test_spawn_despawn_and_reference_lifecycle_are_validated() -> None:
    events = _events()
    spawn = next(item for item in events if item["id"] == "event.spawn")
    spawn["payload"]["entity"]["id"] = "entity.existing"
    _assert_error(_scenario(events), "scenario.event_lifecycle_conflict", ("events",))
    events = _events()
    despawn = next(item for item in events if item["id"] == "event.despawn")
    despawn["trigger"]["tick"] = 9
    _assert_error(_scenario(events), "scenario.event_lifecycle_invalid", ("events",))
    events = _events()
    message = next(item for item in events if item["id"] == "event.message")
    message["trigger"]["tick"] = 9
    message["depends_on"] = []
    _assert_error(_scenario(events), "scenario.event_reference_outside_lifecycle", ("events",))


def test_jamming_pairs_and_order_are_validated() -> None:
    events = _events()
    end = next(item for item in events if item["id"] == "event.jam.end")
    end["payload"]["session_id"] = "jam/unpaired"
    _assert_error(_scenario(events), "scenario.event_jamming_pair_invalid", ("events",))
    events = _events()
    end = next(item for item in events if item["id"] == "event.jam.end")
    end["trigger"]["tick"] = 13
    end["depends_on"] = []
    _assert_error(_scenario(events), "scenario.event_jamming_order_invalid", ("events",))


def test_apply_effect_cannot_directly_mutate_health() -> None:
    events = _events()
    effect = next(item for item in events if item["id"] == "event.effect")
    effect["payload"]["health"] = 0.0
    _assert_error(_scenario(events), "scenario.event_payload_forbidden", ("events", "payload"))


def test_message_visibility_and_recipient_endpoints_are_strict() -> None:
    events = _events()
    message = next(item for item in events if item["id"] == "event.message")
    message["payload"]["visibility"] = "leak_everything"
    _assert_error(_scenario(events), "scenario.event_visibility_invalid", ("events",))
    events = _events()
    message = next(item for item in events if item["id"] == "event.message")
    message["payload"]["recipient_controller_slots"] = ["controller/missing"]
    _assert_error(_scenario(events), "scenario.event_reference_missing", ("events",))


def test_event_roundtrip_is_catalog_free_and_contains_no_executable_or_source_data() -> None:
    resolved = _compile(_scenario())
    encoded = resolved.to_json()
    restored: Any = ResolvedScenarioV2.from_json(encoded)
    assert restored == resolved
    assert json.loads(encoded)["events"]
    assert not any(
        token in encoded
        for token in ("source_yaml", "source_path", "python", "callable", "catalog_resolver")
    )


def _rehashed_event_json(resolved: Any, mutate: Any) -> str:
    payload: dict[str, Any] = json.loads(resolved.to_json())
    mutate(payload)
    resolved_type: Any = ResolvedScenarioV2
    payload["resolved_hash"] = resolved_type.compute_resolved_hash(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda payload: payload["events"][0].update(event_type="run_python"),
        lambda payload: payload["events"][7]["payload"].update(health=0.0),
        lambda payload: payload["events"][1].update(depends_on=["event.missing"]),
        lambda payload: payload["events"][0]["payload"]["entity"].update(id="entity.existing"),
        lambda payload: payload["events"][7]["payload"]["effect_binding"].update(
            exact_ref="effect.missing@2.1.0"
        ),
    ),
)
def test_from_json_revalidates_event_type_payload_dependency_lifecycle_and_resource(
    mutate: Any,
) -> None:
    encoded = _rehashed_event_json(_compile(_scenario()), mutate)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(encoded)
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_dependency_predecessor_cannot_occur_after_dependent() -> None:
    events = _events()
    zone = next(item for item in events if item["id"] == "event.zone")
    weather = next(item for item in events if item["id"] == "event.weather")
    weather["depends_on"] = ["event.zone"]
    zone["trigger"]["tick"] = 13
    weather["trigger"]["tick"] = 12
    _assert_error(_scenario(events), "scenario.event_dependency_temporal_invalid", ("events",))


def test_resolved_event_order_is_nondecreasing_and_respects_every_dependency() -> None:
    resolved = _compile(_scenario())
    ticks = tuple(event.trigger.tick for event in resolved.events)
    assert ticks == tuple(sorted(ticks))
    indexes = {event.id: index for index, event in enumerate(resolved.events)}
    for event in resolved.events:
        assert all(indexes[dependency] < indexes[event.id] for dependency in event.depends_on)


@pytest.mark.parametrize(
    ("event_id", "field", "value"),
    (
        ("event.suppress", "duration_ticks", 0),
        ("event.suppress", "duration_ticks", -1),
        ("event.message", "body", ""),
        ("event.message", "body", "x" * 4097),
        ("event.message", "sender_entity_id", ""),
        ("event.jam.start", "session_id", ""),
        ("event.marker", "marker_id", ""),
    ),
)
def test_typed_event_values_have_positive_duration_and_bounded_nonempty_strings(
    event_id: str, field: str, value: Any
) -> None:
    events = _events()
    event = next(item for item in events if item["id"] == event_id)
    event["payload"][field] = value
    _assert_error(_scenario(events), "scenario.event_value_invalid", ("events",))


def test_message_recipients_are_unique_and_typed() -> None:
    events = _events()
    message = next(item for item in events if item["id"] == "event.message")
    message["payload"]["recipient_entity_ids"] = ["entity.spawned", "entity.spawned"]
    _assert_error(_scenario(events), "scenario.event_recipient_duplicate", ("events",))
    events = _events()
    message = next(item for item in events if item["id"] == "event.message")
    message["payload"]["recipient_entity_ids"] = "entity.spawned"
    _assert_error(_scenario(events), "scenario.event_value_invalid", ("events",))


@pytest.mark.parametrize(
    "selector",
    (
        {},
        {"unknown": ["entity.existing"]},
        {"entity_ids": []},
        {"entity_ids": "entity.existing"},
        {"entity_ids": [7]},
    ),
)
def test_apply_effect_selector_is_nonempty_typed_and_whitelisted(selector: Any) -> None:
    events = _events()
    effect = next(item for item in events if item["id"] == "event.effect")
    effect["payload"]["target_selector"] = selector
    _assert_error(_scenario(events), "scenario.event_selector_invalid", ("events",))


@pytest.mark.parametrize(
    "duplicate_id",
    ("event.jam.start", "event.jam.end", "event.despawn", "event.spawn"),
)
def test_duplicate_lifecycle_and_jamming_session_transitions_are_rejected(
    duplicate_id: str,
) -> None:
    events = _events()
    duplicate = copy.deepcopy(next(item for item in events if item["id"] == duplicate_id))
    duplicate["id"] += ".duplicate"
    duplicate["trigger"]["tick"] += 1
    events.append(duplicate)
    expected = (
        "scenario.event_jamming_pair_invalid"
        if "jam" in duplicate_id
        else "scenario.event_lifecycle_duplicate"
    )
    _assert_error(_scenario(events), expected, ("events",))


def test_v2_events_require_explicit_world_duration_without_legacy_bypass() -> None:
    payload = _scenario()
    payload["world"].pop("duration_ticks")
    _assert_error(payload, "scenario.event_time_bounds_missing", ("events",))


def test_spawn_weather_and_effect_are_runtime_ready_complete_resolved_payloads() -> None:
    resolved = _compile(_scenario())
    spawn = next(event for event in resolved.events if event.event_type == "spawn")
    entity = spawn.payload.entity
    assert entity.initial_state.position_m == (10.0, 20.0, 30.0)
    assert entity.composition.platform_ref == "platform.arbitrary@2.1.0"
    assert entity.resource_bindings["platforms"]
    assert entity.runtime_initial.ammunition == {}
    assert entity.domain == "synthetic-domain"
    weather = next(event for event in resolved.events if event.event_type == "weather_change")
    assert weather.payload.environment_binding.resource_type == "environments"
    assert weather.payload.environment_binding.content
    effect = next(event for event in resolved.events if event.event_type == "apply_effect")
    assert effect.payload.effect_binding.resource_type == "effects"
    assert effect.payload.damage_binding.resource_type == "damage_models"
    assert effect.payload.effect_binding.model_evidence.artifact_sha256 == PLUGIN_HASH
    encoded = resolved.to_json()
    del resolved
    restored: Any = ResolvedScenarioV2.from_json(encoded)
    assert restored.events and "catalog_resolver" not in encoded


def test_v2_all_legacy_tick_triggers_cannot_bypass_missing_duration() -> None:
    payload = _scenario()
    payload["world"].pop("duration_ticks")
    for event in payload["events"]:
        event["trigger"] = {"tick": event["trigger"]["tick"]}
    _assert_error(payload, "scenario.event_time_bounds_missing", ("events",))


def test_weather_resolved_payload_contains_binding_not_lazy_environment_ref() -> None:
    resolved = _compile(_scenario())
    weather = next(event for event in resolved.events if event.event_type == "weather_change")
    assert weather.payload.environment_binding.exact_ref == "weather.arbitrary@2.1.0"
    assert "environment_ref" not in weather.payload.values
    assert "environment_ref" not in json.dumps(weather.payload.model_dump(mode="json"))


@pytest.mark.parametrize("predecessor_id", ("event.spawn", "event.jam.start"))
def test_spawn_and_jamming_dependencies_have_no_temporal_exemption(
    predecessor_id: str,
) -> None:
    events = _events()
    predecessor = next(item for item in events if item["id"] == predecessor_id)
    marker = next(item for item in events if item["id"] == "event.marker")
    predecessor["trigger"]["tick"] = 10
    marker["trigger"]["tick"] = 5
    marker["depends_on"] = [predecessor_id]
    _assert_error(_scenario(events), "scenario.event_dependency_temporal_invalid", ("events",))


@pytest.mark.parametrize(
    ("event_id", "path", "value"),
    (
        ("event.message", ("payload", "body"), ""),
        (
            "event.weather",
            ("payload", "environment_binding", "exact_ref"),
            "weather.missing@2.1.0",
        ),
        (
            "event.weather",
            ("payload", "environment_binding", "model_ref"),
            "models.forged@2.0.0",
        ),
        (
            "event.weather",
            ("payload", "environment_binding", "content", "state"),
            "forged",
        ),
        (
            "event.weather",
            ("payload", "environment_binding", "content_hash"),
            "sha256:" + "0" * 64,
        ),
        (
            "event.spawn",
            ("payload", "entity", "resource_bindings", "platforms", 0, "content_hash"),
            "sha256:" + "1" * 64,
        ),
        (
            "event.spawn",
            ("payload", "entity", "resource_bindings", "platforms", 0, "content", "domain"),
            "forged-domain",
        ),
        (
            "event.effect",
            ("payload", "effect_binding", "content_hash"),
            "sha256:" + "2" * 64,
        ),
        (
            "event.effect",
            ("payload", "damage_binding", "model_ref"),
            "models.forged@2.0.0",
        ),
    ),
)
def test_from_json_uses_entity_grade_integrity_for_event_nested_resources(
    event_id: str, path: tuple[Any, ...], value: Any
) -> None:
    resolved = _compile(_scenario())

    def mutate(payload: dict[str, Any]) -> None:
        event = next(item for item in payload["events"] if item["id"] == event_id)
        target: Any = event
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    encoded = _rehashed_event_json(resolved, mutate)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(encoded)
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_all_legacy_shape_without_clock_priority_or_dependencies_still_fails_closed() -> None:
    payload = _scenario()
    payload["world"].pop("duration_ticks")
    for event in payload["events"]:
        event["trigger"] = {"tick": event["trigger"]["tick"]}
        event.pop("priority")
        event.pop("depends_on")
    _assert_error(payload, "scenario.event_time_bounds_missing", ("events",))


def test_generic_compiler_source_has_no_shape_based_legacy_event_bypass() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    assert "legacy_event_ids" not in source
    assert "legacy_event_document" not in source
    assert "legacy_normalized" not in source
    assert "if duration is None and not legacy" not in source


@pytest.mark.parametrize(
    ("event_id", "binding_name", "path", "value"),
    (
        ("event.weather", "environment_binding", ("normalized_content", "state"), "forged"),
        ("event.weather", "environment_binding", ("units", "speed_mps"), "knots"),
        ("event.spawn", "platform_binding", ("field_units", "position_m"), "km"),
        ("event.effect", "effect_binding", ("defaults", "mode", "value"), 99),
        (
            "event.effect",
            "effect_binding",
            ("defaults", "mode", "source", "id"),
            "models.forged@2.0.0",
        ),
        (
            "event.effect",
            "damage_binding",
            ("defaults", "period", "conversion_scale"),
            0.0,
        ),
    ),
)
def test_outer_rehash_cannot_hide_nested_binding_normalization_or_default_tamper(
    event_id: str, binding_name: str, path: tuple[str, ...], value: Any
) -> None:
    resolved = _compile(_scenario())

    def mutate(payload: dict[str, Any]) -> None:
        event = next(item for item in payload["events"] if item["id"] == event_id)
        if binding_name == "platform_binding":
            target = event["payload"]["entity"]["resource_bindings"]["platforms"][0]
        else:
            target = event["payload"][binding_name]
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value

    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(_rehashed_event_json(resolved, mutate))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_entity_and_event_bindings_use_one_shared_integrity_routine() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    routine = "_validate_resource_binding_integrity"
    assert f"def {routine}" in source
    assert source.count(f"{routine}(") >= 4
    assert "_validate_event_binding_integrity" not in source


@pytest.mark.parametrize(
    ("event_id", "field", "value"),
    (
        ("event.message", "visibility", "unknown-scope"),
        ("event.message", "recipient_entity_ids", "entity.spawned"),
        (
            "event.message",
            "recipient_entity_ids",
            ["entity.spawned", "entity.spawned"],
        ),
        ("event.message", "body", 7),
        ("event.message", "sender_entity_id", 7),
        ("event.suppress", "duration_ticks", 0),
        ("event.suppress", "duration_ticks", 1.5),
        ("event.suppress", "target_entity_id", 7),
        ("event.suppress", "component_ref", 7),
        ("event.jam.start", "session_id", ""),
        ("event.jam.start", "session_id", 7),
        ("event.jam.start", "source_entity_id", 7),
        ("event.jam.end", "session_id", 7),
        ("event.despawn", "entity_id", 7),
        ("event.zone", "zone_id", 7),
        ("event.marker", "marker_id", 7),
    ),
)
def test_from_json_revalidates_all_typed_payload_field_types_and_ranges(
    event_id: str, field: str, value: Any
) -> None:
    resolved = _compile(_scenario())

    def mutate(payload: dict[str, Any]) -> None:
        event = next(item for item in payload["events"] if item["id"] == event_id)
        event["payload"][field] = value

    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(_rehashed_event_json(resolved, mutate))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


@pytest.mark.parametrize(
    ("dependent_id", "predecessor_id"),
    (
        ("event.message", "event.spawn"),
        ("event.jam.end", "event.jam.start"),
    ),
)
def test_every_dependency_edge_is_checked_temporally_before_lifecycle_rules(
    dependent_id: str, predecessor_id: str
) -> None:
    events = _events()
    predecessor = next(item for item in events if item["id"] == predecessor_id)
    dependent = next(item for item in events if item["id"] == dependent_id)
    predecessor["trigger"]["tick"] = 10
    dependent["trigger"]["tick"] = 5
    dependent["depends_on"] = [predecessor_id]
    _assert_error(
        _scenario(events),
        "scenario.event_dependency_temporal_invalid",
        ("events",),
    )


def test_dependency_temporal_validation_has_no_event_type_exemptions() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    assert "dependent_references_spawn" not in source
    assert "paired_jamming_transition" not in source


def _spawn_entity_json(payload: dict[str, Any]) -> dict[str, Any]:
    event = next(item for item in payload["events"] if item["id"] == "event.spawn")
    return cast(dict[str, Any], event["payload"]["entity"])


def _set_spawn_fake_ammunition(payload: dict[str, Any]) -> None:
    entity = _spawn_entity_json(payload)
    entity["composition"]["ammunition"] = {"ammunition.fake@2.1.0": 2}
    entity["runtime_initial"]["ammunition"] = {"ammunition.fake@2.1.0": 2}


def _duplicate_spawn_binding(payload: dict[str, Any]) -> None:
    bindings = _spawn_entity_json(payload)["resource_bindings"]["platforms"]
    bindings.append(copy.deepcopy(bindings[0]))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda payload: _spawn_entity_json(payload)["composition"].update(
            platform_ref="platform.missing@2.1.0"
        ),
        lambda payload: _spawn_entity_json(payload)["composition"].update(
            dynamics_ref="platform.arbitrary@2.1.0"
        ),
        lambda payload: _spawn_entity_json(payload)["runtime_initial"]["initial_state"].update(
            position_m=[1.0, 2.0]
        ),
        lambda payload: _spawn_entity_json(payload)["runtime_initial"]["initial_state"].update(
            position_m=[float("nan"), 2.0, 3.0]
        ),
        lambda payload: _spawn_entity_json(payload)["runtime_initial"].update(
            ammunition={"ammunition.fake@2.1.0": 1}
        ),
        _set_spawn_fake_ammunition,
        lambda payload: _spawn_entity_json(payload)["composition"].update(
            ammunition={"ammunition.fake@2.1.0": 0}
        ),
        lambda payload: _spawn_entity_json(payload)["composition"].update(sensor_refs=[]),
        _duplicate_spawn_binding,
    ),
)
def test_outer_rehash_spawn_entity_tamper_uses_complete_entity_semantics(
    mutate: Any,
) -> None:
    resolved = _compile(_scenario())
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(_rehashed_event_json(resolved, mutate))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_static_and_spawned_entities_share_one_complete_semantic_validator() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    routine = "_validate_resolved_entity_integrity"
    assert f"def {routine}" in source
    assert source.count(f"{routine}(") >= 3
    assert "_validate_spawn_entity_integrity" not in source

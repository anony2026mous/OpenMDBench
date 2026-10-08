"""RF-03 RED contract for declarative v2 packages, compiler, and resolved output."""

from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)

PLUGIN_HASH = "sha256:" + "3" * 64


def _v2_api() -> tuple[Any, Any, Any, Any]:
    """Load the target API at test time so missing implementation is executable RED."""
    try:
        module = importlib.import_module("openmdbench.scenarios.declarative_v2")
    except ModuleNotFoundError:
        pytest.fail(
            "RF-03 implementation missing: openmdbench.scenarios.declarative_v2",
            pytrace=False,
        )
    required = (
        "ScenarioPackageV2",
        "ScenarioCompilerV2",
        "ResolvedScenarioV2",
        "CompilerErrorV2",
    )
    missing = tuple(name for name in required if not hasattr(module, name))
    if missing:
        pytest.fail(f"RF-03 public API missing: {', '.join(missing)}", pytrace=False)
    return tuple(getattr(module, name) for name in required)


def _catalog() -> CatalogV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.schema-only",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position_m": "m", "velocity_mps": "m/s"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256=PLUGIN_HASH,
            resource_types=("platforms", "dynamics", "environments"),
            field_units={"position_m": "m", "velocity_mps": "m/s"},
        ),
        lambda definition: definition,
    )
    registry.freeze()
    dynamics = CatalogResourceV2(
        schema_version="2.0",
        resource_type="dynamics",
        id="dynamics.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.schema-only@2.0.0",
        content={"compatible_platform_types": ["generic"], "mobile": True},
    )
    platform = CatalogResourceV2(
        schema_version="2.0",
        resource_type="platforms",
        id="platforms.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.schema-only@2.0.0",
        content={
            "platform_type": "generic",
            "domain": "air",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": [],
            "payload_capacity_kg": 0.0,
        },
    )
    environment = CatalogResourceV2(
        schema_version="2.0",
        resource_type="environments",
        id="environments.generic",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.schema-only@2.0.0",
        content={"state": "nominal"},
    )
    return CatalogV2(
        (platform, dynamics, environment),
        engine_version="2.0.0",
        model_registry=registry,
    )


def _entity(identifier: str = "entity-independent") -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "id": identifier,
        "faction_id": "faction.alpha",
        "platform_ref": "platforms.generic@2.0.0",
        "dynamics_ref": "dynamics.generic@2.0.0",
        "initial_state": {
            "schema_version": "2.0",
            "position_m": [100.0, 200.0, 300.0],
            "velocity_mps": [10.0, 0.0, 0.0],
            "heading_deg": 90.0,
        },
        "controller_slot": f"controllers/{identifier}",
        "tags": ["generic"],
    }


def _scenario(*, formation_count: int = 0) -> dict[str, Any]:
    formation = {
        "schema_version": "2.0",
        "id": "formation-independent",
        "count": formation_count,
        "id_pattern": "formed-{index:03d}",
        "entity_template": _entity("formation-template"),
        "offsets_m": [[0.0, 0.0, 0.0]],
    }
    return {
        "schema_version": "2.0",
        "scenario_id": "scenario.independent",
        "display_name": "Display name ignored by logical identity",
        "factions": [
            {"schema_version": "2.0", "id": "faction.alpha"},
            {"schema_version": "2.0", "id": "faction.bravo"},
            {"schema_version": "2.0", "id": "faction.civilian"},
        ],
        "relationships": [
            {
                "schema_version": "2.0",
                "source_faction_id": "faction.alpha",
                "target_faction_id": "faction.bravo",
                "relation": "hostile",
            },
            {
                "schema_version": "2.0",
                "source_faction_id": "faction.alpha",
                "target_faction_id": "faction.civilian",
                "relation": "protected",
            },
        ],
        "entities": [] if formation_count else [_entity()],
        "formations": [formation] if formation_count else [],
        "world": {
            "schema_version": "2.0",
            "coordinate_system": "local_m",
            "duration_ticks": 1000,
            "tick_seconds": 1.0,
            "boundary_policy": "constrain_motion",
            "zones": [
                {
                    "schema_version": "2.0",
                    "id": "zone.objective",
                    "geometry_type": "polygon",
                    "coordinates_m": [[0.0, 0.0], [1000.0, 0.0], [0.0, 1000.0]],
                    "tags": ["objective"],
                }
            ],
        },
        "events": [
            {
                "schema_version": "2.0",
                "id": "event.weather",
                "event_type": "weather_change",
                "trigger": {"kind": "tick", "tick": 5},
                "priority": 0,
                "depends_on": [],
                "payload": {"environment_ref": "environments.generic@2.0.0"},
            }
        ],
        "mission_rules": [
            {
                "schema_version": "2.0",
                "id": "rule.timeout",
                "priority": 10,
                "condition": {
                    "schema_version": "2.0",
                    "operator": "time",
                    "parameters": {"tick": 100},
                },
                "outcome": "success",
            }
        ],
        "score_metrics": [
            {
                "schema_version": "2.0",
                "id": "metric.survival",
                "value": None,
                "available": False,
                "weight": 1.0,
            }
        ],
    }


def _single_file_package(payload: dict[str, Any] | None = None) -> Any:
    Package, _Compiler, _Resolved, _Error = _v2_api()
    return Package.from_mapping(
        {
            "schema_version": "package@2.0",
            "package_name": "package-name-a",
            "scenario": payload or _scenario(),
        }
    )


def _write_multi_file(root: Path, scenario: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    sections = {
        "factions.yaml": {
            "factions": scenario["factions"],
            "relationships": scenario["relationships"],
        },
        "entities.yaml": {
            "entities": scenario["entities"],
            "formations": scenario["formations"],
        },
        "world.yaml": {"world": scenario["world"]},
        "events.yaml": {"events": scenario["events"]},
        "mission.yaml": {"mission_rules": scenario["mission_rules"]},
        "scoring.yaml": {"score_metrics": scenario["score_metrics"]},
    }
    manifest = {
        "schema_version": "package@2.0",
        "package_name": "package-name-b",
        "scenario_id": scenario["scenario_id"],
        "display_name": scenario["display_name"],
        "includes": list(sections),
    }
    (root / "scenario.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    for name, content in sections.items():
        (root / name).write_text(yaml.safe_dump(content), encoding="utf-8")


def test_single_and_multi_file_packages_are_semantically_equivalent(tmp_path: Path) -> None:
    Package, Compiler, _Resolved, _Error = _v2_api()
    scenario = _scenario()
    single = _single_file_package(scenario)
    _write_multi_file(tmp_path, scenario)
    multiple = Package.from_directory(tmp_path)

    first = Compiler(catalog=_catalog()).compile(single)
    second = Compiler(catalog=_catalog()).compile(multiple)
    assert first == second
    assert first.resolved_hash == second.resolved_hash


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_dynamic_factions_and_formation_expansion_are_stable(count: int) -> None:
    _Package, Compiler, _Resolved, _Error = _v2_api()
    scenario = _scenario(formation_count=count) if count else _scenario()
    if count == 0:
        scenario["entities"] = []
    package = _single_file_package(scenario)
    first = Compiler(catalog=_catalog()).compile(package)
    second = Compiler(catalog=_catalog()).compile(package)

    assert tuple(item.id for item in first.factions) == (
        "faction.alpha",
        "faction.bravo",
        "faction.civilian",
    )
    assert tuple(item.id for item in first.entities) == tuple(
        f"formed-{index:03d}" for index in range(count)
    )
    assert first.entities == second.entities


def test_resolved_carries_all_declarative_sections_and_controller_slots() -> None:
    _Package, Compiler, _Resolved, _Error = _v2_api()
    resolved = Compiler(catalog=_catalog()).compile(_single_file_package())

    assert resolved.relationships[0].relation == "hostile"
    assert resolved.world.zones[0].id == "zone.objective"
    assert resolved.world.boundary_policy == "constrain_motion"
    assert resolved.events[0].id == "event.weather"
    assert resolved.mission_rules[0].id == "rule.timeout"
    assert resolved.score_metrics[0].id == "metric.survival"
    assert resolved.entities[0].controller_slot == "controllers/entity-independent"


def test_resolved_is_deeply_frozen_json_roundtrippable_and_source_independent() -> None:
    _Package, Compiler, Resolved, _Error = _v2_api()
    resolved = Compiler(catalog=_catalog()).compile(_single_file_package())
    encoded = resolved.to_json()

    assert Resolved.from_json(encoded) == resolved
    assert "source_yaml" not in encoded and "source_path" not in encoded
    with pytest.raises((TypeError, AttributeError)):
        resolved.entities[0].initial_state.component_states["injected"] = {}
    with pytest.raises((TypeError, AttributeError)):
        resolved.world.zones += ()


def test_canonical_hash_ignores_mapping_order_display_name_and_package_name() -> None:
    Package, Compiler, _Resolved, _Error = _v2_api()
    first_payload = _scenario()
    second_payload = dict(reversed(tuple(first_payload.items())))
    second_payload["display_name"] = "Renamed for another user"
    first = _single_file_package(first_payload)
    second = Package.from_mapping(
        {
            "package_name": "renamed-package",
            "scenario": second_payload,
            "schema_version": "package@2.0",
        }
    )

    assert first.logical_hash == second.logical_hash
    assert first.content_hash == second.content_hash
    assert (
        Compiler(catalog=_catalog()).compile(first).resolved_hash
        == Compiler(catalog=_catalog()).compile(second).resolved_hash
    )


def test_compiler_error_has_stable_location_value_reason_and_suggestion() -> None:
    _Package, Compiler, _Resolved, Error = _v2_api()
    payload = _scenario()
    payload["entities"] = [_entity("one"), _entity("two")]
    payload["entities"][1]["controller_slot"] = payload["entities"][0]["controller_slot"]

    with pytest.raises(Error) as captured:
        Compiler(catalog=_catalog()).compile(_single_file_package(payload))
    error = captured.value
    assert error.code == "scenario.controller_slot_duplicate"
    assert error.file == "entities.yaml"
    assert error.path == ("entities", "1", "controller_slot")
    assert error.value == "controllers/one"
    assert error.reason and error.suggestion


@pytest.mark.parametrize(
    "bad_value",
    (
        math.nan,
        math.inf,
        -math.inf,
        (100.0, 200.0),
    ),
)
def test_invalid_or_nonfinite_coordinates_have_structured_errors(bad_value: Any) -> None:
    _Package, Compiler, _Resolved, Error = _v2_api()
    payload = _scenario()
    payload["entities"][0]["initial_state"]["position_m"] = bad_value
    with pytest.raises(Error) as captured:
        Compiler(catalog=_catalog()).compile(_single_file_package(payload))
    assert captured.value.code == "scenario.coordinate_invalid"
    assert captured.value.path[-1] == "position_m"
    assert captured.value.suggestion


def test_package_rejects_unsafe_duplicate_and_escaping_entries() -> None:
    Package, _Compiler, _Resolved, Error = _v2_api()
    unsafe_yaml = b"payload: !!python/object/apply:os.system ['echo unsafe']"
    cases = (
        (("../escape.yaml", b"{}"),),
        (("scenario.yaml", b"{}"), ("scenario.yaml", b"{}")),
        (("scenario.yaml", unsafe_yaml),),
    )
    for entries in cases:
        with pytest.raises(Error) as captured:
            Package.from_entries(entries)
        assert captured.value.code.startswith("package.")
        assert captured.value.file
        assert captured.value.reason and captured.value.suggestion

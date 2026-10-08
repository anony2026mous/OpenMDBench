"""RF-03 RED contract for runtime-ready resolved Catalog resource bindings."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from typing import Any

import pytest
from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
    ResourceTypeV2,
)
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)
from pydantic import ValidationError

ALL_TYPES: tuple[ResourceTypeV2, ...] = (
    "platforms",
    "dynamics",
    "collision_shapes",
    "sensors",
    "communications",
    "weapons",
    "ammunition",
    "effects",
    "damage_models",
    "energy",
    "loadouts",
    "visualization_assets",
)
PLUGIN_HASH = "sha256:" + "a" * 64


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
        version="2.4.1",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.runtime-binding@2.0.0",
        dependencies=dependencies,
        content=content,
    )


def _resources() -> dict[str, CatalogResourceV2]:
    damage = _resource("damage_models", "damage.arbitrary", {"effect_types": ["impulse"]})
    effect = _resource(
        "effects",
        "effect.arbitrary",
        {"effect_type": "impulse", "damage_model_ref": damage.exact_ref},
        (damage.exact_ref,),
    )
    weapon = _resource(
        "weapons",
        "weapon.arbitrary",
        {
            "allowed_platform_types": ["stratospheric-relay"],
            "target_domains": ["surface"],
            "effect_ref": effect.exact_ref,
            "range_m": 5000.0,
        },
        (effect.exact_ref,),
    )
    ammunition = _resource(
        "ammunition",
        "round.arbitrary",
        {"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 0.25},
        (weapon.exact_ref,),
    )
    dynamics = _resource(
        "dynamics",
        "motion.arbitrary",
        {
            "compatible_platform_types": ["stratospheric-relay"],
            "mobile": True,
            "maximum_speed_mps": 80.0,
        },
    )
    sensor = _resource(
        "sensors",
        "sensor.arbitrary",
        {"compatible_platform_types": ["stratospheric-relay"], "slot_type": "sensor"},
    )
    communication = _resource(
        "communications",
        "link.arbitrary",
        {
            "compatible_platform_types": ["stratospheric-relay"],
            "slot_type": "communication",
        },
    )
    energy = _resource(
        "energy",
        "power.arbitrary",
        {"compatible_platform_types": ["stratospheric-relay"], "capacity_j": 9000.0},
    )
    collision = _resource(
        "collision_shapes",
        "shape.arbitrary",
        {"compatible_domains": ["upper-atmosphere"], "shape": "sphere", "radius_m": 2.0},
    )
    visual = _resource(
        "visualization_assets",
        "visual.arbitrary",
        {"compatible_domains": ["upper-atmosphere"], "profile": "diamond"},
    )
    loadout = _resource(
        "loadouts",
        "payload.arbitrary",
        {
            "compatible_platform_types": ["stratospheric-relay"],
            "required_slots": ["payload"],
            "mass_kg": 4.0,
            "weapon_refs": [weapon.exact_ref],
            "ammunition_refs": [ammunition.exact_ref],
        },
        (weapon.exact_ref, ammunition.exact_ref),
    )
    platform = _resource(
        "platforms",
        "vehicle.arbitrary",
        {
            "platform_type": "stratospheric-relay",
            "domain": "upper-atmosphere",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": ["payload", "sensor", "communication"],
            "loadout_slots": ["payload"],
            "payload_capacity_kg": 20.0,
            "energy_ref": energy.exact_ref,
            "collision_shape_ref": collision.exact_ref,
            "visualization_ref": visual.exact_ref,
        },
        (energy.exact_ref, collision.exact_ref, visual.exact_ref),
    )
    return {
        item.resource_type: item
        for item in (
            platform,
            dynamics,
            sensor,
            communication,
            energy,
            collision,
            visual,
            loadout,
            weapon,
            ammunition,
            effect,
            damage,
        )
    }


def _catalog(
    *,
    artifact: str = "a",
    mutate: Callable[[dict[str, CatalogResourceV2]], None] | None = None,
    reverse: bool = False,
) -> CatalogV2:
    resources = _resources()
    if mutate is not None:
        mutate(resources)
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.runtime-binding",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"position_m": "m", "speed_mps": "m/s"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + artifact * 64,
            resource_types=ALL_TYPES,
            field_units={
                "position_m": "m",
                "speed_mps": "m/s",
                "scan_period_s": "s",
                "mode": "1",
            },
        ),
        lambda definition: definition,
    )
    registry.freeze()
    values = list(resources.values())
    return CatalogV2(
        reversed(values) if reverse else values,
        engine_version="2.0.0",
        model_registry=registry,
    )


def _entity(*, components: bool = True, rounds: int = 3) -> dict[str, Any]:
    resources = _resources()
    return {
        "schema_version": "2.0",
        "id": "entity.arbitrary",
        "faction_id": "faction.arbitrary",
        "platform_ref": resources["platforms"].exact_ref,
        "dynamics_ref": resources["dynamics"].exact_ref,
        "loadout_ref": resources["loadouts"].exact_ref if components else None,
        "component_refs": (
            [resources["sensors"].exact_ref, resources["communications"].exact_ref]
            if components
            else []
        ),
        "ammunition": {resources["ammunition"].exact_ref: rounds} if components else {},
        "target_domains": ["surface"] if components else [],
        "initial_state": {
            "schema_version": "2.0",
            "position_m": [1.0, 2.0, 3.0],
            "velocity_mps": [0.0, 0.0, 0.0],
            "heading_deg": 0.0,
        },
    }


def _scenario(*, components: bool = True, rounds: int = 3) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "scenario_id": "scenario.resource-expansion",
        "factions": [{"schema_version": "2.0", "id": "faction.arbitrary"}],
        "relationships": [],
        "entities": [_entity(components=components, rounds=rounds)],
        "formations": [],
        "world": {"schema_version": "2.0", "coordinate_system": "local_m", "zones": []},
        "events": [],
        "mission_rules": [],
        "score_metrics": [],
    }


def _compile(catalog: CatalogV2, payload: dict[str, Any] | None = None) -> Any:
    package = ScenarioPackageV2.from_mapping(
        {"schema_version": "package@2.0", "scenario": payload or _scenario()}
    )
    return ScenarioCompilerV2(catalog=catalog).compile(package)


def _binding_map(entity: Any) -> Mapping[str, tuple[Any, ...]]:
    bindings = entity.resource_bindings
    assert isinstance(bindings, Mapping)
    return bindings


def test_resolved_entity_embeds_complete_immutable_canonical_resource_graph() -> None:
    resolved = _compile(_catalog())
    bindings = _binding_map(resolved.entities[0])
    assert set(bindings) == set(ALL_TYPES)
    expected = _resources()
    for resource_type, values in bindings.items():
        assert values
        for binding in values:
            source = expected[resource_type]
            assert binding.exact_ref == source.exact_ref
            assert binding.resource_type == resource_type
            assert binding.version == source.version
            assert binding.content_hash == source.content_hash
            assert binding.model_ref == source.model_ref
            assert binding.content == source.content
            assert binding.units == {"position_m": "m", "speed_mps": "m/s"}
            with pytest.raises((TypeError, AttributeError)):
                binding.content["mutation"] = True


@pytest.mark.parametrize(("components", "rounds"), ((False, 0), (True, 0), (True, 11)))
def test_zero_one_many_compositions_are_expanded_and_inventory_is_runtime_initial_state(
    components: bool, rounds: int
) -> None:
    resolved = _compile(_catalog(), _scenario(components=components, rounds=rounds))
    entity = resolved.entities[0]
    expected_ammunition = {_resources()["ammunition"].exact_ref: rounds} if components else {}
    assert dict(entity.runtime_initial.ammunition) == expected_ammunition
    if components:
        assert "ammunition" not in entity.resource_bindings["ammunition"][0].content
    else:
        assert entity.resource_bindings.get("ammunition", ()) == ()
    assert entity.composition.target_domains == (("surface",) if components else ())
    assert entity.composition.sensor_refs == (
        (_resources()["sensors"].exact_ref,) if components else ()
    )


def test_compilation_deep_freezes_and_does_not_share_nested_runtime_or_definitions() -> None:
    first = _compile(_catalog())
    second = _compile(_catalog())
    assert first.entities[0].runtime_initial is not second.entities[0].runtime_initial
    assert first.entities[0].resource_bindings is not second.entities[0].resource_bindings
    with pytest.raises((TypeError, AttributeError)):
        first.entities[0].runtime_initial.ammunition["round.injected@2.4.1"] = 99
    assert "round.injected@2.4.1" not in second.entities[0].runtime_initial.ammunition


def test_top_level_records_all_authority_hashes_and_order_is_irrelevant() -> None:
    catalog = _catalog()
    reversed_catalog = _catalog(reverse=True)
    first = _compile(catalog)
    second = _compile(reversed_catalog)
    assert first.catalog_hash == catalog.content_hash
    assert first.model_registry_hash == catalog.model_registry.content_hash
    assert first.compiler_version == "2.0.0"
    assert first.resolved_hash == second.resolved_hash


def test_resource_or_plugin_artifact_change_changes_resolved_hash() -> None:
    baseline = _compile(_catalog())

    def change_sensor(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={"content": {**sensor.content, "range_m": 1234.0}}
        )

    assert baseline.resolved_hash != _compile(_catalog(mutate=change_sensor)).resolved_hash
    assert baseline.resolved_hash != _compile(_catalog(artifact="b")).resolved_hash


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        ("platform_ref", "vehicle.arbitrary", "scenario.resource_ref_invalid"),
        ("dynamics_ref", "missing.arbitrary@2.4.1", "scenario.resource_missing"),
        ("component_refs", ["payload.arbitrary@2.4.1"], "scenario.resource_type_mismatch"),
    ),
)
def test_inexact_missing_and_wrong_typed_refs_have_stable_compiler_errors(
    field: str, value: Any, code: str
) -> None:
    payload = _scenario()
    payload["entities"][0][field] = value
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(), payload)
    error = captured.value
    assert error.code == code
    assert error.file == "entities.yaml"
    assert field in error.path
    assert error.value is not None and error.reason and error.suggestion


def test_full_composition_validation_receives_every_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Any] = []
    original = CatalogV2.validate_full_composition

    def spy(instance: CatalogV2, composition: Any) -> bool:
        captured.append(composition)
        return original(instance, composition)

    monkeypatch.setattr(CatalogV2, "validate_full_composition", spy)
    _compile(_catalog())
    assert len(captured) == 1
    composition = captured[0]
    resources = _resources()
    assert composition.sensor_refs == (resources["sensors"].exact_ref,)
    assert composition.communication_refs == (resources["communications"].exact_ref,)
    assert composition.energy_ref == resources["energy"].exact_ref
    assert composition.collision_shape_ref == resources["collision_shapes"].exact_ref
    assert composition.visualization_ref == resources["visualization_assets"].exact_ref
    assert composition.ammunition == {resources["ammunition"].exact_ref: 3}
    assert composition.target_domains == ("surface",)


@pytest.mark.parametrize(
    "reason",
    (
        "missing dependency effect.arbitrary@2.4.1",
        "definition model reference mismatch",
        "model field unit is incompatible for speed_mps",
    ),
)
def test_dependency_model_and_unit_failures_are_stable_compile_errors(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    def reject(_instance: CatalogV2, _composition: Any) -> bool:
        raise CatalogResolutionErrorV2(reason)

    monkeypatch.setattr(CatalogV2, "validate_full_composition", reject)
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog())
    error = captured.value
    assert error.code == "scenario.composition_invalid"
    assert error.file == "entities.yaml"
    assert error.path[:2] == ("entities", "0")
    assert reason in error.reason
    assert error.value is not None and error.suggestion


def test_json_roundtrip_is_catalog_free_and_contains_no_lazy_or_source_obligation() -> None:
    resolved = _compile(_catalog())
    encoded = resolved.to_json()
    restored: Any = ResolvedScenarioV2.from_json(encoded)
    assert restored == resolved
    document = json.loads(encoded)
    assert document["entities"][0]["resource_bindings"]
    forbidden = ("source_yaml", "source_path", "catalog_resolver", "lazy", "callable")
    assert not any(token in encoded for token in forbidden)
    del resolved
    assert restored.entities[0].resource_bindings["platforms"][0].content["domain"] == (
        "upper-atmosphere"
    )


def _rehashed_tampered_json(resolved: Any, mutate: Callable[[dict[str, Any]], None]) -> str:
    payload: dict[str, Any] = json.loads(resolved.to_json())
    mutate(payload)
    resolved_type: Any = ResolvedScenarioV2
    payload["resolved_hash"] = resolved_type.compute_resolved_hash(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _assert_integrity_rejected(encoded: str) -> None:
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(encoded)
    error = captured.value
    assert getattr(error, "code", None) == "resolved.integrity_invalid"
    assert str(error)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda payload: payload["entities"][0]["resource_bindings"]["damage_models"].clear(),
        lambda payload: payload["entities"][0]["composition"].update(
            dynamics_ref="motion.missing@2.4.1"
        ),
        lambda payload: payload["entities"][0]["resource_bindings"]["effects"][0].update(
            dependencies=[]
        ),
        lambda payload: payload["entities"][0]["resource_bindings"]["effects"][0].update(
            resource_type="weapons"
        ),
        lambda payload: payload["entities"][0]["resource_bindings"]["effects"][0]["content"].update(
            effect_type="forged"
        ),
    ),
)
def test_recomputed_outer_hash_cannot_hide_broken_binding_closure(mutate: Any) -> None:
    resolved = _compile(_catalog())
    _assert_integrity_rejected(_rehashed_tampered_json(resolved, mutate))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("schema_version", "9.9"),
        ("engine_compatibility", ">=9.0.0"),
        ("version", "2.4.2"),
        ("model_ref", "models.forged@2.0.0"),
        ("content_hash", "sha256:" + "0" * 64),
        ("units", {"speed_mps": "knots"}),
    ),
)
def test_binding_canonical_identity_tampering_is_rejected_after_outer_rehash(
    field: str, value: Any
) -> None:
    resolved = _compile(_catalog())

    def mutate(payload: dict[str, Any]) -> None:
        payload["entities"][0]["resource_bindings"]["dynamics"][0][field] = value

    _assert_integrity_rejected(_rehashed_tampered_json(resolved, mutate))


def test_binding_has_complete_resource_identity_and_recomputable_definition_hash() -> None:
    resolved = _compile(_catalog())
    for bindings in resolved.entities[0].resource_bindings.values():
        for binding in bindings:
            assert binding.schema_version == "2.0"
            assert binding.engine_compatibility == ">=2.0.0,<3.0.0"
            rebuilt = CatalogResourceV2(
                schema_version=binding.schema_version,
                resource_type=binding.resource_type,
                id=binding.id,
                version=binding.version,
                engine_compatibility=binding.engine_compatibility,
                model_id=binding.model_ref,
                dependencies=binding.dependencies,
                content=dict(binding.content),
            )
            assert rebuilt.exact_ref == binding.exact_ref
            assert rebuilt.content_hash == binding.content_hash


def test_composition_refs_and_dependency_closure_have_exactly_one_typed_binding() -> None:
    resolved = _compile(_catalog())
    entity = resolved.entities[0]
    flattened = [binding for values in entity.resource_bindings.values() for binding in values]
    by_ref: dict[str, list[Any]] = {}
    for binding in flattened:
        by_ref.setdefault(binding.exact_ref, []).append(binding)
    assert all(len(values) == 1 for values in by_ref.values())
    direct_refs = {
        entity.composition.platform_ref: "platforms",
        entity.composition.dynamics_ref: "dynamics",
        entity.composition.loadout_ref: "loadouts",
        entity.composition.energy_ref: "energy",
        entity.composition.collision_shape_ref: "collision_shapes",
        entity.composition.visualization_ref: "visualization_assets",
        **{ref: "sensors" for ref in entity.composition.sensor_refs},
        **{ref: "communications" for ref in entity.composition.communication_refs},
        **{ref: "ammunition" for ref in entity.composition.ammunition},
    }
    for reference, resource_type in direct_refs.items():
        assert reference is not None
        assert len(by_ref[reference]) == 1
        assert by_ref[reference][0].resource_type == resource_type
    for binding in flattened:
        for dependency in binding.dependencies:
            assert len(by_ref[dependency]) == 1


def test_binding_model_evidence_matches_top_registry_snapshot() -> None:
    resolved = _compile(_catalog())
    snapshot = {item.exact_ref: item for item in resolved.model_registry_snapshot}
    assert resolved.model_registry_hash
    for bindings in resolved.entities[0].resource_bindings.values():
        for binding in bindings:
            evidence = binding.model_evidence
            metadata = snapshot[binding.model_ref]
            assert evidence.artifact_sha256 == metadata.artifact_sha256 == PLUGIN_HASH
            assert evidence.interface_version == metadata.interface_version == "2.0"
            assert evidence.input_schema == metadata.input_schema == "catalog-resource@2.0"
            assert evidence.output_schema == metadata.output_schema == "runtime-component@2.0"
            assert evidence.model_ref == binding.model_ref


def test_declared_defaults_are_materialized_with_source_evidence() -> None:
    def declare_default(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={
                "content": {
                    **sensor.content,
                    "required_defaults": ["scan_period_s"],
                    "defaults": {
                        "scan_period_s": {
                            "value": 2.0,
                            "unit": "s",
                            "source": {
                                "kind": "model_metadata",
                                "id": "models.runtime-binding@2.0.0",
                            },
                        }
                    },
                }
            }
        )

    resolved = _compile(_catalog(mutate=declare_default))
    binding = resolved.entities[0].resource_bindings["sensors"][0]
    assert binding.normalized_content["scan_period_s"] == 2.0
    assert binding.defaults["scan_period_s"].source.kind == "model_metadata"
    assert binding.defaults["scan_period_s"].source.id == "models.runtime-binding@2.0.0"
    assert binding.defaults["scan_period_s"].unit == "s"


def test_unresolved_required_default_fails_compile_with_stable_error() -> None:
    def require_without_default(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={"content": {**sensor.content, "required_defaults": ["scan_period_s"]}}
        )

    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(mutate=require_without_default))
    error = captured.value
    assert error.code == "scenario.resource_default_missing"
    assert error.file == "entities.yaml"
    assert "sensor" in error.reason.lower()
    assert error.path and error.value is not None and error.suggestion


@pytest.mark.parametrize(
    "required",
    (
        "scan_period_s",
        {"scan_period_s": True},
        ["scan_period_s", "scan_period_s"],
        [""],
        [7],
    ),
)
def test_required_defaults_are_unique_nonempty_string_sequences(required: Any) -> None:
    def malformed(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={"content": {**sensor.content, "required_defaults": required}}
        )

    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(mutate=malformed))
    error = captured.value
    assert error.code == "scenario.resource_default_schema_invalid"
    assert error.file == "entities.yaml"
    assert error.value is not None and error.reason and error.suggestion


@pytest.mark.parametrize(
    ("source", "unit", "code"),
    (
        ("model", "s", "scenario.resource_default_source_invalid"),
        ({"kind": "invented", "id": "anything"}, "s", "scenario.resource_default_source_invalid"),
        (
            {"kind": "model_metadata", "id": "models.missing@2.0.0"},
            "s",
            "scenario.resource_default_source_invalid",
        ),
        (
            {"kind": "model_metadata", "id": "models.runtime-binding@2.0.0"},
            "fortnight",
            "scenario.resource_default_unit_invalid",
        ),
    ),
)
def test_default_source_and_unit_match_typed_model_contract(
    source: Any, unit: str, code: str
) -> None:
    def malformed(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={
                "content": {
                    **sensor.content,
                    "required_defaults": ["scan_period_s"],
                    "defaults": {"scan_period_s": {"value": 2.0, "unit": unit, "source": source}},
                }
            }
        )

    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(mutate=malformed))
    assert captured.value.code == code
    assert captured.value.file == "entities.yaml"


def test_explicit_trusted_unit_conversion_is_materialized_canonically() -> None:
    def converted(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        resources["sensors"] = sensor.model_copy(
            update={
                "content": {
                    **sensor.content,
                    "required_defaults": ["scan_period_s"],
                    "trusted_unit_conversions": {
                        "si.ms-to-s@1.0": {"from": "ms", "to": "s", "scale": 0.001}
                    },
                    "defaults": {
                        "scan_period_s": {
                            "value": 2000.0,
                            "unit": "ms",
                            "conversion_ref": "si.ms-to-s@1.0",
                            "source": {
                                "kind": "model_metadata",
                                "id": "models.runtime-binding@2.0.0",
                            },
                        }
                    },
                }
            }
        )

    resolved = _compile(_catalog(mutate=converted))
    default = resolved.entities[0].resource_bindings["sensors"][0].defaults["scan_period_s"]
    assert default.input_value == 2000.0 and default.input_unit == "ms"
    assert default.value == 2.0 and default.unit == "s"
    assert default.conversion_ref == "si.ms-to-s@1.0"


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("defaults", "scan_period_s", "value"), 99.0),
        (("defaults", "scan_period_s", "unit"), "fortnight"),
        (("normalized_content", "scan_period_s"), 99.0),
        (("model_evidence", "trusted"), False),
        (("model_evidence", "deterministic"), False),
        (("model_evidence", "interface_version"), "9.0"),
        (("model_evidence", "resource_types"), ["weapons"]),
    ),
)
def test_from_json_revalidates_default_and_model_evidence_after_outer_rehash(
    path: tuple[str, ...], value: Any
) -> None:
    resolved = _compile(_catalog())

    def mutate(payload: dict[str, Any]) -> None:
        target = payload["entities"][0]["resource_bindings"]["sensors"][0]
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value

    _assert_integrity_rejected(_rehashed_tampered_json(resolved, mutate))


def _default_resource_mutation(
    *, field: str, value: Any, unit: str, value_type: str | None = None
) -> Callable[[dict[str, CatalogResourceV2]], None]:
    def mutate(resources: dict[str, CatalogResourceV2]) -> None:
        sensor = resources["sensors"]
        content = {
            **sensor.content,
            "required_defaults": [field],
            "defaults": {
                field: {
                    "value": value,
                    "unit": unit,
                    "source": {
                        "kind": "model_metadata",
                        "id": "models.runtime-binding@2.0.0",
                    },
                }
            },
        }
        if value_type is not None:
            content["default_value_types"] = {field: value_type}
        resources["sensors"] = sensor.model_copy(update={"content": content})

    return mutate


@pytest.mark.parametrize(
    "value",
    ("2.0", [2.0], {"value": 2.0}, True),
)
def test_physical_default_requires_finite_non_bool_number(value: Any) -> None:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(
            _catalog(
                mutate=_default_resource_mutation(field="scan_period_s", value=value, unit="s")
            )
        )
    error = captured.value
    assert error.code == "scenario.resource_default_value_invalid"
    assert error.file == "entities.yaml"
    assert error.value is not None and error.reason and error.suggestion


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_nonfinite_physical_default_is_rejected_at_catalog_schema_boundary(
    value: float,
) -> None:
    with pytest.raises(ValidationError, match="numeric values must be finite"):
        _catalog(mutate=_default_resource_mutation(field="scan_period_s", value=value, unit="s"))


@pytest.mark.parametrize("value_type", (None, "object", "floatish", ""))
def test_dimensionless_default_requires_controlled_value_type_schema(
    value_type: str | None,
) -> None:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(
            _catalog(
                mutate=_default_resource_mutation(
                    field="mode", value=True, unit="1", value_type=value_type
                )
            )
        )
    assert captured.value.code == "scenario.resource_default_schema_invalid"


@pytest.mark.parametrize(
    ("value_type", "value"),
    (
        ("number", True),
        ("number", "1"),
        ("integer", 1.0),
        ("integer", False),
        ("boolean", 1),
        ("string", True),
    ),
)
def test_dimensionless_default_enforces_exact_declared_value_type(
    value_type: str, value: Any
) -> None:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(
            _catalog(
                mutate=_default_resource_mutation(
                    field="mode", value=value, unit="1", value_type=value_type
                )
            )
        )
    assert captured.value.code == "scenario.resource_default_value_invalid"


@pytest.mark.parametrize(
    ("value_type", "value"),
    (("number", 1.5), ("integer", 1), ("boolean", True), ("string", "automatic")),
)
def test_dimensionless_controlled_value_types_have_valid_examples(
    value_type: str, value: Any
) -> None:
    resolved = _compile(
        _catalog(
            mutate=_default_resource_mutation(
                field="mode", value=value, unit="1", value_type=value_type
            )
        )
    )
    default = resolved.entities[0].resource_bindings["sensors"][0].defaults["mode"]
    assert default.value == value
    assert default.value_type == value_type


@pytest.mark.parametrize("scale", (True, 0.0, -0.1, "0.001"))
def test_trusted_conversion_scale_must_be_finite_positive_number(scale: Any) -> None:
    def invalid_conversion(resources: dict[str, CatalogResourceV2]) -> None:
        mutate = _default_resource_mutation(field="scan_period_s", value=2000.0, unit="ms")
        mutate(resources)
        sensor = resources["sensors"]
        content = dict(sensor.content)
        content["trusted_unit_conversions"] = {
            "si.ms-to-s@1.0": {"from": "ms", "to": "s", "scale": scale}
        }
        content["defaults"]["scan_period_s"]["conversion_ref"] = "si.ms-to-s@1.0"
        resources["sensors"] = sensor.model_copy(update={"content": content})

    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(mutate=invalid_conversion))
    assert captured.value.code == "scenario.resource_default_conversion_invalid"


@pytest.mark.parametrize("scale", (math.nan, math.inf, -math.inf))
def test_nonfinite_conversion_scale_is_rejected_at_catalog_schema_boundary(
    scale: float,
) -> None:
    def invalid_conversion(resources: dict[str, CatalogResourceV2]) -> None:
        mutate = _default_resource_mutation(field="scan_period_s", value=2000.0, unit="ms")
        mutate(resources)
        sensor = resources["sensors"]
        content = dict(sensor.content)
        content["trusted_unit_conversions"] = {
            "si.ms-to-s@1.0": {"from": "ms", "to": "s", "scale": scale}
        }
        content["defaults"]["scan_period_s"]["conversion_ref"] = "si.ms-to-s@1.0"
        resources["sensors"] = sensor.model_copy(update={"content": content})

    with pytest.raises(ValidationError, match="numeric values must be finite"):
        _catalog(mutate=invalid_conversion)


def test_trusted_conversion_rejects_non_numeric_input() -> None:
    def invalid_input(resources: dict[str, CatalogResourceV2]) -> None:
        mutate = _default_resource_mutation(field="scan_period_s", value="2000", unit="ms")
        mutate(resources)
        sensor = resources["sensors"]
        content = dict(sensor.content)
        content["trusted_unit_conversions"] = {
            "si.ms-to-s@1.0": {"from": "ms", "to": "s", "scale": 0.001}
        }
        content["defaults"]["scan_period_s"]["conversion_ref"] = "si.ms-to-s@1.0"
        resources["sensors"] = sensor.model_copy(update={"content": content})

    with pytest.raises(CompilerErrorV2) as captured:
        _compile(_catalog(mutate=invalid_input))
    assert captured.value.code == "scenario.resource_default_value_invalid"


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("defaults", "mode", "value"), True),
        (("defaults", "mode", "value_type"), "object"),
        (("defaults", "scan_period_s", "conversion_scale"), 0.0),
        (("defaults", "scan_period_s", "conversion_scale"), math.inf),
    ),
)
def test_from_json_revalidates_default_value_type_and_conversion_scale(
    path: tuple[str, ...], value: Any
) -> None:
    resolved = _compile(_catalog())

    def mutate(payload: dict[str, Any]) -> None:
        target = payload["entities"][0]["resource_bindings"]["sensors"][0]
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value

    _assert_integrity_rejected(_rehashed_tampered_json(resolved, mutate))

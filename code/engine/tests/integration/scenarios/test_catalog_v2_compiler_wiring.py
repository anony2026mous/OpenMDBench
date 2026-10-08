"""RF-02 production-path contracts for atomic CatalogV2 composition validation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    CatalogV2,
    EntityCompositionV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
    ResourceTypeV2,
)
from openmdbench.scenarios import compiler as compiler_module
from openmdbench.scenarios.compiler import ScenarioCompileError, ScenarioCompiler
from openmdbench.scenarios.package import ScenarioPackageRef

MAP_RAW_HASH = "sha256:1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675"
MAP_XY_HASH = "sha256:6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067"
PLUGIN_HASH = "sha256:" + "a" * 64
ALL_RESOURCE_TYPES: tuple[ResourceTypeV2, ...] = (
    "maps",
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
    "environments",
    "loadouts",
    "visualization_assets",
    "missions",
    "scoring",
    "trusted_model_plugins",
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
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.test-data@2.0.0",
        dependencies=dependencies,
        content=content,
    )


def _catalog(
    *, mutation: Callable[[dict[str, CatalogResourceV2]], None] | None = None
) -> CatalogV2:
    damage = _resource("damage_models", "damage.test", {"effect_types": ["blast"]})
    effect = _resource(
        "effects",
        "effects.test",
        {"effect_type": "blast", "damage_model_ref": damage.exact_ref},
        (damage.exact_ref,),
    )
    weapon = _resource(
        "weapons",
        "weapons.test",
        {
            "allowed_platform_types": ["uav"],
            "target_domains": ["air"],
            "effect_ref": effect.exact_ref,
        },
        (effect.exact_ref,),
    )
    ammunition = _resource(
        "ammunition",
        "ammunition.test",
        {"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 1.0},
        (weapon.exact_ref,),
    )
    dynamics = _resource(
        "dynamics",
        "dynamics.test",
        {"compatible_platform_types": ["uav"], "mobile": True, "maximum_speed_mps": 100.0},
    )
    sensor = _resource(
        "sensors",
        "sensors.test",
        {"compatible_platform_types": ["uav"], "slot_type": "sensor"},
    )
    communication = _resource(
        "communications",
        "communications.test",
        {"compatible_platform_types": ["uav"], "slot_type": "communication"},
    )
    energy = _resource(
        "energy",
        "energy.test",
        {"compatible_platform_types": ["uav"], "capacity_j": 1000.0},
    )
    collision = _resource(
        "collision_shapes",
        "collision.test",
        {"compatible_domains": ["air"], "shape": "sphere"},
    )
    visual = _resource(
        "visualization_assets",
        "visual.test",
        {"compatible_domains": ["air"], "profile": "generic"},
    )
    loadout = _resource(
        "loadouts",
        "loadouts.test",
        {
            "compatible_platform_types": ["uav"],
            "required_slots": ["payload"],
            "mass_kg": 10.0,
            "weapon_refs": [weapon.exact_ref],
            "ammunition_refs": [ammunition.exact_ref],
        },
        (weapon.exact_ref, ammunition.exact_ref),
    )
    platform = _resource(
        "platforms",
        "platforms.test",
        {
            "platform_type": "uav",
            "domain": "air",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": ["payload", "sensor", "communication"],
            "loadout_slots": ["payload"],
            "payload_capacity_kg": 100.0,
            "energy_ref": energy.exact_ref,
            "collision_shape_ref": collision.exact_ref,
            "visualization_ref": visual.exact_ref,
        },
        (energy.exact_ref, collision.exact_ref, visual.exact_ref),
    )
    resources: dict[str, CatalogResourceV2] = {
        item.resource_type: item
        for item in (
            damage,
            effect,
            weapon,
            ammunition,
            dynamics,
            sensor,
            communication,
            energy,
            collision,
            visual,
            loadout,
            platform,
        )
    }
    if mutation is not None:
        mutation(resources)
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.test-data",
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
            resource_types=ALL_RESOURCE_TYPES,
            field_units={},
        ),
        lambda definition: definition,
    )
    registry.freeze()
    return CatalogV2(resources.values(), engine_version="2.0.0", model_registry=registry)


def _package(tmp_path: Path, *, include_wave: bool = True) -> ScenarioPackageRef:
    scenario = {
        "schema_version": "1.0",
        "scenario_id": "GENERIC-CATALOG-WIRING",
        "category": "generic",
        "difficulty": "easy",
        "world": {"bounds": [0.0, 0.0, 1000.0, 1000.0], "map_id": "weihai_v1"},
        "public": {
            "name": "Generic catalog wiring",
            "background": "Generic catalog wiring validation.",
            "primary_objectives": ["Validate composition"],
            "weather_forecast": "clear",
        },
        "entities": [],
        "spawn_counts": {"blue": {}, "red": {}},
        "time_limit_ticks": 100,
        "roe": [],
        "initial_weather": "clear",
        "success_conditions": ["timeout"],
        "failure_conditions": [],
        "scoring": {"weights": {}, "baseline_version": "2.0", "baseline": {}},
        "referee": {"opponent_intent": "", "hidden_events": [], "ground_truth": {}},
    }
    entity = {
        "id": "asset-static-template",
        "side": "red",
        "platform_ref": "platforms.test@2.0.0",
        "dynamics_ref": "dynamics.test@2.0.0",
        "loadout_ref": "loadouts.test@2.0.0",
        "sensor_refs": ["sensors.test@2.0.0"],
        "communication_ref": "communications.test@2.0.0",
        "initial_state": {
            "lon_deg": 122.28,
            "lat_deg": 37.54,
            "altitude_m": 900.0,
            "heading_deg": 90.0,
            "speed_mps": 30.0,
            "terrain": "air",
        },
        "inventory": {"weapons.test@2.0.0": 2},
    }
    composition: dict[str, Any] = {
        "schema_version": "composition@1.0",
        "scenario_id": "GENERIC-CATALOG-WIRING",
        "scenario_version": "2.0.0",
        "map": {
            "map_id": "weihai_v1",
            "version": "1.0",
            "raw_sha256": MAP_RAW_HASH,
            "xy_sha256": MAP_XY_HASH,
            "origin_lonlat": [122.0, 37.4],
            "legacy_scale": 50.0,
            "offset_margin": 10.0,
        },
        "primary_entity_id": entity["id"],
        "protected_point_lonlat": [122.2, 37.51],
        "entities": [entity],
        "spawn_zones": [
            {"id": "wave-zone", "lon_deg": 122.55, "lat_deg": 37.5, "half_width_m": 200.0}
        ],
        "waves": [],
        "events": [],
    }
    if include_wave:
        composition["waves"] = [
            {
                "id": "wave-template",
                "entity_prefix": "wave-asset",
                "side": "blue",
                "count": 2,
                "platform_ref": entity["platform_ref"],
                "dynamics_ref": entity["dynamics_ref"],
                "loadout_ref": entity["loadout_ref"],
                "sensor_refs": entity["sensor_refs"],
                "communication_ref": entity["communication_ref"],
                "inventory": entity["inventory"],
                "spawn_zone": "wave-zone",
                "time_tick": 5,
                "altitude_min_m": 500.0,
                "altitude_max_m": 700.0,
                "speed_mps": 30.0,
            }
        ]
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "scenario.yaml").write_text(yaml.safe_dump(scenario), encoding="utf-8")
    (tmp_path / "composition.yaml").write_text(yaml.safe_dump(composition), encoding="utf-8")
    (tmp_path / "catalog.yaml").write_text("schema_version: catalog@1.0\nresources: []\n")
    return ScenarioPackageRef(tmp_path, "scenario.yaml", "composition.yaml", ("catalog.yaml",))


def _compile_with_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, catalog: CatalogV2
) -> None:
    monkeypatch.setattr(
        compiler_module,
        "load_legacy_composition_catalog_v2",
        lambda documents: catalog,
    )
    ScenarioCompiler().compile_package(_package(tmp_path))


def test_compiler_calls_full_validation_for_static_and_wave_templates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    catalog = _catalog()
    captured: list[EntityCompositionV2] = []
    original = CatalogV2.validate_full_composition

    def spy(instance: CatalogV2, composition: EntityCompositionV2) -> bool:
        captured.append(composition)
        return original(instance, composition)

    monkeypatch.setattr(CatalogV2, "validate_full_composition", spy)
    _compile_with_catalog(monkeypatch, tmp_path, catalog)

    assert len(captured) == 2
    for composition in captured:
        assert composition.sensor_refs == ("sensors.test@2.0.0",)
        assert composition.communication_refs == ("communications.test@2.0.0",)
        assert composition.ammunition == {"ammunition.test@2.0.0": 2}
        assert composition.energy_ref == "energy.test@2.0.0"
        assert composition.collision_shape_ref == "collision.test@2.0.0"
        assert composition.visualization_ref == "visual.test@2.0.0"


@pytest.mark.parametrize(
    "reason",
    (
        "combined component slot capacity exceeded",
        "ammunition is absent from selected loadout",
        "ammunition weapon is absent from loadout",
        "energy is incompatible with platform type",
        "collision_shapes is incompatible with platform domain",
        "visualization_assets is incompatible with platform domain",
        "weapon effect damage chain is invalid",
    ),
)
def test_compiler_translates_atomic_full_composition_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reason: str
) -> None:
    catalog = _catalog()

    def reject(instance: CatalogV2, composition: EntityCompositionV2) -> bool:
        assert composition.platform_ref == "platforms.test@2.0.0"
        raise CatalogResolutionErrorV2(reason)

    monkeypatch.setattr(CatalogV2, "validate_full_composition", reject)
    with pytest.raises(ScenarioCompileError) as captured:
        _compile_with_catalog(monkeypatch, tmp_path, catalog)
    assert captured.value.reason == "compatibility.invalid"
    assert reason in str(captured.value)


def test_zero_inventory_still_validates_loadout_weapon_effect_damage_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    catalog = _catalog()
    called = False

    def require_chain(instance: CatalogV2, composition: EntityCompositionV2) -> bool:
        nonlocal called
        called = True
        loadout = instance.resolve("loadouts", composition.loadout_ref or "")
        assert loadout.content["weapon_refs"] == ("weapons.test@2.0.0",)
        weapon = instance.resolve("weapons", "weapons.test@2.0.0")
        effect = instance.resolve("effects", str(weapon.content["effect_ref"]))
        instance.resolve("damage_models", str(effect.content["damage_model_ref"]))
        return True

    monkeypatch.setattr(CatalogV2, "validate_full_composition", require_chain)
    ref = _package(tmp_path, include_wave=False)
    composition = yaml.safe_load((tmp_path / "composition.yaml").read_text(encoding="utf-8"))
    composition["entities"][0]["inventory"] = {}
    (tmp_path / "composition.yaml").write_text(yaml.safe_dump(composition), encoding="utf-8")
    monkeypatch.setattr(
        compiler_module,
        "load_legacy_composition_catalog_v2",
        lambda documents: catalog,
    )
    ScenarioCompiler().compile_package(ref)
    assert called


def test_source_does_not_use_partial_validation_as_full_substitute() -> None:
    source = Path(compiler_module.__file__).read_text(encoding="utf-8")
    method = source.split("    def _compile_composition(", 1)[1].split("\n    def ", 1)[0]
    assert "validate_full_composition" in method
    assert "validate_entity_composition" not in method

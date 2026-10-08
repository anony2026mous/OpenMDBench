"""MD3-02 acceptance tests for the standalone MD-INT-003 Catalog closure."""

from __future__ import annotations

from pathlib import Path

import pytest
from openmdbench.catalog.formal_v2 import load_catalog_bundle_v2, load_md_ad_002_catalog_v2
from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    CatalogV2,
    EntityCompositionV2,
)

_BUNDLE_PATH = Path(__file__).resolve().parents[2] / "catalog" / "v2" / "md_int_003.yaml"
_UNVALIDATED = "UNVALIDATED_BENCHMARK"


def _catalog() -> CatalogV2:
    return load_catalog_bundle_v2(_BUNDLE_PATH)


def test_md_int_003_catalog_is_a_closed_versioned_surface_resource_set() -> None:
    catalog = _catalog()
    resources = catalog.snapshot()
    exact_refs = {resource.exact_ref for resource in resources}

    assert len(resources) == 72
    assert len(exact_refs) == len(resources)
    assert {
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
    } == {resource.resource_type for resource in resources}
    assert all("md-int-003" not in resource.id for resource in resources)
    assert all("scenario" not in resource.id for resource in resources)

    benchmark_resources = [resource for resource in resources if resource.resource_type != "maps"]
    assert benchmark_resources
    assert all(
        resource.content["parameter_source"] == "MD-INT-003-V4" for resource in benchmark_resources
    )
    assert all(resource.content["fidelity"] == _UNVALIDATED for resource in benchmark_resources)


def test_md_int_003_reuses_the_reviewed_weihai_map_bytes_and_definition() -> None:
    catalog = _catalog()
    existing = load_md_ad_002_catalog_v2()

    md3_map = catalog.resolve("maps", "map.weihai-local@2.0.0")
    existing_map = existing.resolve("maps", "map.weihai-local@2.0.0")

    assert md3_map.content["raw_sha256"] == existing_map.content["raw_sha256"]
    assert md3_map.content["terrain_source"] == existing_map.content["terrain_source"]
    assert md3_map.content["visualization_source"] == existing_map.content["visualization_source"]
    assert md3_map.content["fidelity"] == "VERIFIED_REUSE"


def test_md_int_003_binds_material_usv_motion_and_declared_benchmark_limits() -> None:
    catalog = _catalog()

    defender = catalog.instantiate("dynamics", "dynamics.defender-interdictor-usv@2.0.0")
    attacker = catalog.instantiate("dynamics", "dynamics.attacker-suicide-usv@2.0.0")
    isuav = catalog.instantiate("dynamics", "dynamics.surface-isuav@2.0.0")

    assert defender.parameters["max_speed_mps"] == 15.0
    assert attacker.parameters["max_speed_mps"] == 18.0
    assert defender.parameters["max_nps"] == 200.0
    assert attacker.parameters["max_nps"] == 240.0
    assert isuav.parameters["max_speed_mps"] == 35.0
    assert (
        catalog.resolve("dynamics", "dynamics.defender-interdictor-usv@2.0.0").content[
            "benchmark_requested_max_speed_mps"
        ]
        == 15.0
    )
    assert (
        catalog.resolve("dynamics", "dynamics.attacker-suicide-usv@2.0.0").content[
            "benchmark_requested_max_speed_mps"
        ]
        == 18.0
    )


def test_md_int_003_declares_one_normalized_energy_contract_for_usv_fire() -> None:
    catalog = _catalog()
    energy = catalog.resolve("energy", "energy.defender-interdictor-usv@2.0.0").content
    weapon = catalog.resolve("weapons", "weapon.usv-surface-interdictor@2.0.0").content

    assert 0.0 < weapon["energy_per_shot"] < 1.0
    assert weapon["energy_per_shot"] == pytest.approx(
        energy["fire_energy_j"] / energy["capacity_j"]
    )
    assert energy["idle_rate_per_second"] == pytest.approx(
        energy["idle_power_w"] / energy["capacity_j"]
    )
    assert energy["motion_rate_per_meter"] > 0.0


@pytest.mark.parametrize(
    ("version", "detection_probability", "range_noise_fraction", "bearing_noise_deg"),
    (
        ("2.1.0", 0.95, 0.05, 1.0),
        ("2.2.0", 0.88, 0.08, 2.0),
        ("2.3.0", 0.80, 0.10, 3.0),
    ),
)
def test_md_int_003_has_immutable_difficulty_sensor_profiles(
    version: str,
    detection_probability: float,
    range_noise_fraction: float,
    bearing_noise_deg: float,
) -> None:
    catalog = _catalog()
    expected_ranges = {
        "sensor.defender-usv-surface-radar": 8000.0,
        "sensor.defender-usv-eo-ir": 4000.0,
        "sensor.isuav-surface-radar": 12000.0,
        "sensor.isuav-eo-ir": 6000.0,
        "sensor.shore-surface-radar": 20000.0,
        "sensor.attacker-navigation-radar": 3000.0,
    }

    for resource_id, expected_range_m in expected_ranges.items():
        resource = catalog.resolve("sensors", f"{resource_id}@{version}")
        content = resource.content
        assert content["range_m"] == expected_range_m
        assert content["detection_probability"] == detection_probability
        assert content["probability"] == detection_probability
        assert content["range_noise_fraction"] == range_noise_fraction
        assert content["bearing_noise_deg"] == bearing_noise_deg
        assert content["update_ticks"] >= 1
        assert content["confirmation_frames"] == 2
        assert content["stale_after_ticks"] == 3
        assert content["engagement_max_age_ticks"] == 10
        assert content["minimum_contact_confidence"] == 0.70
        assert content["high_sea_range_multiplier"] in {0.70, 0.75}
        assert content["parameter_source"] == "MD-INT-003-V4"
        assert content["fidelity"] == _UNVALIDATED


def test_md_int_003_has_a_separate_defender_uav_relay_profile() -> None:
    catalog = _catalog()
    surface = catalog.resolve("communications", "communication.defender-surface-tactical@2.1.0")
    uav = catalog.resolve("communications", "communication.defender-uav-surface-tactical@2.1.0")

    assert surface.content["range_m"] == 20000.0
    assert uav.content["range_m"] == 50000.0
    assert surface.content["max_relay_hops"] == uav.content["max_relay_hops"] == 2
    assert surface.content["compatible_platform_types"] == (
        "defender-interdictor-usv",
        "shore-surface-radar",
    )
    assert uav.content["compatible_platform_types"] == ("surface-isuav",)
    assert all(
        resource.content["parameter_source"] == "MD-INT-003-V4"
        and resource.content["fidelity"] == _UNVALIDATED
        for resource in (surface, uav)
    )


def test_md_int_003_versions_the_v4_high_sea_profile_without_rewriting_v2_data() -> None:
    catalog = _catalog()
    legacy = catalog.resolve("environments", "environment.md3-high-sea@2.0.0")
    high_sea = catalog.resolve("environments", "environment.md3-high-sea@2.1.0")

    assert legacy.content["motion_speed_multiplier"] == 0.75
    assert high_sea.content["motion_speed_multiplier"] == 0.70
    assert high_sea.content["sensor_range_multiplier"] == 1.0
    assert high_sea.content["sensor_profile_multiplier_keys"] == {
        "sensor.range": "high_sea_range_multiplier"
    }
    assert high_sea.content["weapon_hit_probability_multiplier"] == 0.80
    assert high_sea.content["energy_consumption_multiplier"] == 1.30
    assert high_sea.content["communication_loss_additive"] == 0.05
    assert high_sea.content["parameter_source"] == "MD-INT-003-V4"
    assert high_sea.content["fidelity"] == _UNVALIDATED


@pytest.mark.parametrize(
    "composition",
    (
        EntityCompositionV2(
            schema_version="2.0",
            platform_ref="platform.defender-interdictor-usv@2.0.0",
            dynamics_ref="dynamics.defender-interdictor-usv@2.0.0",
            loadout_ref="loadout.defender-surface-interdictor@2.0.0",
            sensor_refs=(
                "sensor.defender-usv-surface-radar@2.0.0",
                "sensor.defender-usv-eo-ir@2.0.0",
            ),
            communication_refs=("communication.defender-surface-tactical@2.0.0",),
            energy_ref="energy.defender-interdictor-usv@2.0.0",
            collision_shape_ref="shape.defender-interdictor-usv@2.0.0",
            visualization_ref="visual.defender-interdictor-usv@2.0.0",
            ammunition={"ammunition.usv-surface-interdictor@2.0.0": 10},
            target_domains=("surface",),
        ),
        EntityCompositionV2(
            schema_version="2.0",
            platform_ref="platform.attacker-suicide-usv@2.0.0",
            dynamics_ref="dynamics.attacker-suicide-usv@2.0.0",
            loadout_ref="loadout.attacker-suicide-usv@2.0.0",
            sensor_refs=("sensor.attacker-navigation-radar@2.0.0",),
            communication_refs=("communication.attacker-surface-tactical@2.0.0",),
            energy_ref="energy.attacker-suicide-usv@2.0.0",
            collision_shape_ref="shape.attacker-suicide-usv@2.0.0",
            visualization_ref="visual.attacker-suicide-usv@2.0.0",
            ammunition={"ammunition.suicide-usv-warhead@2.0.0": 1},
            target_domains=("surface",),
        ),
        EntityCompositionV2(
            schema_version="2.0",
            platform_ref="platform.surface-isuav@2.0.0",
            dynamics_ref="dynamics.surface-isuav@2.0.0",
            sensor_refs=(
                "sensor.isuav-surface-radar@2.0.0",
                "sensor.isuav-eo-ir@2.0.0",
            ),
            communication_refs=("communication.defender-surface-tactical@2.0.0",),
            energy_ref="energy.surface-isuav@2.0.0",
            collision_shape_ref="shape.surface-isuav@2.0.0",
            visualization_ref="visual.surface-isuav@2.0.0",
        ),
        EntityCompositionV2(
            schema_version="2.0",
            platform_ref="platform.shore-surface-radar@2.0.0",
            dynamics_ref="dynamics.shore-surface-radar@2.0.0",
            sensor_refs=("sensor.shore-surface-radar@2.0.0",),
            communication_refs=("communication.defender-surface-tactical@2.0.0",),
            energy_ref="energy.shore-surface-radar@2.0.0",
            collision_shape_ref="shape.shore-surface-radar@2.0.0",
            visualization_ref="visual.shore-surface-radar@2.0.0",
        ),
        EntityCompositionV2(
            schema_version="2.0",
            platform_ref="platform.neutral-civilian-usv@2.0.0",
            dynamics_ref="dynamics.neutral-civilian-usv@2.0.0",
            communication_refs=("communication.neutral-navigation@2.0.0",),
            energy_ref="energy.neutral-civilian-usv@2.0.0",
            collision_shape_ref="shape.neutral-civilian-usv@2.0.0",
            visualization_ref="visual.neutral-civilian-usv@2.0.0",
        ),
    ),
)
def test_md_int_003_validates_each_platform_component_closure(
    composition: EntityCompositionV2,
) -> None:
    assert _catalog().validate_full_composition(composition) is True


def test_md_int_003_rejects_over_slots_and_incompatible_surface_weapon_target_domain() -> None:
    catalog = _catalog()
    over_slots = EntityCompositionV2(
        schema_version="2.0",
        platform_ref="platform.defender-interdictor-usv@2.0.0",
        sensor_refs=(
            "sensor.defender-usv-surface-radar@2.0.0",
            "sensor.defender-usv-eo-ir@2.0.0",
            "sensor.defender-usv-eo-ir@2.0.0",
        ),
    )
    incompatible_target = EntityCompositionV2(
        schema_version="2.0",
        platform_ref="platform.defender-interdictor-usv@2.0.0",
        loadout_ref="loadout.defender-surface-interdictor@2.0.0",
        target_domains=("air",),
    )

    with pytest.raises(CatalogResolutionErrorV2, match="slot"):
        catalog.validate_full_composition(over_slots)
    with pytest.raises(CatalogResolutionErrorV2, match="target domain"):
        catalog.validate_full_composition(incompatible_target)


@pytest.mark.parametrize("forbidden_key", ("health", "pending_detonation", "rng_state"))
def test_md_int_003_catalog_schema_rejects_mutable_runtime_state(forbidden_key: str) -> None:
    with pytest.raises(ValueError, match="runtime mutable state"):
        CatalogResourceV2.model_validate(
            {
                "schema_version": "2.0",
                "resource_type": "effects",
                "id": "effect.invalid-state",
                "version": "2.0.0",
                "engine_compatibility": ">=2.0.0,<3.0.0",
                "model_id": "models.formal-data@2.0.0",
                "dependencies": [],
                "content": {forbidden_key: 1},
            }
        )


def test_md_int_003_catalog_loads_as_fresh_definition_objects() -> None:
    first = _catalog()
    second = _catalog()

    first_platform = first.resolve("platforms", "platform.defender-interdictor-usv@2.0.0")
    second_platform = second.resolve("platforms", "platform.defender-interdictor-usv@2.0.0")
    assert first is not second
    assert first_platform is not second_platform
    assert first_platform.content == second_platform.content
    assert first_platform.content is not second_platform.content

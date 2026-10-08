"""Unit and component tests for catalog-backed free-form composition."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml
from openmdbench.catalog.legacy_adapters import md_ad_002_catalog
from openmdbench.core.session_runtime import SessionRuntime
from openmdbench.scenarios.compiler import ScenarioCompileError, ScenarioCompiler
from openmdbench.scenarios.md_ad_002_config import load_md_ad_002_config
from openmdbench.scenarios.package import (
    PackageBoundaryError,
    ScenarioPackageRef,
    unpack_scenario_package,
)
from openmdbench.scenarios.runtime import create_runtime_from_resolved

REPO_ROOT = Path(__file__).resolve().parents[3]


def _install_package(tmp_path: Path, *, bad_weapon: bool = False) -> ScenarioPackageRef:
    tmp_path.mkdir(parents=True, exist_ok=True)
    scenario = yaml.safe_load(
        (REPO_ROOT / "openmdbench/scenarios/area_denial/MD-AD-002.yaml").read_text()
    )
    scenario["scenario_id"] = "CUSTOM-FREEFORM-01"
    scenario["time_limit_ticks"] = 120
    loaded = load_md_ad_002_config("MD-AD-002-EASY")
    catalog = md_ad_002_catalog(loaded.config)
    composition = {
        "schema_version": "composition@1.0",
        "scenario_id": "CUSTOM-FREEFORM-01",
        "scenario_version": "1.0.0",
        "map": {
            "map_id": "weihai_v1",
            "version": "1.0",
            "raw_sha256": loaded.config.map.raw_sha256,
            "xy_sha256": loaded.config.map.xy_sha256,
            "origin_lonlat": list(loaded.config.map.origin_lonlat),
            "legacy_scale": loaded.config.map.legacy_scale,
            "offset_margin": loaded.config.map.legacy_offset_margin,
        },
        "primary_entity_id": "red-uav-alpha",
        "protected_point_lonlat": [122.2, 37.51],
        "entities": [
            {
                "id": "red-uav-alpha",
                "side": "red",
                "platform_ref": "interceptor_uav@1.0.0",
                "dynamics_ref": "uav_kinematics@1.0.0",
                "loadout_ref": "ad2_uav_loadout@1.0.0",
                "sensor_refs": ["radar_uav@1.0.0", "eo_uav@1.0.0"],
                "communication_ref": "ad2_command_network@1.0.0",
                "initial_state": {
                    "lon_deg": 122.28,
                    "lat_deg": 37.54,
                    "altitude_m": 900,
                    "heading_deg": 90,
                    "speed_mps": 31,
                    "terrain": "air",
                },
                "inventory": {
                    ("unknown_weapon@1.0.0" if bad_weapon else "uav_interceptor_missile@1.0.0"): 7
                },
            }
        ],
        "spawn_zones": [
            {"id": "incoming", "lon_deg": 122.55, "lat_deg": 37.5, "half_width_m": 600}
        ],
        "waves": [
            {
                "id": "custom-wave",
                "entity_prefix": "blue-raider",
                "side": "blue",
                "count": 2,
                "platform_ref": "interceptor_uav@1.0.0",
                "dynamics_ref": "uav_kinematics@1.0.0",
                "loadout_ref": "ad2_uav_loadout@1.0.0",
                "inventory": {"uav_interceptor_missile@1.0.0": 3},
                "spawn_zone": "incoming",
                "time_tick": 8,
                "altitude_min_m": 120,
                "altitude_max_m": 220,
                "speed_mps": 37,
            }
        ],
        "events": [{"tick": 1, "type": "jamming_start", "payload": {"zone": "incoming"}}],
        "adjudication": {"initial_weather": "clear"},
    }
    (tmp_path / "scenario.yaml").write_text(yaml.safe_dump(scenario, allow_unicode=True))
    (tmp_path / "composition.yaml").write_text(yaml.safe_dump(composition, allow_unicode=True))
    (tmp_path / "catalog.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "catalog@1.0", "resources": list(catalog.snapshot())},
            allow_unicode=True,
        )
    )
    return ScenarioPackageRef(tmp_path, "scenario.yaml", "composition.yaml", ("catalog.yaml",))


def test_free_entity_wave_loadout_and_runtime_are_catalog_driven(tmp_path: Path) -> None:
    resolved = ScenarioCompiler().compile_package(_install_package(tmp_path))
    assert resolved.scenario_id == "CUSTOM-FREEFORM-01"
    assert resolved.formal is True
    assert len(resolved.deployments) == 1
    assert resolved.deployments[0].loadout_ref == "ad2_uav_loadout@1.0.0"
    assert resolved.deployments[0].weapon_inventory == {"uav_interceptor_missile@1.0.0": 7}
    assert resolved.waves[0].count == 2
    assert resolved.waves[0].side == "blue"
    runtime = create_runtime_from_resolved(resolved, seed=73)
    assert tuple(item.entity_id for item in runtime.scheduled_entities) == (
        "blue-raider-01",
        "blue-raider-02",
    )
    assert all(
        item.weapon_inventory == {"uav_interceptor_missile@1.0.0": 3}
        for item in runtime.scheduled_entities
    )


def test_inventory_must_belong_to_selected_loadout(tmp_path: Path) -> None:
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(_install_package(tmp_path, bad_weapon=True))
    assert captured.value.reason == "compatibility.invalid"


def test_catalog_files_are_packaged_and_hash_verified(tmp_path: Path) -> None:
    ref = _install_package(tmp_path / "source")
    archive = ref.pack(tmp_path / "custom.omdscenario")
    restored = unpack_scenario_package(archive, tmp_path / "restored")
    assert restored.catalogs == ("catalog.yaml",)
    assert restored.content_hash() == ref.content_hash()


def test_composed_scenario_runs_through_shared_session_kernel(tmp_path: Path) -> None:
    resolved = ScenarioCompiler().compile_package(_install_package(tmp_path))
    runtime = SessionRuntime(resolved, 73)
    observation, info = runtime.reset(seed=73)
    assert observation["scenario_id"] == "CUSTOM-FREEFORM-01"
    assert info["scenario_id"] == "CUSTOM-FREEFORM-01"
    assert runtime._env.observation_space.contains(observation)
    next_observation, _reward, terminated, truncated, _info = runtime.step([20.0, 45.0])
    assert next_observation["timestamp"] == 1
    assert not terminated
    assert not truncated
    assert runtime.pipeline_trace
    assert runtime._env.wave_events[-1]["event_type"] == "jamming_start"
    runtime.close()


def test_dynamics_speed_envelope_is_checked_at_compile_time(tmp_path: Path) -> None:
    ref = _install_package(tmp_path)
    path = tmp_path / "composition.yaml"
    composition = yaml.safe_load(path.read_text())
    composition["entities"][0]["initial_state"]["speed_mps"] = 81
    path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(ref)
    assert captured.value.reason == "compatibility.invalid"
    assert "maximum_speed_mps" in str(captured.value)


def test_scenario_entity_resource_limit_is_enforced(tmp_path: Path) -> None:
    ref = _install_package(tmp_path)
    path = tmp_path / "composition.yaml"
    composition = yaml.safe_load(path.read_text())
    composition["waves"][0]["count"] = 1_001
    path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(ref)
    assert captured.value.reason == "schema.invalid"


def test_scenario_and_composition_identity_must_match(tmp_path: Path) -> None:
    ref = _install_package(tmp_path)
    path = tmp_path / "composition.yaml"
    composition = yaml.safe_load(path.read_text())
    composition["scenario_id"] = "DIFFERENT-SCENARIO"
    path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(ref)
    assert captured.value.reason == "reference.mismatch"


def test_wave_jitter_cannot_schedule_before_tick_zero(tmp_path: Path) -> None:
    ref = _install_package(tmp_path)
    path = tmp_path / "composition.yaml"
    composition = yaml.safe_load(path.read_text())
    composition["waves"][0]["time_tick"] = 2
    composition["waves"][0]["time_jitter_ticks"] = 3
    path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(ref)
    assert captured.value.reason == "wave.out_of_range"


def test_declared_map_identity_must_match_verified_asset(tmp_path: Path) -> None:
    ref = _install_package(tmp_path)
    path = tmp_path / "composition.yaml"
    composition = yaml.safe_load(path.read_text())
    composition["map"]["map_id"] = "another_map"
    path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ScenarioCompileError) as captured:
        ScenarioCompiler().compile_package(ref)
    assert captured.value.reason == "map.identity_mismatch"


def test_archive_duplicate_paths_are_rejected_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "duplicate.omdpkg"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("scenario.yaml", "one")
        output.writestr("scenario.yaml", "two")
        output.writestr("manifest.json", "{}")
    with pytest.raises(PackageBoundaryError, match="duplicate paths"):
        unpack_scenario_package(archive, tmp_path / "unpacked")

"""AD2-02 configuration-driven runtime contracts."""

from pathlib import Path

import numpy as np
import pytest
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.scenarios.runtime import create_scenario_runtime

SCENARIOS = (
    "MD-AD-002-EASY",
    "MD-AD-002-MEDIUM",
    "MD-AD-002-HARD",
)


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_registered_runtime_builds_deterministically(scenario_id: str) -> None:
    first = create_scenario_runtime(scenario_id, seed=19)
    second = create_scenario_runtime(scenario_id, seed=19)
    assert first.metadata == second.metadata
    assert first.world.entities_stable() == second.world.entities_stable()
    assert first.scheduled_entities == second.scheduled_entities
    assert first.metadata.coordinate_system == "local_aeqd_metre"
    assert first.metadata.config_hash.startswith("sha256:")


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_ad2_runtime_contains_seven_red_assets_and_fifteen_scheduled_ids(
    scenario_id: str,
) -> None:
    runtime = create_scenario_runtime(scenario_id, seed=3)
    assert len(runtime.world.entities_stable()) == 7
    assert {entity.side.value for entity in runtime.world.entities_stable()} == {"red"}
    assert len(runtime.scheduled_entities) == 15
    assert runtime.scheduled_entities[0].entity_id == "blue-striker-uav-01"
    assert runtime.scheduled_entities[-1].entity_id == "blue-striker-uav-15"
    for entity in runtime.world.entities_for_type("shore_radar"):
        assert runtime.geo_frame.is_land_local(*entity.position[:2])
    for entity in runtime.world.entities_for_type("usv"):
        assert not runtime.geo_frame.is_land_local(*entity.position[:2])


def test_ad2_sessions_have_isolated_world_and_motion_state() -> None:
    first = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=5)
    second = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=5)
    first.reset(seed=5)
    second.reset(seed=5)
    assert first.world is not None and second.world is not None
    first.step(np.array([25.0, 90.0], dtype=np.float32))
    assert first.world is not second.world
    assert first.world.entities_stable() != second.world.entities_stable()
    assert first._usv_mmg_adapters is not second._usv_mmg_adapters


def test_core_dispatch_does_not_branch_on_new_difficulty_ids() -> None:
    source = (Path(__file__).parents[2] / "openmdbench/envs/benchmark.py").read_text()
    assert "MD-AD-002-EASY" not in source
    assert "MD-AD-002-MEDIUM" not in source
    assert "MD-AD-002-HARD" not in source


def test_ad2_checkpoint_contains_and_validates_runtime_identity() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=11)
    env.reset(seed=11)
    state = env.export_state()
    assert state["runtime_metadata"]["scenario_id"] == "MD-AD-002-MEDIUM"
    assert state["runtime_metadata"]["rules_version"] == "breach_count_v1"
    assert len(state["scheduled_entities"]) == 11
    tampered = {**state, "runtime_metadata": {**state["runtime_metadata"], "config_hash": "bad"}}
    with pytest.raises(ValueError, match="config hash"):
        env.import_state(tampered)


def test_ad2_checkpoint_restores_per_usv_motion_state() -> None:
    continuous = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=13)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=13)
    continuous.reset(seed=13)
    restored.reset(seed=13)
    action = np.array([25.0, 90.0], dtype=np.float32)
    continuous.step(action)
    restored.import_state(continuous.export_state())
    continuous.step(action)
    restored.step(action)
    assert continuous.world is not None and restored.world is not None
    assert continuous.world.entities_stable() == restored.world.entities_stable()

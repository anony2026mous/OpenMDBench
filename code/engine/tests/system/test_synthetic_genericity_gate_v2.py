"""RF-10 synthetic genericity gate using only scenario/test data additions."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from openmdbench.scenarios.declarative_v2 import (
    ResolvedEntityV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.sessions.runners_v2 import ReplayRunnerV2

ROOT = Path("scenarios/synthetic")


@pytest.mark.parametrize("identifier", ("gs_001", "gs_002", "gs_003", "gs_004"))
def test_genericity_packages_are_data_only_and_scenario_names_are_arbitrary(
    identifier: str,
) -> None:
    payload = yaml.safe_load((ROOT / identifier / "scenario.yaml").read_text())
    assert payload["schema_version"] == "package@2.0"
    package = ScenarioPackageV2.from_directory(ROOT / identifier)
    assert not any(path.suffix == ".py" for path in (ROOT / identifier).rglob("*"))
    renamed = copy.deepcopy(payload)
    renamed["scenario"]["scenario_id"] = f"renamed.{identifier}"
    renamed_package = ScenarioPackageV2.from_mapping(renamed)
    assert renamed_package.logical_hash == package.logical_hash


def test_gs001_compiles_three_arbitrary_factions_without_side_fields() -> None:
    from tests.contract import test_declarative_scenario_v2 as fixture

    resolved = fixture._v2_api()[1](catalog=fixture._catalog()).compile(
        ScenarioPackageV2.from_directory(ROOT / "gs_001")
    )
    assert tuple(item.id for item in resolved.factions) == (
        "faction.alpha",
        "faction.bravo",
        "faction.civilian",
    )
    assert "side" not in resolved.to_json()


@pytest.mark.parametrize("count", (1, 10, 100))
def test_gs002_formation_expansion_is_stable_for_1_10_100(count: int) -> None:
    from tests.contract import test_declarative_scenario_v2 as fixture

    payload = yaml.safe_load((ROOT / "gs_002" / "scenario.yaml").read_text())
    payload["scenario"]["formations"][0]["count"] = count
    compiler = fixture._v2_api()[1](catalog=fixture._catalog())
    package = ScenarioPackageV2.from_mapping(payload)
    first = compiler.compile(package)
    second = compiler.compile(package)
    assert len(first.entities) == count
    assert first.resolved_hash == second.resolved_hash
    assert tuple(item.id for item in first.entities) == tuple(
        f"formed-{index:03d}" for index in range(count)
    )


def test_gs003_real_world_combat_damage_checkpoint_and_restore() -> None:
    from tests.contract import test_combat_damage_v2 as fixture
    from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture

    disk_resolved = ScenarioCompilerV2(catalog=resource_fixture._catalog()).compile(
        ScenarioPackageV2.from_directory(ROOT / "gs_003")
    )
    disk_entity = disk_resolved.entities[0]
    assert isinstance(disk_entity, ResolvedEntityV2)
    assert disk_entity.resource_bindings["weapons"]
    assert disk_entity.resource_bindings["effects"]

    system = fixture._system()
    before = system.world.checkpoint()
    execution = system.execute_batch(
        (fixture._request(),), expected_tick=0, operation_id="gs003.combat"
    )
    assert execution and execution[0].shots
    checkpoint = system.world.checkpoint()
    assert checkpoint.checkpoint_hash != before.checkpoint_hash
    restored = system.world_factory.restore_checkpoint(
        checkpoint,
        resolved=system.resolved,
        model_registry=system.model_registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
        expected_session_id=system.world.session_id,
        expected_seed=checkpoint.seed,
    )
    assert restored.checkpoint().semantic_hash == system.world.checkpoint().semantic_hash
    restored.close()


def test_gs004_compiler_freezes_dynamic_events_mission_and_scoring() -> None:
    from tests.contract import test_declarative_mission_control_v2 as fixture

    package = ScenarioPackageV2.from_directory(ROOT / "gs_004")
    resolved = ScenarioCompilerV2(catalog=fixture._catalog()).compile(package)
    assert resolved.events
    assert resolved.mission_rules
    assert resolved.scoring is not None
    assert resolved.scoring.metrics
    assert resolved.to_json() == type(resolved).from_json(resolved.to_json()).to_json()


def test_gen_gate_local_observation_frame_checkpoint_and_replay_share_tick() -> None:
    from tests.integration.test_session_action_world_v2 import _session

    session = _session("session.gen-gate").load().start()
    session.step(operation_id="gen.tick.000", expected_tick=0)
    observation = session.world_view.observation(observer_faction_id="coalition.alpha")
    frame = VisualizationFrameV2(
        schema_version="2.0",
        session_id=session.session_id,
        scenario_id="renamed.genericity",
        tick=observation.tick,
        view="faction",
        view_faction_id="coalition.alpha",
        entities=observation.own_entities,
        contacts_by_faction=observation.contacts_by_faction,
    )
    checkpoint = session.checkpoint()
    replay = ReplayRunnerV2(
        records=(
            {
                "tick": frame.tick,
                "frame": frame.model_dump(mode="json"),
                "checkpoint_hash": checkpoint.checkpoint_hash,
            },
        )
    )
    replayed = replay.next()
    assert replayed is not None
    assert replayed["tick"] == observation.tick == session.world_view.tick
    session.stop().close()

"""AD2-03 deterministic wave activation and checkpoint boundaries."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from openmdbench.api.sessions import SessionStore
from openmdbench.core.entities import Lifecycle
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.replay import ReplayReader
from openmdbench.scenarios import runtime as runtime_module
from openmdbench.scenarios.md_ad_002_config import (
    LoadedMDAD002Config,
    load_md_ad_002_config,
)
from openmdbench.scenarios.runtime import create_scenario_runtime, validate_scheduled_entities


def test_easy_wave_boundaries_activate_4_5_6_exactly_once() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=23)
    env.reset(seed=23)
    assert env.world is not None
    assert len(env.world.entities_for_side("blue")) == 4
    env._spawn_due(599)
    assert len(env.world.entities_for_side("blue")) == 4
    env._spawn_due(600)
    assert len(env.world.entities_for_side("blue")) == 9
    env._spawn_due(600)
    assert len(env.world.entities_for_side("blue")) == 9
    env._spawn_due(1200)
    assert len(env.world.entities_for_side("blue")) == 15
    assert len(env.scheduled_entities) == 0


def test_medium_and_hard_jitter_is_seeded_and_bounded() -> None:
    for scenario_id in ("MD-AD-002-MEDIUM", "MD-AD-002-HARD"):
        first = create_scenario_runtime(scenario_id, seed=31)
        same = create_scenario_runtime(scenario_id, seed=31)
        different = create_scenario_runtime(scenario_id, seed=32)
        assert first.scheduled_entities == same.scheduled_entities
        wave_two = {
            item.scheduled_tick for item in first.scheduled_entities if item.wave_id == "wave-2"
        }
        assert len(wave_two) == 1 and 480 <= wave_two.pop() <= 720
        assert first.scheduled_entities != different.scheduled_entities


def test_named_wave_compilation_is_independent_of_config_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_id = "MD-AD-002-MEDIUM"
    baseline = create_scenario_runtime(scenario_id, seed=31)
    loaded = load_md_ad_002_config(scenario_id)
    reordered = loaded.config.model_copy(update={"waves": tuple(reversed(loaded.config.waves))})
    monkeypatch.setattr(
        runtime_module,
        "load_md_ad_002_config",
        lambda _scenario_id: LoadedMDAD002Config(reordered, loaded.sha256, loaded.path),
    )

    permuted = create_scenario_runtime(scenario_id, seed=31)

    assert permuted.scheduled_entities == baseline.scheduled_entities


def test_checkpoint_before_wave_does_not_duplicate_spawn() -> None:
    original = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=41)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=41)
    original.reset(seed=41)
    restored.reset(seed=41)
    restored.import_state(original.export_state())
    original._spawn_due(600)
    restored._spawn_due(600)
    assert original.world is not None and restored.world is not None
    assert original.world.entities_stable() == restored.world.entities_stable()
    assert original.wave_events == restored.wave_events


def test_checkpoint_crossing_real_step_wave_boundary_matches_continuous_run() -> None:
    original = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=42)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=42)
    original.reset(seed=42)
    restored.reset(seed=42)
    assert original.world is not None
    original._tick = 599
    original.world.tick = 599
    original.world.time_remaining = 1201
    restored.import_state(original.export_state())
    action = np.array([25.0, 90.0], dtype=np.float32)
    original.step(action)
    restored.step(action)
    assert original.world is not None and restored.world is not None
    assert len(original.world.entities_for_side("blue")) == 9
    assert original.world.entities_stable() == restored.world.entities_stable()
    assert original.wave_events == restored.wave_events


def test_world_boundary_latches_tombstone_without_id_reuse() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=43)
    env.reset(seed=43)
    assert env.world is not None and env.geo_frame is not None
    entity = env.world.registry.get("blue-striker-uav-01")
    env.world.registry.update(entity.model_copy(update={"position": (1e9, 1e9, 100.0)}))
    env._apply_world_constraints(1)
    assert env.world.registry.get(entity.id).lifecycle is Lifecycle.OUT_OF_BOUNDS
    assert entity.id in {item.id for item in env.world.entities_stable()}


@pytest.mark.parametrize("fault", ("duplicate", "land", "outside"))
def test_invalid_spawn_descriptors_fail_closed(fault: str) -> None:
    runtime = create_scenario_runtime("MD-AD-002-EASY", seed=47)
    items = list(runtime.scheduled_entities)
    if fault == "duplicate":
        items[1] = replace(items[1], entity_id=items[0].entity_id)
    elif fault == "land":
        shore = runtime.world.entities_for_type("shore_radar")[0]
        items[0] = replace(items[0], position=shore.position)
    else:
        items[0] = replace(items[0], position=(1e9, 1e9, 100.0))
    runtime.scheduled_entities = tuple(items)
    with pytest.raises(ValueError, match="duplicate|water|outside"):
        validate_scheduled_entities(runtime)


def test_spawn_events_are_persisted_in_replay(tmp_path: Path) -> None:
    store = SessionStore(replay_dir=tmp_path)
    session = store.create("MD-AD-002-EASY", seed=53)
    store.delete(session.session_id)
    frames = list(ReplayReader(tmp_path / f"{session.session_id}.replay.jsonl").frames())
    spawned = [event for event in frames[0].events if event.event_type == "entity_spawned"]
    assert [event.entity_id for event in spawned] == [
        f"blue-striker-uav-{index:02d}" for index in range(1, 5)
    ]

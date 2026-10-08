"""AD2-08 MEDIUM configuration-driven weather, routes, and evasion."""

import numpy as np
from openmdbench.core.entities import PlatformAsset, Side
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import AD2MediumBlueAgent
from openmdbench.scenarios.runtime import create_scenario_runtime
from openmdbench.systems.sensors.ad2 import detection_probability


def test_medium_starts_clear_and_applies_cloudy_event_exactly_at_600() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=81)
    env.reset(seed=81)
    assert env.world is not None
    assert env.world.weather == "clear"
    env._apply_ad2_difficulty_events(599)
    assert env.world.weather == "clear"
    env._apply_ad2_difficulty_events(600)
    assert env.world.weather == "cloudy"
    assert env.wave_events[-1] == {
        "event_type": "weather_changed",
        "tick": 600,
        "weather": "cloudy",
    }


def test_medium_cloudy_reduces_detection_probability() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=82)
    env.reset(seed=82)
    assert env.world is not None and env._runtime is not None
    assert env._runtime.md_ad_config is not None
    profile = next(
        item for item in env._runtime.md_ad_config.sensors if item.sensor_id == "radar_gap"
    )
    radar = env.world.registry.get("red-island-radar-2")
    target = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(radar, PlatformAsset) and isinstance(target, PlatformAsset)
    target = target.model_copy(
        update={"position": (radar.position[0] + 5_000.0, radar.position[1], 100.0)}
    )
    clear = detection_probability(profile, radar, target, weather="clear")
    cloudy = detection_probability(profile, radar, target, weather="cloudy")
    assert 0.0 < cloudy < clear


def test_medium_applies_configured_twelve_percent_difficulty_miss_factor() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=85)
    env.reset(seed=85)
    assert env.world is not None and env._ad2_perception is not None
    assert env._runtime is not None and env._runtime.md_ad_config is not None
    radar = env.world.registry.get("red-island-radar-2")
    target = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(radar, PlatformAsset) and isinstance(target, PlatformAsset)
    target = target.model_copy(update={"position": (*radar.position[:2], 100.0)})
    env.world.registry.update(target)
    env._update_sensors(2)
    report = next(
        event
        for event in env._ad2_perception.events
        if event["sensor_id"] == "red-island-radar-2:radar_gap"
        and event["truth_id"] == "blue-striker-uav-01"
    )
    profile = next(
        item for item in env._runtime.md_ad_config.sensors if item.sensor_id == "radar_gap"
    )
    assert profile.base_detection_probability == 0.792
    expected = detection_probability(profile, radar, target, weather="clear")
    assert report["probability"] == expected


def test_medium_blue_split_and_single_evasion_are_seed_deterministic() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=83)
    env.reset(seed=83)
    observation = env.public_observation(Side.BLUE)
    protected = (float(env._protected_point[0]), float(env._protected_point[1]), 100.0)
    first = AD2MediumBlueAgent(protected)
    second = AD2MediumBlueAgent(protected)
    first.reset(observation, 83)
    second.reset(observation, 83)
    direct = first.act(observation)
    assert direct == second.act(observation)
    targets = {action.entity_id: action.target for action in direct.actions}
    assert targets["blue-striker-uav-01"] != targets["blue-striker-uav-03"]

    engaged = observation.model_copy(update={"event_log": ({"event_type": "engagement"},)})
    evading = first.act(engaged)
    assert evading == second.act(engaged)
    assert evading.high_level_intent["evading"] == ["blue-striker-uav-01"]
    repeated = first.act(engaged)
    assert repeated.high_level_intent["evading"] == ["blue-striker-uav-01"]

    restored = AD2MediumBlueAgent(protected)
    restored.restore(first.snapshot())
    assert restored.act(engaged) == repeated


def test_medium_altitudes_and_wave_three_high_speed_are_config_bounded() -> None:
    runtime = create_scenario_runtime("MD-AD-002-MEDIUM", seed=84)
    assert all(50.0 <= item.position[2] <= 150.0 for item in runtime.scheduled_entities)
    wave_three = [item for item in runtime.scheduled_entities if item.wave_id == "wave-3"]
    assert [item.speed_mps for item in wave_three] == [30.0, 30.0, 30.0, 30.0, 45.0, 45.0]


def test_medium_checkpoint_crossing_weather_boundary_is_exact() -> None:
    continuous = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=86)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=86)
    continuous.reset(seed=86)
    restored.reset(seed=86)
    assert continuous.world is not None
    continuous._tick = 599
    continuous.world.tick = 599
    continuous.world.time_remaining = 1_201
    restored.import_state(continuous.export_state())
    action = np.asarray([25.0, 90.0], dtype=np.float32)
    continuous.step(action)
    restored.step(action)
    assert continuous.world is not None and restored.world is not None
    assert continuous.world.weather == restored.world.weather == "cloudy"
    assert continuous.export_state() == restored.export_state()

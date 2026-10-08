"""AD2-10 HARD environment, policy, suppression, and checkpoint closure."""

import json
import math

import numpy as np
from openmdbench.core.entities import Lifecycle, PlatformAsset
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import AD2HardBlueAgent
from openmdbench.systems.sensors.ad2 import detection_probability


def test_hard_weather_and_sea_state_begin_exactly_at_tick_900() -> None:
    first = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=301)
    second = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=301)
    first.reset(seed=301)
    second.reset(seed=301)
    assert first.world is not None and second.world is not None
    first._apply_ad2_difficulty_events(899)
    assert first.world.weather == "clear" and first.world.sea_state == 2
    assert first._ad2_event_rng.snapshot()["streams"] == {}
    first._apply_ad2_difficulty_events(900)
    second._apply_ad2_difficulty_events(900)
    assert first.world.weather == second.world.weather
    assert first.world.weather in {"light_rain", "fog"}
    assert first.world.sea_state == second.world.sea_state == 4
    assert [event["event_type"] for event in first.wave_events[-3:]] == [
        "weather_changed",
        "sea_state_changed",
        "jamming_started",
    ]
    observation = first.red_observation()
    assert observation.environment == {"weather": first.world.weather, "sea_state": 4}


def test_high_sea_state_only_degrades_usv_sensor_probability() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=302)
    env.reset(seed=302)
    assert env.world is not None and env._runtime is not None
    assert env._runtime.md_ad_config is not None
    usv = env.world.registry.get("red-picket-usv-1")
    uav = env.world.registry.get("red-interceptor-uav-1")
    target = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(usv, PlatformAsset)
    assert isinstance(uav, PlatformAsset)
    assert isinstance(target, PlatformAsset)
    target = target.model_copy(
        update={"position": (usv.position[0] + 1_000.0, usv.position[1], 100.0)}
    )
    usv_profile = next(
        profile for profile in env._runtime.md_ad_config.sensors if profile.sensor_id == "radar_usv"
    )
    uav_profile = next(
        profile for profile in env._runtime.md_ad_config.sensors if profile.sensor_id == "radar_uav"
    )
    usv_two = detection_probability(usv_profile, usv, target, weather="clear", sea_state=2)
    usv_four = detection_probability(usv_profile, usv, target, weather="clear", sea_state=4)
    uav_two = detection_probability(uav_profile, uav, target, weather="clear", sea_state=2)
    uav_four = detection_probability(uav_profile, uav, target, weather="clear", sea_state=4)
    assert math.isclose(usv_four, usv_two * 0.8)
    assert uav_four == uav_two


def test_usv_proximity_suppression_is_component_scoped_and_recovers() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=303)
    env.reset(seed=303)
    assert env.world is not None and env._communication is not None
    usv = env.world.registry.get("red-picket-usv-1")
    other = env.world.registry.get("red-picket-usv-2")
    blue = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(usv, PlatformAsset)
    assert isinstance(other, PlatformAsset)
    assert isinstance(blue, PlatformAsset)
    env.world.registry.update(blue.model_copy(update={"position": usv.position}))
    env._apply_ad2_difficulty_events(10)
    suppressed = env.world.registry.get(usv.id)
    unaffected = env.world.registry.get(other.id)
    assert isinstance(suppressed, PlatformAsset)
    assert isinstance(unaffected, PlatformAsset)
    assert suppressed.lifecycle is Lifecycle.DEGRADED
    assert not suppressed.components.sensor_operational
    assert not suppressed.components.communication_operational
    assert not suppressed.components.propulsion_operational
    assert not suppressed.components.weapons_operational
    assert not env._communication.endpoints[usv.id].online
    assert unaffected.components.sensor_operational
    assert env.wave_events[-1]["ends_tick"] == 100
    suppressed_position = suppressed.position
    env._pending_navigation[usv.id] = (12.0, 90.0, usv.position[2])
    env.step(np.asarray((0.0, 0.0), dtype=np.float32))
    after_step = env.world.registry.get(usv.id)
    assert isinstance(after_step, PlatformAsset)
    assert after_step.position == suppressed_position
    assert (usv.id, "propulsion_suppressed") in env.last_dynamics_trace

    env._apply_ad2_difficulty_events(99)
    assert not env._communication.endpoints[usv.id].online
    env._apply_ad2_difficulty_events(100)
    recovered = env.world.registry.get(usv.id)
    assert isinstance(recovered, PlatformAsset)
    assert recovered.lifecycle is Lifecycle.ACTIVE
    assert recovered.components.sensor_operational
    assert recovered.components.communication_operational
    assert recovered.components.propulsion_operational
    assert recovered.components.weapons_operational
    assert env._communication.endpoints[usv.id].online
    assert env.wave_events[-1]["event_type"] == "suppression_ended"


def test_hard_event_and_suppression_checkpoint_json_round_trip() -> None:
    continuous = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=304)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=304)
    continuous.reset(seed=304)
    restored.reset(seed=304)
    assert continuous.world is not None
    usv = continuous.world.registry.get("red-picket-usv-1")
    blue = continuous.world.registry.get("blue-striker-uav-01")
    assert isinstance(usv, PlatformAsset) and isinstance(blue, PlatformAsset)
    continuous.world.registry.update(blue.model_copy(update={"position": usv.position}))
    continuous._apply_ad2_difficulty_events(10)
    checkpoint = json.loads(json.dumps(continuous.export_state()))
    restored.import_state(checkpoint)
    continuous._apply_ad2_difficulty_events(100)
    restored._apply_ad2_difficulty_events(100)
    continuous._apply_ad2_difficulty_events(900)
    restored._apply_ad2_difficulty_events(900)
    assert continuous.export_state() == restored.export_state()


def test_hard_blue_policy_continuously_changes_serpentine_phase() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=305)
    env.reset(seed=305)
    assert env.world is not None
    protected = (float(env._protected_point[0]), float(env._protected_point[1]), 100.0)
    agent = AD2HardBlueAgent(protected)
    at_zero = env.public_observation("blue")
    first = agent.act(at_zero)
    env.world.tick = 20
    at_twenty = env.public_observation("blue")
    second = agent.act(at_twenty)
    first_targets = {action.entity_id: action.target for action in first.actions}
    second_targets = {action.entity_id: action.target for action in second.actions}
    assert first.high_level_intent["strategy"] == "hard_multi_axis_continuous_serpentine"
    assert first_targets.keys() == second_targets.keys()
    assert any(first_targets[key] != second_targets[key] for key in first_targets)

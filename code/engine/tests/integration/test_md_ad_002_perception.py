"""AD2-04 environment integration, false alarm, replay privacy, and checkpoint tests."""

import json

from openmdbench.core.entities import PlatformAsset, Side
from openmdbench.envs import OpenMDBenchEnv


def _place_first_blue_on_radar(env: OpenMDBenchEnv) -> None:
    assert env.world is not None
    radar = env.world.registry.get("red-island-radar-2")
    target = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(radar, PlatformAsset) and isinstance(target, PlatformAsset)
    env.world.registry.update(
        target.model_copy(update={"position": (radar.position[0], radar.position[1], 100.0)})
    )


def test_environment_exposes_stable_opaque_red_contact() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=61)
    env.reset(seed=61)
    _place_first_blue_on_radar(env)
    assert env.world is not None
    for tick in (2, 4, 6):
        env._update_sensors(tick)
    env.world.tick = 6
    observation = env.public_observation(Side.RED)
    assert observation.situational_data.detected_contacts
    encoded = observation.model_dump_json()
    assert "blue-striker-uav" not in encoded
    assert env.world.contacts.get(Side.BLUE, []) == []
    assert all(
        "truth_id" not in event
        for event in env.wave_events
        if event.get("event_type") in {"sensor_report", "track_fused"}
    )
    first_id = observation.situational_data.detected_contacts[0].id
    env._update_sensors(8)
    env.world.tick = 8
    assert env.public_observation(Side.RED).situational_data.detected_contacts[0].id == first_id
    assert env.public_observation(Side.RED).situational_data.detected_contacts[0].age == 0


def test_checkpoint_restores_perception_rng_and_tracks_exactly() -> None:
    first = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=67)
    second = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=67)
    first.reset(seed=67)
    second.reset(seed=67)
    _place_first_blue_on_radar(first)
    for tick in (2, 4, 6):
        first._update_sensors(tick)
    second.import_state(first.export_state())
    first._update_sensors(8)
    second._update_sensors(8)
    assert first.world is not None and second.world is not None
    assert first._ad2_perception is not None and second._ad2_perception is not None
    assert first.world.contacts == second.world.contacts
    assert first._ad2_perception.snapshot() == second._ad2_perception.snapshot()
    assert "blue-striker-uav" not in json.dumps(first.world.contacts[Side.RED], default=str)


def test_medium_false_alarm_is_seed_deterministic() -> None:
    first = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=71)
    second = OpenMDBenchEnv(scenario_id="MD-AD-002-MEDIUM", seed=71)
    first.reset(seed=71)
    second.reset(seed=71)
    for env in (first, second):
        assert env.world is not None
        for entity in env.world.entities_for_side("red"):
            assert isinstance(entity, PlatformAsset)
            env.world.registry.update(
                entity.model_copy(
                    update={
                        "components": entity.components.model_copy(update={"sensor_mode": "off"})
                    }
                )
            )
        for tick in (30, 32, 34):
            env._update_sensors(tick)
    assert first.world is not None and second.world is not None
    assert first.world.contacts[Side.RED] == second.world.contacts[Side.RED]
    assert first.world.contacts[Side.RED][0].detected_by == ("clutter",)

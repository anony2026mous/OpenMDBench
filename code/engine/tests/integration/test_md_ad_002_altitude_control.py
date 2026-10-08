"""MD-AD-002 navigation altitude reaches the bounded UAV dynamics."""

import pytest
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.schemas.md_ad_002_interface import (
    NavigationAction,
    RedActionBatch,
    RedPlatformAction,
)


def _altitude_batch(env: OpenMDBenchEnv, altitude_m: float) -> RedActionBatch:
    assert env.world is not None
    entity = env.world.registry.get("red-interceptor-uav-1")
    return RedActionBatch(
        scenario_id="MD-AD-002-EASY",
        timestamp=env.world.tick,
        actions=(
            RedPlatformAction(
                entity_id=entity.id,
                navigation=NavigationAction(
                    mode="move_to",
                    target_m=(entity.position[0], entity.position[1], altitude_m),
                    speed_mps=0.0,
                ),
            ),
        ),
    )


def test_uav_target_altitude_climbs_and_descends_at_bounded_rate() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=91)
    env.reset(seed=91)
    assert env.world is not None
    entity_id = "red-interceptor-uav-1"
    initial = env.world.registry.get(entity_id).position[2]

    env.step_red_action_batch(_altitude_batch(env, initial + 100.0))
    climbed = env.world.registry.get(entity_id)
    assert climbed.position[2] == pytest.approx(initial + 20.0)
    assert climbed.velocity[2] == pytest.approx(20.0)

    env.step_red_action_batch(_altitude_batch(env, initial - 100.0))
    descended = env.world.registry.get(entity_id)
    assert descended.position[2] == pytest.approx(initial)
    assert descended.velocity[2] == pytest.approx(-20.0)


def test_hold_position_preserves_current_altitude() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=92)
    env.reset(seed=92)
    assert env.world is not None
    entity = env.world.registry.get("red-interceptor-uav-1")
    batch = RedActionBatch(
        scenario_id="MD-AD-002-EASY",
        timestamp=0,
        actions=(
            RedPlatformAction(
                entity_id=entity.id,
                navigation=NavigationAction(mode="hold_position"),
            ),
        ),
    )
    env.step_red_action_batch(batch)
    held = env.world.registry.get(entity.id)
    assert held.position[2] == pytest.approx(entity.position[2])
    assert held.velocity[2] == pytest.approx(0.0)

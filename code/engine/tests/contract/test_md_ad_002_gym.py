from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from openmdbench.envs.md_ad_002 import MDAD002GymEnv
from openmdbench.policies import AD2RedBaselineAgent


def test_fixed_slot_gym_spaces_contain_reset_and_step_values() -> None:
    env = MDAD002GymEnv(seed=3)
    observation, info = env.reset(seed=3)
    assert env.observation_space.contains(observation)
    assert len(info["red_observation"]["own_forces"]) == 7
    action = {
        "action_mask": np.zeros(7, dtype=np.int8),
        "navigation_mode": np.zeros(7, dtype=np.int64),
        "target_m": np.zeros((7, 3), dtype=np.float32),
        "speed_mps": np.zeros(7, dtype=np.float32),
        "sensor_mode": np.zeros(7, dtype=np.int64),
        "relay_enabled": np.zeros(7, dtype=np.int8),
        "engagement_mask": np.zeros(7, dtype=np.int8),
        "contact_slot": np.zeros(7, dtype=np.int64),
        "weapon": np.zeros(7, dtype=np.int64),
        "ciws_auto": np.zeros(7, dtype=np.int64),
    }
    assert env.action_space.contains(action)
    advanced, _, _, _, advanced_info = env.step(cast(dict[str, NDArray[Any]], action))
    assert env.observation_space.contains(advanced)
    assert advanced_info["red_observation"]["timestamp"] == 1


def test_canonical_rule_agent_batch_round_trips_through_gym_slots() -> None:
    env = MDAD002GymEnv(seed=8)
    env.reset(seed=8)
    protected = (float(env.core._protected_point[0]), float(env.core._protected_point[1]))
    agent = AD2RedBaselineAgent(protected)
    public = env.core.red_observation()
    batch = agent.act(public)
    encoded = env.encode_action_batch(batch)
    assert env._batch(encoded).actions == batch.actions


def test_medium_uses_the_same_fixed_slot_gym_contract() -> None:
    env = MDAD002GymEnv(scenario_id="MD-AD-002-MEDIUM", seed=9)
    observation, info = env.reset(seed=9)
    assert env.observation_space.contains(observation)
    assert info["red_observation"]["scenario_id"] == "MD-AD-002-MEDIUM"

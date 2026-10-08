"""Contracts for the public scenario environment and tensor wrapper."""

import gymnasium as gym
import numpy as np
import openmdbench  # noqa: F401
from gymnasium.utils.env_checker import check_env
from openmdbench.envs import OpenMDBenchEnv, TensorObservationWrapper


def test_structured_environment_contract() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-REC-001", seed=7)
    check_env(env)
    observation, info = env.reset(seed=7)
    assert env.observation_space.contains(observation)
    assert observation["scenario_id"] == info["scenario_id"] == "MD-REC-001"
    result, _, terminated, truncated, _ = env.step(np.array([0.0, 0.0], dtype=np.float32))
    assert env.observation_space.contains(result)
    assert not terminated and not truncated


def test_registered_environment_and_tensor_wrapper() -> None:
    structured = gym.make(
        "OpenMDBench-v1", scenario_id="MD-TRK-001", seed=11, observation_mode="structured"
    )
    assert structured.observation_space.contains(structured.reset(seed=11)[0])
    env = TensorObservationWrapper(OpenMDBenchEnv(scenario_id="MD-TRK-001"))
    check_env(env)
    observation, _ = env.reset(seed=11)
    assert observation.shape == (8,)
    assert observation.dtype == np.float32
    assert env.observation_space.contains(observation)

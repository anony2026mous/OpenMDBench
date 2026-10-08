"""Gymnasium and terminal-state contract tests for the surface smoke environment."""

import gymnasium as gym
import numpy as np
import openmdbench  # noqa: F401 - registers the environment
import pytest
from gymnasium.utils.env_checker import check_env
from openmdbench.envs import SurfaceSmokeEnv


def test_gymnasium_contract() -> None:
    env = gym.make("OpenMDBench-SurfaceSmoke-v0", max_episode_steps=5)
    check_env(env.unwrapped)


def test_goal_terminates_and_state_cannot_advance() -> None:
    env = SurfaceSmokeEnv(goal_tolerance_m=1.0)
    env.reset(options={"position": [100.0, 100.0], "goal": [100.0, 101.0]})
    observation, _, terminated, truncated, info = env.step(np.array([1.0, 0.0]))
    assert terminated and not truncated and info["reached_goal"]
    final_position = observation["position"].copy()
    with pytest.raises(RuntimeError, match="after episode end"):
        env.step(np.array([1.0, 0.0]))
    np.testing.assert_array_equal(observation["position"], final_position)


def test_collision_terminates_independently() -> None:
    env = SurfaceSmokeEnv(obstacles=((100.0, 101.0, 1.0),))
    env.reset(options={"position": [100.0, 100.0]})
    _, _, terminated, truncated, info = env.step(np.array([1.0, 0.0]))
    assert terminated and not truncated and info["collision"]


def test_timeout_truncates_without_termination() -> None:
    env = SurfaceSmokeEnv(max_episode_steps=1)
    env.reset()
    _, _, terminated, truncated, _ = env.step(np.array([0.0, 0.0]))
    assert not terminated and truncated

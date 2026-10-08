"""End-to-end deterministic surface trajectory tests."""

import numpy as np
from openmdbench.envs import SurfaceSmokeEnv


def _trajectory(seed: int) -> tuple[np.ndarray, dict[str, object]]:
    env = SurfaceSmokeEnv(world_size_m=100_000.0, max_episode_steps=1_001)
    observation, info = env.reset(seed=seed)
    positions = [observation["position"].copy()]
    action = np.array([7.7, 45.0], dtype=np.float32)
    for _ in range(1000):
        observation, _, terminated, truncated, _ = env.step(action)
        assert not terminated and not truncated
        positions.append(observation["position"].copy())
    return np.stack(positions), info


def test_same_seed_and_actions_match_for_1000_ticks() -> None:
    first, first_info = _trajectory(7)
    second, second_info = _trajectory(7)
    np.testing.assert_array_equal(first, second)
    assert first_info == second_info
    assert first_info["seed"] == 7
    assert str(first_info["config_hash"]).startswith("sha256:")


def test_different_seed_changes_spawn() -> None:
    first, _ = _trajectory(7)
    second, _ = _trajectory(8)
    assert np.any(first != second)

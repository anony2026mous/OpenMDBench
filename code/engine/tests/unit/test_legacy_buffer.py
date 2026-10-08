"""Regression tests for the bounded legacy PPO buffer."""

from types import SimpleNamespace

import numpy as np
from framework.buffer import Buffer


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        action_space=2,
        buffer_capacity=2,
        context_len=1,
        device="cpu",
        obs_space=3,
        seed=7,
        use_bev=False,
        use_mask=False,
    )


def _insert_step(buffer: Buffer, value: float) -> None:
    data = {
        "actions": np.full((2, 1), value),
        "actions_mask": np.ones((2, 1)),
        "bevs": np.zeros((2, 1, 1, 1)),
        "bevs_next": np.zeros((2, 1, 1, 1)),
        "dones": np.zeros(2),
        "masks": np.ones(2),
        "rewards": np.full(2, value),
        "states": np.full((2, 1, 3), value),
        "states_next": np.full((2, 1, 3), value + 1),
    }
    for name, item in data.items():
        buffer.insert(name, item)


def test_buffer_is_bounded_and_repeated_sample_is_safe() -> None:
    buffer = Buffer(_config())
    for value in (1.0, 2.0, 3.0):
        _insert_step(buffer, value)
    assert buffer.size == 2
    assert all(len(values) == 2 for values in buffer.buffer_dict.values())

    first = buffer.sample(batch_size=2)
    second = buffer.sample(batch_size=2)
    assert isinstance(buffer.buffer_dict["states"], list)
    np.testing.assert_array_equal(np.sort(first[0], axis=0), np.sort(second[0], axis=0))

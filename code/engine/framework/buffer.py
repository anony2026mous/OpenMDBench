"""Bounded, repeat-safe trajectory buffer retained for legacy PPO trainers."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np


def discount_cumsum(values: np.ndarray, gamma: float) -> np.ndarray:
    """Compute discounted cumulative sums without modifying the input."""
    result = np.zeros_like(values)
    if values.size == 0:
        return result
    result[-1] = values[-1]
    for index in reversed(range(values.shape[0] - 1)):
        result[index] = values[index] + gamma * result[index + 1]
    return result


class Buffer:
    """A capacity-limited transition buffer with non-mutating sampling."""

    property_list = (
        "states",
        "states_next",
        "bevs",
        "bevs_next",
        "rewards",
        "dones",
        "masks",
        "actions",
        "actions_mask",
    )

    def __init__(self, config: Any) -> None:
        self.config = config
        self.device = config.device
        self.state_dim = config.obs_space
        self.action_dim = config.action_space
        self.length = config.context_len
        self.buffer_size = int(config.buffer_capacity)
        if self.buffer_size <= 0:
            raise ValueError("buffer_capacity must be positive")
        self.use_bev = bool(config.use_bev)
        self.use_mask = bool(config.use_mask)
        self._rng = np.random.default_rng(getattr(config, "seed", 0))
        self.buffer_dict: dict[str, list[Any]] = {}
        self.buffer_dict_clear()

    @property
    def size(self) -> int:
        """Number of complete time steps currently available."""
        return min((len(values) for values in self.buffer_dict.values()), default=0)

    def buffer_dict_clear(self) -> None:
        self.buffer_dict = {name: [] for name in self.property_list}

    def insert(self, item_name: str, data: Any) -> None:
        if item_name not in self.buffer_dict:
            raise KeyError(f"unknown buffer property: {item_name}")
        values = self.buffer_dict[item_name]
        values.append(np.array(data, copy=True) if isinstance(data, np.ndarray) else data)
        if len(values) > self.buffer_size:
            del values[: len(values) - self.buffer_size]

    def save_offline_data(self, path: str | Path) -> None:
        with Path(path).open("wb") as output:
            pickle.dump(self.buffer_dict, output)

    def _stack(self, item: str) -> np.ndarray:
        values = self.buffer_dict[item]
        if not values:
            raise ValueError(f"cannot sample an empty buffer property: {item}")
        array = np.stack(values)
        if "state" in item:
            return array.transpose(1, 0, 2, 3)
        if item in {"rewards", "dones", "masks"}:
            return array.transpose(1, 0)
        if "bevs" in item:
            return array.transpose(1, 0, 2, 3, 4)
        return array.transpose(1, 0, 2)

    def sample(self, batch_size: int = 256, length: int | None = None) -> tuple[np.ndarray, ...]:
        """Sample environment trajectories without rewriting stored lists."""
        if self.size == 0:
            raise ValueError("cannot sample before a complete transition is inserted")
        state = self._stack("states")
        environment_count = state.shape[0]
        selected_count = min(batch_size, environment_count)
        indices = self._rng.choice(environment_count, selected_count, replace=False)
        time_slice = slice(-length, None) if length is not None else slice(None)

        def selected(item: str) -> np.ndarray:
            return self._stack(item)[indices, time_slice]

        bev = selected("bevs") if self.use_bev else None
        bev_next = selected("bevs_next") if self.use_bev else None
        action_mask = selected("actions_mask") if self.use_mask else None
        return (
            selected("states"),
            selected("actions"),
            selected("rewards"),
            selected("dones"),
            selected("states_next"),
            bev,
            bev_next,
            selected("masks"),
            action_mask,
        )

"""Python, Gymnasium and vector interfaces sharing one session authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from openmdbench.sessions.gateway import AgentGateway
from openmdbench.sessions.session import ObservationSnapshot


class JsonObjectSpace(gym.Space[dict[str, Any]]):
    """A JSON-object contract for scenario-dependent public observations."""

    def __init__(self) -> None:
        super().__init__(shape=None, dtype=None)

    def sample(self, mask: Any = None, probability: Any = None) -> dict[str, Any]:
        del mask, probability
        return {}

    def contains(self, value: Any) -> bool:
        return isinstance(value, Mapping)


class StructuredPythonAdapter:
    def __init__(
        self, scenario_id: str, *, seed: int = 0, gateway: AgentGateway | None = None
    ) -> None:
        self.gateway = gateway or AgentGateway()
        self.scenario_id = scenario_id
        self.seed = seed
        self.session_id: str | None = None

    def reset(self, *, seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.session_id is not None:
            self.gateway.close(self.session_id)
        session = self.gateway.create(self.scenario_id, seed=self.seed if seed is None else seed)
        self.session_id = session.session_id
        self.gateway.start(session.session_id)
        snapshot = session.snapshot()
        return snapshot.observation, self._info(snapshot)

    def step(
        self, action: object | None
    ) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        snapshot = self.gateway.step(self._identifier(), action)
        return (
            snapshot.observation,
            snapshot.reward,
            snapshot.terminated,
            snapshot.truncated,
            self._info(snapshot),
        )

    def close(self) -> None:
        if self.session_id is not None:
            self.gateway.close(self.session_id)
            self.session_id = None

    def _identifier(self) -> str:
        if self.session_id is None:
            raise RuntimeError("adapter must be reset before use")
        return self.session_id

    @staticmethod
    def _info(snapshot: ObservationSnapshot) -> dict[str, Any]:
        return {
            "session_id": snapshot.session_id,
            "scenario_hash": snapshot.scenario_hash,
            "tick": snapshot.tick,
            "state": snapshot.state.value,
        }


class GymnasiumSessionEnv(gym.Env[dict[str, Any], np.ndarray]):
    metadata = {"render_modes": []}

    def __init__(self, scenario_id: str, *, seed: int = 0) -> None:
        self.adapter = StructuredPythonAdapter(scenario_id, seed=seed)
        self.observation_space = JsonObjectSpace()
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0], dtype=np.float32),
            high=np.array([80.0, 360.0], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        del options
        super().reset(seed=seed)
        return self.adapter.reset(seed=seed)

    def step(self, action: np.ndarray) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        if not self.action_space.contains(action):
            raise ValueError("action is outside the public action space")
        return self.adapter.step(action)

    def close(self) -> None:
        self.adapter.close()


class VectorSessionEnv:
    """Deterministic vector facade; each member owns an independent session."""

    def __init__(self, scenario_id: str, seeds: Sequence[int]) -> None:
        if not seeds:
            raise ValueError("at least one seed is required")
        if len(seeds) != len(set(seeds)):
            raise ValueError("vector session seeds must be unique")
        self.envs = tuple(StructuredPythonAdapter(scenario_id, seed=seed) for seed in seeds)

    def reset(self) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        results = tuple(env.reset() for env in self.envs)
        return tuple(item[0] for item in results), tuple(item[1] for item in results)

    def step(
        self, actions: Sequence[object]
    ) -> tuple[tuple[dict[str, Any], float, bool, bool, dict[str, Any]], ...]:
        if len(actions) != len(self.envs):
            raise ValueError("one action is required per vector member")
        return tuple(env.step(action) for env, action in zip(self.envs, actions, strict=True))

    def close(self) -> None:
        for env in self.envs:
            env.close()

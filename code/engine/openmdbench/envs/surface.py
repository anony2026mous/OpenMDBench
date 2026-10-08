"""Minimal CPU surface-USV closed loop with a strict Gymnasium contract."""

from __future__ import annotations

import math
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from numpy.typing import NDArray

from openmdbench.core.rng import SessionRNG, configuration_hash
from openmdbench.core.units import heading_deg_to_math_rad
from openmdbench.domains.surface.actions import validate_kinematic_actions


class SurfaceSmokeEnv(gym.Env[dict[str, NDArray[np.float32]], NDArray[np.float32]]):
    """One kinematic USV used to verify Phase-0 environment semantics on CPU."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        world_size_m: float = 2_000.0,
        max_episode_steps: int = 1_000,
        goal_tolerance_m: float = 10.0,
        collision_radius_m: float = 5.0,
        obstacles: tuple[tuple[float, float, float], ...] = (),
    ) -> None:
        super().__init__()
        if world_size_m <= 0 or max_episode_steps <= 0:
            raise ValueError("world size and max episode steps must be positive")
        self.world_size_m = float(world_size_m)
        self.max_episode_steps = int(max_episode_steps)
        self.goal_tolerance_m = float(goal_tolerance_m)
        self.collision_radius_m = float(collision_radius_m)
        self.obstacles = obstacles
        self._rng = SessionRNG(0)
        self.config_hash = configuration_hash(
            {
                "collision_radius_m": self.collision_radius_m,
                "goal_tolerance_m": self.goal_tolerance_m,
                "max_episode_steps": self.max_episode_steps,
                "obstacles": self.obstacles,
                "world_size_m": self.world_size_m,
            }
        )
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0], dtype=np.float32),
            high=np.array(
                [12.9, np.nextafter(np.float32(360.0), np.float32(0.0))], dtype=np.float32
            ),
            dtype=np.float32,
        )
        vector_bound = np.full(2, self.world_size_m, dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "goal_direction": spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32),
                "position": spaces.Box(0.0, vector_bound, shape=(2,), dtype=np.float32),
                "velocity": spaces.Box(-12.9, 12.9, shape=(2,), dtype=np.float32),
            }
        )
        self._position = np.zeros(2, dtype=np.float64)
        self._velocity = np.zeros(2, dtype=np.float64)
        self._goal = np.zeros(2, dtype=np.float64)
        self._step_count = 0
        self._episode_ended = False

    def _observation(self) -> dict[str, NDArray[np.float32]]:
        difference = self._goal - self._position
        distance = float(np.linalg.norm(difference))
        direction = difference / distance if distance > 0.0 else np.zeros(2)
        return {
            "goal_direction": direction.astype(np.float32),
            "position": self._position.astype(np.float32),
            "velocity": self._velocity.astype(np.float32),
        }

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, NDArray[np.float32]], dict[str, Any]]:
        super().reset(seed=seed)
        session_seed = 0 if seed is None else seed
        self._rng.reset(session_seed)
        options = options or {}
        default_position = self._rng.generator.uniform(50.0, 150.0, size=2)
        self._position = np.asarray(options.get("position", default_position), dtype=np.float64)
        self._goal = np.asarray(
            options.get("goal", [self.world_size_m - 100.0, self.world_size_m - 100.0]),
            dtype=np.float64,
        )
        if self._position.shape != (2,) or self._goal.shape != (2,):
            raise ValueError("position and goal reset options must contain two coordinates")
        if np.any(self._position < 0.0) or np.any(self._position > self.world_size_m):
            raise ValueError("initial position must be inside the world")
        self._velocity = np.zeros(2, dtype=np.float64)
        self._step_count = 0
        self._episode_ended = False
        return self._observation(), {
            "config_hash": self.config_hash,
            "distance_to_goal": self._distance_to_goal(),
            "seed": self._rng.seed,
        }

    def _distance_to_goal(self) -> float:
        return float(np.linalg.norm(self._goal - self._position))

    def _has_collision(self) -> bool:
        if np.any(self._position < 0.0) or np.any(self._position > self.world_size_m):
            return True
        for obstacle_x, obstacle_y, obstacle_radius in self.obstacles:
            distance = math.hypot(self._position[0] - obstacle_x, self._position[1] - obstacle_y)
            if distance <= self.collision_radius_m + obstacle_radius:
                return True
        return False

    def step(
        self, action: NDArray[np.float32]
    ) -> tuple[dict[str, NDArray[np.float32]], float, bool, bool, dict[str, Any]]:
        if self._episode_ended:
            raise RuntimeError(
                "step() called after episode end; call reset() before stepping again"
            )
        validated = validate_kinematic_actions(action)
        speed_mps, heading_deg = float(validated[0]), float(validated[1])
        angle_rad = heading_deg_to_math_rad(heading_deg)
        self._velocity = speed_mps * np.array([math.cos(angle_rad), math.sin(angle_rad)])
        previous_distance = self._distance_to_goal()
        self._position += self._velocity
        self._step_count += 1

        collision = self._has_collision()
        reached_goal = self._distance_to_goal() <= self.goal_tolerance_m
        terminated = collision or reached_goal
        truncated = self._step_count >= self.max_episode_steps and not terminated
        self._episode_ended = terminated or truncated

        reward = previous_distance - self._distance_to_goal() - 0.1
        if reached_goal:
            reward += 200.0
        if collision:
            reward -= 500.0
        info = {
            "collision": collision,
            "distance_to_goal": self._distance_to_goal(),
            "reached_goal": reached_goal,
        }
        return self._observation(), float(reward), terminated, truncated, info

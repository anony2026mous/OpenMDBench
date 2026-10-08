"""RF-07 configuration-selected adapter over the existing simulation kernel."""

from __future__ import annotations

from typing import Any

import numpy as np

from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import (
    AD2EasyBlueAgent,
    AD2HardBlueAgent,
    AD2MediumBlueAgent,
    AD2RedBaselineAgent,
)
from openmdbench.scenarios.resolved import ResolvedScenario
from openmdbench.visualization.live import VisualizationView, frame_from_world
from openmdbench.visualization.schema import VisualizationFrame


class SessionRuntime:
    """Consume a resolved scenario without introducing another world or tick loop.

    Every authoritative tick delegates to ``OpenMDBenchEnv.step`` or its existing
    bilateral adapter. Capability selection uses resolved component keys rather
    than scenario IDs.
    """

    def __init__(
        self, resolved: ResolvedScenario, seed: int, *, builtin_policies: bool = False
    ) -> None:
        self.resolved = resolved
        self.seed = seed
        self.builtin_policies = builtin_policies
        self._env = OpenMDBenchEnv(seed=seed, resolved_scenario=resolved)
        self._blue_observation: Any = None
        self._red_observation: Any = None
        self._ad2_blue_agent: Any = None
        self._ad2_red_agent: Any = None

    @property
    def pipeline_trace(self) -> tuple[tuple[str, str], ...]:
        return self._env.last_dynamics_trace

    @property
    def outcome(self) -> str | None:
        adjudicator = self._env._adjudicator
        return adjudicator.result.outcome.value if adjudicator and adjudicator.result else None

    def reset(self, *, seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        effective_seed = self.seed if seed is None else seed
        observation, info = self._env.reset(seed=effective_seed)
        if self.builtin_policies and "md_ad_002" in self.resolved.components:
            if self._env.world is None:
                raise RuntimeError("MD-AD capability requires a formal world")
            protected_2d = (
                float(self._env._protected_point[0]),
                float(self._env._protected_point[1]),
            )
            difficulty = self.resolved.difficulty
            blue_types = {
                "easy": AD2EasyBlueAgent,
                "medium": AD2MediumBlueAgent,
                "hard": AD2HardBlueAgent,
            }
            self._ad2_red_agent = AD2RedBaselineAgent(protected_2d)
            self._ad2_blue_agent = blue_types[difficulty]((*protected_2d, 100.0))
            self._red_observation = self._env.red_observation()
            self._blue_observation = self._env.public_observation("blue")
            self._ad2_red_agent.reset(self._red_observation, effective_seed)
            self._ad2_blue_agent.reset(self._blue_observation, effective_seed)
        return observation, info

    def step(self, action: object) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        if self._ad2_blue_agent is not None and self._ad2_red_agent is not None:
            red_batch = self._ad2_red_agent.act(self._red_observation)
            if self.resolved.difficulty == "hard":
                _, reward, terminated, truncated, info = self._env.step_red_action_batch(red_batch)
                self._blue_observation = self._env.public_observation("blue")
            else:
                blue_batch = self._ad2_blue_agent.act(self._blue_observation)
                internal_red = self._env._validate_red_batch(red_batch)
                self._blue_observation, _, terminated, info = self._env.step_bilateral(
                    blue_batch, internal_red
                )
                reward = 0.0
                truncated = False
            self._red_observation = self._env.red_observation()
            return self._env._observation(), reward, terminated, truncated, dict(info)
        values = np.asarray(action, dtype=np.float32)
        return self._env.step(values)

    def close(self) -> None:
        self._env.close()

    def visualization_frame(self, view: VisualizationView) -> VisualizationFrame:
        if self._env.world is None:
            raise RuntimeError("runtime has no formal world to visualize")
        frame = frame_from_world(
            self._env.world,
            view=view,
            geo_frame=self._env.geo_frame,
        )
        return frame.model_copy(
            update={
                "session_id": self._env.world.session_id,
                "scenario_id": self.resolved.scenario_id,
                "sim_time_s": self._env.world.tick * float(self.resolved.clock.tick_seconds or 1.0),
                "map_identity": self._env.map_metadata,
            }
        )

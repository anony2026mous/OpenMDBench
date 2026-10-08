"""
OpenMDBench — User-Local Hybrid Agent (ULHA) Client

The ULHA client is the agent-side interface to the CSS.
It communicates with the CSS exclusively through the polling API —
the agent NEVER accesses the environment directly.

This is the key abstraction that enables distributed evaluation:
the agent runs on the user's infrastructure, the CSS runs on the
benchmark server, and they communicate via a standardized protocol.

For Phase 0, the ULHA client wraps a CSS instance in-process.
For Phase 1+, it wraps HTTP calls to a remote CSS.

Reference: Section 3.3, Appendix B/F of OpenMDBench paper.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.css_server import CentralSimulationServer


class ULHAClient:
    """
    User-Local Hybrid Agent client — in-process mode.

    Wraps a CSS instance and provides the polling-based interface
    that agents use.  Agents call:
      - reset()          → init session, get initial obs
      - get_observation() → poll current obs
      - submit_actions()  → send actions, get next obs + reward
      - close()           → end session, get final scores

    This mirrors the HTTP API exactly, so switching to remote CSS
    only requires changing this class (not the agent code).
    """

    def __init__(
        self,
        css: CentralSimulationServer,
        agent_name: str,
        scenario_id: str = "grid_simple",
        difficulty: str = "simple",
        role: str = "blue",
        seed: int = 42,
    ):
        self.css = css
        self.agent_name = agent_name
        self.scenario_id = scenario_id
        self.difficulty = difficulty
        self.role = role
        self.seed = seed
        self.session_id: Optional[str] = None
        self.last_observation: Optional[dict] = None
        self.last_reward: float = 0.0
        self.done: bool = False

    def reset(self) -> dict:
        """
        Initialize a new session and return the initial observation.

        This corresponds to:
          POST /api/v1/session/init
          GET  /api/v1/session/{id}/observation
        """
        self.session_id = self.css.init_session(
            scenario_id=self.scenario_id,
            difficulty=self.difficulty,
            role=self.role,
            agent_name=self.agent_name,
            seed=self.seed,
        )
        self.last_observation = self.css.poll_observation(self.session_id)
        self.last_reward = 0.0
        self.done = False
        return self.last_observation

    def get_observation(self) -> dict:
        """
        Poll the current observation.

        Corresponds to: GET /api/v1/session/{id}/observation
        """
        if self.session_id is None:
            raise RuntimeError("Session not initialized. Call reset() first.")
        self.last_observation = self.css.poll_observation(self.session_id)
        return self.last_observation

    def submit_actions(self, actions: dict) -> dict:
        """
        Submit actions and advance one step.

        Corresponds to: POST /api/v1/session/{id}/actions

        Returns:
            {"observation": dict, "reward": float, "done": bool}
        """
        if self.session_id is None:
            raise RuntimeError("Session not initialized.")

        result = self.css.submit_actions(self.session_id, actions)
        self.last_observation = result["observation"]
        self.last_reward = result["reward"]
        self.done = result["done"]
        return result

    def record_plan(self, plan: dict):
        """
        Record an upper-layer planning decision for trajectory.
        Called by hybrid agents after their LLM planner runs.
        """
        if self.session_id:
            self.css.record_upper_layer_decision(self.session_id, plan)

    def close(self) -> dict:
        """
        End the session and get final scores.

        Corresponds to: POST /api/v1/session/{id}/end
        """
        if self.session_id is None:
            raise RuntimeError("Session not initialized.")

        result = self.css.end_session(self.session_id)
        self.session_id = None
        return result

    def get_env(self):
        """
        Get the underlying environment (for local observations).
        NOTE: This breaks the distributed abstraction!
        Only use for RL agents that need local 5x5 observations.
        In Phase 1+, local observations will be served via the API.
        """
        if self.session_id is None:
            raise RuntimeError("Session not initialized.")
        return self.css.get_env(self.session_id)


class ULHAHTTPClient:
    """
    User-Local Hybrid Agent client — HTTP mode (Phase 1+).

    Connects to a remote CSS via HTTP.  Same interface as ULHAClient
    but all calls go through the network.

    Usage:
        client = ULHAHTTPClient("http://localhost:5000", "my_agent")
        obs = client.reset()
        while not client.done:
            actions = my_agent.act(obs)
            result = client.submit_actions(actions)
            obs = result["observation"]
        final = client.close()
    """

    def __init__(
        self,
        base_url: str,
        agent_name: str,
        scenario_id: str = "grid_simple",
        difficulty: str = "simple",
        role: str = "blue",
        seed: int = 42,
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_name = agent_name
        self.scenario_id = scenario_id
        self.difficulty = difficulty
        self.role = role
        self.seed = seed
        self.session_id: Optional[str] = None
        self.last_observation: Optional[dict] = None
        self.last_reward: float = 0.0
        self.done: bool = False

    def _post(self, path: str, data: dict = None) -> dict:
        import requests
        resp = requests.post(f"{self.base_url}{path}", json=data or {}, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str) -> dict:
        import requests
        resp = requests.get(f"{self.base_url}{path}", timeout=60)
        resp.raise_for_status()
        return resp.json()

    def reset(self) -> dict:
        result = self._post("/api/v1/session/init", {
            "scenario_id": self.scenario_id,
            "difficulty": self.difficulty,
            "role": self.role,
            "agent_name": self.agent_name,
            "seed": self.seed,
        })
        self.session_id = result["session_id"]
        self.last_observation = result["initial_observation"]
        self.done = False
        return self.last_observation

    def get_observation(self) -> dict:
        obs = self._get(f"/api/v1/session/{self.session_id}/observation")
        self.last_observation = obs
        return obs

    def submit_actions(self, actions: dict) -> dict:
        result = self._post(f"/api/v1/session/{self.session_id}/actions", {
            "actions": actions,
        })
        self.last_observation = result["observation"]
        self.last_reward = result["reward"]
        self.done = result["done"]
        return result

    def close(self) -> dict:
        result = self._post(f"/api/v1/session/{self.session_id}/end")
        self.session_id = None
        return result

"""
OpenMDBench — Central Simulation Server (CSS)

The CSS is the single source of truth for the environment state.
It wraps the simulation environment and exposes a clean interface:
  - init_session()   → create a new evaluation session
  - poll_observation() → get current observation (ULHA calls this)
  - submit_actions()  → receive actions and advance env
  - end_session()     → finalize and return metrics

All agent interaction goes through this interface — agents NEVER
access the environment directly.  This is the core of C3 (distributed
open evaluation architecture).

For Phase 0 (grid concept validation), the CSS runs in-process.
For Phase 1+, it runs as an HTTP server (see server.py).

Reference: Section 3.3, Appendix B of OpenMDBench paper.
"""

from __future__ import annotations

import threading
import uuid
import time
from typing import Any, Dict, Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_env.grid_env import GridEnv, MAX_STEPS
from evaluation.trajectory import TrajectoryRecorder
from evaluation.metrics import MetricEngine


class CSSSession:
    """A single evaluation session managed by the CSS."""

    def __init__(
        self,
        session_id: str,
        env: GridEnv,
        scenario_id: str,
        difficulty: str,
        role: str,
        agent_name: str,
        seed: int,
    ):
        self.session_id = session_id
        self.env = env
        self.scenario_id = scenario_id
        self.difficulty = difficulty
        self.role = role
        self.agent_name = agent_name
        self.seed = seed
        self.status = "initialized"  # initialized | running | completed
        self.step_count = 0


class CentralSimulationServer:
    """
    Central Simulation Server — manages all evaluation sessions.

    Usage:
        css = CentralSimulationServer()
        session_id = css.init_session("grid_simple", "simple", "blue", "hybrid_v1", seed=42)
        obs = css.poll_observation(session_id)
        result = css.submit_actions(session_id, {"blue_0": 3, "blue_1": 0, ...})
        # ... repeat poll/submit until done ...
        final = css.end_session(session_id)
    """

    def __init__(self, output_dir: str = "evaluation_output"):
        self.output_dir = output_dir
        self.sessions: Dict[str, CSSSession] = {}
        self._sessions_lock = threading.Lock()  # guards session table only;
        # each session's env is touched by a single match thread at a time
        self.trajectory_recorder = TrajectoryRecorder(
            output_dir=os.path.join(output_dir, "trajectories")
        )
        self.metric_engine = MetricEngine(alpha=0.5, beta=0.5)

    def init_session(
        self,
        scenario_id: str = "grid_simple",
        difficulty: str = "simple",
        role: str = "blue",
        agent_name: str = "default",
        seed: int = 42,
    ) -> str:
        """
        Initialize a new evaluation session.

        Creates the environment, starts trajectory recording,
        and returns the initial observation.

        Returns:
            session_id
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # Create environment
        env = GridEnv(difficulty=difficulty, seed=seed)

        # Create session
        session = CSSSession(
            session_id=session_id,
            env=env,
            scenario_id=scenario_id,
            difficulty=difficulty,
            role=role,
            agent_name=agent_name,
            seed=seed,
        )
        with self._sessions_lock:
            self.sessions[session_id] = session

        # Start trajectory recording
        self.trajectory_recorder.start_episode(
            session_id=session_id,
            scenario_id=scenario_id,
            difficulty=difficulty,
            role=role,
            agent_name=agent_name,
            seed=seed,
        )

        return session_id

    def poll_observation(self, session_id: str, role: Optional[str] = None) -> dict:
        """
        Poll the current observation (ULHA calls this every step).

        Each side receives its OWN view of the world (symmetric partial
        observability).  Defaults to the session's role; an explicit
        role lets a referee/harness poll the opposing view.
        """
        session = self._get_session(session_id)
        obs_role = role if role is not None else session.role
        return session.env._get_observation(role=obs_role)

    def submit_actions(self, session_id: str, actions: dict) -> dict:
        """
        Submit actions and advance the environment by one step.

        The CSS executes the actions, advances simulation time,
        computes the reward, and records the trajectory.

        Args:
            session_id: the session ID
            actions: {unit_id: action_int} from the ULHA

        Returns:
            {
                "observation": next observation,
                "reward": float,
                "done": bool,
            }
        """
        session = self._get_session(session_id)
        session.status = "running"

        # Record current observation (before action)
        obs_before = session.env._get_observation()

        # Execute actions
        blue_actions = {}
        red_actions = {}
        for uid, action in actions.items():
            if uid.startswith("blue"):
                blue_actions[uid] = int(action)
            elif uid.startswith("red"):
                red_actions[uid] = int(action)

        # Step the environment (uid-prefix split above already routed
        # each action to its side; env.step always takes (blue, red))
        obs_after = session.env.step(blue_actions, red_actions)

        # Compute reward
        reward = session.env.compute_reward(role=session.role)

        # Record trajectory
        self.trajectory_recorder.record_step(
            session_id=session_id,
            t=session.env.step_count,
            observation=obs_before,
            action=actions,
            reward=reward,
            upper_layer_decision=None,  # agents can set this separately
            lower_layer_actions=actions,
        )

        session.step_count = session.env.step_count

        return {
            "observation": obs_after,
            "reward": reward,
            "done": session.env.done,
        }

    def record_upper_layer_decision(self, session_id: str, decision: dict):
        """
        Record an upper-layer (LLM) planning decision.
        Called by agents that have a separate planning step.
        This is stored in the trajectory for counterfactual replay.
        """
        session = self._get_session(session_id)
        # The decision is attached to the next timestep — the one whose
        # actions execute this plan (agents decide BEFORE submitting).
        self.trajectory_recorder.note_upper_layer_decision(session_id, decision)

    def end_session(self, session_id: str) -> dict:
        """
        End the session and return final scores.

        Computes all layered metrics, finalizes trajectory recording,
        and returns the complete evaluation result.
        """
        session = self._get_session(session_id)
        session.status = "completed"

        # Compute metrics
        env_metrics = session.env.get_episode_metrics()
        metric_result = self.metric_engine.compute(
            env_metrics,
            max_steps=MAX_STEPS,
        )

        # Finalize trajectory
        self.trajectory_recorder.end_episode(
            session_id=session_id,
            metrics={
                **env_metrics,
                "planning_score": metric_result.planning_score,
                "execution_score": metric_result.execution_score,
                "composite_score": metric_result.composite_score,
                **metric_result.details,
            },
            winner=session.env.winner,
        )

        # Build result
        result = {
            "session_id": session_id,
            "scenario_id": session.scenario_id,
            "difficulty": session.difficulty,
            "role": session.role,
            "agent_name": session.agent_name,
            "seed": session.seed,
            "steps": session.step_count,
            "winner": session.env.winner,
            "env_metrics": env_metrics,
            "planning_score": metric_result.planning_score,
            "execution_score": metric_result.execution_score,
            "composite_score": metric_result.composite_score,
            "metric_details": metric_result.details,
        }

        # Clean up session
        with self._sessions_lock:
            self.sessions.pop(session_id, None)

        return result

    def get_env(self, session_id: str) -> GridEnv:
        """Get the underlying environment (for advanced use cases)."""
        return self._get_session(session_id).env

    def _get_session(self, session_id: str) -> CSSSession:
        with self._sessions_lock:
            session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        return session

    def save_trajectories(self, filename: Optional[str] = None) -> str:
        """Save all recorded trajectories to disk."""
        return self.trajectory_recorder.save(filename)

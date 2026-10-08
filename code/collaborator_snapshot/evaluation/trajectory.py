"""
OpenMDBench — Trajectory Recorder

Records the full observation-action-reward trace at every timestep,
including upper-layer (LLM) planning decisions and lower-layer (RL)
execution actions.  This data is required for:
  - Phase 4: Counterfactual replay attribution (ΔP, ΔE, ΔI)
  - Phase 5: Effective coupling C_effective computation
  - Debugging and analysis

Reference: Section 3.5.1 of OpenMDBench paper.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TimestepRecord:
    """One timestep of the trajectory."""
    t: int
    observation: dict           # full observation sent to ULHA
    action: dict                # full action received from ULHA
    reward: float               # reward computed by CSS
    upper_layer_decision: Optional[dict] = None   # LLM plan (if any)
    lower_layer_actions: Optional[dict] = None     # per-unit movements
    env_state: Optional[dict] = None              # internal state (for replay)


@dataclass
class EpisodeRecord:
    """One complete episode trajectory."""
    session_id: str
    scenario_id: str
    difficulty: str
    role: str                   # "blue" | "red"
    agent_name: str
    seed: int
    start_time: float
    end_time: float = 0.0
    timesteps: List[TimestepRecord] = field(default_factory=list)
    final_metrics: dict = field(default_factory=dict)
    winner: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def length(self) -> int:
        return len(self.timesteps)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "scenario_id": self.scenario_id,
            "difficulty": self.difficulty,
            "role": self.role,
            "agent_name": self.agent_name,
            "seed": self.seed,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "length": self.length,
            "timesteps": [asdict(ts) for ts in self.timesteps],
            "final_metrics": self.final_metrics,
            "winner": self.winner,
        }


class TrajectoryRecorder:
    """
    Records trajectories for multiple episodes.

    Thread-safe and multi-session capable: active episodes are keyed by
    session_id, so several matches can record concurrently (required
    for parallel tournament execution and the distributed CSS design).

    Usage:
        recorder = TrajectoryRecorder(output_dir="trajectories")
        recorder.start_episode(session_id, scenario_id, ...)
        for each step:
            recorder.record_step(session_id, t, obs, action, reward, ...)
        recorder.end_episode(session_id, metrics, winner)
        recorder.save()
    """

    def __init__(self, output_dir: str = "trajectories"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._active: Dict[str, EpisodeRecord] = {}
        self.history: List[EpisodeRecord] = []
        self._lock = threading.Lock()
        # Pending upper-layer decisions: recorded by the agent BEFORE it
        # submits actions, attached to the timestep that executes them.
        self._pending_uld: Dict[str, Optional[dict]] = {}

    def start_episode(
        self,
        session_id: str,
        scenario_id: str,
        difficulty: str,
        role: str,
        agent_name: str,
        seed: int,
    ):
        """Begin recording a new episode for the given session."""
        record = EpisodeRecord(
            session_id=session_id,
            scenario_id=scenario_id,
            difficulty=difficulty,
            role=role,
            agent_name=agent_name,
            seed=seed,
            start_time=time.time(),
        )
        with self._lock:
            self._active[session_id] = record

    def get_active(self, session_id: str) -> Optional[EpisodeRecord]:
        """Get the active episode record for a session (or None)."""
        with self._lock:
            return self._active.get(session_id)

    def note_upper_layer_decision(self, session_id: str, decision: dict):
        """
        Register an upper-layer (LLM) planning decision.  It is attached
        to the NEXT recorded timestep — the one whose actions execute
        this plan.
        """
        with self._lock:
            if session_id in self._active:
                self._pending_uld[session_id] = decision

    def record_step(
        self,
        session_id: str,
        t: int,
        observation: dict,
        action: dict,
        reward: float,
        upper_layer_decision: Optional[dict] = None,
        lower_layer_actions: Optional[dict] = None,
        env_state: Optional[dict] = None,
    ):
        """Record one timestep for the given session."""
        record = self.get_active(session_id)
        if record is None:
            raise RuntimeError(
                f"No active episode for session {session_id}. "
                "Call start_episode first."
            )

        step = TimestepRecord(
            t=t,
            observation=observation,
            action=action,
            reward=reward,
            upper_layer_decision=upper_layer_decision,
            lower_layer_actions=lower_layer_actions,
            env_state=env_state,
        )
        with self._lock:
            # Attach a pending upper-layer decision (noted by the agent
            # before submitting these actions), if any.
            pending = self._pending_uld.pop(session_id, None)
            if pending is not None:
                step.upper_layer_decision = pending
            record.timesteps.append(step)

    def end_episode(
        self,
        session_id: str,
        metrics: dict,
        winner: Optional[str] = None,
    ):
        """Finalize the episode recording for the given session."""
        with self._lock:
            record = self._active.pop(session_id, None)
            if record is None:
                raise RuntimeError(
                    f"No active episode for session {session_id}."
                )
            record.end_time = time.time()
            record.final_metrics = metrics
            record.winner = winner
            self.history.append(record)
            self._pending_uld.pop(session_id, None)

    def save(self, filename: Optional[str] = None):
        """Save all recorded episodes to disk."""
        if filename is None:
            filename = f"trajectories_{int(time.time())}.json"
        path = os.path.join(self.output_dir, filename)

        data = {
            "num_episodes": len(self.history),
            "episodes": [ep.to_dict() for ep in self.history],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def get_last_episode(self) -> Optional[EpisodeRecord]:
        """Get the most recently completed episode."""
        return self.history[-1] if self.history else None

    def get_upper_layer_decisions(self, episode_idx: int = -1) -> List[dict]:
        """
        Extract upper-layer (LLM) decisions from an episode.
        Used for counterfactual replay in Phase 4.
        """
        ep = self.history[episode_idx]
        decisions = []
        for ts in ep.timesteps:
            if ts.upper_layer_decision is not None:
                decisions.append({
                    "t": ts.t,
                    "decision": ts.upper_layer_decision,
                })
        return decisions

    def get_action_sequence(self, episode_idx: int = -1) -> List[dict]:
        """
        Extract the full action sequence from an episode.
        Returns list of {t, action} for replay.
        """
        ep = self.history[episode_idx]
        return [{"t": ts.t, "action": ts.action} for ts in ep.timesteps]

    def clear(self):
        """Clear all recorded data."""
        with self._lock:
            self._active.clear()
            self._pending_uld.clear()
            self.history.clear()

"""Optional action re-simulation drift detector; never used by ordinary playback."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import numpy as np

from openmdbench.envs import OpenMDBenchEnv
from openmdbench.replay.reader import ReplayReader
from openmdbench.visualization.schema import VisualizationEntity


@dataclass(frozen=True, slots=True)
class DriftReport:
    matched: bool
    first_drift_tick: int | None = None
    field: str | None = None
    expected: object | None = None
    actual: object | None = None


def verify_action_replay(reader: ReplayReader, *, atol: float = 1e-6) -> DriftReport:
    """Re-run actions and report the first difference from authority snapshots."""
    if atol < 0.0:
        raise ValueError("atol cannot be negative")
    metadata = reader.metadata
    env = OpenMDBenchEnv(scenario_id=metadata.scenario_id, seed=metadata.seed)
    observation, _ = env.reset(seed=metadata.seed)
    if env.scenario_hash != metadata.config_hash:
        return DriftReport(False, 0, "config_hash", metadata.config_hash, env.scenario_hash)
    frames = reader.frames()
    try:
        first = next(frames)
    except StopIteration:
        return DriftReport(False, None, "frames", "at least one frame", "empty")
    drift = _compare_state(
        first.timestamp, first.entities[0] if first.entities else None, observation, atol
    )
    if drift is not None:
        return drift
    for frame in frames:
        if len(frame.actions) != 1:
            return DriftReport(False, frame.timestamp, "actions", "one action", len(frame.actions))
        action = frame.actions[0]
        if action.get("type") != "kinematic":
            return DriftReport(
                False, frame.timestamp, "action.type", "kinematic", action.get("type")
            )
        try:
            command = np.asarray(
                [float(action["speed_mps"]), float(action["heading"])], dtype=np.float32
            )
        except (KeyError, TypeError, ValueError) as error:
            return DriftReport(
                False, frame.timestamp, "action", "valid kinematic action", str(error)
            )
        observation, _, terminated, truncated, _ = env.step(command)
        drift = _compare_state(
            frame.timestamp, frame.entities[0] if frame.entities else None, observation, atol
        )
        if drift is not None:
            return drift
        if terminated or truncated:
            break
    return DriftReport(True)


def _compare_state(
    tick: int,
    authority: VisualizationEntity | None,
    observation: Mapping[str, object],
    atol: float,
) -> DriftReport | None:
    if authority is None:
        return DriftReport(False, tick, "entities", "controlled entity", "missing")
    position = authority.position[:2]
    velocity = authority.velocity[:2]
    actual_position = cast(list[float], observation["position"])
    actual_velocity = cast(list[float], observation["velocity"])
    if not np.allclose(position, actual_position, rtol=0.0, atol=atol):
        return DriftReport(False, tick, "position", position, actual_position)
    if not np.allclose(velocity, actual_velocity, rtol=0.0, atol=atol):
        return DriftReport(False, tick, "velocity", velocity, actual_velocity)
    return None

"""Goal encoding for the fifth arm: LLM plan -> per-unit feature block.

The fifth arm replaces the rule executor with a learned one, so the LLM's goal has
to reach the network as **input**.  This module is the whole of that translation and
nothing else: it turns the broker's active `GoalCommand`s into a fixed-size,
per-unit feature block that `ie_rl_env` appends to the unit block.

Design notes that matter for the ablation:

* **Per-unit, not global.**  Every `GoalCommand` carries `parameters["unit_id"]`, so
  the goal is encoded into the slot of the unit it was issued to.  A global goal
  vector would force the network to learn the goal->unit matching itself, which is
  work the rule executor never had to do, and the ablation would then be measuring
  that instead of the executor.
* **Reads the broker, not the last LLM reply.**  Goals can be superseded or
  preempted; the rule executor reads the broker every tick, so this does too.
* **Pure.**  No session, no engine: takes plain mappings and returns an array, so
  the encoding can be tested exhaustively without building a scenario.
* **Unknown goal types raise rather than being silently dropped.**  A silently
  zeroed one-hot looks exactly like "no goal", which would make a protocol mismatch
  indistinguishable from a planning decision.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from goai_protocol import PRIORITY_EPSILON

# Order is part of the observation layout: changing it invalidates checkpoints.
GOAL_TYPE_ORDER: tuple[str, ...] = (
    "waypoint", "patrol", "track", "intercept", "hold", "return", "loiter",
    "barrier", "ambush", "reserve", "disengage",
)
N_TYPES = len(GOAL_TYPE_ORDER)
# 11 type one-hot + has_goal + has_target + target(sin,cos,dist)
#   + position(dx,dy) + speed + priority + deadline + 3 type-specific scalars
PER_UNIT_WIDTH = N_TYPES + 1 + 1 + 3 + 2 + 1 + 1 + 1 + 3

_POS_SCALE_M = 40000.0
_TYPE_SCALAR_SCALE_M = 20000.0
_DEADLINE_SCALE = 100.0


def goal_type_index(goal_type: str) -> int:
    """Index into the one-hot, or -1 when the type is not in the vocabulary."""
    try:
        return GOAL_TYPE_ORDER.index(str(goal_type))
    except ValueError:
        return -1


def encode_goals(
    goals_by_unit: Mapping[str, Sequence[Any]],
    unit_ids: Sequence[str],
    unit_positions: Mapping[str, Sequence[float]],
    *,
    objective: Sequence[float] = (0.0, 0.0),
    speed_limits: Mapping[str, float] | None = None,
    target_positions: Mapping[str, Sequence[float]] | None = None,
    tick: int = 0,
) -> np.ndarray:
    """(len(unit_ids), PER_UNIT_WIDTH) float32 feature block.

    ``goals_by_unit`` maps entity_id -> list of goal objects (or plain dicts) that
    are currently active and not terminal.  Only the **highest-priority** goal per
    unit is encoded; a unit with several active goals is a situation the rule
    executor also resolves by priority, so the encoder must not invent an ordering
    of its own.
    """
    speed_limits = speed_limits or {}
    target_positions = target_positions or {}
    out = np.zeros((len(unit_ids), PER_UNIT_WIDTH), dtype=np.float32)

    for index, unit_id in enumerate(unit_ids):
        goals = list(goals_by_unit.get(str(unit_id)) or ())
        if not goals:
            continue                                  # has_goal stays 0
        best = goals[0]
        for candidate in goals[1:]:
            if (_field(candidate, "priority", 0.5)
                    > _field(best, "priority", 0.5) + PRIORITY_EPSILON):
                best = candidate
        goal_type = str(_field(best, "goal_type", ""))
        slot = goal_type_index(goal_type)
        if slot < 0:
            raise ValueError(
                f"unknown goal_type {goal_type!r} for unit {unit_id}; "
                f"vocabulary is {GOAL_TYPE_ORDER}. A silently unset one-hot would "
                f"be indistinguishable from 'no goal'.")
        row = out[index]
        row[slot] = 1.0
        row[N_TYPES] = 1.0                            # has_goal

        params = dict(_field(best, "parameters", {}) or {})
        unit_pos = np.asarray(unit_positions.get(str(unit_id), (0.0, 0.0, 0.0)),
                              dtype=np.float64)[:2]

        # --- target direction -------------------------------------------------
        target_id = params.get("target_id")
        target_pos = target_positions.get(str(target_id)) if target_id else None
        if target_pos is None:
            target_pos = params.get("position")
        if target_pos is not None:
            tpos = np.asarray(target_pos, dtype=np.float64)[:2]
            delta = tpos - unit_pos
            dist = float(np.linalg.norm(delta))
            bearing = math.atan2(delta[0], delta[1])
            row[N_TYPES + 1] = 1.0                    # has_target
            row[N_TYPES + 2] = math.sin(bearing)
            row[N_TYPES + 3] = math.cos(bearing)
            row[N_TYPES + 4] = min(1.0, dist / _POS_SCALE_M)

        # --- waypoint offset --------------------------------------------------
        position = params.get("position")
        if position is not None:
            ppos = np.asarray(position, dtype=np.float64)[:2]
            offset = (ppos - unit_pos) / _POS_SCALE_M
            row[N_TYPES + 5] = float(np.clip(offset[0], -1.0, 1.0))
            row[N_TYPES + 6] = float(np.clip(offset[1], -1.0, 1.0))
        else:
            # No explicit waypoint: encode the offset to the protected objective,
            # which is the reference the barrier/reserve goals also use.
            offset = (np.asarray(objective, dtype=np.float64)[:2] - unit_pos) \
                / _POS_SCALE_M
            row[N_TYPES + 5] = float(np.clip(offset[0], -1.0, 1.0))
            row[N_TYPES + 6] = float(np.clip(offset[1], -1.0, 1.0))

        # --- scalars ----------------------------------------------------------
        limit = float(speed_limits.get(str(unit_id), 0.0)) or 1.0
        row[N_TYPES + 7] = float(np.clip(
            float(params.get("speed_mps") or 0.0) / limit, 0.0, 1.0))
        row[N_TYPES + 8] = float(np.clip(_field(best, "priority", 0.5), 0.0, 1.0))
        deadline = _field(best, "deadline", None)
        issued = float(_field(best, "issued_at", tick) or 0.0)
        if deadline is not None:
            remaining = max(0.0, float(deadline) - (float(tick) - issued))
            row[N_TYPES + 9] = float(np.clip(remaining / _DEADLINE_SCALE, 0.0, 1.0))
        else:
            row[N_TYPES + 9] = 1.0                    # no deadline == not urgent

        # --- type-specific scalars (unused ones stay 0) -----------------------
        for offset, key in ((10, "radius_m"), (11, "standoff_m"),
                            (12, "commit_within_m")):
            value = params.get(key)
            if value is not None:
                row[N_TYPES + offset] = float(np.clip(
                    float(value) / _TYPE_SCALAR_SCALE_M, 0.0, 1.0))
    return out


def _field(goal: Any, name: str, default: Any) -> Any:
    """Read a field from a dataclass/object or a plain mapping."""
    if isinstance(goal, Mapping):
        return goal.get(name, default)
    return getattr(goal, name, default)


def active_by_unit(active: Mapping[str, Any]) -> dict[str, list[Any]]:
    """Group a broker's ``active`` mapping into entity_id -> [goal commands].

    Broker semantics this must respect: a state carries ``command``, ``status`` and
    ``terminal``; superseded or finished goals are not executable, and only they are
    filtered here.  Priority ordering is left to the encoder.
    """
    grouped: dict[str, list[Any]] = {}
    for state in (active or {}).values():
        command = _field(state, "command", None)
        if command is None:
            continue
        if bool(_field(state, "terminal", False)):
            continue
        status = str(_field(state, "status", "") or "")
        if status in ("superseded", "completed", "failed", "timeout", "infeasible"):
            continue
        unit = _field(command, "unit_id", None)
        if not unit:
            continue
        grouped.setdefault(str(unit), []).append(command)
    return grouped


def width() -> int:
    return PER_UNIT_WIDTH


def goal_terms() -> Iterable[str]:
    """Human-readable term names, for diagnostics and the design doc."""
    names = [f"type:{t}" for t in GOAL_TYPE_ORDER]
    names += ["has_goal", "has_target", "target_sin", "target_cos", "target_dist",
              "pos_dx", "pos_dy", "speed_frac", "priority", "deadline_frac",
              "radius", "standoff", "commit_within"]
    return names

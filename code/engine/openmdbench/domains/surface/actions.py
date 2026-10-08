"""Explicit action semantics for surface dynamics."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from openmdbench.core.units import shortest_heading_error_rad

DEFAULT_MAX_NPS = 5.0
DEFAULT_MAX_RUDDER_RAD = 0.3
DEFAULT_MAX_SPEED_MPS = 12.9


@dataclass(frozen=True, slots=True)
class MMGAction:
    """MMG control input: propeller revolutions per second and rudder radians."""

    nps: float
    rudder_rad: float


@dataclass(frozen=True, slots=True)
class KinematicAction:
    """Kinematic control input: speed in m/s and public heading in degrees."""

    speed_mps: float
    heading_deg: float


def heading_to_rudder(
    target_heading_deg: float,
    current_math_rad: float,
    *,
    gain: float = 1.0,
    max_rudder_rad: float = DEFAULT_MAX_RUDDER_RAD,
) -> float:
    """Convert a target heading to a legal MMG rudder command."""
    if not all(math.isfinite(value) for value in (target_heading_deg, current_math_rad, gain)):
        raise ValueError("heading controller inputs must be finite")
    if gain <= 0.0 or max_rudder_rad <= 0.0:
        raise ValueError("heading controller gain and rudder limit must be positive")
    command = gain * shortest_heading_error_rad(target_heading_deg, current_math_rad)
    return max(-max_rudder_rad, min(max_rudder_rad, command))


def _validate_action_array(actions: NDArray[np.floating], name: str) -> NDArray[np.float64]:
    array = np.asarray(actions, dtype=np.float64)
    if array.ndim < 1 or array.shape[-1] != 2:
        raise ValueError(f"{name} actions must have final dimension 2, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} actions must contain only finite values")
    return array


def validate_action_tensor_shape(
    actions: NDArray[np.floating], *, batch_size: int, entity_count: int
) -> None:
    """Require the public Phase-0 action layout `(batch, entity, action)` exactly."""
    expected = (batch_size, entity_count, 2)
    if np.shape(actions) != expected:
        raise ValueError(f"surface actions must have shape {expected}, got {np.shape(actions)}")


def validate_mmg_actions(
    actions: NDArray[np.floating],
    *,
    max_nps: float = DEFAULT_MAX_NPS,
    max_rudder_rad: float = DEFAULT_MAX_RUDDER_RAD,
) -> NDArray[np.float64]:
    """Validate `[nps, rudder_rad]` without silently changing the command."""
    array = _validate_action_array(actions, "MMG")
    if np.any((array[..., 0] < 0.0) | (array[..., 0] > max_nps)):
        raise ValueError(f"MMG nps must be within [0, {max_nps}]")
    if np.any(np.abs(array[..., 1]) > max_rudder_rad):
        raise ValueError(f"MMG rudder_rad must be within [-{max_rudder_rad}, {max_rudder_rad}]")
    return array


def validate_kinematic_actions(
    actions: NDArray[np.floating],
    *,
    max_speed_mps: float = DEFAULT_MAX_SPEED_MPS,
) -> NDArray[np.float64]:
    """Validate `[speed_mps, heading_deg]` without silently normalizing it."""
    array = _validate_action_array(actions, "kinematic")
    if np.any((array[..., 0] < 0.0) | (array[..., 0] > max_speed_mps)):
        raise ValueError(f"kinematic speed_mps must be within [0, {max_speed_mps}]")
    if np.any((array[..., 1] < 0.0) | (array[..., 1] >= 360.0)):
        raise ValueError("kinematic heading_deg must be within [0, 360)")
    return array

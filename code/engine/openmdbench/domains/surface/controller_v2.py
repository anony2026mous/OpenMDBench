"""Scenario-independent navigation-to-actuator controller for MMG vessels."""

from __future__ import annotations

import math
from collections.abc import Mapping

from openmdbench.core.units import heading_deg_to_math_rad
from openmdbench.domains.surface.actions import MMGAction, heading_to_rudder

_DEFAULT_MAX_SPEED_MPS = 12.9
_DEFAULT_MAX_NPS = 5.0
_DEFAULT_MAX_RUDDER_RAD = 0.3
_DEFAULT_HEADING_GAIN = 1.0
_MAX_MMG_NPS = 240.0


def _positive_parameter(parameters: Mapping[str, int | float], key: str, default: float) -> float:
    value = float(parameters.get(key, default))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"MMG {key} must be a finite positive value")
    return value


def mmg_navigation_action_v2(
    *,
    current_heading_deg: float,
    target_speed_mps: float,
    target_heading_deg: float,
    parameters: Mapping[str, int | float],
) -> MMGAction:
    """Translate public speed/heading navigation into bounded MMG actuators.

    Navigation remains the public agent contract.  The propeller and rudder
    values are a deterministic, model-local implementation detail whose limits
    are carried by the selected versioned dynamics resource.
    """

    values = (current_heading_deg, target_speed_mps, target_heading_deg)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("MMG navigation inputs must be finite")
    if target_speed_mps < 0.0:
        raise ValueError("MMG target speed must be nonnegative")
    max_speed = _positive_parameter(parameters, "max_speed_mps", _DEFAULT_MAX_SPEED_MPS)
    max_nps = _positive_parameter(parameters, "max_nps", _DEFAULT_MAX_NPS)
    max_rudder = _positive_parameter(parameters, "max_rudder_rad", _DEFAULT_MAX_RUDDER_RAD)
    gain = _positive_parameter(parameters, "controller_gain", _DEFAULT_HEADING_GAIN)
    if max_nps > _MAX_MMG_NPS or max_rudder > _DEFAULT_MAX_RUDDER_RAD:
        raise ValueError("MMG controller parameters exceed trusted solver actuator limits")
    target_speed = min(float(target_speed_mps), max_speed)
    nps = max_nps * target_speed / max_speed
    rudder_rad = heading_to_rudder(
        float(target_heading_deg) % 360.0,
        heading_deg_to_math_rad(float(current_heading_deg) % 360.0),
        gain=gain,
        max_rudder_rad=max_rudder,
    )
    return MMGAction(nps=nps, rudder_rad=rudder_rad)


__all__ = ["mmg_navigation_action_v2"]

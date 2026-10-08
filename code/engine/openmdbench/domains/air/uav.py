"""Deterministic simplified UAV kinematics and original vector silhouette."""

from __future__ import annotations

import math

from matplotlib.path import Path
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.core.units import bounded_heading_deg


class UAVState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position: tuple[float, float, float]
    heading_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0, le=80.0)
    energy: float = Field(default=1.0, ge=0.0, le=1.0)


class UAVCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0, le=80.0)
    altitude_m: float = Field(ge=0.0, le=3000.0)


def step_uav(
    state: UAVState,
    command: UAVCommand,
    *,
    tick_seconds: float = 1.0,
    max_turn_rate_deg_s: float = 30.0,
    max_climb_rate_mps: float = 20.0,
    max_acceleration_mps2: float = 8.0,
    max_deceleration_mps2: float = 10.0,
    max_speed_mps: float = 80.0,
    performance_factor: float = 1.0,
) -> UAVState:
    if tick_seconds <= 0.0:
        raise ValueError("tick_seconds must be positive")
    if not 0.0 < performance_factor <= 1.0:
        raise ValueError("performance_factor must be within (0, 1]")
    effective_max_speed = max_speed_mps * performance_factor
    effective_turn_rate = max_turn_rate_deg_s * performance_factor
    heading = bounded_heading_deg(
        state.heading_deg, command.heading_deg, effective_turn_rate * tick_seconds
    )
    target_speed = min(command.speed_mps, effective_max_speed)
    speed_error = target_speed - state.speed_mps
    speed_change = max(
        -max_deceleration_mps2 * tick_seconds,
        min(max_acceleration_mps2 * tick_seconds, speed_error),
    )
    speed = max(0.0, min(effective_max_speed, state.speed_mps + speed_change))
    altitude_change = max(
        -max_climb_rate_mps * tick_seconds,
        min(max_climb_rate_mps * tick_seconds, command.altitude_m - state.position[2]),
    )
    heading_rad = math.radians(heading)
    east_velocity = speed * math.sin(heading_rad)
    north_velocity = speed * math.cos(heading_rad)
    return state.model_copy(
        update={
            "heading_deg": heading,
            "position": (
                state.position[0] + east_velocity * tick_seconds,
                state.position[1] + north_velocity * tick_seconds,
                state.position[2] + altitude_change,
            ),
            "speed_mps": speed,
        }
    )


def uav_path() -> Path:
    """Unit top view with nose, swept wings, fuselage, and tail, facing north."""
    vertices = [
        (0.0, 0.55),
        (-0.08, 0.15),
        (-0.5, -0.05),
        (-0.48, -0.18),
        (-0.08, -0.1),
        (-0.2, -0.48),
        (0.0, -0.38),
        (0.2, -0.48),
        (0.08, -0.1),
        (0.48, -0.18),
        (0.5, -0.05),
        (0.08, 0.15),
        (0.0, 0.55),
    ]
    return Path(vertices, [Path.MOVETO, *([Path.LINETO] * 11), Path.CLOSEPOLY])

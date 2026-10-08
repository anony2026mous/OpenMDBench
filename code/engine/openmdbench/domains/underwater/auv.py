"""Deterministic simplified AUV kinematics and original silhouette."""

from __future__ import annotations

import math

from matplotlib.path import Path
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.core.units import bounded_heading_deg
from openmdbench.schemas.geometry import CollisionShape, EntityGeometry


class AUVState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position: tuple[float, float, float]
    heading_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0, le=4.1)
    energy: float = Field(default=1.0, ge=0.0, le=1.0)


class AUVCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading_deg: float = Field(ge=0.0, lt=360.0)
    speed_mps: float = Field(ge=0.0, le=4.1)
    depth_m: float = Field(ge=0.0, le=300.0)


def step_auv(
    state: AUVState,
    command: AUVCommand,
    *,
    tick_seconds: float = 1.0,
    max_turn_rate_deg_s: float = 15.0,
    max_vertical_rate_mps: float = 2.0,
) -> AUVState:
    if not -300.0 <= state.position[2] <= 0.0:
        raise ValueError("AUV state z must remain between -300 and 0 metres")
    heading = bounded_heading_deg(
        state.heading_deg, command.heading_deg, max_turn_rate_deg_s * tick_seconds
    )
    target_z = -command.depth_m
    vertical_change = max(
        -max_vertical_rate_mps * tick_seconds,
        min(max_vertical_rate_mps * tick_seconds, target_z - state.position[2]),
    )
    heading_rad = math.radians(heading)
    return state.model_copy(
        update={
            "heading_deg": heading,
            "position": (
                state.position[0] + command.speed_mps * math.sin(heading_rad) * tick_seconds,
                state.position[1] + command.speed_mps * math.cos(heading_rad) * tick_seconds,
                state.position[2] + vertical_change,
            ),
            "speed_mps": command.speed_mps,
        }
    )


def auv_geometry() -> EntityGeometry:
    return EntityGeometry(
        length_m=8.0,
        width_m=1.2,
        diameter_m=1.2,
        collision_shape=CollisionShape.CAPSULE,
    )


def auv_path() -> Path:
    """Unit torpedo body with stern fins and propulsor, facing north."""
    vertices = [
        (0.0, 0.52),
        (-0.22, 0.36),
        (-0.25, -0.28),
        (-0.48, -0.42),
        (-0.18, -0.4),
        (-0.1, -0.52),
        (0.1, -0.52),
        (0.18, -0.4),
        (0.48, -0.42),
        (0.25, -0.28),
        (0.22, 0.36),
        (0.0, 0.52),
    ]
    return Path(vertices, [Path.MOVETO, *([Path.LINETO] * 10), Path.CLOSEPOLY])

"""Fixed shore radar state and original facility silhouette."""

from __future__ import annotations

from typing import Any

from matplotlib.path import Path
from pydantic import BaseModel, ConfigDict, Field


class ShoreRadarState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position: tuple[float, float, float]
    beam_heading_deg: float = Field(default=0.0, ge=0.0, lt=360.0)
    sensor_mode: str = "active_search"


def apply_shore_command(
    state: ShoreRadarState, action_type: str, parameters: dict[str, Any]
) -> ShoreRadarState:
    if action_type in {"move_to", "patrol", "return_to_base"}:
        raise ValueError(f"fixed shore radar rejects movement action: {action_type}")
    if action_type == "set_sensor_mode":
        updates: dict[str, Any] = {"sensor_mode": str(parameters["mode"])}
        if "beam_heading_deg" in parameters:
            heading = float(parameters["beam_heading_deg"])
            if not 0.0 <= heading < 360.0:
                raise ValueError("beam_heading_deg must be within [0, 360)")
            updates["beam_heading_deg"] = heading
        return state.model_copy(update=updates)
    if action_type == "hold_position":
        return state
    raise ValueError(f"unsupported shore radar action: {action_type}")


def shore_radar_path() -> Path:
    """Unit icon combining square base, tower, and north-facing antenna."""
    vertices = [
        (-0.45, -0.45),
        (0.45, -0.45),
        (0.45, -0.2),
        (0.12, -0.2),
        (0.12, 0.15),
        (0.42, 0.38),
        (0.0, 0.5),
        (-0.42, 0.38),
        (-0.12, 0.15),
        (-0.12, -0.2),
        (-0.45, -0.2),
        (-0.45, -0.45),
    ]
    return Path(vertices, [Path.MOVETO, *([Path.LINETO] * 10), Path.CLOSEPOLY])

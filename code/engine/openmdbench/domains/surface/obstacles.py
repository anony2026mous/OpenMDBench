"""Backward-compatible non-controllable surface obstacles."""

from __future__ import annotations

from enum import StrEnum

from matplotlib.path import Path
from pydantic import BaseModel, ConfigDict, Field

from openmdbench.core.entities import Domain, DynamicObstacle, Side


class ObstacleProfile(StrEnum):
    CIRCLE = "circle"
    CIVILIAN_VESSEL = "civilian_vessel"
    DEBRIS = "debris"
    BUOY = "buoy"


class LegacyCircleObstacle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    x: float
    y: float
    radius_m: float = Field(gt=0.0)
    profile: ObstacleProfile = ObstacleProfile.CIRCLE


def adapt_legacy_obstacle(obstacle: LegacyCircleObstacle) -> DynamicObstacle:
    """Convert old circle data without granting platform/control capabilities."""
    return DynamicObstacle(
        id=obstacle.id,
        side=Side.NEUTRAL,
        domain=Domain.SURFACE,
        position=(obstacle.x, obstacle.y, 0.0),
        obstacle_type=obstacle.profile.value,
    )


def civilian_vessel_path() -> Path:
    """Neutral merchant-like hull with a rectangular superstructure."""
    vertices = [
        (0.0, 0.5),
        (-0.38, 0.25),
        (-0.42, -0.45),
        (-0.18, -0.5),
        (0.18, -0.5),
        (0.42, -0.45),
        (0.38, 0.25),
        (0.0, 0.5),
    ]
    return Path(vertices, [Path.MOVETO, *([Path.LINETO] * 6), Path.CLOSEPOLY])

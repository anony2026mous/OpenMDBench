"""Registry and world transform for original entity vector paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from matplotlib.path import Path
from matplotlib.transforms import Affine2D

from openmdbench.core.entities import Lifecycle, Side
from openmdbench.domains.air import uav_path
from openmdbench.domains.shore import shore_radar_path
from openmdbench.domains.surface import usv_path
from openmdbench.domains.surface.obstacles import civilian_vessel_path
from openmdbench.domains.underwater import auv_path

Theme = Literal["standard", "colorblind"]
LineStyle = Literal["-", "--", ":"]


@dataclass(frozen=True, slots=True)
class ProfileStyle:
    facecolor: str
    edgecolor: str
    alpha: float
    linestyle: LineStyle


_PALETTES: dict[Theme, dict[Side, str]] = {
    "standard": {Side.BLUE: "#2878B5", Side.RED: "#D73027", Side.NEUTRAL: "#7F7F7F"},
    "colorblind": {Side.BLUE: "#0072B2", Side.RED: "#D55E00", Side.NEUTRAL: "#777777"},
}


def missile_path() -> Path:
    """Original generic missile silhouette, facing north in local coordinates."""

    return Path(
        [(0.0, 0.6), (-0.12, -0.45), (0.0, -0.3), (0.12, -0.45), (0.0, 0.6)],
        [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY],
    )


def path_for_profile(profile_id: str) -> Path:
    factories = {
        "armed_usv_generic": usv_path,
        "auv_generic": auv_path,
        "civilian_vessel": civilian_vessel_path,
        "civilian_usv_generic": civilian_vessel_path,
        "fast_usv_generic": usv_path,
        "shore_radar_generic": shore_radar_path,
        "missile_generic": missile_path,
        "uav_generic": uav_path,
        "usv_generic": usv_path,
    }
    try:
        return factories[profile_id]()
    except KeyError as error:
        raise ValueError(f"unknown visual profile: {profile_id}") from error


def transform_profile(
    profile_id: str,
    *,
    position: tuple[float, float],
    heading_deg: float,
    length_m: float,
    width_m: float,
) -> Path:
    """Scale a north-facing local path, rotate clockwise, and translate to world ENU."""
    transform = (
        Affine2D()
        .scale(width_m, length_m)
        .rotate_deg(-heading_deg)
        .translate(position[0], position[1])
    )
    return transform.transform_path(path_for_profile(profile_id))


def display_dimensions(
    length_m: float,
    width_m: float,
    *,
    meters_per_pixel: float,
    minimum_pixels: float = 6.0,
) -> tuple[float, float]:
    """Preserve real aspect ratio while enforcing a screen-space visibility floor."""
    if min(length_m, width_m, meters_per_pixel, minimum_pixels) <= 0.0:
        raise ValueError("dimensions, scale, and minimum size must be positive")
    scale = max(1.0, minimum_pixels * meters_per_pixel / max(length_m, width_m))
    return length_m * scale, width_m * scale


def style_for_entity(side: Side, status: Lifecycle, *, theme: Theme = "standard") -> ProfileStyle:
    """Return stable side colors and redundant terminal-state styling."""
    color = _PALETTES[theme][side]
    if status is Lifecycle.DESTROYED:
        return ProfileStyle(color, "#222222", 0.35, "--")
    if status is Lifecycle.OFFLINE:
        return ProfileStyle(color, "#222222", 0.55, ":")
    return ProfileStyle(color, "#111111", 0.9, "-")

"""USV geometry and legacy MMG adapter metadata."""

from __future__ import annotations

from collections.abc import Mapping

from matplotlib.path import Path

from openmdbench.schemas.geometry import (
    CollisionShape,
    EntityGeometry,
    GeometryPresentation,
    VisualProfile,
)


def usv_geometry_from_mmg(parameters: Mapping[str, float]) -> GeometryPresentation:
    """Use authoritative MMG length/beam for collision and rendering dimensions."""
    try:
        length_m = float(parameters["Lpp"])
        width_m = float(parameters["B"])
    except KeyError as error:
        raise ValueError(f"missing MMG hull dimension: {error.args[0]}") from error
    geometry = EntityGeometry(
        length_m=length_m,
        width_m=width_m,
        diameter_m=width_m,
        collision_shape=CollisionShape.CAPSULE,
    )
    return GeometryPresentation(
        geometry=geometry,
        visual_profile=VisualProfile(
            profile_id="usv_generic",
            minimum_display_size_m=20.0,
        ),
    )


def usv_path() -> Path:
    """Return an original unit hull centered at the origin with its bow at north."""
    vertices = [
        (0.0, 0.5),
        (-0.48, 0.2),
        (-0.42, -0.3),
        (-0.24, -0.5),
        (0.24, -0.5),
        (0.42, -0.3),
        (0.48, 0.2),
        (0.0, 0.5),
    ]
    codes = [Path.MOVETO, *([Path.LINETO] * 6), Path.CLOSEPOLY]
    return Path(vertices, codes)

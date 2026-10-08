"""Deterministic DISPLAY-free PNG export using Matplotlib Agg directly."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from openmdbench.visualization.dashboard import frame_for_view
from openmdbench.visualization.live import VisualizationView
from openmdbench.visualization.renderer import MatplotlibRenderer
from openmdbench.visualization.schema import VisualizationFrame


def export_png(
    frame: VisualizationFrame,
    output: str | Path,
    *,
    view: VisualizationView = "referee",
    world_bounds: tuple[float, float, float, float] = (0.0, 0.0, 200_000.0, 200_000.0),
    static_polygons: Sequence[Sequence[tuple[float, float]]] = (),
    static_lines: Sequence[Sequence[tuple[float, float]]] = (),
    width_pixels: int = 1_200,
    height_pixels: int = 800,
    dpi: int = 100,
) -> Path:
    if min(width_pixels, height_pixels, dpi) <= 0:
        raise ValueError("image dimensions and dpi must be positive")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure = Figure(figsize=(width_pixels / dpi, height_pixels / dpi), dpi=dpi, facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(1, 1, 1)
    axes.set_xlim(world_bounds[0], world_bounds[2])
    axes.set_ylim(world_bounds[1], world_bounds[3])
    axes.set_aspect("equal", adjustable="box")
    axes.set_title(f"OpenMDBench tick {frame.timestamp}", fontfamily="DejaVu Sans")
    renderer = MatplotlibRenderer(axes, static_polygons=static_polygons, static_lines=static_lines)
    renderer.update(frame_for_view(frame, view))
    figure.savefig(
        target,
        format="png",
        dpi=dpi,
        metadata={"Software": "OpenMDBench", "Creation Time": None},
    )
    figure.clear()
    return target

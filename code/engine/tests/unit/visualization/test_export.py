"""DISPLAY-free deterministic PNG export."""

from pathlib import Path
from typing import Any

from openmdbench.visualization import export_png
from openmdbench.visualization.schema import (
    DetectionSets,
    ScoreSets,
    SideScore,
    VisualizationFrame,
)


def test_png_export_without_display_is_deterministic(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    frame = VisualizationFrame(
        timestamp=7,
        entities=(),
        detections=DetectionSets(),
        scores=ScoreSets(blue=SideScore(total=0.3), red=SideScore(total=0.4)),
    )
    first = export_png(frame, tmp_path / "first.png", width_pixels=400, height_pixels=300)
    second = export_png(frame, tmp_path / "second.png", width_pixels=400, height_pixels=300)
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().startswith(b"\x89PNG")

"""Safe view switching and authoritative event/score panel state."""

from __future__ import annotations

from dataclasses import dataclass

from openmdbench.core.entities import Side
from openmdbench.visualization.live import VisualizationView
from openmdbench.visualization.renderer import MatplotlibRenderer
from openmdbench.visualization.schema import (
    DetectionSets,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)


def frame_for_view(
    referee_frame: VisualizationFrame, view: VisualizationView
) -> VisualizationFrame:
    """Project an authority frame without exposing hostile ground-truth entities."""
    if view == "referee":
        return referee_frame
    allowed_side = Side.BLUE if view == "blue" else Side.RED if view == "red" else None
    entities = tuple(
        entity
        for entity in referee_frame.entities
        if entity.side is Side.NEUTRAL or entity.side is allowed_side
    )
    detections = DetectionSets(
        blue=referee_frame.detections.blue if view == "blue" else (),
        red=referee_frame.detections.red if view == "red" else (),
    )
    events = tuple(
        event
        for event in referee_frame.events
        if not isinstance(event.data.get("visible_to"), (list, tuple))
        or view in event.data["visible_to"]
    )
    return referee_frame.model_copy(
        update={"entities": entities, "detections": detections, "events": events}
    )


@dataclass(frozen=True, slots=True)
class ScorePoint:
    timestamp: int
    blue: float
    red: float


class VisualizationDashboard:
    def __init__(self, renderer: MatplotlibRenderer, *, view: VisualizationView = "public") -> None:
        self.renderer = renderer
        self.view = view
        self.current_frame: VisualizationFrame | None = None
        self.events: list[tuple[int, VisualizationEvent]] = []
        self.scores: list[ScorePoint] = []

    def set_view(self, view: VisualizationView) -> None:
        self.view = view
        if self.current_frame is not None:
            self.renderer.update(frame_for_view(self.current_frame, view))

    def update(self, authority_frame: VisualizationFrame) -> None:
        self.current_frame = authority_frame
        self.events.extend((authority_frame.timestamp, event) for event in authority_frame.events)
        self.scores.append(
            ScorePoint(
                authority_frame.timestamp,
                authority_frame.scores.blue.total,
                authority_frame.scores.red.total,
            )
        )
        self.renderer.update(frame_for_view(authority_frame, self.view))

    def entity_detail(self, entity_id: str) -> VisualizationEntity | None:
        if self.current_frame is None:
            return None
        visible = frame_for_view(self.current_frame, self.view)
        return next((entity for entity in visible.entities if entity.id == entity_id), None)

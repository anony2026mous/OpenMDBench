"""Immutable schema-v2 frames and bounded live publication."""

from __future__ import annotations

from collections import deque
from threading import RLock

from openmdbench.schemas.core_v2 import ObservationV2, VisualizationFrameV2


class FrameBuilderV2:
    @staticmethod
    def from_observation(
        observation: ObservationV2, *, scenario_id: str, public: bool = False
    ) -> VisualizationFrameV2:
        if not isinstance(observation, ObservationV2):
            raise TypeError("frame builder requires immutable ObservationV2")
        return VisualizationFrameV2(
            schema_version="2.0",
            session_id=observation.session_id,
            scenario_id=scenario_id,
            tick=observation.tick,
            view="public" if public else "faction",
            view_faction_id=None if public else observation.observer_faction_id,
            entities=() if public else observation.own_entities,
            contacts_by_faction={} if public else observation.contacts_by_faction,
        )


class LiveFrameBusV2:
    """Bounded drop-oldest bus; publication never waits for a renderer."""

    def __init__(self, *, capacity: int) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("frame capacity must be a positive integer")
        self.capacity = capacity
        self._frames: deque[VisualizationFrameV2] = deque(maxlen=capacity)
        self._dropped = 0
        self._closed = False
        self._lock = RLock()

    @property
    def dropped_frames(self) -> int:
        with self._lock:
            return self._dropped

    def publish(self, frame: VisualizationFrameV2) -> None:
        if not isinstance(frame, VisualizationFrameV2):
            raise TypeError("live bus accepts VisualizationFrameV2")
        with self._lock:
            if self._closed:
                raise RuntimeError("live frame bus is closed")
            if self._frames and frame.tick <= self._frames[-1].tick:
                raise ValueError("live frame ticks must increase")
            if len(self._frames) == self.capacity:
                self._dropped += 1
            self._frames.append(frame)

    def drain(self) -> tuple[VisualizationFrameV2, ...]:
        with self._lock:
            result = tuple(self._frames)
            self._frames.clear()
            return result

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._frames.clear()


__all__ = ["FrameBuilderV2", "LiveFrameBusV2"]

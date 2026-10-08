"""Bounded non-blocking live frame publication and shared frame sources."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from threading import Condition, RLock

from openmdbench.replay.reader import ReplayReader
from openmdbench.visualization.schema import VisualizationFrame


class LiveFrameBus:
    def __init__(self, capacity: int = 64) -> None:
        if capacity < 1:
            raise ValueError("frame bus capacity must be positive")
        self.capacity = capacity
        self._frames: deque[VisualizationFrame] = deque(maxlen=capacity)
        self._dropped = 0
        self._closed = False
        self._condition = Condition(RLock())

    @property
    def dropped_frames(self) -> int:
        with self._condition:
            return self._dropped

    def publish(self, frame: VisualizationFrame) -> None:
        with self._condition:
            if self._closed:
                return
            if len(self._frames) == self.capacity:
                self._dropped += 1
            self._frames.append(frame)
            self._condition.notify_all()

    def latest(self) -> VisualizationFrame:
        with self._condition:
            if not self._frames:
                raise LookupError("frame bus is empty")
            return self._frames[-1]

    def drain(self) -> tuple[VisualizationFrame, ...]:
        with self._condition:
            frames = tuple(self._frames)
            self._frames.clear()
            return frames

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._frames.clear()
            self._condition.notify_all()


class LiveFrameSource:
    def __init__(self, bus: LiveFrameBus) -> None:
        self._bus = bus

    def current(self) -> VisualizationFrame:
        return self._bus.latest()

    @property
    def dropped_frames(self) -> int:
        return self._bus.dropped_frames


class ReplayFrameSource:
    def __init__(self, reader: ReplayReader) -> None:
        self.reader = reader

    def frames(self) -> Iterator[VisualizationFrame]:
        return self.reader.frames()

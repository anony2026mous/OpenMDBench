"""Deterministic replay timeline and playback controls."""

from __future__ import annotations

import math
from dataclasses import dataclass

from openmdbench.replay.reader import ReplayReader
from openmdbench.visualization.schema import VisualizationFrame


@dataclass(frozen=True, slots=True)
class Timeline:
    start: int
    end: int
    current: int
    index: int
    frame_count: int


class PlaybackController:
    def __init__(self, reader: ReplayReader) -> None:
        self.reader = reader
        self._timestamps = tuple(frame.timestamp for frame in reader.frames())
        if not self._timestamps:
            raise ValueError("replay contains no frames")
        self._index = 0
        self._current = reader.seek(self._timestamps[0])
        self._playing = False
        self._speed = 1.0
        self._fractional_ticks = 0.0

    @property
    def current_frame(self) -> VisualizationFrame:
        return self._current

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def timeline(self) -> Timeline:
        return Timeline(
            start=self._timestamps[0],
            end=self._timestamps[-1],
            current=self._current.timestamp,
            index=self._index,
            frame_count=len(self._timestamps),
        )

    def play(self) -> None:
        if self._index < len(self._timestamps) - 1:
            self._playing = True

    def pause(self) -> None:
        self._playing = False

    def set_speed(self, multiplier: float) -> None:
        if not math.isfinite(multiplier) or multiplier <= 0.0:
            raise ValueError("playback speed must be finite and positive")
        self._speed = multiplier

    def _move_to_index(self, index: int) -> VisualizationFrame:
        self._index = max(0, min(index, len(self._timestamps) - 1))
        self._current = self.reader.seek(self._timestamps[self._index])
        if self._index == len(self._timestamps) - 1:
            self._playing = False
        return self._current

    def step_forward(self, count: int = 1) -> VisualizationFrame:
        if count < 0:
            raise ValueError("step count cannot be negative")
        return self._move_to_index(self._index + count)

    def step_backward(self, count: int = 1) -> VisualizationFrame:
        if count < 0:
            raise ValueError("step count cannot be negative")
        return self._move_to_index(self._index - count)

    def seek(self, timestamp: int) -> VisualizationFrame:
        try:
            index = self._timestamps.index(timestamp)
        except ValueError as error:
            raise KeyError(f"timestamp not found: {timestamp}") from error
        self._fractional_ticks = 0.0
        return self._move_to_index(index)

    def jump_to_start(self) -> VisualizationFrame:
        self._fractional_ticks = 0.0
        return self._move_to_index(0)

    def jump_to_end(self) -> VisualizationFrame:
        self._fractional_ticks = 0.0
        return self._move_to_index(len(self._timestamps) - 1)

    def advance(self, wall_seconds: float) -> VisualizationFrame:
        """Advance according to playback speed without altering recorded timestamps."""
        if not math.isfinite(wall_seconds) or wall_seconds < 0.0:
            raise ValueError("wall_seconds must be finite and non-negative")
        if not self._playing:
            return self._current
        self._fractional_ticks += wall_seconds * self._speed / self.reader.metadata.tick_seconds
        steps = int(self._fractional_ticks)
        self._fractional_ticks -= steps
        if steps:
            return self.step_forward(steps)
        return self._current

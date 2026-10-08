"""Kernel-free read-only replay cursor."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar


class ReplayFrame(Protocol):
    tick: int


FrameT = TypeVar("FrameT", bound=ReplayFrame)


class ReplayRunner(Generic[FrameT]):
    """Read recorded frames without importing or initializing simulation code."""

    def __init__(self, frames: Sequence[FrameT], *, physics_dt_s: float) -> None:
        if not frames:
            raise ValueError("replay requires at least one frame")
        if physics_dt_s <= 0.0 or not math.isfinite(physics_dt_s):
            raise ValueError("physics_dt_s must be finite and positive")
        ticks = tuple(frame.tick for frame in frames)
        if ticks != tuple(sorted(ticks)) or len(ticks) != len(set(ticks)):
            raise ValueError("replay frame ticks must be strictly increasing")
        self._frames = tuple(frames)
        self._index = 0
        self.physics_dt_s = physics_dt_s
        self.speed_ratio = 1.0

    @property
    def sim_time_s(self) -> float:
        return self.current().tick * self.physics_dt_s

    def current(self) -> FrameT:
        return self._frames[self._index]

    def step(self) -> FrameT:
        if self._index < len(self._frames) - 1:
            self._index += 1
        return self.current()

    def set_speed(self, speed_ratio: float) -> None:
        if speed_ratio <= 0.0 or math.isnan(speed_ratio):
            raise ValueError("speed_ratio must be positive")
        self.speed_ratio = speed_ratio

    def terminate(self) -> None:
        self._index = len(self._frames) - 1

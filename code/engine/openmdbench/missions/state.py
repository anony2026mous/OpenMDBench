"""Irreversible mission lifecycle with stable scheduled event delivery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MissionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"


TERMINAL_STATUSES = {
    MissionStatus.SUCCESS,
    MissionStatus.FAILED,
    MissionStatus.TIMEOUT,
    MissionStatus.TERMINATED,
}


@dataclass(frozen=True, order=True, slots=True)
class MissionEvent:
    tick: int
    priority: int
    sequence: int
    event_type: str
    payload: dict[str, str | int | float | bool]


class Mission:
    def __init__(self, time_limit_ticks: int, events: tuple[MissionEvent, ...] = ()) -> None:
        if time_limit_ticks <= 0:
            raise ValueError("mission time limit must be positive")
        if any(event.tick < 0 for event in events):
            raise ValueError("mission event tick cannot be negative")
        self.time_limit_ticks = time_limit_ticks
        self.status = MissionStatus.CREATED
        self.tick = 0
        self._events = tuple(sorted(events))
        self._next_event = 0

    def start(self) -> None:
        if self.status is not MissionStatus.CREATED:
            raise RuntimeError("mission can only start from created state")
        self.status = MissionStatus.RUNNING

    def advance(
        self,
        *,
        success: bool = False,
        failed: bool = False,
        terminated: bool = False,
    ) -> tuple[MissionEvent, ...]:
        if self.status is not MissionStatus.RUNNING:
            raise RuntimeError("terminal or unstarted mission cannot advance")
        if sum((success, failed, terminated)) > 1:
            raise ValueError("mission terminal signals are mutually exclusive")
        self.tick += 1
        due: list[MissionEvent] = []
        while self._next_event < len(self._events):
            event = self._events[self._next_event]
            if event.tick > self.tick:
                break
            due.append(event)
            self._next_event += 1
        if success:
            self.status = MissionStatus.SUCCESS
        elif failed:
            self.status = MissionStatus.FAILED
        elif terminated:
            self.status = MissionStatus.TERMINATED
        elif self.tick >= self.time_limit_ticks:
            self.status = MissionStatus.TIMEOUT
        return tuple(due)

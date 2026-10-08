"""Fixed simulation clock, stable delayed events, and ordered systems."""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SimulationClock:
    tick_seconds: float = 1.0
    tick: int = 0
    paused: bool = False

    def __post_init__(self) -> None:
        if self.tick_seconds <= 0.0 or self.tick < 0:
            raise ValueError("tick duration must be positive and tick cannot be negative")

    def advance(self) -> int:
        if self.paused:
            raise RuntimeError("cannot advance a paused simulation clock")
        self.tick += 1
        return self.tick

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False


@dataclass(order=True, frozen=True, slots=True)
class ScheduledEvent:
    tick: int
    priority: int
    sequence: int
    event_type: str = field(compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)


class EventQueue:
    def __init__(self) -> None:
        self._events: list[ScheduledEvent] = []
        self._next_sequence = 0

    def schedule(
        self,
        tick: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int = 0,
    ) -> ScheduledEvent:
        if tick < 0:
            raise ValueError("event tick cannot be negative")
        event = ScheduledEvent(
            tick=tick,
            priority=priority,
            sequence=self._next_sequence,
            event_type=event_type,
            payload=payload or {},
        )
        self._next_sequence += 1
        heapq.heappush(self._events, event)
        return event

    def pop_due(self, tick: int) -> tuple[ScheduledEvent, ...]:
        due: list[ScheduledEvent] = []
        while self._events and self._events[0].tick <= tick:
            due.append(heapq.heappop(self._events))
        return tuple(due)

    def snapshot(self) -> dict[str, Any]:
        return {
            "events": [
                {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "priority": event.priority,
                    "sequence": event.sequence,
                    "tick": event.tick,
                }
                for event in sorted(self._events)
            ],
            "next_sequence": self._next_sequence,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> EventQueue:
        queue = cls()
        for record in snapshot.get("events", []):
            event = ScheduledEvent(**record)
            heapq.heappush(queue._events, event)
        queue._next_sequence = int(snapshot.get("next_sequence", len(queue._events)))
        return queue


System = Callable[[int], None]


class SystemScheduler:
    def __init__(self) -> None:
        self._systems: list[tuple[int, int, str, System]] = []
        self._next_sequence = 0

    def register(self, name: str, system: System, *, priority: int = 0) -> None:
        if any(registered_name == name for _, _, registered_name, _ in self._systems):
            raise ValueError(f"system name is already registered: {name}")
        self._systems.append((priority, self._next_sequence, name, system))
        self._next_sequence += 1
        self._systems.sort(key=lambda registered: (registered[0], registered[1]))

    def run(self, tick: int) -> None:
        for _, _, _, system in self._systems:
            system(tick)

"""Deterministic clock, event, and system-order tests."""

import pytest
from openmdbench.core.scheduling import EventQueue, SimulationClock, SystemScheduler


def test_pause_resume_does_not_change_logical_time() -> None:
    clock = SimulationClock()
    assert clock.advance() == 1
    clock.pause()
    with pytest.raises(RuntimeError, match="paused"):
        clock.advance()
    assert clock.tick == 1
    clock.resume()
    assert clock.advance() == 2


def test_equal_priority_events_keep_insertion_order() -> None:
    queue = EventQueue()
    queue.schedule(3, "first", priority=2)
    queue.schedule(3, "second", priority=2)
    queue.schedule(3, "urgent", priority=1)
    assert [event.event_type for event in queue.pop_due(3)] == ["urgent", "first", "second"]


def test_system_execution_order_is_stable() -> None:
    calls: list[tuple[str, int]] = []
    scheduler = SystemScheduler()
    scheduler.register("physics", lambda tick: calls.append(("physics", tick)), priority=20)
    scheduler.register("commands", lambda tick: calls.append(("commands", tick)), priority=10)
    scheduler.register("events", lambda tick: calls.append(("events", tick)), priority=10)
    scheduler.run(7)
    assert calls == [("commands", 7), ("events", 7), ("physics", 7)]

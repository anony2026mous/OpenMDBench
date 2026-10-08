"""Mission transition, terminal, timeout, and event-order tests."""

import pytest
from openmdbench.missions import Mission, MissionEvent, MissionStatus


def test_created_running_success_is_irreversible() -> None:
    mission = Mission(10)
    mission.start()
    mission.advance(success=True)
    assert mission.status is MissionStatus.SUCCESS
    with pytest.raises(RuntimeError, match="cannot advance"):
        mission.advance()


def test_timeout_is_separate_terminal_state() -> None:
    mission = Mission(2)
    mission.start()
    mission.advance()
    mission.advance()
    assert mission.status is MissionStatus.TIMEOUT


def test_waves_and_emergency_events_have_stable_order() -> None:
    events = (
        MissionEvent(2, 20, 1, "second", {}),
        MissionEvent(2, 10, 2, "urgent", {}),
        MissionEvent(2, 20, 0, "first", {}),
    )
    mission = Mission(10, events)
    mission.start()
    assert mission.advance() == ()
    assert [event.event_type for event in mission.advance()] == ["urgent", "first", "second"]


def test_conflicting_terminal_signals_are_rejected_atomically() -> None:
    mission = Mission(10)
    mission.start()
    with pytest.raises(ValueError, match="mutually exclusive"):
        mission.advance(success=True, failed=True)
    assert mission.tick == 0
    assert mission.status is MissionStatus.RUNNING

"""Deterministic legal smoke and terminal baseline scripts."""

from __future__ import annotations

from openmdbench.core.entities import Side
from openmdbench.missions.state import Mission, MissionStatus
from openmdbench.scenarios.schema import Scenario


def legal_hold_actions(scenario: Scenario) -> tuple[dict[str, object], ...]:
    """Return one legal non-leaking hold action per explicitly deployed blue asset."""
    return tuple(
        {
            "action_type": "hold_position",
            "asset_id": entity.id,
            "parameters": {"duration": 1},
        }
        for entity in sorted(scenario.entities, key=lambda item: item.id)
        if entity.side is Side.BLUE
    )


def run_terminal_baseline(scenario: Scenario, *, succeed: bool) -> MissionStatus:
    """Exercise a deterministic representative success or failure mission path."""
    mission = Mission(scenario.time_limit_ticks)
    mission.start()
    actions = legal_hold_actions(scenario)
    if not actions:
        raise ValueError("baseline requires at least one deployed blue asset")
    mission.advance(success=succeed, failed=not succeed)
    return mission.status

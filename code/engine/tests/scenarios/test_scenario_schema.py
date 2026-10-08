"""Scenario validation and public/referee isolation tests."""

from copy import deepcopy

import pytest
from openmdbench.scenarios import Scenario, render_briefing
from pydantic import ValidationError


def _scenario() -> dict[str, object]:
    return {
        "scenario_id": "MD-REC-001",
        "category": "reconnaissance",
        "difficulty": "easy",
        "world": {"bounds": [0, 0, 2000, 2000]},
        "public": {
            "name": "Port patrol",
            "background": "Protect the public port approach.",
            "primary_objectives": ["Patrol entrance"],
            "weather_forecast": "Clear",
        },
        "entities": [
            {"id": "blue-usv", "side": "blue", "type": "usv", "position": [100, 100, 0]},
            {"id": "red-uav", "side": "red", "type": "uav", "position": [1000, 1000, 500]},
        ],
        "spawn_counts": {
            "blue": {"usv": 1},
            "red": {"uav": 1},
        },
        "time_limit_ticks": 1200,
        "roe": ["identified_contacts_only"],
        "initial_weather": "clear",
        "success_conditions": ["patrol_complete"],
        "failure_conditions": ["timeout"],
        "scoring": {
            "weights": {"completion": 1.0},
            "baseline_version": "1.0",
            "baseline": {"time_ticks": 1000},
        },
        "referee": {
            "opponent_intent": "secret ambush",
            "hidden_events": [{"tick": 100, "event_type": "secret attack"}],
        },
    }


def test_invalid_platform_coordinates_and_duplicate_ids_are_rejected() -> None:
    invalid = _scenario()
    invalid["entities"] = [
        {"id": "same", "side": "blue", "type": "usv", "position": [100, 100, 0]},
        {"id": "same", "side": "red", "type": "uav", "position": [3000, 100, 100]},
    ]
    with pytest.raises(ValidationError):
        Scenario.model_validate(invalid)

    illegal_type = deepcopy(_scenario())
    illegal_type["entities"][0]["type"] = "submarine"  # type: ignore[index]
    with pytest.raises(ValidationError):
        Scenario.model_validate(illegal_type)


def test_briefing_cannot_leak_referee_fields() -> None:
    briefing = render_briefing(Scenario.model_validate(_scenario()))
    assert "Port patrol" in briefing
    assert "secret ambush" not in briefing
    assert "secret attack" not in briefing

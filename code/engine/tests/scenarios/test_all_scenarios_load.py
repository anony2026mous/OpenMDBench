"""Static validation and smoke tests for all 35 normative scenarios."""

from collections import Counter
from pathlib import Path

from openmdbench.core.entities import Side
from openmdbench.missions import Mission, MissionStatus
from openmdbench.scenarios import load_scenario, render_briefing

SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "openmdbench" / "scenarios"


def test_all_35_unique_scenarios_validate_and_have_public_briefings() -> None:
    paths = sorted(SCENARIO_ROOT.glob("*/*.yaml"))
    scenarios = [load_scenario(path) for path in paths]
    assert len(scenarios) == 35
    assert len({scenario.scenario_id for scenario in scenarios}) == 35
    assert Counter(scenario.category for scenario in scenarios) == {
        "reconnaissance": 8,
        "tracking": 8,
        "interception": 7,
        "area_denial": 6,
        "emergency": 6,
    }
    for scenario in scenarios:
        briefing = render_briefing(scenario)
        assert scenario.public.name in briefing
        assert scenario.referee.opponent_intent not in briefing
        assert scenario.scoring.baseline_version == "1.0"


def test_normative_force_time_weather_and_event_examples() -> None:
    rec = load_scenario(SCENARIO_ROOT / "reconnaissance" / "MD-REC-001.yaml")
    assert rec.time_limit_ticks == 1200
    assert rec.initial_weather == "clear"
    assert rec.spawn_counts[Side.BLUE].uav == 2
    assert rec.spawn_counts[Side.BLUE].usv == 2
    assert rec.spawn_counts[Side.BLUE].shore_radar == 1

    denial = load_scenario(SCENARIO_ROOT / "area_denial" / "MD-AD-006.yaml")
    assert denial.time_limit_ticks == 10800
    assert denial.spawn_counts[Side.BLUE].auv == 2

    emergency = load_scenario(SCENARIO_ROOT / "emergency" / "MD-ER-004.yaml")
    assert emergency.referee.hidden_events[0].tick == 720


def test_every_scenario_can_start_and_advance_smoke() -> None:
    for path in sorted(SCENARIO_ROOT.glob("*/*.yaml")):
        scenario = load_scenario(path)
        mission = Mission(scenario.time_limit_ticks)
        mission.start()
        mission.advance()
        assert mission.status is MissionStatus.RUNNING

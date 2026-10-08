"""Five-category terminal baselines and all-scenario legal policy smoke."""

from pathlib import Path

from openmdbench.missions import MissionStatus
from openmdbench.missions.baselines import legal_hold_actions, run_terminal_baseline
from openmdbench.scenarios import load_scenario

SCENARIO_ROOT = Path(__file__).resolve().parents[2] / "openmdbench" / "scenarios"
REPRESENTATIVES = (
    "reconnaissance/MD-REC-001.yaml",
    "tracking/MD-TRK-001.yaml",
    "area_denial/MD-AD-001.yaml",
    "emergency/MD-ER-001.yaml",
)


def test_each_category_has_repeatable_success_and_failure_path() -> None:
    for relative_path in REPRESENTATIVES:
        scenario = load_scenario(SCENARIO_ROOT / relative_path)
        assert run_terminal_baseline(scenario, succeed=True) is MissionStatus.SUCCESS
        assert run_terminal_baseline(scenario, succeed=False) is MissionStatus.FAILED


def test_every_scenario_has_a_legal_non_leaking_smoke_policy() -> None:
    for path in sorted(SCENARIO_ROOT.glob("*/*.yaml")):
        scenario = load_scenario(path)
        actions = legal_hold_actions(scenario)
        assert actions
        assert all(action["action_type"] == "hold_position" for action in actions)
        serialized = repr(actions)
        assert scenario.referee.opponent_intent not in serialized

"""AD2-10 HARD public runner and view-filter closure."""

from pathlib import Path

from openmdbench.core.entities import PlatformAsset
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.replay.md_ad_002 import AD2AuthorityLog
from openmdbench.runners.md_ad_002 import run_md_ad_002_hard
from openmdbench.scoring.md_ad_002 import score_authority_records


def test_hard_runner_uses_formal_scenario_and_reaches_timeout_path() -> None:
    result = run_md_ad_002_hard(seed=401, max_ticks=3, adjudication_time_limit_ticks=2)
    assert result.ticks == 2
    assert result.outcome == "red_success"
    assert result.reason == "timeout_denial_success"


def test_hard_fixed_seed_success_path_and_offline_score(tmp_path: Path) -> None:
    log_path = tmp_path / "hard.jsonl.gz"
    result = run_md_ad_002_hard(seed=0, max_ticks=1_800, log_path=log_path)
    assert result.outcome == "red_success"
    assert result.reason == "all_threats_destroyed"
    assert result.breaches == 0
    assert result.score.metrics["interception_rate"] == 1.0
    assert result.score.metrics["relay_effectiveness"] == 1.0
    records = AD2AuthorityLog.read(log_path)
    assert score_authority_records(records) == result.score
    assert any(
        event["event_type"] == "weather_changed"
        for record in records
        if record["record_type"] == "tick"
        for event in record["payload"]["scenario_events"]
    )


def test_hard_fixed_seed_failure_path_without_engagement() -> None:
    result = run_md_ad_002_hard(seed=0, max_ticks=1_800, disable_red_engage=True)
    assert result.outcome == "blue_success"
    assert result.reason == "breach_threshold_reached"
    assert result.breaches == 3


def test_red_suppression_event_does_not_leak_blue_truth_id() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=402)
    env.reset(seed=402)
    assert env.world is not None
    usv = env.world.registry.get("red-picket-usv-1")
    blue = env.world.registry.get("blue-striker-uav-01")
    assert isinstance(usv, PlatformAsset) and isinstance(blue, PlatformAsset)
    env.world.registry.update(blue.model_copy(update={"position": usv.position}))
    env._apply_ad2_difficulty_events(1)
    env.world.tick = 1
    event = next(
        item
        for item in env.red_observation().visible_events
        if item["event_type"] == "suppression_started"
    )
    assert "source_id" not in event
    assert not any(value == blue.id for value in event.values())

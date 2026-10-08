"""AD2-08 MEDIUM runner smoke and deterministic failure/timeout paths."""

import json
from pathlib import Path

from openmdbench.replay.md_ad_002 import AD2AuthorityLog
from openmdbench.runners.md_ad_002 import run_md_ad_002_medium
from openmdbench.scenarios.md_ad_002_config import load_md_ad_002_config
from openmdbench.scoring.md_ad_002 import score_authority_records


def test_medium_short_prefix_is_deterministic_and_independent() -> None:
    first = run_md_ad_002_medium(seed=91, max_ticks=35)
    second = run_md_ad_002_medium(seed=91, max_ticks=35)
    assert first == second
    assert first.ticks == 35


def test_medium_explicit_timeout_path() -> None:
    result = run_md_ad_002_medium(
        seed=92, max_ticks=10, blue_hold=True, adjudication_time_limit_ticks=5
    )
    assert result.outcome == "red_success"
    assert result.reason == "timeout_denial_success"
    assert result.ticks == 5


def test_medium_checkpoint_contains_both_policy_states(tmp_path: Path) -> None:
    run_md_ad_002_medium(seed=93, max_ticks=2, checkpoint_dir=tmp_path, checkpoint_every=1)
    checkpoint = json.loads((tmp_path / "tick-0002.json").read_text(encoding="utf-8"))
    assert "red_agent" in checkpoint
    assert checkpoint["blue_agent"]["rng"]["seed"] == 93


def test_medium_seed_zero_matches_independent_golden() -> None:
    golden_path = Path(__file__).parents[1] / "fixtures/md_ad_002/medium-v2-golden.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert load_md_ad_002_config("MD-AD-002-MEDIUM").sha256 == golden["config_hash"]
    result = run_md_ad_002_medium(seed=0, max_ticks=1_800)
    assert {
        "seed": result.seed,
        "ticks": result.ticks,
        "outcome": result.outcome,
        "reason": result.reason,
        "breaches": result.breaches,
        "metrics": result.score.metrics,
        "total_score": result.score.total_score,
    } == {key: value for key, value in golden.items() if key != "config_hash"}


def test_medium_disabled_engagement_is_blue_success() -> None:
    result = run_md_ad_002_medium(seed=0, max_ticks=1_800, disable_red_engage=True)
    assert result.outcome == "blue_success"
    assert result.reason == "breach_threshold_reached"
    assert result.breaches == 3
    assert result.ticks == 792


def test_medium_online_score_equals_offline_log(tmp_path: Path) -> None:
    path = tmp_path / "medium.jsonl.gz"
    result = run_md_ad_002_medium(seed=94, max_ticks=35, log_path=path)
    records = AD2AuthorityLog.read(path)
    assert records[0]["payload"]["scenario_id"] == "MD-AD-002-MEDIUM"
    assert score_authority_records(records) == result.score

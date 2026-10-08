import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, TextIO, cast

import pytest
from openmdbench.envs.md_ad_002 import MDAD002GymEnv
from openmdbench.policies import AD2RedBaselineAgent
from openmdbench.replay.md_ad_002 import AD2AuthorityLog
from openmdbench.runners.md_ad_002 import run_md_ad_002_easy
from openmdbench.scoring.md_ad_002 import score_authority_records


class _FlushCountingStream:
    """Minimal delegating stream used to verify authority-log flush cadence."""

    def __init__(self, delegate: TextIO) -> None:
        self._delegate = delegate
        self.flush_count = 0

    @property
    def closed(self) -> bool:
        return self._delegate.closed

    def write(self, value: str) -> int:
        return self._delegate.write(value)

    def flush(self) -> None:
        self.flush_count += 1
        self._delegate.flush()

    def close(self) -> None:
        self._delegate.close()


def _isolated_match(arguments: str, tmp_path: Path) -> dict[str, Any]:
    code = (
        "import json; from openmdbench.runners.md_ad_002 import run_md_ad_002_easy; "
        f"r=run_md_ad_002_easy({arguments}); "
        "print(json.dumps({'outcome':r.outcome,'reason':r.reason,'breaches':r.breaches,"
        "'interception':r.score.metrics['interception_rate']}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "MPLCONFIGDIR": str(tmp_path / "mpl")},
        check=True,
        capture_output=True,
        text=True,
    )
    return cast(dict[str, Any], json.loads(completed.stdout.splitlines()[-1]))


def test_easy_runner_is_deterministic_for_short_prefix() -> None:
    first = run_md_ad_002_easy(seed=17, max_ticks=3)
    second = run_md_ad_002_easy(seed=17, max_ticks=3)
    assert first == second
    assert first.ticks == 3
    assert first.score.availability["relay_effectiveness"] is False


def test_easy_explicit_timeout_path_is_red_success() -> None:
    result = run_md_ad_002_easy(
        seed=17, max_ticks=10, blue_hold=True, adjudication_time_limit_ticks=5
    )
    assert result.ticks == 5
    assert result.outcome == "red_success"
    assert result.reason == "timeout_denial_success"


def test_easy_seed_zero_is_normal_red_success(tmp_path: Path) -> None:
    result = _isolated_match("seed=0,max_ticks=1800", tmp_path)
    assert result["outcome"] == "red_success"
    assert result["reason"] == "all_threats_destroyed"
    assert result["breaches"] < 3
    assert result["interception"] == 1.0


def test_easy_disabled_engagement_is_blue_success(tmp_path: Path) -> None:
    result = _isolated_match("seed=0,max_ticks=1200,disable_red_engage=True", tmp_path)
    assert result["outcome"] == "blue_success"
    assert result["reason"] == "breach_threshold_reached"
    assert result["breaches"] == 3


def test_easy_gzip_authority_log_is_self_contained(tmp_path: Path) -> None:
    path = tmp_path / "easy.jsonl.gz"
    run_md_ad_002_easy(seed=9, max_ticks=2, log_path=path)
    records = AD2AuthorityLog.read(path)
    assert records[0]["record_type"] == "metadata"
    assert records[0]["payload"]["scenario_id"] == "MD-AD-002-EASY"
    assert [record["payload"]["timestamp"] for record in records[1:]] == [1, 2]
    assert "world" in records[1]["payload"]
    assert "red_observation" in records[1]["payload"]
    red_encoded = str(AD2AuthorityLog.read_view(path, "red"))
    assert "blue-striker-uav-01" not in red_encoded
    assert "world" not in AD2AuthorityLog.read_view(path, "public")[1]["payload"]


def test_authority_world_snapshot_matches_checkpoint_world_payload() -> None:
    env = MDAD002GymEnv(seed=19)
    env.reset(seed=19)

    assert env.core.authority_world_snapshot() == env.core.export_state()["world"]


def test_authority_log_batches_compression_flushes_but_close_completes_it(
    tmp_path: Path,
) -> None:
    path = tmp_path / "batched.jsonl.gz"
    log = AD2AuthorityLog(path, {"scenario_id": "test"}, flush_every=3)
    stream = _FlushCountingStream(log._stream)
    log._stream = cast(TextIO, stream)

    log.append("tick", {"timestamp": 1})
    assert stream.flush_count == 0
    log.append("tick", {"timestamp": 2})
    assert stream.flush_count == 1
    log.append("tick", {"timestamp": 3})
    log.close()

    assert stream.flush_count == 2
    assert [record["record_type"] for record in AD2AuthorityLog.read(path)] == [
        "metadata",
        "tick",
        "tick",
        "tick",
    ]
    with pytest.raises(ValueError, match="flush_every"):
        AD2AuthorityLog(tmp_path / "invalid.jsonl.gz", {"scenario_id": "test"}, flush_every=0)


def test_easy_online_score_equals_offline_authority_log_recalculation(tmp_path: Path) -> None:
    path = tmp_path / "score.jsonl.gz"
    result = run_md_ad_002_easy(seed=9, max_ticks=20, log_path=path)
    records = AD2AuthorityLog.read(path)
    assert score_authority_records(records) == result.score
    state = records[-1]["payload"]["metric_state"]
    assert state["early_warning_baseline_version"] == "shore-low-altitude-envelope-v1"
    assert "metric_state" not in AD2AuthorityLog.read_view(path, "red")[-1]["payload"]


def test_easy_runner_archives_periodic_checkpoints(tmp_path: Path) -> None:
    run_md_ad_002_easy(seed=4, max_ticks=2, checkpoint_dir=tmp_path, checkpoint_every=1)
    checkpoint = json.loads((tmp_path / "tick-0002.json").read_text(encoding="utf-8"))
    assert checkpoint["simulation"]["world"]["tick"] == 2
    assert "last_fired" in checkpoint["red_agent"]


def test_easy_runner_checkpoint_restores_metric_accumulators(tmp_path: Path) -> None:
    continuous = run_md_ad_002_easy(seed=41, max_ticks=4)
    run_md_ad_002_easy(
        seed=41,
        max_ticks=2,
        checkpoint_dir=tmp_path,
        checkpoint_every=2,
    )
    checkpoint_path = tmp_path / "tick-0002.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["runner"]["metric_state"]["scenario_id"] == "MD-AD-002-EASY"

    resumed = run_md_ad_002_easy(seed=41, max_ticks=4, resume_checkpoint=checkpoint_path)
    assert resumed == continuous

    with pytest.raises(ValueError, match="identity or options mismatch"):
        run_md_ad_002_easy(seed=42, max_ticks=4, resume_checkpoint=checkpoint_path)


def test_same_red_policy_core_completes_gym_match() -> None:
    env = MDAD002GymEnv(seed=17)
    env.reset(seed=17)
    assert env.core._ad2_adjudicator is not None
    env.core._ad2_adjudicator.time_limit_ticks = 5
    protected = (
        float(env.core._protected_point[0]),
        float(env.core._protected_point[1]),
    )
    agent = AD2RedBaselineAgent(protected)
    terminated = False
    for _ in range(5):
        batch = agent.act(env.core.red_observation())
        _observation, _reward, terminated, _truncated, _info = env.step(
            env.encode_action_batch(batch)
        )
    assert terminated
    assert env.core._ad2_adjudicator.result.reason == "timeout_denial_success"

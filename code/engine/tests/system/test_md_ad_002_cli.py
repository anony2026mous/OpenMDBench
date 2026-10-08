import json
import os
import subprocess
import sys
from pathlib import Path


def test_easy_selftest_cli_writes_gzip_log(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "openmdbench.cli",
            "selftest",
            "--scenario",
            "MD-AD-002-EASY",
            "--seed",
            "17",
            "--ticks",
            "3",
        ],
        cwd=tmp_path,
        env={**os.environ, "MPLCONFIGDIR": str(tmp_path / "mpl")},
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert result["passed"] is False
    assert result["scenario_id"] == "MD-AD-002-EASY"
    assert (tmp_path / result["artifacts"]["authority_log"]).is_file()


def test_medium_selftest_cli_uses_independent_artifact(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "openmdbench.cli",
            "selftest",
            "--scenario",
            "MD-AD-002-MEDIUM",
            "--seed",
            "17",
            "--ticks",
            "3",
        ],
        cwd=tmp_path,
        env={**os.environ, "MPLCONFIGDIR": str(tmp_path / "mpl")},
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert result["scenario_id"] == "MD-AD-002-MEDIUM"
    assert result["artifacts"]["authority_log"].endswith("medium-selftest.jsonl.gz")
    assert (tmp_path / result["artifacts"]["authority_log"]).is_file()


def test_hard_selftest_cli_uses_independent_artifact(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "openmdbench.cli",
            "selftest",
            "--scenario",
            "MD-AD-002-HARD",
            "--seed",
            "17",
            "--ticks",
            "3",
        ],
        cwd=tmp_path,
        env={**os.environ, "MPLCONFIGDIR": str(tmp_path / "mpl")},
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert result["scenario_id"] == "MD-AD-002-HARD"
    assert result["artifacts"]["authority_log"].endswith("hard-selftest.jsonl.gz")
    assert (tmp_path / result["artifacts"]["authority_log"]).is_file()

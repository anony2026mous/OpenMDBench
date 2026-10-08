"""Action replay equivalence and first-drift diagnostics."""

import json
from pathlib import Path

from openmdbench.api.sessions import SessionStore
from openmdbench.replay import ReplayReader, verify_action_replay


def _match(tmp_path: Path) -> Path:
    store = SessionStore(replay_dir=tmp_path)
    session = store.create("MD-REC-001", 13)
    store.step(session, (1.0, 20.0))
    store.step(session, (2.0, 80.0))
    store.step(session, (3.0, 140.0))
    store.delete(session.session_id)
    return tmp_path / f"{session.session_id}.replay.jsonl"


def test_authority_log_action_replay_matches(tmp_path: Path) -> None:
    report = verify_action_replay(ReplayReader(_match(tmp_path)))
    assert report.matched
    assert report.first_drift_tick is None


def test_modified_action_and_configuration_locate_first_drift(tmp_path: Path) -> None:
    path = _match(tmp_path)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records[2]["actions"][0]["heading"] = 180.0
    modified = tmp_path / "modified.jsonl"
    modified.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    report = verify_action_replay(ReplayReader(modified))
    assert not report.matched
    assert report.first_drift_tick == 1
    assert report.field == "position"

    records[0]["config_hash"] = "sha256:deadbeef"
    changed_config = tmp_path / "changed-config.jsonl"
    changed_config.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    config_report = verify_action_replay(ReplayReader(changed_config))
    assert config_report.first_drift_tick == 0
    assert config_report.field == "config_hash"

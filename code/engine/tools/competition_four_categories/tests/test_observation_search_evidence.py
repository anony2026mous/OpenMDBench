"""Unit checks for source binding and streamed-trajectory completeness."""
from copy import deepcopy
import hashlib
import json

import pytest

from tools.competition_four_categories import audit
from tools.competition_four_categories.observation_search_policy import SETTINGS


def fixture(tmp_path, monkeypatch, failure=None):
    folder = tmp_path/"artifacts"; folder.mkdir()
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    monkeypatch.setattr(audit, "RESULTS", folder)
    sources = audit.recon_extension_sources("observation-adaptive")
    terminal = {"outcome": "objective_complete"}
    own = {"owner": [{"entity_id": "owner", "position_m": [1., 2., 3.]}]}
    trace = [{"tick": 1, "own_states": own, "receiver_inboxes": {"owner": []}, "terminal": terminal}]
    actions = [{"kind": "search_navigation", "tick": 0}]
    record = {"policy": "observation-adaptive", **sources, "controller_settings": deepcopy(SETTINGS),
        "observation_stream": "artifacts/stream.jsonl", "seed": 601, "scenario_id": "MD-REC-006",
        "final_tick": 1, "trace": trace, "terminal": terminal, "submitted_actions": actions, "failure": failure}
    rows = [{"type": "initial", "tick": 0, "source_fingerprints": sources, "seed": 601,
             "scenario_id": record["scenario_id"], "mode": "adaptive", "controller_settings": deepcopy(SETTINGS)},
            {"type": "frame", **deepcopy(trace[0]),
             "observations": {"owner": {"own_entities": deepcopy(own["owner"]), "received_messages": []}},
             "submitted_actions": deepcopy(actions)},
            {"type": "final", "tick": 1, "terminal": terminal, "failure": failure}]
    path = folder/"stream.jsonl"
    write(record, rows, path)
    return record, rows, path


def write(record, rows, path):
    path.write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")
    record["observation_stream_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("failure", [None, {"status": "FAILED_CHECKPOINT_GATE", "error": "native rejection"}])
def test_stream_is_verifiable_without_relabeling_a_failed_native_gate(tmp_path, monkeypatch, failure):
    record, _, _ = fixture(tmp_path, monkeypatch, failure)
    assert audit.recon_policy_extension_matches(record)
    assert record["failure"] == failure


@pytest.mark.parametrize("field", ["policy_source_sha256", "base_policy_sha256", "checkpoint_adapter_sha256", "runtime_source_sha256"])
def test_changed_or_unrecorded_execution_source_cannot_be_current(tmp_path, monkeypatch, field):
    record, _, _ = fixture(tmp_path, monkeypatch)
    record.pop(field)
    assert not audit.recon_policy_extension_matches(record)


def test_unknown_mode_changed_settings_and_external_path_are_rejected(tmp_path, monkeypatch):
    record, _, _ = fixture(tmp_path, monkeypatch)
    changed = deepcopy(record); changed["policy"] = "observation-unknown"
    assert not audit.recon_policy_extension_matches(changed)
    changed = deepcopy(record); changed["controller_settings"]["surface_speed_mps"] = 6.
    assert not audit.recon_policy_extension_matches(changed)
    changed = deepcopy(record); changed["observation_stream"] = "outside.jsonl"
    assert not audit.recon_policy_extension_matches(changed)


def test_stream_digest_detects_edits(tmp_path, monkeypatch):
    record, _, path = fixture(tmp_path, monkeypatch)
    path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        audit.recon_policy_extension_matches(record)


@pytest.mark.parametrize("change,reason", [
    ("truncate", "truncated"), ("frame", "frame differs"), ("seed", "provenance"),
    ("observation", "DTO differs"), ("actions", "actions differ"), ("append", "final status"),
])
def test_even_rehashed_stream_must_match_trial_contents(tmp_path, monkeypatch, change, reason):
    record, rows, path = fixture(tmp_path, monkeypatch)
    if change == "truncate": rows.pop()
    elif change == "frame": rows[1]["tick"] = 2
    elif change == "seed": rows[0]["seed"] = 999
    elif change == "observation": rows[1]["observations"]["owner"]["own_entities"][0]["position_m"][0] = 9000.
    elif change == "actions": rows[1]["submitted_actions"] = []
    else: rows.append({"type": "frame", "tick": 2})
    write(record, rows, path)
    with pytest.raises(ValueError, match=reason):
        audit.recon_policy_extension_matches(record)

from copy import deepcopy
import json

import pytest

from openmdbench.missions.engine_v2 import _canonical_hash
from tools.competition_four_categories.denial_metrics_v1 import DenialMetricV1
from tools.competition_four_categories.denial_state_audit import DenialStateAudit, raw_statistics
from tools.competition_four_categories import denial_state_audit
from tools.competition_four_categories.tests.test_denial_metrics import plugin, value, edge


def test_raw_counts_are_not_confused_with_the_binary_compliance_score():
    model = plugin("breach_free")
    value(model, 1)
    value(model, 2, {}, [edge(2), edge(2, transition="exited")])
    raw = raw_statistics(model.snapshot(), 1.)
    assert raw["native_candidate_score_value"] == 0.
    assert raw["total_zone_entry_count"] == 1
    assert raw["zones"]["zone.a"]["first_breach_scoring_tick"] == 2
    assert raw["zones"]["zone.a"]["last_sampled_intruder_ids_referee_only"] == []


def test_unmeasured_statistics_remain_unavailable_not_zero():
    raw = raw_statistics(plugin().snapshot(), 1.)
    assert raw["measurement_status"] == "not_yet_sampled"
    assert raw["total_zone_entry_count"] is None
    assert all(z["breach_entry_count"] is None and z["protection_time_fraction"] is None for z in raw["zones"].values())
    assert raw["last_sampled_tick"] is None
    assert all(z["last_sampled_intruder_ids_referee_only"] is None for z in raw["zones"].values())


def test_closed_window_occupancy_is_not_misrepresented_as_current():
    model = plugin(end=3)
    value(model, 1)
    value(model, 2, {"target.a": ["zone.a"]})
    value(model, 3, {})
    raw = raw_statistics(model.snapshot(), 1.)
    assert raw["schema_version"] == "referee-denial-raw-statistics@2.0"
    assert raw["last_evaluated_tick"] == 3 and raw["last_sampled_tick"] == 2
    assert raw["zones"]["zone.a"]["last_sampled_intruder_ids_referee_only"] == ["target.a"]
    assert "current_intruder_ids_referee_only" not in raw["zones"]["zone.a"]


def test_first_sample_occupancy_is_not_claimed_as_a_physical_entry_time():
    model = plugin()
    value(model, 1, {"target.a": ["zone.a"]})
    raw = raw_statistics(model.snapshot(), 1.)
    assert raw["total_zone_entry_count"] == 1 and raw["first_breach_scoring_tick"] == 1
    assert "first window sample" in raw["definitions"]["breach_entry_count"]
    assert "not a late-spawn cohort filter" in raw["definitions"]["breach_entry_count"]


def test_audit_failure_does_not_discard_completed_native_result(tmp_path, monkeypatch):
    monkeypatch.setattr(denial_state_audit, "ROOT", tmp_path)
    monkeypatch.setattr(denial_state_audit, "verify", lambda: {"status": "test fixture"})
    versions = iter([{}, {"changed": True}])
    monkeypatch.setattr(denial_state_audit, "frozen_inputs", lambda: next(versions))
    expected = {"trace": [{"tick": 1}], "terminal": {"outcome": "fixture"}}
    monkeypatch.setattr(denial_state_audit.validate_salvo_denial, "run", lambda *args: deepcopy(expected))
    with pytest.raises(RuntimeError, match="source or canonical input changed"):
        denial_state_audit.run(6, "guard", 2001, capture=False)
    directory, = (tmp_path / "artifacts/competition_four_categories").iterdir()
    assert json.loads((directory / "native-result.json").read_text()) == expected
    assert json.loads((directory / "audit-error.json").read_text())["audit_passed"] is False


def test_capture_preserves_return_identity_and_model_state(tmp_path, monkeypatch):
    original = DenialMetricV1.snapshot
    returned = []
    def tracked(model):
        state = original(model); returned.append(state); return state
    monkeypatch.setattr(DenialMetricV1, "snapshot", tracked)
    model = plugin(); before = original(model)
    with DenialStateAudit(tmp_path / "states.jsonl", dt=1.) as observer:
        result = model.snapshot()
        assert result is returned[-1]
        assert original(model) == before
        assert observer.rows[0]["state"] == before
        assert observer.rows[0]["candidate_plugin_state_hash"] == _canonical_hash(before)
    assert DenialMetricV1.snapshot is tracked


def test_observation_does_not_change_any_score_or_snapshot_history(tmp_path):
    control, observed = plugin(), plugin()
    expected = []
    for tick in range(1, 7):
        contacts = {"target.a": ["zone.a"]} if tick in (2, 3) else {}
        transitions = [edge(2)] if tick >= 2 else []
        expected.append((value(control, tick, contacts, transitions), control.snapshot()))
    with DenialStateAudit(tmp_path / "states.jsonl", dt=1.) as observer:
        observed.snapshot()
        for tick, (score, state) in enumerate(expected, 1):
            contacts = {"target.a": ["zone.a"]} if tick in (2, 3) else {}
            transitions = [edge(2)] if tick >= 2 else []
            assert value(observed, tick, contacts, transitions) == score
            assert observed.snapshot() == state
    assert len(observer.rows) == 7


def test_capture_restores_the_method_even_when_the_run_fails(tmp_path):
    original = DenialMetricV1.snapshot
    with pytest.raises(RuntimeError, match="native failure"):
        with DenialStateAudit(tmp_path / "states.jsonl", dt=1.):
            plugin().snapshot()
            raise RuntimeError("native failure")
    assert DenialMetricV1.snapshot is original


def test_repeated_identical_snapshot_reads_are_explicitly_deduplicated(tmp_path):
    model = plugin()
    with DenialStateAudit(tmp_path / "states.jsonl", dt=1.) as observer:
        model.snapshot(); model.snapshot()
    assert observer.snapshot_calls == 2 and len(observer.rows) == 1
    assert json.loads((tmp_path / "states.jsonl").read_text())["audience"] == "referee_only"


def test_all_cause_health_loss_is_not_claimed_as_defender_attribution():
    model = plugin("protected_integrity"); value(model, 1, health=.75)
    raw = raw_statistics(model.snapshot(), .5)
    assert raw["protected_health_all_cause"]["traffic.a"]["maximum_all_cause_health_loss"] == .25
    assert "not defender-only" in raw["definitions"]["protected_health_all_cause"]


def native_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(denial_state_audit, "ROOT", tmp_path)
    model = plugin()
    trace = []
    with DenialStateAudit(tmp_path / "states.jsonl", dt=1.) as observer:
        model.snapshot()
        for tick in (1, 2):
            score = value(model, tick)
            model.snapshot()
            trace.append({"tick": tick, "scores": {model.parameters["metric_id"]: score}})
    result = {"scores": trace[-1]["scores"], "trace": trace, "final_tick": 2}
    return observer, result


def test_verification_covers_all_native_metric_ticks(tmp_path, monkeypatch):
    observer, result = native_fixture(tmp_path, monkeypatch)
    evidence = observer.verify_against_native_result(result)
    assert evidence["every_metric_and_scoring_tick_verified"] is True
    assert evidence["distinct_states_recorded"] == 3
    assert evidence["native_checkpoint_restoration_proven"] is False


@pytest.mark.parametrize("mutation, message", [
    ("trace_gap", "not contiguous"), ("state_gap", "every native scoring tick"),
    ("state_tamper", "state hash changed"), ("score_tamper", "native score receipt")])
def test_verification_rejects_incomplete_or_changed_evidence(tmp_path, monkeypatch, mutation, message):
    observer, result = native_fixture(tmp_path, monkeypatch)
    if mutation == "trace_gap":
        result["trace"].pop(0)
    elif mutation == "state_gap":
        observer.rows.pop(1)
    elif mutation == "state_tamper":
        observer.rows[1]["state"]["samples"] += 1
    else:
        result["trace"][0]["scores"][next(iter(result["scores"]))] = .125
    with pytest.raises(ValueError, match=message):
        observer.verify_against_native_result(result)


def test_pair_comparison_does_not_ignore_actions_or_missing_native_fields():
    control = {"trace_sha256": "hash", "trace": [{"tick": 1}], "terminal": {"done": True},
               "scores": {}, "final_tick": 1, "submitted_actions": [{"status": "accepted"}],
               "native_terminal_checkpoint_gate": {"status": "failed"},
               "referee_metric_state_audit": None, "elapsed_wall_seconds": 1}
    observed = deepcopy(control)
    observed["referee_metric_state_audit"] = {"every_metric_and_scoring_tick_verified": True}
    observed["elapsed_wall_seconds"] = 2
    assert denial_state_audit.compare_results(control, observed)["all_native_evidence_fields_equal"]
    observed["submitted_actions"][0]["status"] = "rejected"
    with pytest.raises(ValueError, match="submitted_actions"):
        denial_state_audit.compare_results(control, observed)
    observed["submitted_actions"] = deepcopy(control["submitted_actions"])
    observed["extra_native_fact"] = None
    with pytest.raises(ValueError, match="extra_native_fact"):
        denial_state_audit.compare_results(control, observed)

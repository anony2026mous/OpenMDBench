from copy import deepcopy
import pytest

from tools.competition_four_categories import tracking_state_audit as audit
from tools.competition_four_categories.tracking_metrics_v1 import TrackingMetricV1
from tools.competition_four_categories.track_report_metrics_v1 import TrackReportMetricV1
from tools.competition_four_categories.tests.test_tracking_metrics import plugin, value
from tools.competition_four_categories.tests.test_track_report_metrics import plugin as report_plugin, snapshot


def test_both_families_are_recorded_without_changing_snapshot_identity(tmp_path, monkeypatch):
    original = TrackingMetricV1.snapshot; returned = []
    def tracking(model):
        state = original(model); returned.append(state); return state
    monkeypatch.setattr(TrackingMetricV1, "snapshot", tracking)
    model = plugin(); report = report_plugin(); before = original(model)
    with audit.TrackingStateAudit(tmp_path / "states.jsonl") as observer:
        state = model.snapshot(); report.snapshot(); model.snapshot()
        assert state is returned[0] and original(model) == before
    assert observer.snapshot_calls == 3 and len(observer.rows) == 2
    assert {r["family"] for r in observer.rows} == {"tracking", "reports"}
    assert TrackingMetricV1.snapshot is tracking


def test_methods_restore_after_native_error(tmp_path):
    before = (TrackingMetricV1.snapshot, TrackReportMetricV1.snapshot)
    with pytest.raises(RuntimeError):
        with audit.TrackingStateAudit(tmp_path / "error.jsonl"):
            raise RuntimeError("native fixture failure")
    assert before == (TrackingMetricV1.snapshot, TrackReportMetricV1.snapshot)


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path); a = plugin(); b = report_plugin(); trace = []
    with audit.TrackingStateAudit(tmp_path / "states.jsonl") as observer:
        a.snapshot(); b.snapshot()
        for tick in range(1, 4):
            score_a = value(a, tick); score_b = b.evaluate(snapshot(tick))["metric.report"]
            a.snapshot(); b.snapshot(); trace.append({"tick": tick, "scores": {"metric.test": score_a, "metric.report": score_b}})
    return observer, {"final_tick": 3, "scores": trace[-1]["scores"], "trace": trace, "terminal": {"done": True}}


def test_all_metrics_and_ticks_and_missing_reports_are_checked(tmp_path, monkeypatch):
    observer, result = fixture(tmp_path, monkeypatch); report = observer.summarize(result, 1)
    assert report["state_rows"] == 8 and report["every_metric_and_scoring_tick_verified"]
    assert report["final_raw_metrics"]["metric.report"]["attributed_identity_switch_fraction"] is None


@pytest.mark.parametrize("change,message", [("hash", "hash differs"), ("missing", "every scoring tick"), ("score", "native receipt")])
def test_inconsistent_or_incomplete_state_is_rejected(tmp_path, monkeypatch, change, message):
    observer, result = fixture(tmp_path, monkeypatch)
    if change == "hash": observer.rows[-1]["state"]["samples"] += 1
    elif change == "missing": observer.rows.pop(2)
    else: result["trace"][0]["scores"]["metric.test"] = .25
    with pytest.raises(ValueError, match=message): observer.summarize(result, 1)


def test_comparison_never_excludes_native_actions_or_failure_flags():
    a = {"elapsed_wall_seconds": 1, "final_tick": 1, "scores": {}, "terminal": {"done": True},
         "trace": [{}], "trace_sha256": "hash", "failure": None, "submitted_actions": [1], "referee_metric_state_audit": None}
    b = deepcopy(a); b["elapsed_wall_seconds"] = 2; b["referee_metric_state_audit"] = {"every_metric_and_scoring_tick_verified": True}
    assert audit.compare_results(a,b)["all_native_fields_equal"]
    b["failure"] = "failed"
    with pytest.raises(ValueError, match="failure"): audit.compare_results(a,b)


def test_failed_audit_preserves_completed_native_result(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path); monkeypatch.setattr(audit, "PACKAGES", tmp_path)
    monkeypatch.setattr(audit, "verify", lambda: {}); monkeypatch.setattr(audit, "frozen_inputs", lambda: {})
    monkeypatch.setattr(audit, "_native_run", lambda *a: {"trace": [1], "terminal": {"done": True}})
    with pytest.raises(FileNotFoundError): audit.run(1,2101,capture=False)
    directory, = (tmp_path / "artifacts/competition_four_categories").iterdir()
    assert (directory / "native-result.json").exists() and (directory / "audit-error.json").exists()

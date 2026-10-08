from copy import deepcopy
import hashlib
import json

import pytest

from tools.competition_four_categories import calibration_matrix as matrix


def setup(tmp_path, monkeypatch):
    folder = tmp_path/"artifacts"; folder.mkdir()
    monkeypatch.setattr(matrix, "ROOT", tmp_path)
    monkeypatch.setattr(matrix, "RESULTS", folder)
    monkeypatch.setattr(matrix, "frozen_inputs", lambda: {"source_hashes": {}, "input_hashes": {}})
    monkeypatch.setattr(matrix, "verify", lambda: {"status": "UNCHANGED"})
    return folder


def test_matrix_covers_all_30_variants_in_seed_major_order():
    seeds = [1201, 1202, 1203, 1204, 1205]
    cases = [case for seed in seeds for case in matrix.cases_for_seed(seed)]
    assert len(cases) == len({c["case_id"] for c in cases}) == 300
    assert [c["seed"] for c in cases] == [seed for seed in seeds for _ in range(60)]
    for seed in seeds:
        subset = [c for c in cases if c["seed"] == seed]
        assert len({c["scenario_id"] for c in subset}) == 28
        variants = {(c["scenario_id"], c["difficulty"]) for c in subset}
        assert len(variants) == 30
        assert all({c["side"] for c in subset if (c["scenario_id"], c["difficulty"]) == variant} == {"A", "B"} for variant in variants)


def test_used_or_reserved_seeds_cannot_be_redeclared_fresh(tmp_path, monkeypatch):
    folder = setup(tmp_path, monkeypatch)
    (folder/"ad-MD-AD-006-guard-1201-20260930T010000Z.json").write_text("{}", encoding="utf-8")
    (folder/"prior-plan.json").write_text(json.dumps({"seeds": [1202]}), encoding="utf-8")
    for seed in (1201, 1202):
        with pytest.raises(ValueError, match="already"): matrix.prepare([seed])
    plan = matrix.prepare([1203]); assert plan.exists()


def test_running_case_is_not_restarted_from_a_state_file(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch); plan_path = matrix.prepare([1201])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    matrix.save_json(plan_path.with_suffix(".state.json"), {"plan_sha256": matrix.sha(plan_path),
        "cases": {plan["cases"][0]["case_id"]: {"status": "running", "pid": 123}}})
    monkeypatch.setattr(matrix.subprocess, "Popen", lambda *a, **k: pytest.fail("must not launch another process"))
    with pytest.raises(ValueError, match="reconciliation"): matrix.run_next(plan_path, 2)


def test_existing_execution_lock_is_not_deleted_or_bypassed(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch); path = matrix.prepare([1201])
    lock = path.with_suffix(".lock"); lock.write_text('{"pid":123}', encoding="utf-8")
    with pytest.raises(ValueError, match="owner PID"): matrix.run_next(path, 1)
    assert lock.read_text(encoding="utf-8") == '{"pid":123}'


def test_state_cannot_skip_cases_or_claim_completion_without_an_artifact(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch); path = matrix.prepare([1201]); plan = json.loads(path.read_text(encoding="utf-8"))
    state = {"plan_sha256": matrix.sha(path), "cases": {plan["cases"][1]["case_id"]: {"status": "recorded"}}}
    matrix.save_json(path.with_suffix(".state.json"), state)
    with pytest.raises(ValueError, match="prefix"): matrix.run_next(path, 1)
    state["cases"] = {plan["cases"][0]["case_id"]: {"status": "recorded"}}
    matrix.save_json(path.with_suffix(".state.json"), state)
    with pytest.raises(ValueError, match="lacks recorded evidence"): matrix.run_next(path, 1)


def test_plan_command_changes_or_frozen_source_drift_are_rejected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch); path = matrix.prepare([1201]); plan = json.loads(path.read_text(encoding="utf-8"))
    changed = deepcopy(plan); changed["cases"][0]["module"] = "os"; matrix.save_json(path, changed)
    with pytest.raises(ValueError, match="commands"): matrix.run_next(path, 1)
    plan["source_hashes"] = {"modified.py": "wrong"}; matrix.save_json(path, plan)
    with pytest.raises(ValueError, match="drifted"): matrix.run_next(path, 1)


def test_both_existing_cli_evidence_formats_are_resolved_within_results(tmp_path, monkeypatch):
    folder = setup(tmp_path, monkeypatch); path = folder/"run.json"; path.write_text("{}", encoding="utf-8")
    assert matrix.evidence_path('evidence=artifacts/run.json') == path
    assert matrix.evidence_path(json.dumps({"evidence": "artifacts/run.json"})) == path
    other = tmp_path/"outside.json"; other.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="inside RESULTS"): matrix.evidence_path('evidence=outside.json')


def result_fixture():
    case = matrix.cases_for_seed(1201)[0]
    terminal = {"outcome": "objective_incomplete"}
    trace = [{"tick": 1, "scores": {"metric": None}, "terminal": terminal}]
    result = {**{k: case[k] for k in ("seed", "scenario_id", "difficulty")},
        "policy": case["expected_policy"], "trace": trace, "scores": trace[-1]["scores"],
        "terminal": terminal, "final_tick": 1, "failure": {"status": "FAILED_CHECKPOINT_GATE"},
        "visibility_audit": {"last_tick": 1, "checked_frames": 2},
        "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()}
    return case, result


def test_recorded_failure_and_missing_metric_are_preserved_not_turned_into_success():
    case, result = result_fixture()
    assert matrix.validate_result(result, case)
    assert result["failure"]["status"] == "FAILED_CHECKPOINT_GATE"
    assert result["scores"]["metric"] is None


@pytest.mark.parametrize("change,reason", [("seed", "identity"), ("digest", "digest"), ("summary", "summary"), ("visibility", "complete")])
def test_invalid_artifact_cannot_count_as_completed_validation(change, reason):
    case, result = result_fixture()
    if change == "seed": result["seed"] = 99
    elif change == "digest": result["trace_sha256"] = "wrong"
    elif change == "summary": result["scores"] = {"metric": 1.}
    else: result["failure"] = None; result["visibility_audit"]["checked_frames"] = 0
    with pytest.raises(ValueError, match=reason): matrix.validate_result(result, case)

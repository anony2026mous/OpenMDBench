"""Turn raw 6.0 P0 observations into auditable gates and run-level records."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from toolkit_paths import PROJECT, ENGINE, EVAL
ARMS = ("rule", "llm", "rule-rl", "llm-rl", "rl", "pure-llm")
LLM_ARMS = {"llm", "llm-rl", "pure-llm"}
FUTURE_PHRASES = ("decoy screen", "real air package", "spawn_tick=",
                  "turn away at tick", "drawn attention")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_table(output: Path, prov: dict) -> list[dict]:
    rows = []
    for manifest_path in sorted(output.glob("ie_*_manifest.json")):
        m = load(manifest_path)
        # A toolkit campaign may store P0 smoke and P1 full episodes together.
        # P1 uses request JSONL and has no smoke-interface fields.
        if "ticks_requested" not in m or "interface_ok" not in m:
            continue
        report = load(output / f"{m['run_id']}.json")
        arm = m["arm"]
        score = report.get("strategy_scorecard") or {}
        checkpoint = prov["checkpoints"].get(arm)
        reqs = load(output / f"{m['run_id']}_requests.json")
        rows.append({
            "scenario_resolved_hash": m["scenario_resolved_hash"],
            "scenario_variant": "frozen_formal_unmodified",
            "scenario": m["scenario"], "seed": m["seed"],
            "run_id": m["run_id"], "arm": arm, "output_tag": output.name,
            "code_hash": m["code_bundle_sha256"],
            "checkpoint_hash": m["checkpoint_sha256"],
            "checkpoint_meta": checkpoint["meta"] if checkpoint else None,
            "LLM_model": prov["llm_configuration"]["model"] if arm in LLM_ARMS else None,
            "backend": prov["llm_configuration"]["backend"] if arm in LLM_ARMS else None,
            "temperature": prov["llm_configuration"]["temperature"] if arm in LLM_ARMS else None,
            "max_tokens": prov["llm_configuration"]["max_tokens"] if arm in LLM_ARMS else None,
            "plan_interval": 10, "decision_interval": 5,
            "speed_source": "legacy_tags" if arm in ("rl", "rule-rl", "llm-rl") else None,
            "rl_stochastic": False, "pure_llm_envelope": "executor",
            "frontend": "graph", "llm_briefing": "withheld",
            "score_version": prov["score_version"],
            "score_code_sha256": prov["score_code_sha256"],
            "ticks_requested": m["ticks_requested"], "ticks_run": report.get("ticks_run"),
            "natural_terminal": report.get("terminal_result") is not None
                                and report.get("aborted") is None,
            "aborted": report.get("aborted"),
            "scored_weight": score.get("scored_weight"),
            "defender_score": score.get("defender_score"),
            "eligible_for_main_score": report.get("terminal_result") is not None
                                       and report.get("aborted") is None
                                       and score.get("scored_weight") is not None,
            "interface_ok": m["interface_ok"], "llm_calls": len(reqs),
            "request_errors": sum("error" in req for req in reqs),
            "empty_responses": sum(not req.get("response") for req in reqs),
            "report_sha256": m["report_sha256"], "log_sha256": m["log_sha256"],
            "requests_sha256": m["requests_sha256"],
        })
    save(output / "p0_run_table.json", rows)
    return rows


def prompt_audit(output: Path, prov: dict) -> dict:
    os.environ["OPENMDBENCH_ROOT"] = str(ENGINE)
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    from attack_driver import load_attack_profile_data
    from run_episode import _build_roe_notes

    profile = load_attack_profile_data("IE-11-DECOY-SCREEN")
    withheld = _build_roe_notes(profile, briefing="withheld")
    declared = _build_roe_notes(profile, briefing="declared")
    entries = []
    for arm in sorted(LLM_ARMS):
        path = output / f"ie_11_decoy_screen_{arm}_s9901_t11_requests.json"
        for index, request in enumerate(load(path)):
            content = str(request["system_prompt"]) + "\n" + str(request["user_message"])
            lower = content.lower()
            entries.append({
                "arm": arm, "call_index": index, "request_path": str(path),
                "base_url": request["base_url"], "model": request["model"],
                "contact_ids_in_prompt": request["contact_ids_in_prompt"],
                "future_phrase_hits": [x for x in FUTURE_PHRASES if x in lower],
                "explicit_decoy_entity_id": "intruder.decoy-" in lower,
                "response_empty": not bool(request.get("response")),
                "request_error": request.get("error"),
                "elapsed_ms": request.get("elapsed_ms"),
            })
    contact = load(output / "ie11_contact_trace.json")
    result = {
        "default_briefing": prov["cli_defaults"]["llm_briefing"],
        "withheld_notes_include_future_label": any(x in withheld.lower() for x in FUTURE_PHRASES),
        "declared_notes_include_future_label": any(x in declared.lower() for x in FUTURE_PHRASES),
        "old_false_main_non_threat_text_present":
            "real air package" in declared.lower()
            and "real air package (spawn_tick=150) is declared non-threat" in declared.lower(),
        "contact_trace": {
            "ticks_run": contact["ticks_run"],
            "contact_fields": contact["contact_fields"],
            "internal_decoy_ids_present": contact["internal_decoy_ids_present"],
            "public_contact_ids_contain_decoy": contact["public_contact_ids_contain_decoy"],
            "public_contact_rows_contain_decoy": contact["public_contact_rows_contain_decoy"],
            "unique_contact_ids": len(contact["first_seen_tick_by_contact"]),
            "decoy_labeled_contact_ids": sum(
                "decoy" in cid.lower() for cid in contact["first_seen_tick_by_contact"]),
            "first_decoy_contact_tick": min((tick for cid, tick in
                contact["first_seen_tick_by_contact"].items() if "decoy" in cid.lower()),
                default=None),
            "first_main_air_contact_tick": min((tick for cid, tick in
                contact["first_seen_tick_by_contact"].items()
                if any(f"intruder.uav-0{i}" in cid for i in range(1, 5))), default=None),
        },
        "actual_llm_requests": entries,
        "future_timeline_withheld_in_all_actual_requests": all(
            not entry["future_phrase_hits"] for entry in entries),
        "decoy_role_id_leaked_in_actual_requests": any(
            entry["explicit_decoy_entity_id"] for entry in entries),
    }
    save(output / "ie11_information_audit.json", result)
    return result


def replay_audit(output: Path) -> dict:
    names = [f"ie_10_dual_axis_pincer_rule_s9901_t20_replay{letter}.json"
             for letter in "AB"]
    if not all((output / name).is_file() for name in names):
        result = {"status": "pending", "reason": "both 20-tick reports are not present"}
    else:
        reports = [load(output / name) for name in names]
        compare = ("scenario", "seed", "planner", "ticks_run", "terminal_result",
                   "score_state", "mission_states", "total_fires", "entities",
                   "fire_rejections", "engagements_by_target_role",
                   "engagements_by_target", "damage_by_kind", "layered_metrics",
                   "strategy_scorecard", "defender", "attack")
        differences = [key for key in compare if reports[0].get(key) != reports[1].get(key)]
        result = {"status": "match" if not differences else "mismatch",
                  "compared_fields": list(compare), "differing_fields": differences,
                  "report_paths": [str(output / name) for name in names],
                  "note": "This is baseline same-seed replay, not an intervention counterfactual."}
    save(output / "baseline_replay_audit.json", result)
    return result


def integrity(output: Path, prov: dict) -> dict:
    drift = []
    for relative, expected in prov["files_sha256"].items():
        path = PROJECT / relative
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            drift.append({"path": relative, "expected": expected, "actual": actual})
    for arm, row in prov["checkpoints"].items():
        path = Path(row["path"])
        actual = sha256(path) if path.is_file() else None
        if actual != row["sha256"]:
            drift.append({"path": str(path), "arm": arm,
                          "expected": row["sha256"], "actual": actual})
    result = {"checked_files": len(prov["files_sha256"]) + len(prov["checkpoints"]),
              "drift": drift, "all_match": not drift}
    save(output / "post_run_integrity.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir
    prov, existing, endpoint = [load(output / name) for name in
        ("provenance.json", "existing_inventory.json", "endpoint_probe.json")]
    runs = run_table(output, prov)
    info = prompt_audit(output, prov)
    replay = replay_audit(output)
    file_check = integrity(output, prov)
    score_test = (output / "strategy_metrics_tests.txt").read_text(
        encoding="utf-8", errors="replace")
    summary = {
        "engine": prov["imported_engine"],
        "selected_scenarios": prov["scenarios"],
        "file_integrity": file_check,
        "endpoint_model_gate": endpoint["status"] == 200
                               and endpoint["required_model_present"],
        "scorecard_unit_test_gate": "26/26 passed" in score_test,
        "ie10_six_arms_interface_ok": all(any(
            r["scenario"] == "IE-10-DUAL-AXIS-PINCER" and r["arm"] == arm
            and r["ticks_requested"] == 1 and r["interface_ok"] for r in runs)
            for arm in ARMS),
        "ie11_three_llm_arms_interface_ok": all(any(
            r["scenario"] == "IE-11-DECOY-SCREEN" and r["arm"] == arm
            and r["ticks_requested"] == 11 and r["interface_ok"] for r in runs)
            for arm in LLM_ARMS),
        "all_smokes_preterminal": all(not r["eligible_for_main_score"] for r in runs),
        "historical_inventory_count": existing["count"],
        "historical_fully_provenanced_natural_terminal_count":
            existing["fully_provenanced_natural_terminal_count"],
        "ie11_future_timeline_withheld": info["future_timeline_withheld_in_all_actual_requests"],
        "ie11_decoy_id_leak": info["decoy_role_id_leaked_in_actual_requests"],
        "baseline_replay": replay,
        "checkpoint_source_drift_counts": {k: len(v) for k, v in
                                           prov["checkpoint_source_drift"].items()},
        "p0_d1_no_hidden_role_truth_gate": not info["decoy_role_id_leaked_in_actual_requests"]
                                        and not info["contact_trace"]["public_contact_ids_contain_decoy"],
    }
    save(output / "p0_summary.json", summary)
    print(json.dumps({k: summary[k] for k in (
        "endpoint_model_gate", "scorecard_unit_test_gate", "ie10_six_arms_interface_ok",
        "ie11_three_llm_arms_interface_ok", "ie11_future_timeline_withheld",
        "ie11_decoy_id_leak", "p0_d1_no_hidden_role_truth_gate")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

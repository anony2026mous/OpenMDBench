"""Verify recorded trace contents, fingerprints and bounded replay evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path

from hifi_trace import canonical, digest, file_hash
from hifi_replay_campaign import SCENARIOS


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_episode(path):
    report = read(path)
    trace = path.with_name("events.jsonl")
    errors = []
    if report["trace_sha256"] != file_hash(trace):
        errors.append("trace_hash_mismatch")
    records = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    transitions = [r for r in records if r["kind"] == "transition"]
    decisions = [r for r in records if r["kind"] == "decision"]
    if decisions != report["decisions"]:
        errors.append("decision_content_mismatch")
    derived = [{"tick": r["tick"], "world": r["world_checkpoint_sha256"],
                "broker": r["broker_sha256"], "transition": digest(r)} for r in transitions]
    if derived != report["fingerprints"]:
        errors.append("transition_fingerprint_mismatch")
    checkpoint_interval = report["config"].get("world_checkpoint_interval", 1)
    if not isinstance(checkpoint_interval, int) or checkpoint_interval < 1:
        errors.append("invalid_checkpoint_interval")
    else:
        expected_schema = "role-c-hifi-trace@1" if checkpoint_interval == 1 else "role-c-hifi-trace@2"
        if report.get("schema") != expected_schema:
            errors.append("trace_schema_checkpoint_interval_mismatch")
        for row in transitions:
            terminal_row = any(
                receipt.get("terminal_result") is not None
                for receipt in row.get("step_receipt", {}).get("world_receipt", {}).get("mission_receipts", [])
            )
            required = row["after_tick"] % checkpoint_interval == 0 or terminal_row
            world_hash = row.get("world_checkpoint_sha256")
            if required != (isinstance(world_hash, str) and len(world_hash) == 64):
                errors.append(f"checkpoint_schedule_mismatch: tick {row['tick']}")
                break
    if [r["tick"] for r in transitions] != list(range(report["ticks_run"] or 0)):
        errors.append("missing_or_duplicate_tick")
    if any(r["after_tick"] != r["tick"] + 1 for r in transitions):
        errors.append("state_clock_mismatch")
    if report["aborted"] or not report["source_unchanged"]:
        errors.append("aborted_or_source_changed")
    goals = []
    states = []
    for row in transitions:
        goals.append(canonical(sorted([
            {k: v for k, v in goal.items() if k not in ("task_id", "issued_at")}
            for goal in row["active_goals_before_execution"]], key=canonical)))
        states.append(canonical(row["own_after"]))
    goal_counts = Counter(goals)
    terminal_evidence = []
    for row in transitions:
        receipts = row.get("step_receipt", {}).get("world_receipt", {}).get("mission_receipts", [])
        for receipt in receipts:
            terminal = receipt.get("terminal_result")
            if terminal is not None:
                if not isinstance(terminal, dict) or terminal.get("latched") is not True:
                    errors.append("unstructured_or_unlatched_terminal_evidence")
                elif terminal.get("tick") != row["after_tick"]:
                    errors.append("terminal_evidence_clock_mismatch")
                else:
                    terminal_evidence.append(terminal)
    if (report["terminal_result"] is not None) != bool(terminal_evidence):
        errors.append("terminal_summary_disagrees_with_authoritative_receipt")
    return {"report_path": str(path.resolve()), "errors": errors,
            "transitions": len(transitions), "decisions": len(decisions),
            "world_checkpoint_interval": checkpoint_interval,
            "world_checkpoints": sum(r.get("world_checkpoint_sha256") is not None for r in transitions),
            "unique_full_states": len(set(states)), "unique_semantic_goal_sets": len(goal_counts),
            "minimum_goal_category_samples": min(goal_counts.values()) if goal_counts else 0,
            "full_state_empirical_MI_degenerates_to_goal_entropy": bool(states) and len(set(states)) == len(states),
            "terminal_reached": bool(terminal_evidence), "authoritative_terminal_evidence": terminal_evidence,
            "replay_check": report["replay_check"],
            "B_if_formal_estimate": None,
            "formal_estimate_unavailable_reason": "Unfrozen statistical encoding, short temporal trace, density/support assumptions unverified"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--passive-control", type=Path)
    args = parser.parse_args()
    campaign, output = args.campaign.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(campaign) or campaign.is_relative_to(output):
        raise ValueError("New audit output outside immutable campaign required")
    summary = read(campaign / "summary.json")
    audits, errors = [], []
    selected = summary.get("selected_scenarios", SCENARIOS)
    if not isinstance(selected, list) or not selected or len(selected) != len(set(selected)) or any(
        scenario not in SCENARIOS for scenario in selected
    ):
        raise ValueError("Invalid selected_scenarios in campaign summary")
    if len(summary["entries"]) != 2 * len(selected):
        errors.append("incomplete_campaign_entry_count")
    reports = {}
    for entry in summary["entries"]:
        path = Path(entry.get("report_path", ""))
        if not path.is_file():
            errors.append(f"missing_report: {entry['scenario']} {entry['kind']}")
            continue
        if file_hash(path) != entry["report_sha256"]:
            errors.append(f"report_hash: {path}")
        audit = verify_episode(path)
        if summary.get("terminal_required") and not audit["terminal_reached"]:
            errors.append(f"required_terminal_not_reached: {entry['alias']} {entry['kind']}")
        report = read(path)
        key = (entry["alias"], entry["kind"])
        if key in reports:
            errors.append(f"duplicate_case: {key}")
        reports[key] = (report, path)
        if report["instrumentation_sha256"] != summary["script_sha256"]:
            errors.append(f"instrumentation_version_mismatch: {key}")
        audits.append({"alias": entry["alias"], "kind": entry["kind"], **audit})
        errors.extend(f"{entry['alias']} {entry['kind']}: {e}" for e in audit["errors"])
    for scenario in selected:
        index = SCENARIOS.index(scenario) + 1
        alias = f"IE-{index:02d}"
        if (alias, "original") not in reports or (alias, "replay") not in reports:
            errors.append(f"missing_pair: {alias}")
            continue
        original, original_path = reports[(alias, "original")]
        replay, replay_path = reports[(alias, "replay")]
        if original["config"]["scenario"] != scenario or original["config"] != replay["config"]:
            errors.append(f"scenario_or_config_mismatch: {alias}")
        if original["source_hashes"] != replay["source_hashes"]:
            errors.append(f"source_version_mismatch: {alias}")
        if original["fingerprints"] != replay["fingerprints"] or original["decisions"] != replay["decisions"]:
            errors.append(f"recomputed_replay_mismatch: {alias}")
        if replay["replay_source_sha256"] != file_hash(original_path):
            errors.append(f"replay_source_hash_mismatch: {alias}")
        original_engine = read(original_path.with_name("engine_result.json"))
        replay_engine = read(replay_path.with_name("engine_result.json"))
        for field in ("terminal_result", "score_state", "mission_states", "total_fires", "entities", "strategy_scorecard"):
            if original_engine[field] != replay_engine[field]:
                errors.append(f"outcome_mismatch: {alias} {field}")
    passive = None
    if args.passive_control:
        root = args.passive_control
        original_path = root / "original/engine_result.json"
        baseline_path = root / "uninstrumented/engine_result.json"
        instrumented, baseline = read(original_path), read(baseline_path)
        timing = {"elapsed_seconds", "ticks_per_second", "step_mean_seconds", "step_max_seconds"}
        differences = [k for k in set(instrumented) | set(baseline) if k not in timing and instrumented.get(k) != baseline.get(k)]
        passive = {"original_sha256": file_hash(original_path), "uninstrumented_sha256": file_hash(baseline_path),
                   "only_excluded_fields": sorted(timing), "differing_fields": sorted(differences),
                   "non_timing_results_identical": not differences,
                   "scope": "IE-01 seed 100, first 30 ticks; final outcome fields, not uninstrumented per-tick hidden state"}
        if differences:
            errors.append("passive_control_result_mismatch")
    selected_passed = summary["limited_replay_gate_passed"] and not errors
    result = {"campaign_summary_sha256": file_hash(campaign / "summary.json"), "errors": errors,
              "selected_scenarios": selected,
              "episodes": audits, "passive_control": passive,
              "selected_replay_gate_passed": selected_passed,
              "all_eight_bounded_replays_passed": selected_passed and set(selected) == set(SCENARIOS),
              "formal_B_if_complete": False, "formal_attribution_complete": False}
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"errors": errors, "episodes": len(audits),
                      "all_eight_bounded_replays_passed": result["all_eight_bounded_replays_passed"],
                      "passive_control": passive}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())

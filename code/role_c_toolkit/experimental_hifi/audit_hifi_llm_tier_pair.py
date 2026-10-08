"""Independent auditor for an LLM+GOAI original and frozen-Goal replay pair."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_hifi_traces import verify_episode
from hifi_trace import file_hash


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit_pair(original_path: Path, replay_path: Path) -> dict:
    original_path, replay_path = original_path.resolve(), replay_path.resolve()
    original, replay = read(original_path), read(replay_path)
    errors = []
    for label, path, report in (("original", original_path, original), ("replay", replay_path, replay)):
        checked = verify_episode(path)
        errors.extend(f"{label}:{err}" for err in checked["errors"])
        if not checked["terminal_reached"]:
            errors.append(f"{label}:natural_terminal_missing")
        if report.get("config", {}).get("planner") != "llm":
            errors.append(f"{label}:not_llm_planner")
        if report.get("config", {}).get("goal_granularity") not in {"weak", "medium", "strong"}:
            errors.append(f"{label}:invalid_goal_tier")
    if original.get("config") != replay.get("config"):
        errors.append("pair_config_mismatch")
    if original.get("source_hashes") != replay.get("source_hashes"):
        errors.append("source_manifest_mismatch")
    if original.get("decisions") != replay.get("decisions"):
        errors.append("decision_stream_mismatch")
    if original.get("fingerprints") != replay.get("fingerprints"):
        errors.append("transition_fingerprint_mismatch")
    if replay.get("replay_source_sha256") != file_hash(original_path):
        errors.append("replay_source_hash_mismatch")
    if not (replay.get("replay_check") or {}).get("exact_match"):
        errors.append("runner_exact_replay_check_failed")

    original_engine = read(original_path.with_name("engine_result.json"))
    replay_engine = read(replay_path.with_name("engine_result.json"))
    outcome_fields = ("terminal_result", "score_state", "mission_states", "ticks_run",
                      "total_fires", "entities", "strategy_scorecard")
    outcome_differences = [key for key in outcome_fields
                           if original_engine.get(key) != replay_engine.get(key)]
    if outcome_differences:
        errors.append("outcome_mismatch:" + ",".join(outcome_differences))

    llm_stats = original.get("llm_client_stats") or {}
    planner_stats = original.get("planner_diagnostics") or {}
    calls = llm_stats.get("total_calls")
    if not isinstance(calls, int) or calls < 1:
        errors.append("original_has_no_confirmed_llm_call")
    if llm_stats.get("errors") != 0:
        errors.append("llm_client_errors_nonzero")
    if planner_stats.get("fallback_count") != 0:
        errors.append("planner_fallback_nonzero")
    if planner_stats.get("parse_failures") != 0:
        errors.append("planner_parse_failures_nonzero")
    if llm_stats.get("model") != original["config"]["llm"]["model"]:
        errors.append("llm_model_stats_mismatch")
    if llm_stats.get("base_url") != original["config"]["llm"]["base_url"]:
        errors.append("llm_endpoint_stats_mismatch")

    return {"schema": "role-c-hifi-llm-goai-pair-audit@1",
            "original_report_path": str(original_path), "original_report_sha256": file_hash(original_path),
            "replay_report_path": str(replay_path), "replay_report_sha256": file_hash(replay_path),
            "errors": errors, "exact_terminal_pair_passed": not errors,
            "outcome_fields_compared": list(outcome_fields),
            "outcome_differences": outcome_differences,
            "llm_diagnostics": {"calls": calls, "errors": llm_stats.get("errors"),
                                "fallbacks": planner_stats.get("fallback_count"),
                                "parse_failures": planner_stats.get("parse_failures"),
                                "model": llm_stats.get("model"),
                                "base_url": llm_stats.get("base_url")},
            "formal_B_if_validated": False, "formal_attribution_validated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or any(output.is_relative_to(path.resolve().parent) or
                              path.resolve().parent.is_relative_to(output)
                              for path in (args.original, args.replay)):
        raise ValueError("New audit output directory outside immutable pair required")
    result = audit_pair(args.original, args.replay)
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    print(json.dumps({"errors": result["errors"],
                      "exact_terminal_pair_passed": result["exact_terminal_pair_passed"],
                      "llm_diagnostics": result["llm_diagnostics"]}, ensure_ascii=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit P1 raw episodes and compute only comparable natural-terminal results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

SCENARIOS = ("IE-04-COMBINED-ARMS", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN")
ARMS = ("rule", "llm", "rule-rl", "llm-rl", "rl", "pure-llm")
PURE = ("rule", "rl", "pure-llm")
LLM_ARMS = ("llm", "llm-rl", "pure-llm")
SEEDS = (201, 202, 203)
BASE_URL = "http://172.18.116.170:8000/v1"
MODEL = "Qwen3.8-27B"
GOAL_GRANULARITY = "strong"
SECONDARY_FIELDS = (
    "weighted_facility_survival", "facilities_out_of_action",
    "real_air_interception_rate_offline", "real_air_leak_rate_offline",
    "real_air_release_rate_offline", "surface_layer_score", "defender_shots",
    "air_target_shots", "surface_target_shots", "defender_ammo_efficiency",
    "ticks_run", "elapsed_seconds", "decoy_shots_authoritative",
    "decoy_shots_pre150", "decoy_shots_tick150_249",
    "real_air_shots_tick150_249", "first_real_air_fire_tick",
)
# IE-11 scripted real-air wave begins at tick 150. Keep this post-arrival
# inspection window fixed before examining any confirmatory IE-11 episode.
IE11_MAIN_ARRIVAL_TICK = 150
IE11_POST_WINDOW_END_EXCLUSIVE = 250


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_id(scenario: str, arm: str, seed: int, attempt: int = 1) -> str:
    return f"{scenario.lower().replace('-', '_')}_{arm}_s{seed}_a{attempt}"


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    lo, hi = int(index), min(len(values) - 1, int(index) + 1)
    weight = index - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def paired_summary(values: list[float]) -> dict:
    if not values:
        return {"n_seed": 0, "mean": None, "bootstrap_2p5": None,
                "bootstrap_97p5": None}
    # Exact n^n enumeration becomes impossible at the planned 20-seed scale.
    rng = random.Random(20260928)
    means = [statistics.mean(rng.choices(values, k=len(values)))
             for _ in range(10000)]
    return {"n_seed": len(values), "mean": statistics.mean(values),
            "bootstrap_2p5": percentile(means, 0.025),
            "bootstrap_97p5": percentile(means, 0.975),
            "seed_values": values, "resamples": len(means)}


def mean_field(rows: list[dict], arm: str, field: str) -> float | None:
    values = [row[field] for row in rows
              if row["arm"] == arm and row[field] is not None]
    return statistics.mean(values) if values else None


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_cell(out: Path, provenance: dict, scenario: str, arm: str, seed: int,
               attempt: int = 1):
    ident = run_id(scenario, arm, seed, attempt)
    paths = {suffix: out / f"{ident}{suffix}" for suffix in
             ("_manifest.json", ".json", ".jsonl", "_requests.jsonl")}
    if not paths["_manifest.json"].is_file():
        return None, {"run_id": ident, "reason": "missing_manifest"}
    manifest = load(paths["_manifest.json"])
    reasons = []
    if manifest.get("run_id") != ident or manifest.get("attempt") != attempt:
        reasons.append("manifest_identity_mismatch")
    if manifest.get("status") != "complete" or not manifest.get("eligible_for_main_score"):
        reasons.append("not_complete_eligible")
    if manifest.get("scenario_resolved_hash") != provenance["scenarios"][scenario]["resolved_hash"]:
        reasons.append("scenario_hash_mismatch")
    if manifest.get("code_bundle_sha256") != provenance["code_bundle_sha256"]:
        reasons.append("code_hash_mismatch")
    if manifest.get("wrapper_sha256") != sha256(Path(__file__).with_name("p1_6_run.py")):
        reasons.append("wrapper_hash_mismatch")
    if manifest.get("score_code_sha256") != provenance["score_code_sha256"]:
        reasons.append("score_hash_mismatch")
    if manifest.get("goal_granularity") != GOAL_GRANULARITY:
        reasons.append("goal_granularity_mismatch")
    if manifest.get("checkpoint_sha256") != (provenance["checkpoints"][arm]["sha256"]
                                                if arm in provenance["checkpoints"] else None):
        reasons.append("checkpoint_mismatch")
    if (manifest.get("pure_llm_envelope"), manifest.get("llm_briefing"),
        manifest.get("frontend"), manifest.get("rl_stochastic")) != (
            "executor", "withheld", "graph", False):
        reasons.append("frontend_or_envelope_mismatch")
    if arm in LLM_ARMS and (
        manifest.get("base_url") != BASE_URL
        or manifest.get("model") != MODEL
        or manifest.get("backend") != "vllm"
    ):
        reasons.append("llm_configuration_mismatch")
    for suffix, hash_key in ((".json", "report_sha256"),
                             (".jsonl", "events_sha256"),
                             ("_requests.jsonl", "requests_sha256")):
        if not paths[suffix].is_file() or sha256(paths[suffix]) != manifest.get(hash_key):
            reasons.append(f"{suffix}_hash_missing_or_mismatch")
    if reasons:
        return None, {"run_id": ident, "reason": ",".join(reasons)}
    report = load(paths[".json"])
    score = report.get("strategy_scorecard") or {}
    if (report.get("terminal_result") is None or report.get("aborted") is not None
        or score.get("scored_weight") is None or score.get("defender_score") is None
        or report.get("scenario") != scenario or report.get("seed") != seed
        or report.get("planner") != arm):
        return None, {"run_id": ident, "reason": "raw_report_not_same_natural_terminal"}
    events = read_jsonl(paths[".jsonl"])
    requests = read_jsonl(paths["_requests.jsonl"])
    request_rows = [row for row in requests if row.get("kind") == "request"]
    reply_rows = [row for row in requests if row.get("kind") in ("response", "error")]
    if len(request_rows) != len(reply_rows) or len(request_rows) != manifest.get("llm_calls"):
        return None, {"run_id": ident, "reason": "llm_request_response_count_mismatch"}
    if arm not in LLM_ARMS and request_rows:
        return None, {"run_id": ident, "reason": "non_llm_arm_has_llm_request"}
    if arm in LLM_ARMS and any(
        row.get("base_url") != BASE_URL
        or row.get("model") != MODEL
        or row.get("backend") != "vllm"
        for row in request_rows
    ):
        return None, {"run_id": ident, "reason": "actual_request_endpoint_or_model_mismatch"}
    tags = {entity["entity_id"]: set(entity.get("tags") or ())
            for entity in report.get("entities") or ()}
    entity_ids = tuple(sorted(tags, key=len, reverse=True))
    fires = []
    for event in events:
        if event.get("t") != "fire" or event.get("side") != "defender" or not event.get("executed"):
            continue
        contact_id = str(event.get("contact_id") or "")
        target = next((name for name in entity_ids if contact_id.endswith(name)), None)
        fires.append({"tick": int(event.get("fire_tick") or event.get("tick") or 0),
                      "target": target, "tags": tags.get(target, set())})
    if len(fires) != report.get("total_fires_defender"):
        return None, {"run_id": ident, "reason": "executed_fire_count_mismatch"}
    decoy_fires = [row for row in fires if "decoy" in row["tags"]]
    real_air_fires = [row for row in fires if "uav" in row["tags"]
                      and "decoy" not in row["tags"] and row["target"]
                      and row["target"].startswith("intruder.")]
    raider_rows = (score.get("air_layer") or {}).get("raiders") or ()
    real_air_raiders = [item for item in raider_rows
                        if "uav" in tags.get(item.get("entity_id"), set())
                        and "decoy" not in tags.get(item.get("entity_id"), set())]
    decoy_raiders = [item for item in raider_rows
                     if "decoy" in tags.get(item.get("entity_id"), set())]
    interception_depths = ((score.get("air_layer") or {}).get("interception_depth_m")
                           or {}).get("per_entity") or {}
    strike_radius = (score.get("air_layer") or {}).get("strike_radius_m")
    real_air_leakers = [item for item in real_air_raiders
                        if isinstance(item.get("final_range_to_target_m"), (int, float))
                        and isinstance(strike_radius, (int, float))
                        and item["final_range_to_target_m"] <= strike_radius]
    if scenario == "IE-11-DECOY-SCREEN" and any(
        "intruder.decoy-" in (str(row.get("system_prompt") or "")
                              + str(row.get("user_message") or ""))
        for row in request_rows
    ):
        return None, {"run_id": ident, "reason": "ie11_role_truth_in_actual_prompt"}
    row = {
        "scenario": scenario, "seed": seed, "arm": arm, "run_id": ident,
        "scenario_hash": manifest["scenario_resolved_hash"],
        "defender_score": score["defender_score"],
        "scored_weight": score["scored_weight"],
        "terminal_outcome": (score.get("terminal") or {}).get("outcome"),
        "terminal_state": (score.get("terminal") or {}).get("state"),
        "ticks_run": report.get("ticks_run"),
        "elapsed_seconds": report.get("elapsed_seconds"),
        "weighted_facility_survival": (score.get("facilities") or {}).get("weighted_survival"),
        "facilities_out_of_action": (score.get("facilities") or {}).get("out_of_action"),
        "air_interception_rate": (score.get("air_layer") or {}).get("interception_rate"),
        "real_air_interception_rate_offline": (
            sum(item.get("entity_id") in interception_depths for item in real_air_raiders)
            / len(real_air_raiders)
            if real_air_raiders else None),
        "real_air_leak_rate_offline": (
            len(real_air_leakers) / len(real_air_raiders) if real_air_raiders else None),
        "real_air_release_rate_offline": (
            sum(bool(item.get("released_on_target")) for item in real_air_raiders)
            / len(real_air_raiders) if real_air_raiders else None),
        "decoy_air_lost_count_offline": sum(bool(item.get("lost")) for item in decoy_raiders),
        "decoy_air_total_offline": len(decoy_raiders),
        "air_leak_rate": (score.get("air_layer") or {}).get("leak_rate"),
        "air_release_rate": (score.get("air_layer") or {}).get("release_rate"),
        "surface_layer_score": (score.get("layers") or {}).get("surface"),
        "defender_shots": report.get("total_fires_defender"),
        "defender_ammo_efficiency": (score.get("fire") or {}).get(
            "defender_ammo_efficiency"),
        "air_target_shots": sum("uav" in item["tags"] for item in fires),
        "surface_target_shots": sum(bool(item["tags"] & {"usv", "boat"}) for item in fires),
        "decoy_shots_authoritative": len(decoy_fires),
        "decoy_shots_pre150": sum(item["tick"] < IE11_MAIN_ARRIVAL_TICK
                                  for item in decoy_fires),
        "pre150_defender_shots": sum(item["tick"] < IE11_MAIN_ARRIVAL_TICK
                                      for item in fires),
        "decoy_shots_tick150_249": sum(
            IE11_MAIN_ARRIVAL_TICK <= item["tick"] < IE11_POST_WINDOW_END_EXCLUSIVE
            for item in decoy_fires),
        "real_air_shots_tick150_249": sum(
            IE11_MAIN_ARRIVAL_TICK <= item["tick"] < IE11_POST_WINDOW_END_EXCLUSIVE
            for item in real_air_fires),
        "first_real_air_fire_tick": min((item["tick"] for item in real_air_fires),
                                        default=None),
        "llm_requests": len(request_rows),
        "llm_errors": sum(item.get("kind") == "error" for item in reply_rows),
        "llm_empty": sum(item.get("kind") == "response" and not item.get("response")
                         for item in reply_rows),
        "llm_latencies_ms": [item.get("elapsed_ms") for item in reply_rows
                             if isinstance(item.get("elapsed_ms"), (int, float))],
        "planner_parse_failures": ((report.get("defender") or {}).get("planner") or {}).get(
            "parse_failures"),
        "planner_fallback_count": (
            ((report.get("defender") or {}).get("planner") or {}).get("fallback_count")
            if arm != "pure-llm" else (report.get("defender") or {}).get("fallback_count")),
        "stale_plan_reuse": ((report.get("defender") or {}).get("planner") or {}).get(
            "stale_plan_reuse"),
        "pure_masked_count": (report.get("defender") or {}).get("masked_count")
        if arm == "pure-llm" else None,
        "legacy_fires_decoy": (report.get("layered_metrics") or {}).get("fires_decoy"),
        "report_sha256": manifest["report_sha256"],
    }
    return row, None


def main() -> None:
    global SCENARIOS, SEEDS, BASE_URL, MODEL, GOAL_GRANULARITY
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    config = load(out / "toolkit_config.json")
    SCENARIOS = tuple(config["scenarios"])
    SEEDS = tuple(config["seeds"])
    BASE_URL = config["base_url"]
    MODEL = config["model"]
    GOAL_GRANULARITY = config["goal_granularity"]
    provenance = load(out / "provenance.json")
    cells, missing, attempt_audit = [], [], []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            for arm in ARMS:
                stem = run_id(scenario, arm, seed).rsplit("_a", 1)[0]
                attempts = sorted({int(path.stem.rsplit("_a", 1)[1].replace("_manifest", ""))
                                   for path in out.glob(f"{stem}_a*_manifest.json")
                                   if path.stem.rsplit("_a", 1)[1].replace("_manifest", "").isdigit()})
                if not attempts:
                    attempts = [1]
                eligible_rows = []
                for attempt in attempts:
                    row, failure = audit_cell(out, provenance, scenario, arm, seed, attempt)
                    attempt_audit.append({"run_id": run_id(scenario, arm, seed, attempt),
                                          "eligible": row is not None,
                                          "reason": None if row is not None else failure["reason"]})
                    if row:
                        eligible_rows.append(row)
                if eligible_rows:
                    # The first certified run is selected by a fixed rule, not score.
                    cells.append(eligible_rows[0])
                else:
                    missing.append({"cell": stem, "attempts": attempts,
                                    "reason": "no_certified_attempt"})
    save(out / "p1_attempt_audit.json", attempt_audit)
    save(out / "p1_missing_or_ineligible.json", missing)
    csv_fields = [key for key in cells[0] if key != "llm_latencies_ms"] if cells else [
        "scenario", "seed", "arm", "run_id"]
    write_csv(out / "p1_cells.csv", cells, csv_fields)
    by_cell = {(row["scenario"], row["seed"], row["arm"]): row for row in cells}
    paired_rows, secondary_paired_rows, scene_summaries = [], [], {}
    for scenario in SCENARIOS:
        scene_rows = [row for row in cells if row["scenario"] == scenario]
        arm_means = {arm: statistics.mean(row["defender_score"] for row in scene_rows
                                           if row["arm"] == arm)
                     for arm in ARMS if sum(row["arm"] == arm for row in scene_rows) == len(SEEDS)}
        best_pure = (max(PURE, key=lambda arm: arm_means[arm])
                     if all(arm in arm_means for arm in PURE) else None)
        differences: dict[str, list[float]] = defaultdict(list)
        for seed in SEEDS:
            cell = {arm: by_cell.get((scenario, seed, arm)) for arm in ARMS}
            row = {"scenario": scenario, "seed": seed,
                   **{f"score_{arm}": cell[arm]["defender_score"] if cell[arm] else None
                      for arm in ARMS}}
            score = {arm: cell[arm]["defender_score"]
                     for arm in ARMS if cell[arm] is not None}
            comparisons = {
                "llm_minus_rule": ("llm", "rule"),
                "llmrl_minus_rulerl": ("llm-rl", "rule-rl"),
                "llm_minus_rl": ("llm", "rl"),
                "llm_minus_purellm": ("llm", "pure-llm"),
                "llmrl_minus_rule": ("llm-rl", "rule"),
                "llmrl_minus_rl": ("llm-rl", "rl"),
                "llmrl_minus_purellm": ("llm-rl", "pure-llm"),
            }
            for name, (left, right) in comparisons.items():
                if left in score and right in score:
                    row[name] = score[left] - score[right]
                    differences[name].append(row[name])
            if all(arm in score for arm in ("rule", "llm", "rule-rl", "llm-rl")):
                row["P_this_seed"] = score["llm"] - score["rule"]
                row["E_this_seed"] = score["rule-rl"] - score["rule"]
                row["I_this_seed"] = (score["llm-rl"] - score["llm"]
                                      - score["rule-rl"] + score["rule"])
            if all(arm in score for arm in PURE):
                seed_best_pure = max(PURE, key=lambda arm: score[arm])
                row["best_pure_this_seed"] = seed_best_pure
                row["B_this_seed"] = score[seed_best_pure] - score["rule"]
                if "P_this_seed" in row:
                    row["hybrid_A_minus_best_pure_this_seed"] = (
                        row["P_this_seed"] - row["B_this_seed"])
                    row["hybrid_B_minus_best_pure_this_seed"] = (
                        row["P_this_seed"] + row["E_this_seed"]
                        + row["I_this_seed"] - row["B_this_seed"])
                    differences["hybrid_A_minus_best_pure_this_seed"].append(
                        row["hybrid_A_minus_best_pure_this_seed"])
                    differences["hybrid_B_minus_best_pure_this_seed"].append(
                        row["hybrid_B_minus_best_pure_this_seed"])
            paired_rows.append(row)
            secondary_row = {"scenario": scenario, "seed": seed}
            for left, right, label in (("llm", "rule", "llm_minus_rule"),
                                       ("llm-rl", "rule-rl", "llmrl_minus_rulerl")):
                if cell[left] is not None and cell[right] is not None:
                    for field in SECONDARY_FIELDS:
                        a, b = cell[left][field], cell[right][field]
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            secondary_row[f"{label}_{field}"] = a - b
            secondary_paired_rows.append(secondary_row)
        formula = None
        if all(arm in arm_means for arm in ("rule", "llm", "rule-rl", "llm-rl")):
            base = arm_means["rule"]
            p = arm_means["llm"] - base
            e = arm_means["rule-rl"] - base
            i = arm_means["llm-rl"] - arm_means["llm"] - arm_means["rule-rl"] + base
            b = arm_means[best_pure] - base if best_pure else None
            formula = {"P": p, "E": e, "I": i, "B": b,
                       "hybrid_A_minus_best_pure": p - b if b is not None else None,
                       "hybrid_B_minus_best_pure": p + e + i - b if b is not None else None,
                       "identity_residual_B": ((p + e + i - b)
                       - (arm_means["llm-rl"] - arm_means[best_pure]))
                       if b is not None else None}
        scene_summaries[scenario] = {
            "n_eligible_cells": len(scene_rows), "arm_means": arm_means,
            "secondary_means_all_eligible_with_n": {
                arm: {"n_episodes": sum(row["arm"] == arm for row in scene_rows),
                      "terminal_outcomes": [row["terminal_outcome"] for row in scene_rows
                                            if row["arm"] == arm],
                      **{field: mean_field(scene_rows, arm, field)
                         for field in SECONDARY_FIELDS}}
                for arm in ARMS},
            "secondary_means_complete_arms_only": {
                arm: {field: mean_field(scene_rows, arm, field)
                      for field in (
                          "weighted_facility_survival", "facilities_out_of_action",
                          "real_air_interception_rate_offline",
                          "real_air_leak_rate_offline", "real_air_release_rate_offline",
                          "surface_layer_score", "defender_shots",
                          "defender_ammo_efficiency", "ticks_run", "elapsed_seconds")}
                for arm in arm_means},
            "best_pure_by_mean": best_pure,
            "paired_differences": {name: paired_summary(values)
                                   for name, values in differences.items()},
            "formula_accounting_deployment_only": formula,
            "terminal_outcomes": {arm: [row["terminal_outcome"] for row in scene_rows
                                       if row["arm"] == arm] for arm in ARMS},
        }
    paired_fields = ["scenario", "seed"] + [f"score_{arm}" for arm in ARMS] + [
        "llm_minus_rule", "llmrl_minus_rulerl", "llm_minus_rl",
        "llm_minus_purellm", "llmrl_minus_rule", "llmrl_minus_rl",
        "llmrl_minus_purellm", "best_pure_this_seed", "P_this_seed",
        "E_this_seed", "I_this_seed", "B_this_seed",
        "hybrid_A_minus_best_pure_this_seed",
        "hybrid_B_minus_best_pure_this_seed"]
    write_csv(out / "p1_paired.csv", paired_rows, paired_fields)
    secondary_paired_fields = ["scenario", "seed"] + [
        f"{label}_{field}" for label in ("llm_minus_rule", "llmrl_minus_rulerl")
        for field in SECONDARY_FIELDS]
    write_csv(out / "p1_secondary_paired.csv", secondary_paired_rows,
              secondary_paired_fields)
    write_csv(out / "p1_mechanism.csv", cells, [
        "scenario", "seed", "arm", "defender_shots", "air_target_shots",
        "surface_target_shots", "decoy_shots_authoritative", "decoy_shots_pre150",
        "pre150_defender_shots", "decoy_shots_tick150_249",
        "real_air_shots_tick150_249", "first_real_air_fire_tick", "legacy_fires_decoy",
        "real_air_interception_rate_offline", "decoy_air_lost_count_offline",
        "decoy_air_total_offline"])
    llm_cells = [row for row in cells if row["arm"] in LLM_ARMS]
    latencies = [value for row in llm_cells for value in row["llm_latencies_ms"]]
    reliability = {
        "eligible_llm_episodes": len(llm_cells),
        "requests": sum(row["llm_requests"] for row in llm_cells),
        "errors": sum(row["llm_errors"] for row in llm_cells),
        "empty_responses": sum(row["llm_empty"] for row in llm_cells),
        "planner_parse_failures": sum(int(row["planner_parse_failures"] or 0)
                                       for row in llm_cells),
        "fallback_count": sum(int(row["planner_fallback_count"] or 0)
                              for row in llm_cells),
        "stale_plan_reuse": sum(int(row["stale_plan_reuse"] or 0)
                                for row in llm_cells),
        "pure_masked_count": sum(int(row["pure_masked_count"] or 0)
                                 for row in llm_cells),
        "latency_ms_p50": percentile(latencies, 0.5) if latencies else None,
        "latency_ms_p95": percentile(latencies, 0.95) if latencies else None,
    }
    save(out / "p1_reliability.json", reliability)
    save(out / "p1_summary.json", {
        "campaign_complete": not missing and len(cells) == len(SCENARIOS) * len(SEEDS) * len(ARMS),
        "expected_cells": len(SCENARIOS) * len(SEEDS) * len(ARMS),
        "eligible_cells": len(cells), "ineligible_or_missing": missing,
        "scenes": scene_summaries, "reliability": reliability,
        "warning": "Bootstrap intervals are exploratory; run_episode legacy fires_decoy is not authoritative after neutral IE-11 IDs. P/E/I are deployment accounting, not oracle attribution.",
    })
    print(json.dumps({"eligible_cells": len(cells), "missing": len(missing),
                      "campaign_complete": not missing and len(cells) == len(SCENARIOS) * len(SEEDS) * len(ARMS)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Audit grid Role-C episode files and summarize P1/P2/P3b without overclaiming."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import statistics

from grid_rolec6 import classify_intercepts


ARMS = ("rule-rule", "llm-rule", "rule-rl", "llm-rl", "rl", "pure-llm")
PURE = ("rule-rule", "rl", "pure-llm")
LLM_ARMS = frozenset(("llm-rule", "llm-rl", "pure-llm"))


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def mean(values):
    return statistics.mean(values) if values else None


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def seed_bootstrap(values, repetitions=10000, seed=20260928):
    if len(values) < 2:
        return {"ci95": None, "n_seed": len(values)}
    rng = random.Random(seed)
    means = [statistics.mean(rng.choices(values, k=len(values)))
             for _ in range(repetitions)]
    return {"ci95": [percentile(means, .025), percentile(means, .975)],
            "n_seed": len(values), "resamples": repetitions,
            "interpretation": "Exploratory seed bootstrap; not independent tick-level evidence."}


def accounting(v: dict[str, float]) -> dict:
    required = set(ARMS)
    if not required.issubset(v):
        return {"available": False, "missing_arms": sorted(required - set(v))}
    p = v["llm-rule"] - v["rule-rule"]
    e = v["rule-rl"] - v["rule-rule"]
    i = v["llm-rl"] - v["llm-rule"] - v["rule-rl"] + v["rule-rule"]
    winner = max(PURE, key=lambda arm: v[arm])
    vm = v[winner]
    b = vm - v["rule-rule"]
    a = p - b
    hybrid_b = p + e + i - b
    return {"available": True, "P": p, "E": e, "I": i,
            "V_m": vm, "best_pure": winner, "B": b,
            "delta_V_A": a, "delta_V_B": hybrid_b,
            "residual_A": a - (v["llm-rule"] - vm),
            "residual_B": hybrid_b - (v["llm-rl"] - vm),
            "interpretation": "Deployed-system algebra, not causal component attribution."}


def audit_llm_request_rows(rows: list[dict], conf: dict, stats: dict, spec: dict) -> list[str]:
    """Independently verify complete, ordered real-request evidence and P0 keys."""
    if conf.get("arm") not in LLM_ARMS:
        return ["unexpected_llm_requests"] if rows else []
    calls = stats.get("llm_stats", {}).get("total_calls")
    if not isinstance(calls, int) or calls < 1 or len(rows) != 2 * calls:
        return ["llm_request_response_count"]
    errors = []
    for index in range(calls):
        request, response = rows[2 * index:2 * index + 2]
        call_id = index + 1
        if (request.get("kind") != "request" or response.get("kind") != "response"
                or request.get("call_id") != call_id or response.get("call_id") != call_id):
            errors.append("llm_request_response_order")
            break
        if request.get("model") != spec.get("model") or request.get("base_url") != spec.get("base_url"):
            errors.append("llm_request_identity")
        system, user = request.get("system"), request.get("user")
        if not isinstance(system, str) or not isinstance(user, str):
            errors.append("llm_prompt_missing")
            continue
        prompt = system + "\n" + user
        if ("is_real_threat" in prompt or "real_threat" in prompt or
                re.search(r"(?i)(?:decoy|feint)[_-]\d+", prompt)):
            errors.append("llm_prompt_role_truth_key_or_id")
    return sorted(set(errors))


def audit_episode(path: Path, spec: dict) -> tuple[dict | None, list[str]]:
    errors = []
    report_path = path / "episode.json"
    if not report_path.is_file():
        return None, ["missing_report"]
    try:
        report = read(report_path)
    except (ValueError, OSError):
        return None, ["unreadable_report"]
    conf = report.get("config", {})
    if report.get("schema") != "grid-role-c-6-episode@1":
        errors.append("schema")
    if not report.get("complete") or report.get("aborted") or report.get("V") is None:
        errors.append("incomplete_or_aborted")
    if (report.get("d1", {}).get("input_role_truth_leaks") or
            report.get("d1", {}).get("prompt_role_truth_leaks")):
        errors.append("input_role_truth_leak")
    if report.get("source_hashes") != spec["source_hashes"]:
        errors.append("source_hash_mismatch")
    if report.get("instrumentation_sha256") != spec["implementation_sha256"]:
        errors.append("runner_hash_mismatch")
    for key in ("difficulty", "task_mode", "goal_mode", "plan_interval",
                "pure_call_interval", "base_url", "model", "checkpoint_sha256"):
        if conf.get(key) != spec.get(key):
            # Base URL/model/checkpoint are intentionally null in non-applicable arms.
            if not (key in ("base_url", "model") and conf.get("arm") not in
                    ("llm-rule", "llm-rl", "pure-llm") and conf.get(key) is None):
                if not (key == "checkpoint_sha256" and conf.get("arm") not in
                        ("rule-rl", "llm-rl", "rl") and conf.get(key) is None):
                    errors.append(f"config_{key}")
    if conf.get("seed") not in spec["seeds"] or conf.get("arm") not in spec["arms"]:
        errors.append("cell_not_in_campaign")
    if not (path / "events.jsonl").is_file() or report.get("events_sha256") != digest(path / "events.jsonl"):
        errors.append("events_hash")
    req = path / "requests.jsonl"
    if report.get("requests_sha256") != (digest(req) if req.exists() else None):
        errors.append("requests_hash")
    if conf.get("arm") in ("llm-rule", "llm-rl", "pure-llm") and not req.is_file():
        errors.append("missing_llm_requests")
    if errors:
        return None, errors
    try:
        request_rows = [json.loads(line) for line in req.read_text(encoding="utf-8").splitlines()] if req.exists() else []
    except (ValueError, OSError):
        return None, ["malformed_requests"]
    errors.extend(audit_llm_request_rows(request_rows, conf, report.get("agent_stats", {}), spec))
    if errors:
        return None, errors
    d1 = report["d1"]
    hit_counts = classify_intercepts(d1["intercepts_labeled_offline"],
                                     d1["truth_labeled_offline_only"])
    stats = report.get("agent_stats", {})
    llm_stats = stats.get("llm_stats", {})
    responses = [item for item in request_rows if item.get("kind") == "response"]
    elapsed = [float(item["elapsed_seconds"]) for item in responses if item.get("elapsed_seconds") is not None]
    real_transport_hits = sum(
        truth.get(item["target"], {}).get("type") == "red_transport" and item.get("is_real_threat") is True
        for item in d1["intercepts_labeled_offline"]
        for truth in (d1["truth_labeled_offline_only"],))
    return {"path": str(path), "seed": conf["seed"], "arm": conf["arm"],
            "V": float(report["V"]), "steps": report["steps"],
            "mission_success": report["metrics"].get("mission_success"),
            "feint_hits": hit_counts["feint_hits"], "real_hits": hit_counts["real_hits"],
            "scout_hits": hit_counts["scout_hits"],
            "real_transport_hits": real_transport_hits,
            "feint_total": d1["feint_total"], "real_transport_total": d1["real_transport_total"],
            "feint_observed": d1["feint_observed"],
            "real_transport_observed": d1["real_transport_observed"],
            "ammo_used": report["metrics"].get("ammo_used"),
            "port_penetrations": report["metrics"].get("port_penetrations"),
            "llm_calls": llm_stats.get("total_calls"), "llm_errors": llm_stats.get("errors"),
            "llm_empty_responses": sum(item.get("empty", False) for item in responses),
            "llm_response_records": len(responses),
            "llm_latency_p50_s": statistics.median(elapsed) if elapsed else None,
            "llm_latency_p95_s": percentile(elapsed, .95),
            "llm_fallbacks": stats.get("fallback_count"),
            "llm_masked": stats.get("masked_count"),
            "goals_proposed": sum(len(s["proposed"]) for s in report["goal_submissions"]),
            "goals_changed": sum(s["proposed"] != s["issued"] for s in report["goal_submissions"]),
            "goals_rejected": sum(len(s["receipt"].get("rejected", [])) for s in report["goal_submissions"])}, []


def analyze_matrix(root: Path) -> dict:
    spec = read(root / "campaign.json")
    if spec.get("schema") != "grid-role-c-6-matrix@1":
        raise ValueError("Not a grid Role-C matrix")
    cells, attempts = [], []
    for seed in spec["seeds"]:
        for arm in spec["arms"]:
            stem = f"{spec['difficulty']}_{spec['task_mode']}_{arm}_s{seed}_{spec['goal_mode']}"
            candidates = sorted(root.glob(stem + "_a*"), key=lambda p: int(p.name.rsplit("_a", 1)[1])
                                if p.is_dir() and p.name.rsplit("_a", 1)[1].isdigit() else 999999)
            valid = []
            for candidate in candidates:
                if not candidate.is_dir():
                    continue
                row, errors = audit_episode(candidate, spec)
                attempts.append({"path": str(candidate), "eligible": row is not None, "errors": errors})
                if row is not None:
                    valid.append(row)
            if valid:
                cells.append(valid[0])  # predeclared earliest-eligible rule
            else:
                attempts.append({"cell": stem, "eligible": False, "errors": ["no_eligible_attempt"]})
    by_seed = {}
    for seed in spec["seeds"]:
        v = {row["arm"]: row["V"] for row in cells if row["seed"] == seed}
        by_seed[str(seed)] = {"scores": v, "accounting": accounting(v),
                              "complete_six_arm": len(v) == len(ARMS)}
    arm_means = {arm: mean([r["V"] for r in cells if r["arm"] == arm])
                 for arm in spec["arms"] if sum(r["arm"] == arm for r in cells) == len(spec["seeds"])}
    formula = accounting(arm_means)
    paired = {}
    for name, left, right in (("llm_minus_rule", "llm-rule", "rule-rule"),
                              ("llmrl_minus_rulerl", "llm-rl", "rule-rl"),
                              ("A_minus_best_pure_per_seed", "llm-rule", "best_pure"),
                              ("B_minus_best_pure_per_seed", "llm-rl", "best_pure")):
        values = []
        for entry in by_seed.values():
            v = entry["scores"]
            if right == "best_pure":
                if not all(a in v for a in PURE) or left not in v:
                    continue
                reference = max(v[a] for a in PURE)
            elif left in v and right in v:
                reference = v[right]
            else:
                continue
            values.append(v[left] - reference)
        paired[name] = {"n_seed": len(values), "values": values, "mean": mean(values),
                        **seed_bootstrap(values)}
    latencies = []
    for row in cells:
        req_file = Path(row["path"]) / "requests.jsonl"
        if req_file.exists():
            latencies.extend(float(item["elapsed_seconds"]) for item in
                             (json.loads(line) for line in req_file.read_text(encoding="utf-8").splitlines())
                             if item.get("kind") == "response" and item.get("elapsed_seconds") is not None)
    formula_ci = {}
    full = [(seed, entry["scores"]) for seed, entry in by_seed.items()
            if entry["complete_six_arm"]]
    if len(full) >= 2:
        rng = random.Random(20260928)
        draws = {key: [] for key in ("P", "E", "I", "B", "delta_V_A", "delta_V_B")}
        for _ in range(10000):
            sample = rng.choices(full, k=len(full))
            means = {arm: statistics.mean(item[1][arm] for item in sample) for arm in ARMS}
            calc = accounting(means)
            for key in draws:
                draws[key].append(calc[key])
        formula_ci = {key: [percentile(values, .025), percentile(values, .975)]
                      for key, values in draws.items()}
    return {"schema": "grid-role-c-6-analysis@1", "campaign": str(root),
            "expected": len(spec["seeds"]) * len(spec["arms"]), "eligible": len(cells),
            "attempts": attempts, "cells": cells, "by_seed": by_seed,
            "arm_means_complete_arms_only": arm_means, "formula": formula,
            "formula_exploratory_seed_bootstrap_ci95": formula_ci,
            "paired": paired,
            "d1": {arm: {"n": len([r for r in cells if r["arm"] == arm]),
                           "feint_hits": sum(r["feint_hits"] for r in cells if r["arm"] == arm),
                           "feint_hit_per_observed": (
                               sum(r["feint_hits"] for r in cells if r["arm"] == arm) /
                               sum(r["feint_observed"] for r in cells if r["arm"] == arm))
                               if sum(r["feint_observed"] for r in cells if r["arm"] == arm) else None,
                           "real_hits": sum(r["real_hits"] for r in cells if r["arm"] == arm),
                           "real_transport_hits": sum(r["real_transport_hits"] for r in cells if r["arm"] == arm),
                           "feints_observed": sum(r["feint_observed"] for r in cells if r["arm"] == arm)}
                   for arm in spec["arms"]},
            "reliability": {"llm_calls": sum(r["llm_calls"] or 0 for r in cells),
                            "llm_errors": sum(r["llm_errors"] or 0 for r in cells),
                            "llm_empty_responses": sum(r["llm_empty_responses"] for r in cells),
                            "llm_response_records": sum(r["llm_response_records"] for r in cells),
                            "latency_p50_s": percentile(latencies, .5),
                            "latency_p95_s": percentile(latencies, .95),
                            "llm_fallbacks": sum(r["llm_fallbacks"] or 0 for r in cells)},
            "limits": ["seed is the sampling unit; no tick-level pseudo-replication",
                       "feint hits are behavioral proxy, not detection accuracy",
                       "P/E/I are deployment accounting, not oracle attribution",
                       "conditional-law mechanism requires separate Goal intervention"]}


def analyze_fault(path: Path) -> dict:
    data = read(path)
    rows = data.get("rows", [])
    valid = bool(data.get("all_own_replays_valid") and rows and
                 all(r.get("original_valid") and r.get("replay_valid") for r in rows))
    by_seed: dict[int, dict[str, dict]] = {}
    for row in rows:
        by_seed.setdefault(row["seed"], {})[row["cell"]] = row
    contrasts = []
    if valid:
        for seed, cells in sorted(by_seed.items()):
            if not all(label in cells for label in ("clean", "planner", "executor", "both")):
                valid = False
                break
            v = {label: cells[label]["original"]["V"] for label in cells}
            contrasts.append({"seed": seed, "planning_fault_loss": v["clean"] - v["planner"],
                              "execution_fault_loss": v["clean"] - v["executor"],
                              "both_fault_loss": v["clean"] - v["both"],
                              "nonadditivity": v["both"] - v["planner"] - v["executor"] + v["clean"],
                              "planner_events": cells["planner"]["original"]["planner_events"],
                              "executor_events": cells["executor"]["original"]["executor_events"]})
    estimates = {}
    if valid:
        for key in ("planning_fault_loss", "execution_fault_loss", "both_fault_loss",
                    "nonadditivity"):
            values = [row[key] for row in contrasts]
            estimates[key] = {"mean": mean(values), "positive_seeds": sum(v > 0 for v in values),
                              "zero_seeds": sum(v == 0 for v in values),
                              "negative_seeds": sum(v < 0 for v in values),
                              **seed_bootstrap(values)}
    return {"replay_gate_pass": valid, "known_fault_contrasts": contrasts if valid else [],
            "estimates": estimates,
            "oracle_attribution_validated": False,
            "interpretation": "Known-fault localization only; not independently validated oracle decomposition."}


def compare_goal_matrices(first: dict, second: dict) -> dict:
    a, b = read(Path(first["campaign"]) / "campaign.json"), read(Path(second["campaign"]) / "campaign.json")
    for key in ("source_hashes", "implementation_sha256", "difficulty", "task_mode",
                "checkpoint_sha256", "seeds", "model", "base_url", "plan_interval",
                "pure_call_interval", "max_steps"):
        if a.get(key) != b.get(key):
            raise ValueError(f"P2 matrices differ in {key}")
    if {a["goal_mode"], b["goal_mode"]} != {"strong", "hold"}:
        raise ValueError("P2 requires one strong and one hold matrix")
    strong, hold = (first, second) if a["goal_mode"] == "strong" else (second, first)
    strong_cells = {(r["seed"], r["arm"]): r for r in strong["cells"]}
    hold_cells = {(r["seed"], r["arm"]): r for r in hold["cells"]}
    pairs = []
    for (seed, arm), sr in sorted(strong_cells.items()):
        if arm not in ("rule-rl", "llm-rl") or (seed, arm) not in hold_cells:
            continue
        hr = hold_cells[(seed, arm)]
        s_events = [json.loads(line) for line in (Path(sr["path"]) / "events.jsonl").read_text(
            encoding="utf-8").splitlines()]
        h_events = [json.loads(line) for line in (Path(hr["path"]) / "events.jsonl").read_text(
            encoding="utf-8").splitlines()]
        first_action_difference = next((x["step"] for x, y in zip(s_events, h_events)
                                        if x["actions"] != y["actions"]), None)
        pairs.append({"seed": seed, "arm": arm, "V_strong": sr["V"], "V_hold": hr["V"],
                      "delta_V_strong_minus_hold": sr["V"] - hr["V"],
                      "first_action_difference_step": first_action_difference,
                      "strong_goal_submissions": sr["goals_proposed"],
                      "hold_changed_submissions": hr["goals_changed"],
                      "hold_rejected_goals": hr["goals_rejected"],
                      "common_prefix_steps": min(len(s_events), len(h_events))})
    by_arm = {arm: [p["delta_V_strong_minus_hold"] for p in pairs if p["arm"] == arm]
              for arm in ("rule-rl", "llm-rl")}
    return {"pairs": pairs, "mean_delta_by_arm": {arm: mean(values)
                for arm, values in by_arm.items()},
            "delta_by_arm": {arm: {"mean": mean(values),
                                   "positive_seeds": sum(v > 0 for v in values),
                                   "zero_seeds": sum(v == 0 for v in values),
                                   "negative_seeds": sum(v < 0 for v in values),
                                   **seed_bootstrap(values)}
                             for arm, values in by_arm.items()},
            "manipulation_pass": bool(pairs and all(p["hold_changed_submissions"] > 0
                                                     and p["hold_rejected_goals"] == 0
                                                     and p["first_action_difference_step"] is not None
                                                     for p in pairs)),
            "interpretation": "Full-episode Goal hold ablation. Rule-RL is deterministic check; LLM-RL future prompts may diverge. Not local causal MI or B_if bits."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fault-summary", type=Path)
    parser.add_argument("--goal-comparator", type=Path,
                        help="Other matrix with the same cells and opposite Goal mode")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new analysis output directory")
    summary = analyze_matrix(args.matrix.resolve())
    if args.goal_comparator:
        other = analyze_matrix(args.goal_comparator.resolve())
        summary["p2"] = compare_goal_matrices(summary, other)
    if args.fault_summary:
        summary["p3b"] = analyze_fault(args.fault_summary.resolve())
    args.output.mkdir(parents=True)
    write(args.output / "summary.json", summary)
    if summary["cells"]:
        with (args.output / "cells.csv").open("x", newline="", encoding="utf-8-sig") as out:
            columns = list(summary["cells"][0])
            writer = csv.DictWriter(out, fieldnames=columns)
            writer.writeheader()
            writer.writerows(summary["cells"])
    print(json.dumps({"expected": summary["expected"], "eligible": summary["eligible"],
                      "formula_available": summary["formula"]["available"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

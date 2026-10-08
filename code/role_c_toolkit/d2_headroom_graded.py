"""D2 headroom measured on the scenario's *declared* composite (graded), not on binary success.

Why this exists: the binary gate (`d2_headroom.py`) reads ``terminal.outcome``, which is one
bit per deterministic scripted policy and therefore almost always 0 or 1 across seeds.  The
competition scenarios already declare a graded utility (``scoring: aggregation=sum,
weight_policy=normalized_sum_one``, ``aggregation_version=utility-v1``), and the evidence
reports carry every per-metric value, so headroom can be measured on the quantity the
scenarios were built to express.

Contract kept from the binary analyzer: success/score is read from machine-written evidence,
seeds are the sampling unit, a case without a terminal is unusable rather than a zero, and
missing metric values are reported instead of being imputed.

Usage:
    python d2_headroom_graded.py --state <plan.state.json> --scenarios <scenarios root> \
        [--plan <plan.json>] --output <d2_graded.json> [--csv <d2_graded_per_case.csv>]
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import d2_headroom as binary
import yaml

D2_LOW, D2_HIGH = 0.40, 0.85
# Weight of a metric that a report did not record.  A metric that is absent is not zero (the
# engine marks unavailable metrics N/A), so the composite is normalised over what existed and
# the coverage is reported next to it.
COMPOSITE_MIN_COVERAGE = 0.5


def contract_key(scenario_id: str, difficulty: str | None, package_dir: Path | None = None) -> str:
    """REC-001 has one package per difficulty, so the difficulty belongs in the key."""
    if scenario_id == "MD-REC-001" and difficulty:
        return f"{scenario_id}-{difficulty.upper()}"
    return scenario_id


def package_for(scenarios_root: Path, scenario_id: str, difficulty: str | None) -> Path | None:
    prefix = scenario_id.lower().replace("-", "_")
    candidates = []
    if scenario_id == "MD-REC-001" and difficulty:
        candidates.append(scenarios_root / f"{prefix}_{difficulty}")
    candidates.extend(sorted(p for p in scenarios_root.glob(prefix + "*") if p.is_dir()))
    for candidate in candidates:
        if (candidate / "scenario.yaml").is_file():
            return candidate
    return None


def scoring_policy(package_dir: Path) -> dict:
    payload = yaml.safe_load((package_dir / "scenario.yaml").read_text(encoding="utf-8"))
    scoring = (payload.get("scenario") or {}).get("scoring") or {}
    metrics = scoring.get("metrics") or []
    if not isinstance(metrics, list):
        raise ValueError(f"unexpected scoring.metrics shape in {package_dir}")
    weights = {}
    for item in metrics:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        weights[str(item["id"])] = {
            "weight": float(item.get("weight") or 0.0),
            "direction": item.get("direction") or scoring.get("direction") or "maximize",
            "aggregation": item.get("aggregation"),
        }
    total = sum(entry["weight"] for entry in weights.values())
    return {
        "weights": weights,
        "weight_sum": round(total, 9),
        "aggregation": scoring.get("aggregation"),
        "aggregation_version": scoring.get("aggregation_version"),
        "weight_policy": scoring.get("weight_policy"),
    }


def composite_of(scores: dict, policy: dict) -> dict:
    """Σ wᵢ·valueᵢ over the metrics the report actually recorded.

    ``value`` is used for maximised metrics and ``1 - value`` for minimised ones, matching the
    engine's ``utility-v1`` semantics.  The result is renormalised by the covered weight, and
    coverage is returned so a partial report cannot masquerade as a full composite.
    """
    parts, covered = {}, 0.0
    for metric_id, entry in policy["weights"].items():
        value = scores.get(metric_id)
        if value is None:
            value = scores.get(metric_id.split(".", 1)[-1])
        if not isinstance(value, (int, float)):
            continue
        term = float(value)
        if entry["direction"] == "minimize":
            term = 1.0 - term
        parts[metric_id] = round(term, 6)
        covered += entry["weight"]
    if not parts:
        return {"composite": None, "covered_weight": 0.0, "terms": {},
                "missing_metrics": sorted(policy["weights"])}
    raw = sum(policy["weights"][metric_id]["weight"] * term for metric_id, term in parts.items())
    return {
        "composite": round(raw / covered, 6) if covered > 0 else None,
        "covered_weight": round(covered, 6),
        "terms": parts,
        "missing_metrics": sorted(set(policy["weights"]) - set(parts)),
    }


def family_of(scenario_id: str) -> str:
    """Family code from the contract id's own segment.

    A plain substring test is wrong here: ``INTERCEPTION-ENGAGEMENT`` contains ``ER``.
    """
    segments = scenario_id.upper().split("-")
    for index, segment in enumerate(segments):
        if segment in {"REC", "TRK", "AD", "ER"} and index + 1 < len(segments) \
                and segments[index + 1].isdigit():
            return segment
    return "?"


def bootstrap_ci(values: list[float], draws: int = 10000, rng_seed: int = 20261003) -> list:
    return binary.bootstrap_ci(values, draws, rng_seed)


def analyse(rows: list[dict], policies: dict, keys: dict) -> dict:
    per_scenario: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    unusable, no_policy = [], []
    for row in rows:
        key = keys.get(row["case_id"])
        policy = policies.get(key)
        if policy is None:
            no_policy.append(row["case_id"])
            continue
        if not row["full_episode_completed"]:
            unusable.append(row["case_id"])
            continue
        entry = composite_of(row.get("scores") or {}, policy)
        if entry["composite"] is None:
            unusable.append(row["case_id"])
            continue
        per_scenario[key][row["policy"]].append({
            "case_id": row["case_id"], "seed": row["seed"], "policy": row["policy"],
            "composite": entry["composite"], "covered_weight": entry["covered_weight"],
            "missing_metrics": entry["missing_metrics"],
            "binary_success": row["success"], "outcome": row["outcome"],
        })
    scenarios = {}
    scored_cases = []
    for key, by_policy in sorted(per_scenario.items()):
        policy_rows = {}
        for name, cases in sorted(by_policy.items()):
            values = [case["composite"] for case in cases]
            binaries = [1.0 if case["binary_success"] else 0.0 for case in cases]
            for case in cases:
                scored_cases.append({**case, "scenario_key": key})
            policy_rows[name] = {
                "cases": len(cases),
                "composite_mean": round(sum(values) / len(values), 4),
                "composite_ci95": bootstrap_ci(values),
                "composite_min": min(values), "composite_max": max(values),
                "binary_success_rate": round(sum(binaries) / len(binaries), 3),
                "covered_weight": cases[0]["covered_weight"],
                "missing_metrics": sorted({m for case in cases for m in case["missing_metrics"]}),
                "is_floor_control": name in binary.FLOOR_POLICIES,
            }
        usable = {name: value for name, value in policy_rows.items()
                  if value["composite_mean"] is not None}
        best = max(usable.items(), key=lambda item: (item[1]["composite_mean"], item[0]))
        # The same maximum restricted to task-relevant policies: a floor control (idle /
        # indiscriminate / naive) can sit at the ceiling and would otherwise hide the fact
        # that no task-relevant baseline reaches it.
        relevant = {name: value for name, value in usable.items()
                    if not value["is_floor_control"]}
        best_relevant = (max(relevant.items(), key=lambda item: (item[1]["composite_mean"],
                                                                 item[0]))
                         if relevant else None)
        entry = {
            "policies": policy_rows,
            "best_baseline_policy": best[0],
            "best_composite_mean": best[1]["composite_mean"],
            "best_composite_ci95": best[1]["composite_ci95"],
            "best_binary_success_rate": best[1]["binary_success_rate"],
            "best_task_relevant_policy": best_relevant[0] if best_relevant else None,
            "best_task_relevant_composite": (best_relevant[1]["composite_mean"]
                                             if best_relevant else None),
            "best_is_floor_control": best[1]["is_floor_control"],
            "d2_graded_verdict": ("pass" if D2_LOW <= best[1]["composite_mean"] <= D2_HIGH
                                  else "fail"),
            "binary_verdict": ("pass" if D2_LOW <= best[1]["binary_success_rate"] <= D2_HIGH
                               else "fail"),
        }
        # Headroom for the family-level decision: a scenario counts as carrying measurable
        # headroom when a *task-relevant* baseline still leaves room below the ceiling.
        headroom_source = (best_relevant[1]["composite_mean"] if best_relevant
                           else best[1]["composite_mean"])
        entry["headroom_basis"] = ("task-relevant baseline" if best_relevant
                                   else "only floor controls recorded")
        entry["headroom_composite"] = headroom_source
        entry["headroom_band"] = ("below_window" if headroom_source < D2_LOW
                                  else "window" if headroom_source <= D2_HIGH
                                  else "near_ceiling")
        scenarios[key] = entry
    verdicts = [entry["d2_graded_verdict"] for entry in scenarios.values()]
    bands = {band: sum(1 for entry in scenarios.values() if entry["headroom_band"] == band)
             for band in ("below_window", "window", "near_ceiling")}
    families = {}
    for key, entry in scenarios.items():
        family = family_of(key)
        bucket = families.setdefault(family, {"scenarios": 0, "in_window": 0,
                                              "near_ceiling": 0, "floor_pick": 0})
        bucket["scenarios"] += 1
        bucket["in_window"] += 1 if entry["headroom_band"] == "window" else 0
        bucket["near_ceiling"] += 1 if entry["headroom_band"] == "near_ceiling" else 0
        bucket["floor_pick"] += 1 if entry["best_is_floor_control"] else 0
    families_sorted = dict(sorted(families.items()))
    families_meeting = [code for code, bucket in families_sorted.items()
                        if code != "?" and bucket["in_window"] >= 3]
    return {
        "schema": "e4-d2-headroom-graded@1",
        "measurement": ("declared composite: Σ wᵢ·valueᵢ over the metrics present, renormalised "
                        "by covered weight; minimised metrics enter as 1 - value"),
        "gate": {"low": D2_LOW, "high": D2_HIGH,
                 "operationalisation": "best pure baseline composite within [0.40, 0.85]",
                 "note": ("graded companion to the pre-registered binary gate; the binary result "
                          "stays on record and both are reported")},
        "n_cases": len(rows),
        "n_unusable": len(unusable),
        "unusable_cases": unusable,
        "cases_without_policy": no_policy,
        "scenarios": scenarios,
        "counts": {
            "scenarios": len(scenarios),
            "graded_pass": verdicts.count("pass"),
            "graded_fail": verdicts.count("fail"),
            "binary_pass": sum(1 for entry in scenarios.values()
                               if entry["binary_verdict"] == "pass"),
            "near_ceiling": bands["near_ceiling"],
            "in_window": bands["window"],
            "below_window": bands["below_window"],
            "best_baseline_is_floor_control": sum(1 for entry in scenarios.values()
                                                  if entry["best_is_floor_control"]),
        },
        "headroom_bands": bands,
        "by_family": families_sorted,
        "families_with_three_in_window": families_meeting,
        "score_policies": policies,
        "scored_cases": scored_cases,
    }


def cases_from_evidence(rows: list[dict], evidence_roots) -> list[dict]:
    """Attach the recorded per-metric scores to each already-loaded row.

    ``evidence`` paths inside a state file are relative to the project root that produced
    them, so the lookup also tries the bare filename under each evidence root; a case whose
    report cannot be found keeps an empty score dict and is later reported as unusable
    rather than silently scored zero.
    """
    roots = [evidence_roots] if isinstance(evidence_roots, (str, Path)) else list(evidence_roots)
    roots = [Path(root) for root in roots] or [Path(".")]
    for row in rows:
        recorded = Path(row["evidence"] or "")
        candidates = [recorded]
        for root in roots:
            candidates.extend([root / recorded, root / recorded.name])
        row["scores"] = {}
        for candidate in candidates:
            if candidate.is_file():
                row["scores"] = (json.loads(candidate.read_text(encoding="utf-8"))
                                 .get("scores") or {})
                break
    return rows


def per_case_csv(scored_cases: list[dict]) -> str:
    lines = ["case_id,scenario_key,policy,seed,composite,covered_weight,binary_success,outcome"]
    for case in sorted(scored_cases, key=lambda item: item["case_id"]):
        lines.append(",".join(str(case.get(key)) for key in
                              ("case_id", "scenario_key", "policy", "seed", "composite",
                               "covered_weight", "binary_success", "outcome")))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, action="append", required=True,
                        help="repeat once per seed plan, in the same order as --plan")
    parser.add_argument("--plan", type=Path, action="append",
                        help="repeat once per seed plan; several plans merge seed-major")
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, action="append",
                        help="directory holding the per-case evidence reports; repeat to add "
                             "more roots (each seed writes into the same artifacts folder)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if args.plan and len(args.plan) != len(args.state):
        raise SystemExit("provide one --state per --plan")

    if args.plan:
        plan, state, merge = binary.merge_plans(args.plan, args.state)
    else:
        plan, plan_path = None, None
        states = [binary.load(path) for path in args.state]
        merged_cases = {}
        for payload in states:
            for case_id, entry in payload["cases"].items():
                merged_cases.setdefault(case_id, entry)
        state = {"cases": merged_cases}
        merge = {"plans": [], "states": [str(path) for path in args.state],
                 "cases": len(merged_cases), "duplicate_case_ids": []}
    rows = binary.cases_from_state(state, plan)
    keys, policy_by_key, difficulty_by_case = {}, {}, {}
    for case in (plan or {}).get("cases", []):
        key = contract_key(case.get("scenario_id"), case.get("difficulty"))
        keys[case["case_id"]] = key
        difficulty_by_case[case["case_id"]] = case.get("difficulty")
        if key not in policy_by_key:
            package = package_for(args.scenarios, case["scenario_id"], case.get("difficulty"))
            policy_by_key[key] = scoring_policy(package) if package else None
    for row in rows:
        row["scenario_key"] = keys.get(row["case_id"])
        if row["scenario_key"] is None:
            row["scenario_key"] = contract_key(row.get("scenario_id") or "",
                                               difficulty_by_case.get(row["case_id"]))
    rows = cases_from_evidence(rows, args.evidence_root or [])
    policies = {key: value for key, value in policy_by_key.items() if value}
    summary = analyse(rows, policies, keys or {row["case_id"]: row["scenario_key"]
                                               for row in rows})
    summary["state"] = merge["states"] if len(merge["states"]) > 1 else merge["states"][0]
    summary["plan"] = merge["plans"] or None
    summary["merged_inputs"] = merge
    summary["evidence_root"] = [str(root) for root in (args.evidence_root or [])]
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    if args.csv:
        args.csv.write_text(per_case_csv(summary["scored_cases"]), encoding="utf-8")
    print(json.dumps({"cases": summary["n_cases"], "unusable": summary["n_unusable"],
                      "counts": summary["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

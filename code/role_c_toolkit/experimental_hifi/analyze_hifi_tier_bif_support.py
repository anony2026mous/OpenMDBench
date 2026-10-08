"""Exploratory pooled-seed support audit for audited HIFI Goal-tier traces.

This does not promote the rule-planner interface baseline to hybrid evidence.
It reuses the predeclared projected mixed Goal→state estimator and records null
when its category/density support conditions fail.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from hifi_mixed_bif_pilot import extract
from hifi_trace import file_hash
from mixed_chain_information import mixed_goal_state_mi

TIERS = ("weak", "medium", "strong")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(labels, x, y, k, min_group):
    try:
        return mixed_goal_state_mi(labels, np.asarray(x, dtype=float), np.asarray(y, dtype=float),
                                   k=k, min_group=min_group)
    except Exception as exc:
        return {"estimate": None, "unavailable_reason": f"{type(exc).__name__}:{exc}",
                "k": k, "n": len(labels), "units": "bits"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", required=True, type=Path)
    ap.add_argument("--pair-audits", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--scenarios", nargs="+", default=["IE-01", "IE-02"])
    ap.add_argument("--min-group", type=int, default=20)
    args = ap.parse_args()
    campaign, audits, output = args.campaign.resolve(), args.pair_audits.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(campaign) or campaign.is_relative_to(output):
        raise ValueError("Output must be new and outside immutable campaign")
    if args.min_group < 2:
        raise ValueError("min-group must be at least 2")
    progress = read(campaign / "progress.json")
    rows_by_key = {(r["alias"], r["seed"], r["tier"]): r for r in progress}
    scenarios = []
    for scenario in args.scenarios:
        seeds = sorted({seed for alias, seed, _ in rows_by_key if alias == scenario})
        complete_seeds = []
        for seed in seeds:
            triplet = [rows_by_key.get((scenario, seed, tier)) for tier in TIERS]
            if all(r and r.get("original_valid") and r.get("replay_valid") for r in triplet):
                valid = True
                for tier, row in zip(TIERS, triplet):
                    audit_path = audits / scenario / f"seed-{seed}" / tier / "audit.json"
                    report_path = Path(row["original"]["report_path"])
                    if not audit_path.is_file() or not report_path.is_file():
                        valid = False
                        break
                    audit = read(audit_path)
                    if (audit.get("errors") or audit.get("exact_terminal_pair_passed") is not True or
                            audit.get("original_report_sha256") != file_hash(report_path)):
                        valid = False
                        break
                if valid:
                    complete_seeds.append(seed)
        tier_results = []
        for tier in TIERS:
            pooled = {}
            provenance = []
            for seed in complete_seeds:
                row = rows_by_key[(scenario, seed, tier)]
                report_path = Path(row["original"]["report_path"])
                ticks, units = extract(report_path)
                provenance.append({"seed": seed, "report": str(report_path),
                                   "report_sha256": file_hash(report_path), "ticks": ticks})
                for uid, data in units.items():
                    target = pooled.setdefault(uid, {"labels": [], "x": [], "y": [], "per_seed": []})
                    target["labels"].extend(data["labels"])
                    target["x"].extend(data["goal_continuous"])
                    target["y"].extend(data["state_continuous"])
                    target["per_seed"].append({"seed": seed, "n": len(data["labels"])})
            unit_results = []
            for uid, data in sorted(pooled.items()):
                labels, x, y = data["labels"], np.asarray(data["x"], dtype=float), np.asarray(data["y"], dtype=float)
                counts = Counter(labels)
                n = len(labels)
                k_calibrated = max(2, int(math.ceil(n ** 0.40)))
                joint = np.column_stack((x, y))
                unit_results.append({
                    "unit_id": uid, "n_transition_rows": n,
                    "per_seed_rows": data["per_seed"],
                    "goal_category_count": len(counts),
                    "goal_category_min_support": min(counts.values()) if counts else 0,
                    "goal_category_max_support": max(counts.values()) if counts else 0,
                    "unique_goal_numeric_rows": int(len(np.unique(x, axis=0))),
                    "unique_state_numeric_rows": int(len(np.unique(y, axis=0))),
                    "repeated_joint_numeric_rows": int(n - len(np.unique(joint, axis=0))),
                    "calibrated_k_n_pow_0_40": k_calibrated,
                    "estimate_k_n_pow_0_40": fit(labels, x, y, k_calibrated, args.min_group),
                    "sensitivity_k_5": fit(labels, x, y, 5, args.min_group),
                })
            tier_results.append({"tier": tier, "pooled_seed_count": len(complete_seeds),
                                 "provenance": provenance, "units": unit_results})
        scenarios.append({"scenario_alias": scenario, "complete_audited_seed_triplets": complete_seeds,
                          "tiers": tier_results})
    script_hashes = {p.name: sha(p) for p in (
        Path(__file__), Path(__file__).with_name("hifi_mixed_bif_pilot.py"),
        Path(__file__).with_name("mixed_chain_information.py"),
        Path(__file__).with_name("mixed_measure_information.py"),
        Path(__file__).with_name("information.py"))}
    estimable = sum(u["estimate_k_n_pow_0_40"]["estimate"] is not None
                    for s in scenarios for t in s["tiers"] for u in t["units"])
    unit_count = sum(len(t["units"]) for s in scenarios for t in s["tiers"])
    result = {"schema": "role-c-hifi-tier-bif-support-audit@1",
              "campaign": str(campaign), "campaign_progress_sha256": sha(campaign / "progress.json"),
              "pair_audits_root": str(audits), "scenarios": scenarios,
              "projection": "I((goal_category,priority+target_xyz);post-tick(position+velocity+energy)), per unit",
              "primary_estimator": "Ross + stratified KSG-1 chain; calibrated k=ceil(n^0.40), min category-group n=20",
              "sensitivity_estimator": "same chain with fixed k=5; exploratory only",
              "implementation_hashes": script_hashes,
              "estimable_unit_cells": estimable, "unit_cells": unit_count,
              "formal_B_if_validated": False, "formal_D3_passed": False,
              "causal_interpretation": False,
              "limitations": [
                  "Campaign traces are planner=rule interface-baseline trajectories, not LLM+GOAI hybrid.",
                  "Pooling seed episodes increases category support but does not remove within-episode temporal dependence.",
                  "The projected variables omit parts of structured Goal and execution state; this is not full B_if.",
                  "Null estimates are support/density failures, not zero mutual information.",
                  "This is an exploratory reanalysis of already collected traces, not a pre-registered confirmatory test."]}
    output.mkdir(parents=True)
    (output / "support_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"scenarios": [{"alias": s["scenario_alias"], "seeds": s["complete_audited_seed_triplets"],
                                     "tier_estimability": {t["tier"]: sum(u["estimate_k_n_pow_0_40"]["estimate"] is not None for u in t["units"]) for t in s["tiers"]}}
                                    for s in scenarios], "estimable_unit_cells": estimable, "unit_cells": unit_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()

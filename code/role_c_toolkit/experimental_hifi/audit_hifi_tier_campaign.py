"""Independent whole-episode goal-tier replay and first-anchor audit."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from audit_hifi_pair import verify_pair
from hifi_trace import file_hash


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def first_transition(path):
    for line in path.with_name("events.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        if row.get("kind") == "transition":
            return row
    raise ValueError(f"No transition in {path}")


def defender_actions(path):
    actions = {}
    for line in path.with_name("events.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        if row.get("kind") == "transition":
            actions[row["tick"]] = [entry["batch"] for entry in row["action_batches"]
                                    if entry["batch"]["faction_id"] == "coalition.defender"]
    return actions


def nested(first, second):
    a = {cmd["task_id"]: cmd for cmd in first["commands"]}
    b = {cmd["task_id"]: cmd for cmd in second["commands"]}
    if set(a) != set(b):
        return False
    return all(a[k]["goal_type"] == b[k]["goal_type"] and
               all(key in b[k]["parameters"] and b[k]["parameters"][key] == value
                   for key, value in a[k]["parameters"].items()) for k in a)


def audit(root):
    summary = read(root / "summary.json")
    errors, rows, manifests = [], [], []
    groups = defaultdict(dict)
    for entry in summary["entries"]:
        key = (entry["scenario"], entry["seed"], entry["tier"])
        paths = []
        for kind in ("original", "replay"):
            meta = entry.get(kind)
            if not meta:
                errors.append(f"missing_{kind}:{key}")
                break
            path = Path(meta["report_path"])
            if not path.exists() or file_hash(path) != meta["report_sha256"]:
                errors.append(f"report_hash:{kind}:{key}")
                break
            paths.append(path)
        if len(paths) != 2:
            continue
        pair = verify_pair(*paths)
        if pair["errors"]:
            errors.extend(f"{key}:{error}" for error in pair["errors"])
        original, replay = read(paths[0]), read(paths[1])
        manifests.extend([original["source_hashes"], replay["source_hashes"]])
        for report in (original, replay):
            if (report.get("goal_tier", {}).get("tier") != entry["tier"] or
                    report.get("goal_tier", {}).get("wrapper_sha256") != summary["tier_wrapper_sha256"]):
                errors.append(f"tier_spec:{key}")
        engine = read(paths[0].with_name("engine_result.json"))
        score = engine.get("strategy_scorecard", {}).get("defender_score")
        if score is None:
            errors.append(f"missing_score:{key}")
        if not pair["exact_terminal_pair_passed"]:
            errors.append(f"terminal_or_replay:{key}")
        row = {"scenario": entry["scenario"], "seed": entry["seed"], "tier": entry["tier"],
               "defender_score": score, "ticks": original["ticks_run"],
               "decision_count": len(original["decisions"]),
               "first_decision": original["decisions"][0] if original["decisions"] else None,
               "first_own_before": first_transition(paths[0])["own_before"],
               "defender_actions": defender_actions(paths[0]),
               "fingerprints": original["fingerprints"],
               "broker_goals_accepted": engine.get("defender", {}).get("broker", {}).get("goals_accepted"),
               "broker_goals_rejected": engine.get("defender", {}).get("broker", {}).get("goals_rejected")}
        rows.append({k: v for k, v in row.items() if k not in ("first_decision", "first_own_before", "fingerprints", "defender_actions")})
        if entry["tier"] in groups[(entry["scenario"], entry["seed"])]:
            errors.append(f"duplicate_tier:{key}")
        groups[(entry["scenario"], entry["seed"])][entry["tier"]] = row
    if manifests and any(m != manifests[0] for m in manifests[1:]):
        errors.append("source_manifest_mismatch")
    comparisons = []
    for (scenario, seed), group in sorted(groups.items()):
        if set(group) != {"weak", "medium", "strong"}:
            errors.append(f"missing_tier:{scenario}:{seed}")
            continue
        weak, medium, strong = [group[t] for t in ("weak", "medium", "strong")]
        same_anchor = weak["first_own_before"] == medium["first_own_before"] == strong["first_own_before"]
        if not same_anchor:
            errors.append(f"first_own_anchor_mismatch:{scenario}:{seed}")
        if any(item["first_decision"] is None for item in (weak, medium, strong)):
            errors.append(f"missing_first_decision:{scenario}:{seed}")
            nesting = None
        else:
            nesting = nested(weak["first_decision"], medium["first_decision"]) and nested(
                medium["first_decision"], strong["first_decision"])
            if not nesting:
                errors.append(f"first_goal_fields_not_nested:{scenario}:{seed}")
        def first_diff(a, b):
            n = min(len(a), len(b))
            return next((i for i in range(n) if a[i] != b[i]), n if len(a) != len(b) else None)
        def action_diff(a, b):
            common = sorted(set(a) & set(b))
            differing = [tick for tick in common if a[tick] != b[tick]]
            return {"shared_ticks": len(common), "first_different_tick": differing[0] if differing else None,
                    "different_shared_ticks": len(differing),
                    "trajectory_lengths": [len(a), len(b)]}
        comparisons.append({"scenario": scenario, "seed": seed,
                            "same_first_own_anchor": same_anchor,
                            "first_goal_fields_nested": nesting,
                            "first_weak_medium_fingerprint_diff_index": first_diff(weak["fingerprints"], medium["fingerprints"]),
                            "first_medium_strong_fingerprint_diff_index": first_diff(medium["fingerprints"], strong["fingerprints"]),
                            "weak_medium_defender_action_difference": action_diff(weak["defender_actions"], medium["defender_actions"]),
                            "medium_strong_defender_action_difference": action_diff(medium["defender_actions"], strong["defender_actions"]),
                            "scores": {t: group[t]["defender_score"] for t in ("weak", "medium", "strong")}})
    return {"schema": "role-c-hifi-goal-tier-campaign-audit@1",
            "campaign": str(root.resolve()), "errors": errors,
            "pairs_checked": len(rows), "rows": rows, "comparisons": comparisons,
            "formal_D3_passed": False, "formal_B_if_validated": False,
            "limitations": ["Initial goal nesting and divergent trajectories are manipulation checks, not MI gradients.",
                            "Full B_if requires predeclared representation, calibrated estimator and seed-level variance."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, output = args.campaign.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("New audit directory outside campaign required")
    result = audit(root)
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"errors": result["errors"], "pairs_checked": result["pairs_checked"],
                      "comparisons": result["comparisons"]}, ensure_ascii=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare audited strong/weak (or medium) 6.0 Goal campaigns by paired seed."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def load_campaign(path: Path) -> tuple[dict, dict, dict]:
    config = json.loads((path / "toolkit_config.json").read_text(encoding="utf-8"))
    provenance = json.loads((path / "provenance.json").read_text(encoding="utf-8"))
    summary = json.loads((path / "p1_summary.json").read_text(encoding="utf-8"))
    rows = {}
    with (path / "p1_cells.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rows[(row["scenario"], int(row["seed"]), row["arm"])] = row
    return config, provenance, {"summary": summary, "rows": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strong", required=True, type=Path)
    p.add_argument("--other", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    strong, source_a, a = load_campaign(args.strong)
    other, source_b, b = load_campaign(args.other)
    if strong["goal_granularity"] != "strong" or other["goal_granularity"] == "strong":
        p.error("Pass a strong campaign and a weak/medium campaign")
    if not set(other["scenarios"]).issubset(strong["scenarios"]):
        p.error("Other-tier scenes must be included in the strong campaign")
    for field in ("seeds", "base_url", "model", "plan_interval",
                  "decision_interval", "max_ticks", "llm_max_tokens"):
        if strong[field] != other[field]:
            p.error(f"Frozen campaigns differ in {field}")
    for field in ("code_bundle_sha256", "score_code_sha256"):
        if source_a[field] != source_b[field]:
            p.error(f"Source provenance differs in {field}")
    if {k: v["sha256"] for k, v in source_a["checkpoints"].items()} != {
            k: v["sha256"] for k, v in source_b["checkpoints"].items()}:
        p.error("Checkpoint hashes differ")
    by_arm = {}
    for scene in other["scenarios"]:
        for arm in ("rule-rl", "llm-rl"):
            differences = []
            for seed in strong["seeds"]:
                key = (scene, seed, arm)
                if key in a["rows"] and key in b["rows"]:
                    differences.append({"seed": seed,
                                        "strong_minus_other": float(a["rows"][key]["defender_score"])
                                        - float(b["rows"][key]["defender_score"])})
            by_arm[f"{scene}/{arm}"] = {
                "eligible_pairs": len(differences), "expected_pairs": len(strong["seeds"]),
                "mean_difference": statistics.mean(x["strong_minus_other"] for x in differences)
                if differences else None, "paired": differences,
            }
    result = {
        "comparison": f"strong-minus-{other['goal_granularity']}",
        "by_scene_arm": by_arm,
        "interpretation": "Whole-episode Goal granularity intervention, not causal mutual information; goal/action manipulation checks require trace audit.",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["eligible_pairs"] for k, v in by_arm.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()

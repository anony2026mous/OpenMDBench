"""Audit interrupted seed rows and combine known-fault factorial seed evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from audit_grid_factorial import audit
from information import seed_summary


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interrupted", required=True, type=Path)
    parser.add_argument("--resumed", required=True, type=Path)
    parser.add_argument("--seed100-audit", required=True, type=Path)
    parser.add_argument("--resumed-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    interrupted = args.interrupted.resolve()
    resumed = args.resumed.resolve()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(interrupted) or interrupted.is_relative_to(output):
        raise ValueError("New output directory separate from source campaigns required")
    progress = read(interrupted / "progress.json")
    rows = [row for row in progress if row["seed"] in (101, 102, 103, 104)]
    if len(rows) != 16 or any(not row.get("original_valid") or not row.get("replay_valid") for row in rows):
        raise ValueError("Interrupted campaign must contain exactly 16 complete valid cells for seeds 101-104")
    resumed_summary = read(resumed / "summary.json")
    # The audit reads the original trace paths. This derived input only restores
    # campaign metadata for the already-completed seed rows; raw traces remain untouched.
    input_dir = output / "derived-input-s101-104"
    input_dir.mkdir(parents=True)
    subset_summary = {**resumed_summary, "seeds": [101, 102, 103, 104], "rows": rows,
                      "source": str(Path(resumed_summary["source"]).resolve())}
    (input_dir / "summary.json").write_text(json.dumps(subset_summary, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    middle = audit(input_dir)
    (output / "audit-s101-104.json").write_text(json.dumps(middle, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
    audits = [read(args.seed100_audit.resolve() / "audit.json"), middle,
              read(args.resumed_audit.resolve() / "audit.json")]
    errors = [f"campaign_{i}:{err}" for i, item in enumerate(audits) for err in item["errors"]]
    effects = [effect for item in audits for effect in item["effects"]]
    effects.sort(key=lambda x: x["seed"])
    seeds = [item["seed"] for item in effects]
    if seeds != list(range(100, 120)):
        errors.append(f"combined_seed_set_invalid:{seeds}")
    fields = ("planner_loss", "executor_loss", "interaction")
    summaries = {field: seed_summary({row["seed"]: row[field] for row in effects}) for field in fields}
    scores = {cell: seed_summary({row["seed"]: row["scores"][cell] for row in effects})
              for cell in ("clean", "planner", "executor", "both")}
    result = {
        "schema": "role-c-grid-known-fault-factorial-combined@1",
        "seed_set": seeds,
        "pairs_checked": sum(item["pairs_checked"] for item in audits),
        "integrity_errors": errors,
        "effects": effects,
        "seed_level_effect_summaries": summaries,
        "cell_score_summaries": scores,
        "planner_label_recovered_seeds": [r["seed"] for r in effects if r["planner_only_label_recovered"]],
        "executor_label_recovered_seeds": [r["seed"] for r in effects if r["executor_only_label_recovered"]],
        "both_layers_active_seeds": [r["seed"] for r in effects if r["both_injection_layers_active"]],
        "both_score_at_floor_seeds": [r["seed"] for r in effects if r["scores"]["both"] <= 0.2 + 1e-12],
        "limitations": [
            "Known injected faults validate layer-label recovery for this grid rule-stack experiment, not paper-level oracle attribution.",
            "The score floor can mask marginal effects and inflate apparent factorial interaction.",
            "The four original seed-101-104 rows were audited from a derived summary; their raw reports and hashes remain at original paths.",
            "Bootstrap intervals resample independent seeds, not within-episode time points."
        ]
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    print(json.dumps({"integrity_errors": errors, "pairs_checked": result["pairs_checked"],
                      "seed_level_effect_summaries": summaries,
                      "planner_recovery": len(result["planner_label_recovered_seeds"]),
                      "executor_recovery": len(result["executor_label_recovered_seeds"]),
                      "both_at_floor": len(result["both_score_at_floor_seeds"])}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())

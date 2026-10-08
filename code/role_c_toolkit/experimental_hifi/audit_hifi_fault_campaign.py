"""Independent high-fidelity fault campaign pair, source and dose audit."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from audit_hifi_fault_pair import verify_pair
from hifi_trace import file_hash


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root):
    summary_path = root / "summary.json"
    summary = read(summary_path)
    errors, rows, manifests = [], [], []
    seen = set()
    for entry in summary["entries"]:
        key = (entry["scenario"], entry["seed"], entry["case"], entry["dose"])
        if key in seen:
            errors.append(f"duplicate_arm:{key}")
            continue
        seen.add(key)
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
        if summary["terminal_required"] and not pair["natural_terminal_both"]:
            errors.append(f"terminal_missing:{key}")
        original, replay = read(paths[0]), read(paths[1])
        manifests.extend([original["source_hashes"], replay["source_hashes"]])
        if original["fault_injection"]["case"] != entry["case"] or original["fault_injection"]["dose"] != entry["dose"]:
            errors.append(f"fault_spec:{key}")
        if original["fault_injection"]["wrapper_sha256"] != summary["fault_wrapper_sha256"]:
            errors.append(f"wrapper_hash:{key}")
        engine_original = read(paths[0].with_name("engine_result.json"))
        engine_replay = read(paths[1].with_name("engine_result.json"))
        score = engine_original.get("strategy_scorecard", {}).get("defender_score")
        if score is None or score != engine_replay.get("strategy_scorecard", {}).get("defender_score"):
            errors.append(f"score_missing_or_replay_mismatch:{key}")
        rows.append({"scenario": entry["scenario"], "seed": entry["seed"],
                     "case": entry["case"], "dose": entry["dose"], "defender_score": score,
                     "fault_events": original["fault_injection"]["event_count"],
                     "ticks": original["ticks_run"],
                     "terminal": pair["natural_terminal_both"]})
    if manifests and any(m != manifests[0] for m in manifests[1:]):
        errors.append("source_manifest_mismatch_across_arms")
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["scenario"], row["seed"], row["case"])][row["dose"]] = row
    curves = []
    for (scenario, seed, case), arms in sorted(grouped.items()):
        if any(d not in arms for d in summary["doses"]):
            errors.append(f"missing_dose:{scenario}:{seed}:{case}")
            continue
        scores = [arms[d]["defender_score"] for d in summary["doses"]]
        events = [arms[d]["fault_events"] for d in summary["doses"]]
        curves.append({"scenario": scenario, "seed": seed, "case": case,
                       "doses": summary["doses"], "scores": scores, "fault_events": events,
                       "strict_score_monotone_decrease": all(a > b for a, b in zip(scores, scores[1:])),
                       "nonincreasing_score": all(a >= b for a, b in zip(scores, scores[1:]))})
    return {"schema": "role-c-hifi-fault-campaign-audit@1",
            "campaign": str(root.resolve()),
            "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "errors": errors, "pairs_checked": len(rows), "rows": rows, "curves": curves,
            "all_curves_strictly_monotone": bool(curves) and all(c["strict_score_monotone_decrease"] for c in curves),
            "formal_attribution_validated": False, "formal_B_if_validated": False,
            "limitations": ["One seed is not a distribution-level dose-response test.",
                            "Full ΔP/ΔE/ΔI requires independently validated references and counterfactual arms."]}


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
                      "curves": result["curves"]}, ensure_ascii=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

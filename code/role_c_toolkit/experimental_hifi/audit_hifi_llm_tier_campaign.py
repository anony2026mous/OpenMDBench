"""Independent campaign audit for LLM+GOAI Goal-tier original/replay data."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from audit_hifi_llm_tier_pair import audit_pair
from hifi_llm_tier_campaign import sha
from hifi_replay_campaign import SCENARIOS


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def first_transition(report_path: Path):
    with report_path.with_name("events.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("kind") == "transition":
                return row
    raise ValueError(f"No transition found: {report_path}")


def audit(root: Path) -> dict:
    summary = read(root / "summary.json")
    errors, rows, groups, manifests = [], [], defaultdict(dict), []
    pairs_checked = 0
    trace_script = Path(__file__).with_name("hifi_llm_tier_trace.py")
    campaign_script = Path(__file__).with_name("hifi_llm_tier_campaign.py")
    if sha(trace_script) != summary.get("trace_script_sha256"):
        errors.append("trace_script_hash_mismatch")
    if sha(campaign_script) != summary.get("campaign_sha256"):
        errors.append("campaign_script_hash_mismatch")
    selected = summary.get("scenarios", [])
    seeds = summary.get("seeds", [])
    expected = len(selected) * len(seeds) * 3
    if len(summary.get("entries", [])) != expected:
        errors.append("campaign_entry_count_mismatch")
    for entry in summary.get("entries", []):
        key = (entry["scenario"], entry["seed"], entry["tier"])
        pair_paths = []
        for kind in ("original", "replay"):
            meta = entry.get(kind)
            if not meta:
                errors.append(f"missing_{kind}:{key}")
                continue
            path = Path(meta["report_path"])
            if not path.is_file() or sha(path) != meta.get("report_sha256"):
                errors.append(f"report_integrity:{kind}:{key}")
                continue
            report = read(path)
            config = report.get("config", {})
            if (config.get("scenario") != entry["scenario"] or
                    config.get("seed") != entry["seed"] or
                    config.get("goal_granularity") != entry["tier"] or
                    config.get("planner") != "llm" or config.get("llm") != summary["llm"]):
                errors.append(f"run_config_mismatch:{kind}:{key}")
            if report.get("instrumentation_sha256") != summary["trace_script_sha256"]:
                errors.append(f"instrumentation_hash_mismatch:{kind}:{key}")
            pair_paths.append(path)
            manifests.append(report.get("source_hashes"))
            if kind == "original":
                engine = read(path.with_name("engine_result.json"))
                stats = report.get("llm_client_stats") or {}
                planner = report.get("planner_diagnostics") or {}
                rows.append({"scenario": entry["scenario"], "seed": entry["seed"],
                             "tier": entry["tier"], "ticks": report.get("ticks_run"),
                             "defender_score": (engine.get("strategy_scorecard") or {}).get("defender_score"),
                             "llm_calls": stats.get("total_calls"), "llm_errors": stats.get("errors"),
                             "parse_failures": planner.get("parse_failures"),
                             "fallback_count": planner.get("fallback_count"),
                             "goal_count_first_decision": len((report.get("decisions") or [{}])[0].get("commands", []))})
                groups[(entry["scenario"], entry["seed"])][entry["tier"]] = path
        if len(pair_paths) == 2:
            pairs_checked += 1
            pair = audit_pair(*pair_paths)
            errors.extend(f"{key}:{error}" for error in pair["errors"])
    if manifests and any(item != manifests[0] for item in manifests[1:]):
        errors.append("engine_manifest_mismatch")

    anchors = []
    for (scenario, seed), tiers in sorted(groups.items()):
        if set(tiers) != {"weak", "medium", "strong"}:
            errors.append(f"incomplete_tier_set:{scenario}:{seed}")
            continue
        first = {tier: first_transition(path)["own_before"] for tier, path in tiers.items()}
        same = first["weak"] == first["medium"] == first["strong"]
        anchors.append({"scenario": scenario, "seed": seed, "same_predecision_state": same})
        if not same:
            errors.append(f"initial_state_mismatch:{scenario}:{seed}")

    return {"schema": "role-c-hifi-llm-goai-tier-campaign-audit@1",
            "campaign": str(root.resolve()), "errors": errors,
            "entries_expected": expected, "cells_checked": len(rows),
            "pairs_checked": pairs_checked,
            "rows": rows, "same_seed_anchor_checks": anchors,
            "run_replay_integrity_passed": not errors,
            "formal_B_if_validated": False, "formal_D3_passed": False,
            "formal_attribution_validated": False,
            "limitations": ["Goal-tier manipulation and exact replay do not themselves estimate B_if.",
                            "This audit does not establish an information-theoretic gradient or cross-seed uncertainty.",
                            "Causal attribution still requires independently qualified reference components and dose tests."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, output = args.campaign.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("New audit directory separate from campaign required")
    result = audit(root)
    output.mkdir(parents=True)
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    print(json.dumps({"errors": result["errors"], "cells_checked": result["cells_checked"],
                      "pairs_checked": result["pairs_checked"],
                      "same_seed_anchor_checks": result["same_seed_anchor_checks"]}, ensure_ascii=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

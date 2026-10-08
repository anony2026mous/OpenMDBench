"""Independent LLM+GOAI fault-dose campaign audit."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from audit_hifi_fault_pair import verify_pair
from hifi_attribution_spec import PAPER_ATTRIBUTION_ARMS
from hifi_llm_fault_campaign import sha
from hifi_llm_fault_trace import FAULTS


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def expected_arm_labels(summary: dict) -> dict[tuple[str, float], str | None]:
    """Resolve the exact case/dose matrix and expected labels from campaign metadata."""
    if summary.get("paper_table3") is True:
        labels = {(case, 0.0): None for case in summary.get("cases", [])}
        for arm in summary.get("paper_table3_arms", []):
            labels[(arm["case"], arm["dose"])] = arm["expected_label"]
        return labels
    return {(case, dose): None
            for case in summary.get("cases", [])
            for dose in summary.get("doses_by_case", {}).get(case, summary.get("doses", []))}


def audit(root: Path) -> dict:
    summary = read(root / "summary.json")
    errors, rows, groups = [], [], defaultdict(dict)
    trace_script = Path(__file__).with_name("hifi_llm_fault_trace.py")
    campaign_script = Path(__file__).with_name("hifi_llm_fault_campaign.py")
    if sha(trace_script) != summary.get("fault_trace_script_sha256"):
        errors.append("fault_trace_script_hash_mismatch")
    if sha(campaign_script) != summary.get("campaign_sha256"):
        errors.append("campaign_script_hash_mismatch")
    paper_mode = summary.get("paper_table3") is True
    if paper_mode and summary.get("paper_table3_arms") != list(PAPER_ATTRIBUTION_ARMS):
        errors.append("paper_table3_spec_mismatch")
    expected_labels = expected_arm_labels(summary)
    expected_arms = set(expected_labels)
    expected = len(summary.get("scenarios", [])) * len(summary.get("seeds", [])) * len(expected_arms)
    if len(summary.get("entries", [])) != expected:
        errors.append("entry_count_mismatch")
    manifests, seen = [], set()
    for entry in summary.get("entries", []):
        key = (entry["scenario"], entry["seed"], entry["case"], entry["dose"])
        if key in seen:
            errors.append(f"duplicate_cell:{key}")
            continue
        seen.add(key)
        if (entry["case"], entry["dose"]) not in expected_arms:
            errors.append(f"unexpected_arm:{key}")
        if paper_mode:
            if entry.get("expected_label") != expected_labels[(entry["case"], entry["dose"])]:
                errors.append(f"expected_label_mismatch:{key}")
        reports = {}
        paths = {}
        for kind in ("original", "replay"):
            meta = entry.get(kind)
            if not meta:
                errors.append(f"missing_{kind}:{key}")
                continue
            path = Path(meta["report_path"])
            paths[kind] = path
            if not path.is_file() or sha(path) != meta.get("report_sha256"):
                errors.append(f"report_hash:{kind}:{key}")
                continue
            report = read(path)
            reports[kind] = report
            config, fault = report.get("config", {}), report.get("fault_injection", {})
            if (config.get("planner") != "llm" or config.get("scenario") != entry["scenario"] or
                    config.get("seed") != entry["seed"] or
                    config.get("goal_granularity") != summary["tier"] or
                    config.get("llm") != summary["llm"] or
                    fault.get("case") != entry["case"] or fault.get("dose") != entry["dose"]):
                errors.append(f"config_or_fault_spec:{kind}:{key}")
            if fault.get("wrapper_sha256") != summary.get("fault_trace_script_sha256"):
                errors.append(f"fault_wrapper_hash_mismatch:{kind}:{key}")
            stats = report.get("llm_client_stats") or {}
            if kind == "original" and (not isinstance(stats.get("total_calls"), int) or
                                        stats.get("total_calls", 0) < 1):
                errors.append(f"no_llm_calls:{key}")
            if kind == "original" and stats.get("errors") != 0:
                errors.append(f"llm_errors:{key}")
            if kind == "original":
                planner_stats = report.get("planner_diagnostics") or {}
                if planner_stats.get("fallback_count") != 0 or planner_stats.get("parse_failures") != 0:
                    errors.append(f"llm_output_unreliable:{key}")
            manifests.append(report.get("source_hashes"))
        if len(paths) == 2 and len(reports) == 2:
            pair = verify_pair(paths["original"], paths["replay"])
            errors.extend(f"{key}:{error}" for error in pair["errors"])
            score = (read(paths["original"].with_name("engine_result.json")).get(
                "strategy_scorecard") or {}).get("defender_score")
            if not isinstance(score, (int, float)):
                errors.append(f"missing_defender_score:{key}")
            groups[(entry["scenario"], entry["seed"], entry["case"])][entry["dose"]] = {
                "score": score,
                "fault_events": (reports["original"].get("fault_injection") or {}).get("event_count", 0)}
            rows.append({"scenario": entry["scenario"], "seed": entry["seed"],
                         "case": entry["case"], "dose": entry["dose"],
                         "score": groups[(entry["scenario"], entry["seed"], entry["case"])][entry["dose"]]["score"],
                         "fault_events": groups[(entry["scenario"], entry["seed"], entry["case"])][entry["dose"]]["fault_events"],
                         "ticks": reports["original"].get("ticks_run"),
                         "natural_terminal": reports["original"].get("terminal_result") is not None})
    if manifests and any(manifest != manifests[0] for manifest in manifests[1:]):
        errors.append("source_manifest_mismatch")
    dose_checks = []
    for (scenario, seed, case), arms in sorted(groups.items()):
        case_doses = summary.get("doses_by_case", {}).get(case, summary.get("doses", []))
        if set(arms) != set(case_doses):
            errors.append(f"incomplete_dose_curve:{scenario}:{seed}:{case}")
            continue
        ordered = [arms[dose]["score"] for dose in case_doses]
        event_counts = [arms[dose]["fault_events"] for dose in case_doses]
        numeric_scores = all(isinstance(score, (int, float)) for score in ordered)
        dose_checks.append({"scenario": scenario, "seed": seed, "case": case,
                            "doses": case_doses, "scores": ordered,
                            "fault_events": event_counts,
                            "score_nonincreasing": (all(a >= b for a, b in zip(ordered, ordered[1:]))
                                                    if numeric_scores else None),
                            "any_nonzero_fault_event": any(event_counts[1:])})
    paper_contrasts = []
    if paper_mode:
        for arm_spec in PAPER_ATTRIBUTION_ARMS:
            for scenario in summary["scenarios"]:
                for seed in summary["seeds"]:
                    group = groups.get((scenario, seed, arm_spec["case"]), {})
                    clean, faulted = group.get(0.0), group.get(arm_spec["dose"])
                    if clean is None or faulted is None:
                        continue
                    if not isinstance(clean["score"], (int, float)) or not isinstance(faulted["score"], (int, float)):
                        errors.append(f"missing_paper_arm_score:{scenario}:{seed}:{arm_spec['case']}:{arm_spec['dose']}")
                        continue
                    paper_contrasts.append({"scenario": scenario, "seed": seed,
                                            "case": arm_spec["case"], "dose": arm_spec["dose"],
                                            "expected_label": arm_spec["expected_label"],
                                            "clean_score": clean["score"],
                                            "faulted_score": faulted["score"],
                                            "performance_drop": clean["score"] - faulted["score"],
                                            "fault_events": faulted["fault_events"]})
    return {"schema": "role-c-hifi-llm-goai-fault-campaign-audit@1",
            "campaign": str(root.resolve()), "errors": errors,
            "cells_expected": expected, "cells_checked": len(rows), "rows": rows,
            "dose_checks": dose_checks, "paper_table3_contrasts": paper_contrasts,
            "all_pairs_and_fault_mechanisms_audited": not errors,
            "formal_attribution_validated": False, "formal_B_if_validated": False,
            "limitations": ["This audit proves fault injection, trace integrity and replay only.",
                            "Dose-response and attribution quality require cross-seed inference and qualified oracles."]}


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
                      "dose_checks": result["dose_checks"]}, ensure_ascii=False))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

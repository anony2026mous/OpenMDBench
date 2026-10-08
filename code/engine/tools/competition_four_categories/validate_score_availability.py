"""Bounded native receipt probes; not calibration or full-episode acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import yaml

from .build import PACKAGES, ROOT
from .protected_inputs import verify as verify_protected_inputs
from .runtime import create_candidate
from .validate_recon import referee_checkpoint_evidence
from .validate_tracking import score_evidence
from .visibility_audit import VisibilityAudit

PACKAGES_TO_CHECK = tuple(f"md_trk_{n:03d}_standard" for n in range(1, 9)) + (
    "md_er_003_standard", "md_er_005_standard", "md_er_006_standard")
MODEL_REFS = {"models.competition-tracking-metrics@1.0.1",
              "models.competition-delivered-dispatch@1.0.1"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def receipt_violations(tick, scores, statuses, windows):
    problems = []
    for metric, start in windows.items():
        value = scores.get(metric)
        if metric not in scores or metric not in statuses:
            problems.append({"tick": tick, "metric": metric, "reason": "missing receipt"})
        elif tick < start:
            if value is not None or statuses[metric] != "missing":
                problems.append({"tick": tick, "metric": metric, "reason": "prewindow not N/A"})
        elif (statuses[metric] != "available" or type(value) not in (int, float)
              or not math.isfinite(value) or not 0 <= value <= 1):
            problems.append({"tick": tick, "metric": metric, "reason": "sampled fraction unavailable"})
    return problems


def source_hashes():
    files = list((ROOT / "tools/competition_four_categories").rglob("*.py"))
    files += [p for p in PACKAGES.rglob("*") if p.suffix in {".yaml", ".json"}]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sorted(files)}


def run_probe(name, seed, directory):
    document = yaml.safe_load((PACKAGES / name / "scenario.yaml").read_text(encoding="utf-8"))["scenario"]
    brief = json.loads((PACKAGES / name / "public_brief.json").read_text(encoding="utf-8"))
    windows = {m["id"]: m["plugin_parameters"]["start_tick"]
               for m in document["scoring"]["metrics"] if m.get("plugin_ref") in MODEL_REFS}
    if not windows:
        raise ValueError("probe requires a revised candidate metric")
    stop_tick = max(windows.values()) + 1
    if stop_tick >= brief["adjudication_tick"]:
        raise ValueError("this probe must stop before native adjudication")
    slots = {e["id"]: e["controller_slot"] for e in document["entities"]
             if e["faction_id"] == brief["evaluated_side"] and e.get("controller_slot")}
    checkpoint_ticks = {0, stop_tick, *windows.values(), *(s - 1 for s in windows.values())}
    trace_path = directory / f"{name}-seed{seed}.jsonl"
    session = create_candidate(PACKAGES / name, seed=seed, session_id=f"availability-{name}-{seed}")
    violations, checkpoints = [], []
    try:
        auditor = VisibilityAudit(session, slots, faction_id=brief["evaluated_side"])
        with trace_path.open("x", encoding="utf-8") as stream:
            for tick in range(stop_tick + 1):
                scores, statuses = {}, {}
                if tick:
                    receipt = session.step(operation_id=f"probe-{tick}", expected_tick=tick - 1)
                    scores, statuses = score_evidence(receipt)
                    violations.extend(receipt_violations(tick, scores, statuses, windows))
                observations = {i: session.world_view.controller_observation(controller_slot_id=s).model_dump(mode="json")
                                for i, s in slots.items()}
                privacy_failure = auditor.check(observations)
                if privacy_failure:
                    violations.append({"tick": tick, "privacy_failure": privacy_failure})
                frame = session.world_view.presentation_snapshot()
                row = {"tick": tick, "observations": observations, "scores": scores,
                       "score_data_status": statuses,
                       "native_score_state": dict(frame.mission_scoring_checkpoint["score_state"]),
                       "terminal": frame.mission_scoring_checkpoint["terminal_result"]}
                if tick in checkpoint_ticks:
                    checkpoint, states = referee_checkpoint_evidence(session)
                    row["checkpoint"] = checkpoint
                    row["checkpoint_plugin_states"] = states
                    checkpoints.append({"tick": tick, **checkpoint})
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                if row["terminal"]:
                    violations.append({"tick": tick, "reason": "unexpected early terminal"})
                    break
        return {"package": name, "seed": seed, "policy": "idle_bounded_receipt_probe",
                "scope": "canonical inputs unchanged; no controller actions; not a natural-terminal experiment",
                "final_tick": session.world_view.tick, "expected_final_tick": stop_tick,
                "score_windows": windows, "availability_passed": not violations,
                "violations": violations, "checkpoint_evidence": checkpoints,
                "visibility_audit": auditor.summary(), "trace": str(trace_path.relative_to(ROOT)),
                "trace_sha256": sha(trace_path), "resolved_hash": session.resolved.resolved_hash,
                "catalog_hash": session.resolved.catalog_hash,
                "model_registry_hash": session.resolved.model_registry_hash,
                "full_restore_equivalence_proven": False, "competition_accepted": False}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--package", action="append", choices=PACKAGES_TO_CHECK)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / "artifacts/competition_four_categories" / f"availability-native-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    before = source_hashes()
    report = {"schema_version": "native-score-availability@1.0", "revision": "score-availability-1.0.1",
              "seed": args.seed, "source_input_hashes_before": before,
              "protected_before": verify_protected_inputs(), "cases": [],
              "competition_accepted": False, "collection_complete": False}
    try:
        for name in args.package or PACKAGES_TO_CHECK:
            result = run_probe(name, args.seed, directory)
            report["cases"].append(result)
            with (directory / f"{name}-summary.json").open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2)
            print(name, "availability_passed=", result["availability_passed"],
                  "ticks=", result["final_tick"], flush=True)
        report["collection_complete"] = True
    finally:
        report["source_input_hashes_after"] = source_hashes()
        report["source_inputs_unchanged"] = before == report["source_input_hashes_after"]
        report["protected_after"] = verify_protected_inputs()
        with (directory / "report.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
        print("REPORT", directory / "report.json", flush=True)
    if not report["source_inputs_unchanged"] or any(not r["availability_passed"] for r in report["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

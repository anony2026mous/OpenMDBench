"""Four-cell known planner/executor fault factorial with own-trace replays."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--difficulty", choices=("simple", "medium", "complex"), default="complex")
    parser.add_argument("--task-mode", choices=("independent", "sequential", "continuous"), default="continuous")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--planner-dose", type=float, required=True)
    parser.add_argument("--executor-dose", type=float, required=True)
    parser.add_argument("--episode-timeout", type=int, default=600)
    args = parser.parse_args()
    if (len(args.seed) != len(set(args.seed)) or not 0 < args.planner_dose <= 1 or
            not 0 < args.executor_dose <= 1):
        raise ValueError("Unique seeds and nonzero doses in (0,1] required")
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("New output outside source required")
    script = Path(__file__).with_name("grid_factorial_fault.py")
    wrapper_hash, campaign_hash = digest(script), digest(Path(__file__))
    output.mkdir(parents=True)
    rows = []
    cells = [("clean", 0.0, 0.0), ("planner", args.planner_dose, 0.0),
             ("executor", 0.0, args.executor_dose),
             ("both", args.planner_dose, args.executor_dose)]
    for seed in args.seed:
        for label, pdose, edose in cells:
            stem = output / f"seed-{seed}" / label
            stem.mkdir(parents=True)
            pair = {}
            for kind in ("original", "replay"):
                if kind == "replay" and not pair.get("original_valid"):
                    pair["replay_skipped"] = "original_failed"
                    break
                target = stem / kind
                cmd = [sys.executable, "-B", "-X", "utf8", str(script),
                       "--source", str(source), "--output", str(target),
                       "--seed", str(seed), "--difficulty", args.difficulty,
                       "--task-mode", args.task_mode, "--interval", str(args.interval),
                       "--planner-dose", str(pdose), "--executor-dose", str(edose)]
                if kind == "replay":
                    cmd += ["--replay-from", str(stem / "original" / "episode.json")]
                with (stem / f"{kind}.console.log").open("x", encoding="utf-8") as stream:
                    try:
                        code = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                              timeout=args.episode_timeout,
                                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
                    except subprocess.TimeoutExpired:
                        code = "timeout"
                report_path = target / "episode.json"
                report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
                fault = report.get("factorial_fault", {})
                pair[kind] = {"returncode": code, "aborted": report.get("aborted", "missing_report"),
                              "V": report.get("V"), "steps": report.get("steps"),
                              "planner_events": fault.get("planner_events"),
                              "executor_events": fault.get("executor_events"),
                              "replay_exact": (report.get("replay_check") or {}).get("exact_match"),
                              "report_path": str(report_path),
                              "report_sha256": digest(report_path) if report_path.exists() else None}
                pair[f"{kind}_valid"] = (code == 0 and report.get("aborted", "missing_report") is None
                                          and fault.get("planner_dose") == pdose
                                          and fault.get("executor_dose") == edose
                                          and fault.get("wrapper_sha256") == wrapper_hash
                                          and (kind != "replay" or
                                               ((report.get("replay_check") or {}).get("exact_match") is True and
                                                fault.get("replay_spec_same") is True)))
            row = {"seed": seed, "cell": label, "planner_dose": pdose,
                   "executor_dose": edose, **pair}
            rows.append(row)
            (output / "progress.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")
            print(json.dumps({"seed": seed, "cell": label, "V": pair.get("original", {}).get("V"),
                              "P_events": pair.get("original", {}).get("planner_events"),
                              "E_events": pair.get("original", {}).get("executor_events"),
                              "replay_exact": pair.get("replay", {}).get("replay_exact")}), flush=True)
    unchanged = digest(script) == wrapper_hash and digest(Path(__file__)) == campaign_hash
    valid = unchanged and all(row.get("original_valid") and row.get("replay_valid") for row in rows)
    result = {"schema": "role-c-grid-known-fault-factorial@1", "source": str(source),
              "seeds": args.seed, "difficulty": args.difficulty, "task_mode": args.task_mode,
              "interval": args.interval, "planner_nonzero_dose": args.planner_dose,
              "executor_nonzero_dose": args.executor_dose,
              "cells": [item[0] for item in cells], "wrapper_sha256": wrapper_hash,
              "campaign_sha256": campaign_hash, "scripts_unchanged": unchanged,
              "all_own_replays_valid": bool(valid), "reference_kind": "same rule stack with injected fault removed",
              "global_oracle_quality_verified": False,
              "formal_attribution_validated": False, "rows": rows}
    (output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

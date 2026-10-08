"""Frozen, seed-major native calibration; execution coverage is not acceptance.

Prepare only after controller development. Every later chunk requires identical
sources and canonical inputs. A running/uncertain case is never silently retried;
reconcile its recorded PID/log and the owning execution handle first.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .build import ROOT, PACKAGES
from .protected_inputs import verify

RESULTS = ROOT / "artifacts/competition_four_categories"
PREFIX = "tools.competition_four_categories."


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases_for_seed(seed):
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    rows = []
    def add(sid, difficulty, side, module, arguments, policy):
        rows.append({"case_id": f"{seed}-{sid}-{difficulty}-{side}", "seed": seed,
            "scenario_id": sid, "difficulty": difficulty, "side": side,
            "module": PREFIX+module, "arguments": [*arguments, "--seed", str(seed)],
            "expected_policy": policy})
    for level in ("easy", "medium", "hard"):
        for side, policy in (("A", "idle"), ("B", "sweep")):
            add("MD-REC-001", level, side, "validate", ["--difficulty", level, "--policy", policy], policy)
    for number in range(2, 9):
        sid = f"MD-REC-{number:03d}"
        add(sid, "standard", "A", "validate_recon", ["--scenario", str(number), "--policy", "sweep"], "sweep")
        if number == 6:
            add(sid, "standard", "B", "validate_observation_search", ["--scenario", str(number), "--mode", "patrol"], "observation-patrol")
        else:
            add(sid, "standard", "B", "validate_recon", ["--scenario", str(number), "--policy", "coordinated"], "coordinated")
    for number in range(1, 9):
        sid = f"MD-TRK-{number:03d}"
        if number <= 6:
            add(sid, "standard", "A", "validate_tracking", ["--scenario", str(number), "--policy", "follow"], "follow")
            add(sid, "standard", "B", "validate_allocated_tracking", ["--scenario", str(number)], "allocated")
        else:
            modules = (("validate_tracking_reports", "report-honest"), ("validate_identity_tracking", "identity-honest")) if number == 7 else (
                ("validate_beacon_tracking", "beacon-honest"), ("validate_coverage_tracking", "coverage-honest"))
            for side, (module, policy) in zip(("A", "B"), modules):
                add(sid, "standard", side, module, ["--scenario", str(number), "--mode", "honest"], policy)
    for number in range(1, 7):
        sid = f"MD-AD-{number:03d}"
        for side, policy in (("A", "indiscriminate"), ("B", "guard")):
            add(sid, "standard", side, "validate_denial", ["--scenario", str(number), "--policy", policy], policy)
    for number, policies in ((1, ("direct", "safe")), (2, ("direct", "team")), (4, ("direct", "preissued"))):
        for side, policy in zip(("A", "B"), policies):
            add(f"MD-ER-{number:03d}", "standard", side, "validate_emergency", ["--scenario", str(number), "--policy", policy], policy)
    for number in (3, 5):
        for side, policy in (("A", "naive"), ("B", "coordinated")):
            add(f"MD-ER-{number:03d}", "standard", side, "validate_response", ["--scenario", str(number), "--policy", policy], policy)
    for side, policy in (("A", "watch-coordinated"), ("B", "progress-watch")):
        add("MD-ER-006", "standard", side, "validate_standing_response", ["--scenario", "6", "--policy", policy], policy)
    return rows


def frozen_inputs():
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/"tools/competition_four_categories").rglob("*.py"))}
    paths = [ROOT/"catalog/v2/competition_four_categories.yaml"] + sorted(
        p for p in PACKAGES.rglob("*") if p.is_file() and p.suffix in {".yaml", ".json"})
    return {"source_hashes": sources, "input_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}}


def save_json(path, value):
    temporary = path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")
    os.replace(temporary, path)


def prepare(seeds):
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("provide unique seeds in the intended order")
    used = set()
    for existing in RESULTS.glob("*.json"):
        match = re.search(r"-(\d+)-\d{8}T", existing.name)
        if match:
            used.add(int(match.group(1)))
        if "plan" in existing.name and existing.stat().st_size < 1000000:
            data = json.loads(existing.read_text(encoding="utf-8-sig"))
            def visit(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if "seed" in key:
                            if type(item) is int: used.add(item)
                            elif isinstance(item, list): used.update(n for n in item if type(n) is int)
                        visit(item)
                elif isinstance(value, list):
                    for item in value: visit(item)
            visit(data)
    if set(seeds) & used:
        raise ValueError("requested calibration seed already executed or reserved")
    plan = {"schema_version": "competition-calibration-plan@1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "seed_order": seeds,
        "cases": [case for seed in seeds for case in cases_for_seed(seed)],
        **frozen_inputs(), "protected_inputs": verify(),
        "scope": "Frozen cross-scenario reference-policy calibration, not LLM/RL experiments, a uniform-policy leaderboard or automatic competition acceptance",
        "protocol": ["Finish every case for one seed before starting another",
            "Do not tune inputs/controllers after observing this plan's results",
            "Preserve native failures, missing scores and incomplete tasks",
            "Report task outcomes, raw metric availability/distributions and native terminal ticks for both preselected controls",
            "Small-sample separation is descriptive evidence, not statistical proof or full acceptance"]}
    path = RESULTS/("calibration-plan-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json")
    save_json(path, plan)
    return path


def evidence_path(log):
    found = set()
    for line in log.splitlines():
        if line.startswith("evidence="):
            found.add(line[len("evidence="):].strip())
        else:
            try: item = json.loads(line)
            except (ValueError, TypeError): continue
            if isinstance(item, dict) and isinstance(item.get("evidence"), str): found.add(item["evidence"])
    resolved = {(ROOT/value).resolve() for value in found}
    if len(resolved) != 1:
        raise ValueError("expected exactly one explicit experiment artifact")
    path, = resolved
    if not path.is_relative_to(RESULTS.resolve()) or path.suffix != ".json" or not path.is_file():
        raise ValueError("experiment evidence must be an existing JSON artifact inside RESULTS")
    return path


def validate_result(result, case):
    if any(result.get(k) != case[k] for k in ("seed", "scenario_id", "difficulty")) or result.get("policy") != case["expected_policy"]:
        raise ValueError("experiment identity differs from frozen case")
    trace = result.get("trace", [])
    if hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest() != result.get("trace_sha256"):
        raise ValueError("native trace digest differs from artifact")
    if trace and (trace[-1]["scores"] != result["scores"] or trace[-1]["terminal"] != result.get("terminal")):
        raise ValueError("native trace summary differs from artifact")
    end = result["final_tick"]
    ticks = [row["tick"] for row in trace]
    continuous = ticks in (list(range(1, end+1)), list(range(end+1)))
    visible = result.get("visibility_audit", {})
    complete = bool(result.get("terminal")) and continuous and visible.get("last_tick") == end and visible.get("checked_frames") == end+1
    if not result.get("failure") and not complete:
        raise ValueError("successful validation lacks a complete native episode")
    return complete


def run_next(path, limit):
    path = path.resolve()
    if not path.is_relative_to(RESULTS.resolve()) or type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("use a stored candidate plan and a bounded chunk of 1..8 cases")
    lock = path.with_suffix(".lock")
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise ValueError("plan execution lock exists; inspect its owner PID before any retry") from error
    try:
        handle.write(json.dumps({"pid": os.getpid(), "started_at_utc": datetime.now(timezone.utc).isoformat()}))
        handle.flush()
        return _run_next_locked(path, limit)
    finally:
        handle.close()
        lock.unlink()


def _run_next_locked(path, limit):
    path = path.resolve()
    if not path.is_relative_to(RESULTS.resolve()) or not 1 <= limit <= 8:
        raise ValueError("use a stored candidate plan and a bounded chunk of 1..8 cases")
    plan = json.loads(path.read_text(encoding="utf-8"))
    expected = [c for seed in plan["seed_order"] for c in cases_for_seed(seed)]
    if plan["schema_version"] != "competition-calibration-plan@1.0" or plan["cases"] != expected:
        raise ValueError("plan cases/commands differ from the declared calibration protocol")
    state_path = path.with_suffix(".state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"plan_sha256": sha(path), "cases": {}}
    if state["plan_sha256"] != sha(path) or any(x["status"] in {"running", "execution_error"} for x in state["cases"].values()):
        raise ValueError("plan changed or a case needs PID/log/evidence reconciliation; refusing to retry")
    if list(state["cases"]) != [case["case_id"] for case in expected[:len(state["cases"])]]:
        raise ValueError("recorded cases are not the seed-major plan prefix")
    for case in expected[:len(state["cases"])]:
        entry = state["cases"][case["case_id"]]
        if entry.get("status") != "recorded" or not isinstance(entry.get("evidence"), str):
            raise ValueError("completed case lacks recorded evidence")
        artifact = (ROOT/entry["evidence"]).resolve()
        if not artifact.is_relative_to(RESULTS.resolve()) or not artifact.is_file() or sha(artifact) != entry.get("evidence_sha256"):
            raise ValueError("completed case evidence changed or is missing")
        validate_result(json.loads(artifact.read_text(encoding="utf-8")), case)
    log_dir = RESULTS/"calibration_runs"/path.stem; log_dir.mkdir(parents=True, exist_ok=True)
    completed = 0
    for case in plan["cases"]:
        if case["case_id"] in state["cases"]: continue
        snapshot = frozen_inputs()
        if any(snapshot[k] != plan[k] for k in snapshot):
            raise ValueError("frozen sources or canonical inputs drifted; preserve this plan and do not relabel its results")
        verify()
        command = [sys.executable, "-B", "-m", case["module"], *case["arguments"]]
        log_path = log_dir/(case["case_id"]+".log")
        if log_path.exists(): raise ValueError("unreconciled case log already exists")
        entry = {"status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                 "command": command, "log": log_path.relative_to(ROOT).as_posix()}
        state["cases"][case["case_id"]] = entry; save_json(state_path, state)
        print("START "+case["case_id"], flush=True)
        with log_path.open("x", encoding="utf-8") as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            entry["pid"] = process.pid; save_json(state_path, state)
            try:
                process.wait(timeout=900)
            except subprocess.TimeoutExpired:
                entry["observation_timeout"] = True
                save_json(state_path, state)
                raise RuntimeError("owned child may still be running; inspect its PID/log rather than restarting")
        try:
            artifact = evidence_path(log_path.read_text(encoding="utf-8", errors="replace"))
            result = json.loads(artifact.read_text(encoding="utf-8"))
            complete = validate_result(result, case)
            if process.returncode not in (0, 1, 2): raise ValueError("unexpected native process exit")
            if process.returncode and not result.get("failure"): raise ValueError("nonzero process exit without recorded validation failure")
            snapshot = frozen_inputs()
            if any(snapshot[k] != plan[k] for k in snapshot): raise ValueError("source/input changed while case was running")
            verify()
            entry.update(status="recorded", exit_code=process.returncode, evidence=artifact.relative_to(ROOT).as_posix(),
                evidence_sha256=sha(artifact), native_status=result["status"], native_failure=result.get("failure"),
                full_episode_completed=complete,
                terminal=result.get("terminal"), final_tick=result["final_tick"], scores=result["scores"],
                finished_at_utc=datetime.now(timezone.utc).isoformat())
        except Exception as error:
            entry.update(status="execution_error", exit_code=process.returncode, error=str(error));save_json(state_path,state);raise
        save_json(state_path, state);print("RECORDED "+case["case_id"]+" "+entry["native_status"],flush=True)
        completed += 1
        if completed >= limit: break
    return {"recorded_cases": len(state["cases"]), "planned_cases": len(plan["cases"]), "state": state_path.as_posix()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-seeds", nargs="+", type=int)
    modes.add_argument("--run-plan", type=Path)
    parser.add_argument("--max-cases", type=int, default=2)
    args = parser.parse_args()
    if args.prepare_seeds: print(prepare(args.prepare_seeds).as_posix())
    else: print(json.dumps(run_next(args.run_plan, args.max_cases), indent=2))


if __name__ == "__main__": main()

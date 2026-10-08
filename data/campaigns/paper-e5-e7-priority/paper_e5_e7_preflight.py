"""Bounded E5 inventory + one E7 baseline, never other checklist experiments."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    os.replace(temporary, path)


def inventory(campaign):
    scenarios = {"IE-03-SURFACE-RAID", "IE-04-COMBINED-ARMS", "IE-08-ISLAND-STRIKE"}
    rows = []
    for path in sorted((campaign / "episodes").glob("*llm-rl*/report.json")):
        r = json.loads(path.read_text(encoding="utf-8")); scenario = r.get("scenario")
        if scenario not in scenarios: continue
        terminal = r.get("terminal_result") or {}; outcome = terminal.get("outcome")
        files = {name: path.parent / name for name in ("report.json", "trajectory.jsonl", "requests.jsonl", "manifest.json")}
        candidate = outcome == "intruder_success" and not r.get("aborted") and not r.get("error")
        rows.append({"case_id": path.parent.name, "scenario": scenario, "seed": r.get("seed"),
            "outcome": outcome, "aborted": r.get("aborted"), "ticks": r.get("ticks_run"),
            "original_elapsed_seconds": r.get("elapsed_seconds"), "natural_failure_candidate": candidate,
            "replay_gate_passed": False, "admitted_for_attribution": False,
            "files": {n: {"path": str(p), "exists": p.is_file(),
                "sha256": sha(p) if p.is_file() else None} for n, p in files.items()}})
    return {"schema": "E5-natural-failure-intake@1", "scope": str(campaign), "cases": rows,
        "hifi_natural_failure_candidates": sum(r["natural_failure_candidate"] for r in rows),
        "grid_cases_screened": 0, "other_historical_archives_not_yet_screened": True,
        "no_machine_or_human_fault_labels_created": True,
        "note": "Intake candidates only: not source-complete attribution, replay admission, or independent human ground truth"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--old-campaign", type=Path, required=True)
    args = parser.parse_args()
    directory, snapshot_root = args.campaign_dir.resolve(), args.snapshot.resolve()
    request = json.loads((directory / "request-plan.json").read_text(encoding="utf-8"))
    if request["requested_scope"] != ["P1/E5", "P1/E7"]:
        raise ValueError("Only requested E5/E7 scope is allowed")
    if (directory / "preflight-status.json").exists():
        raise RuntimeError("Existing preflight state; inspect before any retry")
    seed = request["E7_proposed_small_validation"]["seed_ids"][0]
    status = {"schema": "E5-E7-preflight-status@1", "phase": "inventory",
        "started_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
        "formal_E7_scan_started": False, "E5_attribution_started": False, "error": None}
    save(directory / "preflight-status.json", status)
    try:
        intake = inventory(args.old_campaign.resolve()); save(directory / "E5-source-intake.json", intake)
        status["E5_natural_failure_candidates_in_current_server_campaign"] = intake["hifi_natural_failure_candidates"]
        runner = snapshot_root / "role_c_toolkit/grid_rolec6.py"
        weight = snapshot_root / "role_c_toolkit/assets/mappo_medium_s42_best.pt"
        source = snapshot_root / "openmd"
        required = [runner, weight, source / "code/grid_env/grid_env.py",
            source / "code/grid_env/agents/mappo_agent.py", source / "code/grid_env/agents/hybrid_agent.py"]
        if not all(p.is_file() for p in required): raise FileNotFoundError("Frozen grid source or checkpoint missing")
        pinned = {str(p): sha(p) for p in required}
        output = directory / "E7-baseline" / ("seed-" + str(seed)); output.parent.mkdir(exist_ok=True)
        if output.exists(): raise FileExistsError("Do not overwrite baseline")
        command = [sys.executable, "-B", str(runner), "run", "--source", str(source),
            "--output", str(output), "--seed", str(seed), "--arm", "rl",
            "--difficulty", "medium", "--task-mode", "continuous",
            "--goal-mode", "strong", "--checkpoint", str(weight)]
        save(directory / "E7-baseline-manifest.json", {"purpose": "One pure-RL reference episode for requested E7 pilot",
            "seed": seed, "command": command, "frozen_files": pinned,
            "request_plan_sha256": sha(directory / "request-plan.json"),
            "preflight_script_sha256": sha(Path(__file__)), "new_training": False})
        status.update(phase="E7_first_RL_reference", command=command); save(directory / "preflight-status.json", status)
        env = os.environ.copy(); env.update(MPLBACKEND="Agg", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
        began = time.monotonic()
        with (directory / "E7-baseline.console.log").open("x", encoding="utf-8") as log:
            child = subprocess.Popen(command, cwd=snapshot_root, env=env, stdout=log, stderr=subprocess.STDOUT)
            status["child_pid"] = child.pid; save(directory / "preflight-status.json", status)
            try: code = child.wait(timeout=900)
            except BaseException:
                child.terminate(); child.wait(timeout=30); raise
        status.update(exit_code=code, baseline_elapsed_seconds=time.monotonic()-began, child_pid=None)
        if {str(p): sha(p) for p in required} != pinned: raise RuntimeError("Pinned source or weight changed")
        if code: raise RuntimeError("E7 baseline failed; inspect preserved console log")
        result_path = output / "episode.json"; result = json.loads(result_path.read_text(encoding="utf-8"))
        if not result.get("complete"): raise RuntimeError("Reference episode did not complete")
        status.update(phase="preflight_complete_treatment_adapter_and_E5_gates_pending",
            baseline_report=str(result_path), baseline_report_sha256=sha(result_path),
            engine_and_weights_unchanged=True, finished_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        status.update(phase="preflight_failed", error={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        save(directory / "preflight-status.json", status)


if __name__ == "__main__":
    main()

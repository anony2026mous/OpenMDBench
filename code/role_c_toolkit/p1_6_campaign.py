"""Sequential, resumable P1 six-arm matrix over untouched 6.0 source/weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNNER = Path(__file__).with_name("p1_6_run.py")
SCENARIOS = ("IE-04-COMBINED-ARMS", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN")
ARMS = ("rule", "rule-rl", "rl", "llm", "llm-rl", "pure-llm")
SEEDS = (201, 202, 203)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def id_for(scenario: str, arm: str, seed: int) -> str:
    return f"{scenario.lower().replace('-', '_')}_{arm}_s{seed}_a1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scenario", choices=SCENARIOS,
                        help="Run just one scene; omit for IE-10 then IE-11")
    parser.add_argument("--run-arm", action="append", choices=ARMS,
                        help="Only run these arms now; the locked six-arm design is unchanged")
    args = parser.parse_args()
    out = args.output_dir
    provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
    config = json.loads((out / "toolkit_config.json").read_text(encoding="utf-8"))
    scenes = config["scenarios"]
    seeds = config["seeds"]
    arms = args.run_arm or config["arms"]
    if args.scenario and args.scenario not in scenes:
        parser.error("Scenario is not in the frozen campaign")
    runner_hash = sha256(RUNNER)
    status_path = out / "campaign_status.json"
    status = {
        "updated_utc": now(), "runner_sha256": runner_hash,
        "selected_scenarios": [args.scenario] if args.scenario else scenes,
        "selected_seeds": seeds, "arms": arms,
        "completed": [], "current": None, "stop_reason": None,
    }
    for scenario in (args.scenario,) if args.scenario else scenes:
        for seed in seeds:
            for arm in arms:
                run_id = id_for(scenario, arm, seed)
                manifest_path = out / f"{run_id}_manifest.json"
                if manifest_path.exists():
                    deadline = time.monotonic() + 1800
                    while True:
                        try:
                            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            manifest = {"status": "running"}
                        if manifest.get("status") != "running":
                            break
                        if time.monotonic() >= deadline:
                            status["stop_reason"] = f"Running cell did not finish: {run_id}"
                            save(status_path, status)
                            return 2
                        time.sleep(10)
                    report_path = out / f"{run_id}.json"
                    if (manifest.get("eligible_for_main_score")
                            and manifest.get("wrapper_sha256") == runner_hash
                            and manifest.get("scenario_resolved_hash")
                            == provenance["scenarios"][scenario]["resolved_hash"]
                            and report_path.is_file()
                            and sha256(report_path) == manifest.get("report_sha256")):
                        status["completed"].append(run_id)
                        status["updated_utc"] = now()
                        save(status_path, status)
                        continue
                    status["stop_reason"] = f"Existing cell is not certified: {run_id}"
                    save(status_path, status)
                    return 2
                status["current"] = run_id
                status["updated_utc"] = now()
                save(status_path, status)
                command = [sys.executable, str(RUNNER), "--output-dir", str(out),
                           "--scenario", scenario, "--arm", arm, "--seed", str(seed),
                           "--max-ticks", str(config["max_ticks"]),
                           "--goal-granularity", config["goal_granularity"]]
                console_path = out / f"{run_id}_console.txt"
                if console_path.exists():
                    status["stop_reason"] = f"Console file already exists: {console_path}"
                    save(status_path, status)
                    return 2
                with console_path.open("w", encoding="utf-8") as console:
                    env = dict(os.environ, ROLEC_LLM_BASE_URL=config["base_url"],
                               ROLEC_LLM_MODEL=config["model"])
                    process = subprocess.run(command, cwd=str(RUNNER.parent), env=env,
                                             stdout=console, stderr=subprocess.STDOUT,
                                             check=False)
                if process.returncode:
                    status["stop_reason"] = f"Cell {run_id} exited {process.returncode}"
                    status["current"] = None
                    status["updated_utc"] = now()
                    save(status_path, status)
                    return process.returncode
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not manifest.get("eligible_for_main_score"):
                    status["stop_reason"] = f"Cell lacks natural terminal/score: {run_id}"
                    status["current"] = None
                    status["updated_utc"] = now()
                    save(status_path, status)
                    return 2
                status["completed"].append(run_id)
                status["current"] = None
                status["updated_utc"] = now()
                save(status_path, status)
                print(f"COMPLETE {len(status['completed'])}: {run_id}", flush=True)
    status["updated_utc"] = now()
    save(status_path, status)
    print(f"CAMPAIGN COMPLETE: {len(status['completed'])} cells", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

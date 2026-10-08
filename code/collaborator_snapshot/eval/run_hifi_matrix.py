"""Batch-run all formal V2 high-fidelity scenarios for rule / hybrid / pure-llm."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SCENARIOS = (
    "MD-AD-002-EASY",
    "MD-AD-002-MEDIUM",
    "MD-AD-002-HARD",
    "MD-AD-004-DECEPTION",
    "MD-INT-002-AIR-SURFACE",
    "MD-INT-003-EASY",
    "MD-INT-003-MEDIUM",
    "MD-INT-003-HARD",
    "MD-INT-005-STEALTH-MULTI-AXIS",
    "MD-INT-006-SATURATION-ROE",
)
PLANNERS = ("rule", "llm", "pure-llm")
SEED = 7
WALL = {"rule": 900, "llm": 1800, "pure-llm": 1800}


def main() -> int:
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

    eval_dir = Path(__file__).resolve().parent
    out_dir = eval_dir.parent / "results" / "hifi_full"
    out_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    rows = []
    summary_path = out_dir / "summary.json"
    if summary_path.is_file():
        rows = json.loads(summary_path.read_text(encoding="utf-8"))
    done = {(r.get("scenario"), r.get("planner")) for r in rows}
    durations = {}
    for scenario in SCENARIOS:
        resolved, _catalog = compile_formal_scenario_v2(scenario)
        durations[scenario] = int(resolved.world.duration_ticks)
    for planner in PLANNERS:
        for scenario in SCENARIOS:
            key = (scenario, planner)
            if key in done:
                print(f"skip {planner} {scenario}", flush=True)
                continue
            stem = f"{scenario}_{planner}_seed{SEED}"
            output = out_dir / f"{stem}.json"
            log = out_dir / f"{stem}.jsonl"
            cmd = [
                python, str(eval_dir / "run_episode.py"),
                "--scenario", scenario,
                "--planner", planner,
                "--seed", str(SEED),
                "--max-ticks", str(durations[scenario]),
                "--plan-interval", "10",
                "--step-timeout", "90",
                "--wall-limit", str(WALL[planner]),
                "--output", str(output),
                "--log", str(log),
            ]
            if planner != "rule":
                cmd.extend(["--llm-model", "Qwen3.8-27B"])
            print(f"== start {planner} {scenario}", flush=True)
            started = time.time()
            proc = subprocess.run(cmd, cwd=str(eval_dir))
            elapsed = round(time.time() - started, 1)
            report = {}
            if output.is_file():
                try:
                    report = json.loads(output.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    report = {"error": "invalid json"}
            metrics = report.get("layered_metrics") or {}
            row = {
                "scenario": scenario,
                "planner": planner,
                "seed": SEED,
                "exit_code": proc.returncode,
                "elapsed_seconds": report.get("elapsed_seconds", elapsed),
                "ticks_run": report.get("ticks_run"),
                "aborted": report.get("aborted"),
                "terminal_result": report.get("terminal_result"),
                "total_fires": report.get("total_fires", metrics.get("total_fires")),
                "duration_ticks": durations[scenario],
                "mission_success": metrics.get("mission_success"),
                "outcome": metrics.get("outcome"),
                "performance_v": metrics.get("performance_v"),
                "defender_survival_rate": metrics.get("defender_survival_rate"),
                "threat_neutralization_rate": metrics.get("threat_neutralization_rate"),
                "ammo_efficiency": metrics.get("ammo_efficiency"),
                "first_fire_tick": metrics.get("first_fire_tick"),
                "fires_threat": metrics.get("fires_threat"),
                "fires_decoy": metrics.get("fires_decoy"),
                "fires_civilian": metrics.get("fires_civilian"),
                "score_denial": metrics.get("score_denial"),
                "score_survival": metrics.get("score_survival"),
                "score_efficiency": metrics.get("score_efficiency"),
                "parse_failures": metrics.get("parse_failures"),
                "fallback_count": metrics.get("fallback_count"),
                "error": report.get("error"),
            }
            rows.append(row)
            summary_path.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                f"== done {planner} {scenario} ticks={row['ticks_run']} "
                f"V={row['performance_v']} fires={row['total_fires']} "
                f"abort={row['aborted']}",
                flush=True,
            )
    (out_dir / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only 6.0 Role-C P0 provenance and historical-run inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from toolkit_paths import PROJECT, OPENMD, ENGINE, EVAL
CHECKPOINTS = EVAL / "_w1_runs" / "rl"
SCENARIOS = ("IE-04-COMBINED-ARMS", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN")
WEIGHTS = {"rl": "theta_rl_legacy2.npz", "rule-rl": "theta_arm5_v12.npz",
           "llm-rl": "theta_arm5_llm_reward_v9.npz"}
EVAL_SOURCES = ("run_episode.py", "v2_agent.py", "rule_planner.py", "llm_planner.py",
                "v2_executor.py", "rl_executor.py", "rl_agent.py", "pure_llm_agent.py",
                "ie_rl_env.py", "ie_goal_features.py", "ie_rl_policy.py",
                "strategy_metrics.py", "interception_graph.py", "llm_client_hifi.py",
                "attack_driver.py")
ENGINE_SOURCES = ("openmdbench/sessions/formal_v2.py",
                  "openmdbench/scenarios/formal_v2.py",
                  "openmdbench/scenarios/declarative_v2.py",
                  "openmdbench/systems/sensors/ad2.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def freeze(output: Path) -> dict:
    os.environ["OPENMDBENCH_ROOT"] = str(ENGINE)
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    import openmdbench
    from openmdbench.scenarios.formal_v2 import (
        compile_formal_scenario_v2, formal_scenario_registry_v2,
    )
    from ie_rl_policy import load_theta, read_meta
    from run_episode import build_parser

    actual = Path(openmdbench.__file__).resolve().parent
    if actual != (ENGINE / "openmdbench").resolve():
        raise RuntimeError(f"Wrong engine tree: {actual}")
    registry = formal_scenario_registry_v2()
    files = [EVAL / name for name in EVAL_SOURCES]
    files += [ENGINE / name for name in ENGINE_SOURCES]
    files.append(ENGINE / "scenarios" / "formal" / "registry.yaml")
    scenes = {}
    for public_id in SCENARIOS:
        entry = registry[public_id]
        files += [p for p in entry.package_root.rglob("*") if p.is_file()]
        files.append(entry.catalog_path)
        resolved, catalog = compile_formal_scenario_v2(public_id)
        scenes[public_id] = {
            "package_root": str(entry.package_root), "catalog_bundle": str(entry.catalog_path),
            "resolved_hash": resolved.resolved_hash,
            "catalog_content_hash": catalog.content_hash,
        }
    checkpoints, drift = {}, {}
    for arm, filename in WEIGHTS.items():
        path = CHECKPOINTS / filename
        meta = read_meta(load_theta(path))
        checkpoints[arm] = {"path": str(path), "sha256": sha256(path), "meta": meta}
        drift[arm] = {
            name: {"trained_sha256": trained, "current_sha256": sha256(EVAL / name)}
            for name, trained in meta.get("source_sha256", {}).items()
            if (EVAL / name).is_file() and sha256(EVAL / name) != trained
        }
    hashes = {
        str(p.resolve().relative_to(PROJECT.resolve())).replace("\\", "/"): sha256(p)
        for p in sorted(set(files))
    }
    defaults = build_parser().parse_args([])
    cli_fields = ("max_ticks", "decision_interval", "plan_interval", "pure_llm_envelope",
                  "frontend", "rule_fire_policy", "fire_doctrine", "llm_max_tokens",
                  "rl_stochastic", "llm_briefing")
    try:
        git_result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=OPENMD,
            capture_output=True, text=True, check=False)
        git_status = git_result.stdout if git_result.returncode == 0 else "GIT_UNAVAILABLE\n"
    except OSError:
        git_status = "GIT_UNAVAILABLE\n"
    (output / "git_status_tracked.txt").write_text(git_status, encoding="utf-8")
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT), "engine_root": str(ENGINE),
        "imported_engine": str(actual), "python_executable": sys.executable,
        "python_version": sys.version.split()[0], "registry_count": len(registry),
        "scenarios": scenes, "checkpoints": checkpoints, "checkpoint_source_drift": drift,
        "files_sha256": hashes,
        "code_bundle_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        "score_version": "strategy_scorecard.defender_score; require scored_weight != null and natural terminal",
        "score_code_sha256": sha256(EVAL / "strategy_metrics.py"),
        "llm_configuration": {"base_url": "http://172.18.116.170:8000/v1",
                              "backend": "vllm", "model": "Qwen3.8-27B",
                              "max_tokens": 1024, "temperature": 0.1,
                              "enable_thinking": False},
        "cli_defaults": {name: getattr(defaults, name) for name in cli_fields},
        "git_tracked_status_sha256": hashlib.sha256(git_status.encode()).hexdigest(),
        "git_tracked_status_lines": len(git_status.splitlines()),
    }
    save(output / "provenance.json", report)
    return report


def inventory(output: Path) -> dict:
    run_dir = EVAL / "_w1_runs"
    rows = []
    for path in sorted(run_dir.glob("*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(report, dict):
            continue
        scene = str(report.get("scenario", "")).upper()
        if scene not in SCENARIOS or "strategy_scorecard" not in report:
            continue
        score = report.get("strategy_scorecard") or {}
        meta = ((report.get("defender") or {}).get("executor") or {}).get("checkpoint_meta") or {}
        rows.append({
            "path": str(path), "sha256": sha256(path), "scenario": scene,
            "seed": report.get("seed"), "arm": report.get("planner"),
            "ticks_run": report.get("ticks_run"),
            "natural_terminal": report.get("terminal_result") is not None
                                and report.get("aborted") is None,
            "scored_weight": score.get("scored_weight"),
            "defender_score": score.get("defender_score"),
            "checkpoint_tag": meta.get("tag"), "checkpoint_goal_source": meta.get("goal_source"),
            "has_code_hash": "code_hash" in report,
            "has_resolved_hash": "scenario_resolved_hash" in report,
            "has_envelope": "pure_llm_envelope" in report,
            "has_llm_model": "llm_model" in report,
        })
    counts = Counter((r["scenario"], r["arm"], r["seed"]) for r in rows)
    result = {
        "source": str(run_dir), "count": len(rows),
        "confirmatory_seed_201_203_count": sum(r["seed"] in (201, 202, 203) for r in rows),
        "fully_provenanced_natural_terminal_count": sum(
            r["natural_terminal"] and r["scored_weight"] is not None
            and r["has_code_hash"] and r["has_resolved_hash"]
            and r["has_envelope"] and r["has_llm_model"] for r in rows),
        "duplicate_cells": [{"scenario": s, "arm": a, "seed": z, "count": n}
                            for (s, a, z), n in sorted(counts.items()) if n > 1],
        "rows": rows,
    }
    save(output / "existing_inventory.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frozen = freeze(args.output_dir)
    existing = inventory(args.output_dir)
    print(json.dumps({
        "engine": frozen["imported_engine"],
        "scenarios": {k: v["resolved_hash"] for k, v in frozen["scenarios"].items()},
        "hashed_files": len(frozen["files_sha256"]),
        "checkpoint_source_drift_counts": {
            k: len(v) for k, v in frozen["checkpoint_source_drift"].items()},
        "inventory_count": existing["count"],
        "fully_provenanced_natural_terminal_count": existing["fully_provenanced_natural_terminal_count"],
        "output_dir": str(args.output_dir),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

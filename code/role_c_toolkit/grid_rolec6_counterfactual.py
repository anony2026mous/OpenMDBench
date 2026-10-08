"""Grid planner/executor reference substitutions with frozen-goal self-replay.

The reference planner/executor are archived components, NOT certified oracles.
This program reports positive reference improvements and the four-way contrast;
causal/oracle labels stay disabled until independent reference-quality checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from grid_replay import run_episode


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--difficulty", choices=("simple", "medium", "complex"), default="medium")
    parser.add_argument("--task-mode", choices=("independent", "sequential", "continuous"),
                        default="continuous")
    parser.add_argument("--planner", choices=("rule", "llm"), default="rule")
    parser.add_argument("--executor", choices=("heuristic", "mappo"), default="mappo")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Use a new output directory outside source")
    if args.executor == "mappo" and (not args.checkpoint or not args.checkpoint.is_file()):
        raise FileNotFoundError("--checkpoint required for MAPPO")
    if args.planner == "llm" and (not args.base_url or not args.model):
        raise ValueError("LLM planner requires --base-url and --model")
    output.mkdir(parents=True)
    shared = {"seed": args.seed, "difficulty": args.difficulty, "task_mode": args.task_mode,
              "interval": args.interval}
    reports = {}

    def episode(name, *, planner, executor, replay_from=None):
        target = output / name
        report = run_episode(source, target, **shared, planner_kind=planner,
                             executor_kind=executor, mappo_checkpoint=args.checkpoint
                             if executor == "mappo" else None,
                             llm_base_url=args.base_url if planner == "llm" and not replay_from else None,
                             llm_model=args.model if planner == "llm" and not replay_from else None,
                             replay_from=replay_from)
        reports[name] = {"V": report["V"] if report["done"] and not report["aborted"] else None,
                         "done": report["done"], "aborted": report["aborted"],
                         "replay_exact": (report.get("replay_check") or {}).get("exact_match"),
                         "steps": report["steps"], "report_sha256": sha(target / "episode.json"),
                         "trace_sha256": report["trace_sha256"]}
        write(output / "progress.json", reports)
        if reports[name]["V"] is None:
            raise RuntimeError(f"{name} did not reach a valid terminal episode")
        return report

    try:
        original = episode("original", planner=args.planner, executor=args.executor)
        episode("self_replay", planner=args.planner, executor=args.executor,
                replay_from=output / "original" / "episode.json")
        if reports["self_replay"]["replay_exact"] is not True:
            raise RuntimeError("Own-goal replay did not reproduce original")
        # Frozen original goal sequence: only the executor changes.
        episode("reference_executor", planner=args.planner, executor="oracle",
                replay_from=output / "original" / "episode.json")
        # Reference planner remains free to adapt to feedback from the original executor.
        episode("reference_planner", planner="oracle", executor=args.executor)
        episode("reference_full", planner="oracle", executor="oracle")
        v0 = reports["original"]["V"]
        ve = reports["reference_executor"]["V"]
        vp = reports["reference_planner"]["V"]
        vf = reports["reference_full"]["V"]
        result = {"schema": "grid-role-c-6-reference-counterfactual@1",
                  "config": {**shared, "planner": args.planner, "executor": args.executor,
                             "checkpoint_sha256": sha(args.checkpoint) if args.checkpoint else None,
                             "base_url": args.base_url if args.planner == "llm" else None,
                             "model": args.model if args.planner == "llm" else None},
                  "instrumentation_sha256": sha(Path(__file__)),
                  "self_replay_gate": True, "reference_quality_independently_verified": False,
                  "oracle_causal_attribution_validated": False,
                  "reference_improvement_planning": vp - v0,
                  "reference_improvement_execution": ve - v0,
                  "reference_nonadditivity": vf - vp - ve + v0,
                  "full_reference_improvement": vf - v0,
                  "identity_residual": (vp - v0) + (ve - v0) + (vf - vp - ve + v0) - (vf - v0),
                  "reports": reports,
                  "limits": ["Reference components are not independently qualified oracles",
                             "Frozen original goals in executor substitution only",
                             "Diverged trajectories need external-randomness alignment for eventwise claims",
                             "Reference contrasts are not P1 deployed-system P/E/I"]}
        write(output / "summary.json", result)
        print(json.dumps({"output": str(output), "self_replay_gate": True,
                          "planning": vp-v0, "execution": ve-v0,
                          "interaction": vf-vp-ve+v0}))
        return 0
    except Exception as exc:
        write(output / "failed.json", {"reason": f"{type(exc).__name__}: {exc}",
                                       "reports": reports, "self_replay_gate": False,
                                       "oracle_causal_attribution_validated": False})
        raise


if __name__ == "__main__":
    raise SystemExit(main())

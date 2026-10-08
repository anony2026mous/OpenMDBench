"""OpenMDBench command-line interface."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np

from openmdbench.benchmark import run_benchmark_suite
from openmdbench.envs import SurfaceSmokeEnv
from openmdbench.policies.rule_v2 import FormalRuleAgentTeamV2
from openmdbench.replay import ReplayReader, verify_action_replay
from openmdbench.runners.md_ad_002 import (
    run_md_ad_002_easy,
    run_md_ad_002_hard,
    run_md_ad_002_medium,
)
from openmdbench.scenarios.compiler import ScenarioCompiler
from openmdbench.scenarios.formal_v2 import formal_scenario_registry_v2
from openmdbench.scenarios.loader import load_scenario_id
from openmdbench.scenarios.package import ScenarioPackageRef
from openmdbench.selftest import run_selftest
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.soak import run_soak
from openmdbench.visualization import export_png
from openmdbench.visualization.formal_v2 import ViewV2
from openmdbench.visualization.live_formal_v2 import run_live_formal_v2
from openmdbench.visualization.live_match import run_live_md_ad_002
from openmdbench.visualization.playback_v2 import run_replay_formal_v2


def _run_surface_smoke(seed: int, ticks: int) -> dict[str, Any]:
    if ticks <= 0:
        raise ValueError("ticks must be positive")
    env = SurfaceSmokeEnv(world_size_m=100_000.0, max_episode_steps=ticks)
    observation, reset_info = env.reset(seed=seed)
    action = np.array([0.0, 0.0], dtype=np.float32)
    terminated = False
    truncated = False
    completed_ticks = 0
    final_info: dict[str, Any] = reset_info
    for completed_ticks in range(1, ticks + 1):
        observation, _, terminated, truncated, final_info = env.step(action)
        final_info["completed_ticks"] = completed_ticks
        if terminated or truncated:
            break
    return {
        "config_hash": env.config_hash,
        "position": observation["position"].tolist(),
        "scenario": "surface-smoke",
        "seed": seed,
        "terminated": terminated,
        "ticks": completed_ticks,
        "truncated": truncated,
        "distance_to_goal": final_info["distance_to_goal"],
    }


def _run_formal_v2(scenario_id: str, seed: int, ticks: int) -> dict[str, Any]:
    if ticks <= 0:
        raise ValueError("ticks must be positive")
    session = (
        create_formal_session_v2(
            scenario_id,
            session_id=f"cli.{scenario_id.lower()}.{seed}",
            seed=seed,
        )
        .load()
        .start()
    )
    rule_team = FormalRuleAgentTeamV2.for_scenario(scenario_id, seed=seed)
    try:
        for tick in range(ticks):
            rule_team(session)
            session.step(operation_id=f"cli.tick.{tick:08d}", expected_tick=tick)
        checkpoint = session.checkpoint()
        result = session.world_view.checkpoint().mission_scoring_checkpoint
        return {
            "schema_version": "formal-run@2.0",
            "scenario": scenario_id,
            "resolved_scenario_id": session.resolved.scenario_id,
            "resolved_hash": session.resolved.resolved_hash,
            "seed": seed,
            "ticks": session.world_view.tick,
            "active_entities": len(session.world_view.entities_stable()),
            "terminal_result": None if result is None else result.get("terminal_result"),
            "score_state": {} if result is None else result.get("score_state", {}),
            "checkpoint_hash": checkpoint.checkpoint_hash,
        }
    finally:
        session.stop().close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m openmdbench.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run a headless scenario")
    run_parser.add_argument(
        "--scenario",
        required=True,
        choices=["surface-smoke", *formal_scenario_registry_v2()],
    )
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--ticks", type=int, default=1_000)
    replay_parser = subparsers.add_parser("replay", help="render a standard replay")
    replay_parser.add_argument("path")
    replay_parser.add_argument("--headless", action="store_true")
    replay_parser.add_argument("--output", required=True)
    replay_parser.add_argument("--timestamp", type=int)
    replay_parser.add_argument(
        "--view", choices=["referee", "blue", "red", "public"], default="referee"
    )
    replay_v2_parser = subparsers.add_parser(
        "replay-v2", help="play a rich schema-v2 visualization artifact"
    )
    replay_v2_parser.add_argument("path")
    replay_v2_parser.add_argument("--speed", type=float, default=20.0)
    verify_parser = subparsers.add_parser("verify-replay", help="re-simulate replay actions")
    verify_parser.add_argument("path")
    benchmark_parser = subparsers.add_parser("benchmark", help="run fixed CPU benchmarks")
    benchmark_parser.add_argument("--output")
    soak_parser = subparsers.add_parser("soak", help="run session stability soak")
    soak_parser.add_argument("--hours", type=float, default=12.0)
    soak_parser.add_argument("--minimum-sessions", type=int, default=1_000)
    soak_parser.add_argument("--output")
    selftest_parser = subparsers.add_parser(
        "selftest", help="run and archive release or scenario self-tests"
    )
    selftest_parser.add_argument(
        "--scenario",
        choices=["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"],
    )
    selftest_parser.add_argument("--seed", type=int, default=7)
    selftest_parser.add_argument("--ticks", type=int, default=1_800)
    live_parser = subparsers.add_parser("live", help="run a tick-by-tick interactive match")
    live_parser.add_argument(
        "--scenario",
        required=True,
        choices=[
            "MD-AD-002-EASY",
            "MD-AD-002-MEDIUM",
            "MD-AD-002-HARD",
        ],
    )
    live_parser.add_argument("--seed", type=int, default=73)
    live_parser.add_argument("--speed", type=float, default=10.0)
    live_parser.add_argument(
        "--render-fps",
        type=float,
        default=12.0,
        help="maximum live GUI refresh rate; does not change simulation ticks",
    )
    live_parser.add_argument("--ticks", type=int, default=1_800)
    live_parser.add_argument(
        "--view", choices=["referee", "faction", "blue", "red", "public"], default="referee"
    )
    live_parser.add_argument("--map-extent", choices=["full", "task"], default="task")
    live_parser.add_argument("--faction-id")
    live_parser.add_argument("--replay-output")
    for command in ("validate", "resolve", "inspect"):
        scenario_parser = subparsers.add_parser(
            f"scenario-{command}", help=f"{command} a declarative scenario package"
        )
        scenario_parser.add_argument("root")
        scenario_parser.add_argument("--scenario", default="scenario.yaml")
        scenario_parser.add_argument("--component", default="composition.yaml")
        scenario_parser.add_argument("--catalog", action="append", default=[])
        if command == "resolve":
            scenario_parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command in {"scenario-validate", "scenario-resolve", "scenario-inspect"}:
        ref = ScenarioPackageRef(
            root=Path(args.root),
            scenario=args.scenario,
            component=args.component,
            catalogs=tuple(args.catalog),
        )
        compiler = ScenarioCompiler()
        if args.command == "scenario-validate":
            issues = compiler.validate_package(ref)
            print(json.dumps([asdict(issue) for issue in issues], indent=2, sort_keys=True))
            return 1 if issues else 0
        resolved = compiler.compile_package(ref)
        if args.command == "scenario-inspect":
            print(json.dumps(compiler.inspect(resolved), indent=2, sort_keys=True))
            return 0
        encoded = resolved.to_json()
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(encoded + "\n", encoding="utf-8")
        else:
            print(encoded)
        return 0
    if args.command == "run" and args.scenario == "surface-smoke":
        print(json.dumps(_run_surface_smoke(args.seed, args.ticks), sort_keys=True))
        return 0
    if args.command == "run" and args.scenario in formal_scenario_registry_v2():
        print(json.dumps(_run_formal_v2(args.scenario, args.seed, args.ticks), sort_keys=True))
        return 0
    if args.command == "live":
        live_result: Any
        if args.scenario in formal_scenario_registry_v2():
            if args.view not in {"referee", "faction", "public"}:
                raise ValueError("formal V2 visualization view must be referee, faction, or public")
            replay_path = None if args.replay_output is None else Path(args.replay_output)
            run_live_formal_v2(
                args.scenario,
                seed=args.seed,
                speed=args.speed,
                render_fps=args.render_fps,
                max_ticks=args.ticks,
                replay_path=replay_path,
                view=cast(ViewV2, args.view),
                faction_id=args.faction_id,
            )
            print(
                json.dumps(
                    {
                        "scenario": args.scenario,
                        "renderer": "formal-v2",
                        "replay": args.replay_output,
                    },
                    sort_keys=True,
                )
            )
            return 0
        else:
            live_result = run_live_md_ad_002(
                scenario_id=args.scenario,
                seed=args.seed,
                speed=args.speed,
                view=args.view,
                map_extent=args.map_extent,
                max_ticks=args.ticks,
            )
        print(json.dumps(asdict(live_result), sort_keys=True))
        return 0
    if args.command == "replay-v2":
        run_replay_formal_v2(Path(args.path), speed=args.speed)
        return 0
    if args.command == "replay":
        if not args.headless:
            raise ValueError("the current replay CLI requires --headless")
        reader = ReplayReader(args.path)
        frame = (
            reader.seek(args.timestamp)
            if args.timestamp is not None
            else next(reversed(tuple(reader.frames())))
        )
        scenario = load_scenario_id(reader.metadata.scenario_id)
        world_bounds = scenario.world.bounds
        export_png(
            frame,
            args.output,
            view=args.view,
            world_bounds=world_bounds,
        )
        print(json.dumps({"output": args.output, "timestamp": frame.timestamp, "view": args.view}))
        return 0
    if args.command == "verify-replay":
        report = verify_action_replay(ReplayReader(args.path))
        print(json.dumps(asdict(report), sort_keys=True))
        return 0 if report.matched else 1
    if args.command == "benchmark":
        result = run_benchmark_suite()
        encoded = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
        return 0
    if args.command == "soak":
        result = run_soak(
            duration_seconds=args.hours * 3_600.0,
            minimum_sessions=args.minimum_sessions,
        )
        encoded = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
        return 0
    if args.command == "selftest":
        if args.scenario in {
            "MD-AD-002-EASY",
            "MD-AD-002-MEDIUM",
            "MD-AD-002-HARD",
        }:
            difficulty = args.scenario.rsplit("-", 1)[-1].lower()
            log_path = Path(f"artifacts/md-ad-002/{difficulty}-selftest.jsonl.gz")
            runners = {
                "MD-AD-002-EASY": run_md_ad_002_easy,
                "MD-AD-002-MEDIUM": run_md_ad_002_medium,
                "MD-AD-002-HARD": run_md_ad_002_hard,
            }
            runner = runners[args.scenario]
            # Third-party MMG/Taichi initialization writes banners to stdout.
            with contextlib.redirect_stdout(sys.stderr):
                match = runner(seed=args.seed, max_ticks=args.ticks, log_path=log_path)
            result = {
                "passed": match.outcome != "in_progress",
                "scenario_id": args.scenario,
                "seed": args.seed,
                "ticks": match.ticks,
                "outcome": match.outcome,
                "reason": match.reason,
                "breaches": match.breaches,
                "total_score": match.score.total_score,
                "safety_score": match.score.safety_score,
                "artifacts": {"authority_log": str(log_path)},
            }
        else:
            result = run_selftest()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())

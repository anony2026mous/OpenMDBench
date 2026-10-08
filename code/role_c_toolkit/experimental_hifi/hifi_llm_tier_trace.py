"""Trace an actual LLM-planner + GOAI-executor episode with replay support.

Unlike ``hifi_tier_trace.py`` (the rule baseline), this runner invokes the
engine's ``run_episode.py --planner llm`` path. Replay freezes submitted Goal
commands after constructing the same hybrid agent; it never calls the LLM.
This file does not modify the engine or the active rule campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

from hifi_trace import (TraceContext, TracedSession, canonical, entities,
                        file_hash, plain, source_manifest)


def safe_llm_settings(source: Path, base_url: str | None, model: str | None,
                      max_tokens: int) -> dict:
    """Resolve and record non-secret LLM settings; never read/emit API keys."""
    env = {}
    env_path = source / "code" / ".env"
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.strip() in {"OPENAI_BASE_URL", "LLM_DEFAULT_MODEL"}:
                    env[key.strip()] = value.strip()
    resolved_url = (base_url or os.environ.get("OPENAI_BASE_URL") or
                    env.get("OPENAI_BASE_URL", "http://localhost:8000/v1")).rstrip("/")
    return {"base_url": resolved_url,
            "model": model or os.environ.get("LLM_DEFAULT_MODEL") or
            env.get("LLM_DEFAULT_MODEL", "Qwen3.5-122B-A10B-FP8"),
            "max_tokens": max_tokens}


class TierTraceContext(TraceContext):
    def __init__(self, *args, tier: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.tier = tier
        self.llm_client = None

    def attach_agent(self, agent):
        agent.goal_granularity = self.tier
        self.llm_client = getattr(agent.planner, "llm", None)
        return super().attach_agent(agent)

    def llm_stats(self):
        if self.llm_client is None:
            return None
        try:
            return plain(self.llm_client.get_stats())
        except Exception as exc:
            return {"stats_error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--ticks", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--tier", choices=("weak", "medium", "strong"), required=True)
    parser.add_argument("--world-checkpoint-interval", type=int, default=50)
    parser.add_argument("--step-timeout", type=float, default=300.0)
    parser.add_argument("--replay-from", type=Path)
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-max-tokens", type=int, default=1024)
    args = parser.parse_args()

    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Use a new output directory outside the engine source")
    if min(args.ticks, args.interval, args.world_checkpoint_interval,
           args.llm_max_tokens) < 1 or args.step_timeout <= 0:
        raise ValueError("Positive ticks, intervals, timeout and token budget required")

    hashes = source_manifest(source)
    settings = safe_llm_settings(source, args.llm_base_url, args.llm_model,
                                 args.llm_max_tokens)
    config = {"scenario": args.scenario, "seed": args.seed, "max_ticks": args.ticks,
              "plan_interval": args.interval, "planner": "llm",
              "goal_granularity": args.tier, "llm": settings,
              "world_checkpoint_interval": args.world_checkpoint_interval,
              "runner_step_timeout_seconds": args.step_timeout}
    baseline = replay = None
    if args.replay_from:
        baseline = json.loads(args.replay_from.resolve().read_text(encoding="utf-8"))
        if baseline.get("aborted") or baseline.get("config") != config or baseline.get("source_hashes") != hashes:
            raise ValueError("Replay requires same LLM/tier/config and unchanged engine source")
        replay = {row["tick"]: row for row in baseline["decisions"]}
        if len(replay) != len(baseline["decisions"]):
            raise ValueError("Duplicate decision tick in replay source")

    sys.path[:0] = [str(source / "code" / "eval"),
                    str(source / "source-code" / "source_codes")]
    import run_episode as runner

    original_factory, original_builder = runner.create_formal_session_v2, runner._build_defender
    output.mkdir(parents=True)
    error = None
    trace_path = output / "events.jsonl"
    with trace_path.open("x", encoding="utf-8") as stream:
        context = TierTraceContext(stream, replay, args.world_checkpoint_interval,
                                   tier=args.tier)
        runner.create_formal_session_v2 = lambda *a, **kw: TracedSession(
            original_factory(*a, **kw), context)
        runner._build_defender = lambda *a, **kw: context.attach_agent(
            original_builder(*a, **kw))
        argv = ["run_episode.py", "--scenario", args.scenario, "--seed", str(args.seed),
                "--max-ticks", str(args.ticks), "--planner", "llm",
                "--plan-interval", str(args.interval), "--goal-granularity", args.tier,
                "--step-timeout", str(args.step_timeout),
                "--checkpoint-dir", str(output / "checkpoints"),
                "--checkpoint-tick", str(args.ticks + 1),
                "--llm-max-tokens", str(args.llm_max_tokens),
                "--output", str(output / "engine_result.json"),
                "--log", str(output / "runner.jsonl")]
        if args.llm_base_url:
            argv += ["--llm-base-url", args.llm_base_url]
        if args.llm_model:
            argv += ["--llm-model", args.llm_model]
        old_argv = sys.argv
        sys.argv = argv
        try:
            runner.main()
        except Exception as exc:  # preserve partial trace and explicit failure
            error = f"{type(exc).__name__}: {exc}"
            context.log({"kind": "instrumentation_error", "error": error})
        finally:
            sys.argv = old_argv
            runner.create_formal_session_v2, runner._build_defender = original_factory, original_builder

    engine_path = output / "engine_result.json"
    engine = json.loads(engine_path.read_text(encoding="utf-8")) if engine_path.is_file() else {}
    aborted = error or engine.get("aborted") or ("missing_engine_result" if not engine else None)
    unchanged = hashes == source_manifest(source)
    if not unchanged:
        aborted = "source_changed_during_run"
    fingerprints = context.fingerprints
    replay_check = None
    if baseline is not None:
        replay_check = {"same_length": len(fingerprints) == len(baseline["fingerprints"]),
                        "step_fingerprints_identical": fingerprints == baseline["fingerprints"],
                        "decisions_identical": context.decisions == baseline["decisions"]}
        replay_check["exact_match"] = not aborted and all(replay_check.values())

    result = {"schema": "role-c-hifi-trace@2", "config": config,
              "aborted": aborted,
              "runtime": {"python": sys.version, "executable": sys.executable,
                          "platform": platform.platform()},
              "source_hashes": hashes, "source_unchanged": unchanged,
              "instrumentation_sha256": file_hash(Path(__file__)),
              "base_trace_helper_sha256": file_hash(Path(__file__).with_name("hifi_trace.py")),
              "decisions": context.decisions, "fingerprints": fingerprints,
              "trace_sha256": file_hash(trace_path), "replay_check": replay_check,
              "terminal_result": engine.get("terminal_result"),
              "ticks_run": engine.get("ticks_run"),
              "replay_source_sha256": file_hash(args.replay_from.resolve()) if args.replay_from else None,
              "llm_client_stats": context.llm_stats(),
              "planner_diagnostics": engine.get("defender", {}).get("planner"),
              "layered_metrics": engine.get("layered_metrics"),
              "formal_B_if_validated": False, "formal_attribution_validated": False}
    report_path = output / "measurement_episode.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(canonical({"output": str(output), "planner": "llm", "tier": args.tier,
                     "aborted": aborted, "ticks": result["ticks_run"],
                     "replay_check": replay_check,
                     "planner_diagnostics": result["planner_diagnostics"]}))
    return int(bool(aborted) or (replay_check is not None and not replay_check["exact_match"]))


if __name__ == "__main__":
    raise SystemExit(main())

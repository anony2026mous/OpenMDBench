"""Run one complete, hash-locked 6.0 P1 episode; never edit the engine."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from toolkit_paths import PROJECT, ENGINE, EVAL
WEIGHTS = {
    "rl": "theta_rl_legacy2.npz",
    "rule-rl": "theta_arm5_v12.npz",
    "llm-rl": "theta_arm5_llm_reward_v9.npz",
}
BASE_URL = os.environ.get("ROLEC_LLM_BASE_URL", "http://172.18.116.170:8000/v1")
MODEL = os.environ.get("ROLEC_LLM_MODEL", "Qwen3.8-27B")
ARMS = ("rule", "llm", "rule-rl", "llm-rl", "rl", "pure-llm")
SCENARIOS = ("IE-04-COMBINED-ARMS", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_freeze(provenance: dict, scenario: str) -> None:
    expected_engine = ENGINE / "openmdbench"
    import openmdbench
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

    if Path(openmdbench.__file__).resolve().parent != expected_engine.resolve():
        raise RuntimeError("Imported engine is not the selected 6.0 tree")
    for relative, expected in provenance["files_sha256"].items():
        path = PROJECT / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Frozen source/scene drift: {relative}")
    for arm, item in provenance["checkpoints"].items():
        if sha256(Path(item["path"])) != item["sha256"]:
            raise RuntimeError(f"Checkpoint drift: {arm}")
    for relative, expected in provenance["extra_files_sha256"].items():
        path = PROJECT / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Additional P1 source drift: {relative}")
    resolved, _catalog = compile_formal_scenario_v2(scenario)
    if resolved.resolved_hash != provenance["scenarios"][scenario]["resolved_hash"]:
        raise RuntimeError("Resolved scenario changed after campaign lock")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--goal-granularity", choices=("weak", "medium", "strong"),
                        default="strong")
    parser.add_argument("--max-ticks", type=int, default=1800)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if args.max_ticks < 1200 or args.attempt < 1:
        parser.error("P1 requires max-ticks >= 1200 and attempt >= 1")
    os.environ["OPENMDBENCH_ROOT"] = str(ENGINE)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))

    from llm_client_hifi import LLMClient
    from run_episode import _RunLog, build_parser, run_episode

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    provenance = load(out / "provenance.json")
    config = load(out / "toolkit_config.json")
    if (args.scenario not in config["scenarios"] or args.seed not in config["seeds"]
            or args.arm not in config["arms"]
            or args.goal_granularity != config["goal_granularity"]
            or args.max_ticks != config["max_ticks"]
            or BASE_URL != config["base_url"] or MODEL != config["model"]):
        raise RuntimeError("Episode parameters differ from the frozen toolkit_config.json")
    verify_freeze(provenance, args.scenario)
    run_id = f"{args.scenario.lower().replace('-', '_')}_{args.arm}_s{args.seed}_a{args.attempt}"
    paths = {
        "manifest": out / f"{run_id}_manifest.json",
        "report": out / f"{run_id}.json",
        "events": out / f"{run_id}.jsonl",
        "requests": out / f"{run_id}_requests.jsonl",
        "checkpoint_dir": out / "checkpoints" / run_id,
    }
    if any(paths[key].exists() for key in ("manifest", "report", "events", "requests")):
        raise FileExistsError(f"Refusing to overwrite existing P1 cell: {run_id}")
    argv = [
        "--scenario", args.scenario, "--seed", str(args.seed),
        "--planner", args.arm, "--max-ticks", str(args.max_ticks),
        "--pure-llm-envelope", "executor", "--frontend", "graph",
        "--llm-briefing", "withheld", "--llm-backend", "vllm",
        "--llm-base-url", BASE_URL, "--llm-model", MODEL,
        "--llm-max-tokens", "1024", "--plan-interval", "10",
        "--decision-interval", "5", "--rl-speed-source", "legacy_tags",
        "--checkpoint-dir", str(paths["checkpoint_dir"]),
    ]
    if args.arm in WEIGHTS:
        argv.extend(("--rl-theta", str(EVAL / "_w1_runs" / "rl" / WEIGHTS[args.arm])))
    if args.arm in ("rule-rl", "llm-rl"):
        argv.extend(("--goal-granularity", args.goal_granularity))
    run_args = build_parser().parse_args(argv)
    manifest = {
        "run_id": run_id, "status": "running", "created_utc": utc_now(),
        "scenario": args.scenario, "seed": args.seed, "arm": args.arm,
        "goal_granularity": args.goal_granularity,
        "attempt": args.attempt, "output_tag": out.name, "cli_argv": argv,
        "scenario_resolved_hash": provenance["scenarios"][args.scenario]["resolved_hash"],
        "code_bundle_sha256": provenance["code_bundle_sha256"],
        "wrapper_sha256": sha256(Path(__file__)),
        "checkpoint_sha256": (provenance["checkpoints"][args.arm]["sha256"]
                              if args.arm in WEIGHTS else None),
        "checkpoint_meta": (provenance["checkpoints"][args.arm]["meta"]
                            if args.arm in WEIGHTS else None),
        "model": MODEL if args.arm in ("llm", "llm-rl", "pure-llm") else None,
        "backend": "vllm" if args.arm in ("llm", "llm-rl", "pure-llm") else None,
        "base_url": BASE_URL if args.arm in ("llm", "llm-rl", "pure-llm") else None,
        "temperature": 0.1, "max_tokens": 1024, "plan_interval": 10,
        "decision_interval": 5, "speed_source": "legacy_tags" if args.arm in WEIGHTS else None,
        "rl_stochastic": False, "pure_llm_envelope": "executor",
        "frontend": "graph", "llm_briefing": "withheld",
        "score_version": "strategy_scorecard.defender_score; natural terminal and scored_weight != null",
        "score_code_sha256": provenance["score_code_sha256"],
    }
    save(paths["manifest"], manifest)
    calls = 0
    original_chat = LLMClient.chat
    with paths["requests"].open("w", encoding="utf-8", buffering=1) as request_stream:
        def capture_and_forward(client, system_prompt, user_message,
                                max_tokens=None, temperature=0.1):
            nonlocal calls
            if (client.base_url, client.model, client.backend) != (BASE_URL, MODEL, "vllm"):
                raise RuntimeError("LLM destination differs from locked endpoint/model")
            index = calls
            calls += 1
            started = time.perf_counter()
            request_stream.write(json.dumps({
                "kind": "request", "call_index": index, "timestamp_utc": utc_now(),
                "base_url": client.base_url, "model": client.model,
                "backend": client.backend, "temperature": temperature,
                "max_tokens": max_tokens, "system_prompt": system_prompt,
                "user_message": user_message,
            }, ensure_ascii=False) + "\n")
            try:
                response = original_chat(client, system_prompt, user_message,
                                         max_tokens=max_tokens, temperature=temperature)
            except Exception as exc:
                request_stream.write(json.dumps({
                    "kind": "error", "call_index": index, "timestamp_utc": utc_now(),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": f"{type(exc).__name__}: {exc}",
                }, ensure_ascii=False) + "\n")
                raise
            request_stream.write(json.dumps({
                "kind": "response", "call_index": index, "timestamp_utc": utc_now(),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                "response": response,
            }, ensure_ascii=False) + "\n")
            return response

        LLMClient.chat = capture_and_forward
        try:
            report = run_episode(run_args, _RunLog(paths["events"]))
        except Exception as exc:
            manifest.update(status="exception", finished_utc=utc_now(),
                            exception=f"{type(exc).__name__}: {exc}", llm_calls=calls)
            save(paths["manifest"], manifest)
            raise
        finally:
            LLMClient.chat = original_chat

    save(paths["report"], report)
    score = report.get("strategy_scorecard") or {}
    terminal = report.get("terminal_result") is not None and report.get("aborted") is None
    score_ok = score.get("scored_weight") is not None and score.get("defender_score") is not None
    manifest.update({
        "status": "complete" if terminal and score_ok else "ineligible",
        "finished_utc": utc_now(), "ticks_run": report.get("ticks_run"),
        "terminal_result": report.get("terminal_result"), "aborted": report.get("aborted"),
        "natural_terminal": terminal, "scored_weight": score.get("scored_weight"),
        "defender_score": score.get("defender_score"),
        "eligible_for_main_score": terminal and score_ok,
        "llm_calls": calls, "report_sha256": sha256(paths["report"]),
        "events_sha256": sha256(paths["events"]),
        "requests_sha256": sha256(paths["requests"]),
    })
    save(paths["manifest"], manifest)
    print(json.dumps({key: manifest[key] for key in (
        "run_id", "status", "ticks_run", "natural_terminal", "defender_score",
        "llm_calls", "aborted")}, ensure_ascii=False), flush=True)
    return 0 if manifest["eligible_for_main_score"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""6.0 P0 endpoint probe and one/two-tick interface smoke with exact LLM capture."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from toolkit_paths import PROJECT, ENGINE, EVAL
CHECKPOINTS = EVAL / "_w1_runs" / "rl"
BASE_URL = os.environ.get("ROLEC_LLM_BASE_URL", "http://172.18.116.170:8000/v1").rstrip("/")
MODEL = os.environ.get("ROLEC_LLM_MODEL", "Qwen3.8-27B")
WEIGHTS = {"rl": "theta_rl_legacy2.npz", "rule-rl": "theta_arm5_v12.npz",
           "llm-rl": "theta_arm5_llm_reward_v9.npz"}
ARMS = ("rule", "llm", "rule-rl", "llm-rl", "rl", "pure-llm")


def goal_cli_args(arm: str, granularity: str | None) -> list[str]:
    # Match p1_6_run.py: the controlled Goal tier applies to combined RL arms.
    if arm in ("rule-rl", "llm-rl") and granularity is not None:
        return ["--goal-granularity", granularity]
    return []


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8")


def probe(output: Path) -> None:
    start = time.perf_counter()
    response = requests.get(BASE_URL + "/models", timeout=10)
    response.raise_for_status()
    models = [item.get("id") for item in response.json().get("data", ())]
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "url": BASE_URL + "/models", "status": response.status_code,
              "latency_ms": round((time.perf_counter() - start) * 1000, 1),
              "models": models, "required_model_present": MODEL in models}
    save(output / "endpoint_probe.json", result)
    print(json.dumps(result, ensure_ascii=False))
    if MODEL not in models:
        raise RuntimeError(f"Required model {MODEL} is absent")


def smoke(args: argparse.Namespace) -> None:
    os.environ["OPENMDBENCH_ROOT"] = str(ENGINE)
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    import openmdbench
    from llm_client_hifi import LLMClient
    from run_episode import _RunLog, build_parser, run_episode

    imported = Path(openmdbench.__file__).resolve().parent
    if imported != (ENGINE / "openmdbench").resolve():
        raise RuntimeError(f"Wrong engine tree: {imported}")
    slug = args.scenario.lower().replace("-", "_")
    run_id = f"{slug}_{args.arm}_s{args.seed}_t{args.ticks}"
    if args.tag:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", args.tag):
            raise ValueError("--tag must contain only letters, digits, underscore or dash")
        run_id += f"_{args.tag}"
    out = args.output_dir
    if (out / f"{run_id}.json").exists():
        raise FileExistsError(f"Refusing to overwrite existing P0 smoke: {run_id}")
    argv = ["--scenario", args.scenario, "--seed", str(args.seed),
            "--planner", args.arm, "--max-ticks", str(args.ticks),
            "--pure-llm-envelope", "executor", "--frontend", "graph",
            "--llm-briefing", "withheld", "--llm-backend", "vllm",
            "--llm-base-url", BASE_URL, "--llm-model", MODEL,
            "--llm-max-tokens", "1024", "--plan-interval", "10",
            "--decision-interval", "5", "--rl-speed-source", "legacy_tags",
            "--checkpoint-dir", str(out / "checkpoints")]
    if args.arm in WEIGHTS:
        argv += ["--rl-theta", str(CHECKPOINTS / WEIGHTS[args.arm])]
    argv += goal_cli_args(args.arm, getattr(args, "goal_granularity", None))
    run_args = build_parser().parse_args(argv)
    calls = []
    original_chat = LLMClient.chat

    def capture_and_forward(client, system_prompt, user_message,
                            max_tokens=None, temperature=0.1):
        if (client.base_url, client.model, client.backend) != (BASE_URL, MODEL, "vllm"):
            raise RuntimeError("LLM destination differs from approved endpoint/model")
        row = {
            "base_url": client.base_url, "model": client.model,
            "backend": client.backend, "enable_thinking": client.enable_thinking,
            "max_tokens": max_tokens, "effective_max_tokens": max_tokens or client.max_tokens,
            "temperature": temperature,
            "system_prompt": system_prompt, "user_message": user_message,
            "contact_ids_in_prompt": sorted(set(re.findall(
                r"contact-red-[0-9]+|sensor\.contact\.[A-Za-z0-9_.-]+", user_message))),
        }
        calls.append(row)
        start = time.perf_counter()
        try:
            answer = original_chat(client, system_prompt, user_message,
                                   max_tokens=max_tokens, temperature=temperature)
            row["response"] = answer
            return answer
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            row["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)

    LLMClient.chat = capture_and_forward
    try:
        report = run_episode(run_args, _RunLog(out / f"{run_id}.jsonl"))
    finally:
        LLMClient.chat = original_chat
        save(out / f"{run_id}_requests.json", calls)
    save(out / f"{run_id}.json", report)
    provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
    expected_llm_calls = ((args.ticks - 1) // 10 + 1
                          if args.arm in ("llm", "llm-rl", "pure-llm") else 0)
    result = {
        "run_id": run_id, "scenario": args.scenario, "seed": args.seed,
        "arm": args.arm, "ticks_requested": args.ticks,
        "ticks_run": report.get("ticks_run"), "llm_calls_captured": len(calls),
        "expected_llm_calls": expected_llm_calls,
        "aborted": report.get("aborted"), "terminal_result": report.get("terminal_result"),
        "code_bundle_sha256": provenance["code_bundle_sha256"],
        "wrapper_sha256": sha256(Path(__file__)),
        "scenario_resolved_hash": provenance["scenarios"][args.scenario]["resolved_hash"],
        "checkpoint_sha256": (provenance["checkpoints"][args.arm]["sha256"]
                              if args.arm in WEIGHTS else None),
        "cli_argv": argv, "report_sha256": sha256(out / f"{run_id}.json"),
        "log_sha256": sha256(out / f"{run_id}.jsonl"),
        "requests_sha256": sha256(out / f"{run_id}_requests.json"),
        "interface_ok": report.get("aborted") is None
                        and len(calls) == expected_llm_calls
                        and report.get("ticks_run") == args.ticks,
        "not_a_terminal_score": report.get("terminal_result") is None,
    }
    save(out / f"{run_id}_manifest.json", result)
    print(json.dumps({key: result[key] for key in (
        "run_id", "ticks_run", "llm_calls_captured", "aborted", "interface_ok",
        "not_a_terminal_score")}, ensure_ascii=False))
    if not result["interface_ok"]:
        raise RuntimeError(f"P0 interface smoke did not satisfy its one/two-tick gate: {run_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--scenario", default="IE-10-DUAL-AXIS-PINCER")
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--seed", type=int, default=9901)
    parser.add_argument("--ticks", type=int, default=1)
    parser.add_argument("--tag", default="")
    parser.add_argument("--goal-granularity", choices=("weak", "medium", "strong"), default=None)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.probe:
        probe(args.output_dir)
    elif args.arm:
        smoke(args)
    else:
        parser.error("Choose --probe or --arm")


if __name__ == "__main__":
    main()

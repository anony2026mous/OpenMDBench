"""Run independent LLM-planned formal episodes with isolated result files.

Example:
    python parallel_episodes.py --scenario IE-01-SINGLE-TARGET \
      --seeds 11 12 --parallel 2 --max-ticks 12 \
      --llm-base-urls http://127.0.0.1:8101/v1 http://127.0.0.1:8102/v1 \
      --output-dir /root/openmd/runs/llm-batch
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def run_one(args: argparse.Namespace, seed: int, base_url: str) -> dict:
    run_dir = args.output_dir / f"seed-{seed}"
    run_dir.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable, str(Path(__file__).with_name("run_episode.py")),
        "--scenario", args.scenario, "--planner", "llm",
        "--seed", str(seed), "--max-ticks", str(args.max_ticks),
        "--llm-base-url", base_url, "--llm-model", args.llm_model,
        "--llm-max-tokens", str(args.llm_max_tokens),
        "--output", str(run_dir / "report.json"),
        "--log", str(run_dir / "episode.jsonl"),
        "--checkpoint-dir", str(run_dir / "checkpoints"),
    ]
    environment = dict(os.environ)
    environment.update(PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg",
                       MPLCONFIGDIR=str(args.output_dir / "mpl"))
    start = time.time()
    try:
        with (run_dir / "stdout.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(
                command, cwd=run_dir, env=environment,
                stdout=log, stderr=subprocess.STDOUT, check=False,
                timeout=args.timeout,
            )
        exit_code = process.returncode
        error = None
    except subprocess.TimeoutExpired:
        exit_code = None
        error = f"timed out after {args.timeout} seconds"
    report_path = run_dir / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    planner = report.get("defender", {}).get("planner", {})
    return {
        "seed": seed, "llm_base_url": base_url,
        "started": start, "ended": time.time(),
        "exit_code": exit_code, "error": error,
        "ticks_run": report.get("ticks_run"),
        "aborted": report.get("aborted"),
        "plan_calls": planner.get("plan_calls"),
        "parse_failures": planner.get("parse_failures"),
        "fallback_count": planner.get("fallback_count"),
        "report": str(report_path),
        "log": str(run_dir / "stdout.log"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--max-ticks", type=int, default=1800)
    parser.add_argument("--llm-base-urls", nargs="+", required=True)
    parser.add_argument("--llm-model", default="Qwen3.8-27B")
    parser.add_argument("--llm-max-tokens", type=int, default=1024)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=7200,
                        help="Maximum wall time per episode, in seconds")
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds must contain unique values")
    if min(args.parallel, args.max_ticks, args.llm_max_tokens, args.timeout) < 1:
        parser.error("--parallel, --max-ticks, --llm-max-tokens and --timeout must be positive")
    args.output_dir = args.output_dir.resolve()
    repo = Path(__file__).resolve().parents[3]
    if args.output_dir == repo or repo in args.output_dir.parents:
        parser.error("--output-dir must be outside the source tree")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any((args.output_dir / f"seed-{seed}").exists() for seed in args.seeds):
        parser.error("one or more seed result directories already exist")

    results = []
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(run_one, args, seed,
                        args.llm_base_urls[seed % len(args.llm_base_urls)]): seed
            for seed in args.seeds
        }
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as error:
                seed = futures[future]
                result = {
                    "seed": seed, "exit_code": None,
                    "aborted": "launcher_error", "plan_calls": None,
                    "parse_failures": None,
                    "error": f"{type(error).__name__}: {error}",
                }
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    results.sort(key=lambda item: item["seed"])
    summary = {"scenario": args.scenario, "results": results}
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if any(
        row["exit_code"] != 0 or row["aborted"] is not None or
        not row["plan_calls"] or row["parse_failures"]
        for row in results
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())

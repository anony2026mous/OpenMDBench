"""Sequential terminal campaign for real LLM+GOAI Goal-granularity tiers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from hifi_replay_campaign import SCENARIOS
from hifi_llm_tier_trace import safe_llm_settings


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], log: Path, timeout: int):
    with log.open("x", encoding="utf-8") as stream:
        try:
            return subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=timeout,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
        except subprocess.TimeoutExpired:
            return "timeout"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario", action="append", choices=SCENARIOS, required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--ticks", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--episode-timeout", type=int, default=14400)
    parser.add_argument("--step-timeout", type=float, default=300.0)
    parser.add_argument("--world-checkpoint-interval", type=int, default=50)
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-max-tokens", type=int, default=1024)
    parser.add_argument("--require-terminal", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Use a new output directory outside the engine source")
    if len(set(args.scenario)) != len(args.scenario) or len(set(args.seed)) != len(args.seed):
        raise ValueError("Repeated scenario or seed")

    script = Path(__file__).with_name("hifi_llm_tier_trace.py")
    campaign_hash, trace_hash = sha(Path(__file__)), sha(script)
    settings = safe_llm_settings(source, args.llm_base_url, args.llm_model,
                                 args.llm_max_tokens)
    output.mkdir(parents=True)
    entries = []
    for scenario in args.scenario:
        alias = f"IE-{SCENARIOS.index(scenario) + 1:02d}"
        for seed in args.seed:
            for tier in ("weak", "medium", "strong"):
                stem = output / alias / f"seed-{seed}" / tier
                stem.mkdir(parents=True)
                pair = {}
                for kind in ("original", "replay"):
                    if kind == "replay" and not pair.get("original_valid"):
                        pair["replay_skipped"] = "original_failed"
                        break
                    target = stem / kind
                    cmd = [sys.executable, "-B", "-X", "utf8", str(script),
                           "--source", str(source), "--output", str(target),
                           "--scenario", scenario, "--seed", str(seed),
                           "--ticks", str(args.ticks), "--interval", str(args.interval),
                           "--step-timeout", str(args.step_timeout),
                           "--world-checkpoint-interval", str(args.world_checkpoint_interval),
                           "--tier", tier, "--llm-max-tokens", str(args.llm_max_tokens)]
                    if args.llm_base_url:
                        cmd += ["--llm-base-url", args.llm_base_url]
                    if args.llm_model:
                        cmd += ["--llm-model", args.llm_model]
                    if kind == "replay":
                        cmd += ["--replay-from", str(stem / "original" / "measurement_episode.json")]
                    code = run(cmd, stem / f"{kind}.console.log", args.episode_timeout)
                    report_path = target / "measurement_episode.json"
                    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
                    config = report.get("config", {})
                    terminal = report.get("terminal_result") is not None
                    pair[kind] = {"returncode": code, "aborted": report.get("aborted", "missing_report"),
                                  "ticks": report.get("ticks_run"), "terminal": terminal,
                                  "report_path": str(report_path),
                                  "report_sha256": sha(report_path) if report_path.is_file() else None,
                                  "replay_exact": (report.get("replay_check") or {}).get("exact_match"),
                                  "llm_client_stats": report.get("llm_client_stats"),
                                  "planner_diagnostics": report.get("planner_diagnostics")}
                    pair[f"{kind}_valid"] = (
                        code == 0 and report.get("aborted", "missing_report") is None and
                        (terminal or not args.require_terminal) and config.get("planner") == "llm" and
                        config.get("scenario") == scenario and config.get("seed") == seed and
                        config.get("goal_granularity") == tier and config.get("llm") == settings and
                        (kind != "replay" or (report.get("replay_check") or {}).get("exact_match") is True))
                entry = {"scenario": scenario, "alias": alias, "seed": seed, "tier": tier, **pair}
                entries.append(entry)
                (output / "progress.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf-8")
                print(json.dumps({"scenario": alias, "seed": seed, "tier": tier,
                                  "original_valid": pair.get("original_valid"),
                                  "replay_exact": pair.get("replay", {}).get("replay_exact"),
                                  "llm_calls": (pair.get("original", {}).get("llm_client_stats") or {}).get("total_calls")}),
                      flush=True)
    unchanged = sha(script) == trace_hash and sha(Path(__file__)) == campaign_hash
    valid = unchanged and all(e.get("original_valid") and e.get("replay_valid") for e in entries)
    summary = {"schema": "role-c-hifi-llm-goai-tier-campaign@1", "source": str(source),
               "scenarios": args.scenario, "seeds": args.seed,
               "tiers": ["weak", "medium", "strong"], "ticks": args.ticks,
               "interval": args.interval, "step_timeout": args.step_timeout,
               "episode_timeout": args.episode_timeout,
               "world_checkpoint_interval": args.world_checkpoint_interval,
               "terminal_required": args.require_terminal, "llm": settings,
               "trace_script_sha256": trace_hash, "campaign_sha256": campaign_hash,
               "scripts_unchanged": unchanged, "run_and_replay_valid": bool(valid),
               "formal_B_if_validated": False, "formal_D3_passed": False,
               "formal_attribution_validated": False, "entries": entries}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

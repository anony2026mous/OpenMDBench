"""Whole-episode V2 goal-tier originals and own-trace replays, sequentially."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from hifi_replay_campaign import SCENARIOS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, log, timeout):
    with log.open("x", encoding="utf-8") as stream:
        try:
            return subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
        except subprocess.TimeoutExpired:
            return "timeout"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario", action="append", choices=SCENARIOS, required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--ticks", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--episode-timeout", type=int, default=14400)
    parser.add_argument("--step-timeout", type=float, default=300)
    parser.add_argument("--world-checkpoint-interval", type=int, default=50)
    parser.add_argument("--require-terminal", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("New output outside source required")
    if len(set(args.scenario)) != len(args.scenario) or len(set(args.seed)) != len(args.seed):
        raise ValueError("Repeated scenario/seed")
    script = Path(__file__).with_name("hifi_tier_trace.py")
    wrapper_hash, campaign_hash = digest(script), digest(Path(__file__))
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
                           "--tier", tier]
                    if kind == "replay":
                        cmd += ["--replay-from", str(stem / "original" / "measurement_episode.json")]
                    code = run(cmd, stem / f"{kind}.console.log", args.episode_timeout)
                    report_path = target / "measurement_episode.json"
                    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
                    meta = report.get("goal_tier", {})
                    terminal = report.get("terminal_result") is not None
                    pair[kind] = {"returncode": code, "aborted": report.get("aborted", "missing_report"),
                                  "ticks": report.get("ticks_run"), "terminal": terminal,
                                  "report_path": str(report_path),
                                  "report_sha256": digest(report_path) if report_path.exists() else None,
                                  "replay_exact": (report.get("replay_check") or {}).get("exact_match")}
                    pair[f"{kind}_valid"] = (code == 0 and report.get("aborted", "missing_report") is None and
                                              (terminal or not args.require_terminal) and
                                              meta.get("tier") == tier and meta.get("wrapper_sha256") == wrapper_hash and
                                              (kind != "replay" or
                                               (report.get("replay_check") or {}).get("exact_match") is True))
                entry = {"scenario": scenario, "alias": alias, "seed": seed, "tier": tier, **pair}
                entries.append(entry)
                (output / "progress.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf-8")
                print(json.dumps({"scenario": alias, "seed": seed, "tier": tier,
                                  "original_valid": pair.get("original_valid"),
                                  "replay_exact": pair.get("replay", {}).get("replay_exact")}), flush=True)
    unchanged = digest(script) == wrapper_hash and digest(Path(__file__)) == campaign_hash
    valid = unchanged and all(e.get("original_valid") and e.get("replay_valid") for e in entries)
    summary = {"schema": "role-c-hifi-goal-tier-campaign@1", "source": str(source),
               "scenarios": args.scenario, "seeds": args.seed, "tiers": ["weak", "medium", "strong"],
               "ticks": args.ticks, "interval": args.interval,
               "step_timeout": args.step_timeout, "episode_timeout": args.episode_timeout,
               "world_checkpoint_interval": args.world_checkpoint_interval,
               "terminal_required": args.require_terminal,
               "tier_wrapper_sha256": wrapper_hash, "campaign_sha256": campaign_hash,
               "scripts_unchanged": unchanged, "run_and_replay_valid": bool(valid),
               "formal_D3_passed": False, "formal_B_if_validated": False, "entries": entries}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Sequential terminal HIFI fault-dose runs with immutable per-arm replay.

This campaign validates injection and reproducibility, not oracle quality or
paper-level causal attribution. Every fault has a same-wrapper dose-zero arm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from hifi_fault_trace import FAULTS
from hifi_replay_campaign import SCENARIOS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, log, timeout):
    with log.open("x", encoding="utf-8") as stream:
        try:
            return subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=timeout,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
        except subprocess.TimeoutExpired:
            return "timeout"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario", action="append", choices=SCENARIOS, required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--case", action="append", choices=FAULTS)
    parser.add_argument("--dose", action="append", type=float)
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
    cases, doses = args.case or list(FAULTS), args.dose or [0.25, 0.5, 1.0]
    if (len(args.scenario) != len(set(args.scenario)) or len(args.seed) != len(set(args.seed)) or
            len(cases) != len(set(cases)) or len(doses) != len(set(doses)) or
            any(not 0 < d <= 1 for d in doses)):
        raise ValueError("Unique scenarios/seeds/cases/nonzero doses in (0,1] required")
    script = Path(__file__).with_name("hifi_fault_trace.py")
    wrapper_hash, campaign_hash = digest(script), digest(Path(__file__))
    output.mkdir(parents=True)
    entries = []
    for scenario in args.scenario:
        alias = scenario[:5] if scenario.startswith("IE-") else "IE-08"
        for seed in args.seed:
            for case in cases:
                for dose in [0.0, *doses]:
                    stem = output / alias / f"seed-{seed}" / f"{case}-dose-{dose:g}"
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
                               "--world-checkpoint-interval", str(args.world_checkpoint_interval),
                               "--step-timeout", str(args.step_timeout),
                               "--fault-case", case, "--dose", str(dose)]
                        if kind == "replay":
                            cmd += ["--replay-from", str(stem / "original" / "measurement_episode.json")]
                        code = run(cmd, stem / f"{kind}.console.log", args.episode_timeout)
                        report_path = target / "measurement_episode.json"
                        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
                        spec = report.get("fault_injection", {})
                        terminal = report.get("terminal_result") is not None
                        pair[kind] = {"returncode": code,
                                      "aborted": report.get("aborted", "missing_report"),
                                      "ticks": report.get("ticks_run"),
                                      "terminal": terminal,
                                      "report_path": str(report_path),
                                      "report_sha256": digest(report_path) if report_path.exists() else None,
                                      "fault_events": spec.get("event_count"),
                                      "replay_exact": (report.get("replay_check") or {}).get("exact_match")}
                        pair[f"{kind}_valid"] = (code == 0 and report.get("aborted", "missing_report") is None
                                                  and (terminal or not args.require_terminal)
                                                  and spec.get("case") == case and spec.get("dose") == dose
                                                  and spec.get("wrapper_sha256") == wrapper_hash
                                                  and (kind != "replay" or
                                                       (report.get("replay_check") or {}).get("exact_match") is True))
                    entry = {"scenario": scenario, "alias": alias, "seed": seed,
                             "case": case, "dose": dose, **pair}
                    entries.append(entry)
                    (output / "progress.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
                                                           encoding="utf-8")
                    print(json.dumps({"scenario": alias, "seed": seed, "case": case, "dose": dose,
                                      "terminal": pair.get("original", {}).get("terminal"),
                                      "events": pair.get("original", {}).get("fault_events"),
                                      "replay_exact": pair.get("replay", {}).get("replay_exact")}), flush=True)
    unchanged = digest(script) == wrapper_hash and digest(Path(__file__)) == campaign_hash
    valid = unchanged and all(e.get("original_valid") and e.get("replay_valid") for e in entries)
    summary = {"schema": "role-c-hifi-fault-campaign@1", "source": str(source),
               "scenarios": args.scenario, "seeds": args.seed, "cases": cases,
               "doses": [0.0, *doses], "ticks": args.ticks, "interval": args.interval,
               "world_checkpoint_interval": args.world_checkpoint_interval,
               "step_timeout": args.step_timeout, "episode_timeout": args.episode_timeout,
               "terminal_required": args.require_terminal,
               "fault_wrapper_sha256": wrapper_hash, "campaign_sha256": campaign_hash,
               "scripts_unchanged": unchanged, "run_and_replay_valid": bool(valid),
               "formal_attribution_validated": False, "formal_B_if_validated": False,
               "entries": entries}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

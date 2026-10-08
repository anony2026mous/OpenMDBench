"""Sequential selected-scenario trace/replay gate using fresh Windows processes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

SCENARIOS = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
             "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
             "IE-07-CROSS-DOMAIN", "MD-AD-006-ISLAND-STRIKE",
             "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ticks", type=int, default=30)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--episode-timeout", type=int, default=600)
    parser.add_argument("--require-terminal", action="store_true")
    parser.add_argument("--scenario", action="append", choices=SCENARIOS,
                        help="Select a scenario; repeat for several (default: all eight)")
    parser.add_argument("--world-checkpoint-interval", type=int, default=1)
    parser.add_argument("--step-timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.episode_timeout < 1 or args.ticks < 1 or args.world_checkpoint_interval < 1 or args.step_timeout <= 0:
        raise ValueError("Positive episode timeout, tick budget, checkpoint interval and step timeout required")
    selected = args.scenario or SCENARIOS
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate scenario selection")
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("New output outside source required")
    output.mkdir(parents=True)
    script = Path(__file__).with_name("hifi_trace.py")
    script_hash = hashlib.sha256(script.read_bytes()).hexdigest()
    entries = []
    started = time.monotonic()
    for scenario in selected:
        index = SCENARIOS.index(scenario) + 1
        for kind in ("original", "replay"):
            target = output / f"IE-{index:02d}" / kind
            cmd = [sys.executable, "-B", "-X", "utf8", str(script), "--source", str(source),
                   "--output", str(target), "--scenario", scenario, "--seed", str(args.seed), "--ticks", str(args.ticks),
                   "--world-checkpoint-interval", str(args.world_checkpoint_interval),
                   "--step-timeout", str(args.step_timeout)]
            if kind == "replay":
                original = output / f"IE-{index:02d}" / "original/measurement_episode.json"
                if not original.exists() or json.loads(original.read_text(encoding="utf-8"))["aborted"]:
                    entries.append({"scenario": scenario, "kind": kind, "skipped": "original_failed"})
                    continue
                cmd += ["--replay-from", str(original)]
            with (output / f"IE-{index:02d}-{kind}.console.log").open("x", encoding="utf-8") as log:
                try:
                    completed = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=args.episode_timeout,
                                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    code = completed.returncode
                except subprocess.TimeoutExpired:
                    code = "timeout"
            report_path = target / "measurement_episode.json"
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            entry = {"scenario": scenario, "alias": f"IE-{index:02d}", "kind": kind,
                     "returncode": code, "aborted": report.get("aborted", "missing_report"),
                     "ticks": report.get("ticks_run"), "replay_check": report.get("replay_check"),
                     "terminal_reported": report.get("terminal_result") is not None,
                     "report_path": str(report_path),
                     "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest() if report_path.exists() else None}
            entries.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            (output / "progress.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unchanged = script_hash == hashlib.sha256(script.read_bytes()).hexdigest()
    passed = unchanged and len(entries) == 2 * len(selected) and all(
        e.get("returncode") == 0 and e.get("aborted") is None and
        (not args.require_terminal or e.get("terminal_reported", False)) and
        (e["kind"] != "replay" or e["replay_check"]["exact_match"]) for e in entries)
    result = {"schema": "hifi-selected-scenario-replay-gate@2", "seed": args.seed,
              "selected_scenarios": selected, "world_checkpoint_interval": args.world_checkpoint_interval,
              "runner_step_timeout_seconds": args.step_timeout,
              "tick_budget_per_episode": args.ticks, "elapsed_seconds": time.monotonic() - started,
              "episode_timeout_seconds": args.episode_timeout, "terminal_required": args.require_terminal,
              "script_sha256": script_hash, "script_unchanged": unchanged,
              "limited_replay_gate_passed": passed, "formal_measurement_complete": False,
              "formal_attribution_complete": False, "entries": entries}
    (output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

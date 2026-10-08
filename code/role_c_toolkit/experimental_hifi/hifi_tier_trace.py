"""Whole-episode weak/medium/strong V2 goal-granularity trace wrapper.

Uses the engine's GoalCommand.to_granularity path through AgentV2. No engine
source is edited. Own-trace replay must use identical tier and wrapper hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import hifi_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--tier", choices=("weak", "medium", "strong"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-from", type=Path)
    args, passthrough = parser.parse_known_args()
    wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.replay_from:
        baseline = json.loads(args.replay_from.read_text(encoding="utf-8"))
        if (baseline.get("goal_tier", {}).get("tier") != args.tier or
                baseline.get("goal_tier", {}).get("wrapper_sha256") != wrapper_hash):
            raise ValueError("Replay requires same goal tier and wrapper version")
    original_context, original_argv = hifi_trace.TraceContext, sys.argv

    class TierContext(original_context):
        def attach_agent(self, agent):
            agent.goal_granularity = args.tier
            return super().attach_agent(agent)

    hifi_trace.TraceContext = TierContext
    try:
        sys.argv = [str(Path(hifi_trace.__file__)), "--output", str(args.output), *passthrough]
        if args.replay_from:
            sys.argv += ["--replay-from", str(args.replay_from)]
        code = hifi_trace.main()
    finally:
        hifi_trace.TraceContext, sys.argv = original_context, original_argv
    report_path = args.output.resolve() / "measurement_episode.json"
    if not report_path.exists():
        return code or 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["goal_tier"] = {"tier": args.tier, "wrapper_sha256": wrapper_hash,
                           "source_path": "AgentV2.goal_granularity -> GoalCommand.to_granularity",
                           "formal_D3_passed": False}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"tier": args.tier, "aborted": report["aborted"],
                      "ticks": report["ticks_run"],
                      "terminal": report["terminal_result"] is not None,
                      "replay_exact": (report.get("replay_check") or {}).get("exact_match")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

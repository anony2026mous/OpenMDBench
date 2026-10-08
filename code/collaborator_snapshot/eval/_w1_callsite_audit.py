"""Is the llm-rl branch making MORE planner calls than its cadence requires?

Question 4 of the audit plan asks whether the branch re-plans unnecessarily or sends
duplicate prompts.  The call counts are already recorded per episode in the worker
logs and in every report, so the question can be answered from evidence before any
code is touched:

    expected calls = floor(ticks / plan_interval) + (1 if the first plan is at tick 0)

Anything materially above that is waste; anything at or below it means the cost is
inherent (one call every `plan_interval` ticks times the per-call latency) and the
only honest speedups are fewer ticks, a coarser cadence, or a faster call.

Usage:
    python _w1_callsite_audit.py [--interval 10]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")
RL = RUNS / "rl"


def report_rows() -> list[dict]:
    rows = []
    for path in RUNS.glob("*.json"):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(report, dict):
            continue          # some artifacts in this directory are lists
        defender = report.get("defender")
        if not isinstance(defender, dict):
            continue
        planner = defender.get("planner") or {}
        executor = defender.get("executor") or {}
        calls = planner.get("plan_calls")
        if not calls:
            continue           # rule arm has no planner calls
        # The pure-RL arm also reports its decision count as ``plan_calls``, but its
        # cadence is the decision interval (5 ticks), not the planning interval (10).
        # Mixing the two makes a correct arm look like it plans twice as often as it
        # should -- the arm must come from the planner kind, not from file names.
        kind = str(planner.get("planner") or "?")
        # The RL *executor* is what separates llm-rl from llm: the frozen llm arm also
        # exposes `defender.executor` (the rule executor's own stats), so testing for
        # the block's mere presence mislabels every `ie_llm_*` report as llm-rl.
        learned = bool(executor.get("theta") or executor.get("rl_decisions"))
        if kind == "rl":
            arm, interval = "rl", 5
        elif learned:
            arm, interval = "llm-rl", 10
        else:
            arm, interval = "llm", 10
        rows.append({
            "name": path.name, "arm": arm, "interval": interval,
            "ticks": int(report.get("ticks_run") or 0),
            "calls": int(calls),
            "parse_failures": planner.get("parse_failures"),
            "stale_reuse": planner.get("stale_plan_reuse"),
            "fallback": planner.get("fallback_count"),
            "elapsed": report.get("elapsed_seconds"),
        })
    return rows


def worker_rows() -> list[dict]:
    rows = []
    for path in RL.glob("worker_*.log"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("event") != "episode_end":
                continue
            client = event.get("llm_client") or {}
            rows.append({
                "name": path.name, "scenario": event.get("scenario"),
                "seed": event.get("seed"),
                "ticks": int(event.get("steps") or 0) * 5,
                "calls": client.get("total_calls"),
                "avg_ms": None,
                "avg_latency": client.get("avg_latency"),
                "tokens_per_call": client.get("avg_tokens_per_call"),
                "seconds": event.get("seconds"),
                "outcome": event.get("outcome"),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()

    print("== A. 评测报告里的 plan_calls vs 节奏应有的次数 ==")
    header = (f"{'arm':<8}{'ticks':>7}{'calls':>7}{'expected':>9}{'ratio':>7}"
              f"{'parseFail':>10}{'stale':>7}{'fallback':>9}  file")
    print(header)
    print("-" * len(header))
    worst = []
    for row in sorted(report_rows(), key=lambda r: (r["arm"], r["name"])):
        expected = row["ticks"] // row["interval"] + 1
        ratio = row["calls"] / expected if expected else 0.0
        worst.append(ratio)
        print(f"{row['arm']:<8}{row['ticks']:>7}{row['calls']:>7}{expected:>9}"
              f"{ratio:>7.2f}{str(row['parse_failures']):>10}{str(row['stale_reuse']):>7}"
              f"{str(row['fallback']):>9}  {row['name'][:56]}")
    if worst:
        print(f"\n  ratio: mean={sum(worst)/len(worst):.2f} max={max(worst):.2f}"
              f"  (1.00 = exactly the cadence, >1.05 would be redundant planning)")

    print("\n== B. 训练 worker 日志：每次调用延迟与 token 量（客户端自报）==")
    header2 = (f"{'scenario':<22}{'seed':>6}{'ticks':>7}{'calls':>7}"
               f"{'avg_lat':>9}{'tok/call':>10}{'seconds':>9}  outcome")
    print(header2)
    print("-" * len(header2))
    rows = worker_rows()
    for row in sorted(rows, key=lambda r: (str(r["scenario"]), str(r["seed"]))):
        print(f"{str(row['scenario'])[:21]:<22}{str(row['seed']):>6}{row['ticks']:>7}"
              f"{str(row['calls']):>7}{str(row['avg_latency']):>9}"
              f"{str(row['tokens_per_call']):>10}{str(row['seconds']):>9}"
              f"  {row['outcome']}")
    latencies = [float(r["avg_latency"]) for r in rows if r.get("avg_latency")]
    toks = [float(r["tokens_per_call"]) for r in rows if r.get("tokens_per_call")]
    if latencies:
        print(f"\n  单次调用延迟: mean={sum(latencies)/len(latencies):.2f}s "
              f"min={min(latencies):.2f} max={max(latencies):.2f} (n={len(latencies)})")
    if toks:
        print(f"  每次调用 token: mean={sum(toks)/len(toks):.0f} "
              f"min={min(toks):.0f} max={max(toks):.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

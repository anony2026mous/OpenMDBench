"""Diagnose the fair-口径 run in flight: is the LLM failing to engage?

Counts goal types the planner accepted over the episode, and compares fire volume
against the declared-口径 runs of the same scenario.
"""
from __future__ import annotations

import collections
import glob
import json
import os

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
LOGS = os.path.join(RUNS, "logs")

print("=== goal types accepted over the in-flight fair run ===")
for lg in sorted(glob.glob(os.path.join(LOGS, "*ie-11*_fair*.jsonl")),
                 key=os.path.getmtime, reverse=True)[:3]:
    counts = collections.Counter()
    ticks = []
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "plan":
            ticks.append(e.get("tick"))
            for cmd in (e.get("accepted") or []):
                # task ids look like "intercept_uav92_001" / "hold_uav01_001"
                counts[str(cmd).split("_")[0]] += 1
    print(f"\n  {os.path.basename(lg)}")
    print(f"    plan calls: {len(ticks)}  (ticks {ticks[:6]}...{ticks[-3:] if ticks else ''})")
    for k, v in counts.most_common():
        print(f"      {k:<12} {v}")

print()
print("=== IE-11 fire volume: declared vs fair ===")
for tag, label in (("p2c1", "declared (old)"), ("fair", "withheld (new)")):
    got = []
    for p in glob.glob(os.path.join(RUNS, f"*ie-11*_{tag}*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        got.append((os.path.basename(p), d.get("total_fires_defender"),
                    d.get("ticks_run"),
                    (d.get("strategy_scorecard") or {}).get("defender_score")))
    if got:
        print(f"\n  {label}:")
        for n, f, t, s in sorted(got):
            print(f"    {n:<50} fires={f}  ticks={t}  score={s}")

print()
print("=== what the in-flight run has done so far (fire events) ===")
for lg in sorted(glob.glob(os.path.join(LOGS, "*ie-11*_fair.jsonl")), key=os.path.getmtime)[-1:]:
    fires = 0
    first = last = None
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "fire":
            fires += 1
            if first is None:
                first = e.get("tick")
            last = e.get("tick")
    print(f"  {os.path.basename(lg)}: {fires} fire events, first={first}, last={last}")

"""Verify the LLM planning cadence is actually every 10 ticks.

Three checks:
  1. the default of --plan-interval and what the sweep passes
  2. from run logs: the actual tick sequence of `plan` events
  3. whether plan calls land exactly on multiples of the interval
"""
from __future__ import annotations

import collections
import glob
import json
import os

EVAL = r"C:\Code\source-code\openmd\code\eval"
RUNS = os.path.join(EVAL, "_w1_runs")

print("=== 1) configured cadence ===")
import re
src = open(os.path.join(EVAL, "run_episode.py"), encoding="utf-8").read()
m = re.search(r'"--plan-interval".{0,240}', src, re.S)
if m:
    print("  run_episode.py:", " ".join(m.group(0).split())[:200])
sw = open(os.path.join(EVAL, "_w1_ie_sweep.py"), encoding="utf-8").read()
for line in sw.splitlines():
    if "plan-interval" in line:
        print("  _w1_ie_sweep.py:", line.strip())

print()
print("=== 2) actual plan-event ticks from the freshest logs ===")
logs = sorted(glob.glob(os.path.join(RUNS, "logs", "*_top*.jsonl")),
              key=os.path.getmtime)[-4:]
for lg in logs:
    ticks = []
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "plan":
            ticks.append(e.get("tick"))
    if not ticks:
        continue
    diffs = [b - a for a, b in zip(ticks, ticks[1:])]
    on_grid = sum(1 for t in ticks if isinstance(t, int) and t % 10 == 0)
    print(f"\n  {os.path.basename(lg)}")
    print(f"    plan calls   : {len(ticks)}")
    print(f"    ticks        : {ticks[:14]}{'...' if len(ticks) > 14 else ''}")
    print(f"    gaps         : {sorted(collections.Counter(diffs).items())}")
    print(f"    on 10-grid   : {on_grid}/{len(ticks)}")

print()
print("=== 3) does engine ticks_run / plan count match the cadence? ===")
for p in sorted(glob.glob(os.path.join(RUNS, "*_top.json")))[:6]:
    d = json.load(open(p, encoding="utf-8"))
    de = d.get("defender") or {}
    pl = de.get("planner") if isinstance(de, dict) else None
    calls = pl.get("plan_calls") if isinstance(pl, dict) else None
    tk = d.get("ticks_run")
    if isinstance(tk, int) and tk > 0:
        expect = tk // 10 + 1
        print(f"  {os.path.basename(p)[:52]:<54} ticks={tk:<5} plan_calls={calls}  "
              f"expected~{expect}")

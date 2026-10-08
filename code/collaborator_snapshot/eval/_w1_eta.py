"""How much longer?  Computed from what is actually left, wave by wave.

Key correction: within one sweep invocation the thread pool runs at most
`--jobs` scenarios AT A TIME, so a step with 14 scenarios runs in ceil(14/jobs)
waves.  Treating it as "14 episodes / jobs" understates the tail.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
JOBS = 6

# per-scenario tick estimate from all history
ticks: dict[str, list[int]] = defaultdict(list)
for p in glob.glob(os.path.join(RUNS, "*.json")):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    t = d.get("ticks_run")
    if isinstance(t, int) and t > 100:
        ticks[str(d.get("scenario", "")).upper()].append(t)

SPT = {"llm": 2.49, "pure-llm": 1.39, "llm-rl": 2.58}


def tk(sc: str) -> int:
    v = ticks.get(sc, [])
    return int(st.median(v)) if v else 1199


def done(tag: str, planner: str, sc: str, seed: int) -> bool:
    suffix = "" if seed == 7 else f"_s{seed}"
    stem = f"ie_{planner.replace('-','')}_{sc.lower()}_{tag}{suffix}.json"
    return os.path.exists(os.path.join(RUNS, stem))


g1 = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
      "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE"]
g2 = ["IE-04-COMBINED-ARMS", "IE-07-CROSS-DOMAIN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
g3 = ["IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN"]
all14 = g1 + g3 + ["IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]

steps = [
    ("llm-rule", "llm", "top", 11, ["IE-04-COMBINED-ARMS", "IE-07-CROSS-DOMAIN",
                                    "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE",
                                    "IE-14-SATURATION-THREE-WAVE"]),
    ("llm-rule", "llm", "top", 13, ["IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS",
                                    "IE-06-DECOY-MIXED", "IE-07-CROSS-DOMAIN",
                                    "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
                                    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN",
                                    "IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE",
                                    "IE-14-SATURATION-THREE-WAVE"]),
    ("pure-llm", "pure-llm", "envfix", 7, all14),
    ("pure-llm", "pure-llm", "envfix", 11, all14),
    ("pure-llm", "pure-llm", "envfix", 13, all14),
]

print("=== remaining work, step by step ===")
print(f"  {'step':<26}{'todo':>6}{'waves':>7}{'serial h':>10}{'wall h':>8}")
tot_wall = 0.0
for label, planner, tag, seed, scs in steps:
    todo = [s for s in scs if not done(tag, planner, s, seed)]
    if not todo:
        print(f"  {label + ' seed' + str(seed):<26}{0:>6}{0:>7}{0.0:>10.2f}{0.0:>8.2f}")
        continue
    spt = SPT[planner]
    serial = sum(tk(s) * spt for s in todo)
    waves = math.ceil(len(todo) / JOBS)
    # each wave costs the MAX episode in it, not the mean -> approximate by mean*waves
    mean_wave = serial / len(todo)
    wall = mean_wave * waves
    tot_wall += wall
    print(f"  {label + ' seed' + str(seed):<26}{len(todo):>6}{waves:>7}"
          f"{serial/3600:>10.2f}{wall/3600:>8.2f}")

print(f"\n  REMAINING WALL TIME (batch): {tot_wall/3600:.1f} h  "
      f"(finishes ~{(__import__('datetime').datetime.now() + __import__('datetime').timedelta(seconds=tot_wall)).strftime('%H:%M')})")

print()
print("=== the separate llm-rl top-up (not in the batch) ===")
lr = [s for s in all14 if s != "IE-03-SURFACE-RAID"]
serial_lr = sum(tk(s) * SPT["llm-rl"] for s in lr) * 2   # seeds 11 and 13
waves_lr = math.ceil(len(lr) / JOBS) * 2
wall_lr = (serial_lr / (len(lr) * 2)) * waves_lr
print(f"  episodes: {len(lr)*2}   serial: {serial_lr/3600:.1f} h   "
      f"wall at jobs={JOBS}: {wall_lr/3600:.1f} h")

print()
print(f"=== everything (batch + llm-rl): {(tot_wall + wall_lr)/3600:.1f} h more ===")

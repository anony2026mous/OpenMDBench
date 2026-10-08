"""Correct re-estimate: enumerate the 9 invocations explicitly (no comprehension bug)."""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

spt: dict[str, list[float]] = defaultdict(list)
hist_ticks: dict[str, list[int]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    pl = str(d.get("planner", "")).lower()
    e, t = d.get("elapsed_seconds"), d.get("ticks_run")
    if isinstance(e, (int, float)) and isinstance(t, int):
        if t > 100:
            spt[pl].append(e / t)
        hist_ticks[str(d.get("scenario", "")).upper()].append(t)

# fresh step-1 measurements override history for the llm planner
FRESH = {}
for fn in os.listdir(RUNS):
    if not fn.endswith("_top.json"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if isinstance(d, dict) and isinstance(d.get("ticks_run"), int):
        FRESH[str(d.get("scenario", "")).upper()] = int(d["ticks_run"])

g1 = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
      "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE"]
g2 = ["IE-04-COMBINED-ARMS", "IE-07-CROSS-DOMAIN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
g3 = ["IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN"]
all14 = g1 + g3 + ["IE-12-FOG-ONSET", "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]

# remaining invocations (step 1 = seed 7 on g1 is DONE)
invocations = [
    ("llm", 17, g1), ("llm", 19, g1),          # 16 episodes
    ("llm", 11, g2), ("llm", 13, g2),          # 10
    ("llm", 13, g3),                            # 3
    ("pure-llm", 7, all14), ("pure-llm", 11, all14), ("pure-llm", 13, all14),  # 42
]
DONE = FRESH  # scenarios already completed in step 1

def est_ticks(sc):
    if sc in DONE:
        return DONE[sc]
    v = hist_ticks.get(sc, [])
    return int(st.median(v)) if v else 1199

print("=== per-scenario measured ticks (fresh step-1) vs historical median ===")
for sc in all14:
    fresh = DONE.get(sc)
    hist = hist_ticks.get(sc, [])
    hm = int(st.median(hist)) if hist else 0
    print(f"  {sc:<28} fresh={fresh if fresh else '-':>6}   hist_median={hm:>6}  n_hist={len(hist)}")

print()
print(f"  s/tick  llm = {st.median(spt['llm']):.2f}   pure-llm = {st.median(spt['pure-llm']):.2f}")
print()
print("=== remaining invocations ===")
print(f"  {'planner':<10}{'seed':>5}{'scenarios':>10}{'episodes':>9}{'serial h':>10}")
total = 0.0
tot_ep = 0
for pl, seed, scs in invocations:
    key = "llm" if pl == "llm" else "pure-llm"
    stk = st.median(spt[key])
    secs = sum(est_ticks(s) * stk for s in scs)
    total += secs
    tot_ep += len(scs)
    print(f"  {pl:<10}{seed:>5}{len(scs):>10}{len(scs):>9}{secs/3600:>10.2f}")
print(f"  {'TOTAL':<10}{'':>5}{'':>10}{tot_ep:>9}{total/3600:>10.2f} h serial")
print()
for j in (4, 6, 8):
    print(f"    --jobs {j}: {total/j/3600:.2f} h wall")

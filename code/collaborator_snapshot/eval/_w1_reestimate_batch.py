"""Re-estimate the remaining batch cost from the MEASURED work, not historical medians.

Step 1 gave us 8 fresh llm-rule episodes at seed 7 with the current code: median
2945 s / 1199 ticks. Historical medians were contaminated by seed-7 early
terminations, so they under-estimated badly. This uses per-scenario measured
ticks and a measured s/tick to project the remaining 47 episodes.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

# 1) measured s/tick per planner, from the freshest data available
per_planner: dict[str, list[float]] = defaultdict(list)
ticks_by_planner: dict[str, list[int]] = defaultdict(list)
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
    if isinstance(e, (int, float)) and isinstance(t, int) and t > 100:
        per_planner[pl].append(e / t)
        ticks_by_planner[pl].append(t)

print("=== measured s/tick (episodes with >100 ticks only) ===")
for pl in ("llm", "pure-llm", "llm-rl", "rule"):
    v = per_planner.get(pl, [])
    if v:
        print(f"  {pl:<10} n={len(v):>3}  median={st.median(v):.2f}  mean={st.mean(v):.2f}")

# 2) remaining episodes and their expected tick counts
#    step 1 already done. Remaining:
#      llm-rule: g1(seed17,19) g2(seed11,13) g3(seed13)
#      pure-llm: all14 x (7,11,13)
STEP1_DONE = {"IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
              "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
              "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE"}
g1 = sorted(STEP1_DONE)
g2 = ["IE-04-COMBINED-ARMS", "IE-07-CROSS-DOMAIN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
g3 = ["IE-09-STAGGERED-WAVES", "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN"]
all14 = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
         "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
         "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
         "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
         "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]

jobs = ([("llm-rule", s) for s in (g1 + g1 + g2 + g2 + g3)]
        + [("pure-llm", all14)] * 3)

# per-scenario tick estimate from any planner's history (scenario property)
est_ticks: dict[str, int] = {}
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper()
    t = d.get("ticks_run")
    if isinstance(t, int) and t > 100:
        est_ticks.setdefault(sc, []).append(t)  # type: ignore[arg-type]

print()
print("=== projected remaining work ===")
print(f"  {'planner':<10}{'episodes':>9}{'est. ticks/ep':>14}{'s/tick':>8}{'serial h':>10}")
total_serial = 0.0
n_ep = 0
for pl in ("llm-rule", "pure-llm"):
    planner_key = "llm" if pl == "llm-rule" else "pure-llm"
    stk = st.median(per_planner.get(planner_key, [2.4]))
    eps = []
    for p, scs in jobs:
        if p == pl:
            eps.extend(scs)
    tk = st.mean([st.median(est_ticks.get(s, [1199])) for s in eps]) if eps else 0
    secs = sum(st.median(est_ticks.get(s, [1199])) * stk for s in eps)
    total_serial += secs
    n_ep += len(eps)
    print(f"  {pl:<10}{len(eps):>9}{tk:>14.0f}{stk:>8.2f}{secs/3600:>10.2f}")

print(f"  {'TOTAL':<10}{n_ep:>9}{'':>14}{'':>8}{total_serial/3600:>10.2f} h serial")
for jobs_n in (4, 6, 8):
    print(f"    at --jobs {jobs_n}: {total_serial/jobs_n/3600:.2f} h wall")

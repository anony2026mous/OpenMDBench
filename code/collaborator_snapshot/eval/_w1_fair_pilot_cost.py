"""Cost of the fair-口径 pilot, per scenario (tick-driven, so scenario mix matters)."""
from __future__ import annotations

import glob
import json
import math
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = ["IE-01-SINGLE-TARGET", "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS",
        "IE-06-DECOY-MIXED", "IE-11-DECOY-SCREEN", "IE-13-DEEP-STRIKE"]
SPT = {"llm": 2.54, "pure-llm": 1.77, "llm-rl": 2.58}
JOBS = 6

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


def tk(sc):
    v = ticks.get(sc, [])
    return int(st.median(v)) if v else 1199


print("=== per-scenario tick profile (drives cost) ===")
for sc in SCEN:
    print(f"  {sc:<28} median ticks = {tk(sc):>5}")

print()
print("=== cost per (arm, scenario), 3 seeds ===")
print(f"  {'arm':<10}{'scenario':<28}{'eps':>4}{'serial h':>10}")
total = 0.0
per_arm = defaultdict(float)
for arm, pl in (("llm-rule", "llm"), ("pure-llm", "pure-llm"), ("llm-rl", "llm-rl")):
    for sc in SCEN:
        s = tk(sc) * SPT[pl] * 3
        total += s
        per_arm[arm] += s
        print(f"  {arm:<10}{sc:<28}{3:>4}{s/3600:>10.2f}")
    print()

print("=== totals ===")
for arm, s in per_arm.items():
    print(f"  {arm:<10} {s/3600:>6.1f} h serial   at x{JOBS} = {s/JOBS/3600:>5.1f} h")
print(f"  {'TOTAL':<10} {total/3600:>6.1f} h serial   at x{JOBS} = {total/JOBS/3600:>5.1f} h")

print()
print("=== a cheaper first answer: IE-11 only (the decisive case) ===")
s11 = sum(tk("IE-11-DECOY-SCREEN") * v * 3 for v in SPT.values())
print(f"  IE-11 x 3 arms x 3 seeds = 9 episodes, {s11/3600:.2f} h serial, "
      f"{s11/JOBS/3600:.2f} h at x{JOBS}")
print("  (IE-11 is where the briefing leak AND the misclassification bug both hit;")
print("   if the hybrid loses its edge there too, the full pilot is moot.)")

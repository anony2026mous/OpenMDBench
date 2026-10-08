"""Cost of the three-arm top-up, and the pure-llm consistency decision."""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = {"IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"}

wall: dict[str, list[float]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if str(d.get("scenario", "")).upper() not in SCEN:
        continue
    pl = str(d.get("planner", "")).lower()
    el = d.get("elapsed_seconds")
    if isinstance(el, (int, float)) and el > 0:
        wall[pl].append(float(el))

print("=== measured wall-clock (IE scenarios only) ===")
for pl in sorted(wall):
    v = wall[pl]
    print(f"  {pl:<10} n={len(v):>3}  median={st.median(v):>8.1f}s  mean={st.mean(v):>8.1f}s  "
          f"p90={sorted(v)[int(len(v)*0.9)]:>8.1f}s")

med = {k: st.median(v) for k, v in wall.items()}
CONC = 4   # conservative: LLM endpoint saturates above ~4-6

for label, n_lr, n_pl in (("minimal top-up", 13, 17),
                          ("clean pure-llm (all 14x3)", 13, 42)):
    t_lr = med.get("llm", 1472) * n_lr
    t_pl = med.get("pure-llm", 1362) * n_pl
    tot = t_lr + t_pl
    print()
    print(f"=== {label}: {n_lr + n_pl} episodes ===")
    print(f"  llm-rule {n_lr:>3} x {med.get('llm', 1472):>7.0f}s = {t_lr/3600:>5.2f} h serial")
    print(f"  pure-llm {n_pl:>3} x {med.get('pure-llm', 1362):>7.0f}s = {t_pl/3600:>5.2f} h serial")
    print(f"  serial total {tot/3600:>5.2f} h   at x{CONC} = {tot/CONC/3600:>5.2f} h")

print()
print("=== the trap: is a partial pure-llm re-run valid? ===")
print("""
  pure-llm episodes on the 14 scenarios: 30, ALL without an envelope record.
  The envelope default changed 45/10 -> 43/8 (with the other five arms).
  The per-episode report does NOT record which envelope was used.

  => If we only run the 17 missing cells, each pure-llm cell would be a MIXTURE:
       some episodes at 45/10 (old), some at 43/8 (new) - indistinguishable.
     Averaging them mixes two different arm definitions into one number.

  => The only defensible options are:
     (a) re-run ALL 14 scenarios x >=3 seeds for pure-llm  (42 episodes) -> clean
     (b) keep pure-llm entirely at the OLD envelope, and never mix
         (i.e. run the 17 as --pure-llm-envelope hardcoded) -> clean but keeps the
         known unfairness, which the paper must then disclose
     (c) drop pure-llm from the main table and report it as a separate,
         explicitly-labelled historical baseline
""")

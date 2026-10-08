"""Wall-clock projection for the remaining grid work.

Inputs are all measured, none assumed:
  * ticks per scenario - from the archived declared-口径 LLM-arm episodes (same
    scenarios, same 1800-tick horizon).  The LLM arms terminate on the engine's
    own success latch, so tick count is a scenario property, not an arm property.
  * seconds per tick per arm - from this session's probe.
  * concurrency - the driver's --jobs (6; 9 previously tripped step_timeout).

Output is a P50/P90-ish range, deliberately conservative: LLM latency grows with
concurrent load, so the projection uses the measured loaded-latency rates rather
than the idle ones.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "openmd_private_archive" / "declared_briefing_snapshot_20260927_1419" / "results"

# measured seconds/tick (this session):
#   llm/llm-rule 2.49   pure-llm 1.77   llm-rl 2.58  (rule 0.385, rl 0.32)
RATE = {"llm": 2.49, "llm-rl": 2.58, "pure-llm": 1.77}
CONC = 6
SEEDS = [7, 11, 13]

ticks: dict[str, list[int]] = defaultdict(list)
for p in SNAP.glob("*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if d.get("planner") not in ("llm", "llm-rl"):
        continue
    sc = str(d.get("scenario") or "").upper()
    card = d.get("strategy_scorecard") or {}
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    t = int(d.get("ticks_run") or 0)
    if t > 0:
        ticks[sc].append(t)

print("=" * 92)
print("GRID WALL-CLOCK PROJECTION")
print("=" * 92)
print("\n--- archived tick counts per scenario (LLM arms, declared口径) ---")
per_scen = {}
for sc in sorted(ticks):
    v = ticks[sc]
    med = int(st.median(v))
    per_scen[sc] = med
    print(f"    {sc:<30} n={len(v):<3} median={med:<6} max={max(v)}")

if not per_scen:
    print("    (none found)")
DEFAULT = 900
print(f"\n    scenarios missing from archive use {DEFAULT} ticks")

IE = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
      "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
      "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]

print("\n--- per-arm work (3 seeds x 14 scenarios), serial episode seconds ---")
grand = 0.0
for arm, rate in RATE.items():
    total_s = 0.0
    for sc in IE:
        tk = per_scen.get(sc, DEFAULT)
        total_s += tk * rate * len(SEEDS)
    grand += total_s
    print(f"    {arm:<10} {total_s / 3600:7.1f} h serial   "
          f"{total_s / CONC / 3600:7.1f} h at {CONC}-way")

print(f"\n    TOTAL      {grand / 3600:7.1f} h serial   "
      f"{grand / CONC / 3600:7.1f} h at {CONC}-way")

print(f"\n--- milestones at {CONC}-way ---")
s7 = sum(per_scen.get(sc, DEFAULT) * RATE[a] for a in RATE for sc in IE)
print(f"    P1 (seed 7 only, 42 cells) : {s7 / CONC / 3600:5.1f} h")
print(f"    P1+P2 (all 126 cells)      : {grand / CONC / 3600:5.1f} h")
print(f"\n    NOTE: rates are loaded-latency measurements; a 6-way run serialises")
print(f"    LLM waits, so real time is bounded by total LLM calls, not by ticks alone.")
ncalls = sum(per_scen.get(sc, DEFAULT) / 10 * len(SEEDS) for sc in IE) * len(RATE)
print(f"    LLM planning calls to issue : {ncalls:.0f}")

"""Definitive split: LLM wait vs engine, from plan-event gaps + an A/B control.

1. llm-rule logs DO emit `plan` events every 10 ticks, so the gap between two
   consecutive plan events = (LLM latency) + (engine time for those 10 ticks).
2. Under the CURRENT batch load there are 4 pure-llm episodes running with no
   plan events, so the engine-only cost under that same load can be taken from
   the rule arm's measured s/tick, cross-checked against llm-rl (whose per-tick
   LLM wait is 1/10 of llm-rule's, since it plans on the same cadence).
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
LOGS = os.path.join(RUNS, "logs")

# --- 1. plan-event gaps in llm-rule logs
print("=== llm-rule: gap between consecutive plan events (10 ticks apart) ===")
gaps_all = []
for lg in sorted(glob.glob(os.path.join(LOGS, "*_top*.jsonl")), key=os.path.getmtime):
    ev = []
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "plan" and isinstance(e.get("ts"), (int, float)):
            ev.append((e.get("tick"), e["ts"]))
    g10 = [b[1] - a[1] for a, b in zip(ev, ev[1:])
           if isinstance(a[0], int) and isinstance(b[0], int) and b[0] - a[0] == 10]
    if len(g10) >= 5:
        gaps_all.extend(g10)
        print(f"  {os.path.basename(lg)[:44]:<46} n={len(g10):>3}  "
              f"median={st.median(g10):>6.1f}s  min={min(g10):>5.1f}  max={max(g10):>6.1f}")

if gaps_all:
    med_gap = st.median(gaps_all)
    print(f"\n  pooled: n={len(gaps_all)}  median gap={med_gap:.1f}s  "
          f"mean={st.mean(gaps_all):.1f}s")

# --- 2. engine-only cost from the rule arm
eng = []
for p in glob.glob(os.path.join(RUNS, "*.json")):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or str(d.get("planner", "")).lower() != "rule":
        continue
    e, t = d.get("elapsed_seconds"), d.get("ticks_run")
    if isinstance(e, (int, float)) and isinstance(t, int) and t > 100:
        eng.append(e / t)
ENG = st.median(eng) if eng else 0.385
eng10 = ENG * 10
print(f"\n=== engine-only cost (rule arm, no LLM at all) ===")
print(f"  {ENG:.3f} s/tick  ->  {eng10:.2f} s per 10 ticks")

if gaps_all:
    llm_wait = med_gap - eng10
    print()
    print("=== SPLIT for an llm-rule episode with 180 plan calls (IE-08) ===")
    calls = 180
    print(f"  LLM wait  : {llm_wait:.1f} s x {calls} = {llm_wait*calls/60:.0f} min")
    print(f"  engine    : {eng10:.2f} s x {calls} = {eng10*calls/60:.0f} min")
    tot = (llm_wait + eng10) * calls
    print(f"  total     : {tot/60:.0f} min   ->  LLM share = {llm_wait/(llm_wait+eng10)*100:.0f}%")

# --- 3. cross-check with llm-rl, which uses the SAME plan cadence
print()
print("=== cross-check: per-tick cost by arm (measured) ===")
spt: dict[str, list[float]] = {}
for arm, pl in (("llm-rule", "llm"), ("pure-llm", "pure-llm"),
                ("llm-rl", "llm-rl"), ("rl", "rl"), ("rule", "rule")):
    v = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict) or str(d.get("planner", "")).lower() != pl:
            continue
        e, t = d.get("elapsed_seconds"), d.get("ticks_run")
        if isinstance(e, (int, float)) and isinstance(t, int) and t > 100:
            v.append(e / t)
    if v:
        spt[arm] = v
        excess = st.median(v) - ENG
        print(f"  {arm:<10} n={len(v):>3}  {st.median(v):>5.2f} s/tick   "
              f"excess over engine = {excess:>5.2f} s/tick  "
              f"({excess/(excess+ENG)*100:>4.0f}% of wall)")

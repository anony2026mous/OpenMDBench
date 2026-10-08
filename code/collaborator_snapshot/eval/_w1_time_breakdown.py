"""What is the wall-clock actually spent on?  LLM wait vs engine compute.

Method: in the run logs, each `plan` event is emitted right after the LLM client
returns. Consecutive plan events are 10 ticks apart, so the gap between two plan
events = (LLM latency for the 2nd call) + (engine time for 10 ticks).
Engine time is separately measurable from the rule arm (no LLM at all):
rule elapsed/ticks.
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
LOGS = os.path.join(RUNS, "logs")

# ---- engine-only cost: the rule arm never calls the LLM
engine_spt = []
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
        engine_spt.append(e / t)

print("=== engine-only cost per tick (rule arm, zero LLM calls) ===")
if engine_spt:
    print(f"  n={len(engine_spt)}  median={st.median(engine_spt):.3f} s/tick  "
          f"mean={st.mean(engine_spt):.3f}")
eng = st.median(engine_spt) if engine_spt else 0.4

# ---- LLM arms: gap between plan events
print()
print("=== LLM arms: interval between consecutive plan events ===")
print("    (10 ticks apart; gap = LLM latency + 10 ticks of engine time)")
rows = []
for lg in sorted(glob.glob(os.path.join(LOGS, "*.jsonl")), key=os.path.getmtime)[-8:]:
    plans = []
    for line in open(lg, encoding="utf-8", errors="ignore"):
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if e.get("t") == "plan":
            plans.append((e.get("tick"), e.get("ts")))
    if len(plans) < 5:
        continue
    gaps = [(t2 - t1, s2 - s1) for (t1, s1), (t2, s2) in zip(plans, plans[1:])
            if isinstance(s1, (int, float)) and isinstance(s2, (int, float))]
    g10 = [g for dt, g in gaps if dt == 10]
    if not g10:
        continue
    med = st.median(g10)
    llm = med - 10 * eng
    rows.append((os.path.basename(lg), len(g10), med, llm))
    print(f"  {os.path.basename(lg)[:46]:<48} n={len(g10):>3}  "
          f"gap={med:>6.1f}s  -> LLM≈{llm:>6.1f}s  engine(10t)≈{10*eng:.1f}s")

print()
if rows:
    llms = [r[3] for r in rows]
    med_llm = st.median(llms)
    print(f"=== conclusion ===")
    print(f"  engine per 10 ticks : {10*eng:.2f} s")
    print(f"  LLM per plan call   : {med_llm:.1f} s  (median across logs)")
    share = med_llm / (med_llm + 10 * eng) * 100
    print(f"  => LLM share of a plan cycle: {share:.1f}%")
    print()
    # direct cross-check against the reported per-episode numbers
    print("  cross-check: total LLM time per episode = plan_calls x LLM latency")
    for p in sorted(glob.glob(os.path.join(RUNS, "*_envfix*.json")))[:5]:
        d = json.load(open(p, encoding="utf-8"))
        de = d.get("defender") or {}
        calls = de.get("llm_calls")
        el = d.get("elapsed_seconds")
        tk = d.get("ticks_run")
        if isinstance(calls, int) and isinstance(el, (int, float)) and isinstance(tk, int):
            est_llm = calls * med_llm
            print(f"    {os.path.basename(p)[:46]:<48} ticks={tk:<5} calls={calls:<4} "
                  f"elapsed={el:>7.0f}s  est.LLM={est_llm:>7.0f}s "
                  f"({est_llm/el*100:>4.0f}%)  engine≈{tk*eng:>6.0f}s")

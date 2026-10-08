"""Where does the wall-clock go?  Read the LLM client's own accounting.

Reports record llm_calls and (for some arms) total LLM latency, so the split
between "waiting for the model" and "everything else" can be read directly
instead of inferred.
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

# engine-only baseline
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
print(f"engine-only cost (rule arm): {ENG:.3f} s/tick  ->  {ENG*10:.2f} s per 10 ticks")
print()

print("=== LLM arms: model wait vs the rest ===")
print(f"  {'file':<44}{'ticks':>6}{'calls':>7}{'llm_wait':>9}{'per_call':>9}"
      f"{'engine':>8}{'other':>8}{'llm%':>7}")
rows = []
for arm, pat in (("llm-rule", "ie_llm_*.json"),
                 ("pure-llm", "ie_purellm_*_envfix*.json"),
                 ("llm-rl", "ie_llmrl_*.json")):
    for p in sorted(glob.glob(os.path.join(RUNS, pat)), key=os.path.getmtime)[-3:]:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        el, tk = d.get("elapsed_seconds"), d.get("ticks_run")
        de = d.get("defender") or {}
        if not (isinstance(el, (int, float)) and isinstance(tk, int) and tk > 0):
            continue
        calls = de.get("llm_calls")
        lat = de.get("total_latency") or de.get("llm_total_latency")
        lc = de.get("llm_client") if isinstance(de.get("llm_client"), dict) else {}
        if lat is None and isinstance(lc, dict):
            lat = lc.get("total_latency")
        if calls is None and isinstance(lc, dict):
            calls = lc.get("total_calls")
        if not isinstance(lat, (int, float)) or not isinstance(calls, int) or calls == 0:
            continue
        eng_t = tk * ENG
        other = el - lat - eng_t
        rows.append((os.path.basename(p), tk, calls, lat, lat / calls, eng_t, other,
                     lat / el * 100))
        print(f"  {os.path.basename(p)[:42]:<44}{tk:>6}{calls:>7}{lat:>8.0f}s"
              f"{lat/calls:>8.1f}s{eng_t:>7.0f}s{other:>7.0f}s{lat/el*100:>6.0f}%")

print()
if rows:
    print("=== summary over the sampled episodes ===")
    print(f"  LLM wait      : {st.mean([r[6-1] for r in rows]):.0f} s/episode on average")
    print(f"  engine compute: {st.mean([r[5] for r in rows]):.0f} s/episode")
    print(f"  other         : {st.mean([r[6] for r in rows]):.0f} s/episode")
    print(f"  LLM share     : {st.mean([r[7] for r in rows]):.0f}% of wall-clock")
    print(f"  per-call mean : {st.mean([r[4] for r in rows]):.1f} s")

print()
print("=== per-arm LLM-call cadence (how often the model is asked) ===")
print("  llm-rule / llm-rl : 1 call per 10 ticks  (plan-interval 10)")
print("  pure-llm          : 1 call per 10 ticks  (plan-interval = its call interval)")
print("  rule / rl / rule-rl: 0 calls (no LLM in the loop)")

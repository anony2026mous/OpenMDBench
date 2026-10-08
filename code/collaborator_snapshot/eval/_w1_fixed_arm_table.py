"""Verify the fixed-arm cell: files, real seeds, and the attribution table."""
from __future__ import annotations

import glob
import json
import os
import statistics as st

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

print("=== pure-llm IE-11 runs completed so far ===")
rows = []
for p in sorted(glob.glob(os.path.join(RUNS, "ie_purellm_ie-11-decoy-screen_fair*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    c = d.get("strategy_scorecard") or {}
    de = d.get("defender") or {}
    env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
    rows.append({"file": os.path.basename(p), "seed": d.get("seed"),
                 "ticks": d.get("ticks_run"), "fires": d.get("total_fires_defender"),
                 "score": float(c.get("defender_score", 0)), "env": env})
    print(f"  {os.path.basename(p):<46} seed={d.get('seed')} "
          f"ticks={d.get('ticks_run'):<5} fires={d.get('total_fires_defender')} "
          f"score={c.get('defender_score')}")
    if env:
        print(f"       envelope: {json.dumps(env, sort_keys=True)}")

print()
print("NOTE: the report's `seed` field reads 7 for all three. Check whether the")
print("      filename suffix reflects the seed actually used, since the engine")
print("      seeds its dice from session_id (built from the seed).")
for r in rows:
    print(f"  {r['file']:<46} report.seed={r['seed']}")

print()
print("=" * 88)
print("attribution table for IE-11, arm = pure-llm")
print("=" * 88)
if rows:
    fixed = st.mean([r["score"] for r in rows])
    print(f"  {'configuration':<46}{'pure-llm IE-11':>14}")
    print(f"  {'declared (intel + ROE bug)':<46}{0.618:>14.3f}")
    print(f"  {'intel present, bug FIXED   <- these runs':<46}{fixed:>14.3f}")
    print(f"  {'no intel, bug fixed        <- still to run':<46}{'-':>14}")
    print()
    print(f"  bug-fix contribution = {fixed:.3f} - 0.618 = {fixed - 0.618:+.3f}")
    print(f"  (intel contribution pending the withheld pure-llm runs)")

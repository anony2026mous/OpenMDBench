"""Verify the serendipitous arm: pure-llm's completed 'fairp' runs.

Claim to check: those runs form a clean "intel present, ROE misclassification bug
FIXED" cell, because
  (a) pure_llm_agent injects graph.format_timeline_for_prompt() unconditionally
      -> the enemy timeline (intel) IS present, and
  (b) the misclassification logic lives in run_episode._build_roe_notes, which we
      already rewrote to classify by weapon binding instead of text matching
      -> the "real air package = NON-THREAT" instruction cannot be produced.
If both hold, this cell isolates the BUG-FIX contribution.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
PUB = "IE-11-DECOY-SCREEN"

print("=" * 88)
print("(b) does the rewritten _build_roe_notes still emit a NON-THREAT order?")
print("=" * 88)
payload = run_episode.load_attack_profile_data(PUB)
for mode in ("withheld", "declared"):
    txt = run_episode._build_roe_notes(payload, briefing=mode)
    bad = "do NOT intercept or fire at it" in txt
    print(f"  briefing={mode:<9} contains 'do NOT intercept or fire at it': {bad}")

print()
print("=" * 88)
print("(a) does pure-llm still receive the enemy timeline? (its own channel)")
print("=" * 88)
src = open(r"C:\Code\source-code\openmd\code\eval\pure_llm_agent.py",
           encoding="utf-8").read()
gate = 'briefing_declared' in src
inject = "timeline=timeline_text" in src
print(f"  pure_llm_agent.py gates the timeline on briefing_declared : {gate}")
print(f"  pure_llm_agent.py injects timeline_text unconditionally   : {inject}")
print("  => intel IS present for pure-llm in every briefing mode "
      f"({'confirmed' if inject and not gate else 'needs review'})")

print()
print("=" * 88)
print("the completed 'fairp' episodes (pure-llm, IE-11)")
print("=" * 88)
rows = []
for p in sorted(glob.glob(os.path.join(RUNS, "ie_purellm_ie-11*_fairp*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    c = d.get("strategy_scorecard") or {}
    rows.append((d.get("seed"), d.get("ticks_run"), d.get("total_fires_defender"),
                 float(c.get("defender_score", 0))))
    print(f"  {os.path.basename(p):<46} seed={d.get('seed')} "
          f"ticks={d.get('ticks_run'):<5} fires={d.get('total_fires_defender')} "
          f"score={c.get('defender_score')}")

print()
print("=" * 88)
print("the attribution table this unlocks")
print("=" * 88)
import statistics as st

if rows:
    fixed_intel = st.mean([r[3] for r in rows])
    print(f"  {'arm configuration':<40}{'pure-llm IE-11':>16}")
    print(f"  {'declared  (intel + BUG)':<40}{0.618:>16.3f}")
    print(f"  {'fixed     (intel, no bug)  <- these runs':<40}{fixed_intel:>16.3f}")
    print(f"  {'withheld  (no intel, no bug)  <- to run':<40}{'-':>16}")
    print()
    print(f"  bug-fix contribution  = {fixed_intel:.3f} - 0.618 = {fixed_intel - 0.618:+.3f}")
    print("  intel contribution    = (withheld) - (fixed)  [pending]")

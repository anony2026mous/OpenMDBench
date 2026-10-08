"""Inspect finished grid cells: validity + intelligence-provenance fields.

Every claim in the paper depends on knowing which口径 an episode ran under, so this
check reads the fields that prove it out of the report itself rather than trusting
the command line: `defender.briefing` (set by both LLM planners) and
`defender.speed_max_by_tag` (the envelope actually used by pure-llm).
"""
from __future__ import annotations

import glob
import json
import os
import sys

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

pats = sys.argv[1:] or ["*_n3*.json"]
files = []
for pat in pats:
    files.extend(glob.glob(os.path.join(RUNS, pat)))
files = sorted(set(files))

print("=" * 104)
print(f"GRID CELL INSPECTION   ({len(files)} files)")
print("=" * 104)
hdr = (f"  {'file':<44}{'planner':<9}{'seed':>5}{'ticks':>7}{'raw':>8}{'w':>6}"
       f"{'norm':>8}{'outcome':<18}{'briefing':<10}{'envelope'}")
print(hdr)
print("  " + "-" * 100)

bad = 0
for f in files:
    name = os.path.basename(f)
    try:
        d = json.loads(open(f, encoding="utf-8").read())
    except Exception as exc:  # noqa: BLE001
        print(f"  {name:<44} UNREADABLE {exc}")
        bad += 1
        continue
    if not isinstance(d, dict):
        print(f"  {name:<44} NOT A REPORT (list)")
        bad += 1
        continue
    card = d.get("strategy_scorecard") or {}
    de = d.get("defender") or {}
    raw = card.get("defender_score")
    w = card.get("scored_weight")
    # `defender_score` IS the normalised statistic (see strategy_metrics.py:625-629),
    # so it must NOT be divided by scored_weight again. Recompute it independently
    # from layers x weights x applicability and require agreement instead.
    layers = card.get("layers") or {}
    wts = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = sum(float(layers[k]) * float(wts[k]) for k in wts
              if app.get(k, True) and k in layers)
    den = sum(float(wts[k]) for k in wts if app.get(k, True))
    recomp = (num / den) if den else None
    agree = (raw is not None and recomp is not None and abs(raw - recomp) <= 5e-4)
    outcome = (card.get("terminal") or {}).get("outcome")
    br = de.get("briefing")
    if br is None and isinstance(de.get("planner"), dict):
        br = de["planner"].get("briefing")
    env = de.get("speed_max_by_tag")
    envs = (f"{env.get('uav')}/{env.get('usv')}" if isinstance(env, dict) else "-")
    ok = (int(d.get("ticks_run") or 0) > 0 and outcome not in (None, "undecided")
          and not d.get("aborted") and raw is not None and agree)
    if not ok:
        bad += 1
    print(f"  {name:<44}{str(d.get('planner')):<9}{str(d.get('seed')):>5}"
          f"{str(d.get('ticks_run')):>7}"
          f"{(f'{raw:.4f}' if raw is not None else '-'):>8}"
          f"{(f'{w:.2f}' if w else '-'):>6}"
          f"{(f'{recomp:.4f}' if recomp is not None else '-'):>8}"
          f"{str(outcome):<18}{str(br):<10}{envs}"
          + ("" if ok else "   <<< INVALID"))

print(f"\n  valid: {len(files) - bad}/{len(files)}   invalid: {bad}")
print("\n  'raw' is the headline statistic; 'recomp' is an independent recomputation")
print("  from layers x layer_weights x layer_applicability. They must agree - a")
print("  mismatch would mean the offline reweighting lost the applicability mask.")

"""Verify appendix G's legacy (declared-briefing) column -- the last unverified table.

Paper:  LLM+Rule 0.753 (n=82)   LLM+RL 0.782 (n=49)   Pure LLM 0.516 (n=40)
and the same table's no-intelligence column: 0.774 / 0.783 / 0.431, deltas
+0.021 / +0.000 / -0.085.

Source: `data/grid_withheld_5seeds/DATASET_5SEEDS.{csv,json}` (709 rows, one per episode).
The declared subset is 185 rows over the three LLM arms: 82 + 63 + 40. The paper's
LLM+RL figure uses 49 of the 63, and the rule is a checkpoint condition that the G3 audit
recorded only in prose ("LLM+RL declared checkpoint matched v9"):

    checkpoint_theta == "theta_arm5_llm_reward_v9.npz"

The other 14 declared llm-rl rows used `theta_arm5_rule.npz`, i.e. a rule-planner
checkpoint, so they are a different policy and must not be pooled.

Weighting: equal scenario means (the G3 design's `unit: seed, equal-weight per-seed mean
within one arm/batch`). No new CI is invented -- the audit explicitly declined to.

Independent corroboration: the same numbers appear precomputed in
`data/collaborator_runs/V14_TRACE_ANALYSIS_20261007_p01/G3_AUDIT_r02/analysis/nointel_recomputed.json`.
"""
from __future__ import annotations

import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DS = ROOT / "data" / "grid_withheld_5seeds"
CSV = DS / "DATASET_5SEEDS.csv"
AUDIT = (ROOT / "data" / "collaborator_runs" / "V14_TRACE_ANALYSIS_20261007_p01"
         / "G3_AUDIT_r02" / "analysis" / "nointel_recomputed.json")

V9 = "theta_arm5_llm_reward_v9.npz"
PAPER = {  # arm: (declared V, declared n, withheld V, delta)
    "llm-rule": (0.753, 82, 0.774, +0.021),
    "llm-rl": (0.782, 49, 0.783, +0.000),
    "pure-llm": (0.516, 40, 0.431, -0.085),
}

print("=" * 96)
print("appendix G legacy (declared) column  vs  DATASET_5SEEDS")
print("=" * 96)

if not CSV.is_file():
    print(f"  dataset not present: {CSV}")
    raise SystemExit(0)
rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
print(f"  dataset rows: {len(rows)}")

by = defaultdict(lambda: defaultdict(list))
withheld = defaultdict(lambda: defaultdict(list))
for r in rows:
    arm, br, sc = r["arm"], r["briefing"], r["scenario"]
    try:
        v = float(r["score"])
    except (TypeError, ValueError):
        continue
    if br == "declared":
        # the v9 checkpoint condition applies to llm-rl only
        if arm == "llm-rl" and (r.get("checkpoint_theta") or "") != V9:
            continue
        by[arm][sc].append(v)
    elif br == "withheld":
        withheld[arm][sc].append(v)

bad = 0
print(f"\n  {'arm':<10}{'scen':>5}{'n':>5}{'V':>9}{'paper':>8}{'paper n':>9}"
      f"{'withheld':>10}{'paper':>8}{'delta':>9}{'paper':>8}")
for arm, (pv, pn, pw, pd) in PAPER.items():
    sc = by.get(arm, {})
    if not sc:
        print(f"  {arm:<10}  NO DECLARED ROWS")
        bad += 1
        continue
    per = [st.mean(v) for v in sc.values()]
    n = sum(len(v) for v in sc.values())
    m = st.mean(per)
    wh = [st.mean(v) for v in withheld.get(arm, {}).values()]
    wm = st.mean(wh) if wh else float("nan")
    d = wm - m
    ok = abs(m - pv) <= 0.001 and n == pn and abs(wm - pw) <= 0.001 and abs(d - pd) <= 0.001
    bad += not ok
    print(f"  {arm:<10}{len(sc):>5}{n:>5}{m:>9.4f}{pv:>8.3f}{pn:>9}"
          f"{wm:>10.4f}{pw:>8.3f}{d:>+9.4f}{pd:>+8.3f}"
          f"{'   OK' if ok else '   <-- DIFFERS'}")

print(f"\n  cells mismatching the paper: {bad}/12")
print("  (3 declared V, 3 declared n, 3 withheld V, 3 deltas)")

if AUDIT.is_file():
    g = json.loads(AUDIT.read_text(encoding="utf-8"))
    print(f"\n  --- independent corroboration: G3_AUDIT_r02/analysis/nointel_recomputed.json ---")
    for arm in ("llm-rule", "llm-rl", "pure-llm"):
        e = g["effects"][arm]
        print(f"    {arm:<10} declared={e['declared']:.6f} (n={e['declared_n']})  "
              f"withheld={e['withheld']:.6f}  delta={e['delta']:+.6f}  "
              f"scenarios better={e['scenarios_withheld_better']}/{e['scenarios_compared']}")
    print(f"    weighting note: {g.get('weighting')}")

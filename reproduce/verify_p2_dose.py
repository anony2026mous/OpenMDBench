"""Verify the delivered P2 goal-dose batch against appendix I.2 / tab_p2_seedgrid.

Appendix I.2 reports eight stack-by-dose means. If the delivered P2 batch is the data
behind them, all eight must agree.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

RAW = Path(r"C:\Code\source-code\release_assets\collaborator_runs"
           r"\e2-delivery-20261003\raw")

# Values printed in appendix I.2 (paragraph I.2 and the dose-gain table).
PAPER = {
    ("hold", "rule-rl"): 0.213, ("hold", "llm-rl"): 0.213,
    ("mask2", "rule-rl"): 0.450, ("mask2", "llm-rl"): 0.517,
    ("mask1", "rule-rl"): 0.833, ("mask1", "llm-rl"): 0.710,
    ("strong", "rule-rl"): 0.670, ("strong", "llm-rl"): 0.750,
}

got: dict[tuple[str, str], list[float]] = {}
for d in sorted(RAW.glob("P2__*")):
    cond = d.name.split("__")[3]
    for p in d.rglob("episode.json"):
        e = json.loads(p.read_text(encoding="utf-8"))
        arm = e.get("config", {}).get("arm")
        v = e.get("V")
        if isinstance(v, (int, float)):
            got.setdefault((cond, arm), []).append(float(v))

print("=" * 92)
print("appendix I.2 dose-gain means  vs  delivered P2 batch")
print("=" * 92)
print(f"  {'condition':<10}{'stack':<10}{'n':>4}{'ours':>10}{'paper':>10}{'diff':>10}")
bad = 0
for (cond, arm), pv in PAPER.items():
    vs = got.get((cond, arm), [])
    if not vs:
        print(f"  {cond:<10}{arm:<10}   MISSING")
        bad += 1
        continue
    m = st.mean(vs)
    same = abs(m - pv) <= 0.0005
    if not same:
        bad += 1
    print(f"  {cond:<10}{arm:<10}{len(vs):>4}{m:>10.3f}{pv:>10.3f}"
          f"{m - pv:>+10.3f}{'' if same else '  <-- DIFFERS'}")

print(f"\n  mismatches: {bad}/8")
print(f"  status    : {'ALL AGREE' if bad == 0 else 'REVIEW REQUIRED'}")

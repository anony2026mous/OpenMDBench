"""Recompute G1's per-dose-tier deltas from the 10-seed data, two ways.

Why two: the earlier audit compared raw V across arms and declared "does not reproduce".
That was the wrong quantity -- and the batch itself distinguishes them.

  1. dV  = V(clean) - V(injected)          the convention G1's own pilot_analysis.json uses
  2. delta_planning / delta_execution      the decomposed attribution terms, which the
                                           design's prose calls dP / dE

If either matches the paper's 0.567 / 0.327, the published figure is explained.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "data" / "g1-fault-dose"
PAPER = {"planner": 0.567, "executor": 0.327}


def load(tier_dir: Path) -> dict:
    """Return {seed: {case: (V, dP, dE)}} for one tier directory."""
    out: dict[int, dict] = defaultdict(dict)
    clean = {}
    for p in (tier_dir / "clean").rglob("episode.json"):
        seed = int(p.parent.name.split("-")[-1])
        d = json.loads(p.read_text(encoding="utf-8"))
        clean[seed] = d
    for case in ("planner_wrong_contact", "action_hold"):
        for p in (tier_dir / case).rglob("episode.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            seed = d.get("config", {}).get("seed")
            if seed is None:
                continue
            out[seed][case] = d
    return {"clean": clean, **{s: dict(v) for s, v in out.items()}}


def field(d: dict, *names):
    for n in names:
        v = d.get(n)
        if isinstance(v, (int, float)):
            return float(v)
    return None


print("=" * 100)
print("G1 per-dose deltas, recomputed from the 10-seed batch")
print("=" * 100)

for tier in ("complex", "full"):
    root = BASE / tier
    # clean lives once; injected runs are nested under dose-N.NN
    clean: dict[int, dict] = {}
    for p in (root / "clean").rglob("episode.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        clean[d.get("config", {}).get("seed")] = d
    print(f"\n=== {tier}  (clean seeds: {len(clean)}) ===")

    for case in ("planner_wrong_contact", "action_hold"):
        print(f"\n  --- {case} ---")
        print(f"  {'dose':>6}{'n':>4}{'dV mean':>10}{'dP mean':>10}{'dE mean':>10}"
              f"{'paper':>8}")
        # layout is  <tier>/<case>/seed-NNN/dose-N.NN/episode.json
        by_dose: dict[str, list] = defaultdict(list)
        for p in (root / case).rglob("episode.json"):
            if "dose-" not in p.parent.name:
                continue
            by_dose[p.parent.name.split("-", 1)[1]].append(p)
        for dose in sorted(by_dose, key=float):
            dV, dP, dE = [], [], []
            for p in by_dose[dose]:
                d = json.loads(p.read_text(encoding="utf-8"))
                seed = d.get("config", {}).get("seed")
                c = clean.get(seed)
                if not c:
                    continue
                vc = field(c, "V") or field(c.get("metrics", {}), "blue_score")
                vi = field(d, "V") or field(d.get("metrics", {}), "blue_score")
                if vc is not None and vi is not None:
                    dV.append(vc - vi)
                dp = field(d, "delta_planning")
                de = field(d, "delta_execution")
                if dp is not None:
                    dP.append(dp)
                if de is not None:
                    dE.append(de)
            pv = PAPER["planner"] if case == "planner_wrong_contact" else PAPER["executor"]
            f = lambda xs: f"{st.mean(xs):>10.3f}" if xs else f"{'-':>10}"
            print(f"  {dose:>6}{len(dV):>4}{f(dV)}{f(dP)}{f(dE)}{pv:>8.3f}")

    # also the pooled mean across all doses, which is what a single figure implies
    print(f"\n  --- {tier}: pooled across all doses ---")
    for case in ("planner_wrong_contact", "action_hold"):
        dV, dP, dE = [], [], []
        for p in (root / case).rglob("episode.json"):
            if "dose-" not in p.parent.name:
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            seed = d.get("config", {}).get("seed")
            c = clean.get(seed)
            if c:
                vc = field(c, "V") or field(c.get("metrics", {}), "blue_score")
                vi = field(d, "V") or field(d.get("metrics", {}), "blue_score")
                if vc is not None and vi is not None:
                    dV.append(vc - vi)
            dp, de = field(d, "delta_planning"), field(d, "delta_execution")
            if dp is not None:
                dP.append(dp)
            if de is not None:
                dE.append(de)
        pv = PAPER["planner"] if case == "planner_wrong_contact" else PAPER["executor"]
        print(f"    {case:<24} n={len(dV):<4} dV={st.mean(dV) if dV else float('nan'):+.3f}"
              f"  dP={st.mean(dP) if dP else float('nan'):+.3f}"
              f"  dE={st.mean(dE) if dE else float('nan'):+.3f}   paper {pv:+.3f}")

"""Verify the replanning-frequency sweep (appendix H tab:frequency, figA2).

Appendix H: LLM+RL with a frozen MAPPO executor, goal-mode strong, 3 seeds/condition,
k in {10, 5, 2}; k=10 V=0.467, k=5 V=0.733, k=2 V=0.733, and the pure-RL baseline row
0.978 with a delta-vs-pure-RL column.

Two traps this check exists to catch:

  * The k=10-level directories also hold RL-arm episodes, so the arm must be filtered or
    the mean is wrong (0.680 instead of 0.467).
  * The pure-RL baseline is split across TWO locations: one episode under `E7-baseline/`
    and two under `E7-frequency-stage1/episodes/<seed>-rl/`. Reading only the first gives
    0.933 and makes the printed 0.978 look unsourced. All three are required.
"""
from __future__ import annotations

import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAMP = ROOT / "data" / "campaigns" / "paper-e5-e7-priority"
STAGE = CAMP / "E7-frequency-stage1"
BASE = CAMP / "E7-baseline"
PAPER = {2: 0.733, 5: 0.733, 10: 0.467}
PAPER_BASE = 0.978
PAPER_DELTA = {2: -0.244, 5: -0.244, 10: -0.511}

print("=" * 92)
print("appendix H replanning-frequency sweep  vs  E7-frequency-stage1")
print("=" * 92)


def seed_of(p: Path, cfg: dict, rec: dict) -> int | None:
    """The seed is not always in the record: E7-case.json omits it, the directory has it."""
    for src in (rec.get("seed"), cfg.get("seed")):
        if isinstance(src, int):
            return src
    m = re.search(r"(?:seed-)?(\d{10})", str(p))
    return int(m.group(1)) if m else None


# ---- every episode, keyed by (arm, interval, seed)
recs: list[tuple[str, int | None, int | None, float, str]] = []
for p in sorted(STAGE.rglob("episode.json")):
    e = json.loads(p.read_text(encoding="utf-8"))
    cfg = e.get("config", {})
    v = e.get("V")
    if isinstance(v, (int, float)):
        recs.append((cfg.get("arm"), cfg.get("plan_interval"), seed_of(p, cfg, e),
                     float(v), p.parent.name))
for p in sorted(BASE.rglob("episode.json")):
    e = json.loads(p.read_text(encoding="utf-8"))
    cfg = e.get("config", {})
    v = e.get("V")
    if isinstance(v, (int, float)):
        recs.append((cfg.get("arm"), cfg.get("plan_interval"), seed_of(p, cfg, e),
                     float(v), p.parent.name))
print(f"  episodes read (both locations): {len(recs)}")

bad = 0

print(f"\n  --- reported arm (llm-rl), the three sweep rows ---")
for k in (10, 5, 2):
    sel = [v for arm, iv, _s, v, _n in recs if arm == "llm-rl" and iv == k]
    if not sel:
        print(f"    k={k:<3} NO DATA")
        bad += 1
        continue
    m = st.mean(sel)
    ok = abs(m - PAPER[k]) <= 0.001
    bad += not ok
    print(f"    k={k:<3} n={len(sel)}  V={m:.4f}   paper {PAPER[k]:.3f}   "
          f"{'OK' if ok else 'DIFFERS'}")

print(f"\n  --- pure-RL baseline (all locations) ---")
base = [(sd, v, nm) for arm, iv, sd, v, nm in recs if arm == "rl"]
for sd, v, nm in sorted(base, key=lambda x: (x[0] is None, x[0])):
    print(f"    seed={sd}  V={v:.4f}   ({nm})")
if not base:
    print("    NO DATA")
    bad += 1
else:
    bm = st.mean([v for _sd, v, _nm in base])
    ok = abs(bm - PAPER_BASE) <= 0.001
    bad += not ok
    print(f"    n={len(base)}  mean={bm:.6f} -> {bm:.3f}   paper {PAPER_BASE:.3f}   "
          f"{'OK' if ok else 'DIFFERS'}")
    if len(base) < 3:
        print(f"    NOTE: only {len(base)} baseline episode(s); the caption implies one "
              f"per seed (3).")

    print(f"\n  --- delta vs pure-RL (paired by seed) ---")
    rl_by_seed = {sd: v for _a, _i, sd, v, _n in recs if _a == "rl"}
    for k in (10, 5, 2):
        diffs = [v - rl_by_seed[sd] for arm, iv, sd, v, _n in recs
                 if arm == "llm-rl" and iv == k and sd in rl_by_seed]
        if not diffs:
            print(f"    k={k:<3} no pairable seeds")
            bad += 1
            continue
        m = st.mean(diffs)
        ok = abs(m - PAPER_DELTA[k]) <= 0.001
        bad += not ok
        print(f"    k={k:<3} n={len(diffs)}  dV={m:+.4f}   paper {PAPER_DELTA[k]:+.3f}   "
              f"{'OK' if ok else 'DIFFERS'}")

print(f"\n  rows mismatching the paper: {bad}/7")
print("  (3 sweep rows + 1 baseline + 3 delta cells)")

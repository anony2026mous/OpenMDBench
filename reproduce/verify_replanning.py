"""Verify the replanning-frequency sweep (appendix H tab:frequency, figA2).

Appendix H: LLM+RL with a frozen MAPPO executor, goal-mode strong, 3 seeds/condition,
k in {10, 5, 2}; k=10 V=0.467, k=5 V=0.733, k=2 V=0.733. The k=10 directory also holds
RL-arm episodes, so the arm must be filtered or the mean is wrong (0.680 instead of
0.467) -- that is exactly the kind of silent error this check exists to catch.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\Code\source-code\release\OpenMDBench-Release")
STAGE = ROOT / "data" / "campaigns" / "paper-e5-e7-priority" / "E7-frequency-stage1"
BASE = ROOT / "data" / "campaigns" / "paper-e5-e7-priority" / "E7-baseline"
PAPER = {10: 0.467, 5: 0.733, 2: 0.733}

print("=" * 92)
print("appendix H replanning-frequency sweep  vs  E7-frequency-stage1")
print("=" * 92)

by_k: dict[int, list[tuple[float, str, str]]] = defaultdict(list)
for p in sorted(STAGE.rglob("episode.json")):
    e = json.loads(p.read_text(encoding="utf-8"))
    cfg = e.get("config", {})
    v = e.get("V")
    if isinstance(v, (int, float)):
        by_k[cfg.get("plan_interval")].append(
            (float(v), cfg.get("arm"), p.parent.name))

print(f"  {'k':>3}{'arm':<10}{'n':>4}{'mean':>9}{'paper':>9}{'diff':>9}")
bad = 0
for k in (10, 5, 2):
    rows = by_k.get(k, [])
    for arm in sorted({r[1] for r in rows if r[1]}):
        sel = [r[0] for r in rows if r[1] == arm]
        m = st.mean(sel) if sel else float("nan")
        pv = PAPER[k]
        ok = abs(m - pv) <= 0.001
        if arm == "llm-rl" and not ok:
            bad += 1
        tag = "MATCH" if ok else ""
        print(f"  {k:>3}{arm:<10}{len(sel):>4}{m:>9.3f}{pv:>9.3f}{m - pv:>+9.3f}  {tag}")

# llm-rl is the reported arm
print("\n  --- reported arm only (llm-rl) ---")
for k in (10, 5, 2):
    sel = [r[0] for r in by_k.get(k, []) if r[1] == "llm-rl"]
    m = st.mean(sel) if sel else float("nan")
    print(f"    k={k:<3} n={len(sel)}  V={m:.3f}   paper {PAPER[k]:.3f}   "
          f"{'OK' if abs(m - PAPER[k]) <= 0.001 else 'DIFFERS'}")

# pure-RL baseline for the delta column
print("\n  --- pure-RL baseline ---")
for d in (BASE,):
    for p in sorted(d.rglob("episode.json")):
        e = json.loads(p.read_text(encoding="utf-8"))
        print(f"    {p.parent.name[:44]:<46} arm={e.get('config', {}).get('arm')} "
              f"V={e.get('V')}")
print(f"\n  llm-rl mismatches: {bad}/3")

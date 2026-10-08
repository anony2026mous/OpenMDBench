"""Is the facilities layer continuous or quantised? And how coarse is the score?

If facilities can only take a few discrete values, then the 25%-weighted layer
acts like a coarse quantiser: the score moves in steps regardless of how finely
a method differs in behaviour.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}

fac: dict[str, Counter] = defaultdict(Counter)
dep: dict[str, list[float]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper().strip()
    sc = ALIAS.get(sc, sc)
    if not sc.startswith("IE-"):
        continue
    card = d.get("strategy_scorecard") or {}
    if card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    lay = card.get("layers") or {}
    if isinstance(lay.get("facilities"), (int, float)):
        fac[sc][round(float(lay["facilities"]), 3)] += 1
    if isinstance(lay.get("depth"), (int, float)):
        dep[sc].append(float(lay["depth"]))

print("=== distinct `facilities` values per scenario (how coarse is the dominant layer?) ===")
for sc in sorted(fac):
    c = fac[sc]
    print(f"  {sc:<28} distinct={len(c):>3}  values={sorted(c)[:10]}{'...' if len(c) > 10 else ''}")

print()
print("=== depth layer range per scenario ===")
for sc in sorted(dep):
    v = dep[sc]
    if len(v) < 3:
        continue
    print(f"  {sc:<28} n={len(v):>3}  min={min(v):.3f} max={max(v):.3f} "
          f"mean={sum(v)/len(v):.3f}")

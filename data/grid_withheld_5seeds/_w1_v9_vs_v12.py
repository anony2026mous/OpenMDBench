"""v9 vs v12 per scenario, plus what the baseline arms score on IE-08.

Needed to judge whether v9's IE-08 number is a defect or just a hard scenario.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
SHORT = {"arm5_llm_reward_v9": "v9", "arm5_v12": "v12"}

per: dict[tuple[str, str], list[float]] = defaultdict(list)
baseline: dict[tuple[str, str], list[float]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    try:
        with open(os.path.join(RUNS, fn), encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper().strip()
    sc = ALIAS.get(sc, sc)
    if sc not in SCEN:
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    planner = str(d.get("planner", "")).lower()
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    val = float(card["defender_score"])
    if planner in ("llm-rl", "llmrl") and tag in SHORT:
        per[(sc, tag)].append(val)
    elif planner == "rule":
        baseline[(sc, "rule-rule")].append(val)
    elif planner == "rl" and tag in ("rlb2", "nn1"):
        baseline[(sc, "rl")].append(val)

print("=== v9 vs v12, per scenario ===")
print(f"{'scenario':<28}{'v9':>9}{'n':>4}{'v12':>9}{'n':>4}   favours")
print("-" * 74)
deltas = []
for sc in SCEN:
    a, b = per.get((sc, "arm5_llm_reward_v9"), []), per.get((sc, "arm5_v12"), [])
    if a and b:
        ma, mb = st.mean(a), st.mean(b)
        deltas.append((sc, ma - mb))
        fav = "v9" if ma > mb else ("v12" if mb > ma else "tie")
        print(f"{sc:<28}{ma:>9.4f}{len(a):>4}{mb:>9.4f}{len(b):>4}   {fav}")
    else:
        print(f"{sc:<28}{(f'{st.mean(a):.4f}' if a else '-'):>9}{len(a):>4}"
              f"{(f'{st.mean(b):.4f}' if b else '-'):>9}{len(b):>4}   (no overlap)")

print()
big = [d for d in deltas if abs(d[1]) > 0.05]
print("scenarios where they differ by more than 0.05:")
for sc, dv in sorted(big, key=lambda x: -abs(x[1])):
    print(f"  {sc:<28} Δ{dv:+.4f}")

print()
print("=== IE-08: is 0.47 bad? what do the baseline arms score there? ===")
for arm in ("rule-rule", "rl"):
    vals = baseline.get(("IE-08-ISLAND-STRIKE", arm), [])
    if vals:
        print(f"  {arm:<10} n={len(vals)}  mean={st.mean(vals):.4f}  min={min(vals):.4f} max={max(vals):.4f}")
for tag, lab in SHORT.items():
    vals = per.get(("IE-08-ISLAND-STRIKE", tag), [])
    if vals:
        print(f"  {lab:<10} n={len(vals)}  mean={st.mean(vals):.4f}")

print()
print("=== IE-01: same question ===")
for arm in ("rule-rule", "rl"):
    vals = baseline.get(("IE-01-SINGLE-TARGET", arm), [])
    if vals:
        print(f"  {arm:<10} n={len(vals)}  mean={st.mean(vals):.4f}")
for tag, lab in SHORT.items():
    vals = per.get(("IE-01-SINGLE-TARGET", tag), [])
    if vals:
        print(f"  {lab:<10} n={len(vals)}  mean={st.mean(vals):.4f}")

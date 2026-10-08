"""Rank the llm-rl checkpoints using the SAME field the claim table uses.

The judgement metric is strategy_scorecard["defender_score"] (normalised, with a
recorded scored_weight) - NOT score.facility-integrity, which is an unnormalised
physical count and is therefore NOT comparable across scenarios.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}

data: dict[tuple[str, str], list[float]] = defaultdict(list)
seeds: dict[tuple[str, str], set[int]] = defaultdict(set)
weights: set = set()
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
    if sc not in SCENARIOS:
        continue
    if str(d.get("planner", "")).lower() not in ("llm-rl", "llmrl", "rl"):
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    name = os.path.basename(str(ex.get("theta") or ""))
    ck = tag or (name[len("theta_"):-len(".npz")] if name.startswith("theta_") else "")
    if not ck or "llm" not in ck:
        continue
    data[(sc, ck)].append(float(card["defender_score"]))
    weights.add(card.get("scored_weight"))
    sd = d.get("seed")
    if isinstance(sd, int):
        seeds[(sc, ck)].add(sd)

print("scored_weight values seen:", sorted(str(w)[:60] for w in weights))
cks = sorted({c for _, c in data})
print("checkpoints on the llm-rl arm:", ", ".join(c.replace("arm5_", "") for c in cks))
print()
hdr = f"{'scenario':<28}" + "".join(f"{c.replace('arm5_',''):>18}" for c in cks)
print(hdr)
print("-" * len(hdr))
per: dict[str, list[float]] = defaultdict(list)
for sc in SCENARIOS:
    row = f"{sc:<28}"
    for c in cks:
        vals = data.get((sc, c), [])
        if vals:
            m = st.mean(vals)
            per[c].append(m)
            row += f"{m:>12.4f}({len(seeds[(sc, c)])}s)"
        else:
            row += f"{'-':>18}"
    print(row)

print()
print("=== per-checkpoint summary (defender_score, mean over scenarios with data) ===")
for c in cks:
    vals = per.get(c, [])
    if not vals:
        continue
    hold = sum(1 for v in vals if v >= 0.5)
    print(f"  {c:<30} scenarios={len(vals):>2}  mean={st.mean(vals):.4f}  "
          f"median={st.median(vals):.4f}  hold={hold}/{len(vals)}")

print()
print("=== where checkpoints overlap (only these are fair comparisons) ===")
for i, a in enumerate(cks):
    for b in cks[i + 1:]:
        common = [sc for sc in SCENARIOS if data.get((sc, a)) and data.get((sc, b))]
        if common:
            wa = st.mean([st.mean(data[(sc, a)]) for sc in common])
            wb = st.mean([st.mean(data[(sc, b)]) for sc in common])
            print(f"  {a.replace('arm5_',''):<20} vs {b.replace('arm5_',''):<20} "
                  f"on {len(common)} common: {wa:.4f} vs {wb:.4f}  winner={a if wa>wb else b}")

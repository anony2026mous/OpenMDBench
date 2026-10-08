"""Recover the per-record layer-applicability mask, then re-weight correctly.

strategy_metrics.py drops inapplicable layers from the weighted mean and
renormalises (lines 602-629), but the raw `layers` block keeps placeholder
values. Any offline re-weighting MUST honour the same mask, otherwise it
re-introduces the exact bias that was fixed (IE-01/02 get free `surface`=1.0,
IE-03 loses 0.30 of weight to meaningless zero `depth`/`leak`).

The mask is recoverable: choose the applicable-subset that reproduces the
stored `scored_weight` AND the stored `defender_score` exactly.
"""
from __future__ import annotations

import itertools
import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
ARMS = {"rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm"),
        "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl"), "rule-rl": ("rulerl", "rule-rl")}
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"}, "rule-rl": {"arm5_v12"},
        "llm-rule": set(), "pure-llm": set(), "rule-rule": set()}
BASE = {"terminal": 0.20, "facilities": 0.25, "depth": 0.20, "leak": 0.10,
        "exchange": 0.10, "ammo": 0.05, "surface": 0.10}
LAYERS = list(BASE)


def recover_mask(layers: dict, scored_weight: float, stored: float):
    """Return the applicable-subset reproducing (scored_weight, stored)."""
    hits = []
    for r in range(len(LAYERS) + 1):
        for combo in itertools.combinations(LAYERS, r):
            if not combo:
                continue
            wsum = sum(BASE[k] for k in combo)
            if abs(wsum - scored_weight) > 1e-6:
                continue
            val = sum(layers[k] * BASE[k] for k in combo) / wsum
            if abs(val - stored) < 5e-5:
                hits.append(frozenset(combo))
    return hits


recs = []
ambiguous = 0
no_mask = 0
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper().strip()
    sc = ALIAS.get(sc, sc)
    if sc not in SCEN:
        continue
    card = d.get("strategy_scorecard") or {}
    if card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    pl = str(d.get("planner", "")).lower()
    arm = next((a for a, ks in ARMS.items() if pl in ks), None)
    if arm is None:
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    if WANT.get(arm) and tag and tag not in WANT[arm]:
        continue
    lay = card.get("layers") or {}
    if not all(isinstance(lay.get(k), (int, float)) for k in LAYERS):
        continue
    layers = {k: float(lay[k]) for k in LAYERS}
    hits = recover_mask(layers, float(card["scored_weight"]), float(card["defender_score"]))
    if not hits:
        no_mask += 1
        continue
    if len(hits) > 1:
        ambiguous += 1
    mask = hits[0] if len(hits) == 1 else max(hits, key=len)
    recs.append({"scenario": sc, "arm": arm, "layers": layers,
                 "mask": sorted(mask), "stored": float(card["defender_score"])})

print(f"records with a recovered mask : {len(recs)}")
print(f"records with NO matching mask : {no_mask}")
print(f"records with >1 candidate mask: {ambiguous}")
print()

# ------------------------------------------- validate + measure current weights
err = [abs(sum(r["layers"][k] * BASE[k] for k in r["mask"])
           / sum(BASE[k] for k in r["mask"]) - r["stored"]) for r in recs]
print(f"validation: max |recomputed - stored| = {max(err):.8f}   (must be ~0)")
print()

maskset = defaultdict(int)
for r in recs:
    maskset["+".join(r["mask"])] += 1
print("=== applicability masks seen ===")
for k, v in sorted(maskset.items(), key=lambda kv: -kv[1])[:12]:
    print(f"  {v:>4} runs  {k}")
print()


def score_of(rec, w):
    den = sum(w[k] for k in rec["mask"])
    return sum(rec["layers"][k] * w[k] for k in rec["mask"]) / den if den else 0.0


def evaluate(w):
    by = defaultdict(list)
    for r in recs:
        by[(r["scenario"], r["arm"])].append(score_of(r, w))
    rows = {}
    for sc in SCEN:
        means, sds = [], []
        for a in ARMS:
            v = by.get((sc, a), [])
            if len(v) >= 2:
                means.append(st.mean(v))
                sds.append(st.stdev(v))
        if len(means) < 2:
            continue
        between = max(means) - min(means)
        within = st.mean(sds)
        rows[sc] = (between, within, between / within if within > 0 else float("inf"))
    return rows


CANDIDATES = [
    ("current (default)", BASE),
    ("signal-only fac+depth", {"terminal": 0, "facilities": 0.5, "depth": 0.5, "leak": 0, "exchange": 0, "ammo": 0, "surface": 0}),
    ("fac .35 dep .35 term .15 ammo .15", {"terminal": 0.15, "facilities": 0.35, "depth": 0.35, "leak": 0, "exchange": 0, "ammo": 0.15, "surface": 0}),
    ("fac .40 dep .30 term .20 ammo .10", {"terminal": 0.20, "facilities": 0.40, "depth": 0.30, "leak": 0, "exchange": 0, "ammo": 0.10, "surface": 0}),
    ("fac .30 dep .30 term .20 leak .10 ammo .10", {"terminal": 0.20, "facilities": 0.30, "depth": 0.30, "leak": 0.10, "exchange": 0, "ammo": 0.10, "surface": 0}),
    ("fac .25 dep .25 term .20 leak .10 ammo .10 exch .10", {"terminal": 0.20, "facilities": 0.25, "depth": 0.25, "leak": 0.10, "exchange": 0.10, "ammo": 0.10, "surface": 0}),
]

res = []
for name, w in CANDIDATES:
    rows = evaluate(w)
    ratios = [r[2] for r in rows.values()]
    res.append((name, w, rows, st.mean(ratios), min(ratios),
                sum(1 for x in ratios if x >= 2.0), len(rows)))

print(f"{'scheme':<44}{'meanR':>7}{'minR':>7}{'sep':>6}{'n':>4}")
print("-" * 70)
for name, w, rows, mr, mnr, sep, n in res:
    print(f"{name:<44}{mr:>7.2f}{mnr:>7.2f}{sep:>6}{n:>4}")

print()
best = max(res, key=lambda x: (x[5], x[3]))
print(f"best by (separated, mean ratio) = {best[0]}")
print(f"  {'scenario':<28}{'current':>10}{'best':>10}   change")
for sc in SCEN:
    a = res[0][2].get(sc)
    b = best[2].get(sc)
    if not a or not b:
        continue
    print(f"  {sc:<28}{a[2]:>10.2f}{b[2]:>10.2f}   "
          f"{'better' if b[2] > a[2] else ('worse' if b[2] < a[2] else 'same')}")

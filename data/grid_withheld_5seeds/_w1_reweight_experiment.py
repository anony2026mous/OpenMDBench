"""Step 1: offline re-weighting of the existing 471 episodes.

strategy_metrics.py states every layer is reported raw so a reader can re-weight
without re-running.  This does exactly that: it rebuilds defender_score under
alternative weight vectors and measures whether the metric can better separate
the methods - purely from stored data, engine untouched.

Discrimination metric: for each scenario,
    between = max(arm mean) - min(arm mean)   over arms with n>=2
    within  = mean(arm sd)                    over the same arms
    ratio   = between / within
A ratio below ~2 means a different seed family could reorder the methods.
"""
from __future__ import annotations

import itertools
import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
OUT = r"C:\Code\source-code\openmd\code\eval\_w1_runs\_layer_values.json"
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
LAYERS = ["terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface"]

# ---------------------------------------------------------------- extract once
def extract():
    if os.path.exists(OUT):
        return json.load(open(OUT, encoding="utf-8"))
    recs = []
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
        vals = {ln: float(lay[ln]) for ln in LAYERS if isinstance(lay.get(ln), (int, float))}
        if len(vals) < len(LAYERS):
            continue
        recs.append({"scenario": sc, "arm": arm, "seed": d.get("seed"),
                     "layers": vals, "defender_score": float(card["defender_score"])})
    json.dump(recs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    return recs


recs = extract()
print(f"episodes extracted: {len(recs)}  -> {OUT}")
print()

# ---------------------------------------------------------------- evaluation
def score_of(rec, w):
    return sum(rec["layers"][ln] * w[ln] for ln in LAYERS) / sum(w.values())


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
        rows[sc] = (between, within, between / within if within > 0 else float("inf"),
                    min(means), max(means))
    return rows


def report(name, w):
    rows = evaluate(w)
    ratios = [r[2] for r in rows.values()]
    seps = sum(1 for r in ratios if r >= 2.0)
    # floor/ceiling: scenarios where every arm sits in a narrow band
    floor = sum(1 for r in rows.values() if r[4] < 0.5)
    ceil_ = sum(1 for r in rows.values() if r[3] > 0.85)
    return {
        "name": name, "weights": dict(w),
        "mean_ratio": st.mean(ratios), "min_ratio": min(ratios),
        "separated": seps, "n_scen": len(rows),
        "floor_scen": floor, "ceiling_scen": ceil_, "rows": rows,
    }


CUR = {"terminal": 0.20, "facilities": 0.25, "depth": 0.20, "leak": 0.10,
       "exchange": 0.10, "ammo": 0.05, "surface": 0.10}

CANDIDATES = [
    ("current (default)", CUR),
    ("signal-only: fac+depth", {"terminal": 0, "facilities": 0.5, "depth": 0.5, "leak": 0, "exchange": 0, "ammo": 0, "surface": 0}),
    ("fac+depth+terminal", {"terminal": 0.2, "facilities": 0.4, "depth": 0.4, "leak": 0, "exchange": 0, "ammo": 0, "surface": 0}),
    ("fac 0.4 / dep 0.3 / term 0.2 / rest 0.1", {"terminal": 0.2, "facilities": 0.4, "depth": 0.3, "leak": 0.02, "exchange": 0.02, "ammo": 0.02, "surface": 0.04}),
    ("fac 0.35 / dep 0.35 / term 0.15 / ammo 0.15", {"terminal": 0.15, "facilities": 0.35, "depth": 0.35, "leak": 0, "exchange": 0, "ammo": 0.15, "surface": 0}),
    ("fac 0.45 / dep 0.25 / term 0.15 / leak 0.15", {"terminal": 0.15, "facilities": 0.45, "depth": 0.25, "leak": 0.15, "exchange": 0, "ammo": 0, "surface": 0}),
]

results = [report(n, w) for n, w in CANDIDATES]

print(f"{'scheme':<44}{'meanR':>7}{'minR':>7}{'sep/14':>8}{'floor':>7}{'ceil':>6}")
print("-" * 82)
for r in results:
    print(f"{r['name']:<44}{r['mean_ratio']:>7.2f}{r['min_ratio']:>7.2f}"
          f"{r['separated']:>8}{r['floor_scen']:>7}{r['ceiling_scen']:>6}")

print()
print("=== per-scenario ratio: current vs the best signal-weighted variant ===")
best = max(results, key=lambda r: (r["separated"], r["mean_ratio"]))
print(f"best by (separated, mean ratio) = {best['name']}")
print(f"  {'scenario':<28}{'current':>10}{'best':>10}   change")
for sc in SCEN:
    a = results[0]["rows"].get(sc)
    b = best["rows"].get(sc)
    if not a or not b:
        continue
    arrow = "better" if b[2] > a[2] else ("worse" if b[2] < a[2] else "same")
    print(f"  {sc:<28}{a[2]:>10.2f}{b[2]:>10.2f}   {arrow}")

print()
print("=== sanity: does the re-weighted score still track the stored defender_score? ===")
cur = [score_of(r, CUR) for r in recs]
sto = [r["defender_score"] for r in recs]
diff = [abs(a - b) for a, b in zip(cur, sto)]
print(f"  n={len(cur)}  max|recomputed - stored| = {max(diff):.6f}  (0 => the layer data is complete)")

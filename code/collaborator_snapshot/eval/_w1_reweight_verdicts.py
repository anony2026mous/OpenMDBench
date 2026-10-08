"""Step 1c: apply each candidate weight vector and compare the ACTUAL judgements.

Uses the same rule the claim table uses:
    n>=2 on both sides and |delta| >= 2*pooled_sd  -> pass/fail
    n<2 on either side and |delta| < 0.05          -> insufficient evidence
    |delta| < 2*pooled_sd                          -> unreadable
    else                                           -> pass/fail

Comparing schemes by (separated scenarios) alone is not enough - what matters is
how many of the 84 inequalities can actually be decided.
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
BASE = {"terminal": 0.20, "facilities": 0.25, "depth": 0.20, "leak": 0.10,
        "exchange": 0.10, "ammo": 0.05, "surface": 0.10}
LAYERS = list(BASE)
# the arms the paper's inequalities compare
OPPONENTS = ["rule-rule", "rl", "pure-llm"]
HYBRIDS = ["llm-rule", "llm-rl"]
PLANNER_OF = {"rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm"),
              "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl")}
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"}, "llm-rule": set(),
        "pure-llm": set(), "rule-rule": set()}


def recover(layers, sw, stored):
    for r in range(1, len(LAYERS) + 1):
        for combo in itertools.combinations(LAYERS, r):
            ws = sum(BASE[k] for k in combo)
            if abs(ws - sw) > 1e-6:
                continue
            if abs(sum(layers[k] * BASE[k] for k in combo) / ws - stored) < 5e-5:
                return combo
    return None


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
    sc = ALIAS.get(str(d.get("scenario", "")).upper().strip(),
                   str(d.get("scenario", "")).upper().strip())
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
    arm = next((a for a, ks in PLANNER_OF.items() if pl in ks), None)
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
    m = recover(layers, float(card["scored_weight"]), float(card["defender_score"]))
    if m:
        recs.append({"scenario": sc, "arm": arm, "layers": layers, "mask": m})

print(f"episodes: {len(recs)}")


def verdict(base, ref):
    if not base or not ref:
        return "无数据", 0.0, 0
    mb, mr = st.mean(base), st.mean(ref)
    delta = mb - mr
    if len(base) < 2 and len(ref) < 2 and abs(delta) < 0.05:
        return "证据不足", delta, 0
    if len(base) >= 2 and len(ref) >= 2:
        sd = st.stdev(base + ref)
        if abs(delta) < 2 * sd:
            return "不可判读", delta, sd
    return ("通过" if delta > 0 else "未过"), delta, 0


def apply_weights(w):
    by = defaultdict(list)
    for r in recs:
        den = sum(w[k] for k in r["mask"])
        if den <= 0:
            continue
        by[(r["scenario"], r["arm"])].append(
            sum(r["layers"][k] * w[k] for k in r["mask"]) / den)
    return by


SCHEMES = [
    ("current (default)", BASE),
    ("fac.30 dep.40 term.20 ammo.10 (grid best)", {"terminal": 0.20, "facilities": 0.30, "depth": 0.40, "leak": 0.0, "exchange": 0.0, "ammo": 0.10, "surface": 0.0}),
    ("fac.30 dep.40 term.15 ammo.15", {"terminal": 0.15, "facilities": 0.30, "depth": 0.40, "leak": 0.0, "exchange": 0.0, "ammo": 0.15, "surface": 0.0}),
    ("fac.35 dep.35 term.15 ammo.15", {"terminal": 0.15, "facilities": 0.35, "depth": 0.35, "leak": 0.0, "exchange": 0.0, "ammo": 0.15, "surface": 0.0}),
]

print()
print("=== judgement outcome under each scheme (84 inequalities) ===")
print(f"{'scheme':<44}{'通过':>6}{'未过':>6}{'不可判读':>9}{'证据不足':>9}")
print("-" * 78)
detail = {}
for name, w in SCHEMES:
    by = apply_weights(w)
    tally = defaultdict(int)
    per = {}
    # a scenario/arm cell falls back to the weightless layers if denominator is 0
    for sc in SCEN:
        for hybrid in HYBRIDS:
            base = by.get((sc, hybrid), [])
            for opp in OPPONENTS:
                st_, delta, _ = verdict(base, by.get((sc, opp), []))
                tally[st_] += 1
                per[(sc, hybrid, opp)] = (st_, delta)
    detail[name] = per
    print(f"{name:<44}{tally['通过']:>6}{tally['未过']:>6}{tally['不可判读']:>9}{tally['证据不足']:>9}")

print()
print("=== where the grid-best scheme changes a verdict vs default ===")
cur = detail["current (default)"]
new = detail["fac.30 dep.40 term.20 ammo.10 (grid best)"]
changed = 0
for k in sorted(cur):
    if cur[k][0] != new[k][0]:
        changed += 1
        print(f"  {k[0]:<28} {k[1]:<9} vs {k[2]:<10} "
              f"{cur[k][0]:<6}(Δ{cur[k][1]:+.4f}) -> {new[k][0]:<6}(Δ{new[k][1]:+.4f})")
print(f"  changed verdicts: {changed}")

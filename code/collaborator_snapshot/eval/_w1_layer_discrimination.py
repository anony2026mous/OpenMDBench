"""Which layer actually carries separating signal? Upper bound on any re-weighting.

For each layer independently, compute between-arm spread vs within-arm noise.
Sign is removed: a layer may separate methods while being "lower is better", so
we report the absolute spread. The best achievable single-layer discrimination is
a hard ceiling on what re-weighting can buy, because a weighted mean of layers
whose signals are uncorrelated cannot exceed the strongest component by much.
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

# masks recovered in _w1_reweight_v2.py; recompute here for self-containment
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
    sc = ALIAS.get(str(d.get("scenario", "")).upper().strip(), str(d.get("scenario", "")).upper().strip())
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
    m = recover(layers, float(card["scored_weight"]), float(card["defender_score"]))
    if m:
        recs.append({"scenario": sc, "arm": arm, "layers": layers, "mask": m})

print(f"episodes: {len(recs)}")
print()
print("=== PER-LAYER discrimination (between-arm spread / within-arm noise) ===")
print("    computed only on records where that layer is APPLICABLE")
print(f"    {'layer':<12}{'meanR':>8}{'minR':>8}{'sep>=2':>8}{'appl.n':>8}   note")
layer_rows: dict[str, dict[str, float]] = {}
for ln in LAYERS:
    rows = {}
    for sc in SCEN:
        by = defaultdict(list)
        for r in recs:
            if r["scenario"] == sc and ln in r["mask"]:
                by[r["arm"]].append(r["layers"][ln])
        means = [st.mean(v) for v in by.values() if len(v) >= 2]
        sds = [st.stdev(v) for v in by.values() if len(v) >= 2]
        if len(means) >= 2:
            b = max(means) - min(means)
            w = st.mean(sds)
            rows[sc] = b / w if w > 0 else float("inf")
    layer_rows[ln] = rows
    if not rows:
        print(f"    {ln:<12}{'-':>8}{'-':>8}{'-':>8}{0:>8}")
        continue
    rs = list(rows.values())
    sep = sum(1 for x in rs if x >= 2)
    napp = sum(1 for r in recs if ln in r["mask"])
    note = ""
    if st.mean(rs) < 1.0:
        note = "<== carries no separating signal"
    elif sep >= 10:
        note = "<== strongest discriminator"
    print(f"    {ln:<12}{st.mean(rs):>8.2f}{min(rs):>8.2f}{sep:>8}{napp:>8}   {note}")

print()
print("=== per-scenario: which layer separates, and the achievable ceiling ===")
print(f"  {'scenario':<28}" + "".join(f"{ln[:7]:>9}" for ln in LAYERS))
for sc in SCEN:
    row = f"  {sc:<28}"
    for ln in LAYERS:
        v = layer_rows[ln].get(sc)
        row += f"{(f'{v:.2f}' if v is not None else '-'):>9}"
    print(row)

print()
print("=== ceiling test: best single-layer vs best weighted combination ===")
best_single = max(((ln, st.mean(list(layer_rows[ln].values()))) for ln in LAYERS
                   if layer_rows[ln]), key=lambda x: x[1])
print(f"  best single layer = {best_single[0]} (meanR {best_single[1]:.2f})")

# exhaustive-ish grid over the three layers that plausibly matter
best = None
grid = []
for wf in (0.2, 0.3, 0.4, 0.5):
    for wd in (0.2, 0.3, 0.4, 0.5):
        for wt in (0.0, 0.1, 0.2):
            for wa in (0.0, 0.05, 0.1, 0.15):
                rest = 1.0 - (wf + wd + wt + wa)
                if rest < -1e-9:
                    continue
                w = {"facilities": wf, "depth": wd, "terminal": wt, "ammo": wa,
                     "leak": rest / 2, "exchange": rest / 2, "surface": 0.0}
                by = defaultdict(list)
                for r in recs:
                    den = sum(w[k] for k in r["mask"])
                    if den <= 0:
                        continue
                    by[(r["scenario"], r["arm"])].append(
                        sum(r["layers"][k] * w[k] for k in r["mask"]) / den)
                ratios = []
                for sc in SCEN:
                    means = [st.mean(v) for (s, a), v in by.items() if s == sc and len(v) >= 2]
                    sds = [st.stdev(v) for (s, a), v in by.items() if s == sc and len(v) >= 2]
                    if len(means) >= 2:
                        ww = st.mean(sds)
                        ratios.append((max(means) - min(means)) / ww if ww > 0 else 99)
                if not ratios:
                    continue
                grid.append((sum(1 for x in ratios if x >= 2), st.mean(ratios),
                             min(ratios), w))
grid.sort(key=lambda x: (-x[0], -x[1]))
print(f"  grid points evaluated: {len(grid)}")
print(f"  {'sep/14':>7}{'meanR':>8}{'minR':>8}   weights")
for sep, mr, mnr, w in grid[:6]:
    ws = " ".join(f"{k[:3]}={v:.2f}" for k, v in w.items() if v > 0)
    print(f"  {sep:>7}{mr:>8.2f}{mnr:>8.2f}   {ws}")

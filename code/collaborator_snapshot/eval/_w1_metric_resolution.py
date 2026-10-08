"""Does the scoring mechanism actually separate methods?

Separates two different failure modes:
  * BETWEEN-method spread  = can the metric tell the 6 arms apart at all?
  * WITHIN-method spread   = seed noise of a single arm
If within >= between, the metric cannot rank methods on that scenario no matter
how many runs you collect.
"""
from __future__ import annotations

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
# one canonical checkpoint per arm so we measure the ARM, not the weight
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"},
        "rule-rl": {"arm5_v12"}, "llm-rule": set(), "pure-llm": set(), "rule-rule": set()}

vals: dict[tuple[str, str], list[float]] = defaultdict(list)
layers: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
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
    if sc not in SCEN:
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
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
    vals[(sc, arm)].append(float(card["defender_score"]))
    for ln, lv in (card.get("layers") or {}).items():
        if isinstance(lv, (int, float)):
            layers[(sc, arm)][ln].append(float(lv))

print(f"{'scenario':<28}{'between':>9}{'within':>9}{'ratio':>8}   verdict")
print("-" * 78)
compress = []
for sc in SCEN:
    means, withins = [], []
    for a in ARMS:
        v = vals.get((sc, a), [])
        if len(v) >= 2:
            means.append(st.mean(v))
            withins.append(st.stdev(v))
    if len(means) < 2:
        print(f"{sc:<28}{'-':>9}{'-':>9}{'-':>8}   too few arms with n>=2")
        continue
    between = max(means) - min(means)
    within = st.mean(withins)
    ratio = between / within if within else float("inf")
    tag = "OK" if ratio >= 2 else ("MARGINAL" if ratio >= 1 else "CANNOT SEPARATE")
    if ratio < 2:
        compress.append((sc, between, within, ratio))
    print(f"{sc:<28}{between:>9.4f}{within:>9.4f}{ratio:>8.2f}   {tag}")

print()
print("=== scenarios where the metric cannot cleanly separate methods ===")
for sc, b, w, r in compress:
    print(f"  {sc:<28} between={b:.4f} within={w:.4f} ratio={r:.2f}")

# which layer is near-binary / saturated?
print()
print("=== layer behaviour across all runs (is a layer saturated or binary?) ===")
agg: dict[str, list[float]] = defaultdict(list)
for sc in SCEN:
    for a in ARMS:
        for ln, vv in layers.get((sc, a), {}).items():
            agg[ln].extend(vv)
print(f"  {'layer':<12}{'n':>6}{'mean':>8}{'sd':>8}{'at 1.0':>9}{'at 0.0':>9}   note")
for ln in sorted(agg):
    v = agg[ln]
    if len(v) < 5:
        continue
    ones = sum(1 for x in v if x >= 0.999)
    zeros = sum(1 for x in v if x <= 0.001)
    note = ""
    if ones / len(v) > 0.6:
        note = "<== saturated at 1.0 (no discrimination)"
    elif (ones + zeros) / len(v) > 0.6:
        note = "<== mostly binary"
    print(f"  {ln:<12}{len(v):>6}{st.mean(v):>8.3f}{st.stdev(v):>8.3f}"
          f"{ones/len(v):>8.0%}{zeros/len(v):>8.0%}   {note}")

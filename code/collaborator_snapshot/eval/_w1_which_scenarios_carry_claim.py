"""Which scenarios can carry which claim?

Two different questions, and they give different answers:
  (a) 14-arm all-methods discrimination  -> "can this scenario tell ANY methods apart"
  (b) the paper's 6 inequalities only    -> "can this scenario support the CLAIM"
Also checks claim DIRECTION: a scenario can separate methods while the hybrid
still loses there.
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
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"}, "rule-rl": {"arm5_v12"},
        "llm-rule": set(), "pure-llm": set(), "rule-rule": set()}

vals: dict[tuple[str, str], list[float]] = defaultdict(list)
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


def stats(sc, arm):
    v = vals.get((sc, arm), [])
    if not v:
        return None, 0, 0.0
    return st.mean(v), len(v), (st.stdev(v) if len(v) > 1 else float("nan"))


print("=== (a) all-method discrimination, per scenario ===")
print(f"{'scenario':<28}{'between':>9}{'within':>9}{'ratio':>7}   n per arm (min..max)")
a_rows = {}
for sc in SCEN:
    means, sds, ns = [], [], []
    for a in ARMS:
        m, n, sd = stats(sc, a)
        if m is not None:
            ns.append(n)
        if n >= 2:
            means.append(m)
            sds.append(sd)
    if len(means) < 2:
        print(f"{sc:<28}{'-':>9}{'-':>9}{'-':>7}   n/a")
        continue
    b = max(means) - min(means)
    w = st.mean(sds)
    r = b / w if w > 0 else float("inf")
    a_rows[sc] = r
    print(f"{sc:<28}{b:>9.4f}{w:>9.4f}{r:>7.2f}   {min(ns)}..{max(ns)}")

print()
print("=== (b) 6-inequality spread: max(hybrid) - min(opponent) vs noise ===")
CORE = ["llm-rule", "llm-rl", "rule-rule", "rl", "pure-llm"]
print(f"{'scenario':<28}{'spread':>9}{'noise':>9}{'ratio':>7}   separable?")
b_rows = {}
for sc in SCEN:
    ms, sds = [], []
    for a in CORE:
        m, n, sd = stats(sc, a)
        if n >= 2 and m is not None:
            ms.append((a, m))
            sds.append(sd)
    if len(ms) < 2:
        print(f"{sc:<28}{'-':>9}{'-':>9}{'-':>7}   n/a")
        continue
    hv = [m for a, m in ms if a in ("llm-rule", "llm-rl")]
    op = [m for a, m in ms if a in ("rule-rule", "rl", "pure-llm")]
    if not hv or not op:
        print(f"{sc:<28}{'-':>9}{'-':>9}{'-':>7}   n/a")
        continue
    spread = max(hv) - min(op)
    w = st.mean(sds)
    r = spread / w if w > 0 else float("inf")
    b_rows[sc] = (spread, w, r)
    print(f"{sc:<28}{spread:>9.4f}{w:>9.4f}{r:>7.2f}   {'YES' if r >= 2 else 'no'}")

print()
print("=== which scenarios satisfy BOTH (a)>=2 and (b)>=2 ===")
good = [sc for sc in SCEN if a_rows.get(sc, 0) >= 2 and b_rows.get(sc, (0, 0, 0))[2] >= 2]
print(f"  {len(good)}/14: {', '.join(s.replace('IE-', '') for s in good)}")
weak = [sc for sc in SCEN if sc not in good]
print(f"  not usable: {len(weak)}/14: {', '.join(s.replace('IE-', '') for s in weak)}")

print()
print("=== direction check: is hybrid actually better on the usable scenarios? ===")
print(f"  {'scenario':<28}{'llm-rule':>10}{'llm-rl':>9}{'rule-rule':>11}{'rl':>9}{'pure-llm':>10}   verdict")
for sc in good:
    cells = {}
    for a in CORE:
        m, n, _ = stats(sc, a)
        cells[a] = f"{m:.3f}(n{n})" if m is not None else "-"
    hv = [stats(sc, a)[0] for a in ("llm-rule", "llm-rl") if stats(sc, a)[0] is not None]
    op = [stats(sc, a)[0] for a in ("rule-rule", "rl", "pure-llm") if stats(sc, a)[0] is not None]
    win = max(hv) > max(op) if hv and op else None
    print(f"  {sc:<28}{cells['llm-rule']:>10}{cells['llm-rl']:>9}{cells['rule-rule']:>11}"
          f"{cells['rl']:>9}{cells['pure-llm']:>10}   "
          f"{'hybrid wins' if win else 'HYBRID LOSES' if win is not None else '-'}")

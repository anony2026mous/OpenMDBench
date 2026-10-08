"""Is llm-rl bad because of THIS weight, or because of the architecture?

Three controlled comparisons, all on matched (scenario, seed) cells:
  A. executor effect under a FIXED planner : llm-rl(vX) vs llm-rule
  B. weight effect  within llm-rl          : vX vs vY on the same cells
  C. planner effect under a FIXED executor : llm-rl(v) vs rule-rl(v)
If A is negative for every weight but C is positive, the planner is fine and the
executor is the problem. If B varies a lot, it is a weight problem.
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

# (scenario, seed) -> {key: score}; key = planner or "planner:tag"
cells: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
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
    sd = d.get("seed")
    if not isinstance(sd, int):
        continue
    pl = str(d.get("planner", "")).lower()
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    key = pl if pl in ("rule", "llm") else f"{pl}:{tag}"
    # keep the best-known duplicate: last write wins is fine, but prefer records present
    cells[(sc, sd)][key] = float(card["defender_score"])


def mean_of(pred):
    v = [next(iter(d.values())) for k, d in cells.items() if pred(k, d)]
    return st.mean(v), len(v)


def paired(a_key, b_key, tag=None, only_pairs=True):
    """mean delta over cells that contain both keys."""
    ds, wins, losses = [], 0, 0
    per_scen = defaultdict(list)
    for (sc, sd), d in cells.items():
        ka = [k for k in d if k == a_key or (tag and k.startswith(a_key) and tag in k)]
        kb = [k for k in d if k == b_key or (tag and k.startswith(b_key) and tag in k)]
        if not ka or not kb:
            continue
        va, vb = d[ka[0]], d[kb[0]]
        ds.append(va - vb)
        per_scen[sc].append(va - vb)
        wins += va > vb
        losses += va < vb
    if not ds:
        return None
    return {"n": len(ds), "mean": st.mean(ds), "wins": wins, "losses": losses,
            "per_scen": per_scen}


TAGS = ["arm5_llm_reward_v9", "arm5_llm_full_ie03_v10", "arm5_v11", "arm5_v12",
        "arm5_v13_ie08", "arm5_v2", "arm5_v4", "arm5_llm_formal2", "arm5_rule"]

print("=== B. weight effect INSIDE llm-rl (paired, same scenario+seed) ===")
print(f"  {'tag':<26}{'n':>4}{'mean':>9}{'win/loss':>10}")
for t in TAGS:
    r = paired(f"llm-rl:{t}", f"llm-rl:{t}", tag=t)
    # compare each weight against v9 where they overlap
print("  (pairwise vs v9, only cells where both ran)")
for t in TAGS:
    if t == "arm5_llm_reward_v9":
        continue
    ds = []
    for (sc, sd), d in cells.items():
        a = d.get(f"llm-rl:{t}")
        b = d.get("llm-rl:arm5_llm_reward_v9")
        if a is not None and b is not None:
            ds.append(a - b)
    if ds:
        print(f"  {t:<26} n={len(ds):>3}  mean Δ vs v9 = {st.mean(ds):+.4f}  "
              f"(wins {sum(1 for x in ds if x>0)}/{len(ds)})")

print()
print("=== coverage per weight (how many cells it appears in) ===")
cnt = defaultdict(set)
for (sc, sd), d in cells.items():
    for k in d:
        if k.startswith("llm-rl:"):
            cnt[k.split(":", 1)[1]].add(sc)
for t in TAGS:
    if cnt.get(t):
        print(f"  {t:<26} {len(cnt[t]):>2} scenarios")

print()
print("=== A. executor effect under a FIXED llm planner: llm-rl(v9) vs llm-rule ===")
r = paired("llm-rl", "llm", tag="arm5_llm_reward_v9")
if r:
    print(f"  n={r['n']} paired cells   mean Δ = {r['mean']:+.4f}   "
          f"llm-rl wins {r['wins']}, loses {r['losses']}")
    print("  per scenario:")
    for sc in SCEN:
        v = r["per_scen"].get(sc)
        if v:
            print(f"    {sc:<28} n={len(v)} Δmean={st.mean(v):+.4f}")

print()
print("=== C. planner effect under a FIXED rl executor: llm-rl(v) vs rule-rl(v) ===")
for t in ("arm5_llm_reward_v9", "arm5_v12"):
    ds, per = [], defaultdict(list)
    for (sc, sd), d in cells.items():
        a, b = d.get(f"llm-rl:{t}"), d.get(f"rule-rl:{t}")
        if a is not None and b is not None:
            ds.append(a - b)
            per[sc].append(a - b)
    if ds:
        print(f"  tag={t:<26} n={len(ds):>3}  mean Δ = {st.mean(ds):+.4f}  "
              f"(llm planner wins {sum(1 for x in ds if x>0)}/{len(ds)})")
        for sc in SCEN:
            if per.get(sc):
                print(f"    {sc:<28} n={len(per[sc])} Δmean={st.mean(per[sc]):+.4f}")

print()
print("=== D. is the rl executor good under the RULE planner? rule-rl vs rule-rule ===")
ds, per = [], defaultdict(list)
for (sc, sd), d in cells.items():
    a = next((v for k, v in d.items() if k.startswith("rule-rl:")), None)
    b = d.get("rule")
    if a is not None and b is not None:
        ds.append(a - b)
        per[sc].append(a - b)
if ds:
    print(f"  n={len(ds)}  mean Δ = {st.mean(ds):+.4f}  (rl executor wins "
          f"{sum(1 for x in ds if x>0)}/{len(ds)})")
    for sc in SCEN:
        if per.get(sc):
            print(f"    {sc:<28} n={len(per[sc])} Δmean={st.mean(per[sc]):+.4f}")

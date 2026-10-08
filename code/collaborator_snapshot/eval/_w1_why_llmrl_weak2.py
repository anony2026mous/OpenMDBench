"""Fix the A comparison: executor effect under a FIXED llm planner.

Explicit key matching, no substring collision.
  llm-rl : planner "llm-rl" with a theta tag
  llm-rule: planner "llm" (no tag)
  rule-rl: planner "rule-rl" with a theta tag
  rule-rule: planner "rule"
Paired on the SAME (scenario, seed) cell, so only the executor differs.
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

# cell[(scen, seed)][(planner, tag)] = score
cell: dict[tuple[str, int], dict[tuple[str, str], float]] = defaultdict(dict)
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
    cell[(sc, sd)][(pl, tag)] = float(card["defender_score"])


def compare(name, left, right, want_tag=None):
    """left/right are planner names; when a planner needs a tag, pass want_tag."""
    ds, per = [], defaultdict(list)
    for (sc, sd), d in cell.items():
        lv = rv = None
        for (pl, tag), v in d.items():
            if pl == left and (want_tag is None or tag == want_tag):
                lv = v
            if pl == right and (want_tag is None or tag == want_tag):
                rv = v
        if lv is None or rv is None:
            continue
        ds.append(lv - rv)
        per[sc].append(lv - rv)
    print(f"\n--- {name} ---")
    if not ds:
        print("  no paired cells")
        return
    print(f"  paired cells n={len(ds)}   mean Δ = {st.mean(ds):+.4f}   "
          f"left wins {sum(1 for x in ds if x > 0)}/{len(ds)}   "
          f"median Δ = {st.median(ds):+.4f}")
    for sc in SCEN:
        v = per.get(sc)
        if v:
            print(f"    {sc:<28} n={len(v)}  Δmean={st.mean(v):+.4f}  "
                  f"win {sum(1 for x in v if x > 0)}/{len(v)}")


print("=" * 88)
print("A. EXECUTOR effect, planner FIXED to LLM   (llm-rl vs llm-rule)")
print("   only the executor differs: rule executor -> learned executor")
print("=" * 88)
for t in ("arm5_llm_reward_v9", "arm5_v12"):
    compare(f"llm planner + {t}", "llm-rl", "llm", want_tag=t)
# llm-rule has no tag, handle separately
ds, per = [], defaultdict(list)
for (sc, sd), d in cell.items():
    rv = d.get(("llm", ""))
    if rv is None:
        continue
    for (pl, tag), v in d.items():
        if pl == "llm-rl":
            ds.append(v - rv)
            per[sc].append(v - rv)
if ds:
    print(f"\n--- llm-rl (ALL tags) vs llm-rule ---")
    print(f"  paired cells n={len(ds)}   mean Δ = {st.mean(ds):+.4f}   "
          f"llm-rl wins {sum(1 for x in ds if x > 0)}/{len(ds)}")
    for sc in SCEN:
        if per.get(sc):
            print(f"    {sc:<28} n={len(per[sc])}  Δmean={st.mean(per[sc]):+.4f}")

print()
print("=" * 88)
print("D. EXECUTOR effect, planner FIXED to RULE   (rule-rl vs rule-rule)")
print("=" * 88)
ds, per = [], defaultdict(list)
for (sc, sd), d in cell.items():
    rv = d.get(("rule", ""))
    if rv is None:
        continue
    for (pl, tag), v in d.items():
        if pl == "rule-rl":
            ds.append(v - rv)
            per[sc].append(v - rv)
if ds:
    print(f"  paired cells n={len(ds)}   mean Δ = {st.mean(ds):+.4f}   "
          f"rl executor wins {sum(1 for x in ds if x > 0)}/{len(ds)}")
    for sc in SCEN:
        if per.get(sc):
            print(f"    {sc:<28} n={len(per[sc])}  Δmean={st.mean(per[sc]):+.4f}  "
                  f"win {sum(1 for x in per[sc] if x > 0)}/{len(per[sc])}")

print()
print("=" * 88)
print("C. PLANNER effect, executor FIXED to RL   (llm-rl vs rule-rl, same tag)")
print("=" * 88)
for t in ("arm5_llm_reward_v9", "arm5_v12"):
    ds, per = [], defaultdict(list)
    for (sc, sd), d in cell.items():
        a, b = d.get(("llm-rl", t)), d.get(("rule-rl", t))
        if a is not None and b is not None:
            ds.append(a - b)
            per[sc].append(a - b)
    if ds:
        print(f"  tag={t:<24} n={len(ds):>3}  mean Δ = {st.mean(ds):+.4f}  "
              f"llm planner wins {sum(1 for x in ds if x > 0)}/{len(ds)}")
        for sc in SCEN:
            if per.get(sc):
                print(f"    {sc:<28} Δmean={st.mean(per[sc]):+.4f}")

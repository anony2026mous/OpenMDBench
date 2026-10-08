"""Authoritative gap list: which (scenario, seed) are still missing for llm-rule / pure-llm.

Counts include the step-1 episodes already on disk (tag=top, seed 7 on g1) and
excludes the 30 old pure-llm episodes that carry no envelope record.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
TARGET = 3
SEEDS = [7, 11, 13, 17, 19]

by: dict[tuple[str, str], set] = defaultdict(set)
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
    if pl == "llm":
        by[(sc, "llm-rule")].add(sd)
    elif pl in ("pure-llm", "purellm"):
        de = d.get("defender") or {}
        # only accept pure-llm runs that RECORD the envelope (post-change)
        if isinstance(de, dict) and de.get("speed_max_by_tag"):
            by[(sc, "pure-llm")].add(sd)

print(f"{'scenario':<28}{'llm-rule seeds':>28}{'pure-llm seeds':>24}")
print("-" * 82)
plan: dict[str, list] = defaultdict(list)
for sc in SCEN:
    row = f"{sc:<28}"
    for arm in ("llm-rule", "pure-llm"):
        have = sorted(by.get((sc, arm), set()))
        need = TARGET - len(have)
        miss = [s for s in SEEDS if s not in have][:max(0, need)]
        for s in miss:
            plan[arm].append((sc, s))
        txt = f"{len(have)} {have}" + (f" +{miss}" if miss else " OK")
        row += f"{txt:>28}" if arm == "llm-rule" else f"{txt:>24}"
    print(row)

print()
for arm in ("llm-rule", "pure-llm"):
    items = plan[arm]
    per = defaultdict(list)
    for sc, s in items:
        per[sc].append(s)
    print(f"=== {arm}: {len(items)} episodes still missing ===")
    for sc in SCEN:
        if per.get(sc):
            print(f"    {sc:<28} seeds {per[sc]}")
    print()

# group into sweep invocations by seed
from collections import Counter
print("=== invocations by seed ===")
for arm in ("llm-rule", "pure-llm"):
    cnt = Counter(s for _, s in plan[arm])
    for s in sorted(cnt):
        scs = [sc for sc, ss in plan[arm] if ss == s]
        print(f"  {arm:<10} seed {s:<3} : {cnt[s]:>2} episodes  {[x.replace('IE-','') for x in scs]}")

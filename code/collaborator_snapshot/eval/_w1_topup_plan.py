"""Exact top-up list for the three arms: llm-rule, pure-llm, rl.

Target n>=3 on all 14 scenarios. Reports which seeds already exist per cell so we
only run the missing ones, and splits llm-rule by weight tag (llm-rule has no RL
executor, so tag is empty).
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

# (scenario, arm) -> {seed: [scores]}
by: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
env_seen: dict[tuple[str, str], set] = defaultdict(set)
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
    arm = {"llm": "llm-rule", "pure-llm": "pure-llm", "purellm": "pure-llm",
           "rl": "rl"}.get(pl)
    if arm is None:
        continue
    if arm == "rl":
        ex = (d.get("defender") or {}).get("executor") or {}
        meta = ex.get("checkpoint_meta") or {}
        tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
        if tag and tag not in ("rlb2", "nn1"):
            continue
    by[(sc, arm)][sd].append(float(card["defender_score"]))
    if arm == "pure-llm":
        de = d.get("defender") or {}
        if isinstance(de, dict) and "speed_max_by_tag" in de:
            env_seen[(sc, arm)].add(json.dumps(de["speed_max_by_tag"], sort_keys=True))

SEEDS = [7, 11, 13, 17, 19]
print(f"target n>={TARGET} per (scenario, arm)\n")
print(f"{'scenario':<28}" + "".join(f"{a:>34}" for a in ("llm-rule", "pure-llm", "rl")))
print("-" * 130)
plan: dict[str, list] = defaultdict(list)
total = 0
for sc in SCEN:
    row = f"{sc:<28}"
    for arm in ("llm-rule", "pure-llm", "rl"):
        have = by.get((sc, arm), {})
        n = sum(len(v) for v in have.values())
        need = max(0, TARGET - n)
        seeds_have = sorted(have)
        miss = [s for s in SEEDS if s not in have][:need]
        for s in miss:
            plan[arm].append((sc, s))
        total += len(miss)
        cell = f"n={n} seeds={seeds_have}" + (f" +{miss}" if miss else " OK")
        row += f"{cell:>34}"
    print(row)

print()
print("=== top-up plan ===")
for arm in ("llm-rule", "pure-llm", "rl"):
    items = plan[arm]
    print(f"\n  {arm}: {len(items)} episodes")
    if items:
        per_scen = defaultdict(list)
        for sc, s in items:
            per_scen[sc].append(s)
        for sc, ss in per_scen.items():
            print(f"    {sc:<28} seeds {ss}")

print()
print(f"TOTAL episodes to run: {total}")

print()
print("=== pure-llm envelope provenance (all MUST be re-run) ===")
n_env = sum(1 for k in env_seen if k[1] == "pure-llm")
n_recorded = 0
for (sc, arm), vals in env_seen.items():
    if arm == "pure-llm" and vals:
        n_recorded += 1
print(f"  pure-llm runs with a recorded envelope : {n_recorded}")
print(f"  pure-llm runs WITHOUT one (unusable)   : {len(by.get(('IE-01-SINGLE-TARGET','pure-llm'), {})) and 'see count below'}")
tot_pure = sum(sum(len(v) for v in by.get((sc, 'pure-llm'), {}).values()) for sc in SCEN)
print(f"  pure-llm episodes on the 14 scenarios  : {tot_pure}  -> all superseded by the envelope change")

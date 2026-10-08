"""Audit the E1..E8 experiment list against what is actually on disk.

Also measures the LLM'determinism question nobody has tested: for the SAME
(scenario, seed, planner, tag) configuration, how much do repeated runs differ?
A deterministic pipeline should give identical scores; LLM arms will not.
That variance is the floor on every comparison in the paper.
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

# group repeats of the SAME configuration
cfg: dict[tuple, list[float]] = defaultdict(list)
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
    pl = str(d.get("planner", "")).lower()
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    de = d.get("defender") or {}
    env = json.dumps(de.get("speed_max_by_tag"), sort_keys=True) if isinstance(de, dict) else ""
    # configuration identity: scenario, seed, planner, executor weight, envelope
    cfg[(sc, sd, pl, tag, env)].append(float(card["defender_score"]))

print("=== LLM determinism: repeats of the IDENTICAL configuration ===")
print("    (same scenario, seed, planner, weight, envelope)")
for pl_label, pls in (("pure-deterministic (rule/rl)", ("rule", "rl", "rule-rl")),
                      ("LLM arms (llm/pure-llm/llm-rl)", ("llm", "pure-llm", "llm-rl"))):
    spreads, reps = [], 0
    detail = []
    for k, v in cfg.items():
        if k[2] not in pls or len(v) < 2:
            continue
        reps += 1
        spread = max(v) - min(v)
        spreads.append(spread)
        detail.append((k[0], k[1], k[2], len(v), st.mean(v), spread))
    print(f"\n  {pl_label}: {reps} configurations with >=2 repeats")
    if spreads:
        print(f"    spread (max-min): mean={st.mean(spreads):.4f}  median={st.median(spreads):.4f}  "
              f"max={max(spreads):.4f}")
        print("    worst cases:")
        for sc, sd, pl, n, m, s in sorted(detail, key=lambda x: -x[5])[:8]:
            print(f"      {sc:<28} seed={sd} {pl:<8} n={n} mean={m:.4f} spread={s:.4f}")

print()
print("=== summary: how much does an LLM arm wobble on a fixed configuration? ===")
for pl in ("llm", "pure-llm", "llm-rl", "rule", "rl", "rule-rl"):
    sp = [max(v) - min(v) for k, v in cfg.items() if k[2] == pl and len(v) >= 2]
    if sp:
        print(f"  {pl:<10} repeats={len(sp):>3}  mean spread={st.mean(sp):.4f}  max={max(sp):.4f}")

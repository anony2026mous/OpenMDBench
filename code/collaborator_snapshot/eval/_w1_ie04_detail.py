"""IE-04 detail: the scenario that anchors the 'executor is the bottleneck' claim."""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
TARGET = "IE-04-COMBINED-ARMS"
ARMS = {"rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm"),
        "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl"), "rule-rl": ("rulerl", "rule-rl")}

rows: dict[str, list[tuple[int, float, float, str, str]]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if str(d.get("scenario", "")).upper() != TARGET:
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    pl = str(d.get("planner", "")).lower()
    arm = next((a for a, ks in ARMS.items() if pl in ks), None)
    if arm is None:
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    lay = card.get("layers") or {}
    rows[arm].append((int(d.get("seed") or -1), float(card["defender_score"]),
                      float(lay.get("facilities", float("nan"))),
                      float(lay.get("depth", float("nan"))), tag))

print(f"=== {TARGET} : every run, by arm ===")
for arm in ARMS:
    rs = sorted(rows.get(arm, []))
    if not rs:
        continue
    sc = [r[1] for r in rs]
    print(f"\n  {arm}  n={len(rs)}  mean={st.mean(sc):.4f}  sd={st.stdev(sc) if len(sc) > 1 else 0:.4f}")
    print(f"    {'seed':>5}{'score':>9}{'facil':>8}{'depth':>8}  tag")
    for sd, s, f, dp, tag in rs:
        print(f"    {sd:>5}{s:>9.4f}{f:>8.3f}{dp:>8.3f}  {tag}")

print()
print("=== range vs noise ===")
allsc = [r[1] for rs in rows.values() for r in rs]
means = [st.mean([r[1] for r in rs]) for rs in rows.values() if len(rs) >= 2]
sds = [st.stdev([r[1] for r in rs]) for rs in rows.values() if len(rs) >= 2]
print(f"  all runs            : n={len(allsc)}  min={min(allsc):.4f} max={max(allsc):.4f} spread={max(allsc)-min(allsc):.4f}")
print(f"  arm means           : {[round(m,4) for m in means]}")
print(f"  between-arm range   : {max(means)-min(means):.4f}")
print(f"  mean within-arm sd  : {st.mean(sds):.4f}")

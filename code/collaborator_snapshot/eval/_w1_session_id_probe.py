"""Why does a DETERMINISTIC arm (rule) vary between identical runs?

Hypothesis: the engine's engagement dice are seeded from
`resolved_hash|session_id|tick|...` (see factory_v2.py:4050) and session_id is
generated fresh per run, so the same (scenario, seed) replays differently.
This checks whether session_id actually differs across repeated runs and whether
the score spread tracks it.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

groups: dict[tuple, list[tuple]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    pl = str(d.get("planner", "")).lower()
    if pl != "rule":
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    key = (str(d.get("scenario")), d.get("seed"))
    groups[key].append((fn, d.get("session_id"), float(card["defender_score"]),
                        d.get("ticks_run")))

print("=== rule arm: repeated runs of the same (scenario, seed) ===")
for key in sorted(groups, key=lambda k: str(k)):
    v = groups[key]
    if len(v) < 2:
        continue
    sessions = {s for _, s, _, _ in v}
    scores = [s for _, _, s, _ in v]
    spread = max(scores) - min(scores)
    print(f"\n  {key[0]} seed={key[1]}   n={len(v)}  distinct session_id={len(sessions)}  "
          f"spread={spread:.4f}")
    for fn, sid, sc, tk in v[:6]:
        print(f"      score={sc:.4f} ticks={tk:<5} session_id={str(sid)[:44]}")
    if len(v) > 6:
        print(f"      ... +{len(v)-6} more")
    if len(sessions) == 1 and spread > 0.01:
        print("      >>> SAME session_id but different score: unresolved non-determinism")

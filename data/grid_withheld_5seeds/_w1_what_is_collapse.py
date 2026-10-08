"""What does "the arm collapses on scenario X" actually mean? Show the raw runs.

Prints, for a scenario x arm/checkpoint, the terminal outcome, tick count,
score and the distinguishing counters - so "collapse" is defined by evidence.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
TAIL_MIN = 890


def load():
    out = []
    for fn in os.listdir(RUNS):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        out.append((fn, d))
    return out


ALL = load()


def show(scen: str, label: str, want_ck: str | None = None, planner=None):
    print(f"\n--- {scen} / {label} ---")
    rows = []
    for fn, d in ALL:
        sc = ALIAS.get(str(d.get("scenario", "")).upper(), str(d.get("scenario", "")).upper())
        if sc != scen:
            continue
        card = d.get("strategy_scorecard") or {}
        ex = (d.get("defender") or {}).get("executor") or {}
        meta = ex.get("checkpoint_meta") or {}
        tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
        pl = str(d.get("planner", "")).lower()
        if planner and pl not in planner:
            continue
        if want_ck is not None:
            if pl not in ("llm-rl", "llmrl") or tag != want_ck:
                continue
        term = (card.get("terminal") or {})
        term2 = d.get("terminal_result") or {}
        rows.append({
            "file": fn[:52],
            "seed": d.get("seed"),
            "ticks": d.get("ticks_run"),
            "outcome": term.get("outcome") or term2.get("outcome"),
            "score": card.get("defender_score"),
            "fires": d.get("total_fires_defender"),
            "tag": tag or pl,
        })
    rows.sort(key=lambda r: (str(r["seed"]), r["file"]))
    print(f"  {'seed':>5} {'ticks':>6} {'outcome':<18} {'score':>8} {'fires':>6}  tag")
    for r in rows:
        sc = f"{r['score']:.4f}" if isinstance(r["score"], (int, float)) else "-"
        flag = "  <== TAIL" if isinstance(r["ticks"], int) and r["ticks"] >= TAIL_MIN else ""
        print(f"  {str(r['seed']):>5} {str(r['ticks']):>6} {str(r['outcome']):<18} {sc:>8} "
              f"{str(r['fires']):>6}  {r['tag']}{flag}")


print("=" * 100)
print("IE-01  where v12 is said to collapse (3/3 tail)  vs  v9 (3/3 hold)")
print("=" * 100)
show("IE-01-SINGLE-TARGET", "v12", want_ck="arm5_v12")
show("IE-01-SINGLE-TARGET", "v9", want_ck="arm5_llm_reward_v9")

print()
print("=" * 100)
print("IE-08  where v9 scores ~0.47  vs  the rule-rule baseline's spread")
print("=" * 100)
show("IE-08-ISLAND-STRIKE", "v9", want_ck="arm5_llm_reward_v9")
show("IE-08-ISLAND-STRIKE", "rule-rule baseline", planner=("rule",))

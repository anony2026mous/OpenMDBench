"""Why can the defender not kill the intruder? Read one 899-tick run in full."""
from __future__ import annotations

import json
import os

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"


def dump(fn: str) -> None:
    p = os.path.join(RUNS, fn)
    d = json.load(open(p, encoding="utf-8"))
    print("=" * 96)
    print(fn)
    print("=" * 96)
    print("scenario    :", d.get("scenario"))
    print("seed        :", d.get("seed"))
    print("ticks_run   :", d.get("ticks_run"))
    print("fires       : total", d.get("total_fires"),
          "| defender", d.get("total_fires_defender"),
          "| intruder", d.get("total_fires_intruder"))
    print("score_state :", json.dumps(d.get("score_state"), ensure_ascii=False))
    tr = d.get("terminal_result") or {}
    print("terminal    : outcome=", tr.get("outcome"), " rule=", tr.get("rule_id"), " tick=", tr.get("tick"))
    card = d.get("strategy_scorecard") or {}
    print("defender_score:", card.get("defender_score"), " scored_weight:", card.get("scored_weight"))
    print("engagements_by_target_role:", json.dumps(d.get("engagements_by_target_role"), ensure_ascii=False))
    print("engagements_by_target     :", json.dumps(d.get("engagements_by_target"), ensure_ascii=False))
    print("damage_by_kind            :", json.dumps(d.get("damage_by_kind"), ensure_ascii=False))
    print("fire_rejections           :", json.dumps(d.get("fire_rejections"), ensure_ascii=False)[:300])
    print("mission_states            :", json.dumps(d.get("mission_states"), ensure_ascii=False)[:300])
    print()
    print("entities (final state):")
    for e in d.get("entities") or []:
        print("   ", json.dumps(e, ensure_ascii=False))
    print()
    print("layered_metrics:")
    lm = d.get("layered_metrics") or {}
    for k in sorted(lm):
        v = lm[k]
        if not isinstance(v, (dict, list)):
            print(f"    {k:<34} {v}")
    print()


for name in ("ie_llmrl_ie-01-single-target_v12a.json",
             "ie_llmrl_ie-01-single-target_v9_paired_final.json"):
    if os.path.exists(os.path.join(RUNS, name)):
        dump(name)

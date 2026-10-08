"""Early look at the withheld verdict table, from whatever cells have landed.

Marked EARLY on purpose: at this point each withheld cell is n=1, so these are
single-episode readings, not arm means.  The point of running it now is to catch a
systemic problem while P1 is still in flight (e.g. an arm that is broken, or a
口径 that silently changed nothing) rather than after the whole grid finishes.

The archived `declared` column is shown alongside, since the headline comparison of
this project is "same arms, same scenarios, with vs without intelligence".
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "<private-archive>" / "declared_briefing_snapshot_20260927_1419" / "results"
RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ARMS = ["llm-rule", "llm-rl", "pure-llm", "rule-rule", "rl"]
PLANNER_TO_ARM = {"llm": "llm-rule", "llm-rl": "llm-rl", "pure-llm": "pure-llm",
                  "rule": "rule-rule", "rl": "rl"}


def recomp(card):
    layers = card.get("layers") or {}
    wts = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = sum(float(layers[k]) * float(wts[k]) for k in wts
              if app.get(k, True) and k in layers)
    den = sum(float(wts[k]) for k in wts if app.get(k, True))
    return (num / den) if den else None


def score_of(d):
    card = d.get("strategy_scorecard") or {}
    raw = card.get("defender_score")
    if raw is None:
        return None
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        return None
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        return None
    rc = recomp(card)
    if rc is None or abs(float(raw) - rc) > 5e-4:
        return None
    return float(raw)


def briefing_of(d):
    de = d.get("defender") or {}
    b = de.get("briefing")
    if b is None and isinstance(de.get("planner"), dict):
        b = de["planner"].get("briefing")
    return b if isinstance(b, str) else None


def arm_of(d):
    pl = str(d.get("planner") or "").lower()
    arm = PLANNER_TO_ARM.get(pl)
    if arm == "rl":
        # the rl arm's checkpoint_meta sits under defender.planner; distinguish it
        # from a bare rule run by the policy input width
        de = d.get("defender") or {}
        meta = {}
        for blk in ("executor", "planner"):
            b = de.get(blk)
            if isinstance(b, dict):
                m = b.get("checkpoint_meta") or {}
                if isinstance(m, dict) and m:
                    meta = m
                    break
        if meta.get("obs_dim") != 2866:
            return None
    if arm == "llm-rl":
        de = d.get("defender") or {}
        ex = de.get("executor") or {}
        meta = ex.get("checkpoint_meta") or {} if isinstance(ex, dict) else {}
        tag = str(meta.get("tag") or "")
        if tag and tag != "arm5_llm_reward_v9":
            return None
    return arm


withh: dict[tuple, list] = defaultdict(list)
decl: dict[tuple, list] = defaultdict(list)

for p in RUNS.glob("*_n3*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    arm = arm_of(d)
    if arm is None:
        continue
    sc = str(d.get("scenario") or "").upper()
    if sc not in SCEN:
        continue
    if arm in ("llm-rule", "llm-rl", "pure-llm") and briefing_of(d) != "withheld":
        continue
    v = score_of(d)
    if v is None:
        continue
    withh[(sc, arm)].append(d)

for p in SNAP.glob("*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if briefing_of(d) == "withheld":
        continue
    arm = arm_of(d)
    if arm is None:
        continue
    sc = str(d.get("scenario") or "").upper()
    if sc not in SCEN:
        continue
    v = score_of(d)
    if v is not None:
        decl[(sc, arm)].append(d)

print("=" * 112)
print("EARLY VERDICT TABLE  (withheld = this session, n=1 per cell for now)")
print("=" * 112)
print(f"\n  {'scenario':<28}" + "".join(f"{a:>16}" for a in ARMS))
print(f"  {'':<28}" + "".join(f"{'whd / decl':>16}" for _ in ARMS))
print("  " + "-" * 108)


def cell(sc, arm):
    w = withh.get((sc, arm), [])
    dd = decl.get((sc, arm), [])
    ws = [score_of(x) for x in w]
    ds = [score_of(x) for x in dd]
    ws = [x for x in ws if x is not None]
    ds = [x for x in ds if x is not None]
    left = f"{st.mean(ws):.3f}" if ws else "-"
    right = f"{st.mean(ds):.3f}" if ds else "-"
    return f"{left}/{right}"


for sc in SCEN:
    print(f"  {sc:<28}" + "".join(f"{cell(sc, a):>16}" for a in ARMS))

print("\n  coverage (withheld):")
for a in ARMS:
    n = sum(1 for sc in SCEN if withh.get((sc, a)))
    print(f"    {a:<10} {n}/14 scenarios")

print("\n  EARLY: single-episode readings for the LLM arms; do not quote as means.")

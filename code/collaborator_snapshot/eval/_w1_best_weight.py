"""Which weight candidate is actually best?

Discipline:
  * metric = strategy_scorecard["defender_score"] (the claim table's metric);
  * only compare on scenarios the candidates SHARE (else coverage differs);
  * split by scored_weight and by mode (hold vs 899-tick tail), because a tail
    run scores ~0.66 for reasons that have nothing to do with the weight.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
SHORT = {"arm5_llm_reward_v9": "v9", "arm5_llm_full_ie03_v10": "v10",
         "arm5_v11": "v11", "arm5_v12": "v12", "arm5_v13_ie08": "v13"}
TAIL_MIN_TICKS = 890

# (scen, ck) -> list of (score, seed, ticks, scored_weight)
data: dict[tuple[str, str], list[tuple[float, int, int, str]]] = defaultdict(list)
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    try:
        with open(os.path.join(RUNS, fn), encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper().strip()
    sc = ALIAS.get(sc, sc)
    if sc not in SCENARIOS:
        continue
    if str(d.get("planner", "")).lower() not in ("llm-rl", "llmrl"):
        continue
    card = d.get("strategy_scorecard") or {}
    if "defender_score" not in card or card.get("scored_weight") is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    name = os.path.basename(str(ex.get("theta") or ""))
    ck = tag or (name[len("theta_"):-len(".npz")] if name.startswith("theta_") else "")
    if ck not in SHORT:
        continue
    data[(sc, ck)].append((float(card["defender_score"]), int(d.get("seed") or -1),
                           int(d.get("ticks_run") or 0), str(card.get("scored_weight"))))

print("=== coverage per candidate (runs / scenarios / seeds) ===")
for ck, lab in SHORT.items():
    runs = [r for sc in SCENARIOS for r in data.get((sc, ck), [])]
    scs = [sc for sc in SCENARIOS if data.get((sc, ck))]
    sd = {r[1] for r in runs}
    print(f"  {lab:<4} runs={len(runs):>3}  scenarios={len(scs):>2}  seeds={sorted(sd)}")

print()
print("=== scored_weight mix (must be comparable) ===")
mix = defaultdict(int)
for sc in SCENARIOS:
    for ck in SHORT:
        for r in data.get((sc, ck), []):
            mix[r[3]] += 1
for k, v in sorted(mix.items()):
    print(f"  scored_weight={k}: {v} runs")

# ---------------- pairwise on SHARED scenarios only ----------------
print()
print("=== pairwise comparison on SHARED scenarios (all seeds) ===")
cks = [c for c in SHORT if any(data.get((sc, c)) for sc in SCENARIOS)]
for i, a in enumerate(cks):
    for b in cks[i + 1:]:
        common = [sc for sc in SCENARIOS if data.get((sc, a)) and data.get((sc, b))]
        if not common:
            continue
        pa = [st.mean([r[0] for r in data[(sc, a)]]) for sc in common]
        pb = [st.mean([r[0] for r in data[(sc, b)]]) for sc in common]
        wins = sum(1 for x, y in zip(pa, pb) if x > y + 0.02)
        loss = sum(1 for x, y in zip(pa, pb) if y > x + 0.02)
        print(f"  {SHORT[a]:<4} vs {SHORT[b]:<4} shared={len(common):>2}  "
              f"mean {st.mean(pa):.4f} vs {st.mean(pb):.4f}  (Δ{st.mean(pa)-st.mean(pb):+.4f})  "
              f"win/loss={wins}/{loss}")

# ---------------- hold vs tail, per scenario, on the common core ----------------
print()
print("=== IE-01 / IE-08 detail (the two scenarios that decide the choice) ===")
for sc in ("IE-01-SINGLE-TARGET", "IE-08-ISLAND-STRIKE"):
    print(f"\n  {sc}")
    for ck, lab in SHORT.items():
        rs = data.get((sc, ck), [])
        if not rs:
            print(f"    {lab:<4} (no data)")
            continue
        tail = [r for r in rs if r[2] >= TAIL_MIN_TICKS]
        hold = [r for r in rs if r[2] < TAIL_MIN_TICKS]
        hs = f"{len(hold)}/{len(rs)}"
        hmean = f"{st.mean([r[0] for r in hold]):.4f}" if hold else "-"
        tmean = f"{st.mean([r[0] for r in tail]):.4f}" if tail else "-"
        print(f"    {lab:<4} n={len(rs):<2} hold-rate={hs:<5} hold-mean={hmean:<8} tail-mean={tmean}")

"""Quantify the remaining experimental gaps: cost vs value.

For each candidate experiment, report how much of it already exists and what the
missing episodes would cost, using measured s/tick and the scenario tick profile.
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
# the six scenarios the project already identified as discriminating
DISCRIM = ["IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
           "IE-08-ISLAND-STRIKE", "IE-11-DECOY-SCREEN", "IE-13-DEEP-STRIKE"]

spt = {"llm": 2.49, "pure-llm": 1.39, "llm-rl": 2.58, "rule": 0.38, "rl": 0.42}

# tick profile per scenario from history
ticks: dict[str, list[int]] = defaultdict(list)
weights_used: dict[str, set] = defaultdict(set)
di_used: dict[str, set] = defaultdict(set)
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
    t = d.get("ticks_run")
    if isinstance(t, int) and t > 100:
        ticks[sc].append(t)
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    if isinstance(meta, dict):
        tag = meta.get("tag")
        if tag:
            weights_used[sc].add(str(tag))
        di = meta.get("decision_interval")
        if di is not None:
            di_used[sc].add(int(di))


def tk(sc):
    v = ticks.get(sc, [])
    return int(st.median(v)) if v else 1199


print("=== E4: weight-selection matrix (5 weights x 6 discriminating scenarios) ===")
FIVE = ("arm5_llm_reward_v9", "arm5_llm_full_ie03_v10", "arm5_v11", "arm5_v12", "arm5_v13_ie08")
print(f"  {'scenario':<28}{'weights already run':>22}{'missing':>9}")
miss_e4 = 0
for sc in DISCRIM:
    have = {w for w in FIVE if w in weights_used.get(sc, set())}
    missing = [w for w in FIVE if w not in have]
    miss_e4 += len(missing)
    print(f"  {sc:<28}{len(have):>10}/5{'':>11}{len(missing):>9}  {[m.replace('arm5_','') for m in missing]}")
cost_e4 = sum(tk(sc) * spt["llm-rl"] for sc in DISCRIM) * 2  # rough: 2 of 5 missing on avg
print(f"  E4: {miss_e4} episodes missing, ~{sum(tk(sc)*spt['llm-rl'] for sc in DISCRIM)/5*miss_e4/3600:.1f} h serial")

print()
print("=== E5: bandwidth ablation (--decision-interval 1/2/5) ===")
print(f"  {'interval':>9}{'scenarios with data':>22}")
for di in (1, 2, 5):
    n = sum(1 for sc in SCEN if di in di_used.get(sc, set()))
    print(f"  {di:>9}{n:>22}")
miss_e5 = [(sc, di) for sc in DISCRIM for di in (1, 2) if di not in di_used.get(sc, set())]
print(f"  E5: {len(miss_e5)} cells missing "
      f"(~{sum(tk(sc)*spt['llm-rl'] for sc, _ in miss_e5)/3600:.1f} h serial)")

print()
print("=== E7: second LLM endpoint ===")
print("  availability check: only one endpoint is configured (Qwen3.8-27B).")
print("  without a second model this experiment cannot run at all.")

print()
print("=== E8: cost table ===")
print("  pure aggregation of stored fields (llm_calls, total_tokens, total_latency,")
print("  elapsed_seconds, ticks_run) - no episodes needed.")

print()
print("=== E6: doctrine ablation (--rl-overkill-release both sides) ===")
print("  one-sided data exists; the other side needs authorisation (changes method).")

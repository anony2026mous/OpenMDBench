"""Can we now run one complete paper-ready batch? Measure the cost of closing the gaps.

Uses only recorded wall-clock from existing episodes to extrapolate honestly.
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
ARMS = {"rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm"),
        "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl"), "rule-rl": ("rulerl", "rule-rl")}
WANT = {"llm-rl": {"arm5_llm_reward_v9"}, "rl": {"rlb2", "nn1"}, "rule-rl": {"arm5_v12"},
        "llm-rule": set(), "pure-llm": set(), "rule-rule": set()}

seeds: dict[tuple[str, str], set] = defaultdict(set)
wall: dict[str, list[float]] = defaultdict(list)   # arm -> elapsed_seconds
ticks: dict[str, list[int]] = defaultdict(list)
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
    pl = str(d.get("planner", "")).lower()
    arm = next((a for a, ks in ARMS.items() if pl in ks), None)
    if arm is None:
        continue
    ex = (d.get("defender") or {}).get("executor") or {}
    meta = ex.get("checkpoint_meta") or {}
    tag = str(meta.get("tag") or "") if isinstance(meta, dict) else ""
    if WANT.get(arm) and tag and tag not in WANT[arm]:
        continue
    sd = d.get("seed")
    if isinstance(sd, int):
        seeds[(sc, arm)].add(sd)
    el = d.get("elapsed_seconds")
    if isinstance(el, (int, float)) and el > 0:
        wall[arm].append(float(el))
        if isinstance(d.get("ticks_run"), int):
            ticks[arm].append(int(d["ticks_run"]))

print("=== measured wall-clock per episode (from recorded runs) ===")
for a in ARMS:
    if wall.get(a):
        print(f"  {a:<10} n={len(wall[a]):>4}  median={st.median(wall[a]):>8.1f}s  "
              f"mean={st.mean(wall[a]):>8.1f}s  max={max(wall[a]):>9.1f}s  "
              f"median ticks={int(st.median(ticks[a]))}")

print()
print("=== sample gaps to reach n>=3 everywhere (paper standard) ===")
need = []
for sc in SCEN:
    for a in ARMS:
        n = len(seeds.get((sc, a), ()))
        if n < 3:
            need.append((sc, a, n, 3 - n))
total_missing = sum(x[3] for x in need)
print(f"  cells below n=3: {len(need)} / 84")
per_arm = defaultdict(int)
for sc, a, n, k in need:
    per_arm[a] += k
for a in ARMS:
    print(f"    {a:<10} missing {per_arm[a]:>3} episodes")
print(f"  TOTAL missing episodes: {total_missing}")

print()
print("=== subset: only what the 6 inequalities need ===")
# hybrids + their three opponents (rule-rule, rl, pure-llm)
NEEDED = ["llm-rule", "llm-rl", "rule-rule", "rl", "pure-llm"]
sub = [(sc, a, n, k) for sc, a, n, k in need if a in NEEDED]
print(f"  cells: {len(sub)}   episodes: {sum(x[3] for x in sub)}")
pa = defaultdict(int)
for sc, a, n, k in sub:
    pa[a] += k
for a in NEEDED:
    print(f"    {a:<10} missing {pa[a]:>3}")

print()
print("=== predicted wall-clock (median per arm, at 6-way concurrency) ===")
CONC = 6
tot = 0.0
for a in NEEDED:
    k = pa[a]
    if not k:
        continue
    med = st.median(wall[a]) if wall.get(a) else 0.0
    ser = med * k
    tot += ser
    print(f"  {a:<10} {k:>3} eps x {med:>7.1f}s serial = {ser/3600:>5.2f} h  "
          f"at x{CONC} = {ser/CONC/3600:>5.2f} h")
print(f"  {'serial total':<10} {sum(pa.values()):>3} eps"
      f"{'':>22}{tot/3600:>5.2f} h   at x{CONC} = {tot/CONC/3600:.2f} h")

print()
print("=== all-arm version (everything to n>=3) ===")
tot2 = sum((st.median(wall[a]) if wall.get(a) else 0.0) * per_arm[a] for a in ARMS)
print(f"  {total_missing} episodes  serial={tot2/3600:.2f} h   at x{CONC}={tot2/CONC/3600:.2f} h")

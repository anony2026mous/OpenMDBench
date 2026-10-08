"""Which (scenario, arm) cells fall below the verdict sample threshold?

A judgement needs n>=2 on BOTH sides. This lists every scenario where an arm
that must be compared has fewer than 2 seeds - the cells that cannot currently
be judged no matter what the deltas are.
"""
from __future__ import annotations

import json
import os
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
# only the arms that appear in the paper's inequalities matter for judging
JUDGED = {
    "llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl"),
    "rule-rule": ("rule",), "rl": ("rl",), "pure-llm": ("purellm", "pure-llm", "pure_llm"),
}

seeds: dict[tuple[str, str], set[int]] = defaultdict(set)
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
    planner = str(d.get("planner", "")).lower()
    theta = str(d.get("theta_path") or d.get("theta") or "").lower()
    arm = next((a for a, ks in JUDGED.items() if planner in ks), None)
    if arm == "rl" and "llm" in theta:
        arm = "llm-rl"
    if arm is None:
        continue
    sd = d.get("seed")
    if isinstance(sd, int):
        seeds[(sc, arm)].add(sd)

arms = ["rule-rule", "rl", "pure-llm", "llm-rule", "llm-rl"]
print("seed counts per cell (n<2 marked *):")
hdr = f"{'scenario':<26}" + "".join(f"{a:>10}" for a in arms)
print(hdr)
print("-" * len(hdr))
blocked: dict[str, list[str]] = defaultdict(list)
for sc in SCENARIOS:
    row = f"{sc:<26}"
    for a in arms:
        n = len(seeds.get((sc, a), ()))
        row += f"{(str(n) + ('*' if n < 2 else '')):>10}"
        if n < 2:
            blocked[a].append(sc)
    print(row)

print()
print("=== 低于判定门槛（n<2）的方法 ===")
for a in arms:
    lst = blocked.get(a, [])
    print(f"  {a:<10} {len(lst):>2}/14 场景无法判定: {', '.join(s.replace('IE-','') for s in lst) if lst else '(none)'}")

print()
print("=== 论文 6 条不等式中会因此判不了的 ===")
# llm-rule and llm-rl are the two hybrids; they must beat rule-rule, rl, pure-llm
for hybrid in ("llm-rule", "llm-rl"):
    print(f"\n  {hybrid}:")
    for sc in SCENARIOS:
        nh = len(seeds.get((sc, hybrid), ()))
        bad = []
        for opp in ("rule-rule", "rl", "pure-llm"):
            no = len(seeds.get((sc, opp), ()))
            if nh < 2 or no < 2:
                bad.append(f"{opp}(n={no if no < 2 else 'ok'})" if nh >= 2 else f"{opp}")
        if nh < 2:
            print(f"    {sc:<26} 本臂 n={nh}  -> 3 条不等式全部证据不足")
        else:
            thin = [o for o in ("rule-rule", "rl", "pure-llm") if len(seeds.get((sc, o), ())) < 2]
            if thin:
                print(f"    {sc:<26} 本臂 n={nh}，但对手 {', '.join(thin)} n<2")

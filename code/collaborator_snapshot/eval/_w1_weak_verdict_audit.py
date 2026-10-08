"""Quantify the real sample gap: verdicts decided from a single episode on one side.

The verdict rule is: |delta| < 0.05 with n<2 on either side -> 证据不足.
Anything with a larger delta is still judged 通过/未过 - even when one side is n=1.
This lists those, because they are the paper's weakest links.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
TABLE = r"C:\Code\source-code\openmd\code\eval\LLMRL_CLAIM_TABLE.md"

SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}
JUDGED = {"llm-rule": ("llm",), "llm-rl": ("llmrl", "llm-rl"),
          "rule-rule": ("rule",), "rl": ("rl",),
          "pure-llm": ("purellm", "pure-llm", "pure_llm")}

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
    sc = ALIAS.get(str(d.get("scenario", "")).upper().strip(), str(d.get("scenario", "")).upper().strip())
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

# parse the claim table into (scenario, arm, opponent, verdict, delta)
rows: list[tuple[str, str, str, str, float]] = []
scen = None
for line in open(TABLE, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("## "):
        scen = line[3:].strip()
        continue
    m = re.match(r"\* .([\w-]+).：\s*(.*)", line)
    if not m or not scen or scen == "汇总":
        continue
    arm = m.group(1)
    for opp, st, delta in re.findall(
            r"vs .([\w-]+). \*\*(\S+?)\*\*（Δ([+-][\d.]+)）", m.group(2)):
        rows.append((scen, arm, opp, st, float(delta)))

print("=== verdicts decided while one side has n=1 ===")
risky = []
for sc, arm, opp, st, delta in rows:
    n_a = len(seeds.get((sc, arm), ()))
    n_o = len(seeds.get((sc, opp), ()))
    if st in ("通过", "未过") and (n_a < 2 or n_o < 2):
        risky.append((sc, arm, opp, st, delta, n_a, n_o))

print(f"total: {len(risky)} of {len(rows)} inequalities\n")
for sc, arm, opp, st, delta, na, no in risky:
    flag = "  <== both sides thin" if (na < 2 and no < 2) else ""
    print(f"  {sc:<28} {arm:<9} vs {opp:<10} {st:<4} Δ{delta:+.4f}  n[{arm}]={na} n[{opp}]={no}{flag}")

print()
print("=== per-scenario count of such weak verdicts ===")
per = defaultdict(int)
for sc, *_ in risky:
    per[sc] += 1
for sc in SCENARIOS:
    if per[sc]:
        print(f"  {sc:<28} {per[sc]} 条")

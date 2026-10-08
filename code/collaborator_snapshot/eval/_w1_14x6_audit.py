"""Coverage audit: 14 scenarios x 6 arms, from the actual result JSONs on disk.

Read-only. Reports which (scenario, arm) cells have runs, per-seed counts, and
which scenarios/arms are thin or missing - so "did the cleanup lose anything"
is answered from data rather than memory.
"""
from __future__ import annotations

import json
import os
import re
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

# arm -> how the report identifies it
ARM_KEYS = {
    "rule-rule": ("rule",),
    "rl":       ("rl",),
    "pure-llm": ("purellm", "pure-llm", "pure_llm"),
    "llm-rule": ("llm",),
    "llm-rl":   ("llmrl", "llm-rl"),
    "rule-rl":  ("rulerl", "rule-rl"),
}


def norm_scen(s: str) -> str:
    s = (s or "").upper().strip()
    return ALIAS.get(s, s)


cells: dict[tuple[str, str], list[tuple[int, str, float | None]]] = defaultdict(list)
unparsed = 0
for fn in os.listdir(RUNS):
    if not fn.endswith(".json"):
        continue
    fp = os.path.join(RUNS, fn)
    try:
        with open(fp, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        unparsed += 1
        continue
    if not isinstance(data, dict):
        continue
    scen = norm_scen(str(data.get("scenario", "")))
    if scen not in SCENARIOS:
        continue
    seed = data.get("seed")
    planner = str(data.get("planner", "")).lower()
    # arm from planner + theta tag
    theta = str(data.get("theta_path") or data.get("theta") or "").lower()
    tag = str(data.get("tag") or "")
    arm = None
    for name, keys in ARM_KEYS.items():
        if planner in keys:
            arm = name
            break
    if arm == "rl" and "llm" in theta:
        arm = "llm-rl"
    if arm is None:
        continue
    score = None
    if isinstance(data.get("score_state"), dict):
        score = data["score_state"].get("score.facility-integrity")
    cells[(scen, arm)].append((seed if isinstance(seed, int) else -1, tag, score))

print(f"episode JSONs parsed into cells; unparsed files: {unparsed}")
print(f"total (scenario,arm) cells with data: {len(cells)} / {len(SCENARIOS) * 6}")
print()

arms = ["rule-rule", "rl", "pure-llm", "llm-rule", "llm-rl", "rule-rl"]
hdr = f"{'scenario':<26}" + "".join(f"{a:>10}" for a in arms)
print(hdr)
print("-" * len(hdr))
gap_cells = []
for sc in SCENARIOS:
    row = f"{sc:<26}"
    for a in arms:
        n = len(cells.get((sc, a), []))
        seeds = len({s for s, _, _ in cells.get((sc, a), [])})
        txt = "-" if n == 0 else f"{n}({seeds}s)"
        if n == 0:
            gap_cells.append((sc, a))
        row += f"{txt:>10}"
    print(row)

print()
print("=== scenarios with NO data at all ===")
for sc in SCENARIOS:
    tot = sum(len(cells.get((sc, a), [])) for a in arms)
    if tot == 0:
        print(f"  {sc}")

print()
print("=== arms missing on any scenario ===")
for a in arms:
    miss = [sc for sc in SCENARIOS if not cells.get((sc, a))]
    print(f"  {a:<10} missing on {len(miss):>2}/14: {', '.join(m[:6] for m in miss) if miss else '(none)'}")

print()
print("=== per-arm totals ===")
for a in arms:
    n = sum(len(cells.get((sc, a), [])) for sc in SCENARIOS)
    seeds = len({s for sc in SCENARIOS for s, _, _ in cells.get((sc, a), [])})
    print(f"  {a:<10} runs={n:>4}  distinct seeds={seeds}")

print()
print(f"=== total episode records: {sum(len(v) for v in cells.values())} ===")

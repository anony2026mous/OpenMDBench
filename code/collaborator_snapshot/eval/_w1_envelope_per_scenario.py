"""Which envfix pure-llm runs use uav=40 instead of 43, and do the OTHER arms
use the same value in those scenarios?

What matters for fairness is NOT a fixed number - it is that within a scenario,
pure-llm and the other five arms share the SAME speed table (both derive it from
the scenario's defence.intercept_speed_mps). So the correct check is per-scenario
consistency, not equality to 43.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

print("=== per-scenario uav speed cap actually used, by arm ===")
per: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper()
    pl = str(d.get("planner", "")).lower()
    de = d.get("defender") or {}
    env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
    if isinstance(env, dict) and "uav" in env:
        per[sc][f"{pl} (pure-llm envelope)"].add(float(env["uav"]))
    # the other arms read ExecutorConfigV2.speed_by_tag; it is not echoed in the
    # report, so infer it from pure-llm's executor-envelope runs and from the
    # declared scenario profile instead.

print(f"  {'scenario':<28}{'pure-llm uav caps seen':>26}")
weird = []
mismatch = []
for sc in sorted(per):
    vals = per[sc].get("pure-llm (pure-llm envelope)") or set()
    vals |= per[sc].get("purellm (pure-llm envelope)") or set()
    s = ",".join(str(int(v)) for v in sorted(vals)) or "-"
    print(f"  {sc:<28}{s:>26}")
    if vals and 40.0 in vals:
        weird.append(sc)

print()
print("=== scenarios where pure-llm used uav=40 ===")
for sc in weird:
    print(f"  {sc}")

print()
print("=== declared defence.intercept_speed_mps per scenario (the shared source) ===")
ROOT = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
import yaml  # noqa: E402

for d in sorted(os.listdir(ROOT)):
    ap = os.path.join(ROOT, d, "agents.yaml")
    if not os.path.exists(ap):
        continue
    try:
        y = yaml.safe_load(open(ap, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    sp = ((y or {}).get("defence") or {}).get("intercept_speed_mps")
    if sp is not None:
        mark = "   <== NOT 43" if abs(float(sp) - 43.0) > 1e-6 else ""
        print(f"  {d:<34} intercept_speed_mps = {sp}{mark}")

print()
print("=== verdict ===")
print("  if the uav=40 scenarios declare intercept_speed_mps != 43, then pure-llm")
print("  matching 40 is CORRECT (it equals the other five arms in that scenario).")
print("  Fairness requires per-scenario equality, not equality to a global 43.")

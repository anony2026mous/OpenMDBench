"""Existing pure-llm runs: which envelope were they produced under?

The report does not record the envelope, so this checks whether the old runs can
be told apart at all - needed to know how much data the default change invalidates.
"""
from __future__ import annotations

import json
import os
from collections import Counter

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
keys = Counter()
n = 0
samples = []
for fn in sorted(os.listdir(RUNS)):
    if not fn.endswith(".json") or fn.startswith("_"):
        continue
    try:
        d = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    if str(d.get("planner", "")).lower() not in ("pure-llm", "purellm", "pure_llm"):
        continue
    n += 1
    for k in d:
        keys[k] += 1
    de = d.get("defender") or {}
    if isinstance(de, dict):
        for k in de:
            keys["defender." + k] += 1
    if len(samples) < 2:
        samples.append((fn, d))

print(f"pure-llm episodes found: {n}")
print()
print("=== which keys could carry an envelope/speed record? ===")
for k, v in sorted(keys.items()):
    if any(t in k.lower() for t in ("speed", "envelope", "max", "limit", "tag")):
        print(f"  {v:>4} runs have key: {k}")
print()
print("=== full key set of one pure-llm report ===")
if samples:
    fn, d = samples[0]
    print(" file:", fn)
    print(" top-level:", sorted(d.keys()))
    de = d.get("defender") or {}
    print(" defender :", sorted(de.keys()) if isinstance(de, dict) else type(de))
    print()
    print(" defender block (truncated):")
    print(json.dumps(de, ensure_ascii=False)[:1200])

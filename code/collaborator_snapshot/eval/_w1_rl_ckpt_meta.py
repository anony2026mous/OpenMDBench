"""Print the provenance metadata stored inside every RL checkpoint.

The method document claims, for the two layered RL methods, that "RL training targets
may come from the rule planner or the LLM planner depending on the training
configuration".  That claim is only true if the checkpoints actually DIFFER in
`goal_features`, so read the field rather than assuming it.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np

RL_DIR = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs\rl")

KEYS = ("decision_interval", "goal_features", "obs_dim", "speed_source",
        "num_units", "provenance", "tag", "reward", "goal_source")

def read_meta(path: Path) -> dict:
    """`_meta` is stored as a JSON STRING, not a 0-d object array."""
    import json
    try:
        d = np.load(path, allow_pickle=True)
    except Exception:  # noqa: BLE001
        return {}
    for key in ("_meta", "meta"):
        if key in d.files:
            raw = d[key]
            if hasattr(raw, "item") and getattr(raw, "shape", None) == ():
                raw = raw.item()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except Exception:  # noqa: BLE001
                    return {"_raw": raw[:400]}
            if isinstance(raw, dict):
                return raw
    return {}


print(f"  {'checkpoint':<34}" + "".join(f"{k:>17}" for k in KEYS))
print("  " + "-" * (34 + 17 * len(KEYS)))
for p in sorted(RL_DIR.glob("*.npz")):
    meta = read_meta(p)
    row = f"  {p.name:<34}"
    for k in KEYS:
        row += f"{str(meta.get(k, '-')):>17}"
    print(row)

print("\n  full metadata of the checkpoints actually used in the experiments:")
for name in ("theta_rl_legacy2.npz", "theta_arm5_llm_reward_v9.npz"):
    p = RL_DIR / name
    if not p.exists():
        print(f"    {name}: MISSING")
        continue
    meta = read_meta(p)
    print(f"\n    {name}")
    for k, v in sorted(meta.items()):
        print(f"      {k:<20} {str(v)[:200]}")


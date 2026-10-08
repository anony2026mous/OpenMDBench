"""Print the resolved dynamics resources of MD-AD-006 side by side.

Usage:
    python _w1_dynamics_probe.py [PUBLIC_ID]

The three surface hulls are all retargeted from the same source resource, so a
comparison table makes an accidental inconsistency (a missing parameter, a
mismatched platform type, a stale model ref) obvious.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)

BUNDLE = ROOT / "catalog" / "v2" / "md_ad_006.yaml"
payload = yaml.safe_load(BUNDLE.read_text(encoding="utf-8"))

WANTED = ("dynamics.armed-usv", "dynamics.suicide-usv", "dynamics.civilian-ship",
          "dynamics.picket-usv")
rows = {}
for resource in payload["resources"]:
    if resource.get("resource_type") != "dynamics":
        continue
    if resource["id"] in WANTED:
        rows[resource["id"]] = resource

print(f"bundle = {BUNDLE}")
print(f"dynamics resources present: {sorted(rows)}\n")

keys = sorted({key for item in rows.values() for key in (item.get("content") or {})})
width = max(len(key) for key in keys) + 2
header = "parameter".ljust(width) + "".join(name.ljust(20) for name in sorted(rows))
print(header)
print("-" * len(header))
for key in keys:
    line = key.ljust(width)
    for name in sorted(rows):
        value = (rows[name].get("content") or {}).get(key)
        line += json.dumps(value, ensure_ascii=False)[:19].ljust(20)
    print(line)

print("\n=== non-content fields ===")
for name in sorted(rows):
    item = rows[name]
    print(f"{name}: model_id={item.get('model_id')} "
          f"engine_compatibility={item.get('engine_compatibility')} "
          f"dependencies={item.get('dependencies')}")

# The same comparison against the source bundle the retargets come from.
SRC = ROOT / "catalog" / "v2" / "md_ad_002.yaml"
if SRC.exists():
    src = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    for resource in src["resources"]:
        if resource.get("id") == "dynamics.picket-usv":
            print("\n=== source dynamics.picket-usv@2.0.0 ===")
            print(json.dumps(resource, ensure_ascii=False, indent=2))

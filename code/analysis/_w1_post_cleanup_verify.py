"""Verify the engine still loads everything after the registry/rename work.

Read-only. Compiles every public_id the current registry declares, then compiles
the legacy MD ids directly to check they are still reachable.
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openmdbench.scenarios.formal_v2 import (  # noqa: E402
    compile_formal_scenario_v2,
    formal_scenario_registry_v2,
)

registry = formal_scenario_registry_v2()
print(f"registry entries: {len(registry)}")
for pid in registry:
    print(f"  {pid}  ->  {registry[pid].package_root.name}")

print()
print("=== compile every registry entry ===")
ok = fail = 0
for pid in sorted(registry):
    try:
        resolved, _cat = compile_formal_scenario_v2(pid)
        print(f"  [ ok ] {pid:<34} {resolved.resolved_hash[:22]}...  entities={len(resolved.entities)}")
        ok += 1
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] {pid:<34} {type(exc).__name__}: {exc}")
        fail += 1

print()
print("=== legacy MD ids still reachable (not via registry)? ===")
for pid in ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD",
            "MD-INT-003-EASY", "MD-INT-003-MEDIUM", "MD-INT-003-HARD",
            "MD-AD-004-DECEPTION", "MD-INT-002-AIR-SURFACE",
            "MD-INT-005-STEALTH-MULTI-AXIS", "MD-INT-006-SATURATION-ROE",
            "MD-AD-006-ISLAND-STRIKE"):
    try:
        resolved, _cat = compile_formal_scenario_v2(pid)
        print(f"  [ ok ] {pid:<34} {resolved.resolved_hash[:22]}...")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] {pid:<34} {type(exc).__name__}: {str(exc)[:90]}")

print()
print(f"registry compile: ok={ok} fail={fail}")

# the package directories actually present
root = os.environ.get("OPENMDBENCH_ROOT") or ""
formal = os.path.join(root, "scenarios", "formal")
if os.path.isdir(formal):
    dirs = sorted(d for d in os.listdir(formal) if os.path.isdir(os.path.join(formal, d)))
    print(f"package dirs on disk: {len(dirs)}")

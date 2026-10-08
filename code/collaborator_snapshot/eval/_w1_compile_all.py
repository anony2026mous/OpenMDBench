"""Compile every registered formal V2 scenario.

A cheap regression gate (~seconds): it catches a change that compiles for the
scenario under development but breaks another package — for example a new
faction requirement, a stricter cross-reference check, or a shared prompt/catalog
edit.  It builds no session, so no MMG child process is involved.

Usage:
    python _w1_compile_all.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))


def main() -> int:
    from openmdbench.scenarios.formal_v2 import (
        compile_formal_scenario_v2,
        formal_scenario_registry_v2,
    )

    public_ids = sorted(formal_scenario_registry_v2())
    print(f"engine root = {ROOT}")
    print(f"registered scenarios = {len(public_ids)}\n")

    failures = 0
    for public_id in public_ids:
        try:
            resolved, _catalog = compile_formal_scenario_v2(public_id)
            spawns = sum(1 for event in resolved.events
                         if getattr(event, "event_type", "") == "spawn")
            slots = tuple(getattr(resolved, "controller_slots", ()) or ())
            missing_endpoint = [
                slot.id for slot in slots
                if not (slot.values or {}).get("controller_endpoint_ref")
            ]
            print(f"  [ok  ] {public_id:<34} entities={len(resolved.entities):<3} "
                  f"spawns={spawns:<3} slots={len(slots):<3} "
                  f"endpoints_missing={len(missing_endpoint)}")
            if missing_endpoint:
                failures += 1
                print(f"         slots without an endpoint: {','.join(missing_endpoint)}")
        except Exception as error:  # noqa: BLE001 - the point is to report it
            failures += 1
            print(f"  [FAIL] {public_id:<34} {type(error).__name__}: {error}")

    print(f"\n  {len(public_ids) - failures}/{len(public_ids)} scenarios compile")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

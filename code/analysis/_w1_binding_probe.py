"""Does the resolved scenario expose weapon bindings for spawned (event) entities?

`CombatSystemV2` builds its weapon-profile map exclusively from
`resolved.entities[*].resource_bindings`.  MD-AD-006's entire intruder force is
created by ``event_type: spawn`` blueprints, so this probe compares:

  * weapon/ammunition bindings reachable from ``resolved.entities``
  * weapon/ammunition bindings reachable from spawn-event blueprints
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def weapon_refs(entity) -> list[str]:
    bindings = getattr(entity, "resource_bindings", None) or {}
    out = []
    for group, items in bindings.items():
        for item in items:
            if getattr(item, "resource_type", "") in {"weapons", "ammunition"}:
                out.append(f"{group}:{item.exact_ref}")
    return sorted(out)


def main() -> int:
    resolved, _catalog = compile_formal_scenario_v2(PUBLIC_ID)

    print("=== resolved top-level fields ===")
    for name in sorted(getattr(type(resolved), "__slots__", ()) or ()):
        value = getattr(resolved, name, None)
        if isinstance(value, (tuple, list)):
            print(f"  {name}: {type(value).__name__}[{len(value)}]")
        else:
            print(f"  {name}: {type(value).__name__}")

    print(f"\n=== resolved.entities ({len(resolved.entities)}) ===")
    static_refs: set[str] = set()
    for entity in sorted(resolved.entities, key=lambda e: e.id):
        refs = weapon_refs(entity)
        static_refs.update(refs)
        print(f"  {entity.id:<34} {entity.faction_id:<20} {refs}")

    print("\n=== spawn events ===")
    spawn_refs: set[str] = set()
    events = list(getattr(resolved, "events", ()))
    for event in events:
        if getattr(event, "event_type", "") != "spawn":
            continue
        blueprint = getattr(event, "blueprint", None)
        entities = list(getattr(blueprint, "entities", ()) or ())
        for item in entities:
            refs = weapon_refs(item)
            spawn_refs.update(refs)
            print(f"  {str(getattr(item, 'id', '?')):<34} "
                  f"{str(getattr(item, 'faction_id', '?')):<20} {refs}")

    print("\n=== combat profile coverage (what CombatSystemV2 would register) ===")
    print(f"  from resolved.entities : {sorted(r for r in static_refs if ':weapon' in r)}")
    print(f"  only from spawn events : "
          f"{sorted(r for r in (spawn_refs - static_refs) if ':weapon' in r)}")
    print(f"  MISSING from profiles  : "
          f"{sorted(r.split(':', 1)[1] for r in (spawn_refs - static_refs) if ':weapon' in r)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

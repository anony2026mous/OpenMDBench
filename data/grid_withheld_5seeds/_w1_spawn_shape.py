"""Inspect how a resolved spawn event carries its entity blueprint."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def describe(label: str, value: object, depth: int = 0) -> None:
    pad = "  " * (depth + 1)
    slots = getattr(type(value), "__slots__", None)
    if slots:
        print(f"{pad}{label}: {type(value).__name__} slots={list(slots)}")
        return
    if isinstance(value, (tuple, list)):
        print(f"{pad}{label}: {type(value).__name__}[{len(value)}]")
        if value:
            describe("[0]", value[0], depth + 1)
        return
    print(f"{pad}{label}: {type(value).__name__} = {str(value)[:110]}")


def main() -> int:
    resolved, _catalog = compile_formal_scenario_v2(PUBLIC_ID)
    for event in resolved.events:
        if str(getattr(event, "event_type", "")) != "spawn":
            continue
        payload = getattr(event, "payload", None)
        values = getattr(payload, "values", None) or {}
        print(f"=== spawn event {getattr(event, 'id', None)} ===")
        print(f"  payload keys: {sorted(values)}")
        entity = values.get("entity")
        print(f"  entity type: {type(entity).__name__}")
        if entity is not None:
            for name in sorted(getattr(type(entity), "__slots__", ()) or ()):
                value = getattr(entity, name, None)
                if isinstance(value, Mapping):
                    print(f"    {name}: Mapping keys={sorted(value)}")
                elif isinstance(value, (tuple, list)):
                    print(f"    {name}: {type(value).__name__}[{len(value)}] "
                          f"{str(value)[:120]}")
                else:
                    print(f"    {name}: {type(value).__name__} = {str(value)[:90]}")
            bindings = getattr(entity, "resource_bindings", None) or {}
            print(f"  resource_bindings groups: {sorted(bindings)}")
            for group, items in bindings.items():
                for item in items:
                    print(f"    {group}: {getattr(item, 'exact_ref', item)}")
        print()
        break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

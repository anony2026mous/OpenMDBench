"""Surface the inner cause of combat.resolved_binding_invalid for MD-AD-006."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def check_bindings() -> None:
    """Which spawn-blueprint bindings disagree with the catalog snapshot?"""
    from openmdbench.combat.system_v2 import CombatCatalogSnapshotV2

    resolved, catalog = compile_formal_scenario_v2(PUBLIC_ID)
    snapshot = CombatCatalogSnapshotV2.from_resolved(resolved)
    catalog_resources = dict(snapshot.resource_evidence)
    print(f"catalog evidence entries: {len(catalog_resources)}")

    checked: set[str] = set()
    for entity in resolved.entities:
        for group, items in entity.resource_bindings.items():
            for binding in items:
                checked.add(binding.exact_ref)

    bad: list[tuple[str, str, object, str]] = []
    for event in resolved.events:
        if str(getattr(event, "event_type", "")) != "spawn":
            continue
        blueprint = getattr(getattr(event, "payload", None), "entity", None)
        if blueprint is None:
            continue
        if blueprint.id in {"defender.uav-01"}:
            continue
        for group, items in blueprint.resource_bindings.items():
            for binding in items:
                expected = catalog_resources.get(binding.exact_ref)
                if expected != binding.content_hash:
                    bad.append((blueprint.id, group, binding.exact_ref,
                                f"snapshot={expected} binding={binding.content_hash}"))
    print(f"spawn-blueprint bindings disagreeing with snapshot: {len(bad)}")
    for item in bad[:25]:
        print(f"  {item[0]:<32} {item[1]:<16} {item[2]}")
        print(f"      {item[3]}")
    # Are these refs known to the snapshot at all?
    print("\nrefs absent from the snapshot entirely:")
    seen = {item[2] for item in bad}
    for ref in sorted(seen):
        print(f"  {ref}")
    # what groups does a spawn blueprint expose?
    for event in resolved.events:
        if str(getattr(event, "event_type", "")) != "spawn":
            continue
        blueprint = getattr(event.payload, "entity", None)
        if blueprint is None:
            continue
        print(f"\nblueprint {blueprint.id} binding groups:")
        for group, items in blueprint.resource_bindings.items():
            refs = [getattr(i, "exact_ref", "?") for i in items]
            print(f"  {group}: {refs}")
        break


def main() -> int:
    check_bindings()
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.combat", seed=7)
    try:
        session.load()
        print("\nload OK")
    except Exception as error:  # noqa: BLE001
        print(f"\nload FAILED: {type(error).__name__}: {error}")
        cause = error.__cause__ or error.__context__
        depth = 0
        while cause is not None and depth < 8:
            print(f"  cause[{depth}] {type(cause).__name__}: {cause}")
            for frame in traceback.extract_tb(cause.__traceback__)[-4:]:
                print(f"      {Path(frame.filename).name}:{frame.lineno}  {frame.line}")
            cause = cause.__cause__ or cause.__context__
            depth += 1
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

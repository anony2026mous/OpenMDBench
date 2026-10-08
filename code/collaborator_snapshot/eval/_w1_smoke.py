"""Cross-platform read-only smoke test for a formal V2 scenario.

Windows port of `_tmp_md006_check.py`: the engine root is discovered from
`OPENMDBENCH_ROOT` (or defaults to the sibling `openmd/source-code/source_codes`
checkout) instead of the Linux-only `/root/source_codes_linux/source_codes`.

Usage:
    python _w1_smoke.py [PUBLIC_ID] [--ticks N] [--seed 7]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import (  # noqa: E402
    compile_formal_scenario_v2,
    formal_scenario_registry_v2,
)
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("public_id", nargs="?", default="IE-08-ISLAND-STRIKE")
    parser.add_argument("--ticks", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    print(f"engine root = {ROOT}")

    print("=== registry ===")
    print(f"  {sorted(formal_scenario_registry_v2())}")

    print("\n=== compile ===")
    resolved, catalog = compile_formal_scenario_v2(args.public_id)
    print(f"  resolved_hash = {resolved.resolved_hash[:32]}...")
    print(f"  catalog content_hash = {catalog.content_hash[:32]}...")

    static = list(getattr(resolved, "entities", ()))
    print(f"\n=== static entities ({len(static)}) ===")
    for entity in sorted(static, key=lambda item: item.id):
        print(f"  {entity.id:<24} {entity.faction_id:<20} {entity.platform_ref:<34} "
              f"pos={tuple(round(v) for v in entity.initial_state.position_m)} "
              f"tags={entity.tags} loadout={entity.loadout_ref}")

    events = list(getattr(resolved, "events", ()))
    spawns = [event for event in events if getattr(event, "event_type", "") == "spawn"]
    print(f"\n=== events: {len(events)} total, {len(spawns)} spawns ===")
    for event in spawns:
        blueprint = getattr(event, "blueprint", None)
        entities = list(getattr(blueprint, "entities", ()) or ())
        ids = ",".join(str(getattr(item, "id", "?")) for item in entities) or "?"
        print(f"  tick={getattr(event, 'tick', '?'):>5} spawn -> {ids}")

    if args.ticks <= 0:
        return 0

    print(f"\n=== {args.ticks} ticks ===")
    session = create_formal_session_v2(args.public_id, session_id="audit.smoke",
                                       seed=args.seed)
    session.load().start()
    receipt = None
    for _ in range(args.ticks):
        receipt = session.step(
            operation_id=f"audit.smoke.{session.world_view.tick:08d}",
            expected_tick=session.world_view.tick)
    live = session.world_view.entities_stable()
    print(f"  tick = {session.world_view.tick}, live entities = {len(live)}")
    print(f"  by faction = {dict(Counter(e.faction_id for e in live))}")
    for entity in sorted(live, key=lambda item: item.id):
        print(f"    {entity.id:<24} {entity.faction_id:<20} "
              f"lifecycle={entity.state.lifecycle} health={entity.state.health} "
              f"pos={tuple(round(v) for v in entity.state.position_m)}")
    scores = getattr(getattr(receipt, "world_receipt", None), "score_receipts", ()) or ()
    for score in scores[:1]:
        dump = (score.model_dump(mode="json") if hasattr(score, "model_dump")
                else {k: getattr(score, k) for k in dir(score) if not k.startswith("_")})
        print(f"  score receipt = {dump}")
    session.stop()
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

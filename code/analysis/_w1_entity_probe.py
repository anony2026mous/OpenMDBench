"""Is a disabled facility still present as a World entity?

Prints, at the end of a short run, the ids in ``entities_stable()`` versus the
ids the missile resolver can see, so we can tell whether ``target_unavailable``
comes from the entity being removed or from its motion position being absent.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_episode as R  # noqa: E402
from attack_driver import AttackProfileDriverV2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=600)
    args = parser.parse_args()

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.entity", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)

    previous = {}
    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack(session)
        defender(session)
        try:
            session.step(operation_id=f"audit.entity.{tick:08d}", expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            print(f"[STOPPED] tick {tick}: {type(error).__name__}: {error}")
            break
        current = {e.id: str(e.state.lifecycle)
                   for e in session.world_view.entities_stable()}
        for entity_id, state in current.items():
            if previous.get(entity_id) not in (None, state):
                print(f"[tick {tick:>4}] {entity_id}: {previous[entity_id]} -> {state}")
        for entity_id in set(previous) - set(current):
            print(f"[tick {tick:>4}] {entity_id}: {previous[entity_id]} -> GONE from "
                  f"entities_stable()")
        previous = current

    live = {e.id: str(e.state.lifecycle) for e in session.world_view.entities_stable()}
    print("\n--- facilities in entities_stable() ---")
    for entity_id in sorted(live):
        if entity_id.startswith("facility."):
            print(f"  {entity_id:<20} {live[entity_id]}")
    print("\n--- world internals ---")
    world = getattr(session, "_world", None) or getattr(session, "world", None)
    view = session.world_view
    for label, obj in (("session._world", world), ("world_view", view)):
        if obj is None:
            print(f"  {label}: <none>")
            continue
        entities = getattr(obj, "_entities", None)
        if isinstance(entities, dict):
            print(f"  {label}._entities: {len(entities)} ids; facility.command "
                  f"present={('facility.command' in entities)}")

    try:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

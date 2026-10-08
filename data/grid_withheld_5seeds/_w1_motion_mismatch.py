"""Find which dynamics entity lacks a matching command in MD-AD-006.

The pristine engine raises ``World tick requires exactly one current command
per active dynamics entity`` when the command set produced by the action
pipeline differs from the world's post-lifecycle active-dynamics set.  This
probe monkey-patches the check at runtime (no engine edit) and prints both sets
for the failing tick.
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

import openmdbench.world.factory_v2 as factory  # noqa: E402
import run_episode as R  # noqa: E402
from attack_driver import AttackProfileDriverV2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def patch() -> None:
    for name in dir(factory):
        candidate = getattr(factory, name)
        if isinstance(candidate, type) and "_invoke_motion_provider" in vars(candidate):
            original = vars(candidate)["_invoke_motion_provider"]

            def wrapper(self, *, tick_input, step_tick, expected_entity_ids):
                provided = {item.entity_id for item in tick_input.entity_commands}
                expected = set(expected_entity_ids)
                if provided != expected:
                    missing = sorted(expected - provided)
                    extra = sorted(provided - expected)
                    print(f"\n[MISMATCH] tick={tick_input.expected_tick} "
                          f"step_tick={step_tick}")
                    print(f"  expected (world, post-lifecycle) = {sorted(expected)}")
                    print(f"  provided (action pipeline)       = {sorted(provided)}")
                    print(f"  MISSING commands for : {missing}")
                    print(f"  EXTRA commands for   : {extra}")
                    for entity_id in missing + extra:
                        entity = self._entities.get(entity_id)
                        if entity is None:
                            print(f"    {entity_id}: <not in world>")
                            continue
                        print(f"    {entity_id}: faction={entity.faction_id} "
                              f"lifecycle={entity.state.lifecycle} "
                              f"dynamics={entity.definition.composition.dynamics_ref}")
                    lifecycles = {}
                    for entity_id, entity in self._entities.items():
                        if entity.definition.composition.dynamics_ref is not None:
                            lifecycles[entity_id] = str(entity.state.lifecycle)
                    print(f"  world dynamics lifecycles: "
                          f"{dict(sorted(lifecycles.items()))}")
                return original(self, tick_input=tick_input, step_tick=step_tick,
                                expected_entity_ids=expected_entity_ids)

            setattr(candidate, "_invoke_motion_provider", wrapper)
            print(f"patched {name}._invoke_motion_provider")
            return
    raise SystemExit("could not locate _invoke_motion_provider")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=200)
    args = parser.parse_args()
    patch()

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.motion", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)
    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack(session)
        defender(session)
        try:
            session.step(operation_id=f"audit.motion.{tick:08d}", expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            print(f"\nSTOPPED at tick {tick}: {type(error).__name__}: {error}")
            break
    else:
        print(f"\ncompleted {args.ticks} ticks without a motion mismatch")
    try:
        session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

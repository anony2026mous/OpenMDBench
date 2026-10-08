"""Ask the rule planner directly what goal each blue unit gets at a given tick."""
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
    parser.add_argument("--at", type=int, default=110)
    args = parser.parse_args()

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.plan", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)

    for _ in range(args.at):
        tick = session.world_view.tick
        attack(session)
        defender(session)
        session.step(operation_id=f"audit.plan.{tick:08d}", expected_tick=tick)

    tick = session.world_view.tick
    observation = session.world_view.observation(
        observer_faction_id=defender.faction_id)
    mobile = set(defender._mobile_unit_ids()) if hasattr(defender, "_mobile_unit_ids") else None
    if mobile:
        observation = observation.model_copy(update={
            "own_entities": tuple(item for item in observation.own_entities
                                  if str(item["entity_id"]) in mobile)})
    meta = defender._meta
    goals = defender.planner.plan(observation, tick, [], defender._unit_roles, meta=meta)

    print(f"tick={tick}  goals={len(goals)}")
    print(f"{'unit':<26} {'goal':<10} {'target/position':<44} params")
    for goal in sorted(goals, key=lambda g: str(g.parameters.get("unit_id"))):
        unit = str(goal.parameters.get("unit_id"))
        detail = goal.parameters.get("target_id") or goal.parameters.get("position")
        print(f"{unit:<26} {goal.goal_type:<10} {str(detail):<44} "
              f"{ {k: v for k, v in goal.parameters.items() if k not in {'unit_id','target_id','position'}} }")

    print("\ncontacts the defender holds, by observable class:")
    own_ids = {str(item["entity_id"]) for item in observation.own_entities}
    domains_uav = defender.planner._target_domains(meta, "defender.uav-01")
    counts = {}
    for contact in observation.contacts_by_faction.get(defender.faction_id, ()):
        observer = str(contact.get("observer_entity_id") or "")
        position = contact.get("estimated_position_m") or (0.0, 0.0, 0.0)
        is_air = float(position[2]) > defender.planner.config.air_altitude_threshold_m
        allowed = defender.planner._contact_allowed(contact, domains_uav)
        key = (observer in own_ids, "air" if is_air else "surface", allowed)
        counts[key] = counts.get(key, 0) + 1
    print(f"  (allowed = 对空武器单位 uav-01 是否可交战，domains={domains_uav})")
    for key, value in sorted(counts.items(), key=lambda item: str(item[0])):
        print(f"  self_owned={key[0]!s:<5} class={key[1]:<8} allowed={key[2]!s:<5} x{value}")

    for unit_id in ("defender.uav-05", "defender.uav-08"):
        print(f"\n{unit_id}: weapon target domains = "
              f"{defender.planner._target_domains(meta, unit_id)}")
    try:
        session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Trace two specific blue UAVs up to their collision, with assigned goals."""
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
    parser.add_argument("--ticks", type=int, default=80)
    parser.add_argument("--watch", default="defender.uav-05,defender.uav-08")
    args = parser.parse_args()
    watched = [w.strip() for w in args.watch.split(",") if w.strip()]

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.trace", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)

    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack(session)
        result = defender(session)
        goals = (result.get("submit_result") or {}).get("accepted") or []
        try:
            session.step(operation_id=f"audit.trace.{tick:08d}", expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            print(f"\nSTOPPED at tick {tick}: {type(error).__name__}: {error}")
            break
        if tick % 5 == 0 or tick >= args.ticks - 8:
            parts = []
            for entity_id in watched:
                entity = next((e for e in session.world_view.entities_stable()
                               if e.id == entity_id), None)
                if entity is None:
                    parts.append(f"{entity_id}=<gone>")
                    continue
                position = tuple(round(float(v), 1) for v in entity.state.position_m)
                velocity = tuple(round(float(v), 1) for v in entity.state.velocity_mps)
                parts.append(f"{entity_id} pos={position} vel={velocity} "
                             f"hdg={round(float(entity.state.heading_deg), 1)} "
                             f"{entity.state.lifecycle} h={round(float(entity.state.health), 3)}")
            print(f"[tick {tick:>4}] " + " | ".join(parts))
        if goals and tick < 40:
            print(f"          goals@{tick}: {goals}")
    try:
        session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

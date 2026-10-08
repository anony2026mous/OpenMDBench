"""Why do blue UAVs become disabled before any engagement?

Logs, per tick, every lifecycle transition and every damage receipt with its
effect/attacker evidence, so the cause of early disablement is explicit rather
than inferred.  Read-only diagnostics; the engine is untouched.
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


def plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=120)
    args = parser.parse_args()

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.life", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)

    previous = {e.id: str(e.state.lifecycle)
                for e in session.world_view.entities_stable()}
    previous_health = {e.id: float(e.state.health)
                       for e in session.world_view.entities_stable()}
    previous_energy = {e.id: e.state.energy
                       for e in session.world_view.entities_stable()}

    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack(session)
        defender(session)
        try:
            receipt = session.step(operation_id=f"audit.life.{tick:08d}",
                                   expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            print(f"\nSTOPPED at tick {tick}: {type(error).__name__}: {error}")
            break
        world = receipt.world_receipt

        current = {e.id: str(e.state.lifecycle)
                   for e in session.world_view.entities_stable()}
        for entity_id, state in current.items():
            if previous.get(entity_id) != state:
                entity = next(e for e in session.world_view.entities_stable()
                              if e.id == entity_id)
                print(f"[tick {tick:>4}] LIFECYCLE {entity_id}: "
                      f"{previous.get(entity_id)} -> {state} "
                      f"(health {previous_health.get(entity_id)} -> "
                      f"{round(float(entity.state.health), 3)}, "
                      f"energy {previous_energy.get(entity_id)} -> "
                      f"{entity.state.energy})")

        for damage in getattr(world, "damage_receipts", ()) or ():
            dump = plain(damage)
            intents = dump.get("intents") or dump.get("applied_intents") or []
            if not intents:
                continue
            for intent in intents:
                if float(intent.get("magnitude", 0.0)) <= 0.0:
                    continue
                print(f"[tick {tick:>4}] DAMAGE target={intent.get('target_id')} "
                      f"magnitude={intent.get('magnitude')} "
                      f"source={intent.get('source') or intent.get('cause') or intent.get('effect_ref')} "
                      f"attacker={intent.get('attacker_id')}")

        previous = current
        previous_health = {e.id: float(e.state.health)
                           for e in session.world_view.entities_stable()}
        previous_energy = {e.id: e.state.energy
                           for e in session.world_view.entities_stable()}

    try:
        session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

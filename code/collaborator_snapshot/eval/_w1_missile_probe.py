"""Why do red's guided missiles miss the island facilities?

Dumps ``MissileTerminalReceiptV2`` for every shot aimed at a facility, showing
the terminal status (hit / fuse_miss / expired / target_unavailable) and the
closest approach, so the miss mechanism is measured rather than guessed.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
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
    parser.add_argument("--ticks", type=int, default=1100)
    args = parser.parse_args()

    profile = R.load_attack_profile_data(PUBLIC_ID)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.missile", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(PUBLIC_ID, seed=7)
    defender = R._build_defender(profile, defender_args)
    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack(session)
        defender(session)
        try:
            session.step(operation_id=f"audit.missile.{tick:08d}", expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            print(f"[STOPPED] tick {tick}: {type(error).__name__}: {error}")
            break

    world = session.world_view
    receipts = []
    checkpoint = world.checkpoint()
    receipts = list(getattr(checkpoint, "missile_terminal_receipts", ()) or ())
    if not receipts:
        raw = getattr(world, "_missile_terminal_receipts", None) or {}
        receipts = list(raw.values())
    print(f"missile terminal receipts: {len(receipts)} (from world checkpoint)")

    by_status: Counter = Counter()
    print(f"\n{'missile':<46} {'target':<22} {'status':<18} {'closest_m':>9} "
          f"{'seeker':<10} {'tick':>5}")
    for item in sorted(receipts, key=lambda r: (str(r.target_id), r.tick)):
        by_status[str(item.status)] += 1
        target = str(item.target_id)
        if not target.startswith(("facility", "intruder", "defender")):
            continue
        closest = item.closest_approach_m
        print(f"{str(item.missile_id):<46} {target:<22} {str(item.status):<18} "
              f"{'' if closest is None else round(float(closest), 1)!s:>9} "
              f"{str(item.seeker_state):<10} {int(item.tick):>5}")

    print("\n=== terminal status totals ===")
    for status, count in sorted(by_status.items()):
        print(f"  {status:<20} {count}")

    print("\n=== shots aimed at the 3 island facilities ===")
    island = [r for r in receipts if str(r.target_id).startswith("facility.")
              and not str(r.target_id).endswith("pier")]
    statuses = Counter(str(r.status) for r in island)
    print(f"  total {len(island)}  {dict(sorted(statuses.items()))}")
    for status in ("hit", "fuse_miss", "expired", "target_unavailable"):
        subset = [r for r in island if str(r.status) == status
                  and r.closest_approach_m is not None]
        if subset:
            approaches = sorted(float(r.closest_approach_m) for r in subset)
            print(f"  {status:<18} closest_approach m: min={approaches[0]:.1f} "
                  f"median={approaches[len(approaches) // 2]:.1f} max={approaches[-1]:.1f}")

    try:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

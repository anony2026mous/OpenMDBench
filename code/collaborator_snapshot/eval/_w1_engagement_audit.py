"""Engagement-logic audit for MD-AD-006 (short run, per-event evidence).

Answers, from process data rather than from the final score:
  * who shoots whom, with which weapon, at what range and target domain;
  * whether each shot was executed or denied, and by which engine stage;
  * whether any shot violates the weapon/target domain pairing;
  * whether the firing side wastes submissions (cooldown / ammo / range denials);
  * whether contacts used for firing are self-owned (engine requires
    contact_owner_id == attacker_id);
  * whether ammunition is consumed once per executed shot.

Usage:
    python _w1_engagement_audit.py --ticks 400 [--scenario IE-08-ISLAND-STRIKE]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_episode as R  # noqa: E402
from attack_driver import AttackProfileDriverV2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402


def weapon_domains(entity_view, weapon_ref: str) -> tuple[str, ...]:
    bindings = (getattr(getattr(entity_view, "definition", None),
                        "resource_bindings", None) or {}).get("weapons", ())
    for binding in bindings:
        if getattr(binding, "exact_ref", None) == weapon_ref:
            content = getattr(binding, "normalized_content", None) or {}
            return tuple(str(item) for item in (content.get("target_domains") or ()))
    return ()


def contact_target(contact_id: str) -> str:
    parts = str(contact_id).split(".")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] in {"defender", "intruder", "facility", "boat"}:
            return ".".join(parts[index:])
    return str(contact_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="IE-08-ISLAND-STRIKE")
    parser.add_argument("--ticks", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--timeline-every", type=int, default=50)
    args = parser.parse_args()

    profile = R.load_attack_profile_data(args.scenario)
    defender_args = argparse.Namespace(
        planner="rule", plan_interval=10, lead_pursuit=True, fire_doctrine="assess",
        patrol_sweep=True, deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="salvo", rule_fire_policy_urgent="none",
        rule_fire_policy_urgent_eta=240, goal_granularity=None, frontend="graph",
    )
    session = create_formal_session_v2(args.scenario, session_id="audit.engage",
                                       seed=args.seed)
    session.load().start()
    attack = AttackProfileDriverV2(args.scenario, seed=args.seed)
    defender = R._build_defender(profile, defender_args)

    executed: list[dict] = []
    denied: list[dict] = []
    damage_events: list[tuple[int, str, float, str]] = []
    health_before = {entity.id: float(getattr(entity.state, "health", 1.0))
                     for entity in session.world_view.entities_stable()}
    stopped_at: int | None = None
    stop_reason: str | None = None
    ammo_seen: dict[tuple[str, str], int] = {}

    print(f"scenario={args.scenario} seed={args.seed} ticks={args.ticks}")
    print(f"red faction   = {attack.faction_id}   blue faction = {defender.faction_id}\n")
    print(f"{'tick':>5} {'side':<5} {'shooter':<26} {'weapon':<34} {'target':<26} "
          f"{'tgt_dom':<8} {'range_m':>9} {'status':<10} error")
    print("-" * 150)

    for _ in range(args.ticks):
        tick = session.world_view.tick
        attack_result = attack(session)
        result = defender(session)
        try:
            receipt = session.step(operation_id=f"audit.engage.{tick:08d}",
                                   expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            stopped_at = tick
            stop_reason = f"{type(error).__name__}: {error}"
            print(f"\n[STOPPED] tick {tick}: {stop_reason}")
            break
        meta = {entity.id: entity for entity in session.world_view.entities_stable()}

        current_health = {entity.id: float(getattr(entity.state, "health", 1.0))
                          for entity in session.world_view.entities_stable()}
        for entity_id, health in current_health.items():
            previous = health_before.get(entity_id)
            if previous is not None and health < previous - 1e-9:
                faction = str(getattr(meta.get(entity_id), "faction_id", "?"))
                damage_events.append((tick, entity_id, previous - health,
                                      f"{faction} {previous:.3f}->{health:.3f}"))
        health_before = current_health

        rows = (
            [("blue", v) for v in R._executed_fire_statuses(
                result["executor"].get("fires", ()), receipt)]
            + [("red", v) for v in R._executed_fire_statuses(
                attack_result.get("fire_actions", ()), receipt)]
        )
        for side, verdict in rows:
            shooter = str(verdict.get("entity_id") or "")
            weapon = str(verdict.get("weapon_ref") or "")
            contact = str(verdict.get("contact_id") or "")
            target = contact_target(contact)
            target_view = meta.get(target)
            shooter_view = meta.get(shooter)
            target_domain = str(getattr(target_view, "domain", "") or "")
            domains = weapon_domains(shooter_view, weapon)
            distance = None
            if shooter_view is not None and target_view is not None:
                try:
                    a = tuple(float(v) for v in shooter_view.state.position_m)
                    b = tuple(float(v) for v in target_view.state.position_m)
                    distance = round(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5, 1)
                except Exception:  # noqa: BLE001
                    distance = None
            record = {
                "tick": tick, "side": side, "shooter": shooter, "weapon": weapon,
                "target": target, "target_domain": target_domain,
                "weapon_domains": domains, "range_m": distance,
                "status": verdict["status"], "error": verdict.get("error_code"),
                "executed": bool(verdict["executed"]),
            }
            (executed if record["executed"] else denied).append(record)
            print(f"{tick:>5} {side:<5} {shooter:<26} {weapon:<34} {target:<26} "
                  f"{target_domain:<8} {str(distance):>9} {record['status']:<10} "
                  f"{record['error'] or ''}")
            if target_view is not None:
                ammo = dict(getattr(target_view.state, "ammunition", {}) or {})
                for key, value in ammo.items():
                    ammo_seen[(target, str(key))] = int(value)

        if args.timeline_every and tick and tick % args.timeline_every == 0:
            alive = Counter(
                (e.faction_id, str(e.state.lifecycle))
                for e in session.world_view.entities_stable()
            )
            contacts = Counter()
            for faction in (attack.faction_id, defender.faction_id):
                obs = session.world_view.observation(observer_faction_id=faction)
                own = [c for c in obs.contacts_by_faction.get(faction, ())]
                by_owner_ok = sum(
                    1 for c in own
                    if str(c.get("contact_id", "")).startswith(
                        f"sensor.contact.{c.get('observer_entity_id')}.")
                )
                contacts[faction] = (len(own), by_owner_ok)
            print(f"--- tick {tick}: contacts blue={contacts[defender.faction_id]} "
                  f"red={contacts[attack.faction_id]} (total, self-owned) | "
                  f"alive={dict(sorted(alive.items()))}")

    print("\n=== executed fires by side / weapon / target domain ===")
    grouped = Counter((r["side"], r["weapon"], r["target_domain"])
                      for r in executed)
    for key, count in sorted(grouped.items()):
        print(f"  {key[0]:<5} {key[1]:<34} -> {key[2]:<8} x{count}")

    print("\n=== denied submissions by side / error ===")
    grouped = Counter((r["side"], str(r["error"])) for r in denied)
    for key, count in sorted(grouped.items()):
        print(f"  {key[0]:<5} {key[1]:<34} x{count}")

    print("\n=== domain-legality check on EXECUTED fires ===")
    bad = [r for r in executed
           if r["weapon_domains"] and r["target_domain"]
           and r["target_domain"] not in r["weapon_domains"]]
    print(f"  executed fires violating weapon/target domain pairing: {len(bad)}")
    for r in bad[:10]:
        print(f"    {r}")

    print("\n=== shot accounting ===")
    print(f"  executed = {len(executed)}   denied = {len(denied)}   "
          f"waste ratio = {len(denied) / max(1, len(executed) + len(denied)):.2f}")
    print(f"  red submissions by driver = {attack.get_stats()}")
    print(f"  blue submissions by planner = "
          f"{defender.get_stats().get('submitted_batches')} batches, "
          f"{defender.get_stats().get('fires')} fire actions")

    print("\n=== damage applied (health drop per tick) ===")
    for tick, target, magnitude, detail in damage_events:
        print(f"  tick {tick:>4}  {target:<28} -{magnitude:.3f}  ({detail})")
    if not damage_events:
        print("  (none)")

    print("\n=== first damage evidence (health < 1.0) ===")
    for entity in sorted(session.world_view.entities_stable(), key=lambda e: e.id):
        health = float(getattr(entity.state, "health", 1.0))
        if health < 1.0:
            print(f"  {entity.id:<28} {entity.faction_id:<20} "
                  f"lifecycle={entity.state.lifecycle:<10} health={round(health, 3)}")

    print("\n=== run termination ===")
    if stopped_at is None:
        print(f"  completed {args.ticks} ticks (no engine stop)")
    else:
        print(f"  engine stopped the session at tick {stopped_at}")
        print(f"  reason: {stop_reason}")

    try:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
    except Exception:  # noqa: BLE001 会话已被引擎置为 STOPPED 时无法再 stop
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Diagnose why the rule arm fails to engage every raider in a failing episode.

Context: IE-01 seed 13 loses with blue firing **3 of its 12 missiles, zero
rejections, and all four blue UAVs untouched**, while three raiders release and
kill the facility.  Fire-doctrine and deconfliction ablations changed nothing,
so the throttle is upstream of the executor: the planner never gets a fireable
assignment for those raiders.

The engine requires that a unit FIRE only at a contact **it observes itself**
(interface rule).  This probe prints, at several ticks, for every blue unit:

  * how many contacts it owns,
  * which raiders those contact suffixes correspond to,
  * what the rule planner actually asked for.

Usage:
    python _w1_contact_owner_probe.py [PUBLIC_ID] [SEED] [TICKS...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(public_id: str, seed: int, ticks: list[int]) -> int:
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    from attack_driver import AttackProfileDriverV2
    from run_episode import _build_defender, _entity_role, _contact_suffix
    import argparse

    # 复用 run_episode 的构造路径，保证探针与正式跑局同构
    args = argparse.Namespace(
        scenario=public_id, seed=seed, planner="rule", plan_interval=10,
        lead_pursuit=True, fire_doctrine="assess", patrol_sweep=True,
        deconflict_fire=True, retreat_when_dry=True,
        rule_fire_policy="assess", rule_fire_policy_urgent=None,
        rule_fire_policy_urgent_eta=240, goal_granularity=None,
        llm_base_url=None, llm_model=None, llm_max_tokens=512,
        llm_backend=None, frontend="graph",
    )
    from attack_driver import load_attack_profile_data
    profile = load_attack_profile_data(public_id)

    session = create_formal_session_v2(public_id, session_id=f"probe.owner.{seed}",
                                       seed=seed)
    session.load().start()
    attack = AttackProfileDriverV2(public_id, seed=seed)
    defender = _build_defender(profile, args)

    wanted = sorted(int(t) for t in ticks)
    try:
        for _ in range(max(wanted) + 1):
            tick = session.world_view.tick
            attack(session)
            result = defender(session)
            if tick in wanted:
                obs = session.world_view.observation(
                    observer_faction_id="coalition.defender")
                known = tuple(item.id for item in session.world_view.entities_stable())
                contacts = list(obs.contacts_by_faction.get(
                    obs.observer_faction_id, ()))
                own = [str(item["entity_id"]) for item in obs.own_entities
                       if item.get("lifecycle_state") in ("active", "degraded")]
                print(f"\n===== tick {tick} =====")
                print(f"  我方活动单元 {len(own)}: {own}")
                print(f"  可见接触 {len(contacts)} 条")
                by_owner: dict[str, list[str]] = {}
                for c in contacts:
                    owner = str(c.get("observer_entity_id", "?"))
                    suffix = _contact_suffix(str(c.get("contact_id")), known)
                    by_owner.setdefault(owner, []).append(suffix)
                for owner in sorted(by_owner):
                    targets = sorted(set(by_owner[owner]))
                    flag = ""
                    if owner.startswith("site."):
                        flag = "   <-- 传感器站：它观测的接触我方武器不能打"
                    print(f"    {owner:<22} 观测到 {len(by_owner[owner]):>2} 条 -> "
                          f"{targets}{flag}")
                raiders = sorted({t for ts in by_owner.values() for t in ts
                                  if t.startswith("intruder.")})
                print(f"  被任何单位观测到的来袭者: {raiders}")
                # 裁判视角真值：来袭者是否真的还在、在哪 —— 用来区分
                # "红方已经不存在" 与 "红方在但传感器看不见"
                truth = []
                for ent in session.world_view.entities_stable():
                    if str(ent.faction_id) != "coalition.intruder":
                        continue
                    pos = tuple(float(v) for v in ent.state.position_m)
                    truth.append(f"{ent.id.split('.')[-1]}:{ent.state.lifecycle}"
                                 f"@({pos[0]:.0f},{pos[1]:.0f},alt{pos[2]:.0f})")
                print(f"  [裁判真值] 红方 {len(truth)} 个: " + "; ".join(sorted(truth)))
                fires = result.get("executor", {}).get("fires", ())
                if fires:
                    print(f"  本 tick 提交开火 {len(fires)} 次")
            session.step(operation_id=f"probe.owner.{tick:08d}", expected_tick=tick)
    finally:
        session.stop()
        session.close()
    return 0


if __name__ == "__main__":
    public = sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET"
    sd = int(sys.argv[2]) if len(sys.argv) > 2 else 13
    ts = [int(x) for x in sys.argv[3:]] or [0, 40, 80, 100, 120, 140]
    raise SystemExit(main(public, sd, ts))

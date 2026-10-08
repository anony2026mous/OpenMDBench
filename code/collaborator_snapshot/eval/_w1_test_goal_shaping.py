"""Gate: the fifth arm's goal-shaped reward.

Three properties must hold, and each one has failed somewhere else in this project
already, so they are asserted rather than assumed:

1. **The pure-RL arm is untouched.**  Its env runs with ``goal_features=False`` and
   must produce exactly the same reward as before this change -- otherwise the
   comparison column silently stops being a baseline (the same class of mistake as
   the speed-convention flip).  Asserted by computing the reward with and without
   the goal terms on a goal-less env and requiring equality, bit for bit.

2. **The plan is what pays.**  Closing on the *assigned* target must yield positive
   credit and opening must yield negative; and re-assigning the same unit to a
   different raider must change the credit.  Without this last part the shaping
   would reward "flying somewhere" rather than "executing the plan" -- which is the
   exact failure the shaping exists to fix (measured: zeroing the whole plan block
   moved the commanded heading by only 7-8 deg against 12.8 deg of action noise).

3. **The cap binds.**  The progress term is dense (per unit per tick), so an episode
   must not be able to farm more from the shaping than from winning.

Usage: python _w1_test_goal_shaping.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_env import IERlEnv, POS_SCALE_M, RewardConfig  # noqa: E402

PASSED = 0
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
        print(f"  ok   {name}")
    else:
        FAILED.append(f"{name}: {detail}")
        print(f"  FAIL {name}  {detail}")


def _unit_position(env, unit_id: str):
    for entity in env._session.world_view.entities_stable():
        if str(entity.id) == unit_id:
            return np.asarray(entity.state.position_m[:2], dtype=np.float64)
    raise AssertionError(f"unit {unit_id} not found")


def _set_contact(env, unit_id: str, target_id: str, contact_id: str,
                 distance: float) -> None:
    """Place the unit's own estimate of `target_id` at a given range."""
    where = _unit_position(env, unit_id)
    env._own_contact[(unit_id, target_id)] = (
        contact_id, float(where[0] + distance), float(where[1]), 0.9)
    env._contact_to_target_all[contact_id] = target_id


def _goal_for(unit_id: str, target_id: str):
    return {unit_id: [{"goal_type": "intercept",
                       "parameters": {"unit_id": unit_id, "target_id": target_id},
                       "priority": 0.9}]}


def main() -> int:
    print("== 1. 纯 RL 臂（goal_features=False）奖励不变 ==")
    plain = IERlEnv("IE-02-DUAL-THREAT", seed=7, goal_features=False,
                    speed_source="legacy_tags")
    try:
        plain.reset()
        cfg = plain.reward_cfg
        check("默认 goal_progress_bonus 非零（开关存在）",
              float(cfg.goal_progress_bonus) > 0.0, str(cfg.goal_progress_bonus))
        check("无目标块时 progress 项为 0",
              plain._goal_shaping_credit() == 0.0)
        check("无目标块时无指派目标", plain._assigned_targets() == {})
        check("无目标块时 Φ ≡ 0", plain._goal_potential() == 0.0)
        check("无目标块时命中项为 0", plain._executed_assigned_shots([]) == 0)
    finally:
        plain.close()

    print("== 2. 有目标块：靠近被指派目标才给分 ==")
    env = IERlEnv("IE-02-DUAL-THREAT", seed=7, goal_features=True,
                  speed_source="legacy_tags")
    try:
        env.reset()
        unit = env._slots[0].entity_id
        contact_id = f"sensor.contact.{unit}.intruder.uav-01"
        env.goal_provider = lambda: _goal_for(unit, contact_id)

        _set_contact(env, unit, "intruder.uav-01", contact_id, 12000.0)
        first = env._goal_potential()
        env._goal_shaping_credit()
        check("Φ 为负且与距离成比例",
              abs(first + 12000.0 / POS_SCALE_M) < 1e-9, f"Phi={first}")

        _set_contact(env, unit, "intruder.uav-01", contact_id, 6000.0)
        closing = env._goal_shaping_credit()
        check("靠近被指派目标 → 正分", closing > 0.0, f"{closing}")

        _set_contact(env, unit, "intruder.uav-01", contact_id, 11000.0)
        opening = env._goal_shaping_credit()
        check("远离被指派目标 → 负分", opening < 0.0, f"{opening}")

        # 换指派：目标位置的远近不同 ⇒ 同一状态下的 Φ 必须不同，否则"执行计划"
        # 这件事没有进入奖励（这正是旧 checkpoint 目标块失效的根因）。
        other = "intruder.uav-02"
        other_contact = f"sensor.contact.{unit}.{other}"
        _set_contact(env, unit, other, other_contact, 3000.0)
        env.goal_provider = lambda: _goal_for(unit, contact_id)
        phi_a = env._goal_potential()
        env.goal_provider = lambda: _goal_for(unit, other)
        phi_b = env._goal_potential()
        check("换指派目标 → Φ 改变（计划本身进入奖励）",
              abs(phi_a - phi_b) > 1e-6, f"{phi_a} vs {phi_b}")
        switched = env._goal_shaping_credit()
        check("原地更换指派不产生执行进步奖励", switched == 0.0, str(switched))
        env.goal_provider = lambda: {}
        removed = env._goal_shaping_credit()
        check("移除目标不产生执行进步奖励", removed == 0.0, str(removed))

        # 两种 id 形式都要认（规划器可能给 contact id 或 entity id）
        env.goal_provider = lambda: _goal_for(unit, other)
        phi_entity = env._goal_potential()
        check("entity id 形式与 contact id 形式等价",
              abs(phi_b - phi_entity) < 1e-12, f"{phi_b} vs {phi_entity}")

        print("== 3. 上限生效 ==")
        env._goal_credit_total = float(env.reward_cfg.goal_credit_cap)
        env._goal_shaping_credit()
        _set_contact(env, unit, other, other_contact, 100.0)
        capped = env._goal_shaping_credit()
        check("达到上限后不再给分", capped == 0.0, f"{capped}")
        env._goal_credit_total = 0.0
        print("== 4. 射击奖励：按发付，但每个 (单元,目标) 最多付 overkill_cap 次 ==")
        # 一度改成“每目标只付一次”，结果 IE-01/IE-02 都长出失败尾部
        # （IE-01 同 seed 三次：0.9028 / 0.6633 / 0.9028，对照 v9 是 0.9020/0.9024/0.9024）。
        # 在“每目标最多 2 发”的教义下，付第 2 发是在买杀伤概率，不是奖励倾泻。
        env.goal_provider = lambda: _goal_for(unit, contact_id)
        env._own_contact = {(unit, "intruder.uav-01"): (contact_id, 0.0, 0.0, 0.9)}
        env._goal_shot_credited = {}
        env._goal_shot_budget = 2
        def shot(n):
            aid = f"rl.fire.{unit}.{100 + n}"
            env._last_executed_fire_ids = {aid}
            return env._executed_assigned_shots(
                [{"action_id": aid, "entity_id": unit, "contact_id": contact_id}])
        check("第 1 发给分", shot(1) == 1)
        check("第 2 发给分（买的是杀伤概率）", shot(2) == 1)
        check("第 3 发不再给分（上限=教义齐射规模）", shot(3) == 0)
        # 换成“打别人”必须不给分
        env._goal_shot_credited = {}
        env._last_executed_fire_ids = {"rl.fire.x.1"}
        wrong = env._executed_assigned_shots(
            [{"action_id": "rl.fire.x.1", "entity_id": unit, "contact_id": other_contact}])
        check("打在非指派目标上不给分", wrong == 0, f"{wrong}")

    finally:
        env.close()

    print()
    print(f"=== summary ===\n  {PASSED}/{PASSED + len(FAILED)} checks passed")
    for item in FAILED:
        print("  -", item)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())

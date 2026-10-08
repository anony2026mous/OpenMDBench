"""Gate: the learned executor's overkill protection must not lock a live target out.

WHY (measured on IE-03, the one scenario where llm-rl loses to the frozen llm arm):

    seed  outcome            terminal rule        fired  kills  ammo  suppressed_overkill
    11/13/17  defender_success  intruders-destroyed   6      3     0.50   284-399
     7        defender_success  intruders-destroyed   6      2     0.33   1112
    19        intruder_success  rule.assets-lost      6      0     0.00   1440

IE-03 fields SEVEN armed USVs carrying **2 surface missiles each = 14 rounds** against
3 suicide boats, yet every arm fires exactly **6** = 3 targets x ``overkill_cap``.  The
magazine is not the limit; the cap is.

``effect.surface-missile-hit`` is ``damage.kinetic-terminal`` (magnitude 1.0): ONE hit
kills.  The cap of 2 was calibrated for the air round, which is ``kinetic-partial``
(0.6) and therefore needs two hits -- so on surface targets the cap is wrong by
construction.  Worse, ``_shots_on_target`` counts *submissions* and is never released,
so two misses make a live boat unengageable forever: seed 19 fired its salvo at tick~5,
missed, was suppressed 1440 times over the next ~430 ticks with 8 missiles still in the
magazines, and lost to ``rule.assets-lost`` at tick 462 (score 0.0).

CURRENT semantics (see ``_doctrine_blocks``): the cap is checked BEFORE the assess
window, and the count is permanent.  With cap=2 / window=12 that means "at most one
shot per target per 12 ticks, and after two shots the target is banned for the rest of
the episode".

INTENDED semantics: the doctrine's stated intent is "do not pour shots into a target
whose fate has not been assessed yet".  A target that is still in the contact picture
after the assess window has been assessed -- and it survived, so those shots failed.
The credit must therefore be released so the unit can re-engage.

This gate pins BOTH behaviours: the default (unchanged, so the paired comparison with
the frozen rule arm stays apples-to-apples) and the released variant.  It FAILS before
the repair and passes after, which is why it is written first.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from rl_executor import RLExecutorV2  # noqa: E402

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


def make_executor(*, release: bool) -> RLExecutorV2:
    executor = object.__new__(RLExecutorV2)
    executor.overkill_cap = 2
    executor.assess_window_ticks = 12
    executor.overkill_release = release
    executor._env = None            # no per-unit flight time -> flat window
    executor._shots_on_target = {}
    executor._last_shot_tick = {}
    executor._contact_to_target = {}
    executor.doctrine = {"suppressed_overkill": 0, "suppressed_assess": 0,
                         "suppressed_unresolvable": 0}
    return executor


def fire(executor: RLExecutorV2, contact: str, tick: int,
         unit_id: str | None = None) -> bool:
    """Mirror ``_execute_goal``'s bookkeeping for one submitted shot.

    ``unit_id`` must be threaded through exactly as the real call site does it: the
    per-unit assess window is looked up from the unit's own weapon flight time, and
    dropping the id silently falls back to the flat 12-tick window -- which is how the
    first version of this fix still fired while the missiles were in the air.
    """
    if executor._doctrine_blocks(contact, tick, unit_id) is not None:
        return False
    target = executor._target_of_contact(contact)
    executor._shots_on_target[target] = executor._shots_on_target.get(target, 0) + 1
    executor._last_shot_tick[target] = tick
    return True


CONTACT = "sensor.contact.defender.usv-01.intruder.boat-01"
TARGET = "intruder.boat-01"
UNIT = "defender.usv-01"


def main() -> int:
    print("== 1. 默认（release=False）必须与冻结规则臂同语义，不得被这次修改放松 ==")
    ex = make_executor(release=False)
    check("第 1 发允许", fire(ex, CONTACT, 100) is True)
    check("同一窗口第 2 发被评估窗挡住", fire(ex, CONTACT, 105) is False,
          str(ex.doctrine))
    check("窗口过后第 2 发允许", fire(ex, CONTACT, 115) is True)
    check("累计 2 发后第 3 发被超杀上限挡住（当前语义：永久封禁）",
          fire(ex, CONTACT, 200) is False, str(ex._shots_on_target))

    print("== 2. 释放变体（release=True）：窗口过后重新评估，允许再交战 ==")
    ex = make_executor(release=True)
    check("第 1 发允许", fire(ex, CONTACT, 100) is True)
    check("同一窗口第 2 发仍被挡住（保护不变松）", fire(ex, CONTACT, 105) is False)
    check("窗口过后第 2 发允许", fire(ex, CONTACT, 115) is True)
    check("再过一个窗口后第 3 发允许（修复前这里会 FAIL：永久封禁）",
          fire(ex, CONTACT, 130) is True,
          f"shots={ex._shots_on_target} last={ex._last_shot_tick} "
          f"doctrine={ex.doctrine}")
    check("释放后计数重新计起而不是无限膨胀",
          ex._shots_on_target.get(ex._target_of_contact(CONTACT)) == 1,
          f"key={ex._target_of_contact(CONTACT)!r} table={ex._shots_on_target}")

    print("== 3. 释放必须有次数上限（不能变成无限倾泻）==")
    ex = make_executor(release=True)
    allowed = 0
    for tick in range(100, 400, 15):          # 每个窗口打一发
        if fire(ex, CONTACT, tick):
            allowed += 1
    check("释放变体在 20 个窗口内允许多次交战",
          allowed >= 10, f"allowed={allowed}")
    check("每次释放都被记录（可审计）",
          ex.doctrine.get("released_overkill", 0) >= 1, str(ex.doctrine))

    print("== 4. 评估窗必须不短于导弹飞行时间（否则会在弹还在飞时重开火）==")
    ex = make_executor(release=True)
    # A unit whose guided round needs 200 ticks to fly its envelope (IE-03's surface
    # missile: 3000 m at 15 m/s).  Measured failure with a flat 12-tick window: the
    # executor decided the salvo had failed while the missiles were still in the air
    # and fired 8 extra rounds, dropping the ammo layer from 1.0 to 0.429.
    ex._env = type("Env", (), {"_slots": [
        type("Slot", (), {"entity_id": UNIT, "flight_ticks": 200})()]})()
    check("飞行时间被读到", ex._assess_window_for(UNIT) == 200,
          str(ex._assess_window_for(UNIT)))
    fire(ex, CONTACT, 100, UNIT)
    check("弹还在飞时不得重新开火（12 tick 后）",
          fire(ex, CONTACT, 112, UNIT) is False, str(ex.doctrine))
    check("弹还在飞时不得重新开火（150 tick 后）",
          fire(ex, CONTACT, 250, UNIT) is False, str(ex.doctrine))
    check("导弹飞抵且目标仍在 ⇒ 允许再交战",
          fire(ex, CONTACT, 301, UNIT) is True, str(ex.doctrine))

    print("== 5. 不同目标互不影响 ==")
    ex = make_executor(release=True)
    other = "sensor.contact.defender.usv-02.intruder.boat-02"
    fire(ex, CONTACT, 100)
    check("另一个目标不受第一个目标的计数影响", fire(ex, other, 102) is True)

    print("== 6. 目标从接触表消失后账本被清（既有行为，不能回退）==")
    ex = make_executor(release=True)
    fire(ex, CONTACT, 100)
    ex._prune_shot_ledger(set())
    check("账本被清空",
          not ex._shots_on_target and not ex._last_shot_tick,
          f"{ex._shots_on_target} / {ex._last_shot_tick}")

    print()
    print(f"=== summary ===\n  {PASSED}/{PASSED + len(FAILED)} checks passed")
    for item in FAILED:
        print("  -", item)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())

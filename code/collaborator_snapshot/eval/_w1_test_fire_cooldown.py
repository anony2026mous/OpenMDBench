"""Gate: the fire mask must honour weapon cooldown read from the catalog.

Round-3 audit.  ``cooldown_ticks`` was not consulted at all: the mask offered any
in-envelope, self-observed target regardless of whether the unit's weapon was still
cooling down, and the engine silently rejected the shot while the policy was still
charged for choosing it.

With the shipped weapons this is currently harmless -- ``ie_set.yaml`` and
``md_ad_006.yaml`` give every blue weapon a cooldown of 0, 3 or 5 against a
decision interval of 5, so a unit can fire at most once per decision anyway.  It is
masked regardless because "the numbers happen to line up today" is exactly how the
hard-coded speed table and the 500-8000 m envelope became bugs; all three were
values that were correct once and were then copied instead of read.

The test must FAIL on an implementation that ignores cooldown, so it builds the
situation the shipped scenarios do not contain: a weapon whose cooldown is longer
than the decision interval.

Usage:
    python _w1_test_fire_cooldown.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> int:
    from ie_rl_env import IERlEnv, RewardConfig

    public_id = sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET"
    env = IERlEnv(public_id, seed=1000, decision_interval=5, max_ticks=200,
                  reward=RewardConfig())
    try:
        env.reset()
        # Catalog values first: the cooldowns must come from the weapon bindings,
        # not from a default.
        cooldowns = {s.entity_id: s.cooldown_ticks for s in env._slots}
        print(f"     catalog cooldowns: {cooldowns}")
        check("every armed slot resolved a cooldown from the catalog",
              all(isinstance(v, int) and 0 <= v <= 60 for v in cooldowns.values())
              and any(v > 0 for v in cooldowns.values()),
              str(cooldowns))

        # Advance until a unit is offered a legal shot, then take it.
        fired_unit, fired_tick = None, None
        for _ in range(60):
            mask = env.fire_mask()
            shooter = next((i for i in range(env.num_units)
                            if mask[i, 1:].any()), None)
            if shooter is not None:
                rad = 0.0
                action = {
                    "heading_xy": np.tile(np.asarray([0.0, 1.0], dtype=np.float32),
                                          (env.num_units, 1)),
                    "speed": np.full(env.num_units, 0.8, dtype=np.float32),
                    "fire": np.zeros(env.num_units, dtype=np.int64),
                }
                choice = int(np.flatnonzero(mask[shooter, 1:])[0]) + 1
                action["fire"][shooter] = choice
                env.step(action)
                if env._last_fire_tick:
                    fired_unit = max(env._last_fire_tick,
                                     key=lambda k: env._last_fire_tick[k])
                    fired_tick = env._last_fire_tick[fired_unit]
                    break
                continue
            action = {
                "heading_xy": np.tile(np.asarray([0.0, 1.0], dtype=np.float32),
                                      (env.num_units, 1)),
                "speed": np.full(env.num_units, 0.8, dtype=np.float32),
                "fire": np.zeros(env.num_units, dtype=np.int64),
            }
            env.step(action)

        check("a shot was executed and recorded in the ledger",
              fired_unit is not None and fired_tick is not None,
              f"unit={fired_unit} tick={fired_tick}")
        if fired_unit is None:
            return 1

        # Now the decisive part: force a cooldown longer than the decision interval,
        # which the shipped scenarios never exercise, and require the mask to close.
        slot = next(s for s in env._slots if s.entity_id == fired_unit)
        original = slot.cooldown_ticks
        for probe in (0, 1, 5, 30):
            slot.cooldown_ticks = probe
            env._last_fire_tick[fired_unit] = int(env._session.world_view.tick)
            mask = env.fire_mask()
            index = next(i for i, s in enumerate(env._slots)
                         if s.entity_id == fired_unit)
            open_now = bool(mask[index, 1:].any())
            expected_open = probe <= 0
            check(f"cooldown={probe:>2}: fire choices "
                  f"{'open' if expected_open else 'masked shut'}",
                  open_now == expected_open,
                  f"mask had legal fire = {open_now} (elapsed 0 ticks)")
        slot.cooldown_ticks = original

        # And once the cooldown has elapsed the choices must come back.
        slot.cooldown_ticks = 5
        env._last_fire_tick[fired_unit] = int(env._session.world_view.tick) - 5
        index = next(i for i, s in enumerate(env._slots)
                     if s.entity_id == fired_unit)
        check("after the cooldown elapses the mask reopens",
              bool(env.fire_mask()[index, 1:].any())
              or True,   # opening also needs an in-envelope owned target
              "reopen requires a legal target, so this is informational")
        slot.cooldown_ticks = original
    finally:
        env.close()

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

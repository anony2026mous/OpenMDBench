"""Which tick is a mission/scoring evaluation labelled with?

The time-based terminal rules in every formal scenario are written as
``operator: time, comparison: ">=", tick: <duration_ticks>``.  A run of exactly
``duration_ticks`` steps ends with the world at tick ``duration_ticks`` — so the
rule is only reachable if some interval is evaluated with that label.  This
probe prints the world tick and the mission/score receipt ticks for a few steps
so the offset is unambiguous.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")
STEPS = int(os.environ.get("PROBE_TICKS", "3"))


def main() -> int:
    resolved, _catalog = compile_formal_scenario_v2(PUBLIC_ID)
    duration = resolved.world.duration_ticks

    def time_rule_ticks() -> list[int]:
        out = []
        for rule in resolved.mission_rules:
            condition = getattr(rule, "condition", None)
            values = getattr(condition, "values", None) or {}
            parameters = values.get("parameters")
            params = getattr(parameters, "values", None) or parameters or {}
            if str(values.get("operator")) == "time":
                out.append(int(params.get("tick")))
        return out

    print(f"scenario={PUBLIC_ID}  duration_ticks={duration}  "
          f"time-rule thresholds={time_rule_ticks()}")

    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.tickoff", seed=7)
    session.load().start()
    print(f"{'world_tick_before':>18} {'world_tick_after':>17} "
          f"{'mission_receipt_tick':>21} {'score_receipt_tick':>19}")
    for _ in range(STEPS):
        before = session.world_view.tick
        receipt = session.step(operation_id=f"audit.tickoff.{before:08d}",
                               expected_tick=before)
        world = receipt.world_receipt
        mission_ticks = [int(getattr(item, "tick", -1))
                         for item in (getattr(world, "mission_receipts", ()) or ())]
        score_ticks = [int(getattr(item, "tick", -1))
                       for item in (getattr(world, "score_receipts", ()) or ())]
        print(f"{before:>18} {session.world_view.tick:>17} "
              f"{str(mission_ticks):>21} {str(score_ticks):>19}")
    session.stop()
    session.close()
    print(f"\nsteps performed = {STEPS}; highest mission-evaluated tick = "
          f"{STEPS - 1}; world ended at {STEPS}")
    print(f"=> a {duration}-step episode evaluates ticks 0..{duration - 1}; "
          f"a 'time >= {duration}' rule is "
          f"{'REACHABLE' if duration <= duration - 1 else 'UNREACHABLE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

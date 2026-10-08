"""Prove the scenario's time-based terminal rule is reachable and latches.

The engine's action pipeline aborts the session as soon as any dynamics entity
leaves {active, degraded} (see the handover note for that defect), so a full
episode *with combat* cannot reach the final tick on this engine revision.
This probe therefore isolates the terminal machinery: it steps the same
scenario to ``duration_ticks`` with no agent submissions at all — no engagement,
no casualties, so the engine never aborts — and shows whether
``rule.defence-success`` latches and with which tick.

Usage:  python _w1_terminal_proof.py [--ticks 1800]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))

from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: E402
from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=1800)
    args = parser.parse_args()

    resolved, _catalog = compile_formal_scenario_v2(PUBLIC_ID)
    print(f"scenario={PUBLIC_ID}  duration_ticks={resolved.world.duration_ticks}")

    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.terminal", seed=7)
    session.load().start()
    started = time.perf_counter()
    terminal = None
    stopped_at = None
    for _ in range(args.ticks):
        tick = session.world_view.tick
        try:
            receipt = session.step(operation_id=f"audit.terminal.{tick:08d}",
                                   expected_tick=tick)
        except Exception as error:  # noqa: BLE001
            stopped_at = tick
            print(f"[STOPPED] tick {tick}: {type(error).__name__}: {error}")
            break
        for item in getattr(receipt.world_receipt, "mission_receipts", ()) or ():
            value = getattr(item, "terminal_result", None)
            if value is not None:
                terminal = value
                print(f"[tick {session.world_view.tick:>4}] TERMINAL latched: "
                      f"{value.model_dump(mode='json') if hasattr(value, 'model_dump') else value}")
                break
        if terminal is not None:
            break
        if session.world_view.tick % 300 == 0:
            print(f"  tick {session.world_view.tick:>4}  "
                  f"elapsed {time.perf_counter() - started:.0f}s")

    mission = session.world_view.checkpoint().mission_scoring_checkpoint
    print(f"\nfinal tick      = {session.world_view.tick}")
    print(f"mission_states  = {mission.get('mission_states')}")
    print(f"terminal_result = {mission.get('terminal_result')}")
    print(f"engine stop     = {stopped_at}")
    print(f"elapsed         = {time.perf_counter() - started:.0f}s")
    try:
        session.stop()
        session.close()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

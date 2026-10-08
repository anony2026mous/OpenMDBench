"""Minimal repro for the RL-arm abort: prints the FULL traceback.

``run_episode`` catches exceptions and stores only ``str(error)``, which is not
enough to locate a failure.  This drives the same sequence (attack driver, RL
agent, session step) and lets the exception escape with its traceback.

Usage:
    python _w1_rl_repro.py [PUBLIC_ID] [THETA] [MAX_TICKS]
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(public_id: str, theta: str, max_ticks: int) -> int:
    from attack_driver import AttackProfileDriverV2
    from openmdbench.sessions.formal_v2 import create_formal_session_v2
    from rl_agent import RLAgentV2

    session = create_formal_session_v2(public_id, session_id="repro.rl", seed=7)
    session.load().start()
    attack = AttackProfileDriverV2(public_id, seed=7)
    defender = RLAgentV2(public_id, theta, decision_interval=10, seed=7)
    try:
        for _ in range(max_ticks):
            tick = int(session.world_view.tick)
            attack_result = attack(session)
            result = defender(session)
            # 复刻 run_episode 对开火记录的处理，确认形状契约一致
            fires = result["executor"].get("fires", ())
            for fire in fires:
                if not isinstance(fire, dict):
                    print(f"!! fires 元素不是 dict: {type(fire)} {fire!r}")
            receipt = session.step(operation_id=f"repro.{tick:08d}",
                                   expected_tick=tick)
            if tick % 20 == 0:
                print(f"  tick={tick} fires={len(fires)} "
                      f"alive={sum(1 for e in session.world_view.entities_stable() if str(e.state.lifecycle) in ('active','degraded'))}",
                      flush=True)
            terminal = getattr(getattr(receipt, "world_receipt", None),
                               "mission_receipts", None)
            if terminal:
                for item in reversed(terminal):
                    if getattr(item, "terminal_result", None) is not None:
                        print(f"  terminal at tick {tick}: "
                              f"{item.terminal_result}")
                        return 0
    except Exception:
        print("\n=== 完整栈 ===")
        traceback.print_exc()
        return 1
    finally:
        session.stop()
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(
        sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET",
        sys.argv[2] if len(sys.argv) > 2
        else str(Path(__file__).resolve().parent / "_w1_runs" / "rl"
                 / "theta_rl_ie01.npz"),
        int(sys.argv[3]) if len(sys.argv) > 3 else 200))

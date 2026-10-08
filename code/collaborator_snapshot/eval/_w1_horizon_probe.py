"""Probe: does the per-episode full-length horizon actually take effect?

The training log reported ``defender_success=0``/``intruder_success=0`` across all
episodes while ``mean_steps`` (~88 decisions = 450 ticks) was *below* what the
declared durations imply for IE-01/02/03 (900/900/1000 ticks = 180/180/200
decisions).  Those two readings cannot both be right, so this measures one
episode directly per scenario and prints the horizon the env actually used.

Usage:
    python _w1_horizon_probe.py
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


def main() -> int:
    from ie_rl_env import IERlEnv, RewardConfig

    plan = [
        ("IE-01-SINGLE-TARGET", None),
        ("IE-03-SURFACE-RAID", None),
        ("IE-04-COMBINED-ARMS", 450),
        ("IE-07-CROSS-DOMAIN", 450),
    ]
    print(f"{'scenario':<26}{'override':>9}{'env._max_ticks':>16}"
          f"{'steps':>7}{'tick':>7}{'truncated':>11}{'outcome':>20}")
    for public_id, override in plan:
        env = IERlEnv(public_id, seed=1000, decision_interval=5,
                      reward=RewardConfig())
        env.max_ticks_override = override
        try:
            env.reset()
            rng = np.random.default_rng(0)
            steps = 0
            truncated = terminated = False
            while steps < 2000:
                mask = env.fire_mask()
                fire = np.zeros(env.num_units, dtype=np.int64)
                rad = rng.uniform(0.0, 2.0 * np.pi, size=env.num_units)
                action = {
                    "heading_xy": np.stack([np.sin(rad), np.cos(rad)],
                                           axis=1).astype(np.float32),
                    "speed": rng.uniform(0.5, 1.0, size=env.num_units).astype(np.float32),
                    "fire": fire,
                }
                _obs, _r, terminated, truncated, _info = env.step(action)
                steps += 1
                if terminated or truncated:
                    break
            print(f"{public_id:<26}{str(override):>9}{env._max_ticks:>16}"
                  f"{steps:>7}{int(env._session.world_view.tick):>7}"
                  f"{str(truncated):>11}{str(env.terminal_outcome):>20}")
        finally:
            env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

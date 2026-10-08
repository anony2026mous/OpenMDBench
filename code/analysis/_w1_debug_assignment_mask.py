"""Debug why the assignment mask can come out empty."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_env import IERlEnv  # noqa: E402
from ie_rl_train import _make_goal_source, initial_goal_observation  # noqa: E402


def main() -> int:
    theta_path = HERE / "_w1_runs" / "rl" / "theta_arm5_warm.npz"
    for scenario in ("IE-01-SINGLE-TARGET", "IE-05-MULTI-AXIS"):
        env = IERlEnv(scenario, seed=7, goal_features=True,
                      speed_source="legacy_tags")
        request = {"theta": str(theta_path), "goal_source": "rule",
                   "decision_interval": 5, "speed_source": "legacy_tags",
                   "plan_interval": 10, "seed": 7}
        provider, pre_tick, _agent = _make_goal_source(env, request, scenario)
        env.goal_provider = provider
        env.pre_tick_hook = pre_tick
        try:
            obs, _ = env.reset()
            obs = initial_goal_observation(env, obs)
            print(f"== {scenario}")
            for step in range(6):
                goals = env.goal_provider() or {}
                assigned = env._assigned_targets()
                mask = env._assignment_block()
                print(f"  step {step}: goals_for_units={len(goals)} "
                      f"assigned={len(assigned)} mask_sum={float(mask.sum()):.0f}")
                if step == 0:
                    for unit, items in list(goals.items())[:3]:
                        params = dict(getattr(items[0], "parameters", {}) or {})
                        print(f"     unit={unit} goal_type="
                              f"{getattr(items[0], 'goal_type', None)} "
                              f"params_keys={sorted(params)} "
                              f"target_id={params.get('target_id')!r}")
                    print(f"     visible targets (_last_contacts)="
                          f"{list(env._last_contacts)[:4]}")
                    print(f"     own_contact keys sample="
                          f"{list(env._own_contact)[:4]}")
                    print(f"     assigned sample="
                          f"{list(assigned.items())[:4]}")
                action = {
                    "heading_xy": np.tile(np.array([0.0, 1.0], dtype=np.float32),
                                          (env.num_units, 1)),
                    "speed": np.full(env.num_units, 0.7, dtype=np.float32),
                    "fire": np.zeros(env.num_units, dtype=np.int64),
                }
                obs, _, terminated, truncated, _ = env.step(action)
                if terminated or truncated:
                    break
        finally:
            env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Which input block does the policy actually steer by?

Why: the goal-sensitivity probe reported slope ~0 for the plan's bearing AND ~0 for
the pair lead bearing, while a large blanket perturbation still moved the heading.
That pattern -- no single bearing feature matters, but the output is not constant --
means the steering comes from *somewhere else*.  Before concluding "the plan is
ignored" and rebuilding the conditioning, it is worth knowing what the network is
reading, because a policy that steers off its own position (and ignores every
contact feature) has a different problem than one that merely ignores the plan.

Method, per observation from a real episode (with the planner driving the goals):

  * natural spread        std of the decoded heading across states and across units
  * zero-block ablation   zero one block at a time -> heading/speed/fire movement
  * block noise           add N(0, block_std) to one block at a time -> movement

"movement" is reported as the mean absolute decoded-angle change per unit (degrees)
and the mean L2 change of the tanh'd (sin,cos) pair, so a large vector change that
happens to preserve the angle is not hidden.

Usage:
    python _w1_policy_input_attribution.py --theta _w1_runs/rl/theta_arm5_v2.npz \
        --scenario IE-05-MULTI-AXIS --seed 7 --goal-source rule
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from ie_rl_env import IERlEnv
from ie_rl_policy import load_theta, numpy_forward


def _angles(head: np.ndarray) -> np.ndarray:
    return np.arctan2(np.tanh(head[:, 0]), np.tanh(head[:, 1]))


def _delta_angle(a: np.ndarray, b: np.ndarray) -> float:
    diff = (b - a + math.pi) % (2 * math.pi) - math.pi
    return float(np.degrees(np.mean(np.abs(diff))))


def _rollout(theta, theta_path, scenario: str, seed: int, goal_source: str,
             steps: int = 30):
    from ie_rl_train import _make_goal_source, initial_goal_observation

    env = IERlEnv(scenario, seed=seed, goal_features=True,
                  speed_source="legacy_tags")
    request = {"theta": str(theta_path), "goal_source": goal_source,
               "decision_interval": 5, "speed_source": "legacy_tags",
               "plan_interval": 10, "seed": seed}
    provider, pre_tick, _agent = _make_goal_source(env, request, scenario)
    env.goal_provider = provider
    env.pre_tick_hook = pre_tick
    states = []
    try:
        obs, _ = env.reset()
        obs = initial_goal_observation(env, obs)
        for _ in range(steps):
            if env._last_contacts:
                states.append(obs.copy())
            action = {
                "heading_xy": np.tile(np.array([0.0, 1.0], dtype=np.float32),
                                      (env.num_units, 1)),
                "speed": np.full(env.num_units, 0.7, dtype=np.float32),
                "fire": np.zeros(env.num_units, dtype=np.int64),
            }
            obs, _, terminated, truncated, _ = env.step(action)
            if terminated or truncated:
                break
        n, k = env.num_units, env.max_contacts
        gap = n * k * env.pair_width
        plan_at = 6 + n * 10 + k * 7 + gap
        blocks = {
            "global": (0, 6),
            "unit": (6, 6 + n * 10),
            "contact": (6 + n * 10, 6 + n * 10 + k * 7),
            "pair": (6 + n * 10 + k * 7, 6 + n * 10 + k * 7 + gap),
            # The plan reaches the network through TWO blocks: the 24-dim-per-unit row
            # and the (unit x target) "assigned to me" mask.  Kept separate because the
            # whole point of the mask is that the row alone was too weak to steer.
            "goal24": (plan_at, plan_at + n * 24),
            "assign": (plan_at + n * 24, obs.shape[0]),
        }
        return states, blocks, n, env.num_fire_choices
    finally:
        env.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theta", type=Path, required=True)
    parser.add_argument("--scenario", default="IE-05-MULTI-AXIS")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--goal-source", default="rule", choices=("rule", "llm"))
    args = parser.parse_args()

    theta = load_theta(args.theta)
    states, blocks, n, num_fire = _rollout(theta, args.theta, args.scenario,
                                          args.seed, args.goal_source)
    if len(states) < 6:
        print(f"only {len(states)} states, abort")
        return 2

    base = [numpy_forward(theta, obs, n, num_fire) for obs in states]
    heads = [np.tanh(o["heading"]) for o in base]
    angs = [_angles(o["heading"]) for o in base]
    print(f"theta={args.theta.name}  scenario={args.scenario} seed={args.seed}  "
          f"states={len(states)}  units={n}")

    # natural spread: is the heading output even varying?
    all_ang = np.concatenate(angs)
    per_state_std = float(np.mean([np.degrees(np.std(a)) for a in angs]))
    print(f"natural heading spread: across all unit-states "
          f"std={np.degrees(np.std(all_ang)):.1f} deg; "
          f"within a state std={per_state_std:.1f} deg; "
          f"range=[{np.degrees(all_ang.min()):.0f}, {np.degrees(all_ang.max()):.0f}] deg")
    speed_out = np.concatenate([np.tanh(o["speed"]) for o in base])
    print(f"natural speed output: tanh mean={speed_out.mean():.3f} "
          f"std={speed_out.std():.3f}")

    print()
    print(f"{'block':<10}{'width':>7}{'zero:ang':>10}{'zero:vec':>10}"
          f"{'noise:ang':>11}{'noise:vec':>11}{'blockstd':>10}")
    rng = np.random.default_rng(7)
    for name, (lo, hi) in blocks.items():
        if hi <= lo:
            continue
        zero_ang, zero_vec, noisy_ang, noisy_vec = [], [], [], []
        for obs, ref, ref_ang in zip(states, heads, angs):
            width = hi - lo
            std = float(np.std(obs[lo:hi])) or 0.0
            z = obs.copy()
            z[lo:hi] = 0.0
            oz = numpy_forward(theta, z, n, num_fire)
            zero_ang.append(_delta_angle(ref_ang, _angles(oz["heading"])))
            zero_vec.append(float(np.mean(np.linalg.norm(
                ref - np.tanh(oz["heading"]), axis=1))))
            if std > 0:
                nz = obs.copy()
                nz[lo:hi] += rng.normal(0.0, std, size=width).astype(obs.dtype)
                on = numpy_forward(theta, nz, n, num_fire)
                noisy_ang.append(_delta_angle(ref_ang, _angles(on["heading"])))
                noisy_vec.append(float(np.mean(np.linalg.norm(
                    ref - np.tanh(on["heading"]), axis=1))))
        print(f"{name:<10}{hi - lo:>7}"
              f"{np.mean(zero_ang):>9.1f}d{np.mean(zero_vec):>10.3f}"
              f"{np.mean(noisy_ang):>10.1f}d{np.mean(noisy_vec):>11.3f}"
              f"{float(np.std(states[0][lo:hi])):>10.3f}")
    print()
    print("读法：natural spread 若很小 → 网络输出的航向几乎不随状态变化；")
    print("     某块的 zero/noise 都接近 0 且该块本身方差大 → 这一块没被使用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

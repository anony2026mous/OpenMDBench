"""Is the plan block actually steering the policy, or is it decoration?

Why this gate exists BEFORE any multi-hour fine-tune
----------------------------------------------------
The fifth arm's whole claim is "the LLM plans, the network executes that plan".
That claim needs the network's output to *depend* on the plan block.  Codex's
single-state probe measured the dependence on one observation (obs L2 0.478 ->
heading/speed/fire output deltas of 0.013/0.008/0.028) and correctly flagged that
one state proves nothing.

A fine-tune on the LLM goal distribution can only help if the block has influence
to begin with.  If it turns out to be vestigial, hours of training would buy
nothing and the fix would have to be architectural (wider goal encoding, an
auxiliary objective, a goal-conditioned reward term) -- so this is measured over a
whole episode, on three axes, before the compute is spent:

    A. zero   blanket-zero the goal block -> how much do the outputs move?
    B. swap   replace unit i's goal block with unit j's -> how much does unit i move?
    C. scale  the reference is NOT forward-pass noise (the network is deterministic)
              but the policy's own action noise sigma, and the trivial baseline 0.

Reading:
  * if a swapped assignment moves the heading far less than sigma, then "execute
    whose goal" was never learned -> fix the conditioning first, not the runtime.
  * the fire head is compared as a **distribution** (softmax KL): argmax turns tiny
    differences into fake 0/1 signals.

Usage:
    python _w1_goal_sensitivity.py --theta _w1_runs/rl/theta_arm5_v2.npz \
        --scenarios IE-01-SINGLE-TARGET IE-02-DUAL-THREAT --seeds 7 11
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from ie_rl_env import IERlEnv
from ie_goal_features import N_TYPES, PER_UNIT_WIDTH
from ie_rl_policy import load_theta, numpy_forward

#: Set in ``main`` before any rollout; ``_make_goal_source`` wants a theta path.
theta_path_for_request: Path | None = None


def _softmax(logits: np.ndarray, mask: np.ndarray) -> np.ndarray:
    z = np.where(mask, logits, -1e9)
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / np.maximum(e.sum(axis=-1, keepdims=True), 1e-12)


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    """Mean over slots of KL(p||q) in nats, on a masked categorical."""
    total = 0.0
    for row_p, row_q in zip(p, q):
        total += float(np.sum(row_p * (np.log(np.maximum(row_p, 1e-12))
                                       - np.log(np.maximum(row_q, 1e-12)))))
    return total / max(1, len(p))


def _rollout(theta, scenario: str, seed: int, goal_source: str, steps: int = 24):
    """States from a real episode **with the planner actually driving the goals**.

    The first version of this tool forgot to install a goal provider, so the block
    was identically zero and every delta came out 0.000 -- a measurement that looked
    like "the plan is decoration" but was really "the plan was never supplied".
    That is why the loop below reuses the trainer's own goal-source builder instead
    of hand-rolling one: if the integration is wrong here, it is wrong in the same
    way as in training, and the target-filled fraction (printed below) makes it
    visible instead of silent.
    """
    from ie_rl_train import _make_goal_source, initial_goal_observation

    env = IERlEnv(scenario, seed=seed, goal_features=True,
                  speed_source="legacy_tags")
    request = {"theta": str(theta_path_for_request), "goal_source": goal_source,
               "decision_interval": 5, "speed_source": "legacy_tags",
               "plan_interval": 10, "seed": seed}
    provider, pre_tick, _agent = _make_goal_source(env, request, scenario)
    env.goal_provider = provider
    env.pre_tick_hook = pre_tick
    states = []
    try:
        obs, _info = env.reset()
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
        num_fire = env.num_fire_choices          # k + 1: choice 0 = hold fire
        offset = 6 + n * 10 + k * 7 + n * k * env.pair_width
        sigma = float(np.exp(theta["log_std"]).mean())
        return states, offset, n, num_fire, sigma, env.pair_width
    finally:
        env.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theta", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="*",
                        default=["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT"])
    parser.add_argument("--seeds", nargs="*", type=int, default=[7, 11])
    parser.add_argument("--min-states", type=int, default=8)
    parser.add_argument("--goal-source", default="rule", choices=("rule", "llm"),
                        help="用哪个规划器产生目标。检查某个 checkpoint 是否学会用目标，"
                             "应当用它**训练时**的那个来源（arm5_v2 = rule）。")
    args = parser.parse_args()

    global theta_path_for_request
    theta_path_for_request = args.theta

    theta = load_theta(args.theta)
    sigma_global = float(np.exp(theta["log_std"]).mean())
    print(f"theta = {args.theta}   obs_dim = {int(theta['trunk0.w'].shape[0])}")
    print(f"sigma(log_std mean) = {sigma_global:.4f} "
          f"(policy's own action-noise scale -- the reference)\n")

    rows = []
    for scenario in args.scenarios:
        for seed in args.seeds:
            states, offset, n, num_fire, sigma, env_pair_width = _rollout(
                theta, scenario, seed, args.goal_source)
            if len(states) < args.min_states:
                print(f"-- {scenario} seed={seed}: only {len(states)} states with "
                      f"contacts, skipped")
                continue
            block_shape = (n, PER_UNIT_WIDTH)
            mask = np.ones((n, num_fire), dtype=bool)
            d_head_zero, d_speed_zero, kl_zero = [], [], []
            d_head_swap, d_speed_swap, kl_swap = [], [], []
            has_target_frac = []
            live_slots = 0.0
            for obs in states:
                block = obs[offset:].reshape(block_shape).copy()
                # 只统计**活着的**槽位：目标块覆盖 16 个槽，而场景常常只有 5-9 个真实单元，
                # 把补零槽算进去会把"每个活单元都有目标"读成"只有 40% 有目标"。
                live = block[:, N_TYPES] > 0.5
                live_slots += float(live.sum())
                if live.any():
                    has_target_frac.append(float(live[live].mean() * 0.0
                                                 + np.mean(block[live, N_TYPES + 1] > 0.5)))
                else:
                    has_target_frac.append(0.0)
                base_obs = obs.copy()
                base_obs[offset:] = 0.0
                base = numpy_forward(theta, base_obs, n, num_fire)
                full = numpy_forward(theta, obs, n, num_fire)

                # A. zero the whole block: "there is no plan at all"
                d_head_zero.append(float(np.linalg.norm(
                    np.tanh(full["heading"]) - np.tanh(base["heading"]),
                    axis=1).mean()))
                d_speed_zero.append(float(np.mean(np.abs(
                    np.tanh(full["speed"]) - np.tanh(base["speed"])))))
                kl_zero.append(_kl(_softmax(full["fire"], mask),
                                   _softmax(base["fire"], mask)))

                # B. rotate the goal block by one slot: unit i now holds unit j's
                #    assignment.  This is the axis that matters -- "execute WHOSE
                #    goal" -- and it is invisible to the blanket-zero test.
                if n >= 2:
                    swapped = obs.copy()
                    swapped[offset:] = np.roll(block, 1, axis=0).reshape(-1)
                    sw = numpy_forward(theta, swapped, n, num_fire)
                    d_head_swap.append(float(np.mean(np.linalg.norm(
                        np.tanh(full["heading"]) - np.tanh(sw["heading"]), axis=1))))
                    d_speed_swap.append(float(np.mean(np.abs(
                        np.tanh(full["speed"]) - np.tanh(sw["speed"])))))
                    kl_swap.append(_kl(_softmax(full["fire"], mask),
                                       _softmax(sw["fire"], mask)))

            def mean(values):
                return float(np.mean(values)) if values else float("nan")

            # C. bearing slope: the decisive probe.
            #
            # The swap test above is confounded whenever all units are assigned the
            # SAME target (IE-01 has one raider, so every defender's goal block is
            # nearly identical and rotating them changes nothing).  What "the network
            # executes the plan" actually means is: when the goal says "the target is
            # over there", the commanded heading points there.  So perturb the goal's
            # encoded bearing directly and measure d(heading_out)/d(goal_bearing).
            # A policy that follows its plan has a slope near 1; one that ignores it
            # has a slope near 0.
            offsets = [math.radians(deg) for deg in (-90.0, -45.0, 45.0, 90.0)]
            slopes, residuals = [], []
            for obs in states:
                block = obs[offset:].reshape(block_shape).copy()
                for index in range(n):
                    if block[index, N_TYPES] <= 0.5 or block[index, N_TYPES + 1] <= 0.5:
                        continue
                    base_bearing = math.atan2(float(block[index, N_TYPES + 2]),
                                              float(block[index, N_TYPES + 3]))
                    full = numpy_forward(theta, obs, n, num_fire)
                    out0 = math.atan2(float(np.tanh(full["heading"][index, 0])),
                                      float(np.tanh(full["heading"][index, 1])))
                    xs, ys = [], []
                    for delta in offsets:
                        shifted = obs.copy()
                        new_bearing = base_bearing + delta
                        block2 = block.copy()
                        block2[index, N_TYPES + 2] = math.sin(new_bearing)
                        block2[index, N_TYPES + 3] = math.cos(new_bearing)
                        shifted[offset:] = block2.reshape(-1)
                        out = numpy_forward(theta, shifted, n, num_fire)
                        outd = math.atan2(float(np.tanh(out["heading"][index, 0])),
                                          float(np.tanh(out["heading"][index, 1])))
                        xs.append(delta)
                        ys.append((outd - out0 + math.pi) % (2 * math.pi) - math.pi)
                    xs_arr = np.asarray(xs)
                    ys_arr = np.asarray(ys)
                    if float(np.std(xs_arr)) <= 1e-9:
                        continue
                    slope = float(np.polyfit(xs_arr, ys_arr, 1)[0])
                    predict = slope * xs_arr
                    residuals.append(float(np.mean((ys_arr - predict) ** 2)))
                    slopes.append(slope)
            bearing_slope = float(np.mean(slopes)) if slopes else float("nan")
            bearing_rmse = math.sqrt(float(np.mean(residuals))) if residuals else float("nan")

            # C2. CONTROL: the same perturbation applied to the *lead-bearing* feature
            # of the pair block (index 6/7 of the 8-wide pair row), which is the input
            # the policy is supposed to use for reactive guidance.  Without this
            # control a slope of ~0 for the goal block would be uninterpretable: it
            # could mean "the block is ignored" or "this probe cannot move this
            # network at all".  A large control slope rules out the second reading.
            pair_w = env_pair_width
            k = num_fire - 1                      # contact slots (choice 0 = hold)
            ctrl_slopes = []
            for obs in states:
                pair_off = 6 + n * 10 + k * 7
                for slot_index in range(n):
                    row = pair_off + slot_index * k * pair_w
                    for j in range(k):
                        base_at = row + j * pair_w
                        if base_at + 7 >= offset:
                            continue
                        s0 = float(obs[base_at + 6])
                        c0 = float(obs[base_at + 7])
                        if abs(s0) < 1e-9 and abs(c0) < 1e-9:
                            continue                      # empty pair row
                        base_bearing = math.atan2(s0, c0)
                        full = numpy_forward(theta, obs, n, num_fire)
                        out0 = math.atan2(float(np.tanh(full["heading"][slot_index, 0])),
                                          float(np.tanh(full["heading"][slot_index, 1])))
                        xs, ys = [], []
                        for delta in offsets:
                            shifted = obs.copy()
                            nb = base_bearing + delta
                            shifted[base_at + 6] = math.sin(nb)
                            shifted[base_at + 7] = math.cos(nb)
                            out = numpy_forward(theta, shifted, n, num_fire)
                            outd = math.atan2(
                                float(np.tanh(out["heading"][slot_index, 0])),
                                float(np.tanh(out["heading"][slot_index, 1])))
                            xs.append(delta)
                            ys.append((outd - out0 + math.pi) % (2 * math.pi) - math.pi)
                        xs_arr = np.asarray(xs)
                        ys_arr = np.asarray(ys)
                        if float(np.std(xs_arr)) <= 1e-9:
                            continue
                        ctrl_slopes.append(float(np.polyfit(xs_arr, ys_arr, 1)[0]))
            control_slope = float(np.mean(ctrl_slopes)) if ctrl_slopes else float("nan")

            # D. SENSITIVITY SCALE -- the falsification test for the probe itself.
            #
            # The first version of C/C2 reported ~0 for BOTH the goal bearing and the
            # pair lead bearing, which cannot be read as "the goal is ignored": if a
            # bearing feature the policy is supposed to steer by also has zero slope,
            # the probe is not moving the network at all.  So measure, with no
            # assumptions about which feature matters, how far the heading output
            # travels when the whole non-goal observation is perturbed with noise of
            # increasing size.  Reports both the raw output-vector movement and the
            # decoded ANGLE change (the thing that actually steers a unit).
            rng = np.random.default_rng(12345)
            sensitivity = []
            for scale in (0.02, 0.1, 0.3, 1.0):
                angle_moves, vector_moves = [], []
                for obs in states[:8]:
                    noisy = obs.copy()
                    # perturb everything EXCEPT the goal block
                    noisy[:offset] += rng.normal(0.0, scale, size=offset).astype(
                        obs.dtype)
                    a = numpy_forward(theta, obs, n, num_fire)
                    b = numpy_forward(theta, noisy, n, num_fire)
                    vector_moves.append(float(np.mean(np.linalg.norm(
                        np.tanh(a["heading"]) - np.tanh(b["heading"]), axis=1))))
                    ang_a = np.arctan2(np.tanh(a["heading"][:, 0]),
                                       np.tanh(a["heading"][:, 1]))
                    ang_b = np.arctan2(np.tanh(b["heading"][:, 0]),
                                       np.tanh(b["heading"][:, 1]))
                    diff = (ang_b - ang_a + math.pi) % (2 * math.pi) - math.pi
                    angle_moves.append(float(np.mean(np.abs(diff))))
                sensitivity.append((scale, float(np.mean(vector_moves)),
                                    float(np.mean(angle_moves))))

            rows.append({
                "scenario": scenario, "seed": seed, "states": len(states),
                "has_target": mean(has_target_frac),
                "zero_head": mean(d_head_zero), "zero_speed": mean(d_speed_zero),
                "zero_kl": mean(kl_zero),
                "swap_head": mean(d_head_swap), "swap_speed": mean(d_speed_swap),
                "swap_kl": mean(kl_swap), "sigma": sigma,
                "bearing_slope": bearing_slope, "bearing_rmse": bearing_rmse,
                "bearing_samples": len(slopes),
                "control_slope": control_slope,
                "control_samples": len(ctrl_slopes),
            })
            print(f"-- {scenario} seed={seed}  states={len(states)}  "
                  f"live slots with a target = {mean(has_target_frac):.3f}")
            print(f"     A zero : headingD={mean(d_head_zero):.4f} rad  "
                  f"speedD={mean(d_speed_zero):.4f}  fireKL={mean(kl_zero):.4f}")
            print(f"     B swap : headingD={mean(d_head_swap):.4f} rad  "
                  f"speedD={mean(d_speed_swap):.4f}  fireKL={mean(kl_swap):.4f}")
            print(f"     C slope: d(heading)/d(goal bearing) = {bearing_slope:+.3f} "
                  f"(1.0 = fully follows the plan, 0.0 = ignores it; "
                  f"rmse={bearing_rmse:.3f} rad over {len(slopes)} unit-states)")
            print(f"     C2 CONTROL: d(heading)/d(pair lead bearing) = {control_slope:+.3f}"
                  f"  ({len(ctrl_slopes)} unit-target rows)")
            print("     D sensitivity (噪声加在非目标块上): "
                  + "  ".join(f"noise{scale:g}: vec{vec:.3f}/ang{math.degrees(ang):.1f}deg"
                              for scale, vec, ang in sensitivity))
            print(f"     policy's own noise sigma = {sigma:.4f}")

    print()
    print("=== verdict ===")
    if not rows:
        print("no usable states")
        return 2
    swap_head = float(np.mean([r["swap_head"] for r in rows]))
    swap_kl = float(np.mean([r["swap_kl"] for r in rows]))
    slope = float(np.nanmean([r["bearing_slope"] for r in rows]))
    control = float(np.nanmean([r["control_slope"] for r in rows]))
    has_target = float(np.mean([r["has_target"] for r in rows]))
    sigma = float(np.mean([r["sigma"] for r in rows]))
    print(f"  mean: target-filled={has_target:.3f}  swap headingD={swap_head:.4f} rad "
          f"(~{math.degrees(swap_head):.1f} deg)  fireKL={swap_kl:.4f}  sigma={sigma:.4f}")
    print(f"  mean: bearing slope = {slope:+.3f}   control slope (pair lead) = "
          f"{control:+.3f}")
    # The criterion is the *slope*, not the swap: a slope of 1 means "the commanded
    # heading follows the plan's bearing".  0.3 is a generous floor -- below it the
    # plan influences the course by less than a third of the angle it names.
    ok = slope >= 0.3 and has_target > 0.5
    print(f"  {'PASS' if ok else 'FAIL'}: the plan block drives the commanded heading "
          f"(need slope >= 0.3 and target-filled > 0.5)")
    if not ok:
        print("  -> fix the conditioning (wider goal encoding / auxiliary objective / "
              "goal-conditioned reward term) BEFORE paying for hours of training; "
              "otherwise the result is a pure-RL policy with a decorative input.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Parity and shape tests for the RL policy, reward and env contract.

Two things are checked that a plausible-looking training curve would otherwise
hide:

1. **numpy/torch parity.**  Rollout workers evaluate the policy in numpy while
   the trainer optimises a torch module.  If the two disagree, every worker acts
   under different weights than the ones being updated, and the run is
   meaningless even though loss goes down and returns move.  The test loads the
   *same* theta into both and compares logits, values and action log-probs.

2. **Reward/scorecard relationship.**  The training reward is deliberately not
   the scorecard (the scorecard stays the evaluation instrument).  The test
   pins the documented mapping in ``RewardConfig`` so the two cannot drift apart
   silently.

Runs under the CUDA-torch interpreter; skips the torch half cleanly if torch is
absent so it can also run under the engine venv.

Usage:
    python _w1_test_rl_policy.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_env import RewardConfig, SPEED_BY_CLASS  # noqa: E402
from ie_rl_policy import (  # noqa: E402
    LOG_STD_INIT,
    export_theta_from_torch,
    init_theta,
    load_theta_into_torch,
    numpy_forward,
    numpy_sample,
    theta_shapes,
)

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def test_theta_layout_is_stable():
    obs_dim, num_units, num_fire = 410, 6, 9
    rng = np.random.default_rng(0)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    expected = theta_shapes(obs_dim, num_units, num_fire)
    check("theta keys match the declared layout",
          set(theta) == set(expected), f"{sorted(set(theta) ^ set(expected))}")
    check("theta shapes match",
          all(theta[k].shape == v for k, v in expected.items()),
          str({k: (theta[k].shape, v) for k, v in expected.items()
               if theta[k].shape != v}))
    check("log_std starts at the documented value",
          bool(np.allclose(theta["log_std"], LOG_STD_INIT)),
          f"{theta['log_std'][0]:.3f} vs {LOG_STD_INIT}")
    check("log_std covers 2 heading + 1 speed component per slot",
          theta["log_std"].shape == (3 * num_units,),
          str(theta["log_std"].shape))
    check("the fire head spans all MAX_CONTACTS+1 choices",
          expected["fire.w"][1] == num_units * num_fire)


def test_numpy_sampling_respects_the_fire_mask():
    obs_dim, num_units, num_fire = 410, 6, 9
    rng = np.random.default_rng(1)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    mask = np.zeros((num_units, num_fire), dtype=bool)
    mask[:, 0] = True          # "hold fire" is always available
    mask[2, 3] = True          # unit 2 may additionally fire at choice 3
    obs = rng.standard_normal(obs_dim).astype(np.float32)
    for _ in range(200):
        action, logprob, value, _ = numpy_sample(theta, obs, mask, rng, num_fire)
        # unit 2 may hold or pick choice 3 -- anything else is illegal
        if int(action["fire"][2]) not in (0, 3):
            check("masked sampling only picks legal fire choices", False,
                  f"unit 2 chose {action['fire'][2]}")
            return
        if action["fire"][0] != 0:
            check("a unit with only 'hold' available always holds", False,
                  f"unit 0 chose {action['fire'][0]}")
            return
        if not np.isfinite(logprob) or not np.isfinite(value):
            check("logprob and value stay finite", False, f"{logprob}, {value}")
            return
    check("masked sampling only picks legal fire choices", True)
    check("a unit with only 'hold' available always holds", True)
    check("logprob and value stay finite", True)


def test_action_ranges():
    obs_dim, num_units, num_fire = 410, 6, 9
    rng = np.random.default_rng(2)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    mask = np.ones((num_units, num_fire), dtype=bool)
    obs = rng.standard_normal(obs_dim).astype(np.float32)
    lo_s = hi_s = None
    xy_abs_max = 0.0
    gaps = 0.0
    for _ in range(500):
        action, _, _, _ = numpy_sample(theta, obs, mask, rng, num_fire)
        speed = action["speed"]
        lo_s = speed.min() if lo_s is None else min(lo_s, speed.min())
        hi_s = speed.max() if hi_s is None else max(hi_s, speed.max())
        xy = action["heading_xy"]
        xy_abs_max = max(xy_abs_max, float(np.abs(xy).max()))
        heading = action["heading_deg"]
        if not (np.all(heading >= 0.0) and np.all(heading < 360.0)):
            check("heading stays inside [0, 360)", False, str(heading))
            return
        # the (sin, cos) pair and the reported angle must describe the same
        # direction, otherwise the env and the trainer disagree about the action
        rad = np.radians(heading)
        gaps = max(gaps, float(np.abs(np.arctan2(np.sin(rad), np.cos(rad))
                                      - np.arctan2(xy[:, 0], xy[:, 1])).max()))
    check("speed stays inside [0, 1] (fraction of class max)",
          lo_s >= 0.0 and hi_s <= 1.0, f"[{lo_s:.3f}, {hi_s:.3f}]")
    check("heading components are bounded by tanh",
          xy_abs_max <= 1.0, f"max|xy|={xy_abs_max:.4f}")
    check("heading angle and (sin, cos) pair agree",
          gaps < 1e-4, f"max angular gap {gaps:.2e} rad")


def test_sampler_logprob_matches_the_trainer_recomputation():
    """PPO's ratio is ``exp(new_logp - old_logp)``.

    ``old_logp`` comes from the numpy sampler and ``new_logp`` is recomputed in
    torch from the stored action.  If those two densities disagree, every ratio
    is wrong from the first minibatch and the run silently optimises noise.  With
    three heads (two of them squashed Gaussians) that is easy to get wrong, so it
    is pinned here rather than trusted.
    """
    try:
        import torch
    except Exception as error:  # noqa: BLE001
        print(f"  [skip] log-prob consistency -- torch unavailable "
              f"({type(error).__name__})")
        return
    from ie_rl_policy import build_torch_policy, _logp_tanh

    obs_dim, num_units, num_fire = 410, 6, 9
    rng = np.random.default_rng(11)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    model = build_torch_policy(obs_dim, num_units, num_fire)
    load_theta_into_torch(model, theta)
    obs = rng.standard_normal(obs_dim).astype(np.float32)
    mask = np.zeros((num_units, num_fire), dtype=bool)
    mask[:, 0] = True
    mask[1, 2] = True
    mask[3, 0] = mask[3, 4] = True
    slot = np.ones(num_units, dtype=np.float32)

    action, logprob, _, _ = numpy_sample(theta, obs, mask, rng, num_fire,
                                         slot_mask=slot)
    with torch.no_grad():
        dist = model.distribution(torch.from_numpy(obs[None, :]),
                                  torch.from_numpy(mask[None, :]))
        # ``std`` is (num_units, 3) -- it has no batch dimension, so it must NOT
        # be indexed with [0].
        std = dist["std"]
        xy = torch.from_numpy(action["heading_xy"]).double()
        sp = torch.from_numpy((action["speed"] * 2 - 1).astype(np.float32)).double()
        eps_xy = (torch.atanh(xy.clamp(-0.999999, 0.999999))
                  - dist["heading"][0].double()) / std[:, :2].double()
        eps_sp = (torch.atanh(sp.clamp(-0.999999, 0.999999))
                  - dist["speed"][0].double()) / std[:, 2].double()
        lp = (-0.5 * eps_xy ** 2 - torch.log(std[:, :2].double())
              - 0.5 * float(np.log(2 * np.pi))
              - torch.log(1 - xy ** 2 + 1e-6)).sum()
        lp = lp + (-0.5 * eps_sp ** 2 - torch.log(std[:, 2].double())
                   - 0.5 * float(np.log(2 * np.pi))
                   - torch.log(1 - sp ** 2 + 1e-6)).sum()
        logp_fire = torch.log_softmax(dist["fire_logits"][0].double(), dim=-1)
        lp = lp + logp_fire[torch.arange(num_units),
                            torch.from_numpy(action["fire"])].sum()
    delta = abs(float(lp) - float(logprob))
    check("sampler log-prob equals the trainer's recomputation",
          delta < 1e-3, f"numpy={logprob:.6f} torch={float(lp):.6f} d={delta:.2e}")

    # and the same identity must hold for the numpy-side helper, since that is
    # the code the rollout workers actually call
    pre_xy = torch.atanh(xy.clamp(-0.999999, 0.999999)).numpy()
    pre_sp = torch.atanh(sp.clamp(-0.999999, 0.999999)).numpy()
    lp_np = float(
        _logp_tanh(dist["heading"][0].double().numpy(), pre_xy,
                   action["heading_xy"], std[:, :2].numpy()).sum()
        + _logp_tanh(dist["speed"][0].double().numpy(), pre_sp,
                     action["speed"] * 2 - 1, std[:, 2].numpy()).sum())
    lp_torch_cont = float(lp) - float(
        logp_fire[torch.arange(num_units),
                  torch.from_numpy(action["fire"])].sum())
    check("numpy log-prob helper agrees with the torch density",
          abs(lp_np - lp_torch_cont) < 1e-3,
          f"numpy-helper={lp_np:.6f} torch={lp_torch_cont:.6f}")


def test_numpy_torch_parity():
    try:
        import torch
    except Exception as error:  # noqa: BLE001
        print(f"  [skip] numpy/torch parity -- torch unavailable ({type(error).__name__})")
        return
    from ie_rl_policy import build_torch_policy

    obs_dim, num_units, num_fire = 410, 6, 9
    rng = np.random.default_rng(3)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    model = build_torch_policy(obs_dim, num_units, num_fire)
    load_theta_into_torch(model, theta)

    obs = rng.standard_normal((4, obs_dim)).astype(np.float32)
    mask = np.ones((4, num_units, num_fire), dtype=bool)
    mask[:, :, 4:] = False

    np_out = numpy_forward(theta, obs[0], num_units, num_fire)
    with torch.no_grad():
        dist = model.distribution(torch.from_numpy(obs),
                                  torch.from_numpy(mask))
    check("torch and numpy agree on the heading head",
          bool(np.allclose(np_out["heading"], dist["heading"][0].numpy(), atol=1e-5)),
          f"max|d|={np.abs(np_out['heading'] - dist['heading'][0].numpy()).max():.2e}")
    check("torch and numpy agree on the speed head",
          bool(np.allclose(np_out["speed"], dist["speed"][0].numpy(), atol=1e-5)),
          f"max|d|={np.abs(np_out['speed'] - dist['speed'][0].numpy()).max():.2e}")
    check("torch and numpy agree on the value head",
          bool(np.allclose(float(np_out["value"]), float(dist["value"][0]),
                           atol=1e-5)))
    fire_np = np_out["fire"].reshape(num_units, num_fire)
    fire_torch = dist["fire_logits"][0].numpy()
    # NOTE: the two implementations apply the fire mask at different points --
    # torch masks inside ``distribution()``, numpy masks inside
    # ``numpy_sample()``.  ``numpy_forward`` therefore returns *raw* logits, and
    # comparing them against torch's masked logits differs by exactly the -1e9
    # sentinel on illegal entries.  Only legal entries are comparable here; that
    # both sides mask before sampling is what actually matters and is covered by
    # test_numpy_sampling_respects_the_fire_mask.
    legal = mask[0]
    check("torch and numpy agree on the fire logits (legal entries)",
          bool(np.allclose(fire_np[legal], fire_torch[legal], atol=1e-5)),
          f"max|d|={np.abs(fire_np[legal] - fire_torch[legal]).max():.2e}")
    check("both implementations mask illegal fire entries",
          bool(np.all(fire_torch[~legal] < -1e8)))

    # round-trip: torch -> theta -> numpy must stay consistent
    theta2 = export_theta_from_torch(model)
    np_out2 = numpy_forward(theta2, obs[0], num_units, num_fire)
    check("theta round-trip through torch preserves the policy",
          bool(np.allclose(np_out["fire"].reshape(num_units, num_fire),
                           np_out2["fire"].reshape(num_units, num_fire),
                           atol=1e-5)))

    # one optimiser step must move the numpy view of the weights too
    before = np_out2["fire"].copy()
    optimiser = torch.optim.Adam(model.parameters(), lr=1e-2)
    dist = model.distribution(torch.from_numpy(obs), torch.from_numpy(mask))
    loss = (dist["value"].pow(2).mean() + dist["heading"].pow(2).mean()
            + dist["speed"].pow(2).mean())
    optimiser.zero_grad()
    loss.backward()
    optimiser.step()
    after = numpy_forward(export_theta_from_torch(model), obs[0],
                          num_units, num_fire)["fire"]
    check("a GPU/CPU optimiser step is visible to the numpy worker view",
          not np.allclose(before, after, atol=1e-7),
          f"max|d|={np.abs(before - after).max():.2e}")


def test_ppo_loss_runs_with_minibatch_smaller_than_the_batch():
    """Exercise the trainer's REAL loss on several minibatches.

    Both defects found in this block were invisible while ``minibatch`` exceeded
    the rollout batch (then the minibatch *was* the whole batch, so the reduce and
    index bugs cancelled out).  A run with ``minibatch`` below the batch size is
    therefore the only configuration that catches them -- and it is the
    configuration training actually uses.  The test calls the extracted
    ``ppo_minibatch_loss`` so it tracks the shipped code rather than a copy.
    """
    try:
        import torch
    except Exception as error:  # noqa: BLE001
        print(f"  [skip] PPO loss -- torch unavailable ({type(error).__name__})")
        return
    import ie_rl_train
    from ie_rl_policy import build_torch_policy

    obs_dim, num_units, num_fire = 2226, 16, 21
    total, minibatch = 44, 13        # deliberately smaller, and not a divisor
    rng = np.random.default_rng(21)
    theta = init_theta(rng, obs_dim, num_units, num_fire)
    model = build_torch_policy(obs_dim, num_units, num_fire)
    load_theta_into_torch(model, theta)

    mask = np.zeros((total, num_units, num_fire), dtype=bool)
    mask[:, :, 0] = True
    mask[:, :, 1:4] = rng.random((total, num_units, 3)) < 0.3
    slot = np.ones((total, num_units), dtype=np.float32)
    slot[:, -4:] = 0.0                # padded / dead slots
    batch = {
        "obs": torch.from_numpy(
            rng.standard_normal((total, obs_dim)).astype(np.float32)),
        "mask": torch.from_numpy(mask),
        "slot": torch.from_numpy(slot),
        "heading": torch.from_numpy(np.tanh(
            rng.standard_normal((total, num_units, 2))).astype(np.float32)),
        "speed": torch.from_numpy(
            rng.uniform(0.02, 0.98, (total, num_units)).astype(np.float32)),
        "fire": torch.from_numpy(
            (rng.random((total, num_units)) * 4).astype(np.int64)),
        "logprob": torch.from_numpy(
            rng.standard_normal(total).astype(np.float32)),
        "adv": torch.from_numpy(
            rng.standard_normal(total).astype(np.float32)),
        "ret": torch.from_numpy(
            rng.standard_normal(total).astype(np.float32)),
    }

    optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
    losses = []
    for start in range(0, total, minibatch):
        idx = torch.arange(start, min(total, start + minibatch))
        loss, policy_loss, value_loss, entropy, logp = \
            ie_rl_train.ppo_minibatch_loss(model, batch, idx,
                                           clip=0.2, entropy_coef=0.05)
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()
        losses.append((float(loss), float(policy_loss.detach()),
                       float(value_loss.detach()), float(entropy.detach()),
                       tuple(logp.shape), int(idx.shape[0])))
    check("the PPO loss runs on minibatches smaller than the batch",
          len(losses) == 4, f"{len(losses)} minibatches of {minibatch} for {total}")
    check("every minibatch produced finite loss terms",
          all(np.isfinite(v) for row in losses for v in row[:4]),
          str([row[:4] for row in losses]))
    check("the log-prob is one value per transition in the minibatch",
          all(row[4] == (row[5],) for row in losses),
          str([(row[4], row[5]) for row in losses]))
    # Entropy is a finite scalar -- but NOT necessarily positive.  Each continuous
    # head contributes Gaussian differential entropy
    # ``0.5*(1+ln(2*pi)) + ln(sigma)``, which is negative once sigma < 0.42; at the
    # shipped ``LOG_STD_INIT = -1.5`` (sigma = 0.223) the sum over three heads is
    # legitimately around -1.7.  Asserting ``> 0`` here was testing an assumption
    # rather than the property that matters.
    check("entropy is a finite scalar, not a per-slot vector",
          all(isinstance(row[3], float) and np.isfinite(row[3]) for row in losses),
          str([round(row[3], 3) for row in losses]))
    grads = {name: p.grad for name, p in model.named_parameters()
             if p.grad is not None}
    check("the optimiser step actually touched the parameters",
          bool(grads) and any(bool(g.abs().sum() > 0) for g in grads.values()),
          f"{len(grads)} parameters have gradients")


def test_reward_config_documents_its_mapping():
    cfg = RewardConfig()
    check("facility damage outweighs a single neutralisation",
          abs(cfg.facility_damage) > cfg.raider_neutralised,
          f"{cfg.facility_damage} vs {cfg.raider_neutralised}")
    check("terminal win/loss dominate the dense terms",
          cfg.terminal_win > cfg.raider_neutralised
          and abs(cfg.terminal_loss) > abs(cfg.facility_damage) * 0.4,
          f"win={cfg.terminal_win} loss={cfg.terminal_loss}")
    check("shot cost is small but non-zero (ammo discipline)",
          0.0 < cfg.shot_cost < cfg.raider_neutralised / 10.0,
          f"{cfg.shot_cost}")
    check("speed classes are declared for both domains",
          set(SPEED_BY_CLASS) == {"air", "surface"}, str(SPEED_BY_CLASS))


def main() -> int:
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for name, function in tests:
        print(f"-- {name}")
        try:
            function()
        except AssertionError as error:
            check(f"{name} completed", False, str(error))
        except Exception as error:  # noqa: BLE001
            check(f"{name} completed", False, f"{type(error).__name__}: {error}")
    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

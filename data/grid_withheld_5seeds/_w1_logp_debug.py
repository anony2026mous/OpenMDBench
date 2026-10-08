"""Localise which head's log-prob density disagrees between the numpy sampler
and the torch recomputation used by the PPO loss."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ie_rl_policy import (  # noqa: E402
    _logp_tanh,
    build_torch_policy,
    init_theta,
    load_theta_into_torch,
    numpy_forward,
    numpy_sample,
)

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

import torch  # noqa: E402

with torch.no_grad():
    dist = model.distribution(torch.from_numpy(obs[None, :]),
                              torch.from_numpy(mask[None, :]))
    std = dist["std"]
    xy = torch.from_numpy(action["heading_xy"]).double()
    sp = torch.from_numpy((action["speed_mps"] * 2 - 1).astype(np.float32)).double()
    pre_xy = torch.atanh(xy.clamp(-0.999999, 0.999999))
    pre_sp = torch.atanh(sp.clamp(-0.999999, 0.999999))
    eps_xy = (pre_xy - dist["heading"][0].double()) / std[:, :2].double()
    eps_sp = (pre_sp - dist["speed"][0].double()) / std[:, 2].double()

    gauss_xy = (-0.5 * eps_xy ** 2 - torch.log(std[:, :2].double())
                - 0.5 * float(np.log(2 * np.pi)))
    jac_xy_t = -torch.log(1 - xy ** 2 + 1e-6)
    jac_xy_np = -np.log(np.maximum(1.0 - action["heading_xy"] ** 2, 1e-6))
    gauss_sp = (-0.5 * eps_sp ** 2 - torch.log(std[:, 2].double())
                - 0.5 * float(np.log(2 * np.pi)))
    jac_sp_t = -torch.log(1 - sp ** 2 + 1e-6)
    jac_sp_np = -np.log(np.maximum(1.0 - (action["speed_mps"] * 2 - 1) ** 2, 1e-6))

    logp_fire_t = torch.log_softmax(dist["fire_logits"][0].double(), dim=-1)
    fire_t = logp_fire_t[torch.arange(num_units),
                         torch.from_numpy(action["fire"])]

    # numpy recomputation of the fire term, exactly as numpy_sample does it
    raw = numpy_forward(theta, obs, num_units, num_fire)["fire"]
    lg = np.where(mask, raw, -1e9)
    lg = lg - lg.max(axis=1, keepdims=True)
    pr = np.exp(lg)
    pr /= pr.sum(axis=1, keepdims=True)
    fire_np = np.log(pr[np.arange(num_units), action["fire"]] + 1e-12)

print("component                    numpy        torch        diff")
rows = {
    "heading gauss": (float(_logp_tanh(pre_xy.numpy(),
                                       action["heading_xy"],
                                       std[:, :2].numpy()).sum()), 0.0),
    "heading jac": (float(jac_xy_np.sum()), float(jac_xy_t.sum())),
    "speed gauss": (0.0, 0.0),
    "speed jac": (float(jac_sp_np.sum()), float(jac_sp_t.sum())),
    "value": (0.0, 0.0),
}
gn_xy = float(_logp_tanh(pre_xy.numpy(), action["heading_xy"],
                         std[:, :2].numpy()).sum())
gt_xy = float((gauss_xy + jac_xy_t).sum())
gn_sp = float(_logp_tanh(pre_sp.numpy(), action["speed_mps"] * 2 - 1,
                         std[:, 2].numpy()).sum())
gt_sp = float((gauss_sp + jac_sp_t).sum())
print(f"{'heading total':<24}{gn_xy:>12.6f}{gt_xy:>13.6f}{gn_xy-gt_xy:>12.3e}")
print(f"{'speed total':<24}{gn_sp:>12.6f}{gt_sp:>13.6f}{gn_sp-gt_sp:>12.3e}")
print(f"{'fire total':<24}{float(fire_np.sum()):>12.6f}"
      f"{float(fire_t.sum()):>13.6f}{float(fire_np.sum()-fire_t.sum()):>12.3e}")
print(f"{'TOTAL':<24}{logprob:>12.6f}"
      f"{float(gn_xy and 0)+(gt_xy+gt_sp+float(fire_t.sum())):>13.6f}")
print()
print("std[:, :2] =\n", std[:, :2].numpy())
print("log_std     =", theta["log_std"].reshape(num_units, 3)[:, 0])
print("torch log_std =", model.log_std.reshape(num_units, 3)[:, 0].detach().numpy())
print()
print("squashed heading_xy max|.| =", float(np.abs(action["heading_xy"]).max()))
print("speed_frac range            =", float(action["speed_mps"].min()),
      float(action["speed_mps"].max()))
print("heading mean diff =",
      np.abs(dist["heading"][0].numpy()
             - numpy_forward(theta, obs, num_units, num_fire)["heading"]).max())
print("speed mean diff   =",
      np.abs(dist["speed"][0].numpy()
             - numpy_forward(theta, obs, num_units, num_fire)["speed"]).max())

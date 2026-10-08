"""Reproduce the entropy-term shape failure using the real calibration buffers."""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_policy import build_torch_policy, init_theta, load_theta_into_torch  # noqa: E402

import torch  # noqa: E402

paths = sorted(glob.glob(str(HERE / "_w1_runs" / "rl" / "rollout_calib1_*.npz")))
batches = []
for path in paths:
    with np.load(path) as handle:
        batches.append({k: handle[k] for k in handle.files})
data = {key: np.concatenate([b[key] for b in batches], axis=0) for key in batches[0]}
print("transitions per worker:", [b["reward"].shape[0] for b in batches])
for key in sorted(data):
    print(f"  merged {key:<12} {data[key].shape}")

obs_dim = data["obs"].shape[1]
num_units = data["slot"].shape[1]
num_fire = data["mask"].shape[2]
print(f"obs_dim={obs_dim} num_units={num_units} num_fire={num_fire}")

theta = init_theta(np.random.default_rng(0), obs_dim, num_units, num_fire)
model = build_torch_policy(obs_dim, num_units, num_fire)
load_theta_into_torch(model, theta)

obs = torch.from_numpy(data["obs"])
mask = torch.from_numpy(data["mask"])
slot = torch.from_numpy(data["slot"])
head = torch.from_numpy(data["heading"])
spd = torch.from_numpy(data["speed"])
fire = torch.from_numpy(data["fire"])

dist = model.distribution(obs, mask)
print("dist heading", tuple(dist["heading"].shape))
print("dist speed  ", tuple(dist["speed"].shape))
print("dist logits ", tuple(dist["fire_logits"].shape))
print("dist std    ", tuple(dist["std"].shape))
print("slot        ", tuple(slot.shape))

logits = dist["fire_logits"]
probs = torch.softmax(logits, dim=-1)
ent_fire = -(probs * torch.log(probs + 1e-9)).sum(-1)
print("probs       ", tuple(probs.shape))
print("ent_fire    ", tuple(ent_fire.shape))
print("slot        ", tuple(slot.shape))
try:
    product = ent_fire * slot
    print("ent_fire*slot OK", tuple(product.shape))
except RuntimeError as error:
    print("ent_fire*slot FAILED:", error)

# --- replicate the trainer's block verbatim, with a minibatch slice --------
print()
args_clip = 0.2
total = obs.shape[0]
minibatch = 1024
perm = torch.randperm(total)
start = 0
idx = perm[start:start + minibatch]
sub = model.distribution(obs[idx], mask[idx])
std_xy = sub["std"][:, :2] + 1e-6
std_sp = sub["std"][:, 2] + 1e-6
head_c = head[idx].clamp(-0.999999, 0.999999)
spd_sq = (spd[idx] * 2 - 1).clamp(-0.999999, 0.999999)
logits = sub["fire_logits"]
print("idx          ", tuple(idx.shape))
print("sub heading  ", tuple(sub["heading"].shape))
print("sub std      ", tuple(sub["std"].shape))
print("std_xy       ", tuple(std_xy.shape))
print("std_sp       ", tuple(std_sp.shape))
print("head_c       ", tuple(head_c.shape))
print("spd_sq       ", tuple(spd_sq.shape))
print("logits       ", tuple(logits.shape))
print("slot[idx]    ", tuple(slot[idx].shape))

from ie_rl_train import _log_gauss, _log_gauss_entropy  # noqa: E402

eps_xy = (torch.atanh(head_c) - sub["heading"]) / std_xy
eps_sp = (torch.atanh(spd_sq) - sub["speed"]) / std_sp
logp = ((_log_gauss(eps_xy, std_xy) - torch.log(1 - head_c ** 2 + 1e-6))
        * slot[idx].unsqueeze(-1)).sum((-1, -2))
logp = logp + ((_log_gauss(eps_sp, std_sp) - torch.log(1 - spd_sq ** 2 + 1e-6))
               * slot[idx]).sum(-1)
logp = logp + (torch.log_softmax(logits, dim=-1).gather(
    -1, fire[idx].unsqueeze(-1)).squeeze(-1) * slot[idx]).sum(-1)
print("logp OK      ", tuple(logp.shape))

probs = torch.softmax(logits, dim=-1)
ent_fire = -(probs * torch.log(probs + 1e-9)).sum(-1)
ent_xy = (_log_gauss_entropy(std_xy) + torch.log(1 - head_c ** 2 + 1e-6))
ent_sp = (_log_gauss_entropy(std_sp) + torch.log(1 - spd_sq ** 2 + 1e-6))
print("ent_fire     ", tuple(ent_fire.shape))
print("ent_xy       ", tuple(ent_xy.shape))
print("ent_sp       ", tuple(ent_sp.shape))
for label, expr in (
        ("ent_fire * slot[idx]", lambda: ent_fire * slot[idx]),
        ("ent_xy * slot.unsq  ", lambda: ent_xy * slot[idx].unsqueeze(-1)),
        ("ent_sp * slot[idx]  ", lambda: ent_sp * slot[idx]),
):
    try:
        print(f"{label} OK   ", tuple(expr().shape))
    except RuntimeError as error:
        print(f"{label} FAILED: {error}")

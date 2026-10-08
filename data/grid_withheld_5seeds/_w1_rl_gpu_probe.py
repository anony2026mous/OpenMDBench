"""Measure how much the GPU is actually used by the PPO update (or not).

Motivation: the training loop runs rollouts in CPU subprocess workers (the
simulator is Taichi/CPU-bound) and only the gradient update on the GPU.  With a
(410 -> 256 -> 256) MLP and ~400 transitions per update, the update is a few
milliseconds of GPU work per ~76 s of rollout, i.e. a GPU duty cycle near zero.
``nvidia-smi`` therefore shows 3-4% utilisation and a flat 44 C, which is
exactly what an operator would (correctly) call "not really training on the
GPU".

This script quantifies it: it times the same update on CPU and on CUDA, reports
peak VRAM, and prints the duty cycle implied by the measured rollout time.  Run
it before claiming "training uses the GPU".

Usage:
    python _w1_rl_gpu_probe.py [--obs-dim 410] [--units 6] [--fire 9]
        [--transitions 422] [--epochs 4]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs-dim", type=int, default=410)
    parser.add_argument("--units", type=int, default=6)
    parser.add_argument("--fire", type=int, default=9)
    parser.add_argument("--transitions", type=int, default=422)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatch", type=int, default=1024)
    parser.add_argument("--rollout-seconds", type=float, default=76.0,
                        help="实测每轮 rollout 采集耗时，用于算占空比")
    args = parser.parse_args()

    import torch

    from ie_rl_policy import build_torch_policy, init_theta, load_theta_into_torch

    rng = np.random.default_rng(0)
    theta = init_theta(rng, args.obs_dim, args.units, args.fire)
    total = args.transitions

    obs_np = rng.standard_normal((total, args.obs_dim)).astype(np.float32)
    mask_np = np.ones((total, args.units, args.fire), dtype=bool)
    head_np = np.tanh(rng.standard_normal((total, args.units, 2))).astype(np.float32)
    spd_np = rng.uniform(0.05, 0.95, (total, args.units)).astype(np.float32)
    fire_np = rng.integers(0, args.fire, (total, args.units)).astype(np.int64)
    slot_np = np.ones((total, args.units), dtype=np.float32)
    old_lp_np = rng.standard_normal(total).astype(np.float32)
    adv_np = rng.standard_normal(total).astype(np.float32)
    ret_np = rng.standard_normal(total).astype(np.float32)

    print(f"batch: transitions={total} obs_dim={args.obs_dim} "
          f"units={args.units} fire={args.fire} epochs={args.epochs}")
    print(f"{'device':<8}{'update_s':>10}{'per_epoch_ms':>14}{'peak_VRAM_MB':>14}")
    print("-" * 46)

    results = {}
    for device_name in ("cpu", "cuda"):
        if device_name == "cuda" and not torch.cuda.is_available():
            print("cuda     (unavailable)")
            continue
        device = torch.device(device_name)
        model = build_torch_policy(args.obs_dim, args.units, args.fire).to(device)
        load_theta_into_torch(model, theta)
        optimiser = torch.optim.Adam(model.parameters(), lr=3e-4)

        obs = torch.from_numpy(obs_np).to(device)
        mask = torch.from_numpy(mask_np).to(device)
        head = torch.from_numpy(head_np).to(device)
        spd = torch.from_numpy(spd_np).to(device)
        fire = torch.from_numpy(fire_np).to(device)
        slot = torch.from_numpy(slot_np).to(device)
        old_lp = torch.from_numpy(old_lp_np).to(device)
        adv = torch.from_numpy(adv_np).to(device)
        ret = torch.from_numpy(ret_np).to(device)

        if device_name == "cuda":
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        started = time.perf_counter()
        for _epoch in range(args.epochs):
            perm = torch.randperm(total, device=device)
            for start in range(0, total, args.minibatch):
                idx = perm[start:start + args.minibatch]
                dist = model.distribution(obs[idx], mask[idx])
                std = dist["std"]
                a_xy = head[idx].clamp(-0.999999, 0.999999)
                a_sp = (spd[idx] * 2 - 1).clamp(-0.999999, 0.999999)
                logp = ((-0.5 * ((torch.atanh(a_xy) - dist["heading"])
                                 / (std[:, :2] + 1e-6)) ** 2
                         - torch.log(std[:, :2] + 1e-6)
                         - torch.log(1 - a_xy ** 2 + 1e-6))
                        * slot[idx].unsqueeze(-1)).sum((-1, -2))
                logp = logp + ((-0.5 * ((torch.atanh(a_sp) - dist["speed"])
                                        / (std[:, 2] + 1e-6)) ** 2
                                - torch.log(std[:, 2] + 1e-6)
                                - torch.log(1 - a_sp ** 2 + 1e-6))
                               * slot[idx]).sum(-1)
                # ``dist`` is already the minibatch; re-indexing with the global
                # ``idx`` is out of bounds once minibatch < batch.
                logits = dist["fire_logits"]
                logp = logp + torch.log_softmax(logits, dim=-1).gather(
                    -1, fire[idx].unsqueeze(-1)).squeeze(-1).sum(-1)
                ratio = torch.exp(logp - old_lp[idx])
                surr1 = ratio * adv[idx]
                surr2 = torch.clamp(ratio, 0.8, 1.2) * adv[idx]
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = ((dist["value"] - ret[idx]) ** 2).mean()
                loss = policy_loss + 0.5 * value_loss
                optimiser.zero_grad()
                loss.backward()
                optimiser.step()
        if device_name == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        peak = (torch.cuda.max_memory_allocated() / 1e6
                if device_name == "cuda" else 0.0)
        results[device_name] = elapsed
        print(f"{device_name:<8}{elapsed:>10.4f}{elapsed/args.epochs*1000:>14.2f}"
              f"{peak:>14.1f}")

    if "cuda" in results:
        duty = results["cuda"] / max(1e-9, args.rollout_seconds + results["cuda"])
        print()
        print(f"GPU 占空比 = {results['cuda']:.4f}s / "
              f"({args.rollout_seconds:.1f}s rollout + {results['cuda']:.4f}s update) "
              f"= {duty*100:.3f}%")
        print("结论：更新确实在 GPU 上执行，但以当前网络规模与 batch，"
              "GPU 在整轮里几乎全程空闲 —— 瓶颈是 CPU 仿真。")
        if "cpu" in results:
            print(f"CPU/GPU 更新耗时比 = {results['cpu']/max(1e-9, results['cuda']):.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

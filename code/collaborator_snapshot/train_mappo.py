"""
OpenMDBench v2 — MAPPO training script (CTDE, H.8 System A).

Trains the goal-conditioned MAPPO policy on the v2 grid environment:
  - Team-level GAE (shared team reward; per-timestep advantage copied to
    each alive unit's sample — standard MAPPO simplification)
  - Centralized critic over ground-truth global state (CTDE)
  - Action masking for the UAV (no INTERCEPT)
  - Random GOAI-goal injection curriculum: ~50% of episodes receive
    periodic random upper-layer directives, so the SAME policy works
    both unconditioned (pure-RL evaluation) and goal-conditioned
    (hybrid executor via GOAIExecutor.controller)

Usage:
    python train_mappo.py --difficulty simple --seed 42 --total_steps 5000000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.agents.mappo_agent import (
    MAPPOAgent, encode_unit_obs, build_global_state,
    OBS_DIM, ACT_DIM, GSTATE_DIM, GOAL_TYPE_LIST,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class RunningMeanStd:
    """Welford running mean/var for reward normalization."""

    def __init__(self, epsilon: float = 1e-4):
        self.mean, self.var, self.count = 0.0, 1.0, epsilon

    def update(self, x: float):
        delta = x - self.mean
        total = self.count + 1
        self.mean += delta / total
        self.var = (self.var * self.count + delta * (x - self.mean)) / total
        self.count = total


class TeamRollout:
    """Rollout storage: team sequences per env + flattened unit samples."""

    def __init__(self):
        # flattened unit samples (parallel lists)
        self.f_obs: list = []
        self.f_mask: list = []
        self.f_gstate: list = []
        self.f_action: list = []
        self.f_logp: list = []
        self.f_env: list = []
        self.f_t: list = []
        # team sequences per env: {env_idx: {"values": [], "rewards": [], "dones": []}}
        self.team: dict = {}

    def add(self, env_idx: int, value: float, reward: float, done: bool,
            unit_samples: list):
        """unit_samples: list of (obs, mask, gstate, action, logp) per unit.

        t is the position within this rollout's per-env sequence
        (episodes spanning rollouts are cut by the done flag in GAE)."""
        seq = self.team.setdefault(env_idx, {"values": [], "rewards": [],
                                             "dones": []})
        t = len(seq["values"])
        seq["values"].append(value)
        seq["rewards"].append(reward)
        seq["dones"].append(done)
        for obs, mask, gstate, action, logp in unit_samples:
            self.f_obs.append(obs)
            self.f_mask.append(mask)
            self.f_gstate.append(gstate)
            self.f_action.append(action)
            self.f_logp.append(logp)
            self.f_env.append(env_idx)
            self.f_t.append(t)

    def compute_team_gae(self, bootstrap: dict, gamma: float, lam: float):
        """Per-env team GAE; writes advantages/returns onto the samples."""
        self.f_adv = np.zeros(len(self.f_obs), dtype=np.float32)
        self.f_ret = np.zeros(len(self.f_obs), dtype=np.float32)
        for env_idx, seq in self.team.items():
            T = len(seq["rewards"])
            adv = np.zeros(T, dtype=np.float32)
            last_gae = 0.0
            for t in reversed(range(T)):
                next_v = bootstrap.get(env_idx, 0.0) if t == T - 1 \
                    else seq["values"][t + 1]
                non_terminal = 1.0 - float(seq["dones"][t])
                delta = (seq["rewards"][t] + gamma * next_v * non_terminal
                         - seq["values"][t])
                last_gae = delta + gamma * lam * non_terminal * last_gae
                adv[t] = last_gae
            ret = adv + np.asarray(seq["values"], dtype=np.float32)
            # copy team advantage/return onto this env's samples
            idxs = [i for i, e in enumerate(self.f_env) if e == env_idx]
            for i in idxs:
                self.f_adv[i] = adv[self.f_t[i]]
                self.f_ret[i] = ret[self.f_t[i]]

    def clear(self):
        self.__init__()


# ---------------------------------------------------------------------------
# Random GOAI-goal injection (curriculum for goal-conditioned execution)
# ---------------------------------------------------------------------------

def random_directive(env: GridEnv, rng: np.random.RandomState,
                     guided_uav_prob: float = 0.5) -> dict:
    """Random H.4 upper-layer directive for goal-conditioning exposure."""
    usvs = [uid for uid in env.blue_units
            if env.entities[uid].unit_kind == "usv"]
    uav = env.blue_units[-1] if env.blue_units else None
    assignments = []
    for uid in usvs:
        task = rng.choice(["patrol", "intercept", "track", "hold", "return"],
                          p=[0.3, 0.3, 0.15, 0.15, 0.1])
        a = {"unit_id": uid, "task": str(task)}
        if task == "patrol":
            a["sector"] = str(rng.choice(["east", "south", "north",
                                          "west", "center"]))
        assignments.append(a)
    payload = {"unit_assignments": assignments}
    if uav and rng.rand() < guided_uav_prob:
        reds = [uid for uid in env.red_units
                if env.entities[uid].alive
                and env.entities[uid].entity_type.value == 2]
        if reds:
            payload["uav_lock_assignments"] = [
                {"unit_id": uav, "target_id": reds[rng.randint(len(reds))]}
            ]
            # also give the UAV a task so its subgoal is consistent
            payload["unit_assignments"].append(
                {"unit_id": uav, "task": "track"})
    return payload


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------

class MAPPOTrainer:
    def __init__(
        self,
        difficulty: str = "simple",
        seed: int = 42,
        total_steps: int = 5_000_000,
        steps_per_rollout: int = 4096,
        num_envs: int = 8,
        ppo_epochs: int = 4,
        batch_size: int = 512,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_eps: float = 0.2,
        vf_coef: float = 0.5,
        ent_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        eval_interval: int = 100_000,
        save_dir: str = "checkpoints",
        device: str = "auto",
        goal_inject_prob: float = 0.5,
        goal_inject_period: int = 20,
        task_mode: str = "continuous",
        init_from: str = None,
    ):
        self.difficulty, self.seed = difficulty, seed
        self.task_mode = task_mode
        self.total_steps = total_steps
        self.steps_per_rollout = steps_per_rollout
        self.num_envs = num_envs
        self.ppo_epochs, self.batch_size = ppo_epochs, batch_size
        self.lr, self.gamma, self.gae_lambda = lr, gamma, gae_lambda
        self.clip_eps, self.vf_coef, self.ent_coef = clip_eps, vf_coef, ent_coef
        self.max_grad_norm = max_grad_norm
        self.eval_interval = eval_interval
        self.save_dir = save_dir
        self.goal_inject_prob = goal_inject_prob
        self.goal_inject_period = goal_inject_period

        self.device = torch.device(
            "cuda" if device == "auto" and torch.cuda.is_available()
            else ("cuda" if device == "cuda" else "cpu"))

        os.makedirs(save_dir, exist_ok=True)
        torch.manual_seed(seed)
        np.random.seed(seed)
        self.rng = np.random.RandomState(seed)

        self.agent = MAPPOAgent(role="blue", seed=seed)
        if init_from:
            # curriculum warm start: load weights only (fresh optimizer,
            # step counter starts at 0) — e.g. medium best -> complex run
            self.agent.load_checkpoint(init_from)
            print(f"[curriculum] initialized from {init_from}")
        self.agent.actor.to(self.device)
        self.agent.critic.to(self.device)
        self.optimizer = torch.optim.Adam(
            list(self.agent.actor.parameters()) + list(self.agent.critic.parameters()),
            lr=lr, eps=1e-5)

        self.envs = [GridEnv(difficulty=difficulty, seed=seed + 1000 + i,
                             task_mode=task_mode)
                     for i in range(num_envs)]
        self.env_rngs = [np.random.RandomState(seed + 2000 + i)
                         for i in range(num_envs)]
        self.guided = [bool(r.rand() < goal_inject_prob) for r in self.env_rngs]

        self.total_timesteps = 0
        self.reward_rms = RunningMeanStd()
        self.training_history: list = []

    # -- rollout ----------------------------------------------------------

    def _act_batch(self, env: GridEnv):
        """Sample actions for all alive blue units. Returns
        (actions dict, unit_samples list, team_value float, gstate)."""
        alive = [uid for uid in env.blue_units if env.entities[uid].alive]
        if not alive:
            return {}, [], 0.0, None

        obs_list, mask_list = [], []
        for uid in alive:
            obs, mask = encode_unit_obs(env, uid)
            obs_list.append(obs)
            mask_list.append(mask)

        gstate = build_global_state(env)
        obs_t = torch.as_tensor(np.stack(obs_list), device=self.device)
        mask_t = torch.as_tensor(np.stack(mask_list), device=self.device)
        gs_t = torch.as_tensor(gstate, device=self.device).unsqueeze(0)

        with torch.no_grad():
            dist = self.agent.actor(obs_t, mask_t)
            actions = dist.sample()
            logps = dist.log_prob(actions)
            value = self.agent.critic(gs_t).item()

        actions = actions.tolist()
        logps = logps.tolist()
        samples = [
            (obs_list[i], mask_list[i], gstate, actions[i], logps[i])
            for i in range(len(alive))
        ]
        return dict(zip(alive, actions)), samples, value, gstate

    def collect_rollout(self, buf: TeamRollout) -> dict:
        buf.clear()
        ep_returns, ep_lengths, ep_wins = [], [], []
        cur_ret = [0.0] * self.num_envs
        cur_len = [0] * self.num_envs
        steps = 0

        while steps < self.steps_per_rollout:
            for env_idx, env in enumerate(self.envs):
                if env.done:
                    ep_returns.append(cur_ret[env_idx])
                    ep_lengths.append(cur_len[env_idx])
                    ep_wins.append(float(env.winner == "blue"))
                    cur_ret[env_idx], cur_len[env_idx] = 0.0, 0
                    env.reset()
                    # re-roll guided episode
                    self.guided[env_idx] = bool(
                        self.env_rngs[env_idx].rand() < self.goal_inject_prob)

                # goal-injection curriculum
                if (self.guided[env_idx]
                        and cur_len[env_idx] % self.goal_inject_period == 0):
                    env.set_upper_action(
                        random_directive(env, self.env_rngs[env_idx]))

                actions, samples, team_value, _ = self._act_batch(env)
                if not actions:
                    env.reset()
                    continue

                env.step(actions, None)
                reward = env.compute_reward(role="blue")
                self.reward_rms.update(reward)
                reward = float(np.clip(
                    reward / (np.sqrt(self.reward_rms.var) + 1e-8), -10, 10))

                buf.add(env_idx, team_value, reward, env.done, samples)
                cur_ret[env_idx] += reward
                cur_len[env_idx] += 1
                steps += 1
                self.total_timesteps += 1
                if steps >= self.steps_per_rollout:
                    break

        # bootstrap values for truncation (episode continues past rollout)
        bootstrap = {}
        for env_idx, env in enumerate(self.envs):
            alive = [uid for uid in env.blue_units if env.entities[uid].alive]
            if alive and not env.done:
                gs = build_global_state(env)
                with torch.no_grad():
                    bootstrap[env_idx] = self.agent.critic(
                        torch.as_tensor(gs, device=self.device)
                        .unsqueeze(0)).item()
        buf.compute_team_gae(bootstrap, self.gamma, self.gae_lambda)

        return {"episode_returns": ep_returns, "episode_lengths": ep_lengths,
                "episode_wins": ep_wins, "steps": steps}

    # -- update -----------------------------------------------------------

    def ppo_update(self, buf: TeamRollout) -> dict:
        n = len(buf.f_obs)
        if n == 0:
            return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        obs = torch.as_tensor(np.stack(buf.f_obs), device=self.device)
        mask = torch.as_tensor(np.stack(buf.f_mask), device=self.device)
        gstate = torch.as_tensor(np.stack(buf.f_gstate), device=self.device)
        act = torch.as_tensor(buf.f_action, dtype=torch.long, device=self.device)
        old_logp = torch.as_tensor(buf.f_logp, dtype=torch.float32,
                                   device=self.device)
        adv = torch.as_tensor(buf.f_adv, device=self.device)
        ret = torch.as_tensor(buf.f_ret, device=self.device)

        stats = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        updates = 0
        idx_base = np.arange(n)

        for _ in range(self.ppo_epochs):
            perm = self.rng.permutation(n)
            for start in range(0, n, self.batch_size):
                idx = idx_base[perm[start:start + self.batch_size]]
                if len(idx) == 0:
                    continue

                dist = self.agent.actor(obs[idx], mask[idx])
                new_logp = dist.log_prob(act[idx])
                entropy = dist.entropy().mean()
                values = self.agent.critic(gstate[idx])

                a = adv[idx]
                a = (a - a.mean()) / (a.std() + 1e-8)
                ratio = torch.exp(new_logp - old_logp[idx])
                s1 = ratio * a
                s2 = torch.clamp(ratio, 1 - self.clip_eps,
                                 1 + self.clip_eps) * a
                policy_loss = -torch.min(s1, s2).mean()
                value_loss = 0.5 * (values - ret[idx]).pow(2).mean()
                loss = policy_loss + self.vf_coef * value_loss \
                    - self.ent_coef * entropy

                if not torch.isfinite(loss):
                    self.optimizer.zero_grad()
                    continue

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(
                    list(self.agent.actor.parameters())
                    + list(self.agent.critic.parameters()),
                    self.max_grad_norm)
                self.optimizer.step()

                stats["policy_loss"] += policy_loss.item()
                stats["value_loss"] += value_loss.item()
                stats["entropy"] += entropy.item()
                updates += 1

        for k in stats:
            stats[k] /= max(updates, 1)
        return stats

    # -- eval -------------------------------------------------------------

    def evaluate(self, num_episodes: int = 10) -> dict:
        env = GridEnv(difficulty=self.difficulty, seed=self.seed + 9999,
                      task_mode=self.task_mode)
        rewards, succ, lens = [], [], []
        for _ in range(num_episodes):
            env.reset()
            total, steps = 0.0, 0
            while not env.done and steps < MAX_STEPS:
                alive = [uid for uid in env.blue_units
                         if env.entities[uid].alive]
                if not alive:
                    break
                actions = {}
                for uid in alive:
                    obs, m = encode_unit_obs(env, uid)
                    with torch.no_grad():
                        dist = self.agent.actor(
                            torch.as_tensor(obs).unsqueeze(0).to(self.device),
                            torch.as_tensor(m).unsqueeze(0).to(self.device))
                        actions[uid] = int(dist.probs.argmax(dim=-1).item())
                env.step(actions, None)
                total += env.compute_reward(role="blue")
                steps += 1
            m = env.get_episode_metrics()
            rewards.append(total)
            succ.append(float(m["mission_success"]))
            lens.append(steps)
        return {"success_rate": float(np.mean(succ)),
                "mean_reward": float(np.mean(rewards)),
                "mean_length": float(np.mean(lens))}

    # -- main loop ----------------------------------------------------------

    def train(self) -> MAPPOAgent:
        print(f"Training MAPPO (CTDE) on {self.difficulty}, seed {self.seed}, "
              f"task_mode={self.task_mode}, "
              f"goal_inject_prob={self.goal_inject_prob}")
        print(f"  total_steps={self.total_steps:,}  rollout={self.steps_per_rollout}"
              f"  envs={self.num_envs}  device={self.device}")
        buf = TeamRollout()
        best_sr = -1.0
        t0 = time.time()

        while self.total_timesteps < self.total_steps:
            info = self.collect_rollout(buf)
            upd = self.ppo_update(buf)

            wins = info["episode_wins"]
            mean_ret = float(np.mean(info["episode_returns"][-20:])) if wins else 0.0
            winrate = float(np.mean(wins[-20:])) if wins else 0.0

            if self.total_timesteps % 20000 < self.steps_per_rollout:
                print(f"  step {self.total_timesteps:>10,} | "
                      f"ret {mean_ret:8.2f} | win {winrate:5.1%} | "
                      f"pi {upd['policy_loss']:7.4f} | "
                      f"vf {upd['value_loss']:8.4f} | "
                      f"H {upd['entropy']:.3f} | "
                      f"{time.time() - t0:6.0f}s", flush=True)

            if self.total_timesteps % self.eval_interval < self.steps_per_rollout:
                ev = self.evaluate(10)
                self.training_history.append({
                    "step": self.total_timesteps, **ev,
                    "policy_loss": upd["policy_loss"],
                    "value_loss": upd["value_loss"],
                    "entropy": upd["entropy"],
                    "time": time.time() - t0,
                })
                print(f"\n  *** EVAL @ {self.total_timesteps:,}: "
                      f"SR={ev['success_rate']:.0%} "
                      f"R={ev['mean_reward']:.1f} "
                      f"L={ev['mean_length']:.0f} ***\n", flush=True)
                if ev["success_rate"] > best_sr:
                    best_sr = ev["success_rate"]
                    self.agent.save_checkpoint(self._ckpt("best"),
                                               {"difficulty": self.difficulty,
                                                "seed": self.seed,
                                                "eval_success_rate": best_sr})
                    print(f"      >> best checkpoint (SR={best_sr:.0%})")

        final = self.evaluate(20)
        self.agent.save_checkpoint(self._ckpt("final"),
                                   {"difficulty": self.difficulty,
                                    "seed": self.seed, **final})
        with open(os.path.join(
                self.save_dir,
                os.path.basename(self._ckpt("history")).replace("_history.pt", "_history.json")),
                "w") as f:
            json.dump(self.training_history, f, indent=2)
        print(f"\nFinal: SR={final['success_rate']:.0%} "
              f"R={final['mean_reward']:.1f} — saved "
              f"{self._ckpt('final')} ({time.time() - t0:.0f}s)")
        return self.agent

    def _ckpt(self, tag: str) -> str:
        # continuous + goal-conditioned keeps the canonical v2 name; other
        # task modes / the monolithic (--no-goals) variant get explicit tags
        suffix = ""
        if self.task_mode != "continuous":
            suffix += f"_tm-{self.task_mode}"
        if self.goal_inject_prob <= 0.0:
            suffix += "_mono"
        return os.path.join(
            self.save_dir,
            f"mappo_{self.difficulty}{suffix}_s{self.seed}_{tag}.pt")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Train MAPPO (CTDE) for grid v2")
    p.add_argument("--difficulty", default="simple",
                   choices=["simple", "medium", "complex"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--total_steps", type=int, default=5_000_000)
    p.add_argument("--num_envs", type=int, default=8)
    p.add_argument("--steps_per_rollout", type=int, default=4096)
    p.add_argument("--batch_size", type=int, default=512)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--eval_interval", type=int, default=100_000)
    p.add_argument("--save_dir", default="checkpoints")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--task_mode", default="continuous",
                   choices=["independent", "sequential", "continuous"],
                   help="§4.5 coupling manipulation: independent/sequential/"
                        "continuous standoff-engagement gate")
    p.add_argument("--no-goals", action="store_true",
                   help="monolithic variant: disable goal-injection curriculum")
    p.add_argument("--init_from", default=None,
                   help="curriculum warm start: load actor/critic weights "
                        "from this checkpoint (e.g. medium best for a "
                        "complex run)")
    args = p.parse_args()

    trainer = MAPPOTrainer(
        difficulty=args.difficulty, seed=args.seed,
        total_steps=args.total_steps, num_envs=args.num_envs,
        steps_per_rollout=args.steps_per_rollout, batch_size=args.batch_size,
        lr=args.lr, eval_interval=args.eval_interval, save_dir=args.save_dir,
        device=args.device, task_mode=args.task_mode,
        goal_inject_prob=0.0 if args.no_goals else 0.5,
        init_from=args.init_from)
    trainer.train()


if __name__ == "__main__":
    main()

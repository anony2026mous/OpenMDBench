"""
OpenMDBench — PPO Training Script (PyTorch)

Trains the PPO agent (MAPPO-style with parameter sharing) on the
grid environment.  Uses:
  - PyTorch for automatic differentiation
  - Clipped PPO objective
  - GAE(λ) advantage estimation
  - Mini-batch updates
  - Adam optimizer
  - Checkpoint saving

Usage:
    python train_ppo.py --difficulty simple --total_steps 500000
    python train_ppo.py --difficulty complex --total_steps 2000000
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
import torch.optim as optim

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_env.grid_env import GridEnv, MAX_STEPS, DIFFICULTY_CONFIG
from grid_env.agents.ppo_agent import PPOAgent, ActorCritic


# ---------------------------------------------------------------------------
# Running statistics (for reward normalization / stability)
# ---------------------------------------------------------------------------

class RunningMeanStd:
    """Welford-style running mean/variance tracker."""

    def __init__(self, epsilon: float = 1e-4):
        self.mean = 0.0
        self.var = 1.0
        self.count = epsilon

    def update(self, x: float):
        batch_mean = x
        batch_var = 0.0
        batch_count = 1
        delta = batch_mean - self.mean
        total_count = self.count + batch_count
        new_mean = self.mean + delta * batch_count / total_count
        m_a = self.var * self.count
        m_b = batch_var * batch_count
        m2 = m_a + m_b + delta ** 2 * self.count * batch_count / total_count
        self.mean = new_mean
        self.var = m2 / total_count
        self.count = total_count


# ---------------------------------------------------------------------------
# Rollout Buffer
# ---------------------------------------------------------------------------

class RolloutBuffer:
    """Stores rollout data for PPO updates."""

    def __init__(self):
        self.observations = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.advantages = []
        self.returns = []

    def add(self, obs, action, reward, value, log_prob, done):
        self.observations.append(obs)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)

    def compute_gae(self, last_value: float, gamma: float = 0.99, gae_lambda: float = 0.95):
        """Compute GAE advantages and returns."""
        T = len(self.rewards)
        advantages = np.zeros(T, dtype=np.float32)
        last_gae = 0.0

        for t in reversed(range(T)):
            if t == T - 1:
                next_value = last_value
            else:
                next_value = self.values[t + 1]

            next_non_terminal = 1.0 - float(self.dones[t])
            delta = self.rewards[t] + gamma * next_value * next_non_terminal - self.values[t]
            last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
            advantages[t] = last_gae

        self.advantages = advantages
        self.returns = advantages + np.array(self.values, dtype=np.float32)

    def get_batches(self, batch_size: int):
        """Yield random mini-batches as torch tensors."""
        n = len(self.observations)
        indices = np.random.permutation(n)

        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_idx = indices[start:end]

            yield {
                "obs": torch.as_tensor(np.array([self.observations[i] for i in batch_idx]), dtype=torch.float32),
                "actions": torch.as_tensor(np.array([self.actions[i] for i in batch_idx]), dtype=torch.long),
                "old_log_probs": torch.as_tensor(np.array([self.log_probs[i] for i in batch_idx]), dtype=torch.float32),
                "advantages": torch.as_tensor(self.advantages[batch_idx], dtype=torch.float32),
                "returns": torch.as_tensor(self.returns[batch_idx], dtype=torch.float32),
            }

    def clear(self):
        self.__init__()


# ---------------------------------------------------------------------------
# PPO Trainer
# ---------------------------------------------------------------------------

class PPOTrainer:
    """
    PPO trainer for the grid environment (PyTorch).
    """

    def __init__(
        self,
        difficulty: str = "simple",
        seed: int = 42,
        total_steps: int = 2_000_000,
        steps_per_rollout: int = 2048,
        num_envs: int = 4,
        ppo_epochs: int = 4,
        batch_size: int = 256,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_eps: float = 0.2,
        vf_coef: float = 0.5,
        ent_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        eval_interval: int = 50_000,
        save_dir: str = "checkpoints",
    ):
        self.difficulty = difficulty
        self.seed = seed
        self.total_steps = total_steps
        self.steps_per_rollout = steps_per_rollout
        self.num_envs = num_envs
        self.ppo_epochs = ppo_epochs
        self.batch_size = batch_size
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_eps = clip_eps
        self.vf_coef = vf_coef
        self.ent_coef = ent_coef
        self.max_grad_norm = max_grad_norm
        self.eval_interval = eval_interval
        self.save_dir = save_dir

        os.makedirs(save_dir, exist_ok=True)

        # Set seed
        torch.manual_seed(seed)
        np.random.seed(seed)

        # Create agent
        self.agent = PPOAgent(role="blue", seed=seed, trained=False)
        self.model = self.agent.model

        # Create optimizer
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr, eps=1e-5)

        # Create parallel environments
        self.envs = [
            GridEnv(difficulty=difficulty, seed=seed + i)
            for i in range(num_envs)
        ]

        # Training state
        self.total_timesteps = 0
        self.episode_rewards = []
        self.episode_lengths = []
        self.training_history = []

        # Reward normalization (stability: keeps value targets O(1))
        self.reward_rms = RunningMeanStd()

    def _get_obs_vector(self, env: GridEnv, uid: str) -> np.ndarray:
        """Get the 29-dim observation vector for a unit."""
        local_obs = env.get_local_observation(uid)
        grid = local_obs["grid"].flatten()    # 25
        own_state = local_obs["own_state"]    # 4
        return np.concatenate([grid, own_state]).astype(np.float32)

    def _get_alive_friendly(self, env: GridEnv) -> list:
        """Get list of alive friendly unit IDs."""
        return [
            uid for uid, e in env.entities.items()
            if e.alive and e.team == "blue"
        ]

    def collect_rollout(self, buffer: RolloutBuffer) -> dict:
        """Collect rollout data from parallel environments."""
        buffer.clear()
        env_steps = 0
        episode_returns = []
        episode_lengths = []

        # Reset all envs
        for env in self.envs:
            env.reset()

        current_returns = [0.0] * self.num_envs
        current_lengths = [0] * self.num_envs

        while env_steps < self.steps_per_rollout:
            for env_idx, env in enumerate(self.envs):
                if env.done:
                    episode_returns.append(current_returns[env_idx])
                    episode_lengths.append(current_lengths[env_idx])
                    current_returns[env_idx] = 0.0
                    current_lengths[env_idx] = 0
                    env.reset()

                friendly = self._get_alive_friendly(env)
                if not friendly:
                    env.reset()
                    continue

                # Collect actions for ALL alive units
                unit_data = []
                blue_actions = {}
                for uid in friendly:
                    obs = self._get_obs_vector(env, uid)
                    action, value = self.agent.get_action_and_value(obs, deterministic=False)
                    # Get log_prob from model
                    obs_t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)
                    action_t = torch.as_tensor([action], dtype=torch.long)
                    dist, _ = self.model(obs_t)
                    log_prob = dist.log_prob(action_t).item()

                    blue_actions[uid] = action
                    unit_data.append((obs, action, value, log_prob))

                # Step environment ONCE with joint action
                obs_after = env.step(blue_actions, {})
                reward = env.compute_reward(role="blue")
                done = env.done

                # Normalize reward for stable value-function training
                self.reward_rms.update(reward)
                reward = reward / (np.sqrt(self.reward_rms.var) + 1e-8)
                reward = float(np.clip(reward, -10.0, 10.0))

                # Record one sample per alive unit (all share the same reward)
                for obs, action, value, log_prob in unit_data:
                    buffer.add(obs, action, reward, value, log_prob, done)

                current_returns[env_idx] += reward
                current_lengths[env_idx] += 1
                env_steps += 1
                self.total_timesteps += 1

                if env_steps >= self.steps_per_rollout:
                    break

        # Compute GAE with last value
        last_env = self.envs[0]
        last_friendly = self._get_alive_friendly(last_env)
        if last_friendly:
            last_obs = self._get_obs_vector(last_env, last_friendly[0])
            last_value = self.agent.get_value(last_obs)
        else:
            last_value = 0.0

        buffer.compute_gae(last_value, self.gamma, self.gae_lambda)

        return {
            "episode_returns": episode_returns,
            "episode_lengths": episode_lengths,
            "steps": env_steps,
        }

    def ppo_update(self, buffer: RolloutBuffer) -> dict:
        """Perform PPO update using PyTorch autograd."""
        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        num_updates = 0

        for epoch in range(self.ppo_epochs):
            for batch in buffer.get_batches(self.batch_size):
                obs = batch["obs"]
                actions = batch["actions"]
                old_log_probs = batch["old_log_probs"]
                advantages = batch["advantages"]
                returns = batch["returns"]

                # Normalize advantages
                adv_mean = advantages.mean()
                adv_std = advantages.std() + 1e-8
                norm_advantages = (advantages - adv_mean) / adv_std

                # Forward pass
                new_log_probs, values, entropy = self.model.evaluate_actions(obs, actions)

                # PPO clipped objective
                ratio = torch.exp(new_log_probs - old_log_probs)
                surr1 = ratio * norm_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_eps, 1 + self.clip_eps) * norm_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss
                value_loss = 0.5 * (values - returns).pow(2).mean()

                # Total loss
                loss = policy_loss + self.vf_coef * value_loss - self.ent_coef * entropy

                # NaN guard: skip corrupt updates instead of poisoning weights
                if not torch.isfinite(loss):
                    self.optimizer.zero_grad()
                    continue

                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()
                num_updates += 1

        n = max(num_updates, 1)
        return {
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "entropy": total_entropy / n,
            "num_updates": num_updates,
        }

    def evaluate(self, num_episodes: int = 10) -> dict:
        """Evaluate the current policy."""
        env = GridEnv(difficulty=self.difficulty, seed=self.seed + 999)
        rewards = []
        successes = []
        lengths = []

        for ep in range(num_episodes):
            env.reset()
            total_reward = 0.0
            steps = 0

            while not env.done and steps < MAX_STEPS:
                friendly = self._get_alive_friendly(env)
                if not friendly:
                    break

                actions = {}
                for uid in friendly:
                    obs = self._get_obs_vector(env, uid)
                    action, _ = self.agent.get_action_and_value(obs, deterministic=True)
                    actions[uid] = action

                env.step(actions, {})
                total_reward += env.compute_reward(role="blue")
                steps += 1

            metrics = env.get_episode_metrics()
            rewards.append(total_reward)
            successes.append(float(metrics.get("mission_success", False)))
            lengths.append(steps)

        return {
            "mean_reward": float(np.mean(rewards)),
            "success_rate": float(np.mean(successes)),
            "mean_length": float(np.mean(lengths)),
            "std_reward": float(np.std(rewards)),
        }

    def train(self) -> PPOAgent:
        """Main training loop."""
        print(f"Training PPO on {self.difficulty} difficulty")
        print(f"  Total steps: {self.total_steps:,}")
        print(f"  Rollout size: {self.steps_per_rollout}")
        print(f"  Parallel envs: {self.num_envs}")
        print(f"  PPO epochs: {self.ppo_epochs}")
        print(f"  Learning rate: {self.lr}")
        print()

        buffer = RolloutBuffer()
        best_success_rate = 0.0
        start_time = time.time()

        while self.total_timesteps < self.total_steps:
            # Collect rollout
            rollout_info = self.collect_rollout(buffer)

            # PPO update
            update_info = self.ppo_update(buffer)

            # Logging
            ep_returns = rollout_info["episode_returns"]
            if ep_returns:
                mean_ep_return = np.mean(ep_returns[-20:])
            else:
                mean_ep_return = 0.0

            if self.total_timesteps % 10000 < self.steps_per_rollout:
                elapsed = time.time() - start_time
                print(f"  Step {self.total_timesteps:>10,} | "
                      f"Ep Ret: {mean_ep_return:>7.2f} | "
                      f"Policy Loss: {update_info['policy_loss']:.4f} | "
                      f"Value Loss: {update_info['value_loss']:.4f} | "
                      f"Entropy: {update_info['entropy']:.3f} | "
                      f"Time: {elapsed:.0f}s")

            # Evaluate periodically
            if self.total_timesteps % self.eval_interval < self.steps_per_rollout:
                eval_info = self.evaluate(num_episodes=10)
                elapsed = time.time() - start_time

                self.training_history.append({
                    "step": self.total_timesteps,
                    "eval_success_rate": eval_info["success_rate"],
                    "eval_mean_reward": eval_info["mean_reward"],
                    "policy_loss": float(update_info["policy_loss"]),
                    "value_loss": float(update_info["value_loss"]),
                    "entropy": float(update_info["entropy"]),
                    "time": elapsed,
                })

                print(f"\n  *** EVALUATION @ step {self.total_timesteps:,} ***")
                print(f"      Success Rate: {eval_info['success_rate']:.1%}")
                print(f"      Mean Reward:  {eval_info['mean_reward']:.2f}")
                print(f"      Mean Length:  {eval_info['mean_length']:.1f}\n")

                # Save best checkpoint
                if eval_info["success_rate"] > best_success_rate:
                    best_success_rate = eval_info["success_rate"]
                    ckpt_path = os.path.join(
                        self.save_dir,
                        f"ppo_{self.difficulty}_best.pt"
                    )
                    self.agent.save_checkpoint(ckpt_path)
                    print(f"      >> Saved best checkpoint (SR={best_success_rate:.1%})")

        # Final evaluation
        print("\n=== FINAL EVALUATION ===")
        final_eval = self.evaluate(num_episodes=20)
        print(f"  Success Rate: {final_eval['success_rate']:.1%}")
        print(f"  Mean Reward:  {final_eval['mean_reward']:.2f}")
        print(f"  Mean Length:  {final_eval['mean_length']:.1f}")

        # Save final checkpoint
        final_path = os.path.join(self.save_dir, f"ppo_{self.difficulty}_final.pt")
        self.agent.save_checkpoint(final_path)
        print(f"  Saved final checkpoint: {final_path}")

        # Save training history
        history_path = os.path.join(self.save_dir, f"training_{self.difficulty}.json")
        with open(history_path, "w") as f:
            json.dump(self.training_history, f, indent=2)

        total_time = time.time() - start_time
        print(f"\n  Total training time: {total_time:.1f}s")

        return self.agent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train PPO agent for grid environment")
    parser.add_argument("--difficulty", type=str, default="simple",
                        choices=["simple", "medium", "complex"])
    parser.add_argument("--total_steps", type=int, default=2_000_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num_envs", type=int, default=4)
    parser.add_argument("--steps_per_rollout", type=int, default=2048)
    parser.add_argument("--ppo_epochs", type=int, default=4)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--save_dir", type=str, default="checkpoints")
    args = parser.parse_args()

    trainer = PPOTrainer(
        difficulty=args.difficulty,
        seed=args.seed,
        total_steps=args.total_steps,
        num_envs=args.num_envs,
        steps_per_rollout=args.steps_per_rollout,
        ppo_epochs=args.ppo_epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        save_dir=args.save_dir,
    )

    agent = trainer.train()
    print(f"\nTraining complete for {args.difficulty} difficulty.")


if __name__ == "__main__":
    main()

"""
OpenMDBench — Training Script for Grid Concept Validation

Trains the RL component (PureRLAgent) using policy gradient (REINFORCE)
on the grid environment.  Supports all three difficulty tiers.

Usage:
    python train.py --difficulty simple --seed 42 --total_steps 5000000
    python train.py --difficulty medium --seed 42
    python train.py --difficulty complex --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from typing import Dict, List

import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_env.grid_env import GridEnv, Direction
from grid_env.agents.pure_rl_agent import PureRLAgent
from grid_env.agents.rule_agent import RuleAgent


def collect_rollout(env: GridEnv, agent: PureRLAgent, max_steps: int = 150) -> dict:
    """
    Collect a single rollout (episode) using the current policy.

    Returns:
        Dict with observations, actions, rewards, and metrics.
    """
    obs = env.reset()
    observations = []
    actions_list = []
    rewards = []

    for step in range(max_steps):
        # Get actions from agent
        agent_actions = agent.act(obs, env=env)

        # Record local observations for each unit
        for uid in agent_actions:
            local_obs = env.get_local_observation(uid)
            grid_flat = local_obs["grid"].flatten()
            own_state = local_obs["own_state"]
            x = np.concatenate([grid_flat, own_state])
            observations.append(x)
            actions_list.append(agent_actions[uid])

        # Step environment
        blue_actions = agent_actions
        obs = env.step(blue_actions)

        # Compute reward
        reward = env.compute_reward(role="blue")
        rewards.append(reward)

        if env.done:
            break

    # Compute returns (discounted cumulative rewards)
    gamma = 0.99
    returns = []
    G = 0
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)
    returns = np.array(returns, dtype=np.float32)

    # Normalize advantages
    if len(returns) > 1:
        advantages = (returns - returns.mean()) / (returns.std() + 1e-8)
    else:
        advantages = returns

    # Match observations and actions to returns
    # Each step may have multiple units, so we need to map correctly
    obs_batch = np.array(observations[:len(advantages)])
    action_batch = np.array(actions_list[:len(advantages)])

    # Repeat advantages for each unit in each step
    # (simplified: assign same advantage to all units in a step)
    if len(obs_batch) > len(advantages):
        # Repeat advantages to match
        repeat_factor = len(obs_batch) // max(len(advantages), 1)
        advantages = np.repeat(advantages[:len(obs_batch) // max(repeat_factor, 1)], repeat_factor)
        advantages = advantages[:len(obs_batch)]

    metrics = env.get_episode_metrics()

    return {
        "observations": obs_batch,
        "actions": action_batch,
        "advantages": advantages,
        "metrics": metrics,
        "total_reward": sum(rewards),
    }


def train(
    difficulty: str = "simple",
    seed: int = 42,
    total_steps: int = 5_000_000,
    lr: float = 1e-3,
    eval_interval: int = 100,
    save_interval: int = 500,
    output_dir: str = "checkpoints",
):
    """
    Train the RL agent using policy gradient.

    Args:
        difficulty: "simple" | "medium" | "complex"
        seed: random seed
        total_steps: total training steps
        lr: learning rate
        eval_interval: evaluate every N episodes
        save_interval: save checkpoint every N episodes
        output_dir: directory for checkpoints and logs
    """
    os.makedirs(output_dir, exist_ok=True)

    env = GridEnv(difficulty=difficulty, seed=seed)
    agent = PureRLAgent(role="blue", seed=seed, trained=False)

    print(f"Training PureRLAgent on difficulty={difficulty}, seed={seed}")
    print(f"Total steps: {total_steps:,}")
    print(f"Output: {output_dir}")

    episode = 0
    total_env_steps = 0
    best_success_rate = 0.0
    history = []

    start_time = time.time()

    while total_env_steps < total_steps:
        # Collect rollout
        rollout = collect_rollout(env, agent)
        episode += 1
        total_env_steps += env.step_count

        # Train
        if len(rollout["observations"]) > 0:
            loss = agent.train_step(
                rollout["observations"],
                rollout["actions"],
                rollout["advantages"],
                lr=lr,
            )
        else:
            loss = 0.0

        metrics = rollout["metrics"]

        # Decay exploration
        agent.epsilon = max(0.01, 0.1 * (1 - total_env_steps / total_steps))

        # Logging
        if episode % 10 == 0:
            elapsed = time.time() - start_time
            print(
                f"Episode {episode:5d} | "
                f"Steps {total_env_steps:8d}/{total_steps:,} | "
                f"Reward {rollout['total_reward']:7.1f} | "
                f"Success {metrics['mission_success']} | "
                f"Intercepted {metrics['red_intercepted']} | "
                f"Loss {loss:.4f} | "
                f"Eps {agent.epsilon:.3f} | "
                f"Time {elapsed:.0f}s"
            )

        # Evaluation
        if episode % eval_interval == 0:
            eval_metrics = evaluate_agent(env, agent, n_episodes=10)
            success_rate = eval_metrics["success_rate"]
            print(f"\n--- Evaluation (ep {episode}) ---")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Avg intercepts: {eval_metrics['avg_intercepts']:.1f}")
            print(f"  Avg civilian violations: {eval_metrics['avg_civilian_violations']:.1f}")
            print()

            if success_rate > best_success_rate:
                best_success_rate = success_rate
                save_path = os.path.join(output_dir, f"best_{difficulty}_seed{seed}.npz")
                np.savez(
                    save_path,
                    W1=agent.W1, b1=agent.b1,
                    W2=agent.W2, b2=agent.b2,
                )
                print(f"  Saved best model (success_rate={success_rate:.1%})")

        # Save checkpoint
        if episode % save_interval == 0:
            save_path = os.path.join(output_dir, f"checkpoint_{difficulty}_seed{seed}_ep{episode}.npz")
            np.savez(
                save_path,
                W1=agent.W1, b1=agent.b1,
                W2=agent.W2, b2=agent.b2,
            )

        history.append({
            "episode": episode,
            "total_steps": total_env_steps,
            "reward": rollout["total_reward"],
            "success": metrics["mission_success"],
            "loss": loss,
        })

    # Save final model
    save_path = os.path.join(output_dir, f"final_{difficulty}_seed{seed}.npz")
    np.savez(
        save_path,
        W1=agent.W1, b1=agent.b1,
        W2=agent.W2, b2=agent.b2,
    )

    # Save training history
    history_path = os.path.join(output_dir, f"history_{difficulty}_seed{seed}.json")
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nTraining complete. Total episodes: {episode}, Steps: {total_env_steps:,}")
    print(f"Best success rate: {best_success_rate:.1%}")


def evaluate_agent(env: GridEnv, agent: PureRLAgent, n_episodes: int = 10) -> dict:
    """Evaluate agent over multiple episodes."""
    results = {
        "successes": 0,
        "total_intercepts": 0,
        "total_civilian_violations": 0,
        "total_rewards": [],
    }

    for ep in range(n_episodes):
        rollout = collect_rollout(env, agent)
        metrics = rollout["metrics"]
        results["successes"] += int(metrics["mission_success"])
        results["total_intercepts"] += metrics["red_intercepted"]
        results["total_civilian_violations"] += metrics["civilian_intercepted"]
        results["total_rewards"].append(rollout["total_reward"])

    return {
        "success_rate": results["successes"] / n_episodes,
        "avg_intercepts": results["total_intercepts"] / n_episodes,
        "avg_civilian_violations": results["total_civilian_violations"] / n_episodes,
        "avg_reward": np.mean(results["total_rewards"]),
    }


def main():
    parser = argparse.ArgumentParser(description="Train RL agent for OpenMDBench grid env")
    parser.add_argument("--difficulty", type=str, default="simple",
                        choices=["simple", "medium", "complex"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--total_steps", type=int, default=5_000_000)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--eval_interval", type=int, default=100)
    parser.add_argument("--save_interval", type=int, default=500)
    parser.add_argument("--output_dir", type=str, default="checkpoints")
    args = parser.parse_args()

    train(
        difficulty=args.difficulty,
        seed=args.seed,
        total_steps=args.total_steps,
        lr=args.lr,
        eval_interval=args.eval_interval,
        save_interval=args.save_interval,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()

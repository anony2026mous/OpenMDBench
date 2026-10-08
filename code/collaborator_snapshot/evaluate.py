"""
OpenMDBench — Evaluation Script for Grid Concept Validation

Runs all 4 agent configurations across all difficulty tiers,
collects metrics, and produces summary statistics.

Usage:
    python evaluate.py --episodes 50 --seeds 5
    python evaluate.py --agent hybrid --difficulty complex --episodes 50
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.agents.pure_rl_agent import PureRLAgent
from grid_env.agents.pure_llm_agent import PureLLMAgent
from grid_env.agents.hybrid_agent import HybridAgent
from grid_env.agents.rule_agent import RuleAgent


AGENT_CONFIGS = {
    "pure_rl": {
        "class": PureRLAgent,
        "kwargs": {"trained": False},
        "label": "A: Pure RL (MAPPO)",
    },
    "pure_llm": {
        "class": PureLLMAgent,
        "kwargs": {"backend": "mock"},
        "label": "B: Pure LLM",
    },
    "hybrid": {
        "class": HybridAgent,
        "kwargs": {"llm_backend": "mock", "planner_interval": 10},
        "label": "C: Hybrid (LLM + RL)",
    },
    "rule": {
        "class": RuleAgent,
        "kwargs": {},
        "label": "D: Rule + RL",
    },
}

DIFFICULTIES = ["simple", "medium", "complex"]


def run_episode(
    env: GridEnv,
    agent,
    seed: int,
) -> dict:
    """Run a single episode and return metrics."""
    env.reset(seed=seed)
    agent.reset()

    for step in range(MAX_STEPS):
        obs = env._get_observation()
        actions = agent.act(obs, env=env)
        env.step(actions)

        if env.done:
            break

    metrics = env.get_episode_metrics()
    metrics["agent"] = agent.name
    metrics["seed"] = seed
    metrics["difficulty"] = env.difficulty
    return metrics


def evaluate_agent(
    agent_name: str,
    difficulty: str,
    episodes: int = 50,
    seeds: List[int] = None,
    llm_backend: str = "mock",
) -> List[dict]:
    """Evaluate a single agent on a single difficulty tier."""
    config = AGENT_CONFIGS[agent_name]
    kwargs = dict(config["kwargs"])

    # Override LLM backend if specified
    if "llm_backend" in kwargs:
        kwargs["llm_backend"] = llm_backend
    if "backend" in kwargs:
        kwargs["backend"] = llm_backend

    results = []
    for ep in range(episodes):
        seed = seeds[ep] if seeds else 42 + ep
        env = GridEnv(difficulty=difficulty, seed=seed)
        agent = config["class"](role="blue", seed=seed, **kwargs)
        metrics = run_episode(env, agent, seed)
        results.append(metrics)

    return results


def compute_summary(results: List[dict]) -> dict:
    """Compute summary statistics from a list of episode results."""
    if not results:
        return {}

    n = len(results)
    success_rates = [r["mission_success"] for r in results]
    blue_scores = [r["blue_score"] for r in results]
    intercepts = [r["red_intercepted"] for r in results]
    civilian_violations = [r["civilian_intercepted"] for r in results]
    port_penetrations = [r["port_penetrations"] for r in results]

    return {
        "n_episodes": n,
        "success_rate_mean": np.mean(success_rates),
        "success_rate_std": np.std(success_rates),
        "success_rate_ci95": (
            np.mean(success_rates) - 1.96 * np.std(success_rates) / np.sqrt(n),
            np.mean(success_rates) + 1.96 * np.std(success_rates) / np.sqrt(n),
        ),
        "blue_score_mean": np.mean(blue_scores),
        "blue_score_std": np.std(blue_scores),
        "avg_intercepts": np.mean(intercepts),
        "avg_civilian_violations": np.mean(civilian_violations),
        "avg_port_penetrations": np.mean(port_penetrations),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate agents for OpenMDBench grid env")
    parser.add_argument("--agent", type=str, default=None,
                        help="Agent to evaluate (default: all)")
    parser.add_argument("--difficulty", type=str, default=None,
                        help="Difficulty tier (default: all)")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--llm_backend", type=str, default="mock")
    parser.add_argument("--output_dir", type=str, default="results")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    agents = [args.agent] if args.agent else list(AGENT_CONFIGS.keys())
    difficulties = [args.difficulty] if args.difficulty else DIFFICULTIES
    seed_list = list(range(42, 42 + args.seeds))

    all_results = {}

    for agent_name in agents:
        for difficulty in difficulties:
            print(f"\n{'='*60}")
            print(f"Evaluating {AGENT_CONFIGS[agent_name]['label']} on {difficulty}")
            print(f"{'='*60}")

            start = time.time()
            results = evaluate_agent(
                agent_name, difficulty,
                episodes=args.episodes,
                seeds=seed_list * (args.episodes // args.seeds + 1),
                llm_backend=args.llm_backend,
            )
            elapsed = time.time() - start

            summary = compute_summary(results)
            key = f"{agent_name}_{difficulty}"
            all_results[key] = {
                "agent": agent_name,
                "difficulty": difficulty,
                "summary": summary,
                "episodes": results,
            }

            print(f"  Success rate: {summary['success_rate_mean']:.1%} "
                  f"(±{summary['success_rate_std']:.1%})")
            print(f"  Blue score:   {summary['blue_score_mean']:.3f} "
                  f"(±{summary['blue_score_std']:.3f})")
            print(f"  Avg intercepts: {summary['avg_intercepts']:.1f}")
            print(f"  Avg civilian violations: {summary['avg_civilian_violations']:.1f}")
            print(f"  Time: {elapsed:.1f}s")

    # Save results
    output_path = os.path.join(args.output_dir, "evaluation_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    # Print comparison table
    print(f"\n{'='*80}")
    print(f"{'Agent':<25} {'Difficulty':<10} {'Success':<10} {'Blue Score':<12} {'Intercepts':<12}")
    print(f"{'='*80}")
    for key, data in sorted(all_results.items()):
        s = data["summary"]
        print(
            f"{AGENT_CONFIGS[data['agent']]['label']:<25} "
            f"{data['difficulty']:<10} "
            f"{s['success_rate_mean']:>6.1%}     "
            f"{s['blue_score_mean']:>8.3f}      "
            f"{s['avg_intercepts']:>8.1f}"
        )


if __name__ == "__main__":
    main()

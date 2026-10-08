"""Mid-training snapshot: H.10 criterion-2 risk check on complex.

Uses the CURRENT best checkpoints (no need to wait for 5M completion):
  pure_rl : MAPPO argmax, no goals (exactly the tournament's pure_rl path)
  hybrid  : LLM planner (GOAI) + MAPPO executor via the attribution runner
Reports mission_success rates + Welch t-test on the gap.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, ".")

parser = argparse.ArgumentParser()
parser.add_argument("--difficulty", default="complex")
parser.add_argument("--episodes", type=int, default=20)
parser.add_argument("--systems", default="pure_rl,rule,hybrid")
args = parser.parse_args()

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.agents.mappo_agent import MAPPOAgent, encode_unit_obs

CKPT = f"checkpoints/mappo_{args.difficulty}_s42_best.pt"
assert os.path.exists(CKPT), f"missing {CKPT}"
agent = MAPPOAgent(role="blue", seed=0, checkpoint_path=CKPT)


def run_pure_rl(seed: int) -> dict:
    env = GridEnv(difficulty=args.difficulty, seed=seed)
    steps = 0
    while not env.done and steps < MAX_STEPS:
        obs = env._get_observation("blue")
        env.step(agent.act(obs, env), None)
        env.compute_reward("blue")
        steps += 1
    return env.get_episode_metrics()


def run_rule(seed: int) -> dict:
    from grid_env.agents.rule_agent import RuleAgent
    env = GridEnv(difficulty=args.difficulty, seed=seed)
    ag = RuleAgent(role="blue", seed=seed, executor_checkpoint=CKPT)
    steps = 0
    while not env.done and steps < MAX_STEPS:
        obs = env._get_observation("blue")
        env.step(ag.act(obs, env), None)
        env.compute_reward("blue")
        steps += 1
    return env.get_episode_metrics()


def run_hybrid(seed: int) -> dict:
    from attribution import LLMPlanner, run_system
    from grid_env.agents.llm_client import LLMClient
    return run_system(args.difficulty, seed,
                      LLMPlanner(LLMClient(), seed=seed, interval=10),
                      executor="mappo", mappo_checkpoint=CKPT)["metrics"]


systems = {"pure_rl": run_pure_rl, "rule": run_rule, "hybrid": run_hybrid}
results = {}
for name in args.systems.split(","):
    fn = systems[name]
    sr, scores = [], []
    for i in range(args.episodes):
        m = fn(100 + i)
        sr.append(float(m["mission_success"]))
        scores.append(m["blue_score"])
        print(f"  [{name} ep{i}] ok={int(m['mission_success'])} "
              f"score={m['blue_score']:.2f}", flush=True)
    results[name] = {"sr": np.mean(sr), "scores": scores,
                     "sr_list": sr}
    print(f"== {name}: SR={np.mean(sr):.0%} "
          f"blue_score={np.mean(scores):.3f} ± {np.std(scores):.3f}\n",
          flush=True)

if "pure_rl" in results and "hybrid" in results:
    from validate import _welch_ttest
    gap = results["hybrid"]["sr"] - results["pure_rl"]["sr"]
    _, p = _welch_ttest(results["hybrid"]["sr_list"],
                        results["pure_rl"]["sr_list"])
    print(f"criterion-2 snapshot: hybrid − pure_rl = {gap:+.1%} (p={p:.4f})")
    print("NEED >= +15% with p<0.05 →",
          "ON TRACK" if (gap >= 0.15 and p < 0.05) else
          ("AT RISK" if gap >= 0 else "RED LIGHT — env re-tuning needed"))

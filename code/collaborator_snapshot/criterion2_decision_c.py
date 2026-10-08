"""Criterion-2 recheck under decision (c): pure_rl complex ≈ 0 is accepted,
so the gate is read off the hybrid − pure_rl gap instead.

Systems on complex, all sharing the same executor checkpoint
(curriculum_long final, i.e. the best available trained complex policy):
  pure_rl   : MAPPO argmax, no goals (tournament's pure_rl path)
  rule_mappo: rule planner + MAPPO executor (GOAI stack, no LLM)
  hybrid    : LLM planner + MAPPO executor (the paper's hybrid system)

Usage:
  python criterion2_decision_c.py --systems pure_rl,rule_mappo --episodes 20
  OPENAI_BASE_URL=... LLM_DEFAULT_MODEL=... python criterion2_decision_c.py \
      --systems hybrid --episodes 20 --seed0 100
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, ".")

parser = argparse.ArgumentParser()
parser.add_argument("--difficulty", default="complex")
parser.add_argument("--episodes", type=int, default=20)
parser.add_argument("--seed0", type=int, default=100)
parser.add_argument("--systems", default="pure_rl,rule_mappo,hybrid")
parser.add_argument("--ckpt", default="checkpoints/curriculum_long/"
                                     "mappo_complex_s42_final.pt")
parser.add_argument("--out", default="results/criterion2_decision_c.json")
parser.add_argument("--append_to", default=None,
                    help="merge this run into an existing results json")
args = parser.parse_args()

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.agents.mappo_agent import MAPPOAgent

assert os.path.exists(args.ckpt), f"missing {args.ckpt}"


def run_pure_rl(seed: int, agent) -> dict:
    env = GridEnv(difficulty=args.difficulty, seed=seed)
    steps = 0
    while not env.done and steps < MAX_STEPS:
        obs = env._get_observation("blue")
        env.step(agent.act(obs, env), None)
        env.compute_reward("blue")
        steps += 1
    return env.get_episode_metrics()


def run_rule_mappo(seed: int) -> dict:
    from grid_env.agents.rule_agent import RuleAgent
    env = GridEnv(difficulty=args.difficulty, seed=seed)
    ag = RuleAgent(role="blue", seed=seed, executor_checkpoint=args.ckpt)
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
                      executor="mappo", mappo_checkpoint=args.ckpt)["metrics"]


def run_rule_heuristic(seed: int) -> dict:
    from attribution import RulePlanner, run_system
    return run_system(args.difficulty, seed,
                      RulePlanner(seed=seed, interval=5),
                      executor="heuristic")["metrics"]


def run_hybrid_heuristic(seed: int) -> dict:
    from attribution import LLMPlanner, run_system
    from grid_env.agents.llm_client import LLMClient
    return run_system(args.difficulty, seed,
                      LLMPlanner(LLMClient(), seed=seed, interval=10),
                      executor="heuristic")["metrics"]


def run_hybrid_heuristic_i5(seed: int) -> dict:
    # planner enhancement #1: replan interval 10 -> 5 (matches the rule
    # planner's cadence; agent-side change, allowed under env freeze)
    from attribution import LLMPlanner, run_system
    from grid_env.agents.llm_client import LLMClient
    return run_system(args.difficulty, seed,
                      LLMPlanner(LLMClient(), seed=seed, interval=5),
                      executor="heuristic")["metrics"]


systems = {"pure_rl": run_pure_rl, "rule_mappo": run_rule_mappo,
           "hybrid": run_hybrid, "rule_heuristic": run_rule_heuristic,
           "hybrid_heuristic": run_hybrid_heuristic,
           "hybrid_heuristic_i5": run_hybrid_heuristic_i5}
rl_agent = None
if "pure_rl" in args.systems:
    rl_agent = MAPPOAgent(role="blue", seed=0, checkpoint_path=args.ckpt)

results = {}
for name in args.systems.split(","):
    fn = systems[name]
    sr, scores, lens, wins, eps = [], [], [], [], []
    for i in range(args.episodes):
        seed = args.seed0 + i
        m = fn(seed, rl_agent) if name == "pure_rl" else fn(seed)
        sr.append(float(m["mission_success"]))
        scores.append(m["blue_score"])
        lens.append(m.get("episode_length", 0))
        wins.append(m.get("winner", "?"))
        # full L1 metrics per episode (env frozen v2.1.4) — offline recompute
        # of any future metric without re-running (LLM episodes are not
        # exactly reproducible)
        eps.append(m)
        print(f"  [{name} ep{i}] ok={int(m['mission_success'])} "
              f"score={m['blue_score']:.2f} winner={m.get('winner', '?')}",
              flush=True)
    results[name] = {
        "SR": round(float(np.mean(sr)), 4),
        "blue_score": round(float(np.mean(scores)), 4),
        "avg_len": round(float(np.mean(lens)), 1),
        "sr_list": sr,
        "episodes": eps,
    }
    print(f"== {name}: SR={np.mean(sr):.0%} blue_score={np.mean(scores):.3f}"
          f" ± {np.std(scores):.3f}\n", flush=True)

# merge with previous partial runs of this same recheck (append mode)
merged = {}
if args.append_to and os.path.exists(args.append_to):
    with open(args.append_to) as f:
        merged = json.load(f).get("systems", {})
merged.update(results)

payload = {
    "config": {"difficulty": args.difficulty, "ckpt": args.ckpt,
               "episodes": args.episodes, "seed0": args.seed0,
               "model": os.environ.get("LLM_DEFAULT_MODEL", "rule/nogoal"),
               "decision": "c: accept pure_rl complex~0, gate on hybrid-pure_rl gap"},
    "systems": merged,
}
out = args.append_to or args.out
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(payload, f, indent=2)

if "pure_rl" in merged and "hybrid" in merged:
    from validate import _welch_ttest
    gap = merged["hybrid"]["SR"] - merged["pure_rl"]["SR"]
    _, p = _welch_ttest(merged["hybrid"]["sr_list"],
                        merged["pure_rl"]["sr_list"])
    verdict = "PASS" if (gap >= 0.15 and p < 0.05) else (
        "AT RISK" if gap > 0 else "RED LIGHT")
    print(f"criterion-2 (decision c): hybrid − pure_rl = {gap:+.1%} "
          f"(p={p:.4f}) → {verdict}")

print(f"saved -> {out}")

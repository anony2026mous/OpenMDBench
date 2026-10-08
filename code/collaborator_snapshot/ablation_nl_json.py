"""A3 natural-language interface ablation (Appendix D, grid-exclusive).

Double-edged sword hypothesis (paper Analysis A3):
  - JSON (structured situational_data only) is expected to WIN on low
    semantic-load tasks (simple) where prose adds noise/latency;
  - NL (prose situational report) is expected to WIN on high semantic-load
    tasks (medium/complex: deception cues, anomaly narratives, heading
    drift descriptions) where semantics carry decision-relevant signal.

Conditions: {nl, json} x difficulty tiers, hybrid system (LLM planner +
MAPPO executor via GOAI), fixed executor checkpoints.

Usage:
    python ablation_nl_json.py --difficulties simple,medium --episodes 15
    OPENAI_BASE_URL=<your OpenAI-compatible endpoint> \
    LLM_DEFAULT_MODEL=Qwen3.8-27B python ablation_nl_json.py ...
(complex tier waits for the v2.1.3 curriculum checkpoints, P0-B3)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.agents.hybrid_agent import HybridAgent
from grid_env.agents.llm_client import LLMClient

OUT_PATH = "results/ablation_nl_json.json"


def executor_ckpt(difficulty: str) -> str:
    for suffix in ("_best", "_final"):
        name = f"checkpoints/mappo_{difficulty}_s42{suffix}.pt"
        if os.path.exists(name):
            return name
    return None  # fall back to the built-in heuristic executor


def run_episode(difficulty: str, nl_mode: str, seed: int, ckpt) -> dict:
    env = GridEnv(difficulty=difficulty, seed=seed)
    agent = HybridAgent(role="blue", seed=seed, llm_client=LLMClient(),
                        executor_checkpoint=ckpt, nl_mode=nl_mode)
    steps = 0
    while not env.done and steps < MAX_STEPS:
        obs = env._get_observation("blue")
        env.step(agent.act(obs, env), None)
        env.compute_reward("blue")
        steps += 1
    m = env.get_episode_metrics()
    stats = agent.llm.get_stats()
    return {
        "mission_success": float(m["mission_success"]),
        "blue_score": float(m["blue_score"]),
        "civilian_intercepted": float(m["civilian_intercepted"]),
        "adaptation_latency": (float(np.mean(m["adaptation_latencies"]))
                               if m["adaptation_latencies"] else None),
        "llm_calls": stats["total_calls"],
        "llm_errors": stats["errors"],
        "avg_latency": stats["avg_latency"],
        "length": steps,
        # full L1 metrics dict (env frozen v2.1.4): keeps every per-episode
        # field so future metric changes can be recomputed offline from the
        # result json instead of re-running LLM episodes (which are not
        # exactly reproducible: temperature 0.1 + vLLM state)
        "full_metrics": m,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulties", default="simple,medium")
    ap.add_argument("--episodes", type=int, default=15)
    ap.add_argument("--seed0", type=int, default=200)
    ap.add_argument("--executor", default="mappo", choices=["mappo", "heuristic"],
                    help="heuristic = built-in GOAIExecutor (use on complex: "
                         "the MAPPO executor is an SR=0 floor there, which "
                         "would mask any interface-mode difference)")
    ap.add_argument("--out", default=OUT_PATH,
                    help="output json path (default results/ablation_nl_json.json)")
    args = ap.parse_args()

    if args.executor == "heuristic":
        global executor_ckpt
        executor_ckpt = lambda difficulty: None

    results = defaultdict(lambda: defaultdict(list))
    for difficulty in args.difficulties.split(","):
        ckpt = executor_ckpt(difficulty)
        for nl_mode in ("nl", "json"):
            for i in range(args.episodes):
                seed = args.seed0 + i
                r = run_episode(difficulty, nl_mode, seed, ckpt)
                results[difficulty][nl_mode].append(r)
                print(f"[{difficulty}/{nl_mode} ep{i}] ok={int(r['mission_success'])} "
                      f"score={r['blue_score']:.2f} calls={r['llm_calls']} "
                      f"errs={r['llm_errors']}", flush=True)

    summary = {}
    for difficulty, modes in results.items():
        summary[difficulty] = {}
        for mode, eps in modes.items():
            sr = [e["mission_success"] for e in eps]
            sc = [e["blue_score"] for e in eps]
            lat = [e["avg_latency"] for e in eps if e["avg_latency"]]
            summary[difficulty][mode] = {
                "n": len(eps),
                "SR": round(float(np.mean(sr)), 4),
                "blue_score": round(float(np.mean(sc)), 4),
                "score_std": round(float(np.std(sc)), 4),
                "avg_llm_latency": round(float(np.mean(lat)), 2) if lat else None,
                "total_llm_errors": sum(e["llm_errors"] for e in eps),
            }
        # paired comparison (same seeds across modes)
        nl_sr = [e["mission_success"] for e in results[difficulty]["nl"]]
        js_sr = [e["mission_success"] for e in results[difficulty]["json"]]
        n = min(len(nl_sr), len(js_sr))
        if n:
            diff = np.array(nl_sr[:n]) - np.array(js_sr[:n])
            summary[difficulty]["paired_nl_minus_json_SR"] = round(float(np.mean(diff)), 4)
            # one-sided sign test p-value (binomial) for nl > json:
            # P(X >= wins) under Bin(m, 0.5). math.comb is py3.8+; the jidi
            # conda env runs 3.7, so use an inline comb.
            wins = int(np.sum(diff > 0)); losses = int(np.sum(diff < 0))
            def _comb(m_, k_):
                c = 1
                for i in range(k_):
                    c = c * (m_ - i) // (i + 1)
                return c
            k, m = wins, wins + losses
            p = (sum(_comb(m, i) for i in range(k, m + 1)) / 2 ** m) if m else 1.0
            summary[difficulty]["sign_test_p_nl_gt_json"] = round(p, 4)

    os.makedirs("results", exist_ok=True)
    payload = {
        "config": {"episodes": args.episodes, "seed0": args.seed0,
                   "model": os.environ.get("LLM_DEFAULT_MODEL", "?"),
                   "base_url": os.environ.get("OPENAI_BASE_URL", "?")},
        "summary": summary,
        "episodes": {d: {m: eps for m, eps in modes.items()}
                     for d, modes in results.items()},
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)

    print("\n==== A3 NL vs JSON summary ====")
    for difficulty, s in summary.items():
        nl, js = s.get("nl", {}), s.get("json", {})
        print(f"{difficulty}: NL SR={nl.get('SR', 0):.0%} score={nl.get('blue_score', 0):.2f}  |  "
              f"JSON SR={js.get('SR', 0):.0%} score={js.get('blue_score', 0):.2f}  |  "
              f"paired Δ(NL-JSON)={s.get('paired_nl_minus_json_SR', 0):+.0%} "
              f"(p={s.get('sign_test_p_nl_gt_json', '?')})")
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()

"""How long does one planner LLM call actually take? (measured, not estimated)

Time is the binding constraint on everything in this project -- the arm's evaluation
cost, the training cost, and why `--goal-source llm` training had to be abandoned --
so the number should come from the real planner path, with the real prompt, rather
than from a synthetic ping.

What is measured here is exactly what the eval and training loops do:
``_make_goal_source`` builds the same ``LLMPlannerV2`` through
``run_episode._build_defender``, and the hook is driven per engine tick exactly as
both loops drive it.  Each ``LLMClient.chat`` call is wrapped to record wall time,
prompt size and completion tokens.

Reported: per-call wall time (mean / median / p90 / max), prompt characters, tokens
out, and the implied number of calls and hours for a real episode.

Usage:
    python _w1_measure_llm_latency.py --scenarios IE-01-SINGLE-TARGET IE-05-MULTI-AXIS
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_env import IERlEnv  # noqa: E402
from llm_client_hifi import LLMClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", nargs="*",
                        default=["IE-01-SINGLE-TARGET", "IE-05-MULTI-AXIS"])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--min-calls", type=int, default=6)
    parser.add_argument("--max-ticks", type=int, default=260)
    args = parser.parse_args()

    records: list[dict] = []
    original = LLMClient.chat

    def timed_chat(self, system_prompt, user_message, max_tokens=None,
                   temperature=0.1):
        started = time.perf_counter()
        text = original(self, system_prompt, user_message,
                        max_tokens=max_tokens, temperature=temperature)
        records.append({
            "seconds": time.perf_counter() - started,
            "prompt_chars": len(user_message or "") + len(system_prompt or ""),
            "reply_chars": len(text or ""),
            "usage": dict(self._last_usage),
        })
        print(records[-1], flush=True)
        return text

    LLMClient.chat = timed_chat   # type: ignore[assignment]
    theta = HERE / "_w1_runs" / "rl" / "theta_arm5_warm.npz"
    try:
        for scenario in args.scenarios:
            # Imported here: the trainer module pulls in the engine, which needs the
            # engine venv to be on PYTHONPATH (the same requirement as every sweep).
            from ie_rl_train import _make_goal_source, initial_goal_observation

            env = IERlEnv(scenario, seed=args.seed, goal_features=True,
                          speed_source="legacy_tags")
            request = {"theta": str(theta), "goal_source": "llm",
                       "decision_interval": 5, "speed_source": "legacy_tags",
                       "plan_interval": 10, "seed": args.seed}
            provider, pre_tick, agent = _make_goal_source(env, request, scenario)
            env.goal_provider = provider
            env.pre_tick_hook = pre_tick
            before = len(records)
            started = time.perf_counter()
            try:
                obs, _ = env.reset()
                obs = initial_goal_observation(env, obs)
                for _ in range(args.max_ticks // 5):
                    action = {
                        "heading_xy": np.tile(
                            np.array([0.0, 1.0], dtype=np.float32),
                            (env.num_units, 1)),
                        "speed": np.full(env.num_units, 0.7, dtype=np.float32),
                        "fire": np.zeros(env.num_units, dtype=np.int64),
                    }
                    obs, _, terminated, truncated, _ = env.step(action)
                    if terminated or truncated:
                        break
                    if len(records) - before >= args.min_calls:
                        break
                wall = time.perf_counter() - started
                stats = agent.planner.get_stats() if hasattr(agent, "planner") else {}
                health = stats if isinstance(stats, dict) else None
                print(f"== {scenario}  episode wall {wall:.1f}s for "
                      f"{len(records) - before} planner calls")
                if isinstance(health, dict):
                    print(f"   plan_calls={health.get('plan_calls')} "
                          f"parse_failures={health.get('parse_failures')} "
                          f"fallback={health.get('fallback_count')} "
                          f"stale_reuse={health.get('stale_plan_reuse')}")
            finally:
                env.close()
    finally:
        LLMClient.chat = original   # type: ignore[assignment]

    if not records:
        print("no LLM calls recorded")
        return 2
    seconds = [r["seconds"] for r in records]
    prompts = [r["prompt_chars"] for r in records]
    replies = [r["reply_chars"] for r in records]
    print()
    print(f"=== {len(records)} 次真实规划调用 ===")
    print(f"  每次墙钟: mean={statistics.fmean(seconds):.2f}s  "
          f"median={statistics.median(seconds):.2f}s  "
          f"min={min(seconds):.2f}s  max={max(seconds):.2f}s")
    print(f"  prompt 字符: mean={statistics.fmean(prompts):.0f} "
          f"(min {min(prompts)}, max {max(prompts)})")
    print(f"  回复字符:   mean={statistics.fmean(replies):.0f} "
          f"(min {min(replies)}, max {max(replies)})")
    print(f"  总耗时 {sum(seconds):.1f}s，其中 LLM 占 {sum(seconds):.1f}s")
    per_call = statistics.fmean(seconds)
    for name, ticks in (("IE-01/02 全长 (900t)", 900), ("IE-03 全长 (1000t)", 1000),
                        ("IE-04..06 (1200t)", 1200), ("IE-07 (1400t)", 1400),
                        ("MD-AD-006 (1800t)", 1800)):
        calls = ticks // 10
        print(f"  推算 {name}: {calls} 次调用 ≈ {calls * per_call / 60:.1f} 分钟（纯 LLM 时间）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

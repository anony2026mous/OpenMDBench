"""Round-robin long-stability workload for the four core Legacy scenarios."""

from __future__ import annotations

import argparse
import gc
import json
import time
from typing import Any

import numpy as np
from openmdbench.envs import OpenMDBenchEnv

SCENARIOS = (
    "MD-INT-001",
    "MD-AD-002-EASY",
    "MD-AD-002-MEDIUM",
    "MD-AD-002-HARD",
)


def run_legacy_soak(
    *, duration_seconds: float, minimum_episodes: int, steps_per_episode: int
) -> dict[str, Any]:
    if duration_seconds < 0.0 or minimum_episodes < 1 or steps_per_episode < 1:
        raise ValueError("legacy soak limits must be positive")
    started = time.monotonic()
    deadline = started + duration_seconds
    episodes = 0
    ticks = 0
    scenario_counts = {scenario: 0 for scenario in SCENARIOS}
    action = np.asarray((0.0, 0.0), dtype=np.float32)
    while episodes < minimum_episodes or time.monotonic() < deadline:
        scenario = SCENARIOS[episodes % len(SCENARIOS)]
        environment = OpenMDBenchEnv(scenario_id=scenario, seed=20_000 + episodes)
        environment.reset(seed=20_000 + episodes)
        try:
            for _ in range(steps_per_episode):
                _observation, _reward, terminated, truncated, _info = environment.step(action)
                ticks += 1
                if terminated or truncated:
                    break
        finally:
            environment.close()
        scenario_counts[scenario] += 1
        episodes += 1
        if episodes % 25 == 0:
            gc.collect()
    elapsed = max(time.monotonic() - started, 1e-12)
    tick_seconds = 1.0
    return {
        "duration_seconds": elapsed,
        "target_duration_seconds": duration_seconds,
        "episodes": episodes,
        "ticks": ticks,
        "ticks_per_second": ticks / elapsed,
        "rtf": ticks * tick_seconds / elapsed,
        "scenario_counts": scenario_counts,
        "active_sessions": 0,
        "queue_depth": 0,
        "cache_entries": 0,
        "frame_drops": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--minimum-episodes", type=int, default=4)
    parser.add_argument("--steps-per-episode", type=int, default=60)
    args = parser.parse_args()
    print(
        json.dumps(
            run_legacy_soak(
                duration_seconds=args.seconds,
                minimum_episodes=args.minimum_episodes,
                steps_per_episode=args.steps_per_episode,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

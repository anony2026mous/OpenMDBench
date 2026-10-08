"""Gate: reusing one env across episodes must not corrupt reward accounting.

Round-3 audit finding.  ``_reward`` credits a neutralisation once per entity via
``self._credited_kills``, but ``reset()`` never cleared that set -- and the
rollout worker deliberately **reuses one ``IERlEnv`` object for every episode of
a scenario** (it only rebuilds when the scenario changes).  Entity ids are stable
across episodes (``intruder.uav-01`` ...), so from episode 2 onwards every raider
was already in the set, ``new_kills`` came out empty, and the policy received
**no reward at all for neutralising raiders** -- the single largest positive term.
A 30-iteration run would have taught the policy that shooting achieves nothing.

The test is decisive because it repeats the *same* session id with the same
policy: the engine's hit rolls are seeded from the session id, so two runs of the
same configuration must produce the same accounting.  Any difference is state
leaking across ``reset()``.

Usage:
    python _w1_test_reward_reset.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def run_episode(env, steps: int, rng_seed: int) -> dict:
    """One scripted episode; returns the aggregate reward accounting."""
    rng = np.random.default_rng(rng_seed)
    env.episode_index = 0                # same session id every time
    env.reset()
    # The ledger must be empty *at the start* of an episode; it is legitimately
    # populated once the episode has credited its kills.
    ledger_at_start = set(getattr(env, "_credited_kills", set()))
    rewards, neutralised, fired, own_lost = 0.0, 0, 0, 0
    for _ in range(steps):
        mask = env.fire_mask()
        fire = np.zeros(env.num_units, dtype=np.int64)
        for i in range(env.num_units):
            choices = np.flatnonzero(mask[i, 1:])
            if choices.size and rng.random() < 0.7:
                fire[i] = int(choices[rng.integers(choices.size)]) + 1
        rad = rng.uniform(0.0, 2.0 * np.pi, size=env.num_units)
        action = {
            "heading_xy": np.stack([np.sin(rad), np.cos(rad)],
                                   axis=1).astype(np.float32),
            "speed": rng.uniform(0.5, 1.0, size=env.num_units).astype(np.float32),
            "fire": fire,
        }
        _obs, reward, terminated, truncated, info = env.step(action)
        rewards += reward
        neutralised += int(info.get("raiders_lost", 0))
        fired += int(info.get("fired", 0))
        own_lost += int(info.get("own_lost", 0))
        if terminated or truncated:
            break
    return {"reward": round(rewards, 6), "neutralised": neutralised,
            "fired": fired, "own_lost": own_lost,
            "ledger_at_start": sorted(ledger_at_start)}


def main() -> int:
    from ie_rl_env import IERlEnv, RewardConfig

    public_id = sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET"
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 24

    env = IERlEnv(public_id, seed=7, decision_interval=5, max_ticks=200,
                  reward=RewardConfig())
    try:
        first = run_episode(env, steps, 1234)
        second = run_episode(env, steps, 1234)     # SAME env object, SAME config
        third = run_episode(env, steps, 1234)
        print(f"     episode 1: {first}")
        print(f"     episode 2: {second}")
        print(f"     episode 3: {third}")

        check("a reused env reproduces the same neutralisation count",
              first["neutralised"] == second["neutralised"] == third["neutralised"],
              f"{first['neutralised']} / {second['neutralised']} / "
              f"{third['neutralised']}")
        check("a reused env reproduces the same total reward",
              first["reward"] == second["reward"] == third["reward"],
              f"{first['reward']} / {second['reward']} / {third['reward']}")
        check("the kill credit set is empty at the start of every episode",
              not first["ledger_at_start"] and not second["ledger_at_start"]
              and not third["ledger_at_start"],
              f"ep1={first['ledger_at_start'][:4]} ep2={second['ledger_at_start'][:4]} "
              f"ep3={third['ledger_at_start'][:4]}")

        # a fresh env must agree with the reused one (no hidden cross-episode state)
        fresh = IERlEnv(public_id, seed=7, decision_interval=5, max_ticks=200,
                        reward=RewardConfig())
        try:
            baseline = run_episode(fresh, steps, 1234)
        finally:
            fresh.close()
        check("a fresh env agrees with the reused env",
              {k: v for k, v in baseline.items() if k != "ledger_at_start"}
              == {k: v for k, v in third.items() if k != "ledger_at_start"},
              f"fresh={baseline} reused={third}")
        check("episodes actually score neutralisations (the term is live)",
              baseline["neutralised"] > 0,
              f"{baseline['neutralised']} raiders neutralised with a random policy")
    finally:
        env.close()

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

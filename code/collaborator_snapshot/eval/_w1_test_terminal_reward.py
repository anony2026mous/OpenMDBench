"""Gate: the terminal win/loss reward must actually fire.

Round-6 audit finding.  ``_reward`` pays ``terminal_win`` / ``terminal_loss``
(+/-2.0) when an episode reaches a decided terminal state -- the two largest terms
in the whole reward.  Both were **dead**:

  * the engine's terminal type is a frozen slots dataclass
    (``TerminalMissionResultV2``), which is neither a ``Mapping`` nor has
    ``model_dump``, so ``run_episode._receipt_terminal`` returned
    ``{"result": "<repr text>"}``;
  * ``ie_rl_env`` then read ``getattr(terminal_result, "outcome", "")`` off that
    *dict*, got ``""``, and compared ``""`` against ``"defender_success"`` /
    ``"intruder_success"`` -- so neither branch was ever taken.

The scorecard still looked correct because ``strategy_metrics._parse_terminal_blob``
recovers the fields from the repr text, which is exactly why nobody noticed: the
metric being reported was right while the signal being trained on was missing.

This test drives a real episode to a decided terminal state and asserts the
terminal term is non-zero and that the outcome token is readable.  IE-01 at seed
1000 loses to ``rule.assets-lost`` at tick ~158, which exercises the loss branch;
the win branch is exercised by scanning seeds until a ``defender_success``
appears, so both branches are covered rather than just one.

Usage:
    python _w1_test_terminal_reward.py
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


def play_to_terminal(public_id: str, seed: int, *, fire_at_first: bool,
                     max_decisions: int = 400) -> dict:
    """Run to a decided terminal state and report the terminal accounting."""
    from ie_rl_env import IERlEnv, RewardConfig

    env = IERlEnv(public_id, seed=seed, decision_interval=5,
                  reward=RewardConfig())
    env.max_ticks_override = None          # the scenario's own end
    try:
        env.reset()
        rng = np.random.default_rng(seed)
        total = 0.0
        terminal_reward = None
        outcome_at_termination = None
        for _ in range(max_decisions):
            mask = env.fire_mask()
            fire = np.zeros(env.num_units, dtype=np.int64)
            if fire_at_first:
                for i in range(env.num_units):
                    choices = np.flatnonzero(mask[i, 1:])
                    if choices.size:
                        fire[i] = int(choices[0]) + 1
            rad = rng.uniform(0.0, 2.0 * np.pi, size=env.num_units)
            action = {
                "heading_xy": np.stack([np.sin(rad), np.cos(rad)],
                                       axis=1).astype(np.float32),
                "speed": rng.uniform(0.5, 1.0,
                                     size=env.num_units).astype(np.float32),
                "fire": fire,
            }
            _obs, reward, terminated, truncated, info = env.step(action)
            total += reward
            if terminated:
                terminal_reward = float(info.get("terminal_reward", 0.0))
                outcome_at_termination = env.terminal_outcome
                break
            if truncated:
                outcome_at_termination = env.terminal_outcome
                break
        return {"reward": round(total, 4), "outcome": outcome_at_termination,
                "terminal_reward": terminal_reward,
                "tick": int(env._session.world_view.tick)}
    finally:
        env.close()


def main() -> int:
    print("-- loss branch (IE-01 seed 1000 terminates via rule.assets-lost)")
    seen_loss = None
    for seed in (1000, 1001, 1002, 1003, 1004):
        row = play_to_terminal("IE-01-SINGLE-TARGET", seed, fire_at_first=False)
        print(f"     seed {seed}: {row}")
        if row["outcome"] == "intruder_success" and row["terminal_reward"] is not None:
            seen_loss = row
            break
    check("an intruder_success episode is reachable", seen_loss is not None,
          "no seed produced a decided loss in 5 tries")
    if seen_loss:
        check("the outcome token is a bare token, not a dict blob",
              seen_loss["outcome"] == "intruder_success",
              str(seen_loss["outcome"])[:120])
        check("terminal_loss was actually charged (-2.0)",
              seen_loss["terminal_reward"] == -2.0,
              f"terminal_reward={seen_loss['terminal_reward']}")

    print("-- win branch (scan seeds for defender_success)")
    seen_win = None
    for seed in (1000, 1001, 1002, 1003, 1004, 7, 11, 13, 17, 19):
        row = play_to_terminal("IE-03-SURFACE-RAID", seed, fire_at_first=True)
        if row["outcome"] == "defender_success" and row["terminal_reward"] is not None:
            seen_win = row
            print(f"     seed {seed}: {row}")
            break
    check("a defender_success episode is reachable", seen_win is not None,
          "no seed produced a decided win in 10 tries")
    if seen_win:
        check("terminal_win was actually charged (+2.0)",
              seen_win["terminal_reward"] == 2.0,
              f"terminal_reward={seen_win['terminal_reward']}")

    # direct unit check of the extractor against both shapes
    from ie_rl_env import IERlEnv
    check("a structured dict yields its outcome",
          IERlEnv._outcome_of({"outcome": "defender_success",
                               "rule_id": "r"}) == "defender_success")
    check("the legacy text blob is rejected, not mistaken for a token",
          IERlEnv._outcome_of({"result": "TerminalMissionResultV2(outcome='x')"})
          is None)
    check("an object with .outcome still works",
          IERlEnv._outcome_of(type("T", (), {"outcome": "intruder_success"})())
          == "intruder_success")

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

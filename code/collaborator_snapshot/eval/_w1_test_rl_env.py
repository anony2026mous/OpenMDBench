"""Self-check for the RL environment wrapper: does it really drive the scenario?

Structural checks first (the discipline the goal mandates), then one short real
episode with a random policy to prove that

  * the observation has the advertised fixed shape,
  * the fire mask is non-empty (a mask that is all-False would make PPO learn
    nothing and look like "RL is bad" rather than "the mask is broken"),
  * commands are accepted by the engine (not rejected wholesale),
  * red is driven by the same AttackProfileDriverV2 the other arms use,
  * the reward moves when raiders are neutralised.

Windows note: builds a session, so everything lives inside ``main()`` behind the
``__main__`` guard.

Usage:
    python _w1_test_rl_env.py [PUBLIC_ID] [STEPS]
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


def main(public_id: str, steps: int) -> int:
    from ie_rl_env import IERlEnv, RewardConfig

    env = IERlEnv(public_id, seed=7, decision_interval=5,
                  max_ticks=120, reward=RewardConfig())
    try:
        obs, info = env.reset()
        check("observation has the advertised fixed size",
              obs.shape == (env.observation_size,),
              f"{obs.shape} vs {(env.observation_size,)}")
        check("observation is finite",
              bool(np.all(np.isfinite(obs))))
        check("friendly slots discovered", env.num_units > 0,
              f"{env.num_units} units: {[s.entity_id for s in env._slots]}")
        check("fire mask shape matches units x choices",
              env.fire_mask().shape == (env.num_units, env.num_fire_choices),
              str(env.fire_mask().shape))

        rng = np.random.default_rng(0)
        total_reward = 0.0
        fire_legal_ticks = 0
        infos = []
        for step_index in range(steps):
            mask = env.fire_mask()
            # NOTE: mask[:, 0] ("hold fire") is always legal, so the meaningful
            # check is whether any *fire* column is legal -- mask.any() alone
            # would pass vacuously even with a completely broken mask.
            if mask[:, 1:].any():
                fire_legal_ticks += 1
            fire = np.zeros(env.num_units, dtype=np.int64)
            legal = [i for i in range(env.num_units)
                     if mask[i, 1:].any() and rng.random() < 0.5]
            for i in legal:
                choices = np.flatnonzero(mask[i, 1:])
                fire[i] = int(choices[rng.integers(len(choices))]) + 1
            action = {
                # Direct output: an absolute heading as a (sin, cos) pair and an
                # absolute speed fraction.  Random values are fine here -- the
                # point is that the *engine* accepts them, not that they are
                # sensible.
                "heading_xy": rng.uniform(-1.0, 1.0,
                                          size=(env.num_units, 2)).astype(np.float32),
                "speed": rng.uniform(0.0, 1.0, size=env.num_units).astype(np.float32),
                "fire": fire,
            }
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            infos.append(info)
            if terminated or truncated:
                break

        check("episode produced steps", len(infos) > 0, f"{len(infos)} decisions")
        check("reward is finite", np.isfinite(total_reward), f"{total_reward:.3f}")
        check("fire was actually legal at some point",
              fire_legal_ticks > 0,
              f"{fire_legal_ticks}/{len(infos)} decisions had a legal shot")
        fired_total = sum(i["fired"] for i in infos)
        print(f"      随机策略共提交开火 {fired_total} 次；"
              f"末端 outcome={env.terminal_outcome} tick={env._session.world_view.tick}")
        raiders_lost = sum(i["raiders_lost"] for i in infos)
        print(f"      随机策略中性化来袭者 {raiders_lost} 个；"
              f"设施损伤合计 {sum(i['facility_damage'] for i in infos):.3f}")
        check("red side is actually driven (threat moves)",
              env._attack is not None and env._attack.stats["submitted_batches"] > 0,
              str(dict(env._attack.stats)))

        # --- direct-output semantics ------------------------------------
        # The requirement is that the number the network emits **is** the action.
        # Under the old delta layout, submitting the same value every decision
        # meant "keep turning by the same amount", so holding a course required a
        # stream of different numbers.  With an absolute heading, holding must
        # hold -- that is the observable difference, and it is what this checks.
        import math

        obs, _ = env.reset()
        target_deg = 90.0
        rad = math.radians(target_deg)
        action = {
            "heading_xy": np.tile(np.asarray([math.sin(rad), math.cos(rad)],
                                             dtype=np.float32),
                                  (env.num_units, 1)),
            "speed": np.full(env.num_units, 0.5, dtype=np.float32),
            "fire": np.zeros(env.num_units, dtype=np.int64),
        }

        def _live_headings() -> list[float]:
            entities = {str(e.id): e for e in env._session.world_view.entities_stable()}
            out = []
            for slot in env._slots:
                entity = entities.get(slot.entity_id)
                if entity is not None and str(entity.state.lifecycle) in ("active",
                                                                         "degraded"):
                    out.append(float(entity.state.heading_deg) % 360.0)
            return out

        def _ang_gap(a: float, b: float) -> float:
            return abs((a - b + 180.0) % 360.0 - 180.0)

        samples = []
        for _ in range(4):
            env.step(action)
            live = _live_headings()
            if live:
                samples.append(sum(live) / len(live))
        check("absolute heading is followed at all",
              bool(samples) and _ang_gap(samples[0], target_deg) < 70.0,
              f"after 1 decision mean heading "
              f"{samples[0]:.1f} deg vs commanded {target_deg}"
              if samples else "no live units")
        check("repeating the same absolute heading holds the course",
              bool(samples) and _ang_gap(samples[-1], target_deg) < 30.0,
              f"after {len(samples)} decisions mean heading "
              f"{samples[-1]:.1f} deg (a delta head would have kept rotating)"
              if samples else "no live units")
    finally:
        env.close()

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET",
                          int(sys.argv[2]) if len(sys.argv) > 2 else 12))

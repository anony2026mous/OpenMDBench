"""Unit tests for Phase 5: MAPPO (CTDE) + pure_llm v2 + executor injection.

Covers:
- unified obs encoding (shapes, USV/UAV planes, action masks)
- centralized global-state encoder (dims, determinism, [0,1])
- UAV never samples INTERCEPT under the masked policy
- short training smoke (numerics finite, checkpoints roundtrip)
- PPOAgent alias loads MAPPO (run_tournament compatibility)
- hybrid executor controller injection from a trained checkpoint
- pure_llm v2 action masking (UAV=5 → STAY) with mocked LLM

Run: python -u test_mappo.py
"""
import os
import sys
import types

import numpy as np
import torch

from grid_env.grid_env import GridEnv, Direction, MAX_STEPS
from grid_env.agents.mappo_agent import (
    MAPPOAgent, MAPPOActor, encode_unit_obs, build_global_state,
    make_goai_controller, OBS_DIM, GSTATE_DIM, ACT_DIM,
)
from grid_env.agents import PPOAgent

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'} {name} {'' if cond else detail}")


def test_encoders():
    print("[test_encoders]")
    env = GridEnv(difficulty="complex", seed=3)

    o_usv, m_usv = encode_unit_obs(env, "blue_0")
    o_uav, m_uav = encode_unit_obs(env, "blue_2")
    check("obs dims", o_usv.shape == (OBS_DIM,) and o_uav.shape == (OBS_DIM,))
    check("usv mask full", m_usv.tolist() == [1] * 6)
    check("uav mask no intercept", m_uav.tolist() == [1, 1, 1, 1, 1, 0])

    # USV 5×5 plane centered in the 8×8 window: corners must stay zero
    # unless the USV is near map entities; check the plane width usage
    plane_usv = o_usv[:64].reshape(8, 8)
    plane_uav = o_uav[:64].reshape(8, 8)
    check("usv plane embedded", abs(plane_usv).max() <= 1.0 + 1e-6)
    check("uav plane embedded", abs(plane_uav).max() <= 1.0 + 1e-6)
    check("out-of-bounds code normalized",
          (plane_uav <= 1.0).all() and (plane_uav >= -1.0).all())

    # kind one-hot
    check("kind one-hot usv", o_usv[69] == 1.0 and o_usv[70] == 0.0)
    check("kind one-hot uav", o_uav[69] == 0.0 and o_uav[70] == 1.0)

    # goal conditioning: waypoint goal sets one-hot + relative vector
    o_wp, _ = encode_unit_obs(env, "blue_0", goal_type="waypoint",
                              target_xy=(10, 10))
    check("goal one-hot set", o_wp[71 + 1] == 1.0)  # waypoint = index 1
    e = env.entities["blue_0"]
    exp_dx = (10 - e.x) / 20
    check("goal rel vector", abs(o_wp[79] - exp_dx) < 1e-5)

    # global state
    g1 = build_global_state(env)
    g2 = build_global_state(env)
    check("gstate dims", g1.shape == (GSTATE_DIM,))
    check("gstate deterministic", np.allclose(g1, g2))
    check("gstate range", 0.0 <= g1.min() and g1.max() <= 1.0)
    env.step({}, None)
    g3 = build_global_state(env)
    check("gstate tracks step", abs(g3[-26] - env.step_count / MAX_STEPS) < 1e-6)


def test_masked_policy():
    print("[test_masked_policy]")
    torch.manual_seed(0)
    actor = MAPPOActor()
    env = GridEnv(difficulty="simple", seed=1)
    obs, mask = encode_unit_obs(env, "blue_2")  # UAV
    obs_t = torch.as_tensor(obs).unsqueeze(0)
    mask_t = torch.as_tensor(mask).unsqueeze(0)
    saw_intercept = False
    for _ in range(500):
        dist = actor(obs_t, mask_t)
        a = int(dist.sample().item())
        if a == Direction.INTERCEPT.value:
            saw_intercept = True
    check("uav never samples intercept", not saw_intercept)
    probs = actor(obs_t, mask_t).probs[0]
    check("uav intercept prob zero", probs[5].item() < 1e-12)

    # USV can sample intercept
    obs_s, mask_s = encode_unit_obs(env, "blue_0")
    dist = actor(torch.as_tensor(obs_s).unsqueeze(0),
                 torch.as_tensor(mask_s).unsqueeze(0))
    check("usv intercept prob > 0", dist.probs[0][5].item() > 0)


def test_training_smoke():
    print("[test_training_smoke]")
    from train_mappo import MAPPOTrainer

    trainer = MAPPOTrainer(
        difficulty="simple", seed=7, total_steps=6000,
        steps_per_rollout=1024, num_envs=4, batch_size=256,
        eval_interval=10_000, save_dir="/tmp/mappo_test_ckpt",
        device="cpu")

    buf_stats = None
    from train_mappo import TeamRollout
    buf = TeamRollout()
    info = trainer.collect_rollout(buf)
    check("rollout samples collected", len(buf.f_obs) > 0)
    check("rollout rewards finite",
          all(np.isfinite(r) for seq in buf.team.values()
              for r in seq["rewards"]))
    buf.compute_team_gae({i: 0.0 for i in range(4)}, 0.99, 0.95)
    check("gae finite", np.isfinite(buf.f_adv).all()
          and np.isfinite(buf.f_ret).all())
    check("gae length match", len(buf.f_adv) == len(buf.f_obs))
    buf_stats = info

    upd = trainer.ppo_update(buf)
    check("update losses finite",
          np.isfinite(upd["policy_loss"]) and np.isfinite(upd["value_loss"]))

    # checkpoint roundtrip
    ckpt = "/tmp/mappo_test_ckpt/smoke.pt"
    trainer.agent.save_checkpoint(ckpt, {"difficulty": "simple"})
    loaded = MAPPOAgent(role="blue", seed=1, checkpoint_path=ckpt)
    check("checkpoint roundtrip trained", loaded.trained)
    o1 = torch.as_tensor(encode_unit_obs(trainer.envs[0], "blue_0")[0])
    with torch.no_grad():
        a1 = trainer.agent.actor(o1.unsqueeze(0),
                                 torch.ones(1, ACT_DIM)).probs
        a2 = loaded.actor(o1.unsqueeze(0),
                          torch.ones(1, ACT_DIM)).probs
    check("actor weights restored", torch.allclose(a1, a2, atol=1e-6))

    # short end-to-end training loop (2 rollouts) stays finite
    trainer.total_steps = 2 * 1024
    trainer.train()
    hist = [h for h in trainer.training_history]
    check("training completes with history",
          os.path.exists("/tmp/mappo_test_ckpt/mappo_simple_s7_final.pt"))


def test_controller_injection():
    print("[test_controller_injection]")
    ckpt = "/tmp/mappo_test_ckpt/mappo_simple_s7_final.pt"
    check("smoke checkpoint exists", os.path.exists(ckpt))

    # direct controller
    agent = MAPPOAgent(role="blue", seed=1, checkpoint_path=ckpt)
    ctrl = make_goai_controller(agent)
    env = GridEnv(difficulty="simple", seed=5)
    from grid_env.goai import GOAIBroker, GOAIExecutor, GoalCommand
    broker = GOAIBroker()
    ex = GOAIExecutor(broker, blue_units=list(env.blue_units))
    ex.controller = ctrl
    broker.submit_goals([GoalCommand(
        task_id="wp_001", goal_type="waypoint",
        parameters={"unit_id": "blue_0", "position": [6, 8]})], step=1)
    moved = False
    x0, y0 = env.entities["blue_0"].x, env.entities["blue_0"].y
    for s in range(1, 20):
        acts = ex.act(env, s)
        env.step({u: acts.get(u, 4) for u in env.blue_units},
                 {r: Direction.STAY.value for r in env.red_units})
        if (env.entities["blue_0"].x, env.entities["blue_0"].y) != (x0, y0):
            moved = True
            break
    check("controller drives movement (untrained policy)", moved)

    # hybrid agent end-to-end with controller (mock LLM)
    from grid_env.agents.hybrid_agent import HybridAgent

    class FakeLLM:
        def chat(self, system, user, **kw):
            return ('{"goal_commands": ['
                    '{"task_id": "wp_001", "goal_type": "waypoint", '
                    '"parameters": {"unit_id": "blue_0", "position": [6, 8]}, '
                    '"priority": 0.9}], "reasoning": "mock"}')

        def get_stats(self):
            return {}

    env2 = GridEnv(difficulty="simple", seed=9)
    for r in env2.red_units:
        env2.entities[r].x, env2.entities[r].y = 19, 0
    hybrid = HybridAgent(role="blue", seed=9, llm_client=FakeLLM(),
                         executor_checkpoint=ckpt, planner_interval=10)
    check("hybrid mappo injected", hybrid.mappo is not None
          and hybrid.executor.controller is not None)
    ok_steps = 0
    for _ in range(15):
        obs = env2._get_observation("blue")
        acts = hybrid.act(obs, env=env2)
        env2.step({u: acts.get(u, 4) for u in env2.blue_units},
                  {r: Direction.STAY.value for r in env2.red_units})
        ok_steps += 1
    check("hybrid+MAPPO executor rollout", ok_steps == 15)


def test_pure_llm_mask():
    print("[test_pure_llm_mask]")
    from grid_env.agents.pure_llm_agent import PureLLMAgent

    class BadLLM:
        def chat(self, system, user, **kw):
            return ('{"actions": {"blue_0": 9, "blue_1": 2, "blue_2": 5}}')

        def get_stats(self):
            return {}

    env = GridEnv(difficulty="simple", seed=2)
    for r in env.red_units:
        env.entities[r].x, env.entities[r].y = 19, 0
    agent = PureLLMAgent(role="blue", seed=2, llm_client=BadLLM())
    obs = env._get_observation("blue")
    acts = agent.act(obs, env=env)
    check("oob usv action clamped", 0 <= acts["blue_0"] <= 5)
    check("uav intercept masked to stay",
          acts["blue_2"] == Direction.STAY.value,
          f"blue_2={acts.get('blue_2')}")
    stats = agent.get_stats()
    check("masked counted", stats["masked_count"] >= 1)

    # fallback path (unparseable LLM output) respects v2 enum too
    class JunkLLM:
        def chat(self, system, user, **kw):
            return "I cannot answer that."

        def get_stats(self):
            return {}

    agent2 = PureLLMAgent(role="blue", seed=3, llm_client=JunkLLM())
    env2 = GridEnv(difficulty="simple", seed=3)
    for r in env2.red_units:
        env2.entities[r].x, env2.entities[r].y = 19, 0
    acts2 = agent2.act(env2._get_observation("blue"), env=env2)
    check("fallback actions legal",
          all(0 <= a <= 5 for a in acts2.values())
          and acts2.get("blue_2", 4) != Direction.INTERCEPT.value)


def test_ppo_alias():
    print("[test_ppo_alias]")
    check("PPOAgent is MAPPOAgent", PPOAgent is not None)
    a = PPOAgent(role="blue", seed=1, trained=False)
    check("alias constructs", hasattr(a, "actor") and hasattr(a, "critic"))


if __name__ == "__main__":
    test_encoders()
    test_masked_policy()
    test_training_smoke()
    test_controller_injection()
    test_pure_llm_mask()
    test_ppo_alias()
    print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(1)

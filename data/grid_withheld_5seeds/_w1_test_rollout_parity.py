"""Compare submitted commands in rollout and evaluation with identical policy outputs."""
from __future__ import annotations

import argparse
import json
import difflib
import hashlib
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import patch

import numpy as np

from attack_driver import load_attack_profile_data
from ie_rl_env import IERlEnv
from ie_rl_policy import load_theta, numpy_sample
from ie_rl_train import _make_goal_source, initial_goal_observation
from run_episode import _build_defender, build_parser
from llm_client_hifi import LLMClient


def run(theta, scenario, training, ticks, learned=False, stochastic=False,
        goal_source="rule", transcript=None, replay=False):
    weights = load_theta(theta) if learned else None
    policy_rng = np.random.default_rng(3101)
    env = IERlEnv(scenario, seed=3101, goal_features=True,
                  speed_source="legacy_tags", max_ticks=ticks)
    batches = []
    observations = []
    prompt_mismatches = []
    try:
        if training:
            provider, hook, agent = _make_goal_source(env, {
                "theta": str(theta), "goal_source": goal_source, "seed": 3101,
                "speed_source": "legacy_tags", "decision_interval": 5,
                "plan_interval": 10}, scenario)
            env.goal_provider, env.pre_tick_hook = provider, hook
        else:
            args = build_parser().parse_args([
                "--scenario", scenario, "--planner", f"{goal_source}-rl",
                "--rl-theta", str(theta), "--seed", "3101",
                "--rl-speed-source", "legacy_tags"])
            agent = _build_defender(load_attack_profile_data(scenario), args)
        observation, _ = env.reset()
        original_submit = env._session.submit_actions

        def submit(**kwargs):
            batches.append(kwargs["batch"].model_dump(mode="json"))
            return original_submit(**kwargs)

        def sample(theta, obs, mask, rng, choices, **kwargs):
            observations.append(obs.copy())
            if learned:
                return numpy_sample(weights, obs, mask, policy_rng,
                                    env.num_fire_choices, deterministic=not stochastic,
                                    slot_mask=env.slot_mask() if training else None)
            action = {"heading_xy": np.tile(np.array([0.0, 1.0], dtype=np.float32),
                                            (env.num_units, 1)),
                      "speed": np.full(env.num_units, 0.5, dtype=np.float32),
                      "fire": np.argmax(mask[:, 1:], axis=1) + 1}
            action["fire"][~mask[:, 1:].any(axis=1)] = 0
            return action, 0.0, 0.0, {}

        original_chat = LLMClient.chat
        replay_index = 0

        def chat(client, system_prompt, user_message, **kwargs):
            nonlocal replay_index
            request = {"system": system_prompt, "user": user_message, **kwargs}
            if training and not replay:
                response = original_chat(client, system_prompt, user_message, **kwargs)
                transcript.append({"request": request, "response": response})
                print(f"recorded LLM call {len(transcript)}", flush=True)
            else:
                if replay_index >= len(transcript):
                    raise AssertionError("evaluation requested an extra LLM plan")
                recorded = transcript[replay_index]
                if request != recorded["request"]:
                    print("\n".join(difflib.unified_diff(
                        recorded["request"]["user"].splitlines(), user_message.splitlines(),
                        fromfile="training", tofile="evaluation")), flush=True)
                    prompt_mismatches.append(replay_index)
                response = recorded["response"]
            replay_index += 1
            return response

        with patch.object(env._session, "submit_actions", side_effect=submit), \
                patch("rl_executor.numpy_sample", side_effect=sample), \
                (patch.object(LLMClient, "chat", chat)
                 if goal_source == "llm" else nullcontext()):
            if training:
                observation = initial_goal_observation(env, observation)
                while env._session.world_view.tick < ticks:
                    action, _, _, _ = sample(None, observation, env.fire_mask(), None, 0)
                    observation, _, terminated, truncated, _ = env.step(action)
                    if truncated:
                        observations.append(observation.copy())
                    if terminated or truncated:
                        break
            else:
                while env._session.world_view.tick < ticks:
                    tick = int(env._session.world_view.tick)
                    env._attack(env._session)
                    agent(env._session)
                    receipt = env._session.step(operation_id=f"rl.step.{tick:08d}",
                                                expected_tick=tick)
                    if env._terminal_from(receipt) is not None:
                        break
                else:
                    tick = int(env._session.world_view.tick)
                    env._attack(env._session)
                    agent.plan_once(env._session, tick)
                    successor_env = agent.executor._ensure_env(env._session)
                    observations.append(successor_env.observe().copy())
        if goal_source == "llm" and not training and replay_index != len(transcript):
            raise AssertionError("evaluation skipped recorded LLM plans")
        return batches, observations, prompt_mismatches
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theta", type=Path, required=True)
    parser.add_argument("--scenario", default="IE-01-SINGLE-TARGET")
    parser.add_argument("--ticks", type=int, default=60)
    parser.add_argument("--learned", action="store_true")
    parser.add_argument("--stochastic", action="store_true")
    parser.add_argument("--goal-source", choices=("rule", "llm"), default="rule")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    transcript = json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else []
    training, train_obs, train_prompt_errors = run(args.theta.resolve(), args.scenario, True, args.ticks,
                             args.learned, args.stochastic, args.goal_source, transcript,
                             replay=bool(args.replay))
    if args.output and transcript:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    evaluation, eval_obs, eval_prompt_errors = run(args.theta.resolve(), args.scenario, False, args.ticks,
                              args.learned, args.stochastic, args.goal_source, transcript)
    matching = training == evaluation
    observation_match = len(train_obs) == len(eval_obs) and all(
        np.allclose(train_state, eval_state, atol=1e-6, rtol=0)
        for train_state, eval_state in zip(train_obs, eval_obs))
    result = {"scenario": args.scenario, "ticks": args.ticks,
              "theta_path": str(args.theta.resolve()),
              "theta_sha256": hashlib.sha256(args.theta.read_bytes()).hexdigest(),
              "prompt_mismatches": train_prompt_errors + eval_prompt_errors,
              "goal_source": args.goal_source, "learned": args.learned,
              "stochastic": args.stochastic, "llm_calls": len(transcript),
              "batches_equal": matching, "training_batches": len(training),
                      "observations_equal": observation_match,
                      "evaluation_batches": len(evaluation),
                      "training_decisions": len(train_obs),
                      "evaluation_decisions": len(eval_obs),
                      "observation_count_includes_truncated_successor": True}
    print(json.dumps(result))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not matching:
        for index, (train_batch, eval_batch) in enumerate(zip(training, evaluation)):
            if train_batch != eval_batch:
                print(json.dumps({"first_difference": index, "training": train_batch,
                                  "evaluation": eval_batch}, ensure_ascii=False))
                break
    if not observation_match:
        for index, (train_state, eval_state) in enumerate(zip(train_obs, eval_obs)):
            differences = np.flatnonzero(np.abs(train_state - eval_state) > 1e-6)
            if differences.size:
                print(json.dumps({"observation_difference": index,
                                  "indices": differences.tolist(),
                                  "training": train_state[differences].tolist(),
                                  "evaluation": eval_state[differences].tolist()}))
                break
    return 0 if (matching and observation_match and training
                 and not train_prompt_errors and not eval_prompt_errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""PPO trainer for the IE interception environment (GPU updates, CPU rollouts).

Architecture
------------
    trainer (this process, GPU)                 rollout workers (subprocesses, CPU)
    --------------------------                  ---------------------------------
    holds theta, runs PPO epochs      <----     run episodes with numpy inference
    on flattened batches              ---->     and return transitions as .npz

The simulation is the bottleneck and is CPU/Taichi-bound, so parallelism gains
come from running several simulators at once rather than from the GPU.  Keeping
inference in numpy inside the workers means the GPU is never shared with the
simulators and every update sees large, dense batches.

Windows note: workers construct simulation sessions, so all session work lives
inside ``main()`` behind the ``__main__`` guard.

Usage:
    python ie_rl_train.py --scenario IE-01-SINGLE-TARGET --iterations 30 --workers 4
    python ie_rl_train.py --worker            # internal: subprocess rollout mode
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL))
RUNS = EVAL / "_w1_runs"
RL_DIR = RUNS / "rl"
MARKER = "@@RL_RESULT@@"

# Module level on purpose: importing inside ``main()`` made the name local to the
# whole function, so the ``--log-std-init`` default (evaluated while building the
# parser, i.e. before the import statement runs) raised UnboundLocalError.
# ``ie_rl_policy`` imports only numpy at module scope -- torch stays lazy -- so it
# is safe in the rollout workers too.
from ie_rl_policy import LOG_STD_INIT  # noqa: E402

# The engine checkout (scenarios + catalog) lives here; workers run with it as
# cwd and on PYTHONPATH.
ROOT_FOR_WORKERS = Path(os.environ.get(
    "OPENMDBENCH_ROOT",
    str(Path(__file__).resolve().parents[2] / "source-code" / "source_codes")))


# ---------------------------------------------------------------------------
# worker: one process, N episodes per request, numpy inference only
# ---------------------------------------------------------------------------
def _make_goal_source(env, request: dict, scenario: str):
    """(goal_provider, pre_tick_hook) driving the same planner the eval path uses.

    ``--goal-source rule`` uses ``RulePlannerV2``; ``llm`` uses the full
    ``LLMPlannerV2`` with its rule fallback.  Both are built through
    ``run_episode._build_defender`` rather than re-assembled here, so the planner
    configuration (objective, weapon policies, contact gating, fire doctrine,
    prompt context) is identical to evaluation by construction instead of by
    convention. The planning hook calls only ``plan_once``; the environment
    steps the shared RL executor with the externally sampled PPO action.
    """
    import argparse

    from attack_driver import load_attack_profile_data
    from ie_goal_features import active_by_unit
    from run_episode import _build_defender, build_parser

    kind = str(request.get("goal_source", "rule"))
    profile = load_attack_profile_data(scenario)
    # Derive the namespace from the REAL parser rather than hand-listing fields:
    # a hand-built Namespace died as soon as ``_build_defender`` read one more
    # option (``llm_base_url``), which is a failure mode that would recur on every
    # future CLI addition.
    ns = build_parser().parse_args([])
    ns.planner = "llm" if kind == "llm" else "rule"
    ns.plan_interval = int(request.get("plan_interval", 10))
    ns.seed = int(request.get("seed", 7))
    ns.max_ticks = 10 ** 9          # the harness owns the horizon, not the planner
    ns.llm_max_tokens = int(request.get("llm_max_tokens") or ns.llm_max_tokens)
    agent = _build_defender(profile, ns)
    from rl_executor import RLExecutorV2
    status_executor = RLExecutorV2(
        agent.broker, agent.executor.config,
        theta_path=request["theta"], scenario_id=scenario,
        decision_interval=int(request.get("decision_interval", 5)),
        speed_source=request.get("speed_source"), seed=ns.seed)
    status_executor._env = env
    env.rollout_executor = status_executor

    last_prepared_tick = None

    def pre_tick(tick: int) -> None:
        nonlocal last_prepared_tick
        # Read the session lazily: this hook is installed BEFORE env.reset(), which
        # is what creates the session, so capturing it here would capture None.
        session = env._session
        if session is not None and tick != last_prepared_tick:
            agent.plan_once(session, tick)
            last_prepared_tick = tick

    def provider():
        return active_by_unit(agent.broker.active)

    return provider, pre_tick, agent


def evaluation_policy_args(args, theta_path):
    planner = ("llm-rl" if args.goal_source == "llm" else "rule-rl") \
        if args.goal_features else "rl"
    return ["--planner", planner, "--rl-theta", str(Path(theta_path).resolve()),
            "--decision-interval", str(args.decision_interval),
            "--plan-interval", str(args.plan_interval),
            "--rl-speed-source", str(args.speed_source)]


def initial_goal_observation(env, observation):
    if env.pre_tick_hook is not None:
        tick = int(env._session.world_view.tick)
        env._attack(env._session)
        env._prepared_attack_tick = tick
        env.pre_tick_hook(tick)
        return env.observe()
    return observation


def worker_loop() -> int:
    """Rollout worker: runs under the ENGINE venv (no torch needed).

    The trainer runs under a different interpreter that has CUDA torch, so this
    process must never import torch.  It reports the problem dimensions back so
    the trainer never has to load the engine itself.
    """
    from ie_rl_env import IERlEnv, RewardConfig
    from ie_goal_features import PER_UNIT_WIDTH as GOAL_FEATURE_WIDTH
    from ie_rl_policy import load_theta, numpy_sample, numpy_forward

    env = None
    current = None
    for line in sys.stdin:
        # Tolerate a UTF-8 BOM: piping a request in from PowerShell prepends one,
        # and a worker that dies on it looks exactly like a crashed rollout.
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        if line == "STOP":
            break
        request = json.loads(line)
        if request.get("probe"):
            # The trainer runs under a torch interpreter that must NOT import the
            # engine, so every question about the engine (dimensions, engagement
            # onsets) is answered here, in the worker.
            names = list(request.get("scenarios") or [request["scenario"]])
            rows = []
            for name in names:
                probe_env = IERlEnv(
                    name, seed=int(request.get("seed", 7)),
                    decision_interval=request.get("decision_interval", 5),
                    reward=RewardConfig(),
                    goal_features=bool(request.get("goal_features")),
                    speed_source=str(request.get("speed_source", "catalog")))
                probe_env.reset()
                rows.append({
                    "scenario": name,
                    "obs_dim": probe_env.observation_size,
                    "num_units": probe_env.num_units,
                    "num_fire": probe_env.num_fire_choices,
                    "real_units": probe_env.real_units,
                    "units": [s.entity_id for s in probe_env._slots][:6],
                    "onsets": probe_env.engagement_onsets(),
                })
                probe_env.close()
            print(MARKER + json.dumps({"probe": True, "rows": rows}), flush=True)
            continue

        theta = load_theta(Path(request["theta"]))
        buffers = []
        episode_stats = []
        rng = np.random.default_rng(request["rng_seed"])
        for spec in request["specs"]:
            episode_started = time.perf_counter()
            print(json.dumps({"event": "episode_start", "pid": os.getpid(),
                              "scenario": spec.get("scenario", request["scenario"]),
                              "seed": spec["seed"],
                              "episode_index": spec["episode_index"]}),
                  file=sys.stderr, flush=True)
            # Each episode may name its own scenario: the policy is unit-count
            # invariant, so one set of weights can be trained on a mixture
            # (IE-01 alone only exercises air interception on a single axis and
            # never sees boats, decoys, waves, weather or multi-facility
            # defence).  The env is rebuilt only when the scenario changes.
            scenario = str(spec.get("scenario") or request["scenario"])
            if current != scenario:
                if env is not None:
                    env.close()
                env = IERlEnv(scenario, seed=int(spec["seed"]),
                              decision_interval=request.get("decision_interval", 5),
                              reward=RewardConfig(),
                              goal_features=bool(request.get("goal_features")),
                              speed_source=str(request.get("speed_source", "catalog")))
                current = scenario
            env.seed = int(spec["seed"])
            env.episode_index = int(spec["episode_index"])
            # A per-episode horizon (0 = the scenario's own declared duration).
            # See --full-length-scenarios: the cheap scenarios are won by holding
            # to the end, so truncating them removes the only real win signal.
            limit = spec.get("max_ticks", request.get("max_ticks"))
            env.max_ticks_override = int(limit) if limit else None
            # Fifth arm: drive the SAME planner the evaluation path uses, via
            # AgentV2.plan_once, so the training goal stream and the evaluation goal
            # stream cannot drift apart.  Rebuilt per episode because the broker's
            # active-goal state is per-episode.
            if env.goal_features:
                env.goal_provider, env.pre_tick_hook, goal_agent = _make_goal_source(
                    env, request, scenario)
            else:
                env.goal_provider = None
                env.pre_tick_hook = None
                env.rollout_executor = None
                goal_agent = None
            obs, info = env.reset()
            obs = initial_goal_observation(env, obs)
            obs_buf, lp_buf, val_buf, rew_buf, done_buf = [], [], [], [], []
            term_buf = []
            head_buf, spd_buf, fire_buf, mask_buf, slot_buf = [], [], [], [], []
            # Goal-block liveness.  If the planner is never driven, or the encoder
            # never sees an active goal, the block is all zeros -- the policy then
            # trains on "no plan" and the ablation silently measures a learned
            # executor without a planner, which is the exact failure mode that would
            # make the fifth arm meaningless.
            goal_offset = (6 + env.num_units * 10 + env.max_contacts * 7
                           + env.num_units * env.max_contacts * env.pair_width) \
                if env.goal_features else None
            # The plan block is followed by the (units x targets) assignment mask, so
            # the liveness read must slice its own width instead of reshaping the rest
            # of the observation: `obs[offset:].reshape(num_units, -1)` now yields
            # 44-wide rows that straddle both blocks, which would silently report the
            # wrong has_goal flag.
            goal_block_width = (env.num_units * GOAL_FEATURE_WIDTH
                                if env.goal_features else 0)
            goal_units_seen = goal_decisions = 0
            assign_seen = 0
            ep_return = 0.0
            ep_fires = ep_neutralised = 0
            ep_damage = ep_depth = ep_terminal = 0.0
            ep_own_lost = 0
            ep_truncation = 0.0
            ep_goal = 0.0
            ep_imminent = ep_survival = None
            ep_was_truncated = False
            while True:
                mask = env.fire_mask()
                slots = env.slot_mask()
                if goal_offset is not None:
                    block = obs[goal_offset:goal_offset + goal_block_width].reshape(
                        env.num_units, GOAL_FEATURE_WIDTH)
                    # has_goal is the flag right after the type one-hot
                    from ie_goal_features import N_TYPES
                    goal_units_seen += int((block[:, N_TYPES] > 0.5).sum())
                    goal_decisions += 1
                    # Assignment-mask liveness: how many (unit, target) flags are set.
                    # If this stays 0 the plan never named a visible target and the
                    # goal-shaped reward cannot pay anything.
                    assign_start = goal_offset + goal_block_width
                    assign = obs[assign_start:assign_start
                                 + env.num_units * env.max_contacts]
                    assign_seen += int(np.count_nonzero(assign > 0.5))
                action, logprob, value, _ = numpy_sample(
                    theta, obs, mask, rng, env.num_fire_choices,
                    deterministic=bool(request.get("deterministic")),
                    slot_mask=slots)
                obs_buf.append(obs)
                mask_buf.append(mask)
                slot_buf.append(slots)
                head_buf.append(action["heading_xy"])
                spd_buf.append(action["speed"])
                fire_buf.append(action["fire"])
                lp_buf.append(logprob)
                val_buf.append(value)
                obs, reward, terminated, truncated, step_info = env.step(action)
                rew_buf.append(reward)
                ep_return += reward
                ep_fires += int(step_info.get("fired", 0))
                ep_neutralised += int(step_info.get("raiders_lost", 0))
                ep_damage += float(step_info.get("facility_damage", 0.0))
                # Reward composition, per episode.  Without this the only visible
                # signal is the total, and the whole point of the 2026-09 audit was
                # that a *rising total* hid a *falling scorecard* (reward 5.08 ->
                # 7.86 while IE-01's scorecard went 0.2689 -> 0.1312).  Splitting it
                # by term and by episode type (full-length vs truncated) is what
                # makes a third arbitrage visible instead of inferred.
                ep_depth += float(step_info.get("depth_credit", 0.0))
                ep_terminal += float(step_info.get("terminal_reward", 0.0))
                # Goal-shaped credit (fifth arm only).  Logged separately because it
                # is the term that is supposed to make the plan matter: if it stays
                # at 0 the policy never held a resolvable assignment and the run
                # cannot be measuring "execute the plan" at all.
                ep_goal += float(step_info.get("goal_progress", 0.0)) \
                    + float(step_info.get("goal_shot", 0.0))
                ep_own_lost += int(step_info.get("own_lost", 0))
                if "truncation_bonus" in step_info:
                    ep_truncation = float(step_info["truncation_bonus"])
                    ep_imminent = step_info.get("imminent_threat")
                    ep_survival = step_info.get("facility_survival")
                    ep_was_truncated = True
                done = bool(terminated or truncated)
                done_buf.append(done)
                # GAE must bootstrap through a truncation but not through a real
                # termination; ``done`` alone cannot express that distinction.
                term_buf.append(1.0 if terminated else 0.0)
                if done:
                    break
            bootstrap = (0.0 if terminated else float(numpy_forward(
                theta, obs, env.num_units, env.num_fire_choices)["value"]))
            next_values = np.asarray(val_buf[1:] + [bootstrap], dtype=np.float32)
            buffers.append({
                "obs": np.asarray(obs_buf, dtype=np.float32),
                "mask": np.asarray(mask_buf, dtype=bool),
                "slot": np.asarray(slot_buf, dtype=np.float32),
                "heading": np.asarray(head_buf, dtype=np.float32),
                "speed": np.asarray(spd_buf, dtype=np.float32),
                "fire": np.asarray(fire_buf, dtype=np.int64),
                "logprob": np.asarray(lp_buf, dtype=np.float32),
                "value": np.asarray(val_buf, dtype=np.float32),
                "next_value": next_values,
                "reward": np.asarray(rew_buf, dtype=np.float32),
                "done": np.asarray(done_buf, dtype=np.float32),
                "terminated": np.asarray(term_buf, dtype=np.float32),
            })
            episode_stats.append({
                "seed": int(spec["seed"]),
                "episode_index": int(spec["episode_index"]),
                "seconds": round(time.perf_counter() - episode_started, 3),
                "llm_client": (goal_agent.planner.llm.get_stats()
                               if goal_agent is not None
                               and getattr(goal_agent.planner, "llm", None) is not None
                               else None),
                "return": round(ep_return, 4),
                "steps": len(done_buf),
                "outcome": env.terminal_outcome,
                "scenario": scenario,
                # Diagnostics that expose a collapsed fire head at a glance: a
                # policy that never fires still produces a plausible-looking
                # return, so fire counts must be logged rather than inferred.
                "fires": ep_fires,
                "neutralised": ep_neutralised,
                "facility_damage": round(ep_damage, 4),
                "fire_rate": round(float(np.mean(np.asarray(fire_buf) > 0)), 4)
                             if fire_buf else 0.0,
                # --- reward composition (see the comment at the accumulator) ---
                "truncated": bool(ep_was_truncated),
                "r_kills": ep_neutralised,
                "r_depth": round(ep_depth, 4),
                "r_terminal": round(ep_terminal, 4),
                "r_facility": round(env.reward_cfg.facility_damage * ep_damage, 4),
                "r_own_loss": round(env.reward_cfg.own_loss * ep_own_lost, 4),
                "r_shots": round(-env.reward_cfg.shot_cost * ep_fires, 4),
                "r_truncation": round(ep_truncation, 4),
                "r_goal": round(ep_goal, 4),
                "imminent_at_cut": ep_imminent,
                "survival_at_cut": ep_survival,
                # Goal-block liveness (fifth arm): mean number of units holding an
                # active goal per decision.  0.0 means the plan never reached the
                # network and the run is worthless.
                "goal_units_per_decision": (round(goal_units_seen / goal_decisions, 3)
                                            if goal_decisions and goal_offset is not None
                                            else None),
                # Assignment-mask liveness: mean number of (unit, target) flags lit per
                # decision.  0 means the plan never named a *visible* target, in which
                # case neither the attention block nor the goal-shaped reward can do
                # anything and the run cannot be measuring "execute the plan".
                "assignment_flags_per_decision": (
                    round(assign_seen / goal_decisions, 3)
                    if goal_decisions and goal_offset is not None else None),
                # Health of the goal source itself.  With --goal-source llm a dead
                # endpoint makes LLMPlannerV2 fall back to RulePlannerV2, which would
                # silently swap the training goal distribution mid-run -- a change
                # that looks like nothing at all in the reward.  Recording the counts
                # per episode makes it visible.
                "goal_planner": (dict(goal_agent.planner.get_stats() or {})
                                 if goal_agent is not None
                                 and hasattr(goal_agent.planner, "get_stats")
                                 else None),
            })

            print(json.dumps({"event": "episode_end", "pid": os.getpid(),
                              **episode_stats[-1]}, ensure_ascii=False),
                  file=sys.stderr, flush=True)

        merged = {key: np.concatenate([b[key] for b in buffers], axis=0)
                  for key in buffers[0]}
        out_path = Path(request["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, **merged)
        payload = {"out": str(out_path), "episodes": episode_stats,
                   "transitions": int(merged["reward"].shape[0])}
        print(MARKER + json.dumps(payload), flush=True)
    if env is not None:
        env.close()
    return 0


# ---------------------------------------------------------------------------
# trainer
# ---------------------------------------------------------------------------
def compute_gae(reward, value, done, terminated=None, *, gamma: float,
                lam: float, last_value: float = 0.0, next_values=None):
    """GAE over a batch of concatenated rollout segments.

    ``done`` marks the end of a segment and **stops the recursion**; that is the
    correct boundary here because the batch concatenates episodes from several
    workers, so continuing across a boundary would bootstrap an episode from a
    *different* worker's unrelated episode.

    True termination disables value bootstrapping. Truncation uses the value
    of its own successor observation, while still stopping GAE recursion.
    """
    n = len(reward)
    terminal = np.asarray(done if terminated is None else terminated)
    if next_values is None:
        if np.any((np.asarray(done) > 0) & (terminal == 0)):
            raise ValueError("truncated rollouts require explicit successor values")
        next_values = np.concatenate([np.asarray(value)[1:], [last_value]])
    if len(next_values) != n:
        raise ValueError("successor values must match the rollout length")
    adv = np.zeros(n, dtype=np.float32)
    last_gae = 0.0
    for t in reversed(range(n)):
        next_value = next_values[t]
        nonterminal = 1.0 - float(done[t])
        delta = reward[t] + gamma * next_value * (1.0 - float(terminal[t])) - value[t]
        last_gae = delta + gamma * lam * nonterminal * last_gae
        adv[t] = last_gae
    return adv, adv + value


# Gaussian density / differential-entropy pieces, shared by the log-prob and the
# entropy bonus so the two can never drift apart.
_LOG_2PI = float(np.log(2.0 * np.pi))


def _log_gauss(eps, std):
    """log N(mu + eps*std; mu, std) with the mean already differenced out."""
    import torch
    return -0.5 * eps ** 2 - torch.log(std) - 0.5 * _LOG_2PI


def _log_gauss_entropy(std):
    """Differential entropy of N(0, std): 0.5*log(2*pi*e*std^2)."""
    import torch
    return 0.5 * (1.0 + _LOG_2PI) + torch.log(std)


def ppo_minibatch_loss(model, batch, idx, *, clip: float, entropy_coef: float):
    """PPO loss terms for one minibatch of the direct-output policy.

    Extracted from the training loop so a test can exercise the *real* code path
    instead of a copy.  Two defects have already lived here and one of them was
    invisible for a whole run:

    * indexing ``dist`` (already the minibatch) with the **global** ``idx`` is out
      of bounds as soon as ``minibatch < batch``;
    * the ``ent_xy`` entropy term is ``(B, N, 2)`` and must be reduced over the 2
      heading components **only** -- summing ``(-1, -2)`` (correct for the
      log-prob, which wants one value per transition) collapses the slot axis to
      ``(B,)`` and then cannot broadcast against the ``(B, N)`` slot weights.

    Returns ``(loss, policy_loss, value_loss, entropy, logp)``.
    """
    import torch

    obs, mask, slot = batch["obs"], batch["mask"], batch["slot"]
    # ``dist`` is already the distribution over the minibatch (rows of obs[idx]).
    dist = model.distribution(obs[idx], mask[idx])
    # --- direct-output log-prob -------------------------------------------
    # The stored action is the *post-squash* value the network already emitted
    # (heading as tanh(sin/cos), speed as a fraction of max), so recovering the
    # pre-squash sample needs atanh; the log|Jacobian| of the tanh then corrects
    # the Gaussian density.  Both heads are absolute quantities, not deltas, which
    # is the point of this redesign.
    std_xy = dist["std"][:, :2] + 1e-6           # (N, 2) -- no batch dim
    std_sp = dist["std"][:, 2] + 1e-6            # (N,)
    head_c = batch["heading"][idx].clamp(-0.999999, 0.999999)
    spd_sq = (batch["speed"][idx] * 2 - 1).clamp(-0.999999, 0.999999)
    eps_xy = (torch.atanh(head_c) - dist["heading"]) / std_xy
    eps_sp = (torch.atanh(spd_sq) - dist["speed"]) / std_sp
    logp = ((_log_gauss(eps_xy, std_xy) - torch.log(1 - head_c ** 2 + 1e-6))
            * slot[idx].unsqueeze(-1)).sum((-1, -2))
    logp = logp + ((_log_gauss(eps_sp, std_sp)
                    - torch.log(1 - spd_sq ** 2 + 1e-6)) * slot[idx]).sum(-1)
    logits = dist["fire_logits"]
    logp = logp + (torch.log_softmax(logits, dim=-1).gather(
        -1, batch["fire"][idx].unsqueeze(-1)).squeeze(-1) * slot[idx]).sum(-1)

    ratio = torch.exp(logp - batch["logprob"][idx])
    surr1 = ratio * batch["adv"][idx]
    surr2 = torch.clamp(ratio, 1 - clip, 1 + clip) * batch["adv"][idx]
    policy_loss = -torch.min(surr1, surr2).mean()
    value_loss = ((dist["value"] - batch["ret"][idx]) ** 2).mean()

    # Entropy over **all three** heads.  Charging the entropy bonus to the fire
    # head alone (the previous behaviour) left the heading/speed heads free to
    # collapse to a fixed point with nothing pushing back, which is exactly the
    # failure the fire head had already shown.
    probs = torch.softmax(logits, dim=-1)
    ent_fire = -(probs * torch.log(probs + 1e-9)).sum(-1)          # (B, N)
    ent_xy = (_log_gauss_entropy(std_xy)
              + torch.log(1 - head_c ** 2 + 1e-6))                 # (B, N, 2)
    ent_sp = (_log_gauss_entropy(std_sp)
              + torch.log(1 - spd_sq ** 2 + 1e-6))                 # (B, N)
    # Average over **active slots only**: a padded slot still emits outputs and
    # still carries log_std, so a plain ``.mean()`` would let those phantom slots
    # push the shared log_std for no reason.
    ent_num = (ent_fire * slot[idx]
               + (ent_xy * slot[idx].unsqueeze(-1)).sum(-1)         # reduce the 2
               + ent_sp * slot[idx])                                # heading comps
    entropy = ent_num.sum() / slot[idx].sum().clamp(min=1.0)

    loss = policy_loss + 0.5 * value_loss - entropy_coef * entropy
    return loss, policy_loss, value_loss, entropy, logp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--scenario", default="IE-01-SINGLE-TARGET")
    parser.add_argument("--scenarios", nargs="*", default=None,
                        help="混合训练的场景列表（轮流采样）。留空则只训 --scenario。"
                             "IE-01 单独训练只覆盖'单轴/纯空中/单设施'，"
                             "见文档里的行为覆盖表；要覆盖对海、诱饵、多轴、波次、"
                             "气象、多设施，必须给多个场景。列表里重复写某个场景即加权。")
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--episodes-per-iter", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--decision-interval", type=int, default=5)
    parser.add_argument("--max-ticks", type=int, default=300,
                        help="截断回合长度：全长训练不可行（实测 IE-01 单局 27 s）")
    parser.add_argument("--full-length-scenarios", nargs="*", default=None,
                        help="这些场景**跑到场景声明的全长**，不受 --max-ticks 截断。"
                             "必要性：IE-01/02/03 的规则臂是靠'守满全程'取胜的"
                             "（rule.intruders-destroyed 很少触发），截断到 450 tick 时"
                             "这些场景**永远不可能出现 defender_success**，训练信号只剩"
                             "截断奖励，而评测是全长 —— 训练与评测的目标就不是同一件事。"
                             "这三个场景全长只要 27/29/63 s，比贵场景便宜一个量级，"
                             "所以全长是划算的；贵场景（IE-04..07）继续截断。")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--lam", type=float, default=0.95)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatch", type=int, default=1024)
    parser.add_argument("--entropy-coef", type=float, default=0.02,
                        help="熵正则。**注意这个系数现在同时作用在三个头上**："
                             "48 个连续分量（16 槽 × (2 航向 + 1 速度)）+ 16×21 的分类。"
                             "熵奖励对连续头是 log σ 的增函数，实测 coef=0.05 时"
                             "d(熵)/d(log σ)=0.05×48≈2.4，足以抵消策略梯度，"
                             "于是 log_std 13 轮几乎不动（均值 0.0031 ⇒ σ=1.003），"
                             "航向近似每步随机。降到 0.02 保留'防开火头塌缩'的作用，"
                             "同时让连续头能自己变尖。")
    parser.add_argument("--log-std-init", type=float, default=LOG_STD_INIT,
                        help="连续头的初始 log σ（**fresh 与 resume 都套用**）。"
                             "默认来自 ie_rl_policy.LOG_STD_INIT=-1.5 ⇒ σ≈0.22。"
                             "旧默认 0.0（σ=1.0）实测让航向近似随机、学不动。")
    parser.add_argument("--goal-features", action="store_true",
                        help="第五臂（LLM 规划 + RL 执行层）训练：把 LLM 的目标编码成"
                             "每单元 24 维特征块（观测 2866→3250）。")
    parser.add_argument("--goal-source", default="rule", choices=("rule", "llm"),
                        help="训练时目标的来源：rule=RulePlannerV2（免费、确定，用于"
                             "验证管线）；llm=与评测完全同一套 LLMPlannerV2"
                             "（忠实但要调千问，慢且依赖端点可用）。")
    parser.add_argument("--speed-source", default="catalog",
                        choices=("catalog", "legacy_tags"),
                        help="速度包线来源。catalog=单位真实 max_speed_mps（空 80/水 10）；"
                             "legacy_tags=规则执行器的标签表（空 40/水 8，即已记录三臂"
                             "基线所用的约定）。**消融两侧必须同值**，否则测的是速度表。")
    parser.add_argument("--plan-interval", type=int, default=10,
                        help="目标来源的规划间隔（与评测路径同口径）")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--train-seed-base", type=int, default=1000,
                        help="训练回合使用的引擎种子起点。**故意与评测种子集"
                             "（7/11/13/17/19，即 rule 臂 p18 五种子基线）不相交**："
                             "rule / hybrid / pure-LLM 三臂都没有训练，如果 RL 在评测"
                             "种子上训练过，它就见过那一次命中判定抽样，四臂对照不再公平。"
                             "引擎的命中判定种子 = sha256(resolved_hash, session_id, "
                             "missile_id, tick)，session_id 含 episode_index，所以每局"
                             "仍然各不相同；这里只换种子集合而不换难度。")
    parser.add_argument("--train-seed-span", type=int, default=5,
                        help="训练种子循环长度：每局取 "
                             "train_seed_base + (episode_index %% span)，"
                             "使策略见到 5 种命中判定抽样，而不是把单一抽样的几何背下来。")
    parser.add_argument("--tag", default="rl1")
    parser.add_argument("--resume", default=None)
    parser.add_argument("--worker-python", default=None,
                        help="跑 rollout worker 的解释器。默认用引擎 venv 的 python —— "
                             "worker 需要引擎（Taichi/MMG）但不需要 torch；"
                             "而本训练器需要 CUDA torch，通常跑在另一个 conda 环境里，"
                             "所以两者必须分开指定。")
    parser.add_argument("--eval-every", type=int, default=10,
                        help="每 N 轮用**真实记分卡**评测一次（0=不评测）。"
                             "训练奖励 != 记分卡，不看这个就无法判断被评测的指标是否在改善。")
    parser.add_argument("--eval-scenarios", nargs="*", default=None,
                        help="评测场景；默认取混合里最便宜的两个 + 一个中等成本场景。"
                             "留作零样本测试的场景（如 IE-08）可在这里单独加。")
    parser.add_argument("--eval-max-ticks", type=int, default=0,
                        help="评测截断（0=按场景全长，评测必须与另外三臂同口径）")
    args = parser.parse_args()

    if args.worker:
        return worker_loop()

    import torch

    from ie_rl_policy import (build_torch_policy,
                              export_theta_from_torch, init_theta, load_theta,
                              load_theta_into_torch, save_theta)

    # Provenance travels with the weights (see ie_rl_policy.META_FIELDS and
    # ARM5_LLM_RL_EXECUTOR_DESIGN.md §14.18).  Two of these settings -- the speed
    # convention and whether the plan block is in the observation -- can be flipped
    # on the evaluation side without any error, and the only symptom is an arm that
    # "happens to score lower".  That already cost one discarded batch
    # (`theta_rl_legacy2` trained with legacy_tags, evaluated with catalog), so it
    # is recorded at every save rather than reconstructed from a shell history.
    ckpt_meta = {
        "rollout_semantics": "shared_rl_executor_reward_v9",
        "goal_progress_same_assignment_only": True,
        "truncation_bootstrap": "successor_observation_value",
        "truncation_standing_reward": False,
        "truncation_successor_goals": True,
        "goal_hook_once_per_tick": True,
        "rl_waypoint_3d_status": True,
        "speed_source": args.speed_source,
        "goal_features": bool(args.goal_features),
        "decision_interval": int(args.decision_interval),
        "log_std_init": float(args.log_std_init),
        "tag": str(args.tag),
        "goal_source": str(args.goal_source),
        "train_seed_base": int(args.train_seed_base),
        "train_seed_span": int(args.train_seed_span),
        "scenarios": [str(s) for s in (args.scenarios or [args.scenario])],
        "provenance": "recorded",
        "plan_interval": int(args.plan_interval),
        "source_sha256": {
            name: hashlib.sha256((EVAL / name).read_bytes()).hexdigest()
            for name in ("ie_rl_train.py", "ie_rl_env.py", "ie_rl_policy.py",
                         "ie_goal_features.py", "rl_executor.py", "v2_agent.py",
                         "llm_planner.py", "llm_client_hifi.py", "run_episode.py")
        },
    }

    # Worker interpreter: needs the ENGINE (Taichi/MMG/pydantic) but must not
    # need torch.  The engine venv lives next to the source tree, NOT inside
    # OPENMDBENCH_ROOT, so the default is resolved from the known layout and then
    # verified -- a wrong path fails as WinError 2 deep inside subprocess
    # otherwise, which is hard to read.
    candidates = [
        args.worker_python,
        str(Path(os.environ["OPENMDBENCH_ROOT"]).parents[1] / ".venv"
            / "Scripts" / "python.exe") if os.environ.get("OPENMDBENCH_ROOT") else None,
        r"C:\Code\source-code\source_codes\.venv\Scripts\python.exe",
    ]
    engine_python = next((c for c in candidates if c and Path(c).is_file()), None)
    if engine_python is None:
        print("!! 找不到跑 worker 的引擎 venv python，请用 --worker-python 指定。"
              f"候选：{candidates}")
        return 2

    mixture = list(args.scenarios) if args.scenarios else [args.scenario]
    full_length = {str(name) for name in (args.full_length_scenarios or ())}
    unknown = full_length - set(mixture)
    if unknown:
        print(f"!! --full-length-scenarios 里有不在混合里的场景：{sorted(unknown)}")
        return 2
    # Rough per-episode cost ranking used only for LPT load balancing; the exact
    # numbers do not matter, only the ordering by entity count and duration.
    cost_rank = {name: float(index) for index, name in enumerate(
        sorted(mixture, key=lambda s: (s.startswith("MD-AD-006"),
                                       "SURFACE" in s, s)))}

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        print("!! 警告：CUDA 不可用，退回 CPU 训练", flush=True)
    RL_DIR.mkdir(parents=True, exist_ok=True)
    theta_path = RL_DIR / f"theta_{args.tag}.npz"
    log_path = RL_DIR / f"train_{args.tag}.jsonl"

    # --- persistent rollout workers (engine venv, no torch) ---------------
    world = dict(os.environ)
    world["PYTHONPATH"] = str(EVAL) + os.pathsep + world.get("PYTHONPATH", "")
    engine_root = str(ROOT_FOR_WORKERS)
    world["OPENMDBENCH_ROOT"] = engine_root
    world["PYTHONPATH"] = (str(EVAL) + os.pathsep + engine_root + os.pathsep
                           + world.get("PYTHONPATH", ""))
    workers = []
    worker_logs = []
    for _index in range(max(1, args.workers)):
        # stderr goes to a file rather than DEVNULL: a worker that dies mid-run
        # produced only "rollout worker died" with no cause, which is exactly how
        # the earlier traceback was lost.  The tail is printed on failure.
        log_path_w = RL_DIR / f"worker_{args.tag}_{_index}.log"
        handle = open(log_path_w, "w", encoding="utf-8", errors="replace")
        worker_logs.append((log_path_w, handle))
        proc = subprocess.Popen(
            [engine_python, "-u", str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=handle,
            text=True, cwd=engine_root, env=world)
        workers.append(proc)
    print(f"spawned {len(workers)} rollout workers via {engine_python}", flush=True)

    def worker_tail(worker_index: int, lines: int = 30) -> str:
        path, handle = worker_logs[worker_index]
        try:
            handle.flush()
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return "\n".join(text.strip().splitlines()[-lines:])

    def ask(requests: list[dict]) -> list[dict]:
        for worker_index, proc in enumerate(workers):
            proc.stdin.write(json.dumps(requests[worker_index]) + "\n")
            proc.stdin.flush()
        out = []
        for worker_index, proc in enumerate(workers):
            while True:
                line = proc.stdout.readline()
                if not line:
                    tail = worker_tail(worker_index)
                    raise RuntimeError(
                        f"rollout worker {worker_index} died "
                        f"(exit={proc.poll()}); stderr tail "
                        f"({worker_logs[worker_index][0].name}):\n{tail}")
                if line.startswith(MARKER):
                    out.append(json.loads(line[len(MARKER):]))
                    break
        return out

    try:
        # --- discover dimensions + engagement onsets, in the worker --------
        probe = ask([{"probe": True, "scenarios": sorted(set(mixture)),
                      "seed": args.train_seed_base,
                      "decision_interval": args.decision_interval,
                      "goal_features": bool(args.goal_features),
                      "speed_source": args.speed_source,
                      "specs": []} for _ in workers])[0]
        rows = probe["rows"]
        obs_dim = int(rows[0]["obs_dim"])
        num_units = int(rows[0]["num_units"])
        num_fire = int(rows[0]["num_fire"])
        print(f"scenario(s)={len(set(mixture))} 个  obs_dim={obs_dim} "
              f"units={num_units} fire_choices={num_fire} device={device}", flush=True)
        if len({r["obs_dim"] for r in rows}) != 1:
            print("!! 观测维不一致，策略无法跨场景共用：",
                  {r["scenario"]: r["obs_dim"] for r in rows})
            return 2

        # --- refuse a truncation that would cut out the engagement ---------
        # A cut before the LAST raider becomes engageable silently drops that
        # part of the fight: measured with a uniform 300-tick cut, IE-04's air
        # element (onset ~242) survived but IE-08's second wave (spawn t600)
        # never appeared -- two of eight scenarios would have contributed an
        # empty rollout at full simulation cost.
        print(f"  {'场景':<26}{'真实单元':>9}{'最早':>6}{'最晚':>6}{'来袭者':>7}"
              f"{'截断':>8}", flush=True)
        too_short = []
        for row in rows:
            onsets = row["onsets"]
            limit = 0 if row["scenario"] in full_length else args.max_ticks
            mark = ""
            if limit and onsets["latest"] >= limit:
                mark = "  <-- 会被截断切掉"
                too_short.append(f"{row['scenario']}(最晚 t{onsets['latest']})")
            print(f"  {row['scenario']:<26}{row['real_units']:>9}"
                  f"{onsets['earliest']:>6}{onsets['latest']:>6}"
                  f"{onsets['raiders']:>7}"
                  f"{('全长' if not limit else str(limit)):>8}{mark}", flush=True)
        if too_short:
            print("!! 截断短于'最后一个来袭者进入射程'，以下场景的交战会被整段切掉，"
                  "拒绝启动： " + ", ".join(too_short), flush=True)
            print(f"   当前 --max-ticks={args.max_ticks}。请提高，"
                  f"或从 --scenarios 中移除这些场景。", flush=True)
            return 2

        rng = np.random.default_rng(args.seed)
        if args.resume and Path(args.resume).is_file():
            theta = load_theta(Path(args.resume))
            print(f"resumed theta from {args.resume}", flush=True)
        else:
            theta = init_theta(rng, obs_dim, num_units, num_fire)
        # Applied on resume too, and deliberately so: a checkpoint carries the
        # log_std the old run was stuck at, so resuming without this would resume
        # the very action-noise problem the flag exists to fix.
        theta["log_std"] = np.full_like(theta["log_std"], float(args.log_std_init))
        save_theta(theta_path, theta, {**ckpt_meta, "obs_dim": int(obs_dim),
                                       "num_units": int(num_units),
                                       "num_fire_choices": int(num_fire),
                                       "stage": "init"})
        print(f"log_std init = {args.log_std_init:.2f} (sigma = "
              f"{float(np.exp(args.log_std_init)):.3f}); "
              f"entropy_coef = {args.entropy_coef}", flush=True)

        model = build_torch_policy(obs_dim, num_units, num_fire).to(device)
        optimiser = torch.optim.Adam(model.parameters(), lr=args.lr)
        load_theta_into_torch(model, theta)

        episode_counter = 0
        history = []
        eval_scenarios = (args.eval_scenarios if args.eval_scenarios
                          else mixture[:2] + [mixture[-1]])

        def evaluate(tag_suffix: str) -> list[dict[str, Any]]:
            """Full-length evaluation through the harness' own scoring path.

            Spawns the matching learned-policy arm under the engine interpreter
            so the RL arm is scored by exactly the same code as the other three
            arms.  Without this the only visible signal is the training reward,
            which is a *different* objective from the reported scorecard.
            """
            rows = []
            for name in eval_scenarios:
                out = RL_DIR / f"eval_{args.tag}_{tag_suffix}_{name}.json"
                cmd = [engine_python, "-u", str(EVAL / "run_episode.py"),
                       "--scenario", name,
                       "--seed", str(args.seed), "--output", str(out),
                       *evaluation_policy_args(args, theta_path)]
                if args.eval_max_ticks:
                    cmd += ["--max-ticks", str(args.eval_max_ticks)]
                # The in-training evaluation must use the TRAINING convention, not
                # the evaluator's default; without pinning it the curriculum's own
                # scorecard readings are measured under a different speed table than
                # the policy learned (see ie_rl_policy.META_FIELDS).
                # Pass an explicit environment: the venv carries an editable
                # ``openmdbench`` install pointing at a *different* checkout, so
                # a child that only inherits the environment can silently import
                # the wrong engine tree (9 scenarios, no IE set).
                child_env = dict(os.environ)
                child_env["OPENMDBENCH_ROOT"] = str(ROOT_FOR_WORKERS)
                child_env["PYTHONPATH"] = os.pathsep.join(
                    [str(EVAL), str(ROOT_FOR_WORKERS),
                     child_env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
                try:
                    completed = subprocess.run(cmd, capture_output=True, text=True,
                                               cwd=str(ROOT_FOR_WORKERS),
                                               env=child_env, timeout=3600)
                    if not out.is_file():
                        # Surface the child's own stderr: swallowing it made this
                        # failure undiagnosable ("FileNotFoundError" on the
                        # output file, with no reason why the child died).
                        tail = (completed.stderr or completed.stdout or "")
                        tail = " | ".join(tail.strip().splitlines()[-6:])
                        rows.append({"scenario": name, "score": None,
                                     "error": f"exit={completed.returncode}: {tail}"})
                        continue
                    report = json.loads(out.read_text(encoding="utf-8"))
                    card = report.get("strategy_scorecard") or {}
                    # ``run_episode`` writes a report even when the episode dies,
                    # so "the file exists" does not mean "the run was valid".  A
                    # tick-0 abort was once scored 0.3889 by the scorecard and
                    # silently recorded; require real progress plus a decided
                    # terminal state, and surface the reason instead of a number.
                    ticks = int(report.get("ticks_run") or 0)
                    terminal = (card.get("terminal") or {}).get("outcome")
                    if ticks <= 0 or terminal in (None, "undecided") \
                            or report.get("aborted"):
                        rows.append({
                            "scenario": name, "score": None,
                            "error": (f"invalid episode: ticks={ticks} "
                                      f"outcome={terminal} "
                                      f"aborted={str(report.get('aborted'))[:120]}")})
                        continue
                    rows.append({
                        "scenario": name,
                        "score": card.get("defender_score"),
                        "outcome": (card.get("terminal") or {}).get("outcome"),
                        "layers": card.get("layers"),
                        "ticks": report.get("ticks_run"),
                        "fires": report.get("total_fires_defender"),
                    })
                except Exception as error:  # noqa: BLE001
                    rows.append({"scenario": name, "score": None,
                                 "error": f"{type(error).__name__}: {error}"})
            return rows

        for iteration in range(args.iterations):
            started = time.perf_counter()
            # Honour the REQUESTED episode count instead of a rectangular grid.
            # ``per_worker = episodes // workers`` silently dropped the remainder:
            # asking for 7 episodes across 4 workers ran 4, and asking for 3 across
            # 2 ran 2 -- the run looks configured but samples less than it says.
            # LPT then deals the whole list out by descending expected cost, which
            # needs no rectangular assumption at all.
            episode_count = max(len(workers), int(args.episodes_per_iter))
            requests = []
            # Load balance: episode cost spans ~40x across scenarios (IE-01
            # truncated ~10 s vs MD-AD-006 ~440 s), so handing consecutive episodes
            # to consecutive workers makes the slowest worker set the iteration
            # time.  Dealing by *descending expected cost* is the classic LPT fix.
            ordered = sorted(range(episode_count),
                             key=lambda i: -cost_rank[
                                 mixture[(episode_counter + i) % len(mixture)]])
            assignment: list[list[int]] = [[] for _ in workers]
            for position, index in enumerate(ordered):
                assignment[position % len(workers)].append(index)
            for worker_index in range(len(workers)):
                chunk = []
                for index in sorted(assignment[worker_index]):
                    scenario = mixture[(episode_counter + index) % len(mixture)]
                    chunk.append({
                        "scenario": scenario,
                        # Vary the engine seed across episodes (see
                        # --train-seed-base): a single seed per scenario makes every
                        # episode share one geometry AND one combat-RNG draw, which
                        # the policy can memorise instead of learning to fight.
                        "seed": args.train_seed_base
                                + (episode_counter + index) % max(1, args.train_seed_span),
                        "episode_index": episode_counter + index,
                        # 0 = run to the scenario's declared duration
                        "max_ticks": (0 if scenario in full_length
                                      else args.max_ticks),
                    })
                requests.append({
                    "scenario": chunk[0]["scenario"] if chunk else mixture[0],
                    "theta": str(theta_path),
                    "decision_interval": args.decision_interval,
                    "max_ticks": args.max_ticks,
                    "goal_features": bool(args.goal_features),
                    "goal_source": args.goal_source,
                    "plan_interval": args.plan_interval,
                    "speed_source": args.speed_source,
                    "seed": args.train_seed_base,
                    "rng_seed": int(rng.integers(1 << 30)),
                    "specs": chunk,
                    "out": str(RL_DIR / f"rollout_{args.tag}_{worker_index}.npz"),
                })
            # advance exactly once per iteration (was inside the worker loop,
            # which skipped 4x the episode indices and left most of the mixture
            # unsampled)
            episode_counter += episode_count
            # give each worker its own output file
            for index, request in enumerate(requests):
                request["out"] = str(RL_DIR / f"rollout_{args.tag}_{index}.npz")
            results = ask(requests)
            batches = []
            for result in results:
                with np.load(result["out"]) as data:
                    batches.append({k: data[k] for k in data.files})
            data = {key: np.concatenate([b[key] for b in batches], axis=0)
                    for key in batches[0]}

            obs = torch.from_numpy(data["obs"]).to(device)
            mask = torch.from_numpy(data["mask"]).to(device)
            slot = torch.from_numpy(data["slot"]).to(device)
            act_head = torch.from_numpy(data["heading"]).to(device)
            act_spd = torch.from_numpy(data["speed"]).to(device)
            act_fire = torch.from_numpy(data["fire"]).to(device)
            old_logprob = torch.from_numpy(data["logprob"]).to(device)
            reward = data["reward"]
            value_np = data["value"]
            done = data["done"]
            terminated_arr = data.get("terminated", done)
            adv, ret = compute_gae(reward, value_np, done, terminated_arr,
                                   gamma=args.gamma, lam=args.lam,
                                   next_values=data["next_value"])
            adv_t = torch.from_numpy(adv).to(device)
            adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)
            ret_t = torch.from_numpy(ret.astype(np.float32)).to(device)

            total = obs.shape[0]
            policy_loss_sum = value_loss_sum = entropy_sum = 0.0
            loss_batch = {"obs": obs, "mask": mask, "slot": slot,
                          "heading": act_head, "speed": act_spd, "fire": act_fire,
                          "logprob": old_logprob, "adv": adv_t, "ret": ret_t}
            for _epoch in range(args.epochs):
                perm = torch.randperm(total, device=device)
                for start in range(0, total, args.minibatch):
                    idx = perm[start:start + args.minibatch]
                    loss, policy_loss, value_loss, entropy, _logp = \
                        ppo_minibatch_loss(model, loss_batch, idx,
                                           clip=args.clip,
                                           entropy_coef=args.entropy_coef)
                    optimiser.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                    optimiser.step()
                    policy_loss_sum += float(policy_loss.detach())
                    value_loss_sum += float(value_loss.detach())
                    entropy_sum += float(entropy.detach())

            theta = export_theta_from_torch(model)
            save_theta(theta_path, theta, {**ckpt_meta, "obs_dim": int(obs_dim),
                                           "num_units": int(num_units),
                                           "num_fire_choices": int(num_fire),
                                           "iteration": int(iteration),
                                           "stage": "trained"})

            returns = [e["return"] for r in results for e in r["episodes"]]
            outcomes = [e["outcome"] for r in results for e in r["episodes"]]
            episodes = [e for r in results for e in r["episodes"]]

            # Reward composition split by episode type.  Full-length episodes end
            # on the scenario's own terminal rule; truncated ones end on the
            # standing proxy.  Averaging the two together is exactly what hid a
            # 51% scorecard collapse behind a 55% reward rise, so they are
            # reported separately and every reward term is itemised.
            terms = ("r_kills", "r_depth", "r_terminal", "r_facility",
                     "r_own_loss", "r_shots", "r_truncation", "r_goal")

            def compose(subset: list[dict]) -> dict[str, float]:
                if not subset:
                    return {}
                return {term: round(float(np.mean([e.get(term, 0.0)
                                                   for e in subset])), 3)
                        for term in terms}

            full = [e for e in episodes if not e.get("truncated")]
            cut = [e for e in episodes if e.get("truncated")]
            # Goal-source health across the iteration, for the fifth arm.
            #
            # ``RulePlannerV2.get_stats()`` reports only {'planner','task_seq'} --
            # it has no plan_calls/parse_failures/fallback_count at all, so summing
            # those keys yields a hard 0 that is indistinguishable from "the LLM
            # planner ran and never fell back".  Record the planner NAME and use
            # None for keys that planner does not report, so "not applicable" and
            # "zero occurrences" cannot be confused -- the same ambiguity that hid
            # a dead terminal reward and a never-resolving target_id.
            goal_health = None
            planners = {str((e.get("goal_planner") or {}).get("planner"))
                        for e in episodes if e.get("goal_planner")}
            if planners:
                keys = ("plan_calls", "parse_failures", "fallback_count",
                        "stale_plan_reuse")
                goal_health = {"planner": sorted(planners)}
                for key in keys:
                    present = [e["goal_planner"] for e in episodes
                               if e.get("goal_planner") and key in e["goal_planner"]]
                    goal_health[key] = (sum(int(p.get(key) or 0) for p in present)
                                        if present else None)
                goal_health["mean_goal_units_per_decision"] = round(float(np.mean(
                    [e["goal_units_per_decision"] for e in episodes
                     if e.get("goal_units_per_decision") is not None] or [0.0])), 3)
                goal_health["mean_assignment_flags_per_decision"] = round(float(np.mean(
                    [e["assignment_flags_per_decision"] for e in episodes
                     if e.get("assignment_flags_per_decision") is not None] or [0.0])), 3)
                goal_health["mean_r_goal"] = round(float(np.mean(
                    [e.get("r_goal") or 0.0 for e in episodes] or [0.0])), 4)
            record = {
                "iteration": iteration,
                "transitions": int(total),
                "mean_return": round(float(np.mean(returns)), 4),
                "max_return": round(float(np.max(returns)), 4),
                "composition_full_length": compose(full),
                "composition_truncated": compose(cut),
                "n_full_length": len(full),
                "n_truncated": len(cut),
                "goal_source_health": goal_health,
                "mean_steps": round(float(np.mean(
                    [e["steps"] for e in episodes])), 1),
                "defender_success": sum(1 for o in outcomes
                                        if o == "defender_success"),
                "intruder_success": sum(1 for o in outcomes
                                        if o == "intruder_success"),
                # fire-head health: without these two a "never fires" collapse
                # is invisible in the log
                "fires_per_episode": round(float(np.mean(
                    [e["fires"] for e in episodes])), 2),
                "fire_rate": round(float(np.mean(
                    [e["fire_rate"] for e in episodes])), 4),
                "neutralised_per_episode": round(float(np.mean(
                    [e["neutralised"] for e in episodes])), 2),
                "episodes": len(returns),
                "episode_details": episodes,
                "policy_loss": round(policy_loss_sum / max(1, args.epochs), 4),
                "value_loss": round(value_loss_sum / max(1, args.epochs), 4),
                "entropy": round(entropy_sum / max(1, args.epochs), 4),
                # Sigma of the continuous heads.  Without this the action-noise
                # problem was invisible in the log -- it had to be found by
                # opening the .npz by hand 13 iterations later.
                "log_std_mean": round(float(theta["log_std"].mean()), 4),
                "sigma_mean": round(float(np.exp(theta["log_std"]).mean()), 4),
                "seconds": round(time.perf_counter() - started, 1),
                "device": str(device),
            }
            history.append(record)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"[iter {iteration:>3}] return={record['mean_return']:>8.3f} "
                  f"max={record['max_return']:>8.3f} 守住={record['defender_success']}"
                  f"/{record['episodes']} 开火/局={record['fires_per_episode']:>6.2f} "
                  f"开火率={record['fire_rate']:.3f} "
                  f"击杀/局={record['neutralised_per_episode']:>5.2f} "
                  f"熵={record['entropy']:.3f} Vloss={record['value_loss']:.3f} "
                  f"{record['seconds']}s", flush=True)

            if args.eval_every and (iteration + 1) % args.eval_every == 0:
                rows = evaluate(f"it{iteration + 1}")
                summary = "  ".join(
                    f"{r['scenario'].split('-')[0]}={r['score']}"
                    if r.get("score") is not None else
                    f"{r['scenario'].split('-')[0]}=ERR" for r in rows)
                record["eval"] = rows
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"iteration": iteration,
                                             "eval": rows},
                                            ensure_ascii=False) + "\n")
                print(f"    [记分卡评测 @iter {iteration}] {summary}", flush=True)
    finally:
        for proc in workers:
            try:
                proc.stdin.write("STOP\n")
                proc.stdin.flush()
                proc.wait(timeout=20)
            except Exception:
                proc.kill()

    print(f"\n训练完成：{len(history)} 轮；checkpoint = {theta_path}；日志 = {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

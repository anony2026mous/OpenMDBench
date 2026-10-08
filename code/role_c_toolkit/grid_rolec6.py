"""Versioned grid Role-C episodes: six arms, deception, and Goal ablation.

The game and archived agents are loaded from --source without modifying them.
Run one episode per process; this avoids module/torch state leaking between arms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import requests
import subprocess
import sys
import time


ARMS = ("rule-rule", "llm-rule", "rule-rl", "llm-rl", "rl", "pure-llm")
LLM_ARMS = frozenset(("llm-rule", "llm-rl", "pure-llm"))
RL_ARMS = frozenset(("rule-rl", "llm-rl", "rl"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False,
                               default=str) + "\n", encoding="utf-8")


def source_hashes(source: Path) -> dict[str, str]:
    code = source / "code"
    files = [code / "attribution.py", *sorted((code / "grid_env").rglob("*.py"))]
    if not files[0].is_file() or len(files) < 2:
        raise FileNotFoundError(f"Grid source not found: {code}")
    return {str(p.relative_to(source)): digest(p) for p in files}


def audited_observation(obs: dict) -> dict:
    """Audit only the public observation; never inject hidden truth into agents."""
    sit = obs.get("situational_data", {})
    contacts = [*sit.get("detected_contacts", []), *sit.get("unknown_contacts", [])]
    leaks = []
    for c in contacts:
        if any(key in c for key in ("is_real_threat", "real_threat", "decoy", "feint")):
            leaks.append({"contact_id": c.get("id"), "field": "role_truth_key"})
        if any(word in str(c.get("id", "")).lower() for word in ("decoy", "feint")):
            leaks.append({"contact_id": c.get("id"), "field": "role_truth_id"})
    return {"contact_count": len(contacts), "contact_ids": [c.get("id") for c in contacts],
            "leaks": leaks}


def classify_intercepts(intercepts: list[dict], truth: dict[str, dict]) -> dict[str, int]:
    """Only false RED_TRANSPORT targets are feints; scouts are separate."""
    return {
        "feint_hits": sum(truth.get(item["target"], {}).get("type") == "red_transport"
                          and truth[item["target"]]["is_real_threat"] is False
                          for item in intercepts),
        "real_hits": sum(truth.get(item["target"], {}).get("is_real_threat") is True
                         for item in intercepts),
        "scout_hits": sum(truth.get(item["target"], {}).get("type") == "red_scout"
                          for item in intercepts),
    }


def run_one(args: argparse.Namespace) -> int:
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("--output must be a new directory outside --source")
    if args.arm in RL_ARMS and (not args.checkpoint or not args.checkpoint.is_file()):
        raise FileNotFoundError("RL arm requires an existing --checkpoint")
    if args.arm in LLM_ARMS and (not args.base_url or not args.model):
        raise ValueError("LLM arm requires explicit --base-url and --model")
    if args.goal_mode == "hold" and args.arm not in ("rule-rl", "llm-rl"):
        raise ValueError("Goal ablation is defined only for goal-conditioned RL arms")
    before_hashes = source_hashes(source)
    code = source / "code"
    sys.path.insert(0, str(code))
    from grid_env.grid_env import GridEnv, MAX_STEPS
    from grid_env.grid_env import Direction
    from grid_env.goai import GoalCommand
    from grid_env.agents.rule_agent import RuleAgent
    from grid_env.agents.hybrid_agent import HybridAgent
    from grid_env.agents.mappo_agent import MAPPOAgent
    from grid_env.agents.pure_llm_agent import PureLLMAgent, SYSTEM_PROMPT
    from grid_env.agents.llm_client import LLMClient

    class IntervalCorrectedPureLLM(PureLLMAgent):
        """Fix archived modulo-1 scheduling in instrumentation, not source.

        The archived ``step % interval == 1`` condition calls only at step 1
        when interval=1. This wrapper uses ``(step-1) % interval == 0``.
        """

        def act(self, observation, env=None):
            self.step_count += 1
            assets = observation.get("situational_data", {}).get("friendly_assets", [])
            friendly_ids = [a["id"] for a in assets]
            self._kinds = {a["id"]: a.get("unit", "usv") for a in assets}
            if not friendly_ids:
                return {}
            if (self.step_count - 1) % self.call_interval == 0:
                response = self.llm.chat(SYSTEM_PROMPT, self._build_action_prompt(observation),
                                         max_tokens=4096, temperature=0.1)
                self.call_count += 1
                parsed = self._parse_actions(response, friendly_ids)
                self.last_actions = parsed if parsed else self._fallback_actions(observation, env)
            actions = dict(self.last_actions)
            for uid in friendly_ids:
                actions.setdefault(uid, Direction.STAY.value)
            return self._mask_actions(actions)

    output.mkdir(parents=True)
    events_path, requests_path = output / "events.jsonl", output / "requests.jsonl"
    checkpoint_hash = digest(args.checkpoint) if args.checkpoint else None
    agent = None
    env = GridEnv(difficulty=args.difficulty, seed=args.seed, task_mode=args.task_mode)
    observed_ids: set[str] = set()
    leaks: list[dict] = []
    prompt_leaks: list[dict] = []
    submitted: list[dict] = []
    started = time.monotonic()
    aborted = None

    class RecordingClient(LLMClient):
        def chat(self, system_prompt, user_message, max_tokens=512, temperature=0.1):
            call_id = self.total_calls + 1
            payload_text = system_prompt + "\n" + user_message
            if ("is_real_threat" in payload_text or "real_threat" in payload_text or
                    re.search(r"(?i)(?:decoy|feint)[_-]\d+", payload_text)):
                prompt_leaks.append({"call_id": call_id, "reason": "role_truth_in_actual_prompt"})
            request = {"kind": "request", "call_id": call_id, "model": self.model,
                       "base_url": self.base_url, "system": system_prompt,
                       "user": user_message, "max_tokens": max_tokens,
                       "temperature": temperature, "enable_thinking": False}
            with requests_path.open("a", encoding="utf-8") as out:
                out.write(json.dumps(request, ensure_ascii=False) + "\n")
            tic = time.monotonic()
            # The archived grid client omitted this Qwen/vLLM switch.  The
            # 4096-token budget could be consumed by hidden reasoning, leaving
            # an empty final content.  Match the frozen 6.0 client's setting.
            self.total_calls += 1
            body = {"model": self.model,
                    "messages": [{"role": "system", "content": system_prompt},
                                 {"role": "user", "content": user_message}],
                    "max_tokens": max_tokens, "temperature": temperature,
                    "chat_template_kwargs": {"enable_thinking": False}}
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            response = ""
            for attempt in range(self.max_retries + 1):
                try:
                    api = requests.post(f"{self.base_url}/chat/completions",
                                        headers=headers, json=body, timeout=self.timeout)
                    api.raise_for_status()
                    data = api.json()
                    response = data["choices"][0]["message"].get("content") or ""
                    self.total_tokens += (data.get("usage") or {}).get("total_tokens", 0)
                    break
                except Exception:
                    if attempt == self.max_retries:
                        self.errors += 1
                    else:
                        time.sleep(attempt + 1)
            self.total_latency += time.monotonic() - tic
            with requests_path.open("a", encoding="utf-8") as out:
                out.write(json.dumps({"kind": "response", "call_id": call_id,
                                      "text": response, "elapsed_seconds": time.monotonic() - tic,
                                      "empty": not bool(response)}, ensure_ascii=False) + "\n")
            return response

    client = (RecordingClient(base_url=args.base_url, model=args.model,
                              timeout=args.llm_timeout, max_retries=args.llm_retries)
              if args.arm in LLM_ARMS else None)
    if args.arm == "rule-rule":
        agent = RuleAgent(role="blue", seed=args.seed)
    elif args.arm == "llm-rule":
        agent = HybridAgent(role="blue", seed=args.seed, llm_client=client,
                            planner_interval=args.plan_interval)
    elif args.arm == "rule-rl":
        agent = RuleAgent(role="blue", seed=args.seed,
                          executor_checkpoint=str(args.checkpoint.resolve()))
    elif args.arm == "llm-rl":
        agent = HybridAgent(role="blue", seed=args.seed, llm_client=client,
                            planner_interval=args.plan_interval,
                            executor_checkpoint=str(args.checkpoint.resolve()))
    elif args.arm == "rl":
        agent = MAPPOAgent(role="blue", seed=args.seed, trained=True,
                           checkpoint_path=str(args.checkpoint.resolve()))
    else:
        agent = IntervalCorrectedPureLLM(role="blue", seed=args.seed, llm_client=client,
                                         call_interval=args.pure_call_interval)

    # Keep the two planners on the same intervention clock within a matrix.
    if args.arm in ("rule-rule", "rule-rl"):
        agent.plan_interval = args.plan_interval

    if hasattr(agent, "broker"):
        original_submit = agent.broker.submit_goals

        def submit(commands, *, step):
            proposed = [c.to_dict() for c in commands]
            if args.goal_mode == "hold":
                units = sorted({c.parameters.get("unit_id") for c in commands
                                if c.parameters.get("unit_id")})
                commands = [GoalCommand(task_id=f"rolec_hold_{step * 10 + index:03d}",
                                        goal_type="hold",
                                        parameters={"unit_id": unit, "duration": args.plan_interval},
                                        priority=1.0)
                            for index, unit in enumerate(units)]
            issued = [c.to_dict() for c in commands]
            receipt = original_submit(commands, step=step)
            submitted.append({"step": step, "proposed": proposed, "issued": issued,
                              "receipt": receipt})
            return receipt

        agent.broker.submit_goals = submit

    max_steps = min(args.max_steps or MAX_STEPS, MAX_STEPS)
    with events_path.open("x", encoding="utf-8") as stream:
        try:
            for step in range(1, max_steps + 1):
                if env.done:
                    break
                obs = env._get_observation("blue")
                audit = audited_observation(obs)
                observed_ids.update(c for c in audit["contact_ids"] if c)
                leaks.extend({"step": step, **entry} for entry in audit["leaks"])
                prior_submission = len(submitted)
                actions = {k: int(v) for k, v in agent.act(obs, env=env).items()}
                env.step(actions, None)
                env.compute_reward("blue")
                row = {"step": step, "contact_ids": audit["contact_ids"],
                       "actions": actions, "goals": submitted[prior_submission:],
                       "intercepts_to_date": len(env.metrics["intercept_events"]),
                       "done": bool(env.done)}
                stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        except Exception as exc:
            aborted = f"{type(exc).__name__}: {exc}"

    metrics = env.get_episode_metrics()
    truth = {eid: {"is_real_threat": bool(e.is_real_threat),
                   "type": e.entity_type.name.lower(), "team": e.team}
             for eid, e in env.entities.items() if e.team == "red"}
    intercepts = [{**event, "is_real_threat": truth.get(event["target"], {}).get("is_real_threat")}
                  for event in metrics.get("intercept_events", [])]
    hit_counts = classify_intercepts(intercepts, truth)
    feint_hits, real_hits = hit_counts["feint_hits"], hit_counts["real_hits"]
    feints = {eid for eid, item in truth.items()
              if item["type"] == "red_transport" and not item["is_real_threat"]}
    real_transports = {eid for eid, item in truth.items()
                       if item["type"] == "red_transport" and item["is_real_threat"]}
    complete = bool(env.done and aborted is None)
    after_hashes = source_hashes(source)
    if after_hashes != before_hashes:
        aborted = "source_changed_during_episode"
        complete = False
    config = {"seed": args.seed, "difficulty": args.difficulty, "task_mode": args.task_mode,
              "arm": args.arm, "goal_mode": args.goal_mode,
              "plan_interval": args.plan_interval, "pure_call_interval": args.pure_call_interval,
              "max_steps": max_steps, "checkpoint": str(args.checkpoint.resolve()) if args.checkpoint else None,
              "checkpoint_sha256": checkpoint_hash, "base_url": args.base_url if client else None,
              "model": args.model if client else None,
              "pure_llm_schedule": "corrected_(step-1)%interval==0" if args.arm == "pure-llm" else None}
    result = {"schema": "grid-role-c-6-episode@1", "config": config,
              "source_hashes": before_hashes, "instrumentation_sha256": digest(Path(__file__)),
              "complete": complete, "aborted": aborted, "steps": env.step_count,
              "elapsed_seconds": time.monotonic() - started,
              "V": float(metrics["blue_score"]) if complete else None,
              "metrics": metrics, "agent_stats": agent.get_stats() if hasattr(agent, "get_stats") else {},
              "d1": {"input_role_truth_leaks": leaks, "prompt_role_truth_leaks": prompt_leaks,
                     "observed_contact_ids": sorted(observed_ids),
                     "feint_hits": feint_hits, "real_hits": real_hits,
                     "scout_hits": hit_counts["scout_hits"],
                     "feint_total": len(feints), "real_transport_total": len(real_transports),
                     "feint_observed": len(feints & observed_ids),
                     "real_transport_observed": len(real_transports & observed_ids),
                     "intercepts_labeled_offline": intercepts,
                     "truth_labeled_offline_only": truth,
                     "interpretation": "Behavioral selectivity proxy, not a classifier accuracy."},
              "goal_submissions": submitted,
              "events_sha256": digest(events_path),
              "requests_sha256": digest(requests_path) if requests_path.exists() else None}
    write_json(output / "episode.json", result)
    print(json.dumps({"output": str(output), "complete": complete, "V": result["V"],
                      "steps": env.step_count, "feint_hits": feint_hits, "aborted": aborted}))
    return 0 if complete and not leaks and not prompt_leaks else 1


def add_shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--difficulty", choices=("simple", "medium", "complex"), default="medium")
    parser.add_argument("--task-mode", choices=("independent", "sequential", "continuous"),
                        default="continuous")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--plan-interval", type=int, default=10)
    parser.add_argument("--pure-call-interval", type=int, default=1)
    parser.add_argument("--llm-timeout", type=int, default=120)
    parser.add_argument("--llm-retries", type=int, default=2)
    parser.add_argument("--max-steps", type=int)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run", help="Run one versioned grid episode")
    add_shared(one)
    one.add_argument("--output", type=Path, required=True)
    one.add_argument("--seed", type=int, required=True)
    one.add_argument("--arm", choices=ARMS, required=True)
    one.add_argument("--goal-mode", choices=("strong", "hold"), default="strong")
    matrix = sub.add_parser("matrix", help="Run missing cells in a resumable matrix")
    add_shared(matrix)
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--seed", type=int, action="append", required=True)
    matrix.add_argument("--arm", choices=ARMS, action="append")
    matrix.add_argument("--run-arm", choices=ARMS, action="append",
                        help="Execute only these arms now while keeping the full --arm design locked")
    matrix.add_argument("--goal-mode", choices=("strong", "hold"), default="strong")
    matrix.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.plan_interval < 1 or args.pure_call_interval < 1 or args.llm_timeout < 1:
        parser.error("Intervals and timeout must be positive")
    if args.command == "run":
        return run_one(args)
    source, output = args.source.resolve(), args.output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Matrix output must be outside source")
    if output.exists() and not args.resume:
        raise FileExistsError("Output exists; use --resume only for the same campaign")
    output.mkdir(parents=True, exist_ok=True)
    arms = list(dict.fromkeys(args.arm or ARMS))
    run_arms = list(dict.fromkeys(args.run_arm or arms))
    if not set(run_arms).issubset(arms):
        raise ValueError("Every --run-arm must be included in the locked --arm design")
    seeds = list(dict.fromkeys(args.seed))
    spec = {"schema": "grid-role-c-6-matrix@1", "source": str(source),
            "source_hashes": source_hashes(source), "difficulty": args.difficulty,
            "task_mode": args.task_mode, "checkpoint": str(args.checkpoint.resolve()) if args.checkpoint else None,
            "checkpoint_sha256": digest(args.checkpoint) if args.checkpoint else None,
            "base_url": args.base_url, "model": args.model,
            "plan_interval": args.plan_interval, "pure_call_interval": args.pure_call_interval,
            "max_steps": args.max_steps, "goal_mode": args.goal_mode,
            "seeds": seeds, "arms": arms, "implementation_sha256": digest(Path(__file__))}
    spec_path = output / "campaign.json"
    if spec_path.exists():
        if json.loads(spec_path.read_text(encoding="utf-8")) != spec:
            raise ValueError("Resume campaign identity mismatch")
    else:
        write_json(spec_path, spec)
    failures = 0
    for seed in seeds:
        for arm in run_arms:
            stem = f"{args.difficulty}_{args.task_mode}_{arm}_s{seed}_{args.goal_mode}"
            certified = False
            for prior in sorted(p for p in output.glob(stem + "_a*") if p.is_dir()):
                report = prior / "episode.json"
                if report.exists():
                    old = json.loads(report.read_text(encoding="utf-8"))
                    if (old.get("complete") and not old.get("d1", {}).get("input_role_truth_leaks")
                            and not old.get("d1", {}).get("prompt_role_truth_leaks")
                            and old.get("source_hashes") == spec["source_hashes"]
                            and old.get("instrumentation_sha256") == spec["implementation_sha256"]
                            and old.get("config", {}).get("seed") == seed
                            and old.get("config", {}).get("arm") == arm
                            and old.get("config", {}).get("goal_mode") == args.goal_mode):
                        certified = True
                        break
            if certified:
                print(f"SKIP certified {stem}", flush=True)
                continue
            attempts = sorted(p for p in output.glob(stem + "_a*") if p.is_dir())
            target = output / f"{stem}_a{len(attempts) + 1}"
            cmd = [sys.executable, "-B", str(Path(__file__)), "run", "--source", str(source),
                   "--output", str(target), "--seed", str(seed), "--arm", arm,
                   "--difficulty", args.difficulty, "--task-mode", args.task_mode,
                   "--goal-mode", args.goal_mode, "--plan-interval", str(args.plan_interval),
                   "--pure-call-interval", str(args.pure_call_interval),
                   "--llm-timeout", str(args.llm_timeout), "--llm-retries", str(args.llm_retries)]
            if args.checkpoint:
                cmd += ["--checkpoint", str(args.checkpoint.resolve())]
            if args.base_url:
                cmd += ["--base-url", args.base_url]
            if args.model:
                cmd += ["--model", args.model]
            if args.max_steps:
                cmd += ["--max-steps", str(args.max_steps)]
            with (output / f"{stem}_a{len(attempts) + 1}.console.txt").open("x", encoding="utf-8") as log:
                rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
            print(f"{stem} attempt={len(attempts) + 1} exit={rc}", flush=True)
            failures += int(rc != 0)
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())

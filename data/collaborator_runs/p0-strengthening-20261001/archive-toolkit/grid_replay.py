"""Instrument existing grid-game components and replay recorded goal submissions.

Counterfactual references are archived components; their presence does not
independently certify optimality. The optional goal_bound MAPPO adapter is a
new, explicitly labelled contract variant, not the archived deployed policy.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import random
import requests
import sys
import time

import numpy as np


def plain(value):
    if isinstance(value, np.random.RandomState):
        return {"numpy_random_state": plain(value.get_state())}
    if isinstance(value, random.Random):
        return {"python_random_state": plain(value.getstate())}
    if isinstance(value, Enum):
        return plain(value.value)
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((plain(item) for item in value), key=canonical)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unserializable state type: {type(value).__name__}; no silent omission")


def canonical(value) -> str:
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_components(source: Path):
    code = source.resolve() / "code"
    sys.path.insert(0, str(code))
    import attribution
    from grid_env.grid_env import GridEnv, MAX_STEPS
    from grid_env.goai import GOAIBroker, GOAIExecutor, GoalCommand
    if Path(attribution.__file__).resolve() != (code / "attribution.py").resolve():
        raise RuntimeError("Wrong archived component module already imported")
    return attribution, GridEnv, MAX_STEPS, GOAIBroker, GOAIExecutor, GoalCommand


def component_hashes(source: Path) -> dict:
    code = source / "code"
    files = [code / "attribution.py", *sorted((code / "grid_env").rglob("*.py"))]
    return {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def load_decisions(path: Path) -> tuple[list[dict], dict]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("aborted") or report.get("schema") != "role-c-grid-episode@1":
        raise ValueError("Replay requires a complete versioned source episode")
    if not isinstance(report.get("decisions"), list):
        raise ValueError("Source has no decision timeline")
    return report["decisions"], report


def make_goal_bound_controller(controller, rejections: dict):
    """Fall back to GOAI when MAPPO proposes an action illegal for its Goal."""
    def goal_bound(current_env, unit_id, goal_state):
        action = controller(current_env, unit_id, goal_state)
        if action is None:
            return None
        goal_type = goal_state.command.goal_type
        # Existing Grid action codes: 0=STAY, 5=INTERCEPT.
        if ((action == 5 and goal_type != "intercept") or
                (goal_type == "hold" and action != 0)):
            rejections[goal_type] = rejections.get(goal_type, 0) + 1
            return None
        return action
    return goal_bound


def run_episode(source: Path, output: Path, *, seed: int, difficulty: str = "complex",
                task_mode: str = "continuous", planner_kind: str = "rule",
                executor_kind: str = "heuristic", interval: int = 5,
                degraded_p: float = 0.0, replay_from: Path | None = None,
                mappo_checkpoint: Path | None = None,
                llm_base_url: str | None = None, llm_model: str | None = None,
                executor_contract: str = "legacy") -> dict:
    source, output = source.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Output must be new and outside source tree")
    if interval < 1 or not 0 <= degraded_p <= 1:
        raise ValueError("Invalid interval/degradation probability")
    if executor_contract not in ("legacy", "goal_bound"):
        raise ValueError("Unknown executor contract")
    if executor_contract == "goal_bound" and executor_kind != "mappo":
        raise ValueError("Goal-bound controller contract applies only to MAPPO")
    if executor_kind == "mappo" and (mappo_checkpoint is None or not mappo_checkpoint.is_file()):
        raise FileNotFoundError("MAPPO executor requires a checkpoint")
    if planner_kind == "llm" and replay_from is None and (not llm_base_url or not llm_model):
        raise ValueError("LLM planner requires explicit base URL and model")
    attr, GridEnv, max_steps, Broker, Executor, Command = load_components(source)
    hashes = component_hashes(source)
    replay, baseline = None, None
    if replay_from:
        decisions, baseline = load_decisions(replay_from)
        config = baseline["config"]
        if any(config[key] != value for key, value in
               (("seed", seed), ("difficulty", difficulty), ("task_mode", task_mode), ("interval", interval))):
            raise ValueError("Replay environment/clock mismatch")
        if hashes != baseline["source_hashes"]:
            raise ValueError("Component version mismatch")
        replay = {row["step"]: row for row in decisions}
        if len(replay) != len(decisions):
            raise ValueError("Duplicate decision clock")
    else:
        constructors = {"rule": attr.RulePlanner, "random": attr.RandomPlanner, "oracle": attr.OraclePlanner}
        if planner_kind == "llm":
            from grid_env.agents.llm_client import LLMClient

            class RecordingClient(LLMClient):
                def chat(self, system_prompt, user_message, max_tokens=512, temperature=0.1):
                    with (output / "requests.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(canonical({"kind": "request", "system": system_prompt,
                                                "user": user_message, "model": self.model,
                                                "max_tokens": max_tokens, "temperature": temperature,
                                                "enable_thinking": False}) + "\n")
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
                    started = time.monotonic()
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
                    elapsed = time.monotonic() - started
                    self.total_latency += elapsed
                    with (output / "requests.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(canonical({"kind": "response", "text": response,
                                                "elapsed_seconds": elapsed,
                                                "empty": not bool(response)}) + "\n")
                    return response

            client = RecordingClient(base_url=llm_base_url, model=llm_model)
            planner = attr.LLMPlanner(llm_client=client, seed=seed, interval=interval)
        else:
            planner = constructors[planner_kind](seed=seed, interval=interval)
    env = GridEnv(difficulty=difficulty, seed=seed, task_mode=task_mode)
    broker = Broker()
    executor = Executor(broker, blue_units=list(env.blue_units))
    contract_rejections = {}
    if executor_kind == "oracle":
        executor.controller = attr.make_oracle_controller()
    elif executor_kind == "mappo":
        from grid_env.agents.mappo_agent import MAPPOAgent, make_goai_controller
        mappo = MAPPOAgent(role="blue", seed=seed,
                           checkpoint_path=str(mappo_checkpoint.resolve()))
        controller = make_goai_controller(mappo)
        if executor_contract == "goal_bound":
            executor.controller = make_goal_bound_controller(controller, contract_rejections)
        else:
            executor.controller = controller
    elif executor_kind != "heuristic":
        raise ValueError("Unknown executor")
    rng = np.random.RandomState(seed * 7919 + 13)
    decisions_out, steps_out = [], []
    output.mkdir(parents=True)
    aborted = None
    captured_reports = []
    original_post = broker.post_report

    def post(report):
        captured_reports.append(copy.deepcopy(plain(report.to_dict())))
        return original_post(report)

    broker.post_report = post
    last_plan = -(10 ** 9)
    step = 0
    with (output / "events.jsonl").open("x", encoding="utf-8") as stream:
        def log(row):
            stream.write(canonical(row) + "\n")

        log({"kind": "start", "schema": "role-c-grid-trace@1", "seed": seed,
             "initial_env_hash": fingerprint(vars(env)), "interval": interval,
             "replay_from": str(replay_from) if replay_from else None})
        try:
            while not env.done and step < max_steps:
                step += 1
                # Observation calls occur on the same original schedule, but no
                # original planning policy is invoked in replay mode.
                should_plan = step in replay if replay is not None else step - last_plan >= interval
                if should_plan:
                    observation = env._get_observation("blue")
                    if replay is not None:
                        commands = [Command.from_dict(copy.deepcopy(item)) for item in replay[step]["commands"]]
                    else:
                        commands = planner.plan(observation, env, step)
                    issued = copy.deepcopy(plain([cmd.to_dict() for cmd in commands]))
                    receipt = broker.submit_goals(commands, step=step)
                    decision = {"step": step, "commands": issued, "receipt": plain(receipt)}
                    decisions_out.append(decision)
                    log({"kind": "decision", **decision})
                    last_plan = step
                active = [plain(state.command.to_dict()) for state in broker.active.values() if not state.terminal]
                # Recorder truth stays offline. It is never fed to the planner.
                own_before = {uid: plain(env.entities[uid]) for uid in env.blue_units if uid in env.entities}
                actions = executor.act(env, step)
                faults = []
                if degraded_p > 0:
                    for uid in list(actions):
                        ent = env.entities.get(uid)
                        if ent is None:
                            continue
                        if rng.rand() < degraded_p:
                            hi = 4 if ent.unit_kind == "uav" else 5
                            before = actions[uid]
                            actions[uid] = int(rng.randint(0, hi + 1))
                            faults.append({"unit_id": uid, "before": before, "after": actions[uid]})
                env.step(actions, None)
                env.compute_reward("blue")
                own_after = {uid: plain(env.entities[uid]) for uid in env.blue_units if uid in env.entities}
                row = {"kind": "transition", "step": step, "state_before_tick": step - 1,
                       "state_after_tick": step, "active_goals_before_execution": active,
                       "own_before": own_before, "own_after": own_after,
                       "actions_applied": plain(actions), "injected_faults": plain(faults),
                       "goal_reports": captured_reports[:],
                       "full_env_after_sha256": fingerprint(vars(env)),
                       "broker_after_sha256": fingerprint({"active": broker.active, "reports": broker.reports,
                                                            "stats": broker.stats, "infeasible": broker.infeasible_signatures}),
                       "done": bool(env.done)}
                steps_out.append({"step": step, "env_hash": row["full_env_after_sha256"],
                                  "broker_hash": row["broker_after_sha256"],
                                  "actions_hash": fingerprint(actions)})
                log(row)
                captured_reports.clear()
        except Exception as error:
            aborted = f"{type(error).__name__}: {error}"
            log({"kind": "abort", "step": step, "reason": aborted})
        metrics = plain(env.get_episode_metrics())
        log({"kind": "finish", "steps": step, "done": bool(env.done), "aborted": aborted})
    replay_check = None
    if baseline is not None:
        original_steps = baseline["step_fingerprints"]
        differences = [index + 1 for index, (a, b) in enumerate(zip(original_steps, steps_out)) if a != b]
        replay_check = {"same_length": len(original_steps) == len(steps_out),
                        "first_mismatching_step": differences[0] if differences else None,
                        "metrics_identical": canonical(metrics) == canonical(baseline["metrics"]),
                        "decisions_identical": canonical(decisions_out) == canonical(baseline["decisions"]),
                        "applied_decision_commands_match_source": all(
                            row["step"] in replay and canonical(row["commands"]) == canonical(replay[row["step"]]["commands"])
                            for row in decisions_out),
                        "future_decision_count_not_reached": sum(row["step"] > step for row in baseline["decisions"]),
                        "interpretation": "Exact equality required only when executor and fault configuration also match."}
        replay_check["exact_match"] = (not aborted and replay_check["same_length"] and not differences
                                       and replay_check["metrics_identical"] and replay_check["decisions_identical"])
    report = {"schema": "role-c-grid-episode@1", "aborted": aborted,
              "instrumentation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "replay_source": {"path": str(replay_from.resolve()),
                                "sha256": hashlib.sha256(replay_from.read_bytes()).hexdigest()} if replay_from else None,
              "config": {"seed": seed, "difficulty": difficulty, "task_mode": task_mode,
                         "planner": planner_kind if replay is None else "frozen_decision_timeline",
                         "executor": executor_kind, "executor_contract": executor_contract,
                         "interval": interval, "degraded_p": degraded_p,
                         "mappo_checkpoint_sha256": hashlib.sha256(mappo_checkpoint.read_bytes()).hexdigest()
                         if mappo_checkpoint else None,
                         "llm_base_url": llm_base_url if planner_kind == "llm" else None,
                         "llm_model": llm_model if planner_kind == "llm" else None},
              "design": "frozen_decision_replay" if replay is not None else "original_policy_run",
              "source_hashes": hashes, "decisions": decisions_out, "step_fingerprints": steps_out,
              "steps": step, "done": bool(env.done), "metrics": metrics,
              "V": float(metrics["blue_score"]), "replay_check": replay_check,
              "controller_contract_rejections": contract_rejections,
              "reference_optimality_independently_verified": False,
              "trace_sha256": hashlib.sha256((output / "events.jsonl").read_bytes()).hexdigest(),
              "requests_sha256": hashlib.sha256((output / "requests.jsonl").read_bytes()).hexdigest()
              if (output / "requests.jsonl").exists() else None}
    if hashes != component_hashes(source):
        report["aborted"] = "source_changed_during_run"
    (output / "episode.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--difficulty", choices=("simple", "medium", "complex"), default="complex")
    parser.add_argument("--task-mode", choices=("independent", "sequential", "continuous"), default="continuous")
    parser.add_argument("--planner", choices=("rule", "random", "oracle"), default="rule")
    parser.add_argument("--executor", choices=("heuristic", "oracle"), default="heuristic")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--degraded-p", type=float, default=0)
    parser.add_argument("--replay-from", type=Path)
    args = parser.parse_args()
    report = run_episode(args.source, args.output, seed=args.seed, difficulty=args.difficulty,
                         task_mode=args.task_mode, planner_kind=args.planner,
                         executor_kind=args.executor, interval=args.interval,
                         degraded_p=args.degraded_p, replay_from=args.replay_from)
    print(json.dumps({"aborted": report["aborted"], "steps": report["steps"],
                      "replay_check": report["replay_check"], "output": str(args.output)}, ensure_ascii=False))
    return 1 if report["aborted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

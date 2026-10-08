"""Grid planner × executor fault factorial around one unchanged rule stack.

This uses known injected faults to validate layer labels; uncorrupted rule
components are references for the injection experiment, not global oracles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import grid_replay
from grid_fault_replay import selected


def run_episode(source, output, *, seed, difficulty, task_mode, interval,
                planner_dose, executor_dose, replay_from=None):
    if not 0 <= planner_dose <= 1 or not 0 <= executor_dose <= 1:
        raise ValueError("Fault doses must be in [0,1]")
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("New output outside source required")
    attr, GridEnv, max_steps, Broker, Executor, Command = grid_replay.load_components(source)
    from grid_env.grid_env import GRID_SIZE
    original_load, original_planner = grid_replay.load_components, attr.RulePlanner
    events = []

    class Planner:
        def __init__(self, seed, interval):
            self.inner = original_planner(seed=seed, interval=interval)

        def plan(self, obs, env, step):
            commands = self.inner.plan(obs, env, step)
            for command in commands:
                if not selected(seed, step, command.unit_id, "planner_wrong_assignment", planner_dose):
                    continue
                before = command.parameters.get("position")
                if before is not None and len(before) >= 2:
                    after = [GRID_SIZE - 1 - int(before[0]), GRID_SIZE - 1 - int(before[1])]
                    if after == list(before[:2]):
                        after[0] = (after[0] + 1) % GRID_SIZE
                    command.parameters["position"] = after
                    events.append({"layer": "planner", "step": step, "unit_id": command.unit_id,
                                   "task_id": command.task_id, "before_position": before,
                                   "after_position": after})
                elif command.parameters.get("target_id") is not None:
                    before_target = command.parameters["target_id"]
                    command.parameters["target_id"] = "rolec.invalid-contact"
                    events.append({"layer": "planner", "step": step, "unit_id": command.unit_id,
                                   "task_id": command.task_id, "before_target": before_target,
                                   "after_target": "rolec.invalid-contact"})
            return commands

    class HeldExecutor(Executor):
        def act(self, env, step):
            actions = super().act(env, step)
            for unit, action in list(actions.items()):
                if action != 4 and selected(seed, step, unit, "action_hold", executor_dose):
                    actions[unit] = 4
                    events.append({"layer": "executor_action", "step": step,
                                   "unit_id": unit, "before_action": action, "after_action": 4})
            return actions

    def components(_source):
        return attr, GridEnv, max_steps, Broker, HeldExecutor, Command

    grid_replay.load_components = components
    attr.RulePlanner = Planner
    try:
        report = grid_replay.run_episode(source, output, seed=seed, difficulty=difficulty,
                                         task_mode=task_mode, planner_kind="rule",
                                         executor_kind="heuristic", interval=interval,
                                         replay_from=replay_from)
    finally:
        grid_replay.load_components, attr.RulePlanner = original_load, original_planner
    event_path = output / "fault_events.json"
    event_path.write_text(json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["factorial_fault"] = {"planner_dose": planner_dose,
                                 "executor_dose": executor_dose,
                                 "wrapper_sha256": wrapper_hash,
                                 "planner_events": sum(e["layer"] == "planner" for e in events),
                                 "executor_events": sum(e["layer"] == "executor_action" for e in events),
                                 "event_log_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest()}
    if replay_from is not None:
        original = json.loads(Path(replay_from).read_text(encoding="utf-8"))
        prior = original.get("factorial_fault", {})
        report["factorial_fault"]["replay_spec_same"] = (
            prior.get("planner_dose") == planner_dose and
            prior.get("executor_dose") == executor_dose and
            prior.get("wrapper_sha256") == wrapper_hash)
    (output / "episode.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                          encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--difficulty", choices=("simple", "medium", "complex"), default="complex")
    parser.add_argument("--task-mode", choices=("independent", "sequential", "continuous"), default="continuous")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--planner-dose", type=float, required=True)
    parser.add_argument("--executor-dose", type=float, required=True)
    parser.add_argument("--replay-from", type=Path)
    args = parser.parse_args()
    if args.replay_from:
        baseline = json.loads(args.replay_from.read_text(encoding="utf-8"))
        prior = baseline.get("factorial_fault", {})
        wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if (prior.get("planner_dose") != args.planner_dose or
                prior.get("executor_dose") != args.executor_dose or
                prior.get("wrapper_sha256") != wrapper_hash):
            raise ValueError("Replay requires same factorial doses and wrapper version")
    report = run_episode(args.source, args.output, seed=args.seed, difficulty=args.difficulty,
                         task_mode=args.task_mode, interval=args.interval,
                         planner_dose=args.planner_dose, executor_dose=args.executor_dose,
                         replay_from=args.replay_from)
    print(json.dumps({"aborted": report["aborted"], "V": report["V"], "steps": report["steps"],
                      "planner_events": report["factorial_fault"]["planner_events"],
                      "executor_events": report["factorial_fault"]["executor_events"],
                      "replay_exact": (report.get("replay_check") or {}).get("exact_match")}))
    return int(bool(report["aborted"]) or
               (report["replay_check"] is not None and not report["replay_check"]["exact_match"]))


if __name__ == "__main__":
    raise SystemExit(main())

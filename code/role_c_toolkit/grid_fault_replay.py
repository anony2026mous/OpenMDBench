"""Full-grid episode with versioned, reversible layer-boundary fault injection.

The archived engine, planner, broker and executor source files are unchanged.
This produces mechanism/replay evidence; reference-oracle quality is separate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import grid_replay


FAULTS = ("none", "planner_wrong_contact", "interface_drop_fields",
          "interface_drop_goals", "executor_nearest_contact", "action_hold")


def selected(seed, step, unit, fault, dose):
    if not 0.0 <= dose <= 1.0:
        raise ValueError("Fault dose must be in [0,1]")
    key = f"role-c-fault@1:{seed}:{step}:{unit}:{fault}".encode("utf-8")
    threshold = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / 2 ** 64
    return threshold < dose


def run_fault_episode(source, output, *, seed, difficulty, task_mode, interval,
                      case, dose, replay_from=None):
    if case not in FAULTS or not 0.0 <= dose <= 1.0:
        raise ValueError("Unknown fault case or invalid dose")
    if case == "none" and dose != 0.0:
        raise ValueError("Fault-free case has dose zero")
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("New output outside source required")
    attr, GridEnv, max_steps, Broker, Executor, Command = grid_replay.load_components(source)
    original_load, original_planner = grid_replay.load_components, attr.RulePlanner
    events = []

    class FaultPlanner:
        def __init__(self, seed, interval):
            self.inner = original_planner(seed=seed, interval=interval)

        def plan(self, obs, env, step):
            commands = self.inner.plan(obs, env, step)
            if case != "planner_wrong_contact":
                return commands
            contacts = obs.get("situational_data", {}).get("detected_contacts", [])
            wrong = [contact for contact in contacts if contact.get("type") in
                     ("civilian", "civilian_vessel", "unknown", "?")]
            for command in commands:
                current = command.parameters.get("target_id")
                if current is None or not selected(seed, step, command.unit_id, case, dose):
                    continue
                alternatives = [contact for contact in wrong if contact["id"] != current]
                target = (sorted(alternatives, key=lambda item: str(item["id"]))[0]["id"]
                          if alternatives else "rolec.invalid-contact")
                command.parameters["target_id"] = target
                events.append({"layer": "planner", "step": step, "unit_id": command.unit_id,
                               "task_id": command.task_id, "before_target": current, "after_target": target,
                               "target_source": "visible_nonhostile" if alternatives else "invalid_contact_sentinel"})
            return commands

    class FaultBroker(Broker):
        def submit_goals(self, commands, step, **kwargs):
            transformed = []
            for command in commands:
                if not selected(seed, step, command.unit_id, case, dose):
                    transformed.append(command)
                    continue
                if case == "interface_drop_goals":
                    events.append({"layer": "interface_timing", "step": step,
                                   "unit_id": command.unit_id, "task_id": command.task_id,
                                   "effect": "new_goal_dropped_old_active_goal_may_persist"})
                    continue
                if case == "interface_drop_fields":
                    replacement = Command.from_dict(copy.deepcopy(command.to_dict()))
                    before = copy.deepcopy(replacement.parameters)
                    replacement.parameters.pop("target_id", None)
                    replacement.parameters.pop("position", None)
                    replacement.constraints = []
                    replacement.deadline = None
                    if before != replacement.parameters or command.constraints or command.deadline is not None:
                        events.append({"layer": "interface_semantics", "step": step,
                                       "unit_id": command.unit_id, "task_id": command.task_id,
                                       "before_parameters": before,
                                       "after_parameters": copy.deepcopy(replacement.parameters)})
                    transformed.append(replacement)
                    continue
                transformed.append(command)
            return super().submit_goals(transformed, step=step, **kwargs)

    class FaultExecutor(Executor):
        def act(self, env, step):
            changed_targets = []
            if case == "executor_nearest_contact":
                # This observation call occurs in every dose arm of E1,
                # including dose zero, so dose comparisons share its cost/RNG use.
                contacts = env._get_observation("blue").get("situational_data", {}).get("detected_contacts", [])
                for state in self.broker.active.values():
                    command = state.command
                    unit = env.entities.get(command.unit_id) if command.unit_id else None
                    before = command.parameters.get("target_id")
                    if before is None or unit is None or not selected(seed, step, command.unit_id, case, dose):
                        continue
                    alternatives = [contact for contact in contacts if contact["id"] != before]
                    if not alternatives:
                        continue
                    nearest = min(alternatives, key=lambda contact: (
                        abs(contact["position"][0] - unit.x) + abs(contact["position"][1] - unit.y),
                        str(contact["id"])))
                    target = nearest["id"]
                    command.parameters["target_id"] = target
                    changed_targets.append((command, before))
                    events.append({"layer": "executor_assignment", "step": step,
                                   "unit_id": command.unit_id, "task_id": command.task_id,
                                   "before_target": before, "after_target": target})
            try:
                actions = super().act(env, step)
            finally:
                for command, before in changed_targets:
                    command.parameters["target_id"] = before
            if case == "action_hold":
                for unit, action in list(actions.items()):
                    if action != 4 and selected(seed, step, unit, case, dose):
                        actions[unit] = 4
                        events.append({"layer": "action_realization", "step": step,
                                       "unit_id": unit, "before_action": action, "after_action": 4})
            return actions

    def fault_components(_source):
        return attr, GridEnv, max_steps, FaultBroker, FaultExecutor, Command

    grid_replay.load_components = fault_components
    attr.RulePlanner = FaultPlanner
    try:
        report = grid_replay.run_episode(source, output, seed=seed, difficulty=difficulty,
                                         task_mode=task_mode, planner_kind="rule",
                                         executor_kind="heuristic", interval=interval,
                                         replay_from=replay_from)
    finally:
        grid_replay.load_components, attr.RulePlanner = original_load, original_planner
    event_path = output / "fault_events.json"
    event_path.write_text(json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report["fault_injection"] = {"case": case, "dose": dose,
                                  "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                  "fault_event_count": len(events),
                                  "fault_events_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
                                  "replay_fault_spec_same_as_original": None}
    if replay_from is not None:
        original = json.loads(Path(replay_from).read_text(encoding="utf-8"))
        report["fault_injection"]["replay_fault_spec_same_as_original"] = (
            original.get("fault_injection", {}).get("case") == case and
            original.get("fault_injection", {}).get("dose") == dose and
            original.get("fault_injection", {}).get("wrapper_sha256") == report["fault_injection"]["wrapper_sha256"])
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
    parser.add_argument("--case", choices=FAULTS, required=True)
    parser.add_argument("--dose", type=float, required=True)
    parser.add_argument("--replay-from", type=Path)
    args = parser.parse_args()
    report = run_fault_episode(args.source, args.output, seed=args.seed, difficulty=args.difficulty,
                               task_mode=args.task_mode, interval=args.interval, case=args.case,
                               dose=args.dose, replay_from=args.replay_from)
    result = {"aborted": report["aborted"], "V": report["V"], "steps": report["steps"],
              "fault_events": report["fault_injection"]["fault_event_count"],
              "replay_exact": report["replay_check"]["exact_match"] if report["replay_check"] else None}
    print(json.dumps(result, ensure_ascii=False))
    return int(bool(report["aborted"]) or (report["replay_check"] is not None and not report["replay_check"]["exact_match"]))


if __name__ == "__main__":
    raise SystemExit(main())

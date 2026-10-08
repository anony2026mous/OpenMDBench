"""Layer-boundary fault injection on the actual LLM-planner + GOAI path."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import hifi_llm_tier_trace as llm_trace
from hifi_attribution_spec import EXECUTOR_FAULT_CASES, PAPER_FAULT_CASES, selected


FAULTS = (*PAPER_FAULT_CASES, "interface_drop_goals", "interface_weak_fields", "action_hold")


def main() -> int:
    wrapper = argparse.ArgumentParser(add_help=False)
    wrapper.add_argument("--fault-case", choices=FAULTS, required=True)
    wrapper.add_argument("--dose", type=float, required=True)
    wrapper.add_argument("--seed", type=int, required=True)
    wrapper.add_argument("--output", type=Path, required=True)
    args, passthrough = wrapper.parse_known_args()
    if not 0 <= args.dose <= 1:
        raise ValueError("Fault dose must be in [0,1]")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("New output directory required")
    report_baseline = None
    if "--replay-from" in passthrough:
        source = Path(passthrough[passthrough.index("--replay-from") + 1])
        report_baseline = json.loads(source.read_text(encoding="utf-8"))
        fault = report_baseline.get("fault_injection", {})
        wrapper_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if (fault.get("case") != args.fault_case or fault.get("dose") != args.dose or
                fault.get("wrapper_sha256") != wrapper_sha):
            raise ValueError("Replay requires identical fault case, dose and wrapper version")

    events = []
    original_context, original_session = llm_trace.TierTraceContext, llm_trace.TracedSession

    class FaultContext(original_context):
        def attach_agent(self, agent):
            if args.fault_case in ("planner_wrong_contact", "balanced_mild"):
                plan_original = agent.planner.plan

                def plan(*plan_args, **plan_kwargs):
                    goals = plan_original(*plan_args, **plan_kwargs)
                    tick = int(plan_args[1]) if len(plan_args) > 1 else int(plan_kwargs["tick"])
                    for goal in goals:
                        before = goal.parameters.get("target_id")
                        component = "planner" if args.fault_case == "balanced_mild" else ""
                        if before is None or not selected(args.seed, tick, goal.unit_id,
                                                          args.fault_case, args.dose, component):
                            continue
                        goal.parameters["target_id"] = "rolec.invalid-contact"
                        events.append({"layer": "planner", "tick": tick,
                                       "task_id": goal.task_id, "unit_id": goal.unit_id,
                                       "before_target": before,
                                       "after_target": "rolec.invalid-contact"})
                    return goals

                agent.planner.plan = plan
            elif args.fault_case in ("interface_drop_goals", "interface_weak_fields"):
                submit_original = agent.broker.submit_goals

                def submit_goals(commands, step, **kwargs):
                    transformed = []
                    for command in commands:
                        unit = command.unit_id or "none"
                        if not selected(args.seed, step, unit, args.fault_case, args.dose):
                            transformed.append(command)
                            continue
                        if args.fault_case == "interface_drop_goals":
                            events.append({"layer": "interface_timing", "tick": step,
                                           "task_id": command.task_id, "unit_id": command.unit_id,
                                           "effect": "goal_dropped_before_broker"})
                            continue
                        reduced = command.to_granularity("weak")
                        before, after = llm_trace.plain(command), llm_trace.plain(reduced)
                        if before != after:
                            events.append({"layer": "interface_semantics", "tick": step,
                                           "task_id": command.task_id, "unit_id": command.unit_id,
                                           "before": before, "after": after})
                        transformed.append(reduced)
                    return submit_original(transformed, step=step, **kwargs)

                agent.broker.submit_goals = submit_goals
            return super().attach_agent(agent)

    class FaultSession(original_session):
        def submit_actions(self, *call_args, **call_kwargs):
            if args.fault_case not in EXECUTOR_FAULT_CASES:
                return super().submit_actions(*call_args, **call_kwargs)
            batch = call_kwargs.get("batch", call_args[0] if call_args else None)
            if (self._context.agent is None or
                    str(batch.faction_id) != str(self._context.agent.faction_id)):
                return super().submit_actions(*call_args, **call_kwargs)
            tick = int(batch.based_on_tick)
            commands = []
            changed_commands = []
            component = "executor" if args.fault_case == "balanced_mild" else ""
            execution_layer = ("executor" if args.fault_case in ("executor_degradation", "balanced_mild")
                               else "action_realization")
            for command in batch.persistent_commands:
                payload = dict(command.payload)
                if (command.command_type == "navigation" and payload.get("speed_mps", 0) != 0 and
                        selected(args.seed, tick, command.entity_id, args.fault_case, args.dose, component)):
                    before = payload["speed_mps"]
                    payload["speed_mps"] = 0.0
                    command = command.model_copy(update={"payload": payload})
                    changed_commands.append({"layer": execution_layer, "tick": tick,
                                             "unit_id": command.entity_id,
                                             "before_speed_mps": before, "after_speed_mps": 0.0})
                commands.append(command)
            actions, changed_actions = [], []
            for action in batch.discrete_actions:
                if selected(args.seed, tick, action.entity_id, args.fault_case, args.dose, component):
                    changed_actions.append({"layer": execution_layer, "tick": tick,
                                            "unit_id": action.entity_id,
                                            "suppressed_action": action.action_type,
                                            "action_id": action.action_id})
                else:
                    actions.append(action)
            events.extend(changed_commands)
            events.extend(changed_actions)
            if changed_commands or changed_actions:
                batch = batch.model_copy(update={"persistent_commands": tuple(commands),
                                                 "discrete_actions": tuple(actions)})
            if call_args:
                call_args = (batch, *call_args[1:])
            else:
                call_kwargs["batch"] = batch
            return super().submit_actions(*call_args, **call_kwargs)

    llm_trace.TierTraceContext, llm_trace.TracedSession = FaultContext, FaultSession
    old_argv = sys.argv
    sys.argv = [str(Path(llm_trace.__file__)), "--seed", str(args.seed),
                "--output", str(output), *passthrough]
    try:
        code = llm_trace.main()
    finally:
        llm_trace.TierTraceContext, llm_trace.TracedSession = original_context, original_session
        sys.argv = old_argv

    report_path = output / "measurement_episode.json"
    if not report_path.is_file():
        return code or 1
    event_path = output / "fault_events.json"
    event_path.write_text(json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["fault_injection"] = {"case": args.fault_case, "dose": args.dose,
                                 "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                 "event_count": len(events),
                                 "event_log_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
                                 "replay_planner_fault_not_reinvoked":
                                     args.fault_case == "planner_wrong_contact" and report_baseline is not None}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"case": args.fault_case, "dose": args.dose,
                      "events": len(events), "planner": report["config"]["planner"],
                      "aborted": report["aborted"], "ticks": report["ticks_run"],
                      "replay_exact": (report.get("replay_check") or {}).get("exact_match")},
                     ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

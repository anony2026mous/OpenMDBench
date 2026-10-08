"""V2 boundary-fault wrapper around the unchanged high-fidelity trace runner.

Faults are deterministic by seed/tick/unit and applied only to the selected
boundary. This is an injection mechanism pilot, not an oracle attribution test.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

import hifi_trace
from hifi_attribution_spec import EXECUTOR_FAULT_CASES, PAPER_FAULT_CASES, selected

FAULTS = (*PAPER_FAULT_CASES, "interface_drop_goals", "interface_weak_fields", "action_hold")


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--fault-case", choices=FAULTS, required=True)
    parser.add_argument("--dose", type=float, required=True)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--output", required=True, type=Path)
    args, passthrough = parser.parse_known_args()
    if not 0.0 <= args.dose <= 1.0:
        raise ValueError("Dose must be in [0,1]")
    wrapper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if "--replay-from" in passthrough:
        index = passthrough.index("--replay-from")
        if index + 1 >= len(passthrough):
            raise ValueError("Missing replay report path")
        baseline = json.loads(Path(passthrough[index + 1]).read_text(encoding="utf-8"))
        original_fault = baseline.get("fault_injection", {})
        if (original_fault.get("case") != args.fault_case or
                original_fault.get("dose") != args.dose or
                original_fault.get("wrapper_sha256") != wrapper_hash):
            raise ValueError("Replay requires identical fault case, dose, and wrapper version")
    events = []
    original_context, original_session, original_argv = hifi_trace.TraceContext, hifi_trace.TracedSession, sys.argv

    class FaultContext(original_context):
        def attach_agent(self, agent):
            if args.fault_case in ("planner_wrong_contact", "balanced_mild"):
                original_plan = agent.planner.plan

                def plan(*a, **kw):
                    goals = original_plan(*a, **kw)
                    tick = int(a[1]) if len(a) > 1 else int(kw["tick"])
                    for goal in goals:
                        before = goal.parameters.get("target_id")
                        component = "planner" if args.fault_case == "balanced_mild" else ""
                        if before is None or not selected(args.seed, tick, goal.unit_id, args.fault_case,
                                                          args.dose, component):
                            continue
                        goal.parameters["target_id"] = "rolec.invalid-contact"
                        events.append({"layer": "planner", "tick": tick, "task_id": goal.task_id,
                                       "unit_id": goal.unit_id, "before_target": before,
                                       "after_target": "rolec.invalid-contact"})
                    return goals

                agent.planner.plan = plan
            elif args.fault_case in ("interface_drop_goals", "interface_weak_fields"):
                original_submit = agent.broker.submit_goals

                def submit_goals(commands, step, **kw):
                    transformed = []
                    for command in commands:
                        if not selected(args.seed, step, command.unit_id or "none", args.fault_case, args.dose):
                            transformed.append(command)
                            continue
                        if args.fault_case == "interface_drop_goals":
                            events.append({"layer": "interface_timing", "tick": step,
                                           "task_id": command.task_id, "unit_id": command.unit_id,
                                           "effect": "new_goal_dropped_old_active_goal_may_persist"})
                            continue
                        reduced = command.to_granularity("weak")
                        if hifi_trace.plain(reduced) != hifi_trace.plain(command):
                            events.append({"layer": "interface_semantics", "tick": step,
                                           "task_id": command.task_id, "unit_id": command.unit_id,
                                           "before": hifi_trace.plain(command),
                                           "after": hifi_trace.plain(reduced)})
                        transformed.append(reduced)
                    return original_submit(transformed, step=step, **kw)

                agent.broker.submit_goals = submit_goals
            return super().attach_agent(agent)

    class FaultSession(original_session):
        def submit_actions(self, *a, **kw):
            if args.fault_case not in EXECUTOR_FAULT_CASES:
                return super().submit_actions(*a, **kw)
            batch = kw.get("batch", a[0] if a else None)
            # The traced session carries both defenders and the adversarial
            # scripted side. Attribution faults must touch only the measured
            # defender's action boundary, never the opponent's trajectory.
            if self._context.agent is None or str(batch.faction_id) != str(self._context.agent.faction_id):
                return super().submit_actions(*a, **kw)
            tick = batch.based_on_tick
            changed = []
            commands = []
            component = "executor" if args.fault_case == "balanced_mild" else ""
            execution_layer = ("executor" if args.fault_case in ("executor_degradation", "balanced_mild")
                               else "action_realization")
            for command in batch.persistent_commands:
                payload = dict(command.payload)
                if command.command_type == "navigation" and payload.get("speed_mps", 0) != 0 and selected(
                        args.seed, tick, command.entity_id, args.fault_case, args.dose, component):
                    before = payload["speed_mps"]
                    payload["speed_mps"] = 0.0
                    command = command.model_copy(update={"payload": payload})
                    changed.append({"layer": execution_layer, "tick": tick,
                                    "unit_id": command.entity_id, "before_speed_mps": before,
                                    "after_speed_mps": 0.0})
                commands.append(command)
            actions = []
            for action in batch.discrete_actions:
                if selected(args.seed, tick, action.entity_id, args.fault_case, args.dose, component):
                    changed.append({"layer": execution_layer, "tick": tick,
                                    "unit_id": action.entity_id, "suppressed_action": action.action_type,
                                    "action_id": action.action_id})
                else:
                    actions.append(action)
            if changed:
                batch = batch.model_copy(update={"persistent_commands": tuple(commands),
                                         "discrete_actions": tuple(actions)})
                events.extend(changed)
            if a:
                a = (batch, *a[1:])
            else:
                kw["batch"] = batch
            return super().submit_actions(*a, **kw)

    hifi_trace.TraceContext, hifi_trace.TracedSession = FaultContext, FaultSession
    try:
        # Pass the seed/output arguments through to the underlying canonical
        # runner; only wrapper-specific arguments are removed.
        sys.argv = [str(Path(hifi_trace.__file__)), "--seed", str(args.seed),
                    "--output", str(args.output), *passthrough]
        code = hifi_trace.main()
    finally:
        hifi_trace.TraceContext, hifi_trace.TracedSession, sys.argv = original_context, original_session, original_argv
    output = args.output.resolve()
    report_path = output / "measurement_episode.json"
    if not report_path.exists():
        return code or 1
    event_path = output / "fault_events.json"
    event_path.write_text(json.dumps(events, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["fault_injection"] = {"case": args.fault_case, "dose": args.dose,
                                "wrapper_sha256": wrapper_hash,
                                "event_count": len(events),
                                "event_log_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
                                "replay_planner_fault_not_reinvoked": args.fault_case == "planner_wrong_contact" and
                                "--replay-from" in passthrough}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"aborted": report["aborted"], "ticks": report["ticks_run"],
                      "fault_events": len(events), "replay_exact":
                      report["replay_check"]["exact_match"] if report["replay_check"] else None}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

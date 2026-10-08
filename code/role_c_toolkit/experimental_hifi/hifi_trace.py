"""Passive interface tracing and fixed-goal replay around the existing V2 runner.

The engine, scenario, planner, executor and scoring implementations are unchanged.
Each invocation runs in a fresh process (also required by Windows native workers).
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import copy
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

import numpy as np


def plain(value):
    if isinstance(value, Enum):
        return plain(value.value)
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, Mapping):
        if all(isinstance(k, str) for k in value):
            return {k: plain(v) for k, v in value.items()}
        return {"mapping_entries": sorted([[plain(k), plain(v)] for k, v in value.items()], key=canonical)}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted([plain(v) for v in value], key=canonical)
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if hasattr(type(value), "model_fields"):
        return {name: plain(getattr(value, name)) for name in type(value).model_fields}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported trace type {type(value).__name__}; no silent omission")


def canonical(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest(source):
    engine = source / "source-code/source_codes"
    files = []
    for root in (source / "code/eval", engine / "openmdbench", engine / "catalog",
                 engine / "scenarios", engine / "env", engine / "framework"):
        files.extend(p for p in root.rglob("*") if p.is_file() and p.suffix in (".py", ".yaml", ".yml") and "__pycache__" not in p.parts)
    files.append(engine / "pyproject.toml")
    return {str(p.relative_to(source)): file_hash(p) for p in sorted(set(files))}


def entities(session):
    return [{"id": e.id, "faction_id": e.faction_id, "state": plain(e.state)}
            for e in session.world_view.entities_stable()]


class FrozenPlanner:
    """Agent bookkeeping still runs; exact submitted decisions are applied below."""
    def plan(self, *args, **kwargs):
        return []

    def get_stats(self):
        return {"mode": "frozen_goal_timeline", "original_planner_called": False}


class TraceContext:
    def __init__(self, stream, replay, checkpoint_interval=1):
        if checkpoint_interval < 1:
            raise ValueError("Positive checkpoint interval required")
        self.stream, self.replay = stream, replay
        self.checkpoint_interval = checkpoint_interval
        self.agent = None
        self.decisions, self.fingerprints = [], []
        self.execution = None
        self.batches, self.reports = [], []

    def log(self, event):
        self.stream.write(canonical(event) + "\n")
        self.stream.flush()

    def attach_agent(self, agent):
        self.agent = agent
        from goai_protocol import GoalCommand
        submit = agent.broker.submit_goals
        act = agent.executor.act
        post = agent.broker.post_report
        if self.replay is not None:
            agent.planner = FrozenPlanner()

        def submit_goals(commands, step, **kwargs):
            if self.replay is not None:
                if step not in self.replay:
                    return {"accepted": [], "rejected": []}
                commands = [GoalCommand(**copy.deepcopy(item)) for item in self.replay[step]["commands"]]
            issued = plain(commands)
            receipt = submit(commands, step=step, **kwargs)
            event = {"kind": "decision", "tick": step, "commands": issued, "receipt": plain(receipt)}
            self.decisions.append(event)
            self.log(event)
            return receipt

        def executor_act(session, tick):
            self.execution = {"tick": tick,
                "active_goals_before_execution": [plain(s.command) for s in agent.broker.active.values() if not s.terminal],
                "own_before": [e for e in entities(session) if e["faction_id"] == agent.faction_id]}
            result = act(session, tick)
            self.execution["executor_result"] = plain(result)
            return result

        def post_report(report):
            self.reports.append(plain(report))
            return post(report)

        agent.broker.submit_goals = submit_goals
        agent.broker.post_report = post_report
        agent.executor.act = executor_act
        return agent


class TracedSession:
    def __init__(self, session, context):
        self._session, self._context = session, context

    def __getattr__(self, name):
        return getattr(self._session, name)

    def load(self):
        self._session.load()
        return self

    def start(self):
        self._session.start()
        return self

    def submit_actions(self, *args, **kwargs):
        batch = kwargs.get("batch", args[0] if args else None)
        receipt = self._session.submit_actions(*args, **kwargs)
        self._context.batches.append({"batch": plain(batch), "receipt": plain(receipt)})
        return receipt

    def step(self, *args, **kwargs):
        context = self._context
        tick = self.world_view.tick
        receipt = self._session.step(*args, **kwargs)
        receipt_data = plain(receipt)
        terminal = any(
            mission.get("terminal_result") is not None
            for mission in receipt_data.get("world_receipt", {}).get("mission_receipts", [])
        )
        checkpoint_due = self.world_view.tick % context.checkpoint_interval == 0 or terminal
        checkpoint_sha256 = digest(self.world_view.checkpoint()) if checkpoint_due else None
        after = entities(self)
        if context.execution is None or context.execution["tick"] != tick:
            raise RuntimeError("Missing/misaligned pre-execution trace")
        row = {"kind": "transition", **context.execution, "after_tick": self.world_view.tick,
               "own_after": [e for e in after if e["faction_id"] == context.agent.faction_id],
               "all_entities_after": after, "world_checkpoint_sha256": checkpoint_sha256,
               "broker_sha256": digest({k: v for k, v in vars(context.agent.broker).items() if not callable(v)}),
               "action_batches": context.batches, "status_reports": context.reports,
               "step_receipt": receipt_data}
        context.log(row)
        context.fingerprints.append({"tick": tick, "world": row["world_checkpoint_sha256"],
                                     "broker": row["broker_sha256"], "transition": digest(row)})
        context.execution = None
        context.batches, context.reports = [], []
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", default="IE-01-SINGLE-TARGET")
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--ticks", type=int, default=30)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--world-checkpoint-interval", type=int, default=1)
    parser.add_argument("--step-timeout", type=float, default=60.0,
                        help="Runner wall-clock watchdog per tick; include recorded checkpoint overhead")
    parser.add_argument("--replay-from", type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Use a new output outside the source project")
    if args.ticks < 1 or args.interval < 1 or args.world_checkpoint_interval < 1 or args.step_timeout <= 0:
        raise ValueError("Positive tick budget, intervals and step timeout required")
    hashes = source_manifest(source)
    config = {"scenario": args.scenario, "seed": args.seed, "max_ticks": args.ticks,
              "plan_interval": args.interval, "planner": "rule"}
    if args.world_checkpoint_interval != 1:
        config["world_checkpoint_interval"] = args.world_checkpoint_interval
    if args.step_timeout != 60.0:
        config["runner_step_timeout_seconds"] = args.step_timeout
    baseline, replay = None, None
    if args.replay_from:
        baseline = json.loads(args.replay_from.read_text(encoding="utf-8"))
        if baseline["aborted"] or baseline["config"] != config or baseline["source_hashes"] != hashes:
            raise ValueError("Replay requires non-aborted same-version/configuration source")
        replay = {r["tick"]: r for r in baseline["decisions"]}
        if len(replay) != len(baseline["decisions"]):
            raise ValueError("Duplicate decision tick")
    sys.path[:0] = [str(source / "code/eval"), str(source / "source-code/source_codes")]
    import run_episode as runner
    original_factory, original_builder = runner.create_formal_session_v2, runner._build_defender
    output.mkdir(parents=True)
    error = None
    with (output / "events.jsonl").open("x", encoding="utf-8") as stream:
        context = TraceContext(stream, replay, args.world_checkpoint_interval)
        runner.create_formal_session_v2 = lambda *a, **kw: TracedSession(original_factory(*a, **kw), context)
        runner._build_defender = lambda *a, **kw: context.attach_agent(original_builder(*a, **kw))
        sys.argv = ["run_episode.py", "--scenario", args.scenario, "--seed", str(args.seed),
                    "--max-ticks", str(args.ticks), "--planner", "rule", "--plan-interval", str(args.interval),
                    "--step-timeout", str(args.step_timeout),
                    "--checkpoint-dir", str(output / "checkpoints"), "--checkpoint-tick", str(args.ticks + 1),
                    "--output", str(output / "engine_result.json"), "--log", str(output / "runner.jsonl")]
        try:
            runner.main()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            context.log({"kind": "instrumentation_error", "error": error})
        finally:
            runner.create_formal_session_v2, runner._build_defender = original_factory, original_builder
    result_path = output / "engine_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    aborted = error or result.get("aborted") or ("missing_engine_result" if not result else None)
    unchanged = hashes == source_manifest(source)
    if not unchanged:
        aborted = "source_changed_during_run"
    replay_check = None
    if baseline is not None:
        replay_check = {"same_length": len(context.fingerprints) == len(baseline["fingerprints"]),
                        "step_fingerprints_identical": context.fingerprints == baseline["fingerprints"],
                        "decisions_identical": context.decisions == baseline["decisions"]}
        replay_check["exact_match"] = not aborted and all(replay_check.values())
    report = {"schema": "role-c-hifi-trace@2" if args.world_checkpoint_interval != 1 else "role-c-hifi-trace@1",
              "config": config, "aborted": aborted,
              "runtime": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                          "packages": {name: version(name) for name in ("numpy", "pydantic", "taichi", "pyproj")}},
              "source_hashes": hashes, "source_unchanged": unchanged,
              "instrumentation_sha256": file_hash(Path(__file__)),
              "decisions": context.decisions, "fingerprints": context.fingerprints,
              "trace_sha256": file_hash(output / "events.jsonl"), "replay_check": replay_check,
              "terminal_result": result.get("terminal_result"), "ticks_run": result.get("ticks_run"),
              "replay_source_sha256": file_hash(args.replay_from) if args.replay_from else None,
              "formal_measurement_complete": False, "formal_attribution_complete": False}
    (output / "measurement_episode.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(canonical({"output": str(output), "aborted": aborted, "ticks": report["ticks_run"], "replay_check": replay_check}))
    return int(bool(aborted) or (replay_check is not None and not replay_check["exact_match"]))


if __name__ == "__main__":
    raise SystemExit(main())

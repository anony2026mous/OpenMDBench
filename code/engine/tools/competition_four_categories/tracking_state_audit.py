"""Isolated, referee-only tracking state capture and strict native pairs."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from openmdbench.missions.engine_v2 import _canonical_hash
from .build import ROOT, PACKAGES
from .calibration_matrix import frozen_inputs, save_json, sha
from .protected_inputs import verify
from .tracking_metrics_v1 import TrackingMetricV1
from .track_report_metrics_v1 import TrackReportMetricV1
from .tracking_raw_metrics import tracking_statistics, report_statistics, temporal_statistics

_ACTIVE = False
FAMILIES = {"tracking": TrackingMetricV1, "reports": TrackReportMetricV1}
FORMATTERS = {"tracking": tracking_statistics, "reports": report_statistics}


class TrackingStateAudit:
    def __init__(self, path):
        self.path, self.rows, self.seen, self.snapshot_calls = Path(path), [], set(), 0

    def __enter__(self):
        global _ACTIVE
        if _ACTIVE: raise ValueError("tracking state audit requires one isolated session")
        self.stack = ExitStack()
        self.stream = self.stack.enter_context(self.path.open("x", encoding="utf-8"))
        def wrap(original, family):
            def observed(model):
                state = original(model); self.snapshot_calls += 1
                digest = _canonical_hash(state)
                key = (family, state["parameters"]["metric_id"], state["last_tick"], digest)
                if key not in self.seen:
                    self.seen.add(key)
                    row = {"sequence": len(self.rows), "audience": "referee_only",
                           "family": family, "state_hash": digest, "state": deepcopy(state)}
                    self.stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    self.stream.flush(); self.rows.append(row)
                return state
            return observed
        try:
            for family, cls in FAMILIES.items():
                self.stack.enter_context(patch.object(cls, "snapshot", wrap(cls.snapshot, family)))
        except BaseException:
            self.stack.close(); raise
        _ACTIVE = True
        return self

    def __exit__(self, *exc):
        global _ACTIVE
        try: self.stack.close()
        finally: _ACTIVE = False
        return False

    def summarize(self, result, dt):
        end = result["final_tick"]; trace = result["trace"]
        if [f["tick"] for f in trace] != list(range(1, end + 1)):
            raise ValueError("native tracking trace is not contiguous")
        by_metric, families = {}, {}
        for row in self.rows:
            state = row["state"]; mid = state["parameters"]["metric_id"]; tick = state["last_tick"]
            if _canonical_hash(state) != row["state_hash"]: raise ValueError("captured state hash differs")
            if mid in families and families[mid] != row["family"]: raise ValueError("metric changed family")
            families[mid] = row["family"]
            if tick in by_metric.setdefault(mid, {}): raise ValueError("multiple distinct states at one metric/tick")
            by_metric[mid][tick] = state
        if set(by_metric) != set(result["scores"]): raise ValueError("not all native metrics were captured")
        final, temporal = {}, {}
        for mid, states in by_metric.items():
            if set(states) != {-1, *range(1, end + 1)}: raise ValueError("not every scoring tick was captured")
            for frame in trace:
                if states[frame["tick"]]["last_value"] != frame["scores"][mid]:
                    raise ValueError("plugin state score differs from native receipt")
            if states[end]["last_value"] != result["scores"][mid]: raise ValueError("final score differs")
            final[mid] = FORMATTERS[families[mid]](states[end], dt)
            temporal[mid] = temporal_statistics([states[t] for t in sorted(states)], families[mid], dt)
        return {"schema_version": "referee-tracking-state-audit@1.0", "audience": "referee_only",
            "snapshot_calls_observed": self.snapshot_calls, "state_rows": len(self.rows),
            "state_journal": self.path.relative_to(ROOT).as_posix(), "state_journal_sha256": sha(self.path),
            "every_metric_and_scoring_tick_verified": True, "metric_families": families,
            "final_raw_metrics": final, "temporal_metrics": temporal,
            "native_checkpoint_restoration_proven": False, "competition_accepted": False}


def _native_run(number, seed):
    if number <= 6:
        from .validate_allocated_tracking import run
        return run(number, seed)
    if number == 7:
        from .validate_identity_tracking import run
    elif number == 8:
        from .validate_coverage_tracking import run
    else: raise ValueError("tracking scenario must be 1..8")
    return run(number, "honest", seed)


def run(number, seed, *, capture):
    before, protected = frozen_inputs(), verify()
    directory = ROOT / "artifacts/competition_four_categories" / (
        f"tracking-state-audit-{number:03d}-{seed}-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True, exist_ok=False)
    observer = None
    if capture:
        with TrackingStateAudit(directory / "metric-states.jsonl") as observer:
            result = _native_run(number, seed)
    else: result = _native_run(number, seed)
    with (directory / "native-result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    try:
        brief = json.loads((PACKAGES / f"md_trk_{number:03d}_standard/public_brief.json").read_text(encoding="utf-8"))
        if not result["terminal"] or result["final_tick"] != brief["adjudication_tick"]:
            raise ValueError("tracking audit requires the complete natural episode")
        if hashlib.sha256(json.dumps(result["trace"], sort_keys=True).encode()).hexdigest() != result["trace_sha256"]:
            raise ValueError("native trace hash differs")
        raw = observer.summarize(result, brief["physics_dt_seconds"]) if observer is not None else None
        if frozen_inputs() != before: raise ValueError("source/input changed during collection")
    except Exception as error:
        save_json(directory / "audit-error.json", {"error_type": type(error).__name__, "error": str(error),
            "native_result_preserved": "native-result.json", "audit_passed": False})
        raise
    result["referee_metric_state_audit"] = raw
    result["referee_metric_state_audit_provenance"] = {"source_inputs": before, "source_inputs_unchanged": True,
        "protected_before": protected, "protected_after": verify(), "capture_enabled": capture,
        "scope": "Existing candidate plugin snapshots only; not World checkpoints or controller inputs"}
    path = directory / "result.json"
    with path.open("x", encoding="utf-8") as stream: json.dump(result, stream, indent=2, allow_nan=False)
    print("evidence=" + path.relative_to(ROOT).as_posix(), flush=True)
    return path


def compare_results(control, observed):
    excluded = {"elapsed_wall_seconds", "referee_metric_state_audit", "referee_metric_state_audit_provenance"}
    a = {k: v for k, v in control.items() if k not in excluded}
    b = {k: v for k, v in observed.items() if k not in excluded}
    differences = sorted(k for k in set(a) | set(b) if k not in a or k not in b or a[k] != b[k])
    if differences: raise ValueError("observer changed native fields: " + ", ".join(differences))
    if control["referee_metric_state_audit"] is not None or not observed["referee_metric_state_audit"]["every_metric_and_scoring_tick_verified"]:
        raise ValueError("control/observed audit roles are invalid")
    if not observed["terminal"] or not observed["trace"]: raise ValueError("native episode not complete")
    return {"all_native_fields_equal": True, "compared_fields": sorted(a), "excluded_fields": sorted(excluded),
        "final_tick": observed["final_tick"], "scores": observed["scores"], "terminal": observed["terminal"],
        "trace_sha256": observed["trace_sha256"], "raw_state_audit": observed["referee_metric_state_audit"],
        "native_checkpoint_restoration_proven": False, "competition_accepted": False}


def _stop_owned_process(process):
    if process.poll() is not None: return
    if os.name == "nt":
        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
    else: process.kill()
    process.wait(timeout=30)


def run_pair(number, seed):
    before = frozen_inputs()
    directory = ROOT / "artifacts/competition_four_categories" / (
        f"tracking-state-pair-{number:03d}-{seed}-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True, exist_ok=False)
    for kind in ("source_hashes", "input_hashes"):
        for relative, digest in before[kind].items():
            target = directory / "frozen_sources_inputs" / relative; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream: stream.write((ROOT / relative).read_bytes())
            if sha(target) != digest: raise ValueError("source changed during freeze")
    plan = {"schema_version": "tracking-state-noninterference-plan@1.0", "scenario_number": number, "seed": seed,
        "reference_policy": "allocated" if number <= 6 else ("identity-honest" if number == 7 else "coverage-honest"),
        "case_order": ["control", "observed"], "timeout_seconds_per_case": 900, **before,
        "protected_before": verify(), "purpose": "Candidate metric recording audit, not policy calibration"}
    save_json(directory / "plan.json", plan)
    state = {"collection_complete": False, "active": None, "completed": [], "error": None}
    save_json(directory / "state.json", state); print("pair=" + directory.relative_to(ROOT).as_posix(), flush=True)
    try:
        for mode in plan["case_order"]:
            if frozen_inputs() != before: raise ValueError("frozen sources or inputs changed")
            command = [sys.executable, "-B", "-m", __package__ + ".tracking_state_audit",
                "--scenario", str(number), "--seed", str(seed)] + (["--capture"] if mode == "observed" else [])
            log = directory / (mode + ".log")
            with log.open("x", encoding="utf-8") as stream:
                process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                state["active"] = {"mode": mode, "pid": process.pid, "command": command}; save_json(directory / "state.json", state)
                try: code = process.wait(timeout=plan["timeout_seconds_per_case"])
                except BaseException: _stop_owned_process(process); raise
            if code: raise RuntimeError(f"{mode} exited {code}; see {log}")
            paths = [line[9:] for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("evidence=")]
            if len(paths) != 1: raise ValueError("expected one native evidence path")
            state["completed"].append({"mode": mode, "result": paths[0], "sha256": sha(ROOT / paths[0]), "exit_code": code})
            state["active"] = None; save_json(directory / "state.json", state); print(mode + " complete", flush=True)
        results = [json.loads((ROOT / c["result"]).read_text(encoding="utf-8")) for c in state["completed"]]
        comparison = compare_results(*results)
        if frozen_inputs() != before: raise ValueError("source/input changed during comparison")
        comparison.update(cases=state["completed"], source_inputs_unchanged=True, protected_after=verify(), plan_sha256=sha(directory / "plan.json"))
        save_json(directory / "comparison.json", comparison); state["collection_complete"] = True
    except BaseException as error:
        state["error"] = {"type": type(error).__name__, "message": str(error)}; raise
    finally:
        state["active"] = None; save_json(directory / "state.json", state)
    return directory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=range(1, 9), required=True)
    parser.add_argument("--seed", type=int, required=True)
    mode = parser.add_mutually_exclusive_group(); mode.add_argument("--capture", action="store_true"); mode.add_argument("--pair", action="store_true")
    args = parser.parse_args()
    if args.pair: run_pair(args.scenario, args.seed)
    else: run(args.scenario, args.seed, capture=args.capture)

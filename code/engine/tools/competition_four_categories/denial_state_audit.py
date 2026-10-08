"""Referee-only observation of existing DenialMetricV1 snapshots.

The original candidate snapshot method is called once and its exact result is
returned unchanged. No score, model state, native checkpoint or controller input
is replaced. Use only in one isolated native session/process. This is subsystem
audit evidence, not a successful engine checkpoint or restoration workaround.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import yaml

from openmdbench.missions.engine_v2 import _canonical_hash
from .build import ROOT
from .calibration_matrix import frozen_inputs, save_json, sha
from .denial_metrics_v1 import DenialMetricV1, MODEL_REF
from .denial_breach_audit import DenialBreachAudit
from .protected_inputs import verify
from . import validate_salvo_denial

_ACTIVE = False
RAW_SCHEMA = "referee-denial-raw-statistics@2.0"


def raw_statistics(state, dt):
    p, samples = state["parameters"], state["samples"]
    measured = samples > 0
    zones = {}
    for identifier, history in state["zones"].items():
        zones[identifier] = {
            "breach_entry_count": history["breaches"] if measured else None,
            "first_breach_scoring_tick": history["first_breach_tick"],
            "last_breach_scoring_tick": history["last_breach_tick"],
            "safe_sample_ticks": history["safe_ticks"] if measured else None,
            "safe_sample_seconds": history["safe_ticks"] * dt if measured else None,
            "protection_time_fraction": history["safe_ticks"] / samples if measured else None,
            "ever_inactive_in_window": history["ever_inactive"] if measured else None,
            "last_sampled_intruder_ids_referee_only": list(history["inside"]) if measured else None,
        }
    protected = {row["entity_id"]: {
        "minimum_observed_health": state["minimum_health"][row["entity_id"]] if measured else None,
        "maximum_all_cause_health_loss": row["initial_health"] - state["minimum_health"][row["entity_id"]] if measured else None,
        "health_preservation_fraction": state["minimum_health"][row["entity_id"]] / row["initial_health"] if measured else None,
    } for row in p["protected_entities"]}
    first = [row["first_breach_tick"] for row in state["zones"].values() if row["first_breach_tick"] is not None]
    return {"schema_version": RAW_SCHEMA, "metric_id": p["metric_id"], "kind": p["kind"],
            "window_start_tick": p["start_tick"], "window_end_tick_exclusive": p["end_tick"],
            "last_evaluated_tick": state["last_tick"], "sample_count": samples,
            "last_sampled_tick": min(state["last_tick"], p["end_tick"] - 1) if measured else None,
            "measurement_status": "measured" if measured else "not_yet_sampled",
            "native_candidate_score_value": state["last_value"],
            "total_zone_entry_count": sum(row["breaches"] for row in state["zones"].values()) if measured else None,
            "first_breach_scoring_tick": min(first) if first else None,
            "zones": zones, "protected_health_all_cause": protected,
            "definitions": {
                "breach_entry_count": "Existing model counter: union of authoritative entered transitions and newly occupied eligible intruders at each sampled tick; includes occupancy on the first window sample and can include entry followed by destruction within one tick; a late window is not a late-spawn cohort filter",
                "first_breach_scoring_tick": "Model evaluation tick that first records an entry, not a substituted continuous-time collision timestamp",
                "last_sampled_intruder_ids_referee_only": "Occupancy remembered at last_sampled_tick, not current occupancy after the scoring window; null before the first sample",
                "protected_health_all_cause": "All-cause preservation; not defender-only damage or misclassification attribution"}}


class DenialStateAudit:
    def __init__(self, path, *, dt):
        if type(dt) not in (int, float) or not 0 < dt < float("inf"):
            raise ValueError("audit requires a finite positive native tick duration")
        self.path, self.dt = Path(path), dt
        self.rows, self.seen, self.snapshot_calls = [], set(), 0

    def __enter__(self):
        global _ACTIVE
        if _ACTIVE:
            raise ValueError("denial snapshot audit is isolated to one active session")
        self.stream = self.path.open("x", encoding="utf-8")
        original = DenialMetricV1.snapshot
        def observed_snapshot(model):
            state = original(model)
            self.snapshot_calls += 1
            fingerprint = _canonical_hash(state)
            key = (state["parameters"]["metric_id"], state["last_tick"], fingerprint)
            if key not in self.seen:
                self.seen.add(key)
                row = {"sequence": len(self.rows), "audience": "referee_only",
                       "model_ref": MODEL_REF, "candidate_plugin_state_hash": fingerprint,
                       "state": deepcopy(state), "raw_statistics": raw_statistics(state, self.dt)}
                self.stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                self.stream.flush()
                self.rows.append(row)
            return state
        self.patcher = patch.object(DenialMetricV1, "snapshot", observed_snapshot)
        self.patcher.start()
        _ACTIVE = True
        return self

    def __exit__(self, *exc):
        global _ACTIVE
        self.patcher.stop()
        self.stream.close()
        _ACTIVE = False
        return False

    def verify_against_native_result(self, result):
        if [frame["tick"] for frame in result["trace"]] != list(range(1, result["final_tick"] + 1)):
            raise ValueError("native result trace is not contiguous")
        by_metric = {}
        for row in self.rows:
            state = row["state"]
            if _canonical_hash(state) != row["candidate_plugin_state_hash"]:
                raise ValueError("captured plugin state hash changed")
            key, tick = state["parameters"]["metric_id"], state["last_tick"]
            old = by_metric.setdefault(key, {}).get(tick)
            if old is not None and old != row:
                raise ValueError("multiple different plugin states at one metric/tick")
            by_metric[key][tick] = row
        if set(by_metric) != set(result["scores"]):
            raise ValueError("not all native score metrics have captured raw state")
        for metric, rows in by_metric.items():
            if set(rows) != {-1, *range(1, result["final_tick"] + 1)}:
                raise ValueError("raw metric state does not cover every native scoring tick")
            for frame in result["trace"]:
                if rows[frame["tick"]]["state"]["last_value"] != frame["scores"][metric]:
                    raise ValueError("observed raw state differs from native score receipt")
        return {"schema_version": RAW_SCHEMA,
                "audience": "referee_only", "snapshot_calls_observed": self.snapshot_calls,
                "distinct_states_recorded": len(self.rows),
                "state_journal": self.path.relative_to(ROOT).as_posix(),
                "state_journal_sha256": sha(self.path),
                "every_metric_and_scoring_tick_verified": True,
                "final_metrics": {metric: rows[result["final_tick"]]["raw_statistics"] for metric, rows in by_metric.items()},
                "native_checkpoint_restoration_proven": False,
                "scope": "Observed candidate-plugin snapshots only; not a validated World checkpoint, not recovery state, and never controller input"}


def run(number, policy, seed, *, capture, breach_inputs=False):
    if breach_inputs and not capture:
        raise ValueError("breach inputs require the accompanying candidate state audit")
    before, protected = frozen_inputs(), verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / "artifacts/competition_four_categories" / f"denial-state-audit-{number:03d}-{seed}-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    observer = None
    breach = None
    if capture:
        brief = json.loads((ROOT / f"scenarios/competition_v1/md_ad_{number:03d}_standard/public_brief.json").read_text())
        with (DenialBreachAudit(directory / "breach-inputs.jsonl") if breach_inputs else nullcontext()) as breach, DenialStateAudit(directory / "metric-states.jsonl", dt=brief["physics_dt_seconds"]) as observer:
            result = validate_salvo_denial.run(number, policy, seed)
    else:
        result = validate_salvo_denial.run(number, policy, seed)
    # Preserve the completed native episode even if the separate audit fails.
    with (directory / "native-result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    try:
        raw = observer.verify_against_native_result(result) if observer is not None else None
        if breach is not None:
            package = yaml.safe_load((ROOT / f"scenarios/competition_v1/md_ad_{number:03d}_standard/scenario.yaml").read_text(encoding="utf-8"))
            raw["breach_cohort_audit"] = breach.summarize(package, observer.rows, result["final_tick"])
        if frozen_inputs() != before:
            raise RuntimeError("source or canonical input changed during referee-state audit")
    except Exception as error:
        save_json(directory / "audit-error.json", {"type": type(error).__name__, "error": str(error),
                  "native_result_preserved": "native-result.json", "audit_passed": False})
        raise
    result["referee_metric_state_audit"] = raw
    result["referee_metric_state_audit_provenance"] = {
        "source_inputs": before, "sources_inputs_unchanged": True, "capture_enabled": capture,
        "observer_source_sha256": sha(Path(__file__)),
        "original_metric_source_sha256": sha(ROOT / "tools/competition_four_categories/denial_metrics_v1.py"),
        "protected_before": protected, "protected_after": verify(),
        "noninterference_requires_paired_native_comparison": True, "competition_accepted": False}
    with (directory / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print("evidence=" + (directory / "result.json").relative_to(ROOT).as_posix(), flush=True)
    return directory / "result.json"


def compare_results(control, observed):
    """Compare every native result field except elapsed time and observer metadata."""
    excluded = {"elapsed_wall_seconds", "referee_metric_state_audit",
                "referee_metric_state_audit_provenance"}
    left = {k: v for k, v in control.items() if k not in excluded}
    right = {k: v for k, v in observed.items() if k not in excluded}
    differing = sorted(k for k in set(left) | set(right)
                       if k not in left or k not in right or left[k] != right[k])
    if differing:
        raise ValueError("observer changed native evidence fields: " + ", ".join(differing))
    if control["referee_metric_state_audit"] is not None:
        raise ValueError("control run unexpectedly enabled the observer")
    audit = observed["referee_metric_state_audit"]
    if not audit or not audit["every_metric_and_scoring_tick_verified"]:
        raise ValueError("observed run has no verified raw state coverage")
    if not observed["terminal"] or not observed["trace"]:
        raise ValueError("pair must reach a natural terminal")
    return {"all_native_evidence_fields_equal": True,
            "compared_fields": sorted(left), "excluded_fields": sorted(excluded),
            "trace_sha256": observed["trace_sha256"],
            "final_tick": observed["final_tick"], "scores": observed["scores"],
            "terminal": observed["terminal"], "raw_state_audit": audit,
            "native_terminal_checkpoint_gate": observed["native_terminal_checkpoint_gate"],
            "native_checkpoint_restoration_proven": False, "competition_accepted": False,
            "scope": "One same-input/seed/policy native pair; not all-policy or all-scenario noninterference"}


def run_pair(number, policy, seed, *, breach_inputs=False):
    """Freeze first, then run each side in its own process and preserve all outcomes."""
    before = frozen_inputs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / "artifacts/competition_four_categories" / f"denial-state-pair-{number:03d}-{seed}-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    for kind in ("source_hashes", "input_hashes"):
        for relative, expected in before[kind].items():
            source = ROOT / relative
            target = directory / "frozen_sources_inputs" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
            if sha(target) != expected:
                raise ValueError("source changed while archiving: " + relative)
    plan = {"schema_version": "denial-state-noninterference-plan@1.0",
            "scenario_number": number, "policy": policy, "seed": seed,
            "case_order": ["control", "observed"], **before,
            "breach_inputs_enabled_for_observed": breach_inputs,
            "protected_before": verify(), "timeout_seconds_per_case": 900,
            "purpose": "Referee metric export noninterference, not new policy calibration",
            "competition_accepted": False}
    save_json(directory / "plan.json", plan)
    state = {"collection_complete": False, "active": None, "completed": [],
             "comparison": None, "error": None}
    save_json(directory / "state.json", state)
    print("pair=" + directory.relative_to(ROOT).as_posix(), flush=True)
    try:
        for mode in plan["case_order"]:
            if frozen_inputs() != before:
                raise ValueError("frozen study source or input changed")
            command = [sys.executable, "-B", "-m", __package__ + ".denial_state_audit",
                       "--scenario", str(number), "--policy", policy, "--seed", str(seed)]
            if mode == "observed":
                command.append("--capture")
                if breach_inputs: command.append("--breach-inputs")
            log = directory / (mode + ".log")
            with log.open("x", encoding="utf-8") as stream:
                process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                state["active"] = {"mode": mode, "pid": process.pid, "command": command}
                save_json(directory / "state.json", state)
                try:
                    exit_code = process.wait(timeout=plan["timeout_seconds_per_case"])
                except BaseException:
                    process.kill()
                    process.wait()
                    raise
            if exit_code != 0:
                raise RuntimeError(f"{mode} exited {exit_code}; see {log}")
            paths = [line.removeprefix("evidence=") for line in log.read_text(encoding="utf-8").splitlines()
                     if line.startswith("evidence=")]
            if len(paths) != 1:
                raise ValueError("native subprocess did not report exactly one evidence path")
            result_path = ROOT / paths[0]
            state["completed"].append({"mode": mode, "result": paths[0],
                                       "sha256": sha(result_path), "exit_code": exit_code})
            state["active"] = None
            save_json(directory / "state.json", state)
            print(mode + " complete", flush=True)
        results = [json.loads((ROOT / row["result"]).read_text(encoding="utf-8")) for row in state["completed"]]
        comparison = compare_results(*results)
        if frozen_inputs() != before:
            raise ValueError("frozen study source or input changed")
        comparison.update({"source_inputs_unchanged": True, "protected_after": verify(),
                           "plan_sha256": sha(directory / "plan.json"), "cases": state["completed"]})
        save_json(directory / "comparison.json", comparison)
        state.update({"collection_complete": True, "comparison": "comparison.json"})
    except BaseException as error:
        state["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        state["active"] = None
        save_json(directory / "state.json", state)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=range(1, 7), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--policy", choices=("guard", "receipt-aware-salvo", "planning-lead-salvo"), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--pair", action="store_true")
    parser.add_argument("--breach-inputs", action="store_true")
    args = parser.parse_args()
    if args.breach_inputs and not (args.capture or args.pair):
        parser.error("--breach-inputs requires --capture or --pair")
    if args.pair:
        run_pair(args.scenario, args.policy, args.seed, breach_inputs=args.breach_inputs)
    else:
        run(args.scenario, args.policy, args.seed, capture=args.capture, breach_inputs=args.breach_inputs)


if __name__ == "__main__":
    main()

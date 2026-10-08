"""Full-episode invariance probes for candidate packages; never engine edits.

Scenario renaming, declaration order and catalog registration order are tested
separately. Canonical repetition checks the comparison's own determinism first.
These fixtures do not establish task feasibility, full checkpoint equivalence,
arbitrary-policy invariance or competition acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import argparse
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import yaml

from .calibration_matrix import cases_for_seed, frozen_inputs, save_json, sha, validate_result
from .build import ROOT, PACKAGES
from .protected_inputs import verify
from . import runtime

MODES = ("baseline", "repeat", "rename", "declaration_order", "registry_order")
DECLARATION_PATHS = (
    ("entities",), ("controller_slots",), ("events",), ("mission_rules",),
    ("factions",), ("relationships",), ("zones",), ("world", "zones"),
    ("geography", "zones"), ("scoring", "metrics"),
)


def transform_package(package, mode):
    if mode not in MODES:
        raise ValueError("unknown native invariance mode")
    transformed = deepcopy(package)
    scenario = transformed["scenario"]
    changed = []
    if mode == "rename":
        scenario["scenario_id"] = "independent.invariance.scenario"
        changed.append("scenario.scenario_id")
    elif mode == "declaration_order":
        for path in DECLARATION_PATHS:
            owner = scenario
            for key in path[:-1]:
                owner = owner.get(key, {})
            value = owner.get(path[-1])
            if isinstance(value, list) and len(value) > 1:
                value.reverse()
                changed.append("scenario." + ".".join(path))
    return transformed, changed


def matrix_cases(seed):
    references = [case for case in cases_for_seed(seed) if case["side"] == "B"]
    if len(references) != 30:
        raise ValueError("native matrix requires all thirty declared package variants")
    families = {family: [case for case in references if case["scenario_id"].split("-")[1] == family]
                for family in ("REC", "TRK", "AD", "ER")}
    references = [items[index] for index in range(max(map(len, families.values())))
                  for items in families.values() if index < len(items)]
    return [{**case, "case_id": f"{seed}-{case['scenario_id']}-{case['difficulty']}-{mode}",
             "mode": mode}
            for case in references for mode in MODES]


RESULTS = ROOT / "artifacts/competition_four_categories"


def plain(value):
    if hasattr(value, "model_dump"):
        return plain(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((plain(item) for item in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, Enum):
        return plain(value.value)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError(f"unsupported immutable native trace value: {type(value).__name__}")


def redact_capabilities(value):
    if isinstance(value, dict):
        return {key: "<redacted-authority-token>" if key == "authority_token" else redact_capabilities(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact_capabilities(item) for item in value]
    return value


class Journal:
    def __init__(self, path):
        self.path = path
        self.stream = path.open("x", encoding="utf-8")
        self.records = 0
        self.world_ticks = []

    def write(self, record):
        record = redact_capabilities(plain(record))
        self.stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        self.stream.flush()
        self.records += 1
        if record["kind"] == "world":
            self.world_ticks.append(record["frame"]["tick"])

    def close(self):
        self.stream.close()


class ViewProbe:
    def __init__(self, native, journal):
        self.native, self.journal = native, journal

    def __getattr__(self, name):
        return getattr(self.native, name)

    def controller_observation(self, *args, **kwargs):
        result = self.native.controller_observation(*args, **kwargs)
        self.journal.write({"kind": "observation", "observation": result})
        return result


class SessionProbe:
    def __init__(self, native, journal):
        self.native, self.journal = native, journal
        self.world_view = ViewProbe(native.world_view, journal)
        journal.write({"kind": "world", "frame": native.world_view.presentation_snapshot()})

    def __getattr__(self, name):
        return getattr(self.native, name)

    def step(self, *args, **kwargs):
        result = self.native.step(*args, **kwargs)
        self.journal.write({"kind": "step_receipt", "receipt": result})
        self.journal.write({"kind": "world", "frame": self.native.world_view.presentation_snapshot()})
        return result

    def submit_actions(self, *args, **kwargs):
        result = self.native.submit_actions(*args, **kwargs)
        # Never write authority tokens. The batch and authorized result suffice.
        self.journal.write({"kind": "submission", "batch": kwargs["batch"], "receipt": result})
        return result


def reversed_catalog(original):
    registry = runtime.ModelRegistryV2(interface_version="2.0")
    for metadata in reversed(original.model_registry.snapshot()):
        def factory(definition, ref=metadata.exact_ref):
            return original.model_registry.create(ref, definition)
        registry.register(metadata, factory)
    registry.freeze()
    return runtime.CatalogV2(list(reversed(original.snapshot())), engine_version="2.0.0", model_registry=registry)


def runner_arguments(case, function):
    options = dict(zip(case["arguments"][::2], case["arguments"][1::2]))
    values = {"seed": case["seed"], "level": case["difficulty"],
              "number": int(case["scenario_id"].split("-")[-1]),
              "policy": options.get("--policy"), "mode": options.get("--mode"),
              "comparison_plan": "native-invariance-separate-transforms@1.0"}
    result = {}
    for name, parameter in inspect.signature(function).parameters.items():
        if name in values and values[name] is not None:
            result[name] = values[name]
        elif parameter.default is inspect.Parameter.empty:
            raise ValueError(f"unsupported required reference-runner argument: {name}")
    return result


def run_case(case_path):
    case_path = case_path.resolve()
    if not case_path.is_relative_to(RESULTS.resolve()):
        raise ValueError("store native invariance cases inside the candidate artifact directory")
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if case not in matrix_cases(case.get("seed")):
        raise ValueError("case differs from the declared native verification protocol")
    before, protected = frozen_inputs(), verify()
    module = importlib.import_module(case["module"])
    journal_path = case_path.with_suffix(".native.jsonl")
    journal = Journal(journal_path)
    original_compile, original_create = runtime.compile_candidate, runtime.create_candidate
    compilations = []

    def compile_variant(path):
        canonical, catalog = original_compile(path)
        raw = yaml.safe_load((Path(path) / "scenario.yaml").read_text(encoding="utf-8"))
        if raw.get("includes"):
            raise ValueError("multi-file package transformation requires an explicit mapping")
        transformed, changes = transform_package(raw, case["mode"])
        if case["mode"] in {"baseline", "repeat"}:
            resolved = canonical
        elif case["mode"] == "registry_order":
            catalog = reversed_catalog(catalog)
            resolved = runtime.ScenarioCompilerV2(catalog=catalog).compile(
                runtime.ScenarioPackageV2.from_directory(path))
            changes = ["catalog.resource_registration_order", "catalog.model_registration_order"]
        else:
            resolved, catalog = runtime.compile_package(transformed)
        compilations.append({"canonical_resolved_hash": canonical.resolved_hash,
                             "variant_resolved_hash": resolved.resolved_hash,
                             "changes": changes, "original_manifest_sha256": sha(Path(path) / "scenario.yaml"),
                             "transformed_manifest": transformed,
                             "mode": case["mode"]})
        return resolved, catalog

    def create_probe(*args, **kwargs):
        native = original_create(*args, **kwargs)
        try:
            return SessionProbe(native, journal)
        except Exception:
            if native.state.value == "running":
                native.stop()
            native.close()
            raise

    try:
        with patch.object(runtime, "compile_candidate", compile_variant), patch.object(runtime, "create_candidate", create_probe):
            if hasattr(module, "create_candidate"):
                with patch.object(module, "create_candidate", create_probe):
                    result = module.run(**runner_arguments(case, module.run))
            else:
                result = module.run(**runner_arguments(case, module.run))
        complete = validate_result(result, case)
        if len(compilations) != 1 or journal.world_ticks != list(range(result["final_tick"] + 1)):
            raise ValueError("native journal must cover exactly one complete session from tick zero")
        if frozen_inputs() != before:
            raise ValueError("candidate sources or inputs changed during native invariance trial")
        journal.close()
        result["invariance_evidence"] = {"schema_version": "native-invariance-episode@1.0",
            "case": case, "compilation": compilations[0], "native_journal": journal_path.relative_to(ROOT).as_posix(),
            "native_journal_sha256": sha(journal_path), "journal_records": journal.records,
            "world_ticks": journal.world_ticks, "full_episode_completed": complete,
            "sources_inputs": before, "sources_inputs_unchanged": True,
            "trace_redaction": "Only authority_token values are redacted; ownership and execution outcomes remain recorded",
            "protected_before": protected, "protected_after": verify(),
            "scope": "Public API observations/submissions/step receipts and immutable referee frames through natural termination; not full checkpoint recovery or arbitrary-policy proof",
            "competition_accepted": False}
        target = case_path.with_suffix(".result.json")
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
        print("evidence=" + target.relative_to(ROOT).as_posix(), flush=True)
        return target
    finally:
        journal.close()
        verify()


def first_difference(left, right, path=""):
    if type(left) is not type(right):
        return {"path": path, "left": str(left)[:200], "right": str(right)[:200], "reason": "type"}
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return {"path": path, "reason": "keys", "different_keys": sorted(left.keys() ^ right.keys())}
        for key in sorted(left):
            result = first_difference(left[key], right[key], path + "/" + key)
            if result:
                return result
    elif isinstance(left, list):
        if len(left) != len(right):
            return {"path": path, "reason": "length", "left": len(left), "right": len(right)}
        for index, (a, b) in enumerate(zip(left, right)):
            result = first_difference(a, b, path + "/" + str(index))
            if result:
                return result
    elif left != right:
        return {"path": path, "reason": "value", "left": str(left)[:200], "right": str(right)[:200]}
    return None


def metadata_neutral(record):
    record = deepcopy(record)
    if record.get("kind") == "observation":
        metadata = record.get("observation", {}).get("metadata", {})
        if "resolved_hash" in metadata:
            metadata["resolved_hash"] = "<compiled-input-identity>"
    return record


def compare_journals(left, right, *, allow_compiled_identity=False, kinds=None):
    import itertools
    def records(stream):
        for line in stream:
            value = json.loads(line)
            if kinds is None or value.get("kind") in kinds:
                yield metadata_neutral(value) if allow_compiled_identity else value
    with left.open(encoding="utf-8") as a, right.open(encoding="utf-8") as b:
        for index, (record_a, record_b) in enumerate(itertools.zip_longest(records(a), records(b)), 1):
            if record_a is None or record_b is None:
                return {"record": index, "reason": "record count"}
            difference = first_difference(record_a, record_b)
            if difference:
                return {"record": index, **difference}
    return None


def summarize(directory):
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
    groups = {}
    for entry in state["recorded"]:
        path = ROOT / entry["evidence"]
        if sha(path) != entry["evidence_sha256"]:
            raise ValueError("native result changed after recording")
        result = json.loads(path.read_text(encoding="utf-8"))
        evidence = result["invariance_evidence"]
        if sha(ROOT / evidence["native_journal"]) != evidence["native_journal_sha256"]:
            raise ValueError("native journal changed after recording")
        case = evidence["case"]
        groups.setdefault((case["scenario_id"], case["difficulty"]), {})[case["mode"]] = result
    comparisons = []
    for key, modes in groups.items():
        if "baseline" not in modes:
            raise ValueError("recorded variant lacks its baseline")
        baseline = modes["baseline"]
        for mode in MODES[1:]:
            if mode not in modes:
                continue
            result = modes[mode]
            left = ROOT / baseline["invariance_evidence"]["native_journal"]
            right = ROOT / result["invariance_evidence"]["native_journal"]
            difference = compare_journals(left, right)
            behavioral_difference = compare_journals(left, right, allow_compiled_identity=True)
            comparisons.append({"scenario_id": key[0], "difficulty": key[1], "mode": mode,
                                "strict_native_api_equal": difference is None, "first_difference": difference,
                                "metadata_neutral_native_equal": behavioral_difference is None,
                                "first_metadata_neutral_difference": behavioral_difference,
                                "public_observations_equal": compare_journals(left, right, allow_compiled_identity=True, kinds={"observation"}) is None,
                                "submissions_equal": compare_journals(left, right, kinds={"submission"}) is None,
                                "baseline_final_tick": baseline["final_tick"], "variant_final_tick": result["final_tick"],
                                "scores_equal": baseline["scores"] == result["scores"],
                                "terminal_equal": baseline["terminal"] == result["terminal"],
                                "both_full_episodes": baseline["invariance_evidence"]["full_episode_completed"]
                                    and result["invariance_evidence"]["full_episode_completed"]})
    report = {"schema_version": "native-invariance-comparison@1.0", "plan_sha256": sha(directory / "plan.json"),
              "recorded_episodes": len(state["recorded"]), "planned_episodes": len(plan["cases"]),
              "completed_variant_groups": sum(set(x) == set(MODES) for x in groups.values()),
              "comparisons": comparisons, "comparison_protocol": "Exact values, types and ordering; native trace redacts authority_token values only. Separate metadata-neutral comparison ignores only observation.metadata.resolved_hash; RNG/loss samples and all other values remain strict",
              "competition_accepted": False, "goal_complete": False}
    save_json(directory / "comparison.json", report)
    return report


def prepare(seed, pilot=False):
    if type(seed) is not int or seed < 0:
        raise ValueError("use a nonnegative integer seed")
    pattern = re.compile(r'"(?:seed|seeds|seed_order)"\s*:\s*(?:' + str(seed) + r'\b|\[[^\]]*\b' + str(seed) + r'\b)')
    if any(pattern.search(path.read_text(encoding="utf-8")) for path in RESULTS.rglob("*.json")):
        raise ValueError("native invariance seed already used or reserved")
    cases = matrix_cases(seed)
    if pilot:
        cases = cases[:len(MODES)]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = RESULTS / ("native-invariance-pilot-" if pilot else "native-invariance-plan-")
    directory = directory.with_name(directory.name + stamp)
    directory.mkdir(parents=True, exist_ok=False)
    plan = {"schema_version": "native-invariance-plan@1.0", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "seed": seed, "pilot": pilot, "cases": cases, **frozen_inputs(), "protected_inputs": verify(),
            "scope": "Separate full-episode repetition, native scenario rename, declaration order and registration order probes; not task feasibility or full checkpoint recovery"}
    save_json(directory / "plan.json", plan)
    save_json(directory / "state.json", {"plan_sha256": sha(directory / "plan.json"), "recorded": [], "active": None})
    return directory


def run_next(directory, limit):
    directory = directory.resolve()
    if not directory.is_relative_to(RESULTS.resolve()) or type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("use a stored native plan and a bounded chunk of one to five cases")
    lock = directory / "execution.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid()}))
    try:
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        expected = matrix_cases(plan["seed"])[ :len(MODES)] if plan["pilot"] else matrix_cases(plan["seed"])
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        if (plan["cases"] != expected or state["plan_sha256"] != sha(directory / "plan.json")
                or state["active"] is not None or state.get("execution_error")):
            raise ValueError("plan changed or an active/uncertain case needs PID and log reconciliation")
        if [x["case_id"] for x in state["recorded"]] != [x["case_id"] for x in expected[:len(state["recorded"])]]:
            raise ValueError("completed cases do not form the planned prefix")
        summarize(directory)
        for case in expected[len(state["recorded"]):len(state["recorded"]) + limit]:
            if any(frozen_inputs()[key] != plan[key] for key in ("source_hashes", "input_hashes")):
                raise ValueError("sources or inputs differ from the frozen plan")
            case_path = directory / (case["case_id"] + ".case.json")
            if case_path.exists():
                raise ValueError("case artifact already exists; reconcile before any retry")
            save_json(case_path, case)
            command = [sys.executable, "-B", "-m", __package__ + ".native_invariance", "--case", str(case_path)]
            log_path = case_path.with_suffix(".log")
            with log_path.open("x", encoding="utf-8") as log:
                child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                state["active"] = {"case_id": case["case_id"], "pid": child.pid, "command": command,
                                   "log": log_path.relative_to(ROOT).as_posix()}
                save_json(directory / "state.json", state)
                print("START " + case["case_id"] + " pid=" + str(child.pid), flush=True)
                try:
                    child.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    state["active"]["observation_timeout"] = True
                    save_json(directory / "state.json", state)
                    raise RuntimeError("owned child may still be running; inspect PID/log before retry")
            result_path = case_path.with_suffix(".result.json")
            if child.returncode or not result_path.exists():
                state["execution_error"] = {"exit_code": child.returncode, "case_id": case["case_id"],
                                            "pid": child.pid, "log": log_path.relative_to(ROOT).as_posix()}
                state["active"] = None
                save_json(directory / "state.json", state)
                raise RuntimeError("native probe failed; read its stored log")
            if any(frozen_inputs()[key] != plan[key] for key in ("source_hashes", "input_hashes")):
                raise RuntimeError("sources or inputs changed during native probe")
            state["recorded"].append({"case_id": case["case_id"], "evidence": result_path.relative_to(ROOT).as_posix(),
                                      "evidence_sha256": sha(result_path), "exit_code": child.returncode})
            state["active"] = None
            save_json(directory / "state.json", state)
            print("RECORDED " + case["case_id"], flush=True)
        verify()
        return summarize(directory)
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare-seed", type=int)
    action.add_argument("--case", type=Path)
    action.add_argument("--run-plan", type=Path)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--max-cases", type=int, default=1)
    args = parser.parse_args()
    if args.prepare_seed is not None:
        print(prepare(args.prepare_seed, pilot=args.pilot))
    elif args.case:
        run_case(args.case)
    else:
        report = run_next(args.run_plan, args.max_cases)
        print(json.dumps({key: report[key] for key in ("recorded_episodes", "planned_episodes", "completed_variant_groups", "comparisons")}, indent=2))


if __name__ == "__main__":
    main()

"""Diagnostic native checkpoint contract probe, not a scoring workaround.

An in-memory test-only model and package exercise the existing public compiler,
registry, session and checkpoint APIs. No engine/canonical file or acceptance
assertion is patched. Expected rejection documents a limitation, not a passed
checkpoint gate. The zero-valued control is genuinely measured zero.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .build import ROOT
from .tracking import tracking
from . import runtime
from .calibration_matrix import frozen_inputs
from .protected_inputs import verify
from .validate_recon import referee_checkpoint_evidence
from .native_invariance import plain

MODEL_ID = "models.diagnostic-checkpoint-availability"
MODEL_VERSION = "1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_VERSION}"
MODES = ("measured_zero", "missing_then_zero", "omitted_output", "structured_unavailable")


class DiagnosticMetric:
    def __init__(self, record_output):
        self._record_output = record_output

    def bind_session(self, *, session_id, seed, parameters):
        if (set(parameters) != {"metric_id", "mode", "unit"}
                or parameters["mode"] not in MODES or parameters["unit"] != "1"):
            raise ValueError("diagnostic parameters must be explicit")
        self.session_id = session_id
        self.parameters = dict(parameters)
        self.last_tick, self.last_value = -1, None

    def evaluate(self, snapshot):
        tick = snapshot.tick
        mode, identifier = self.parameters["mode"], self.parameters["metric_id"]
        if mode == "omitted_output":
            produced = {}
        elif mode == "structured_unavailable":
            produced = {identifier: {"value": None, "data_status": "missing"}}
        else:
            produced = {identifier: None if mode == "missing_then_zero" and tick < 2 else 0.}
        self.last_tick = tick
        self.last_value = deepcopy(produced.get(identifier))
        self._record_output({"session_id": self.session_id, "mode": mode,
                             "tick": tick, "produced": deepcopy(produced)})
        return produced

    def snapshot(self):
        return {"parameters": deepcopy(self.parameters), "last_tick": self.last_tick,
                "last_value": deepcopy(self.last_value)}

    def restore(self, state):
        if set(state) != {"parameters", "last_tick", "last_value"} or state["parameters"] != self.parameters:
            raise ValueError("diagnostic checkpoint differs from its binding")
        self.last_tick, self.last_value = state["last_tick"], deepcopy(state["last_value"])

    def close(self):
        pass


def exception_evidence(error):
    values, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        values.append({"type": type(error).__name__, "error": str(error)})
        error = error.__cause__ or error.__context__
    return values


def build_fixture(mode):
    if mode not in MODES:
        raise ValueError("unknown diagnostic mode")
    base = runtime.load_candidate_catalog(allow_candidate=True)
    registry = runtime.ModelRegistryV2(interface_version="2.0")
    for metadata in base.model_registry.snapshot():
        def factory(definition, ref=metadata.exact_ref):
            return base.model_registry.create(ref, definition)
        registry.register(metadata, factory)
    observed_outputs = []
    def record_output(value):
        observed_outputs.append(deepcopy(value))
    def diagnostic_factory(_definition):
        return DiagnosticMetric(record_output)
    source_hash = "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    registry.register(runtime.ModelFactoryMetadataV2(
        schema_version="2.0", model_id=MODEL_ID, version=MODEL_VERSION, interface_version="2.0",
        input_schema="catalog-resource@2.0", output_schema="runtime-component@2.0",
        # The observer is probe/process-local; outputs do not depend on it.
        # Runtime state is recreated from the JSON checkpoint in each process.
        units={"score": "1"}, deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=source_hash, resource_types=("scoring",), field_units={"score": "1"}), diagnostic_factory)
    registry.freeze()
    resource = runtime.CatalogResourceV2(schema_version="2.0", resource_type="scoring",
        id="scoring.diagnostic-checkpoint-availability", version=MODEL_VERSION,
        engine_compatibility=">=2.0.0,<3.0.0", model_id=MODEL_REF, content={"unit": "1", "session_local": True})
    catalog = runtime.CatalogV2([*base.snapshot(), resource], engine_version="2.0.0", model_registry=registry)
    package = deepcopy(tracking(1)[0])
    scenario = package["scenario"]
    shore = next(e for e in scenario["entities"] if e["id"] == "unit.r04")
    scenario.update(scenario_id=f"diagnostic.checkpoint-availability.{mode}", entities=[shore],
                    formations=[], events=[], mission_states=["state.active"], mission_rules=[],
                    controller_slots=[s for s in scenario["controller_slots"] if s["id"] == shore["controller_slot"]])
    scenario["world"].update(duration_ticks=4, zones=[], roe_rules=[])
    metric = deepcopy(scenario["scoring"]["metrics"][0])
    metric.update(id="metric.probe", selector={"schema_version": "2.0", "entity_ids": [shore["id"]]},
                  weight=1., plugin_ref=MODEL_REF, plugin_parameters={"metric_id": "metric.probe", "mode": mode, "unit": "1"})
    scenario["scoring"]["metrics"] = [metric]
    scenario["score_metrics"] = []
    resolved = runtime.ScenarioCompilerV2(catalog=catalog).compile(runtime.ScenarioPackageV2.from_mapping(package))
    return package, resolved, catalog, observed_outputs


def run_probe(mode):
    package, resolved, catalog, observed_outputs = build_fixture(mode)
    session_id = f"diagnostic-checkpoint-availability-{mode}"
    session = runtime.SessionLifecycleV2.create(
        session_id=session_id, seed=0, resolved=resolved, expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash, model_registry_hash=resolved.model_registry_hash,
        world_factory=runtime.WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=runtime.RunnerModeV2.LOCKSTEP, physics_dt_seconds=1., decision_interval_ticks=1)
    session.load().start()
    rows = []
    try:
        checkpoint, _ = referee_checkpoint_evidence(session)
        rows.append({"tick": 0, "checkpoint": checkpoint, "score_receipts": []})
        for tick in (1, 2, 3):
            try:
                receipt = session.step(operation_id=f"probe-{tick}", expected_tick=tick - 1)
            except Exception as error:
                rows.append({"requested_tick": tick, "step_error": exception_evidence(error)})
                break
            checkpoint, _ = referee_checkpoint_evidence(session)
            rows.append({"tick": session.world_view.tick, "checkpoint": checkpoint,
                         "score_receipts": [plain(x) for x in receipt.world_receipt.score_receipts]})
        sessions = {row["session_id"] for row in observed_outputs}
        if (len(sessions) != 1 or any(row["mode"] != mode for row in observed_outputs)
                or len({row["tick"] for row in observed_outputs}) != len(observed_outputs)):
            errors = [row["step_error"] for row in rows if "step_error" in row]
            raise ValueError(f"diagnostic output scope is not unique: sessions={sessions}, step_errors={errors}")
        return {"mode": mode, "fixture": package, "resolved_hash": resolved.resolved_hash,
                "rows": rows, "diagnostic_binding_session_ids": sorted(sessions),
                "diagnostic_plugin_outputs": [{"tick": row["tick"], "produced": row["produced"]}
                                               for row in observed_outputs],
                "checkpoint_acceptance_passed": False,
                "scope": "In-memory one-stationary-entity API diagnostic, not a canonical scene or a recovery workaround"}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()


def main():
    before, protected = frozen_inputs(), verify()
    results = [run_probe(mode) for mode in MODES]
    after = frozen_inputs()
    if before != after:
        raise RuntimeError("canonical sources or inputs changed during the diagnostic")
    report = {"schema_version": "checkpoint-availability-diagnostic@1.0",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "cases": results, "source_input_hashes": before, "sources_inputs_unchanged": True,
              "protected_before": protected, "protected_after": verify(),
              "diagnostic_only": True, "canonical_scene_changed": False,
              "engine_changed": False, "competition_accepted": False}
    path = ROOT / "artifacts/competition_four_categories" / (
        "checkpoint-availability-diagnostic-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print("REPORT", path)
    for result in results:
        print(result["mode"], [(r.get("tick", r.get("requested_tick")),
              r.get("checkpoint", {}).get("status", "step_error")) for r in result["rows"]])


if __name__ == "__main__":
    main()

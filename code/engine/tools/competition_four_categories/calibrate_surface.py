"""Empirical navigation mapping for the existing native MMG proxy, not real-vessel validation.

Only ephemeral versioned resources and ordinary native navigation actions are
used. No scoring thresholds, damage models or protected source files are edited.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

import yaml
from openmdbench.catalog.v2 import CatalogResourceV2, CatalogV2, ModelRegistryV2
from openmdbench.dynamics.native_v2 import register_native_dynamics_models_v2
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from .build import ROOT, reconnaissance, entity, selector, yaml_text
from .runtime import load_candidate_catalog
from .validate_denial import submit_navigation
from .protected_inputs import verify

OUT = ROOT / "artifacts/competition_four_categories/surface_calibration"
MAX_SPEED = 12.9
FIT_SPEEDS = [2., 4., 6., 8., 10., 12.]
HOLDOUT_SPEEDS = [3., 5., 7., 9., 11., 12.9]
TOLERANCES = {"relative_speed_error": .05, "absolute_speed_error_mps": .2,
              "settling_window_span_mps": .03, "straight_heading_error_deg": 1.}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_ratio():
    path = ROOT / "catalog/v2/md_ad_006.yaml"
    row = next(r for r in yaml.safe_load(path.read_text(encoding="utf-8"))["resources"]
               if r["id"] == "dynamics.armed-usv" and r["version"] == "2.0.0")
    return row["content"]["max_nps"]/row["content"]["max_speed_mps"]


def calibration_catalog(ratio, label):
    if not isinstance(ratio, (float, int)) or not math.isfinite(ratio) or not 0 < ratio*MAX_SPEED <= 240:
        raise ValueError("probe parameters exceed the native trusted envelope")
    base = load_candidate_catalog(allow_candidate=True)
    resources = list(base.snapshot())
    dynamic = next(r for r in resources if r.id == "dynamics.picket-usv" and r.version == "2.0.0").model_dump(mode="json")
    platform = next(r for r in resources if r.id == "platform.picket-usv" and r.version == "2.0.0").model_dump(mode="json")
    dynamic.update(id=f"dynamics.competition-surface-{label}", version="0.1.0")
    dynamic["content"].update(max_speed_mps=MAX_SPEED, max_nps=ratio*MAX_SPEED)
    platform.update(id=f"platform.competition-surface-{label}", version="0.1.0")
    dref, pref = dynamic["id"]+"@0.1.0", platform["id"]+"@0.1.0"
    platform["content"]["allowed_dynamics"] = [dref]
    registry = ModelRegistryV2(interface_version="2.0")
    original_registry = base.model_registry
    for metadata in original_registry.snapshot():
        if not metadata.model_id.startswith("models.native-"):
            registry.register(metadata, lambda definition, ref=metadata.exact_ref: original_registry.create(ref, definition))
    register_native_dynamics_models_v2(registry)
    registry.freeze()
    added = [CatalogResourceV2.model_validate(dynamic), CatalogResourceV2.model_validate(platform)]
    catalog = CatalogV2((*resources, *added), engine_version="2.0.0", model_registry=registry)
    return catalog, pref, dref, dynamic, platform


def trial_package(speeds, pref, dref, horizon=180, initial_speed=0.):
    package, _ = reconnaissance("easy")
    s = package["scenario"]
    template = deepcopy(s["controller_slots"][0])
    vessels = []
    for index, speed in enumerate(speeds):
        identifier = f"unit.r{index+1:02d}"
        vessel = entity(identifier, "red", "surface", [0., index*350., 0.], None, [initial_speed, 0., 0.])
        vessel.update(platform_ref=pref, dynamics_ref=dref)
        vessels.append(vessel)
    s["scenario_id"] = "competition.native-surface-mapping-probe"
    s["entities"] = vessels
    s["world"].update(duration_ticks=horizon+1, zones=[])
    s.pop("scoring", None)
    s["score_metrics"] = []
    rule = deepcopy(next(r for r in s["mission_rules"] if r["id"] == "rule.timeout"))
    rule["condition"]["parameters"]["tick"] = horizon+1
    marker_id = rule["outcome"]["emit_event"]
    event = deepcopy(next(e for e in s["events"] if e["id"] == marker_id))
    event["trigger"]["tick"] = horizon+1
    s["events"], s["mission_rules"] = [event], [rule]
    s["controller_slots"] = [{**deepcopy(template), "id": e["controller_slot"], "controller_id": f"agent.{e['id']}",
        "faction_id": "red", "controller_endpoint_ref": e["id"], "selector": selector([e["id"]])} for e in vessels]
    return package


def run_trial(label, ratio, speeds, *, maneuver=False):
    before = verify()
    catalog, pref, dref, dynamic, platform = calibration_catalog(ratio, label)
    horizon = 240 if maneuver else 180
    package = trial_package(speeds, pref, dref, horizon=horizon, initial_speed=6. if maneuver else 0.)
    resolved = ScenarioCompilerV2(catalog=catalog).compile(ScenarioPackageV2.from_mapping(package))
    session = SessionLifecycleV2.create(session_id=f"native-surface-{label}", seed=601, resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash, catalog_hash=resolved.catalog_hash, model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry), runner_mode="lockstep", physics_dt_seconds=1., decision_interval_ticks=1)
    trace, began = [], time.monotonic()
    try:
        session.load().start()
        for index, speed in enumerate(speeds):
            submit_navigation(session, f"unit.r{index+1:02d}", "red", 0, {"valid_until_tick": horizon,
                "payload": {"speed_mps": speed, "heading_deg": 90.}})
        for tick in range(horizon):
            if maneuver and tick == 60:
                # Separate speed-step and turn probes, no score-driven tuning.
                submit_navigation(session, "unit.r01", "red", tick, {"valid_until_tick": horizon, "payload": {"speed_mps": 3., "heading_deg": 90.}})
                submit_navigation(session, "unit.r02", "red", tick, {"valid_until_tick": horizon, "payload": {"speed_mps": 6., "heading_deg": 0.}})
            session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            rows = []
            for index, requested in enumerate(speeds):
                identifier = f"unit.r{index+1:02d}"; state = session.world_view.get(identifier).state
                speed = math.hypot(state.velocity_mps[0], state.velocity_mps[1])
                rows.append({"entity_id": identifier, "speed_mps": speed, "position_m": list(state.position_m),
                    "heading_deg": state.heading_deg, "lifecycle": state.lifecycle})
            trace.append({"tick": tick+1, "vessels": rows})
        summaries = []
        for index, requested in enumerate(speeds):
            values = [r["vessels"][index]["speed_mps"] for r in trace[-30:]]
            final = trace[-1]["vessels"][index]
            target = 3. if maneuver and index == 0 else requested
            target_heading = 0. if maneuver and index == 1 else 90.
            actual = statistics.mean(values)
            summaries.append({"entity_id": final["entity_id"], "requested_speed_mps": target,
                "settled_speed_mps": actual, "relative_error": abs(actual-target)/target,
                "absolute_error_mps": abs(actual-target), "settling_span_mps": max(values)-min(values),
                "heading_error_deg": abs((final["heading_deg"]-target_heading+180.)%360.-180.),
                "final_position_m": final["position_m"], "lifecycle": final["lifecycle"]})
        result = {"schema_version": "native-surface-calibration@1.0", "label": label,
            "scope": "native MMG proxy control mapping, not real-vessel physical validation",
            "ratio_nps_per_mps": ratio, "maximum_speed_mps": MAX_SPEED, "maximum_nps": ratio*MAX_SPEED,
            "seed": 601, "horizon_ticks": horizon, "physics_dt_seconds": 1., "maneuver": maneuver,
            "summaries": summaries, "trace": trace, "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "resolved_hash": resolved.resolved_hash, "catalog_hash": resolved.catalog_hash, "model_registry_hash": resolved.model_registry_hash,
            "source_sha256": sha(__file__), "source_catalog_sha256": sha(ROOT/"catalog/v2/md_ad_006.yaml"),
            "elapsed_wall_seconds": time.monotonic()-began, "tolerances": TOLERANCES,
            "resource_definitions": [dynamic, platform], "scenario": package,
            "protected_inputs_before": before, "protected_inputs_after": verify()}
        OUT.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = OUT / f"{label}-{stamp}.json"
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"label": label, "ratio": ratio, "summaries": summaries, "evidence": path.relative_to(ROOT).as_posix()}), flush=True)
        return path, result
    finally:
        if session.state.value == "running": session.stop()
        session.close()
        verify()


def fit_mapping(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data["source_sha256"] != sha(__file__) or data["label"] != "reference":
        raise ValueError("reference probe does not match this calibration implementation")
    rows = data["summaries"]
    if [r["requested_speed_mps"] for r in rows] != FIT_SPEEDS:
        raise ValueError("reference speed set differs from the predeclared fit set")
    gain = sum(r["requested_speed_mps"]*r["settled_speed_mps"] for r in rows)/sum(r["requested_speed_mps"]**2 for r in rows)
    if not math.isfinite(gain) or gain <= 0:
        raise ValueError("invalid fitted speed gain")
    ratio = data["ratio_nps_per_mps"]/gain
    return {"schema_version": "surface-navigation-profile@1.0", "status": "fitted_pending_holdout",
        "fidelity": "UNVALIDATED_REAL_WORLD", "maximum_speed_mps": MAX_SPEED, "nps_per_mps": ratio,
        "maximum_nps": ratio*MAX_SPEED, "reference_gain": gain, "fit_speeds_mps": FIT_SPEEDS,
        "holdout_speeds_mps": HOLDOUT_SPEEDS, "tolerances": TOLERANCES,
        "reference_evidence": Path(path).resolve().relative_to(ROOT).as_posix(),
        "reference_evidence_sha256": sha(path), "calibration_source_sha256": sha(__file__),
        "protected_input_baseline_sha256": data["protected_inputs_after"]["baseline_sha256"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("reference", "fit", "holdout", "maneuver"), required=True)
    parser.add_argument("--reference")
    parser.add_argument("--profile")
    args = parser.parse_args()
    if args.phase == "reference":
        run_trial("reference", reference_ratio(), FIT_SPEEDS)
    elif args.phase == "fit":
        if not args.reference: parser.error("fit requires --reference")
        profile = fit_mapping(ROOT / args.reference)
        path = OUT / "fitted-profile.json"; path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        print(json.dumps(profile, indent=2))
    else:
        if not args.profile: parser.error("holdout/maneuver requires --profile")
        profile = json.loads((ROOT / args.profile).read_text(encoding="utf-8"))
        if profile["calibration_source_sha256"] != sha(__file__): raise ValueError("profile source version differs")
        run_trial(args.phase, profile["nps_per_mps"], HOLDOUT_SPEEDS if args.phase == "holdout" else [6.,6.], maneuver=args.phase == "maneuver")


if __name__ == "__main__": main()

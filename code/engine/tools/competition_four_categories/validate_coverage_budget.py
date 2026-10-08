"""Controlled native policy/budget calibration, never an automatic scenario promotion."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json

from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2, RunnerModeV2
from openmdbench.world.factory_v2 import WorldFactoryV2

from . import coverage_tracking_policy, tracking_budget_profile, identity_tracking_policy, shore_beacon_policy
from . import tracking_policy, validate_emergency, validate_tracking as adapter
from . import validate_tracking_reports as execution
from .build import ROOT, yaml_text
from .runtime import compile_package
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import plain

POLICIES = ("beacon", "coverage")


def source_fingerprints():
    return {**execution.source_fingerprints(), "validator_sha256": adapter.sha(__file__),
        "executor_sha256": adapter.sha(execution.__file__),
        "coverage_policy_sha256": adapter.sha(coverage_tracking_policy.__file__),
        "profile_factory_sha256": adapter.sha(tracking_budget_profile.__file__),
        "identity_policy_sha256": adapter.sha(identity_tracking_policy.__file__),
        "shore_policy_sha256": adapter.sha(shore_beacon_policy.__file__)}


def run(profile, policy, mode, seed):
    if profile not in tracking_budget_profile.PROFILES or policy not in POLICIES or mode not in execution.MODES:
        raise ValueError("explicit calibration profile, policy and mode required")
    verify_protected_inputs()
    package, brief, opponent_plan, provenance = tracking_budget_profile.load_profile(8, profile)
    fingerprints = source_fingerprints()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT/"artifacts/competition_four_categories/calibration_inputs"/f"coverage-{profile}-{policy}-{mode}-{seed}-{stamp}"
    folder.mkdir(parents=True, exist_ok=False)
    contents = {"scenario.yaml": yaml_text(package), "public_brief.json": json.dumps(brief, indent=2),
                "scripted_blue_policy.json": json.dumps(opponent_plan, indent=2), "profile_provenance.json": json.dumps(provenance, indent=2)}
    for name, text in contents.items(): (folder/name).write_text(text, encoding="utf-8")
    input_hashes = {name: adapter.sha(folder/name) for name in contents}
    resolved, catalog = compile_package(package)
    actor_type = coverage_tracking_policy.CoverageReportingPolicy if policy == "coverage" else shore_beacon_policy.BeaconIdentityReportingPolicy
    agents = {i: actor_type(brief, i, mode) for i in brief["track_reporting"]["reporter_ids"]}
    support = {i: shore_beacon_policy.ShoreBindingPolicy(brief, i) for i in brief["observers"]
               if brief["observer_domains"][i] == "shore" and i not in agents}
    opponent = tracking_policy.ScheduledNavigationPolicy(opponent_plan)
    session = SessionLifecycleV2.create(
        session_id=f"coverage-trk008-{profile}-{policy}-{mode}-{seed}", seed=seed, resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash, catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash, world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=RunnerModeV2.LOCKSTEP, physics_dt_seconds=resolved.world.tick_seconds, decision_interval_ticks=1)
    session = session.load().start()
    try:
        result = execution.execute(session, brief, opponent, mode, agents=agents, support_agents=support)
        if fingerprints != source_fingerprints(): raise AssertionError("calibration source changed while running")
        if any(adapter.sha(folder/name) != digest for name, digest in input_hashes.items()):
            raise AssertionError("staged calibration inputs changed while running")
        canonical = tracking_budget_profile.PACKAGES/"md_trk_008_standard"
        if any(adapter.sha(canonical/name) != digest for name, digest in provenance["canonical_file_hashes"].items()):
            raise AssertionError("canonical scenario changed during calibration")
        peers = []
        for record in session.world_view.presentation_snapshot().event_state.message_queue:
            try: body = json.loads(record.get("payload", ""))
            except (ValueError, TypeError): continue
            if isinstance(body, dict) and body.get("schema_version") == identity_tracking_policy.PEER_PROTOCOL:
                peers.append(plain(record))
        diagnostics = {i: {"binding_events": a.tracker.binding_events,
            "own_bound_tracks": [a.tracker.labels[n] for owner, n in a.tracker.owner_labels if owner == i],
            "unobserved_public_tracks": [a.tracker.labels[n] for n,t in enumerate(a.tracker.tracks) if t["observed_tick"] is None],
            "primary_designations": getattr(a.tracker, "primary_designations", None),
            "backup_designations": getattr(a.tracker, "backup_designations", None),
            "rejected_peer_claims": a.tracker.rejected_peer_claims} for i,a in agents.items()}
        return {**result, "policy": f"calibration-{policy}-{mode}", "asset_profile": profile, "seed": seed,
            "control_version": coverage_tracking_policy.POLICY_VERSION if policy == "coverage" else "beacon-v1",
            "calibration_only": True, "canonical_scenario_unchanged": True, **fingerprints,
            "staged_input_path": folder.relative_to(ROOT).as_posix(), "staged_input_hashes": input_hashes,
            "profile_provenance": provenance, "policy_diagnostics": diagnostics, "peer_delivery_evidence": peers,
            "support_observers": sorted(support), "official_reporters": brief["track_reporting"]["reporter_ids"],
            "resolved_hash": resolved.resolved_hash, "catalog_hash": resolved.catalog_hash, "model_registry_hash": resolved.model_registry_hash,
            "policy_source_sha256": adapter.sha(tracking_policy.__file__),
            "scripted_policy_sha256": adapter.sha(folder/"scripted_blue_policy.json"),
            "public_brief_sha256": adapter.sha(folder/"public_brief.json"),
            "privacy_validator_sha256": adapter.sha(validate_emergency.__file__),
            "engine_contact_source_sha256": adapter.sha(ROOT/"openmdbench/world/factory_v2.py")}
    finally:
        if session.state.value == "running": session.stop()
        session.close()
        verify_protected_inputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tracking_budget_profile.PROFILES, required=True)
    parser.add_argument("--policy", choices=POLICIES, required=True)
    parser.add_argument("--mode", choices=execution.MODES, default="honest")
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args(); result = run(args.profile, args.policy, args.mode, args.seed)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = ROOT/"artifacts/competition_four_categories"/f"coverage-trial-{args.profile}-{args.policy}-{args.mode}-{args.seed}-{stamp}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("asset_profile", "policy", "seed", "status", "final_tick", "scores")}), flush=True)
    print(f"evidence={path.relative_to(ROOT)}", flush=True)
    if result["failure"]: raise SystemExit(2)


if __name__ == "__main__":
    main()

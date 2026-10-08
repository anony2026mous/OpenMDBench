"""Canonical TRK008 candidate entrypoint using the validated reference budget."""
from __future__ import annotations
import argparse
import json

from . import coverage_tracking_policy, identity_tracking_policy, shore_beacon_policy
from . import tracking_policy, validate_emergency, validate_tracking as adapter
from . import validate_tracking_reports as execution
from .build import ROOT, PACKAGES
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import plain

MODES = execution.MODES


def source_fingerprints():
    return {**execution.source_fingerprints(), "validator_sha256": adapter.sha(__file__),
        "executor_sha256": adapter.sha(execution.__file__),
        "coverage_policy_sha256": adapter.sha(coverage_tracking_policy.__file__),
        "identity_policy_sha256": adapter.sha(identity_tracking_policy.__file__),
        "shore_policy_sha256": adapter.sha(shore_beacon_policy.__file__)}


def run(number, mode, seed):
    if number != 8 or mode not in MODES:
        raise ValueError("canonical coverage entrypoint is currently scoped to TRK008")
    verify_protected_inputs()
    path = PACKAGES/"md_trk_008_standard"
    brief_path, plan_path = path/"public_brief.json", path/"scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    if brief.get("asset_profile", {}).get("name") != "DEF-P3" or brief["difficulty"] != "standard":
        raise ValueError("validated reference-budget candidate is not installed")
    opponent = tracking_policy.ScheduledNavigationPolicy(json.loads(plan_path.read_text(encoding="utf-8")))
    agents = {i: coverage_tracking_policy.CoverageReportingPolicy(brief, i, mode) for i in brief["track_reporting"]["reporter_ids"]}
    support = {i: shore_beacon_policy.ShoreBindingPolicy(brief, i) for i in brief["observers"]
               if brief["observer_domains"][i] == "shore" and i not in agents}
    fingerprints = source_fingerprints()
    session = create_candidate(path, seed=seed, session_id=f"coverage-trk008-DEF-P3-coverage-{mode}-{seed}")
    try:
        result = execution.execute(session, brief, opponent, mode, agents=agents, support_agents=support)
        if fingerprints != source_fingerprints(): raise AssertionError("canonical trial sources changed while running")
        peers = []
        for record in session.world_view.presentation_snapshot().event_state.message_queue:
            try: body = json.loads(record.get("payload", ""))
            except (ValueError, TypeError): continue
            if isinstance(body, dict) and body.get("schema_version") == identity_tracking_policy.PEER_PROTOCOL:
                peers.append(plain(record))
        return {**result, "policy": f"coverage-{mode}", "seed": seed, **fingerprints,
            "control_version": coverage_tracking_policy.POLICY_VERSION, "asset_profile": brief["asset_profile"]["name"],
            "canonical_candidate_entrypoint": True, "calibration_only": False,
            "official_reporters": list(brief["track_reporting"]["reporter_ids"]), "support_observers": sorted(support),
            "peer_delivery_evidence": peers,
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash,
            "policy_source_sha256": adapter.sha(tracking_policy.__file__), "scripted_policy_sha256": adapter.sha(plan_path),
            "public_brief_sha256": adapter.sha(brief_path), "privacy_validator_sha256": adapter.sha(validate_emergency.__file__),
            "engine_contact_source_sha256": adapter.sha(ROOT/"openmdbench/world/factory_v2.py")}
    finally:
        if session.state.value == "running": session.stop()
        session.close()
        verify_protected_inputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=(8,), default=8)
    parser.add_argument("--mode", choices=MODES, default="honest")
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args(); result = run(args.scenario, args.mode, args.seed); path = adapter.save_result(result)
    print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
    print(f"evidence={path.relative_to(ROOT)}", flush=True)
    if result["failure"]: raise SystemExit(2)


if __name__ == "__main__":
    main()

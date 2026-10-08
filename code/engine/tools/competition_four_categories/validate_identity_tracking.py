"""Native trials of persistent public identity and actual peer communication."""
from __future__ import annotations

import argparse
import json

from . import identity_tracking_policy, tracking_policy, validate_emergency
from . import validate_tracking as adapter
from . import validate_tracking_reports as execution
from .build import ROOT, PACKAGES
from .protected_inputs import verify as verify_protected_inputs
from .runtime import create_candidate
from .visibility_audit import plain

MODES = execution.MODES


def source_fingerprints():
    return {**execution.source_fingerprints(),
        "validator_sha256": adapter.sha(__file__),
        "executor_sha256": adapter.sha(execution.__file__),
        "identity_policy_sha256": adapter.sha(identity_tracking_policy.__file__)}


def run(number, mode, seed):
    if number not in (7, 8) or mode not in MODES:
        raise ValueError("identity report trial requires TRK007/008 and a declared mode")
    verify_protected_inputs()
    path = PACKAGES/f"md_trk_{number:03d}_standard"
    brief_path, plan_path = path/"public_brief.json", path/"scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = tracking_policy.ScheduledNavigationPolicy(json.loads(plan_path.read_text(encoding="utf-8")))
    agents = {i: identity_tracking_policy.IdentityReportingPolicy(brief, i, mode)
              for i in brief["track_reporting"]["reporter_ids"]}
    fingerprints = source_fingerprints()
    session = create_candidate(path, seed=seed, session_id=f"candidate-trk{number}-identity-{mode}-{seed}")
    try:
        result = execution.execute(session, brief, opponent, mode, agents=agents)
        peers = []
        for record in session.world_view.presentation_snapshot().event_state.message_queue:
            try:
                body = json.loads(record.get("payload", ""))
            except (ValueError, TypeError):
                continue
            if isinstance(body, dict) and body.get("schema_version") == identity_tracking_policy.PEER_PROTOCOL:
                peers.append(plain(record))
        if fingerprints != source_fingerprints():
            raise AssertionError("identity trial sources changed during execution")
        diagnostics = {i: {"binding_events": agent.tracker.binding_events,
            "unobserved_public_tracks": [agent.tracker.labels[n] for n, track in enumerate(agent.tracker.tracks) if track["observed_tick"] is None],
            "own_bound_tracks": [agent.tracker.labels[n] for owner, n in agent.tracker.owner_labels if owner == i],
            "rejected_peer_claims": agent.tracker.rejected_peer_claims} for i, agent in agents.items()}
        return {**result, "policy": f"identity-{mode}", "seed": seed, **fingerprints,
            "identity_peer_delivery_evidence": peers, "identity_diagnostics": diagnostics,
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash,
            "policy_source_sha256": adapter.sha(tracking_policy.__file__),
            "scripted_policy_sha256": adapter.sha(plan_path),
            "privacy_validator_sha256": adapter.sha(validate_emergency.__file__),
            "public_brief_sha256": adapter.sha(brief_path),
            "engine_contact_source_sha256": adapter.sha(ROOT/"openmdbench/world/factory_v2.py")}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=(7, 8), required=True)
    parser.add_argument("--mode", choices=MODES, default="honest")
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args()
    result = run(args.scenario, args.mode, args.seed)
    path = adapter.save_result(result)
    print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
    print(f"evidence={path.relative_to(ROOT)}", flush=True)
    if result["failure"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

"""Evaluate the allocated public-observation policy on unchanged tracking packages.

The native session owns all state evolution and scoring. The existing tracking
runner remains unchanged; its action and score adapters are explicitly hashed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from . import allocated_tracking_policy, tracking_policy, validate_emergency
from . import validate_tracking as adapter
from .build import PACKAGES, ROOT
from .protected_inputs import verify as verify_protected_inputs
from .runtime import create_candidate
from .visibility_audit import VisibilityAudit


def source_fingerprints():
    return {
        "validator_sha256": adapter.sha(__file__),
        "evaluated_policy_source_sha256": adapter.sha(allocated_tracking_policy.__file__),
        "action_adapter_sha256": adapter.sha(adapter.__file__),
    }


def run(number, seed):
    if number not in range(1, 9):
        raise ValueError("tracking scenario must be 1..8")
    verify_protected_inputs()
    path = PACKAGES / f"md_trk_{number:03d}_standard"
    brief_path, opponent_path = path/"public_brief.json", path/"scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = tracking_policy.ScheduledNavigationPolicy(json.loads(opponent_path.read_text(encoding="utf-8")))
    followers = {i: allocated_tracking_policy.AllocatedTrackPolicy(brief, i) for i in brief["mobile_observers"]}
    fingerprints = source_fingerprints()
    session = create_candidate(path, seed=seed, session_id=f"candidate-trk{number}-allocated-{seed}")
    trace, actions, failure, checked = [], [], None, 0
    began = time.monotonic()
    try:
        auditor = VisibilityAudit(session, {i: f"slot.{i}" for i in brief["observers"]}, faction_id=brief["evaluated_side"])
        red = adapter.observe(session, brief["observers"])
        failure = validate_emergency.audit_observations(red, auditor=auditor)
        checked += len(red)
        for tick in range(brief["adjudication_tick"]):
            if failure:
                break
            blue = adapter.observe(session, opponent.entity_ids)
            for identifier, command in opponent.commands(tick, blue).items():
                receipt = adapter.submit_navigation(session, identifier=identifier, faction=opponent.plan["faction_id"],
                    tick=tick, payload=command["payload"], valid_until_tick=command["valid_until_tick"])
                actions.append({"faction": "blue", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
            if tick < brief["scoring_deadline_tick"] and tick % 4 == 0:
                for identifier, follower in followers.items():
                    payload = follower.command(red[identifier])
                    if payload is None:
                        continue
                    receipt = adapter.submit_navigation(session, identifier=identifier, faction=brief["evaluated_side"],
                        tick=tick, payload=payload, valid_until_tick=min(tick+8, brief["scoring_deadline_tick"]))
                    actions.append({"faction": "red", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
            step_receipt = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            red = adapter.observe(session, brief["observers"])
            checked += len(red)
            failure = validate_emergency.audit_observations(red, auditor=auditor)
            frame = session.world_view.presentation_snapshot()
            mission = frame.mission_scoring_checkpoint
            terminal = mission["terminal_result"]
            scores, score_status = adapter.score_evidence(step_receipt)
            blue = adapter.observe(session, opponent.entity_ids)
            trace.append({"tick": session.world_view.tick,
                "red_own_states": {i: o["own_entities"] for i, o in red.items()},
                "referee_blue_states": {i: o["own_entities"] for i, o in blue.items()},
                "observed_contact_counts": {i: len(o["organic_contacts"]) for i, o in red.items()},
                "delivered_shared_contact_counts": {i: len(o["shared_contacts"]) for i, o in red.items()},
                "policy_designation_assignments": {i: list(p.assigned_designations) for i, p in followers.items()},
                "policy_public_track_estimates": {i: deepcopy(p.tracks) for i, p in followers.items()},
                "referee_event_evidence": {"weather_event_id": frame.event_state.weather_state.get("event_id"),
                    "component_suppression_keys": sorted(frame.event_state.component_suppressions),
                    "mission_markers": sorted(frame.event_state.mission_marker_ledger)},
                "scores": scores, "score_data_status": score_status,
                "native_score_state": dict(mission["score_state"]),
                "terminal": dict(terminal) if terminal else None})
            if terminal or failure:
                break
        final = trace[-1] if trace else {"scores": {}, "terminal": None}
        if not failure and not final["terminal"]:
            raise AssertionError("native tracking mission did not terminate at its horizon")
        if final["terminal"] and session.world_view.tick < brief["adjudication_tick"]:
            raise AssertionError("tracking must not terminate after an early detection")
        if fingerprints != source_fingerprints():
            raise AssertionError("evaluated policy or adapter changed while the episode was running")
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard", "policy": "allocated",
            "seed": seed, "status": failure["status"] if failure else "candidate_validation_not_release",
            "competition_accepted": False, "failure": failure, "final_tick": session.world_view.tick,
            "scores": final["scores"], "terminal": final["terminal"], "trace": trace,
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash, **fingerprints,
            "policy_source_sha256": adapter.sha(tracking_policy.__file__),
            "scripted_policy_sha256": adapter.sha(opponent_path),
            "privacy_validator_sha256": adapter.sha(validate_emergency.__file__),
            "public_brief_sha256": adapter.sha(brief_path),
            "engine_contact_source_sha256": adapter.sha(ROOT/"openmdbench/world/factory_v2.py"),
            "observations_checked": checked, "submitted_actions": actions, "visibility_audit": auditor.summary()}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=range(1, 9), required=True)
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args()
    result = run(args.scenario, args.seed)
    path = adapter.save_result(result)
    print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
    print(f"evidence={path.relative_to(ROOT)}", flush=True)
    if result["failure"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

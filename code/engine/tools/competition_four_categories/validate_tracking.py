"""Native tracking episodes with strict controller visibility and bound policies."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from .build import PACKAGES, ROOT
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit
from . import tracking_policy, validate_emergency


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observe(session, identifiers):
    return {i: session.world_view.controller_observation(controller_slot_id=f"slot.{i}").model_dump(mode="json")
            for i in identifiers}


def submit_navigation(session, *, identifier, faction, tick, payload, valid_until_tick):
    command = PersistentCommandV2(schema_version="2.0", entity_id=identifier, faction_id=faction,
        based_on_tick=tick, valid_until_tick=valid_until_tick, command_id=f"nav-{identifier}-{tick}",
        command_type="navigation", payload=payload)
    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id,
        batch_id=f"batch-{identifier}-{tick}", idempotency_key=f"batch-{identifier}-{tick}",
        faction_id=faction, based_on_tick=tick, valid_until_tick=valid_until_tick, persistent_commands=(command,))
    return session.submit_actions(batch=batch, authority_token=f"authority.{identifier}",
        operation_id=f"submit-{identifier}-{tick}", expected_tick=tick)


def score_evidence(step_receipt):
    receipts = step_receipt.world_receipt.score_receipts
    if not receipts:
        raise AssertionError("native score receipt missing after an authoritative tick")
    last = max(receipts, key=lambda r: r.tick)
    metrics = last.metric_receipts
    # Native missing receipts retain a numeric placeholder in raw_value. Status
    # is authoritative: never present that placeholder as an observed zero score.
    return ({m.metric_id: m.raw_value if m.data_status == "available" else None for m in metrics},
            {m.metric_id: m.data_status for m in metrics})


def run(number, policy, seed):
    if policy not in {"idle", "follow", "cooperative"}:
        raise ValueError("unknown tracking baseline")
    path = PACKAGES / f"md_trk_{number:03d}_standard"
    brief_path, opponent_path = path / "public_brief.json", path / "scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = tracking_policy.ScheduledNavigationPolicy(json.loads(opponent_path.read_text(encoding="utf-8")))
    policy_type = tracking_policy.CooperativeTrackPolicy if policy == "cooperative" else tracking_policy.ContactFollowPolicy
    followers = {i: policy_type(brief, i) for i in brief["mobile_observers"]}
    session = create_candidate(path, seed=seed, session_id=f"candidate-trk{number}-{policy}-{seed}")
    trace, actions, failure, checked = [], [], None, 0
    began = time.monotonic()
    try:
        auditor = VisibilityAudit(session, {i: f"slot.{i}" for i in brief["observers"]}, faction_id=brief["evaluated_side"])
        red = observe(session, brief["observers"])
        failure = validate_emergency.audit_observations(red, auditor=auditor)
        checked += len(red)
        for tick in range(brief["adjudication_tick"]):
            if failure:
                break
            blue = observe(session, opponent.entity_ids)
            for identifier, command in opponent.commands(tick, blue).items():
                receipt = submit_navigation(session, identifier=identifier, faction=opponent.plan["faction_id"],
                    tick=tick, payload=command["payload"], valid_until_tick=command["valid_until_tick"])
                actions.append({"faction": "blue", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
            if policy in {"follow", "cooperative"} and tick < brief["scoring_deadline_tick"] and tick % 4 == 0:
                for identifier, follower in followers.items():
                    if not red[identifier]["own_entities"]:
                        continue
                    receipt = submit_navigation(session, identifier=identifier, faction=brief["evaluated_side"],
                        tick=tick, payload=follower.command(red[identifier]),
                        valid_until_tick=min(tick+8, brief["scoring_deadline_tick"]))
                    actions.append({"faction": "red", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
            step_receipt = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            red = observe(session, brief["observers"])
            checked += len(red)
            failure = validate_emergency.audit_observations(red, auditor=auditor)
            frame = session.world_view.presentation_snapshot()
            mission = frame.mission_scoring_checkpoint
            terminal = mission["terminal_result"]
            scores, score_status = score_evidence(step_receipt)
            # Referee/blue evidence is never fed into ContactFollowPolicy.
            blue = observe(session, opponent.entity_ids)
            trace.append({"tick": session.world_view.tick,
                "red_own_states": {i: o["own_entities"] for i, o in red.items()},
                "referee_blue_states": {i: o["own_entities"] for i, o in blue.items()},
                "observed_contact_counts": {i: len(o["organic_contacts"]) for i, o in red.items()},
                "delivered_shared_contact_counts": {i: len(o["shared_contacts"]) for i,o in red.items()},
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
            raise AssertionError("tracking must not succeed or end after an early detection")
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard", "policy": policy,
            "seed": seed, "status": failure["status"] if failure else "candidate_validation_not_release",
            "competition_accepted": False, "failure": failure, "final_tick": session.world_view.tick,
            "scores": final["scores"], "terminal": final["terminal"], "trace": trace,
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash, "validator_sha256": sha(__file__),
            "policy_source_sha256": sha(tracking_policy.__file__), "scripted_policy_sha256": sha(opponent_path),
            "privacy_validator_sha256": sha(validate_emergency.__file__), "public_brief_sha256": sha(brief_path),
            "engine_contact_source_sha256": sha(ROOT / "openmdbench/world/factory_v2.py"),
            "observations_checked": checked, "submitted_actions": actions, "visibility_audit": auditor.summary()}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()


def save_result(result):
    directory = ROOT / "artifacts/competition_four_categories"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"trk-{result['scenario_id']}-{result['policy']}-{result['seed']}-{stamp}.json"
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=range(1, 9))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--policy", choices=["idle", "follow", "cooperative"], default="follow")
    args = parser.parse_args()
    if args.all == (args.scenario is not None):
        parser.error("choose exactly one of --all or --scenario")
    failed = False
    for number in range(1, 9) if args.all else [args.scenario]:
        result = run(number, args.policy, args.seed)
        path = save_result(result)
        print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
        print(f"evidence={path.relative_to(ROOT)}", flush=True)
        failed = failed or bool(result["failure"])
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

"""Strict REC002..008 checks; a failed gate is not a completed experiment."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import time

from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.world.checkpoint_v2 import CheckpointErrorV2
from .build import PACKAGES, ROOT
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit
from .recon_metrics_v1 import plain
from . import recon_policy, denial_policy, tracking_policy, validate_denial, validate_emergency, validate_tracking


def submit_report(session, identifier, faction, tick, payload):
    key = f"report-{identifier}-{tick}"
    item = DiscreteActionV2(schema_version="2.0", entity_id=identifier, faction_id=faction,
        based_on_tick=tick, valid_until_tick=tick+1, action_id=key, action_type="send_message", payload=payload)
    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id, batch_id=key, idempotency_key=key,
        faction_id=faction, based_on_tick=tick, valid_until_tick=tick+1, discrete_actions=(item,))
    return session.submit_actions(batch=batch, authority_token=validate_denial.authority(session, identifier),
        operation_id=f"submit-{key}", expected_tick=tick)


def referee_checkpoint_evidence(session):
    # The display snapshot deliberately omits plugin states. Use the existing
    # checkpoint API, preserving its known failures instead of inventing data.
    try:
        checkpoint = session.world_view.checkpoint()
    except CheckpointErrorV2 as error:
        # Preserve the native rejection and its underlying reason. A terminal
        # receipt failure is not the same problem as a missing plugin sample.
        causes, seen = [], {id(error)}
        cause = error.__cause__ or error.__context__
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            causes.append({"type": type(cause).__name__, "error": str(cause)})
            cause = cause.__cause__ or cause.__context__
        return {"status": "FAILED_CHECKPOINT_GATE", "error": str(error),
                "causes": causes}, None
    return {"status": "available_not_full_restore_equivalence", "world_checkpoint_hash": checkpoint.checkpoint_hash}, plain(checkpoint.mission_scoring_checkpoint["plugin_states"])


def run(number, policy, seed):
    path = PACKAGES / f"md_rec_{number:03d}_standard"
    brief_path, plan_path = path / "public_brief.json", path / "scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = denial_policy.WaveNavigationPolicy(json.loads(plan_path.read_text(encoding="utf-8")))
    policies = {a["entity_id"]: recon_policy.SearchPolicy(brief, a["entity_id"], policy) for a in brief["own_assets"]}
    slots = {i: f"slot.{i}" for i in policies}
    session = create_candidate(path, seed=seed, session_id=f"candidate-rec{number}-{policy}-{seed}")
    trace, actions, checked = [], [], 0
    began = time.monotonic()
    try:
        auditor = VisibilityAudit(session, slots, faction_id=brief["evaluated_side"])
        red = validate_denial.observe_slots(session, slots)
        failure = validate_emergency.audit_observations(red, auditor=auditor)
        checked += len(red)
        for tick in range(brief["adjudication_tick"]):
            if failure:
                break
            released = {i: opponent.plan["controller_slots"][i] for i in opponent.active_ids(tick)}
            blue = validate_denial.observe_slots(session, released)
            for identifier, command in opponent.commands(tick, blue).items():
                receipt = validate_denial.submit_navigation(session, identifier, "blue", tick, command)
                actions.append({"kind": "blue_navigation", "entity_id": identifier, "tick": tick, "status": str(receipt.status)})
            for identifier, controller in policies.items():
                command = controller.navigation(red[identifier])
                if command is not None:
                    receipt = validate_denial.submit_navigation(session, identifier, "red", tick, command)
                    actions.append({"kind": "search_navigation", "entity_id": identifier, "tick": tick, "status": str(receipt.status)})
                report = controller.report(red[identifier])
                if report is not None:
                    receipt = submit_report(session, identifier, "red", tick, report)
                    actions.append({"kind": "contact_report", "entity_id": identifier, "tick": tick, "status": str(receipt.status)})
            step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            red = validate_denial.observe_slots(session, slots)
            checked += len(red)
            failure = validate_emergency.audit_observations(red, auditor=auditor)
            mission = session.world_view.presentation_snapshot().mission_scoring_checkpoint
            scores, score_status = validate_tracking.score_evidence(step)
            terminal = mission["terminal_result"]
            trace.append({"tick": session.world_view.tick, "own_states": {i: o["own_entities"] for i, o in red.items()},
                "receiver_inboxes": {i: o.get("received_messages", []) for i, o in red.items()},
                "action_receipts": [c.model_dump(mode="json") for c in step.child_receipts],
                "scores": scores, "score_data_status": score_status, "native_score_state": dict(mission["score_state"]),
                "terminal": dict(terminal) if terminal else None})
            if failure or terminal:
                break
        final = trace[-1] if trace else {"scores": {}, "terminal": None}
        if not failure and not final["terminal"]:
            raise AssertionError("recon episode has no native terminal at the deadline")
        if final["terminal"] and session.world_view.tick != brief["adjudication_tick"]:
            raise AssertionError("recon episode ended before all observation windows")
        checkpoint_evidence, plugin_states = referee_checkpoint_evidence(session)
        if failure is None and checkpoint_evidence["status"] == "FAILED_CHECKPOINT_GATE":
            failure = checkpoint_evidence
        sha = validate_tracking.sha
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard", "policy": policy, "seed": seed,
            "status": failure["status"] if failure else "candidate_validation_not_release", "failure": failure,
            "competition_accepted": False, "final_tick": session.world_view.tick, "scores": final["scores"], "visibility_audit": auditor.summary(),
            "terminal": final["terminal"], "trace": trace,
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "referee_plugin_states": plugin_states, "native_checkpoint_evidence": checkpoint_evidence,
            "elapsed_wall_seconds": round(time.monotonic()-began, 3), "observations_checked": checked,
            "submitted_actions": actions, "resolved_hash": session.resolved.resolved_hash,
            "catalog_hash": session.resolved.catalog_hash, "model_registry_hash": session.resolved.model_registry_hash,
            "validator_sha256": sha(__file__), "policy_source_sha256": sha(recon_policy.__file__),
            "scripted_policy_sha256": sha(plan_path), "public_brief_sha256": sha(brief_path),
            "privacy_validator_sha256": sha(validate_emergency.__file__), "score_adapter_sha256": sha(validate_tracking.__file__),
            "navigation_validator_sha256": sha(tracking_policy.__file__), "wave_policy_source_sha256": sha(denial_policy.__file__),
            "action_adapter_sha256": sha(validate_denial.__file__),
            "engine_contact_source_sha256": sha(ROOT / "openmdbench/world/factory_v2.py"),
            "protected_input_integrity": verify_protected_inputs()}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()


def save_result(result):
    directory = ROOT / "artifacts/competition_four_categories"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"rec-{result['scenario_id']}-{result['policy']}-{result['seed']}-{stamp}.json"
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=range(2, 9))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--policy", choices=["idle", "sweep", "coordinated"], default="coordinated")
    args = parser.parse_args()
    if args.all == (args.scenario is not None):
        parser.error("choose exactly one of --all or --scenario")
    failed = False
    for number in range(2, 9) if args.all else [args.scenario]:
        result = run(number, args.policy, args.seed)
        path = save_result(result)
        print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
        print(f"evidence={path.relative_to(ROOT)}", flush=True)
        failed = failed or bool(result["failure"])
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

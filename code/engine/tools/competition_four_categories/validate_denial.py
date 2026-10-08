"""Strict native area-denial candidate validation, never a release approver."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import yaml

from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2, PersistentCommandV2
from openmdbench.world.checkpoint_v2 import CheckpointErrorV2
from .build import PACKAGES, ROOT
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit
from . import denial_harm_audit
from . import denial_policy, tracking_policy, validate_emergency, validate_tracking


def observe_slots(session, slots):
    return {identifier: session.world_view.controller_observation(controller_slot_id=slot).model_dump(mode="json")
            for identifier, slot in slots.items()}


def authority(session, identifier):
    direct = session.world_view.authority_tokens.get(f"authority.{identifier}")
    if direct is not None and direct.entity_ids == (identifier,):
        return direct.token
    grants = [g for g in session.world_view.authority_tokens.values()
              if identifier in g.entity_ids and len(g.entity_ids) == 1]
    if not grants or len({g.controller_id for g in grants}) != 1:
        raise ValueError(f"expected one native authority grant for {identifier}")
    return min(grants, key=lambda g: g.token).token


def submit_navigation(session, identifier, faction, tick, command):
    end = command["valid_until_tick"]
    item = PersistentCommandV2(schema_version="2.0", entity_id=identifier, faction_id=faction,
        based_on_tick=tick, valid_until_tick=end, command_id=f"nav-{identifier}-{tick}",
        command_type="navigation", payload=command["payload"])
    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id,
        batch_id=f"nav-{identifier}-{tick}", idempotency_key=f"nav-{identifier}-{tick}", faction_id=faction,
        based_on_tick=tick, valid_until_tick=end, persistent_commands=(item,))
    return session.submit_actions(batch=batch, authority_token=authority(session, identifier),
        operation_id=f"nav-submit-{identifier}-{tick}", expected_tick=tick)


def submit_fire(session, identifier, faction, tick, payload):
    item = DiscreteActionV2(schema_version="2.0", entity_id=identifier, faction_id=faction,
        based_on_tick=tick, valid_until_tick=tick+1, action_id=f"fire-{identifier}-{tick}",
        action_type="fire_weapon", payload=payload)
    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id,
        batch_id=f"fire-{identifier}-{tick}", idempotency_key=f"fire-{identifier}-{tick}", faction_id=faction,
        based_on_tick=tick, valid_until_tick=tick+1, discrete_actions=(item,))
    return session.submit_actions(batch=batch, authority_token=authority(session, identifier),
        operation_id=f"fire-submit-{identifier}-{tick}", expected_tick=tick)


def run(number, policy, seed):
    path = PACKAGES / f"md_ad_{number:03d}_standard"
    brief_path, plan_path = path / "public_brief.json", path / "scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = denial_policy.WaveNavigationPolicy(json.loads(plan_path.read_text(encoding="utf-8")))
    defenders = {i: denial_policy.ZoneGuardPolicy(brief, i, policy) for i in brief["defenders"]}
    harm = denial_harm_audit.ProtectedHarmAudit.from_package(
        yaml.safe_load((path / "scenario.yaml").read_text(encoding="utf-8")), brief["defenders"])
    session = create_candidate(path, seed=seed, session_id=f"candidate-ad{number}-{policy}-{seed}")
    red_slots = {i: f"slot.{i}" for i in defenders}
    trace, actions, checked, failure = [], [], 0, None
    damage_prefix, prefix_checkpoint_error = None, None
    began = time.monotonic()
    try:
        auditor = VisibilityAudit(session, red_slots, faction_id=brief["evaluated_side"])
        red = observe_slots(session, red_slots)
        failure = validate_emergency.audit_observations(red, auditor=auditor)
        checked += len(red)
        for tick in range(brief["adjudication_tick"]):
            if failure:
                break
            released_slots = {i: opponent.plan["controller_slots"][i] for i in opponent.active_ids(tick)}
            blue = observe_slots(session, released_slots)
            for identifier, command in opponent.commands(tick, blue).items():
                receipt = submit_navigation(session, identifier, opponent.plan["faction_id"], tick, command)
                actions.append({"kind": "navigation", "entity_id": identifier, "tick": tick, "status": str(receipt.status)})
            if tick < brief["scoring_deadline_tick"]:
                for identifier, defender in defenders.items():
                    payload = defender.action(red[identifier])
                    if payload is not None:
                        receipt = submit_fire(session, identifier, brief["evaluated_side"], tick, payload)
                        actions.append({"kind": "fire_weapon", "entity_id": identifier, "tick": tick, "status": str(receipt.status)})
            step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            damage_evidence = [r.model_dump(mode="json") for r in step.world_receipt.damage_receipts]
            red = observe_slots(session, red_slots)
            checked += len(red)
            failure = validate_emergency.audit_observations(red, auditor=auditor)
            frame = session.world_view.presentation_snapshot()
            mission = frame.mission_scoring_checkpoint
            scores, score_status = validate_tracking.score_evidence(step)
            terminal = mission["terminal_result"]
            if session.world_view.tick == brief["scoring_deadline_tick"] and not terminal:
                try:
                    prefix = session.world_view.checkpoint()
                    damage_prefix = (prefix.tick, prefix.model_dump(mode="json")["combat_ledger"])
                except CheckpointErrorV2 as error:
                    prefix_checkpoint_error = str(error)
            # Referee evidence is recorded after policy execution, never passed to it.
            all_slots = {i: opponent.plan["controller_slots"][i] for i in opponent.active_ids(session.world_view.tick)}
            blue_states = observe_slots(session, all_slots)
            trace.append({"tick": session.world_view.tick,
                "own_states": {i: o["own_entities"] for i, o in red.items()},
                "referee_blue_states": {i: o["own_entities"] for i, o in blue_states.items()},
                "action_receipts": [c.model_dump(mode="json") for c in step.child_receipts],
                "referee_damage_receipts": damage_evidence,
                "referee_event_evidence": {"active_jamming_sessions": sorted(frame.event_state.jamming_sessions),
                    "zone_activation": dict(frame.zone_activation_state)},
                "scores": scores, "score_data_status": score_status,
                "native_score_state": dict(mission["score_state"]),
                "terminal": dict(terminal) if terminal else None})
            if failure or terminal:
                break
        final = trace[-1] if trace else {"scores": {}, "terminal": None}
        if not failure and not final["terminal"]:
            raise AssertionError("native denial episode did not terminate at the horizon")
        if final["terminal"] and session.world_view.tick != brief["adjudication_tick"]:
            raise AssertionError("area denial ended before the complete protection deadline")
        sha = validate_tracking.sha
        # Referee-only end-of-run read. The step receipt excludes damage applied
        # inside immediate weapon execution; the native checkpoint retains it.
        damage_ledger, damage_tail = [], None
        checkpoint_gate = {"status": "not_checked", "restoration_equivalence_proven": False}
        try:
            try:
                final_checkpoint = session.world_view.checkpoint()
            except CheckpointErrorV2 as error:
                checkpoint_gate.update(status="FAILED", error=str(error),
                    cause=str(error.__cause__) if error.__cause__ else None)
                if damage_prefix is None:
                    raise ValueError(f"no valid damage checkpoint prefix: {prefix_checkpoint_error}") from error
                prefix_tick, damage_ledger = damage_prefix
                if session.world_view.tick != prefix_tick + 1 or step.world_receipt.start_tick != prefix_tick:
                    raise ValueError("damage evidence tail is not exactly one contiguous step") from error
                harm.consume_checkpoint_ledger(damage_ledger, prefix_tick)
                harm.consume_verified_noncombat_tail(prefix_tick, step.world_receipt.damage_receipts,
                    step.world_receipt.combat_receipts)
                damage_tail = {"start_tick": prefix_tick, "end_tick": session.world_view.tick,
                    "damage_receipts": trace[-1]["referee_damage_receipts"],
                    "combat_receipts": step.model_dump(mode="json")["world_receipt"]["combat_receipts"]}
            else:
                checkpoint_gate["status"] = "read_passed_not_restore_acceptance"
                damage_ledger = final_checkpoint.model_dump(mode="json")["combat_ledger"]
                harm.consume_checkpoint_ledger(damage_ledger, session.world_view.tick)
            harm_result = {**harm.summary(), "complete_through_final_tick": harm.next_tick == session.world_view.tick}
        except (ValueError, KeyError, TypeError) as error:
            # Preserve native episode evidence; unavailable attribution is never zero.
            harm_result = {"contract": denial_harm_audit.CONTRACT, "data_status": "UNAVAILABLE",
                "failure": str(error), "complete_through_final_tick": False,
                "defender_weapon_harm_rate": None, "defender_weapon_hull_health_loss": None}
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard", "policy": policy, "seed": seed,
            "status": failure["status"] if failure else "candidate_validation_not_release",
            "competition_accepted": False, "failure": failure, "final_tick": session.world_view.tick,
            "protected_harm_audit": harm_result,
            "referee_damage_transaction_ledger": damage_ledger,
            "referee_damage_verified_tail": damage_tail,
            "native_terminal_checkpoint_gate": checkpoint_gate,
            "harm_audit_source_sha256": sha(denial_harm_audit.__file__),
            "protected_input_integrity": verify_protected_inputs(),
            "scores": final["scores"], "terminal": final["terminal"], "trace": trace,
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash, "validator_sha256": sha(__file__),
            "policy_source_sha256": sha(denial_policy.__file__), "scripted_policy_sha256": sha(plan_path),
            "privacy_validator_sha256": sha(validate_emergency.__file__),
            "navigation_validator_sha256": sha(tracking_policy.__file__),
            "score_adapter_sha256": sha(validate_tracking.__file__),
            "public_brief_sha256": sha(brief_path), "engine_contact_source_sha256": sha(ROOT / "openmdbench/world/factory_v2.py"),
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
    target = directory / f"ad-{result['scenario_id']}-{result['policy']}-{result['seed']}-{stamp}.json"
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=range(1, 7))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--policy", choices=["idle", "guard", "indiscriminate"], default="guard")
    args = parser.parse_args()
    if args.all == (args.scenario is not None):
        parser.error("choose exactly one of --all or --scenario")
    failed = False
    for number in range(1, 7) if args.all else [args.scenario]:
        result = run(number, args.policy, args.seed)
        path = save_result(result)
        print(json.dumps({k: result[k] for k in ("scenario_id", "seed", "policy", "status", "final_tick", "scores")}), flush=True)
        print(f"evidence={path.relative_to(ROOT)}", flush=True)
        failed = failed or bool(result["failure"])
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

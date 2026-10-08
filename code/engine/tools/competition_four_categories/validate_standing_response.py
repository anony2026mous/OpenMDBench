"""Independent standing-watch response trials; all native gates remain enforced."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import time

from .build import ROOT, PACKAGES
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit
from .delivered_dispatch_v1 import PROTOCOL
from . import message_policy, response_policy, validate_denial, validate_emergency, validate_tracking, validate_recon
from . import standing_response_policy, validate_response as response_adapter
from . import progress_response_policy


def plan_hash(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


submit_source_messages = response_adapter.submit_source_messages


def run(number, policy, seed):
    if policy not in {"watch-coordinated", "progress-watch"}:
        raise ValueError("standing response requires its declared mode")
    path = PACKAGES / f"md_er_{number:03d}_standard"
    brief_path, source_path = path / "public_brief.json", path / "scripted_message_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    if brief.get("response_protocol") != PROTOCOL:
        raise ValueError("this response validator requires the delivered-notice candidate protocol")
    nominal = json.loads(source_path.read_text(encoding="utf-8"))
    realized = message_policy.sample_schedule(nominal, seed=seed, maximum_shift_ticks=brief["notice_timing_variation_ticks"])
    if any(row["send_tick"] >= brief["scoring_deadline_tick"] for row in realized["messages"]):
        raise ValueError("source message schedule extends beyond the response deadline")
    source = message_policy.ScheduledMessagePolicy(realized)
    controller = progress_response_policy.ProgressResponsePolicy if policy == "progress-watch" else standing_response_policy.StandingResponsePolicy
    responders = {i: controller(brief, i, policy) for i in brief["responders"]}
    slots = {i: f"slot.{i}" for i in responders}
    if set(slots) & set(realized["controller_slots"]):
        raise ValueError("environment message actors cannot also be participating responders")
    session = create_candidate(path, seed=seed, session_id=f"candidate-response{number}-{policy}-{seed}")
    trace, actions, source_submissions = [], [], []
    checked, began = 0, time.monotonic()
    try:
        auditor = VisibilityAudit(session, slots, faction_id=brief["evaluated_side"])
        observations = validate_denial.observe_slots(session, slots)
        failure = validate_emergency.audit_observations(observations, auditor=auditor)
        checked += len(observations)
        for tick in range(brief["adjudication_tick"]):
            if failure: break
            source_observations = validate_denial.observe_slots(session, realized["controller_slots"])
            due = source.actions(tick, source_observations)
            source_submissions.extend(response_adapter.submit_source_messages(session, actions=due, faction=realized["faction_id"], tick=tick))
            for identifier, controller in responders.items():
                payload = controller.command(observations[identifier])
                if payload is not None:
                    command = {"payload": payload, "valid_until_tick": min(tick+4, brief["scoring_deadline_tick"])}
                    receipt = validate_denial.submit_navigation(session, identifier, brief["evaluated_side"], tick, command)
                    actions.append({"entity_id": identifier, "tick": tick, "payload": payload, "status": str(receipt.status)})
            step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            observations = validate_denial.observe_slots(session, slots)
            checked += len(observations)
            failure = validate_emergency.audit_observations(observations, auditor=auditor)
            scores, score_status = validate_tracking.score_evidence(step)
            mission = session.world_view.presentation_snapshot().mission_scoring_checkpoint
            terminal = mission["terminal_result"]
            trace.append({"tick": session.world_view.tick,
                "controller_observations": observations,
                "controller_phases": {i: p.phase for i, p in responders.items()},
                "controller_motion_gain": {i: {"estimate": p.motion_gain, "samples": p.gain_samples}
                    if hasattr(p, "motion_gain") else None for i, p in responders.items()},
                "own_states": {i: o["own_entities"] for i, o in observations.items()},
                "receiver_inboxes": {i: o["received_messages"] for i, o in observations.items()},
                "action_receipts": [r.model_dump(mode="json") for r in step.child_receipts],
                "scores": scores, "score_data_status": score_status, "native_score_state": dict(mission["score_state"]),
                "terminal": dict(terminal) if terminal else None})
            if failure or terminal: break
        final = trace[-1] if trace else {"scores": {}, "terminal": None}
        if failure is None and final["terminal"] is None:
            raise AssertionError("response episode has no native terminal by its deadline")
        if session.world_view.tick > brief["adjudication_tick"]:
            raise AssertionError("response episode exceeded its declared clock")
        checkpoint_evidence, plugin_states = validate_recon.referee_checkpoint_evidence(session)
        if failure is None and checkpoint_evidence["status"] == "FAILED_CHECKPOINT_GATE":
            failure = checkpoint_evidence
        sha = validate_tracking.sha
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard", "response_protocol": PROTOCOL,
            "policy": policy, "seed": seed, "status": failure["status"] if failure else "candidate_validation_not_release",
            "failure": failure, "competition_accepted": False, "full_episode_completed": final["terminal"] is not None,
            "final_tick": session.world_view.tick, "scores": final["scores"], "terminal": final["terminal"], "visibility_audit": auditor.summary(),
            "trace": trace, "trace_sha256": plan_hash(trace), "source_submissions": source_submissions,
            "submitted_actions": actions, "observations_checked": checked, "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash, "validator_sha256": sha(__file__),
            "public_brief_sha256": sha(brief_path), "source_plan_sha256": sha(source_path),
            "source_realization": realized, "source_realization_sha256": plan_hash(realized),
            "source_policy_sha256": sha(message_policy.__file__),
            "policy_source_sha256": sha(progress_response_policy.__file__ if policy == "progress-watch" else standing_response_policy.__file__),
            "standing_policy_source_sha256": sha(standing_response_policy.__file__),
            "response_base_policy_sha256": sha(response_policy.__file__),
            "response_message_adapter_sha256": sha(response_adapter.__file__),
            "controller_settings": dict(standing_response_policy.SETTINGS),
            "progress_controller_settings": dict(progress_response_policy.SETTINGS) if policy == "progress-watch" else None,
            "privacy_validator_sha256": sha(validate_emergency.__file__), "action_adapter_sha256": sha(validate_denial.__file__),
            "score_adapter_sha256": sha(validate_tracking.__file__), "checkpoint_adapter_sha256": sha(validate_recon.__file__),
            "engine_contact_source_sha256": sha(ROOT / "openmdbench/world/factory_v2.py"),
            "native_checkpoint_evidence": checkpoint_evidence, "referee_plugin_states": plugin_states,
            "protected_input_integrity": verify_protected_inputs()}
    finally:
        if session.state.value == "running": session.stop()
        session.close()
        verify_protected_inputs()


def save_result(result):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = ROOT / "artifacts/competition_four_categories" / f"er-{result['scenario_id']}-{result['policy']}-{result['seed']}-{stamp}.json"
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=(3, 5, 6), required=True)
    parser.add_argument("--policy", choices=("watch-coordinated", "progress-watch"), default="watch-coordinated")
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args()
    result = run(args.scenario, args.policy, args.seed)
    path = save_result(result)
    print(json.dumps({k: result[k] for k in ("scenario_id", "policy", "seed", "status", "final_tick", "scores", "terminal")}), flush=True)
    print(f"evidence={path.relative_to(ROOT)}", flush=True)
    if result["failure"]: raise SystemExit(2)


if __name__ == "__main__": main()

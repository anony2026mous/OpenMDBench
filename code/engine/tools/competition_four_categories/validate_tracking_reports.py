"""Native tracking report trials with source-bound public-DTO agents."""
from __future__ import annotations

import argparse
import hashlib
import json
import time

from . import allocated_tracking_policy, track_report_metrics_v1, track_reporting_policy
from . import tracking_policy, validate_emergency, validate_response
from . import native_localization_audit
from . import validate_tracking as adapter
from .build import ROOT, PACKAGES
from .protected_inputs import verify as verify_protected_inputs
from .runtime import create_candidate
from .visibility_audit import VisibilityAudit, plain

MODES = ("honest", "silent", "swapped")


def source_fingerprints():
    return {"validator_sha256": adapter.sha(__file__),
        "report_policy_sha256": adapter.sha(track_reporting_policy.__file__),
        "navigation_policy_sha256": adapter.sha(allocated_tracking_policy.__file__),
        "report_metric_source_sha256": adapter.sha(track_report_metrics_v1.__file__),
        "localization_audit_source_sha256": adapter.sha(native_localization_audit.__file__),
        "message_adapter_sha256": adapter.sha(validate_response.__file__),
        "action_adapter_sha256": adapter.sha(adapter.__file__)}


def _reports(frame):
    rows = []
    for record in frame.event_state.message_queue:
        try:
            body = json.loads(record.get("payload", ""))
        except (ValueError, TypeError):
            continue
        if isinstance(body, dict) and body.get("schema_version") == track_report_metrics_v1.PROTOCOL:
            rows.append(plain(record))
    return rows


def execute(session, brief, opponent, mode, *, agents=None, support_agents=None):
    if mode not in MODES:
        raise ValueError("unknown report trial mode")
    if agents is None:
        agents = {i: track_reporting_policy.TrackReportingPolicy(brief, i, mode)
                  for i in brief["track_reporting"]["reporter_ids"]}
    if (set(agents) != set(brief["track_reporting"]["reporter_ids"])
            or any(getattr(agent, "identifier", None) != identifier for identifier, agent in agents.items())):
        raise ValueError("trial agents must match their declared controller endpoints")
    support_agents = {} if support_agents is None else support_agents
    allowed_support = set(brief["observers"])-set(brief["track_reporting"]["reporter_ids"])
    if (not set(support_agents) <= allowed_support
            or any(getattr(agent, "identifier", None) != identifier
                   or brief["observer_domains"].get(identifier) != "shore"
                   for identifier, agent in support_agents.items())):
        raise ValueError("support agents must be declared stationary observer endpoints")
    controllers = {**agents, **support_agents}
    localization = native_localization_audit.NativeContactLocalizationAudit(brief["observers"], opponent.entity_ids)
    localization_failure = None
    auditor = VisibilityAudit(session, {i: f"slot.{i}" for i in brief["observers"]}, faction_id=brief["evaluated_side"])
    trace, actions, message_submissions = [], [], []
    began = time.monotonic()
    red = adapter.observe(session, brief["observers"])
    failure = validate_emergency.audit_observations(red, auditor=auditor)
    interval = brief["track_reporting"]["suggested_interval_ticks"]
    for tick in range(brief["adjudication_tick"]):
        if failure:
            break
        blue = adapter.observe(session, opponent.entity_ids)
        for identifier, command in opponent.commands(tick, blue).items():
            receipt = adapter.submit_navigation(session, identifier=identifier, faction=opponent.plan["faction_id"],
                tick=tick, payload=command["payload"], valid_until_tick=command["valid_until_tick"])
            actions.append({"faction": "blue", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
        if tick < brief["scoring_deadline_tick"] and tick % interval == 0:
            outgoing = []
            for identifier, agent in controllers.items():
                decision = agent.decide(red[identifier])
                if identifier in support_agents and decision["navigation"] is not None:
                    raise ValueError("stationary support agent cannot issue navigation")
                if decision["navigation"] is not None:
                    receipt = adapter.submit_navigation(session, identifier=identifier, faction=brief["evaluated_side"],
                        tick=tick, payload=decision["navigation"], valid_until_tick=min(tick+8, brief["scoring_deadline_tick"]))
                    actions.append({"faction": "red", "tick": tick, "entity_id": identifier, "status": str(receipt.status)})
                if any(row.get("sender_id") != identifier for row in decision["messages"]):
                    raise ValueError("agent attempted to send as another endpoint")
                outgoing.extend(decision["messages"])
            message_submissions.extend(validate_response.submit_source_messages(
                session, actions=outgoing, faction=brief["evaluated_side"], tick=tick))
        step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
        red = adapter.observe(session, brief["observers"])
        failure = validate_emergency.audit_observations(red, auditor=auditor)
        frame = session.world_view.presentation_snapshot()
        if failure is None and localization_failure is None:
            try:
                localization.capture(step.world_receipt, frame, red)
            except (ValueError, KeyError, TypeError) as error:
                localization_failure = {"status": "FAILED_NATIVE_LOCALIZATION_EVIDENCE",
                    "world_tick": session.world_view.tick, "error": str(error)}
        terminal = frame.mission_scoring_checkpoint["terminal_result"]
        scores, availability = adapter.score_evidence(step)
        reports = _reports(frame)
        trace.append({"tick": session.world_view.tick,
            "red_own_states": {i: o["own_entities"] for i, o in red.items()},
            "referee_blue_states": {i: o["own_entities"] for i, o in adapter.observe(session, opponent.entity_ids).items()},
            "observed_contact_counts": {i: len(o["organic_contacts"]) for i, o in red.items()},
            "report_transport_counts": {status: sum(r.get("transport_status") == status for r in reports)
                                        for status in ("queued", "delivered", "blocked", "expired", "dropped")},
            "scores": scores, "score_data_status": availability,
            "terminal": dict(terminal) if terminal else None})
        if terminal or failure:
            break
    final = trace[-1] if trace else {"scores": {}, "terminal": None}
    if not failure and (not final["terminal"] or session.world_view.tick != brief["adjudication_tick"]):
        raise AssertionError("tracking report trial must reach its native adjudication tick")
    if localization_failure:
        localization_result = {"contract": native_localization_audit.CONTRACT, "status": "UNAVAILABLE",
            "failure": localization_failure, "complete_through_final_tick": False,
            "native_measurement_rmse_3d_m": None, "agent_reported_trajectory_rmse_m": None}
    else:
        localization_result = {**localization.summary(),
            "complete_through_final_tick": localization.next_tick == session.world_view.tick and failure is None}
    return {"scenario_id": brief["scenario_id"], "difficulty": brief["difficulty"],
        "policy": f"report-{mode}", "status": failure["status"] if failure else "candidate_validation_not_release",
        "competition_accepted": False, "failure": failure, "final_tick": session.world_view.tick,
        "scores": final["scores"], "terminal": final["terminal"], "trace": trace,
        "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
        "elapsed_wall_seconds": round(time.monotonic()-began, 3),
        "submitted_actions": actions, "message_submissions": message_submissions,
        "report_delivery_evidence": _reports(session.world_view.presentation_snapshot()),
        "native_localization_audit": localization_result,
        "native_localization_evidence": localization.evidence(),
        "localization_audit_source_sha256": adapter.sha(native_localization_audit.__file__),
        "visibility_audit": auditor.summary(), "observations_checked": auditor.checked_observations}


def run(number, mode, seed):
    if number not in (7, 8):
        raise ValueError("report trial requires TRK007 or TRK008")
    verify_protected_inputs()
    path = PACKAGES/f"md_trk_{number:03d}_standard"
    brief_path, plan_path = path/"public_brief.json", path/"scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = tracking_policy.ScheduledNavigationPolicy(json.loads(plan_path.read_text(encoding="utf-8")))
    fingerprints = source_fingerprints()
    session = create_candidate(path, seed=seed, session_id=f"candidate-trk{number}-report-{mode}-{seed}")
    try:
        result = execute(session, brief, opponent, mode)
        if fingerprints != source_fingerprints():
            raise AssertionError("report trial sources changed during execution")
        return {**result, "seed": seed, **fingerprints,
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash,
            "policy_source_sha256": adapter.sha(tracking_policy.__file__), "scripted_policy_sha256": adapter.sha(plan_path),
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

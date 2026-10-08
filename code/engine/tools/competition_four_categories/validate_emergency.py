"""Native ER candidate episodes. No referee data enters the baseline policy."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from .build import PACKAGES, ROOT
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit, audit_observations as evidence_audit


def center(zone):
    vertices = zone["coordinates_m"]
    return [sum(v[i] for v in vertices) / len(vertices) for i in range(2)]


class DispatchPolicy:
    """Reference navigation only; receives the public brief and own-side DTOs."""

    def __init__(self, brief, policy):
        self.brief, self.policy = brief, policy
        self.requests = {r["request_id"]: r for r in brief["initial_requests"]}
        self.routes = {}
        self.seen_messages = set()

    def commands(self, observations):
        if self.policy == "idle":
            return {}
        for obs in observations.values():
            for record in obs["received_messages"]:
                key = record.get("message_id", json.dumps(record, sort_keys=True))
                if key in self.seen_messages:
                    continue
                self.seen_messages.add(key)
                body = record.get("payload")
                if not isinstance(body, str):
                    continue
                try:
                    alert = json.loads(body)
                except (ValueError, TypeError):
                    continue
                if not isinstance(alert, dict) or "request_id" not in alert:
                    continue
                if alert.get("status") == "cancelled":
                    self.requests.pop(alert["request_id"], None)
                    self.routes.clear()
                elif alert.get("status") == "confirmed" and "destination" in alert:
                    self.requests[alert["request_id"]] = alert
        requests = sorted(self.requests.values(), key=lambda r: (-r["priority"], r["request_id"]))
        commands = {}
        for index, (identifier, obs) in enumerate(sorted(observations.items())):
            if not requests or (index > 0 and self.policy != "team"):
                continue
            own = obs["own_entities"][0]
            position = own["position_m"]
            request = requests[min(index, len(requests)-1)]
            key = (identifier, request["request_id"])
            if key not in self.routes:
                tx, ty = center(request["destination"])
                route = []
                if self.policy in {"safe", "team"} and self.brief["risk_regions"]:
                    # A deliberately simple public-map detour, not an oracle of
                    # hazard onset, target position or hidden event contents.
                    floor = min(v[1] for z in self.brief["risk_regions"] for v in z["coordinates_m"]) - 160.
                    route.extend([(position[0], floor), (tx, floor)])
                route.append((tx, ty))
                self.routes[key] = route
            route = self.routes[key]
            tx, ty = route[0]
            distance = math.hypot(tx-position[0], ty-position[1])
            if distance < 45 and len(route) > 1:
                route.pop(0)
                tx, ty = route[0]
                distance = math.hypot(tx-position[0], ty-position[1])
            commands[identifier] = {"speed_mps": 0. if distance < 35 else min(22., max(3., distance/3)),
                                    "heading_deg": math.degrees(math.atan2(tx-position[0], ty-position[1])) % 360,
                                    "altitude_m": 100.}
        return commands


def audit_observations(observations, *, auditor=None):
    return evidence_audit(observations, auditor=auditor)


def run(number, policy, seed):
    path = PACKAGES / f"md_er_{number:03d}_standard"
    brief_path = path / "public_brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    if brief.get("response_protocol") == "dispatch-task@1.0":
        from .validate_response import run as run_delivered_response
        aliases = {"idle": "idle", "direct": "naive", "safe": "coordinated", "team": "coordinated"}
        if policy not in aliases:
            raise ValueError("use validate_response for delivered-response policy names")
        result = run_delivered_response(number, aliases[policy], seed)
        result["requested_policy_alias"] = policy
        return result
    baseline = DispatchPolicy(brief, policy)
    session = create_candidate(path, seed=seed, session_id=f"candidate-er{number}-{policy}-{seed}")
    trace, action_statuses, checked, failure = [], [], 0, None
    submitted_command_ticks = []
    began = time.monotonic()
    # Referee expectations are ONLY used to reject invalid episodes; never passed
    # to DispatchPolicy. Native messages must reach the actual controller DTO.
    message_events = [e for e in session.resolved.events if e.event_type == "message"]
    observed_bodies = set()
    def observations():
        return {identifier: session.world_view.controller_observation(
                    controller_slot_id=f"slot.{identifier}").model_dump(mode="json")
                for identifier in brief["responders"]}
    try:
        auditor = VisibilityAudit(session, {i: f"slot.{i}" for i in brief["responders"]}, faction_id=brief["evaluated_side"])
        obs = observations()
        failure = audit_observations(obs, auditor=auditor)
        checked += len(obs)
        for tick in range(brief["adjudication_tick"]):
            if failure:
                break
            should_submit = tick == 0 if policy == "preissued" else tick % 4 == 0
            if tick < brief["scoring_deadline_tick"] and should_submit:
                for identifier, payload in baseline.commands(obs).items():
                    command = PersistentCommandV2(schema_version="2.0", entity_id=identifier, faction_id="red",
                        based_on_tick=tick, valid_until_tick=brief["scoring_deadline_tick"] if policy == "preissued"
                            else min(tick+8, brief["scoring_deadline_tick"]),
                        command_id=f"nav-{identifier}-{tick}", command_type="navigation", payload=payload)
                    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id,
                        batch_id=f"batch-{identifier}-{tick}", idempotency_key=f"batch-{identifier}-{tick}",
                        faction_id="red", based_on_tick=tick, valid_until_tick=command.valid_until_tick,
                        persistent_commands=(command,))
                    receipt = session.submit_actions(batch=batch, authority_token=f"authority.{identifier}",
                        operation_id=f"submit-{identifier}-{tick}", expected_tick=tick)
                    action_statuses.append(str(receipt.status))
                    submitted_command_ticks.append(tick)
            session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            obs = observations()
            checked += len(obs)
            failure = audit_observations(obs, auditor=auditor)
            for observation in obs.values():
                for record in observation["received_messages"]:
                    body = record.get("payload")
                    if isinstance(body, str):
                        observed_bodies.add(body)
            frame = session.world_view.presentation_snapshot()
            mission = frame.mission_scoring_checkpoint
            event_state = frame.event_state
            terminal = mission["terminal_result"]
            trace.append({"tick": session.world_view.tick,
                "positions": {i: o["own_entities"][0]["position_m"] for i, o in obs.items()},
                "own_states": {i: o["own_entities"][0] for i, o in obs.items()},
                "messages": {i: o["received_messages"] for i, o in obs.items()},
                "referee_event_evidence": {"weather_event_id": event_state.weather_state.get("event_id"),
                    "active_jamming_sessions": sorted(event_state.jamming_sessions),
                    "component_suppression_keys": sorted(event_state.component_suppressions),
                    "message_queue": [{"message_id": m.get("message_id"),
                        "event_id": m.get("event_id"), "transport_status": m.get("transport_status"),
                        "delivered_tick": m.get("delivered_tick"), "expiry_tick": m.get("expiry_tick")}
                        for m in event_state.message_queue]},
                "scores": dict(mission["score_state"]), "terminal": dict(terminal) if terminal else None})
            for event in message_events:
                if session.world_view.tick >= event.trigger.tick + 2 and event.payload["body"] not in observed_bodies:
                    failure = failure or {"status": "FAILED_MESSAGE_VISIBILITY_GATE",
                        "event_id": event.id, "event_tick": event.trigger.tick,
                        "detail": "Declared recipient message absent from actual controller DTO two ticks after release"}
            if terminal or failure:
                break
        final = trace[-1] if trace else {"scores": {}, "terminal": None}
        if failure is None and final["terminal"] is None:
            raise AssertionError("native episode did not terminate")
        return {"scenario_id": brief["scenario_id"], "difficulty": "standard",
            "policy": policy, "seed": seed, "status": failure["status"] if failure else "candidate_validation_not_release",
            "competition_accepted": False, "failure": failure,
            "final_tick": session.world_view.tick, "scores": final["scores"], "terminal": final["terminal"],
            "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "trace": trace, "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash,
            "validator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "public_brief_sha256": hashlib.sha256(brief_path.read_bytes()).hexdigest(),
            "engine_contact_source_sha256": hashlib.sha256((ROOT / "openmdbench/world/factory_v2.py").read_bytes()).hexdigest(),
            "observations_checked": checked, "visibility_audit": auditor.summary(), "action_statuses": sorted(set(action_statuses)),
            "submitted_command_ticks": submitted_command_ticks}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()


def save_result(result):
    directory = ROOT / "artifacts/competition_four_categories"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"er-{result['scenario_id']}-{result['policy']}-{result['seed']}-{stamp}.json"
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=range(1, 7), required=True)
    parser.add_argument("--policy", choices=["idle", "direct", "safe", "team", "preissued"], default="safe")
    parser.add_argument("--seed", type=int, default=601)
    args = parser.parse_args()
    result = run(args.scenario, args.policy, args.seed)
    target = save_result(result)
    print(json.dumps({k: result[k] for k in ("scenario_id", "policy", "seed", "status", "final_tick", "scores", "terminal")}), flush=True)
    print(f"evidence={target.relative_to(ROOT)}", flush=True)
    if result["failure"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

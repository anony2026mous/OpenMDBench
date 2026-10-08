"""Delivered-notice ER003/005/006 candidates using existing native actions."""
from copy import deepcopy
import json

from .build import selector, zone
from .emergency import emergency, alert, event
from .delivered_dispatch_v1 import MODEL_REF, PROTOCOL, contract_hash
from .message_policy import ScheduledMessagePolicy


def response(number):
    if number not in (3, 5, 6):
        raise ValueError("delivered-response expansion covers ER003, ER005 and ER006")
    package, brief, acceptance = emergency(number)
    s = package["scenario"]
    original = deepcopy(s["scoring"]["metrics"][0]["plugin_parameters"])
    if number == 6:
        # More time is required for a real blackout/re-notification and two
        # physical destinations. This is still an uncalibrated short candidate.
        brief.update(duration_seconds=240, scoring_deadline_tick=240, adjudication_tick=241,
                     fidelity="UNVALIDATED synthetic 240-second mixed-response candidate, not full rescue")
        s["world"]["duration_ticks"] = 241
        s["mission_rules"][1]["condition"]["parameters"]["tick"] = 241
        for r in original["requests"]:
            r["deadline_tick"] = 240
        for e in s["events"]:
            if e["id"] in {"event.deadline", "event.success", "event.timeout"}:
                e["trigger"]["tick"] = 241
            if e["id"] == "event.fault": e["payload"]["duration_ticks"] = 240
        for metric in s["scoring"]["metrics"]:
            metric["plugin_parameters"]["end_tick"] = 241
        advisory = zone("zone.request03", -1000., 600., 100.)
        s["world"]["zones"].append(advisory)
        s["events"].extend([alert("event.advisory", 8, advisory, status="unverified", priority=4),
            alert("event.withdrawal", 20, advisory, status="cancelled", priority=4),
            event("event.receiver-blackout", "component_suppression", 22,
                {"target_entity_id": "unit.r02", "component_ref": "communication.competition-dispatch@1.0.0", "duration_ticks": 18})])
    horizon = brief["scoring_deadline_tick"]
    events = sorted((e for e in s["events"] if e["event_type"] == "message"), key=lambda e: e["trigger"]["tick"])
    bodies = [json.loads(e["payload"]["body"]) for e in events]
    requests, task_bodies, cautions = [], {}, {}
    legacy = {r["zone_id"]: r for r in original["requests"]}
    destinations = {b["destination"]["id"]: b["destination"] for b in bodies}
    for index, zone_id in enumerate(sorted(destinations)):
        r = legacy.get(zone_id)
        relevant = [b for b in bodies if b["destination"]["id"] == zone_id]
        caution = []
        if any(b["status"] == "unverified" for b in relevant):
            # Published with the unverified alert, never leaked in the initial brief.
            caution = [zone(f"zone.approach.{index+1:02d}", -340., 30., 135.)]
            s["world"]["zones"].extend(caution)
        rid = f"task.{index+1:02d}"
        observers = list(r["observer_ids"] if r else brief["responders"])
        body = {"schema_version": PROTOCOL, "request_id": rid, "status": "confirmed",
            "destination": deepcopy(destinations[zone_id]), "caution_regions": caution,
            "observer_ids": observers, "deadline_tick": r["deadline_tick"] if r else horizon,
            "dwell_ticks": r["dwell_ticks"] if r else 3, "priority": max(b["priority"] for b in relevant)}
        task_bodies[zone_id] = body
        requests.append({"request_id": rid, "zone_id": zone_id, "deadline_tick": body["deadline_tick"],
            "weight": r["weight"] if r else 1., "dwell_ticks": body["dwell_ticks"],
            "observer_ids": observers, "initially_known": False, "required": r is not None,
            "contract_sha256": contract_hash(body), "caution_zone_ids": [z["id"] for z in caution]})
    initial = []
    for index, identifier in enumerate(brief["responders"]):
        point = zone(f"zone.duty.{index+1:02d}", -100., -100. if index == 0 else 300., 65.)
        s["world"]["zones"].append(point)
        body = {"schema_version": PROTOCOL, "request_id": f"duty.{index+1:02d}", "status": "confirmed",
            "destination": point, "caution_regions": [], "observer_ids": [identifier],
            "deadline_tick": 12, "dwell_ticks": 3, "priority": 1}
        initial.append(body)
        requests.append({"request_id": body["request_id"], "zone_id": point["id"], "deadline_tick": 12,
            "weight": .15, "dwell_ticks": 3, "observer_ids": [identifier], "initially_known": True,
            "required": True, "contract_sha256": contract_hash(body), "caution_zone_ids": []})
    source_ids = sorted({e["payload"]["sender_entity_id"] for e in events})
    entities = {e["id"]: e for e in s["entities"]}
    plan = {"schema_version": "scheduled-messages@1.0", "faction_id": "red",
        "controller_slots": {i: entities[i]["controller_slot"] for i in source_ids}, "messages": []}
    for index, (e, old_body) in enumerate(zip(events, bodies)):
        body = {**deepcopy(task_bodies[old_body["destination"]["id"]]), "status": old_body["status"]}
        plan["messages"].append({"message_id": f"notice.{index+1:03d}", "sender_id": e["payload"]["sender_entity_id"],
            "send_tick": e["trigger"]["tick"], "recipient_controller_slots": list(e["payload"]["recipient_controller_slots"]),
            "message": json.dumps(body, sort_keys=True)})
    latest = {}
    for item in plan["messages"]:
        latest[json.loads(item["message"])["request_id"]] = item
    for rid, item in sorted(latest.items()):
        plan["messages"].append({**deepcopy(item), "message_id": f"notice.{len(plan['messages'])+1:03d}", "send_tick": 45})
    ScheduledMessagePolicy(plan)
    s["events"] = [e for e in s["events"] if e["event_type"] != "message"]
    continuity = [m for m in s["scoring"]["metrics"] if m["id"] == "metric.continuity"]
    residual = 1-sum(m["weight"] for m in continuity)
    metrics = []
    for mid, kind, weight in [("metric.arrival", "arrival_fraction", .55),
                              ("metric.timeliness", "timeliness", .15),
                              ("metric.safety", "route_safety", .15),
                              ("metric.triage", "triage_discipline", .15)]:
        metrics.append({"id": mid, "selector": selector(brief["responders"]), "aggregation": "mean",
            "unit": "1", "direction": "maximize", "weight": residual*weight, "available": True,
            "value": 0., "required": True, "normalization": {"lower_bound": 0., "upper_bound": 1.},
            "plugin_ref": MODEL_REF, "plugin_parameters": {"metric_id": mid, "kind": kind,
                "requests": deepcopy(requests), "hazards": deepcopy(original["hazards"]), "source_ids": source_ids,
                "observer_slots": {i: f"slot.{i}" for i in brief["responders"]},
                "start_tick": 1, "end_tick": horizon+1, "unit": "1"}})
    s["scoring"]["metrics"] = metrics+continuity
    s["mission_rules"][0]["condition"]["parameters"]["conditions"].append(
        {"operator": "score", "parameters": {"metric_id": "metric.triage", "comparison": ">=", "value": 1.}})
    brief.update(response_protocol=PROTOCOL, validation_entrypoint="tools.competition_four_categories.validate_response",
        initial_requests=initial, trusted_dispatch_sources=source_ids, source_actor_control="environment_only",
        notice_timing_variation_ticks=3,
        task="Complete the public initial station duties. Dispatch only on authentic delivered confirmed tasks, dwell as specified, and avoid entering published caution regions for unverified or cancelled alerts. Arrival is not physical rescue.")
    if brief.get("standing_missions"):
        for standing in brief["standing_missions"]:
            standing["measurement_window"]["end_tick_exclusive"] = brief["adjudication_tick"]
        brief["task"] += " Maintain the published standing watch alongside the delivered incident tasks."
    acceptance["unmet_gates"] = [g for g in acceptance["unmet_gates"] if "native message events do not currently reach" not in g]
    acceptance["unmet_gates"].extend(["independent acceptance of native-action notice protocol",
        "full initial-mission and sustained-response contract beyond bounded station duties",
        "declarative SOS event delivery remains unsupported; this candidate uses documented native actions instead"])
    acceptance["scope"] = "delivered-notice navigation-dispatch candidate, not physical rescue"
    return package, brief, acceptance, plan

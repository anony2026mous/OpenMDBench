"""Six declarative emergency candidates; dispatch/arrival is not physical rescue.

These deliberately retain native message events even while the native inbox gate
is failing. A validator must not reveal their payloads via an alternate channel.
One standard difficulty first: multiplying unvalidated incidents is not evidence
of meaningful easy/medium/hard versions. All values are synthetic/unvalidated.
"""
from copy import deepcopy
import json

from .build import condition, entity, metric, reconnaissance, selector, zone
from .dispatch_metrics_v1 import MODEL_REF


def event(identifier, kind, tick, payload):
    return {"schema_version": "2.0", "id": identifier, "event_type": kind,
            "trigger": {"tick": tick}, "payload": payload}


def request(identifier, zone_id, release, horizon, weight=1.0):
    return {"request_id": identifier, "zone_id": zone_id,
            "release_event_id": release, "deadline_tick": horizon,
            "weight": weight, "dwell_ticks": 3,
            "observer_ids": ["unit.r01", "unit.r02"]}


def alert(identifier, tick, destination, *, status="confirmed", priority=1):
    return event(identifier, "message", tick, {
        "body": json.dumps({"request_id": destination["id"], "status": status,
                            "destination": destination, "priority": priority}, sort_keys=True),
        "visibility": "recipients", "sender_entity_id": "unit.r03",
        "recipient_controller_slots": ["slot.unit.r01", "slot.unit.r02"]})


def emergency(number):
    if number not in range(1, 7):
        raise ValueError("emergency scenario number must be 1..6")
    names = {1: "Weather Diversion", 2: "Equipment Failure", 3: "Distress Call Dispatch",
             4: "Comm Blackout", 5: "Conflicting Alert Triage", 6: "Concurrent Incident Dispatch"}
    horizon = 180
    package, _ = reconnaissance("easy")
    s = package["scenario"]
    sid = f"MD-ER-{number:03d}"
    s["scenario_id"] = f"competition.{sid}.standard"
    s["entities"] = [entity("unit.r01", "red", "air", [0., 0., 100.], None),
                     entity("unit.r02", "red", "air", [0., 300., 100.], None),
                     entity("unit.r03", "red", "shore", [-250., -250., 0.], None)]
    destination = zone("zone.request01", 1200., 0., 100.)
    zones, hazards, known_requests, events = [destination], [], [], []
    reqs = [request("request.01", destination["id"], None, horizon)]
    gaps = ["competition duration/calibration", "held-out seeds", "independent review"]
    if number in (1, 2, 4):
        known_requests = [{"request_id": "request.01", "destination": destination, "priority": 1}]
    if number in (1, 6):
        hazard = zone("zone.hazard01", 600., 0., 180.)
        zones.append(hazard)
        hazards.append({"zone_id": hazard["id"], "activation_event_id": "event.weather"})
        events.append(event("event.weather", "weather_change", 12,
                            {"environment_ref": "environment.competition-storm@1.0.0"}))
        gaps.append("runtime weather/hazard alert not yet exposed in controller observation")
    if number in (2, 6):
        # The native declarative compiler supports sensor/communication suppression,
        # not dynamics_ref suppression. Preserve the paper's radar-station outage
        # and require the mobile responders to reacquire the observable contact.
        for index, kind in ((0, "air"), (1, "air"), (2, "shore")):
            s["entities"][index]["component_refs"].append(f"sensor.competition-{kind}-easy@1.0.0")
        s["entities"][2]["initial_state"]["position_m"] = [850., 0., 0.]
        s["entities"].append(entity("unit.x01", "blue", "shore", [1200., 0., 0.], None))
        events.append(event("event.fault", "component_suppression", 18,
            {"target_entity_id": "unit.r03", "component_ref": "sensor.competition-shore-easy@1.0.0",
             "duration_ticks": horizon}))
        gaps.append("native contact-ID privacy gate must pass before radar-outage acceptance")
    if number in (3, 5, 6):
        reqs[0]["release_event_id"] = "event.request01"
        events.append(alert("event.request01", 15 if number == 3 else 25, destination, priority=3))
        gaps.append("native message events do not currently reach controller received_messages")
    if number == 4:
        s["entities"].append(entity("unit.x01", "blue", "shore", [0., 600., 0.], None))
        events += [event("event.blackout", "jamming_start", 12,
                        {"session_id": "outage.01", "source_entity_id": "unit.x01", "target_entity_id": "unit.r01"}),
                   event("event.restore", "jamming_end", 90, {"session_id": "outage.01"})]
        gaps.append("command delivery/outage progress require native communication probe")
    if number == 5:
        unconfirmed = zone("zone.request02", -1000., 600., 100.)
        zones.append(unconfirmed)
        events += [alert("event.unconfirmed", 8, unconfirmed, status="unverified", priority=2),
                   alert("event.correction", 25, unconfirmed, status="cancelled", priority=2)]
        gaps.append("navigation triage only; original attack/engagement contract not implemented")
    if number == 6:
        second = zone("zone.request02", 1200., -550., 100.)
        zones.append(second)
        reqs[0]["weight"] = 3.
        reqs.append(request("request.02", second["id"], "event.request02", horizon, 1.))
        events.append(alert("event.request02", 28, second, priority=1))
        gaps.append("navigation multi-incident proxy only; no rescue or engagement loop")
    s["world"]["zones"] = zones
    s["world"]["duration_ticks"] = horizon + 1
    s["events"] = events + [event("event.deadline", "mission_marker", horizon + 1,
                                   {"marker_id": "marker.deadline"})]
    s["mission_rules"] = []
    for name, priority, cond in [
        ("success", 100, condition("all", {"conditions": [
            {"operator": "score", "parameters": {"metric_id": mid, "comparison": ">=", "value": 1.}}
            for mid in ("metric.arrival", "metric.safety")]})),
        ("timeout", 10, condition("time", {"comparison": ">=", "tick": horizon + 1}))]:
        outcome_event = f"event.{name}"
        s["events"].append(event(outcome_event, "mission_marker", horizon+1,
                                 {"marker_id": f"marker.{name}"}))
        s["mission_rules"].append({"schema_version": "2.0", "id": f"rule.{name}",
            "priority": priority, "depends_on": [], "condition": cond,
            "outcome": {"set_state": f"state.{name}", "emit_event": outcome_event,
                        "terminal": True, "result": "objective_complete" if name == "success" else "objective_incomplete",
                        "ranking": {"red": 1 if name == "success" else 2,
                                    "blue": 2 if name == "success" else 1}}})
    s["scoring"]["metrics"] = []
    for identifier, kind, weight in [("metric.arrival", "arrival_fraction", .6),
                                     ("metric.timeliness", "timeliness", .2),
                                     ("metric.safety", "route_safety", .2)]:
        s["scoring"]["metrics"].append({"id": identifier, "selector": selector(["unit.r01", "unit.r02"]),
            "aggregation": "mean", "unit": "1", "direction": "maximize", "weight": weight,
            "available": True, "value": 0., "required": True,
            "normalization": {"lower_bound": 0., "upper_bound": 1.},
            "plugin_ref": MODEL_REF, "plugin_parameters": {"metric_id": identifier, "kind": kind,
                "observer_ids": ["unit.r01", "unit.r02"], "requests": deepcopy(reqs),
                "hazards": deepcopy(hazards), "start_tick": 1, "end_tick": horizon + 1, "unit": "1"}})
    if number in (2, 6):
        for item, weight in zip(s["scoring"]["metrics"], (.4, .1, .1)):
            item["weight"] = weight
        continuity = metric("metric.continuity", "contact_fraction",
                            ["unit.r01", "unit.r02", "unit.r03"], ["unit.x01"], horizon, .4)
        continuity["plugin_parameters"]["start_tick"] = 19
        continuity["plugin_parameters"]["maximum_age_ticks"] = 1
        s["scoring"]["metrics"].append(continuity)
        s["mission_rules"][0]["condition"]["parameters"]["conditions"].append(
            {"operator": "score", "parameters": {"metric_id": "metric.continuity",
                                                     "comparison": ">=", "value": .65}})
    template = s["controller_slots"][0]
    for item in s["entities"]:
        item["component_refs"] = ["communication.competition-dispatch@1.0.0"
            if ref == "communication.command-network@2.0.0" else ref for ref in item["component_refs"]]
    s["controller_slots"] = [{**deepcopy(template), "id": e["controller_slot"],
        "controller_id": f"agent.{e['id']}", "faction_id": e["faction_id"],
        "controller_endpoint_ref": e["id"], "selector": selector([e["id"]])} for e in s["entities"]]
    brief = {"schema_version": "competition-brief@1.0", "scenario_id": sid,
        "difficulty": "standard", "name": names[number], "evaluated_side": "red",
        "status": "candidate_not_competition_accepted", "duration_seconds": horizon,
        "physics_dt_seconds": 1., "scoring_deadline_tick": horizon, "adjudication_tick": horizon + 1,
        "task": "Dispatch to confirmed requests, dwell for three ticks, avoid published risk regions. Arrival is not rescue.",
        "available_actions": ["navigation", "hold", "send_message"],
        "responders": ["unit.r01", "unit.r02"], "initial_requests": known_requests,
        "risk_regions": [z for z in zones if any(h["zone_id"] == z["id"] for h in hazards)],
        "difficulty_rationale": "One standard event-mechanism candidate; three levels require measured policy separation first.",
        "fidelity": "UNVALIDATED synthetic 180-second microbenchmark, not paper-duration reproduction"}
    if number in (2, 6):
        continuity = next(m for m in s["scoring"]["metrics"] if m["id"] == "metric.continuity")
        requirement = next(c["parameters"] for c in s["mission_rules"][0]["condition"]["parameters"]["conditions"]
                           if c.get("parameters", {}).get("metric_id") == "metric.continuity")
        station = next(e for e in s["entities"] if e["id"] == "unit.r03")
        station_position = station["initial_state"]["position_m"]
        # Publish an operating sector around our own support station, not the
        # hidden contact position, fault tick, or a future incident destination.
        brief["standing_missions"] = [{"mission_id": "watch.initial",
            "kind": "maintain_physical_contact", "target_count": 1,
            "description": "Maintain a fresh physical sensor contact on the initial watch contact while servicing incident requests.",
            "search_region": zone("public.watch-sector", station_position[0], station_position[1], 600.),
            "controlled_observers": list(brief["responders"]),
            "initial_support_station": {"entity_id": station["id"], "position_m": list(station_position)},
            "metric_id": requirement["metric_id"], "comparison": requirement["comparison"],
            "threshold": requirement["value"], "unit": "fraction_of_eligible_ticks",
            "maximum_contact_age_ticks": continuity["plugin_parameters"]["maximum_age_ticks"],
            "measurement_window": {"starts_after": "station_service_loss", "start_time_is_private": True,
                                   "end_tick_exclusive": brief["adjudication_tick"]}}]
        brief["task"] += " Published standing surveillance remains mandatory; incident arrival does not replace it."
    # Referee acceptance gaps are separate from the public brief: do not leak the
    # future fault target, alert location, event time, or true/false alert status.
    acceptance = {"scenario_id": sid, "competition_accepted": False,
                  "scope": "navigation-dispatch candidate", "unmet_gates": gaps}
    return package, brief, acceptance

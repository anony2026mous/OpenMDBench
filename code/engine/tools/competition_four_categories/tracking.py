"""Eight distinct declarative tracking candidates plus opponent-policy data.

Scripted navigation is a separate authorized BLUE agent using native actions.
Its plan is not a red observation or a second world/event loop. Runtime evidence
must bind its content hash in addition to the native resolved scenario hash.
"""
from copy import deepcopy
import math

from .build import condition, entity, reconnaissance, selector, zone
from .emergency import event
from .tracking_metrics_v1 import MODEL_REF


def tracking(number, *, asset_profile=None):
    if number not in range(1, 9):
        raise ValueError("tracking scenario number must be 1..8")
    if asset_profile not in (None, "legacy", "DEF-P3") or (number != 8 and asset_profile is not None):
        raise ValueError("asset profile override is scoped to TRK008")
    horizon, start = 240, 20
    names = {1: "Single Contact Track", 2: "Dual Contact Monitor",
             3: "Cross-Domain Handover", 4: "Evasive Maneuvers",
             5: "Weather Degradation", 6: "Intermittent Contact Relay",
             7: "Feint and Pursuit", 8: "Mixed-Domain Tracking"}
    package, _ = reconnaissance("easy")
    s = package["scenario"]
    sid = f"MD-TRK-{number:03d}"
    s["scenario_id"] = f"competition.{sid}.standard"
    observers = ["unit.r01", "unit.r02", "unit.r03", "unit.r04"]
    kinds = ["air", "air", "surface", "shore"]
    positions = [[0., -120., 100.], [0., 250., 140.], [150., -200., 0.], [600., -300., 0.]]
    if number == 6:
        positions[-1] = [1000., -300., 0.]
    sensors = {i: f"sensor.competition-{kind}-easy@1.0.0" for i, kind in zip(observers, kinds)}
    s["entities"] = [entity(i, "red", kind, pos, sensors[i]) for i, kind, pos in zip(observers, kinds, positions)]
    # kind, position, commanded speed, heading; no hidden intent encoded in IDs.
    routes = [("surface", [300., 0., 0.], 4., 90.)]
    if number == 2:
        routes = [("surface", [300., -150., 0.], 4., 120.),
                  ("surface", [300., 150., 0.], 4., 60.)]
    if number == 3:
        routes = [("surface", [300., -80., 0.], 3., 90.),
                  ("air", [350., 150., 220.], 4., 90.)]
    if number == 4:
        routes = [("air", [300., -120., 200.], 8., 90.),
                  ("air", [300., 150., 280.], 8., 90.)]
    if number == 5:
        routes = [("surface", [300., -180., 0.], 4., 90.),
                  ("surface", [350., 180., 0.], 4., 90.),
                  ("air", [300., 0., 250.], 6., 90.)]
    if number == 7:
        routes = [("air", [300., -220., 200.], 8., 60.),
                  ("air", [300., 220., 300.], 8., 120.),
                  ("air", [700., 220., 240.], 8., 240.),
                  ("air", [700., -220., 340.], 8., 300.)]
    if number == 8:
        routes = [("surface", [300., -200., 0.], 4., 90.),
                  ("surface", [500., 220., 0.], 4., 60.),
                  ("air", [300., -100., 200.], 8., 60.),
                  ("air", [350., 100., 260.], 8., 120.),
                  ("air", [700., 200., 320.], 8., 240.),
                  ("air", [750., -200., 380.], 8., 300.)]
    targets = []
    segments = []
    for index, (kind, pos, speed, heading) in enumerate(routes):
        identifier = f"unit.x{index+1:02d}"
        targets.append(identifier)
        # A moving-contact task starts underway. The native MMG model accelerates
        # very slowly from rest with this inherited uncalibrated platform profile;
        # do not call centimetres of startup drift a moving-target experiment.
        velocity = [speed*math.sin(math.radians(heading)), speed*math.cos(math.radians(heading)), 0.]
        target = entity(identifier, "blue", kind, pos, None, velocity)
        target["initial_state"]["heading_deg"] = heading
        s["entities"].append(target)
        payload = {"speed_mps": speed, "heading_deg": heading}
        if kind == "air":
            payload["altitude_m"] = pos[2]
        segments.append({"entity_id": identifier, "start_tick": 0, "end_tick": horizon, "payload": payload})
    events, edges, reacquire = [], [], []
    def suppress(identifier, tick, duration, label):
        events.append(event(label, "component_suppression", tick,
            {"target_entity_id": identifier, "component_ref": sensors[identifier], "duration_ticks": duration}))
    if number in (3, 6):
        suppress("unit.r03", 1, 44, "event.surface-initial-suppression")
        suppress("unit.r04", 1, 119 if number == 6 else horizon, "event.shore-initial-suppression")
        for identifier in observers[:2]:
            suppress(identifier, 55, horizon, f"event.air-suppression-{identifier}")
        edges = [{"from_group": "air", "to_group": "surface", "minimum_count": 1}]
    if number == 6:
        suppress("unit.r03", 100, 6, "event.interruption")
        events.append(event("event.reappearance", "mission_marker", 106, {"marker_id": "marker.reappearance"}))
        suppress("unit.r03", 130, horizon, "event.surface-final-suppression")
        edges.append({"from_group": "surface", "to_group": "shore", "minimum_count": 1})
        reacquire.append({"event_id": "event.reappearance", "deadline_ticks": 12})
    if number == 4:
        original = deepcopy(segments)
        segments = []
        for index, segment in enumerate(original):
            for first, last, heading in [(0, 70, 90.), (70, 140, 0. if index == 0 else 180.), (140, horizon, 270.)]:
                segments.append({**segment, "start_tick": first, "end_tick": last,
                                 "payload": {**segment["payload"], "heading_deg": heading}})
        for tick in (70, 140):
            marker = f"event.turn-{tick}"
            events.append(event(marker, "mission_marker", tick+1, {"marker_id": f"marker.turn-{tick}"}))
            reacquire.append({"event_id": marker, "deadline_ticks": 15})
    if number == 5:
        events.append(event("event.fog", "weather_change", 80,
                            {"environment_ref": "environment.competition-tracking-fog@1.0.0"}))
        reacquire.append({"event_id": "event.fog", "deadline_ticks": 20})
    if number == 8:
        suppress("unit.r01", 100, 40, "event.air-window")
        events.append(event("event.air-restored", "mission_marker", 140, {"marker_id": "marker.air-restored"}))
        reacquire.append({"event_id": "event.air-restored", "deadline_ticks": 15})
    link = "communication.competition-tracking-delayed@1.0.0" if number == 8 else "communication.competition-dispatch@1.0.0"
    for item in s["entities"]:
        item["component_refs"] = [link if ref.startswith("communication.") else ref for ref in item["component_refs"]]
    groups = [{"group_id": name, "observer_ids": ids} for name, ids in
              (("air", observers[:2]), ("surface", observers[2:3]), ("shore", observers[3:]))]
    scored = targets[:2] if number == 7 else targets
    specs = [("metric.continuity", "continuity", .7), ("metric.gap", "gap_compliance", 1.)]
    if edges:
        specs.append(("metric.handover", "handover_fraction", 1.))
    if reacquire:
        specs.append(("metric.reacquisition", "reacquisition_fraction", 1.))
    if number == 8:
        specs.append(("metric.freshness", "freshness", .6))
    windows = {}
    if number == 4:
        specs.extend([("metric.after_turn1", "continuity", .7), ("metric.after_turn2", "continuity", .7)])
        windows.update({"metric.after_turn1": (71, 141), "metric.after_turn2": (141, horizon+1)})
    if number == 5:
        specs.append(("metric.after_fog", "continuity", .7))
        windows["metric.after_fog"] = (80, horizon+1)
    metrics = []
    for identifier, kind, threshold in specs:
        window_start, window_end = windows.get(identifier, (start, horizon+1))
        params = {"metric_id": identifier, "kind": kind, "observer_ids": observers,
            "target_ids": scored, "observer_groups": deepcopy(groups), "handover_edges": deepcopy(edges),
            "reacquisition_events": deepcopy(reacquire), "start_tick": window_start, "end_tick": window_end,
            "maximum_age_ticks": 2, "maximum_gap_ticks": 18, "unit": "1"}
        metrics.append({"id": identifier, "selector": selector(observers), "aggregation": "mean",
            "unit": "1", "direction": "maximize", "weight": 1./len(specs), "available": True,
            "value": 0., "required": True, "normalization": {"lower_bound": 0., "upper_bound": 1.},
            "plugin_ref": MODEL_REF, "plugin_parameters": params})
    s["scoring"]["metrics"] = metrics
    s["world"].update(duration_ticks=horizon+1, zones=[])
    s["events"] = events + [event("event.deadline", "mission_marker", horizon+1, {"marker_id": "marker.deadline"})]
    success_conditions = [{"operator": "time", "parameters": {"comparison": ">=", "tick": horizon+1}}]
    success_conditions += [{"operator": "score", "parameters": {"metric_id": mid, "comparison": ">=", "value": threshold}}
                           for mid, _, threshold in specs]
    s["mission_rules"] = []
    for name, priority, cond in [("success", 100, condition("all", {"conditions": success_conditions})),
                                 ("timeout", 10, condition("time", {"comparison": ">=", "tick": horizon+1}))]:
        outcome_event = f"event.{name}"
        s["events"].append(event(outcome_event, "mission_marker", horizon+1,
                                 {"marker_id": f"marker.{name}"}))
        s["mission_rules"].append({"schema_version": "2.0", "id": f"rule.{name}",
            "priority": priority, "depends_on": [], "condition": cond,
            "outcome": {"set_state": f"state.{name}", "emit_event": outcome_event, "terminal": True,
                "result": "objective_complete" if name == "success" else "objective_incomplete",
                "ranking": {"red": 1 if name == "success" else 2, "blue": 2 if name == "success" else 1}}})
    template = s["controller_slots"][0]
    s["controller_slots"] = [{**deepcopy(template), "id": e["controller_slot"],
        "controller_id": f"agent.{e['id']}", "faction_id": e["faction_id"],
        "controller_endpoint_ref": e["id"], "selector": selector([e["id"]])} for e in s["entities"]]
    cues = [zone(f"cue.{index+1:02d}", routes[index][1][0], routes[index][1][1], 65.) for index in range(len(scored))]
    brief = {"schema_version": "competition-brief@1.0", "scenario_id": sid, "difficulty": "standard",
        "name": names[number], "status": "candidate_not_competition_accepted", "evaluated_side": "red",
        "duration_seconds": horizon, "physics_dt_seconds": 1., "scoring_deadline_tick": horizon,
        "adjudication_tick": horizon+1, "scoring_start_tick": start, "observers": observers,
        "observer_domains": dict(zip(observers, kinds)),
        "mobile_observers": observers[:3], "initial_designation_regions": cues,
        "task": "Maintain the initially designated observable contacts until the deadline; one detection is not completion.",
        "available_actions": ["navigation", "hold", "send_message"],
        "difficulty_rationale": "One mechanism-specific standard candidate; three levels require measured separation and calibration.",
        "fidelity": "UNVALIDATED synthetic 240-second microbenchmark, not paper-duration reproduction"}
    gaps = ["strict native contact-ID privacy", "full checkpoint hash equivalence",
            "native checkpoint integrity rejects pre-window None plugin evidence",
            "competition duration and asset-budget calibration", "held-out seeds and independent review",
            "source-bound scripted opponent driver must be used, not static target fallback"]
    if number in (3, 6):
        gaps.append("handover measures sensor-group transfer; communication-delivered track handover not yet scored")
    if number in (7, 8):
        gaps.append("agent track-report identity-switch/position-error scoring not yet implemented")
    if number == 8:
        gaps.append("freshness metric uses sensor facts, not yet communication-delivered information age")
    acceptance = {"scenario_id": sid, "competition_accepted": False, "unmet_gates": gaps}
    opponent = {"schema_version": "scheduled-navigation@1.0", "faction_id": "blue",
                "status": "candidate_opponent_policy_not_red_public_brief", "segments": segments}
    if number in (7, 8):
        from .track_reporting import attach_reporting_contract
        attach_reporting_contract(package, brief, acceptance, scored)
    if number == 8 and asset_profile != "legacy":
        from .tracking_budget_profile import apply_def_p3
        apply_def_p3(package, brief)
    return package, brief, acceptance, opponent

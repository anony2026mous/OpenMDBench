"""REC002..008 declarative candidates; no engine or legacy edits."""
from copy import deepcopy
import math

from .build import condition, entity, reconnaissance as pilot, selector, zone
from .emergency import event
from .recon_metrics_v1 import MODEL_REF


def group(identifier, observers, items, start=1, end=241):
    return {"group_id": identifier, "observer_ids": list(observers), "item_ids": list(items),
            "start_tick": start, "end_tick": end}


def reconnaissance(number):
    if type(number) is not int or number not in range(2, 9):
        raise ValueError("new reconnaissance scenario number must be 2..8")
    horizon = 240
    names = {2: "Eastern Sector Sweep", 3: "Coastal Recon", 4: "Low-Observability Contact Search",
             5: "Multi-Domain Probe", 6: "Storm Watch", 7: "Intermittent Ingress Search",
             8: "Air-Surface-Shore Awareness"}
    package, _ = pilot("easy")
    s = package["scenario"]
    sid = f"MD-REC-{number:03d}"
    s["scenario_id"] = f"competition.{sid}.standard"
    level = "hard" if number in (4, 7) else "easy"
    sensor = lambda kind: f"sensor.competition-{kind}-{level}@1.0.0"
    red = [entity("unit.r01", "red", "air", [0., 350., 120.], sensor("air")),
           entity("unit.r02", "red", "surface", [0., -350., 0.], sensor("surface")),
           entity("unit.r03", "red", "shore", [-200., 0., 0.], None if number == 5 else sensor("shore"))]
    if number in (2, 8):
        red[0]["initial_state"]["position_m"] = [0., -600., 120.]
        red.append(entity("unit.r04", "red", "air", [0., 600., 160.], sensor("air")))
    if number == 8:
        red[1]["initial_state"]["position_m"] = [100., 0., 0.]
    observers = [e["id"] for e in red]
    mobiles = [e["id"] for e in red if e["id"] != "unit.r03"]
    events, actors, static, segments, windows = [], [], [], [], []
    def target(kind, x, y, release=0, end=241, heading=270., speed=2.):
        identifier = f"unit.x{len(actors)+1:02d}"
        altitude = 220. if kind == "air" else 0.
        velocity = [speed*math.sin(math.radians(heading)), speed*math.cos(math.radians(heading)), 0.]
        actor = entity(identifier, "blue", kind, [x, y, altitude], None, velocity)
        actor["initial_state"]["heading_deg"] = heading
        if release:
            actor["controller_slot"] = f"controller/{identifier}"
            events.append(event(f"event.spawn-{identifier}", "spawn", release, {"entity": actor}))
        else:
            static.append(actor)
        actors.append(actor)
        base = {"speed_mps": speed, "heading_deg": heading}
        if kind == "air":
            base["altitude_m"] = altitude
        # The opponent really moves via its own native navigation actions.
        turn = min(release+55, horizon)
        for first, last, course in [(release, turn, heading), (turn, horizon, (heading+180.) % 360.)]:
            if first < last:
                segments.append({"entity_id": identifier, "start_tick": first, "end_tick": last,
                                 "payload": {**base, "heading_deg": course}})
        windows.append({"id": identifier, "domain": kind, "start": max(1, release+1), "end": end})
        return identifier

    if number == 2:
        sectors = [[(550., -600.), (1100., -600.)], [(550., 600.), (1100., 600.)]]
        target("surface", 1100., -600.)
        target("air", 1100., 600., speed=3.)
    elif number == 3:
        sectors = [[(550., 350.), (1000., 350.)], [(400., -350.), (800., -350.)]]
        target("air", 1000., 350., speed=3.)
        target("surface", 800., -350.)
    elif number == 4:
        sectors = [[(450., -120.), (850., 180.), (1250., -120.)]]
        target("surface", 1120., -80., speed=1.)
    elif number == 5:
        sectors = [[(450., 350.), (900., 350.)], [(450., -350.), (900., -350.)]]
        target("air", 850., 350., speed=3.)
        target("surface", 850., -350.)
    elif number == 6:
        sectors = [[(450., 300.), (850., 300.)], [(400., -300.), (800., -300.)]]
        target("air", 850., 300., speed=3.)
        target("surface", 800., -300.)
    elif number == 7:
        sectors = [[(450., 0.), (850., 0.), (1150., 0.)]]
        target("surface", 700., 120., end=81, speed=1.)
        target("air", 850., -100., release=85, end=156, speed=2.)
        target("surface", 1100., 120., release=165, speed=1.)
    else:
        sectors = [[(500., y), (900., y)] for y in (-600., 0., 600.)]
        for wave, release in enumerate((0, 75, 150)):
            for index, y in enumerate((-600., 0., 600.)):
                target("surface" if index == 1 else "air", 850.+wave*60., y,
                       release=release, end=(75, 150, 241)[wave], speed=2.)
    zones, public_sectors, coverage_groups = [], [], []
    for index, centers in enumerate(sectors):
        cells = [zone(f"zone.s{index+1:02d}.c{j+1:02d}", x, y, 130.) for j, (x, y) in enumerate(centers)]
        zones.extend(cells)
        public_sectors.append({"sector_id": f"sector.{index+1:02d}", "cells": cells})
        coverage_groups.append(group(f"sector.{index+1:02d}", mobiles, [c["id"] for c in cells]))
    if number in (6, 8):
        events.extend([event("event.weather-onset", "weather_change", 70,
                            {"environment_ref": "environment.competition-tracking-fog@1.0.0"}),
                       event("event.weather-clear", "weather_change", 150,
                            {"environment_ref": "environment.clear@2.0.0"})])
    if number in (7, 8):
        for index, (first, duration) in enumerate(((60, 35), (150, 30)) if number == 7 else ((120, 30),)):
            events.append(event(f"event.observation-gap-{index}", "component_suppression", first,
                {"target_entity_id": "unit.r01", "component_ref": sensor("air"), "duration_ticks": duration}))
    link = "communication.competition-recon-delayed@1.0.0" if number in (5, 8) else "communication.competition-dispatch@1.0.0"
    if number == 8:
        events.append(event("event.communication-gap", "component_suppression", 120,
            {"target_entity_id": "unit.r02", "component_ref": link, "duration_ticks": 25}))
    for actor in red+actors:
        actor["component_refs"] = [link if r.startswith("communication.") else r for r in actor["component_refs"]]
    all_targets = [a["id"] for a in actors]
    if number in (3, 5):
        discovery = [group("domain.air", ["unit.r01"], [w["id"] for w in windows if w["domain"] == "air"]),
                     group("domain.surface", ["unit.r02", "unit.r03"] if number == 3 else ["unit.r02"],
                           [w["id"] for w in windows if w["domain"] == "surface"])]
    elif number == 6:
        discovery = [group(name, observers, all_targets, first, last) for name, first, last in
                     [("before_weather", 1, 70), ("degraded_weather", 71, 150), ("after_weather", 151, 241)]]
    elif number in (7, 8):
        discovery = [group(f"observation.{index+1:02d}", observers, [w["id"]], w["start"], w["end"])
                     for index, w in enumerate(windows)]
    else:
        discovery = [group("all_contacts", observers, all_targets)]
    specs = [("metric.discovery", "recall", discovery, 1.),
             ("metric.coverage", "coverage", coverage_groups, 1.),
             ("metric.discovery_timeliness", "discovery_timeliness", discovery, None)]
    if number == 2:
        specs.append(("metric.efficient_coverage", "nonduplicate_effort", coverage_groups, None))
    if number in (6, 8):
        specs.extend([("metric.freshness", "fresh_fraction", discovery, .2),
                      ("metric.information_timeliness", "information_freshness", discovery, .25)])
    if number == 5:
        specs = [("metric.delivered_recall", "delivered_recall", discovery, 1.),
                 ("metric.delivered_freshness", "delivered_fresh_fraction", discovery, .15),
                 ("metric.delivered_timeliness", "delivered_information_freshness", discovery, None)]
    if number == 8:
        # The receiving station cannot self-report to satisfy handoff.
        delivered = [{**g, "observer_ids": mobiles} for g in discovery]
        specs.append(("metric.delivered_recall", "delivered_recall", delivered, 1.))
    delivery = {"recipient_entity_id": "unit.r03", "recipient_controller_slot": "slot.unit.r03"}
    s["entities"] = red+static
    s["world"].update(duration_ticks=horizon+1, zones=zones)
    s["events"] = events+[event("event.deadline", "mission_marker", horizon+1, {"marker_id": "marker.deadline"})]
    s["scoring"]["metrics"] = [{"id": mid, "selector": selector(observers), "aggregation": "mean",
        "unit": "1", "direction": "maximize", "weight": 1/len(specs), "available": True,
        "value": 0., "required": threshold is not None, "normalization": {"lower_bound": 0., "upper_bound": 1.},
        "plugin_ref": MODEL_REF, "plugin_parameters": {"metric_id": mid, "kind": kind, "groups": deepcopy(groups),
            "maximum_age_ticks": 8 if kind.startswith("delivered_") else 2,
            "delivery": delivery if kind.startswith("delivered_") else None, "unit": "1"}}
        for mid, kind, groups, threshold in specs]
    conditions = [{"operator": "time", "parameters": {"comparison": ">=", "tick": horizon+1}}]
    conditions.extend({"operator": "score", "parameters": {"metric_id": mid, "comparison": ">=", "value": threshold}}
                      for mid, _, _, threshold in specs if threshold is not None)
    s["mission_rules"] = []
    for name, priority, cond in [("success", 100, condition("all", {"conditions": conditions})),
                                ("timeout", 10, condition("time", {"comparison": ">=", "tick": horizon+1}))]:
        # Both rules may qualify at the deadline. Distinct declared outcomes
        # preserve both receipt events; native priority still selects success.
        outcome_event = f"event.{name}"
        s["events"].append(event(outcome_event, "mission_marker", horizon+1,
                                 {"marker_id": f"marker.{name}"}))
        s["mission_rules"].append({"schema_version": "2.0", "id": f"rule.{name}", "priority": priority,
            "depends_on": [], "condition": cond, "outcome": {"set_state": f"state.{name}", "emit_event": outcome_event,
                "terminal": True, "result": "objective_complete" if name == "success" else "objective_incomplete",
                "ranking": {"red": 1 if name == "success" else 2, "blue": 2 if name == "success" else 1}}})
    template = s["controller_slots"][0]
    s["controller_slots"] = [{**deepcopy(template), "id": e["controller_slot"], "controller_id": f"agent.{e['id']}",
        "faction_id": e["faction_id"], "controller_endpoint_ref": e["id"], "selector": selector([e["id"]])} for e in red+static]
    if number in (2, 8):
        assignments = {"unit.r01": [public_sectors[0]["sector_id"]], "unit.r04": [public_sectors[-1]["sector_id"]],
                       "unit.r02": [public_sectors[1 if number == 8 else 0]["sector_id"]]}
    else:
        assignments = {"unit.r01": [public_sectors[0]["sector_id"]], "unit.r02": [public_sectors[-1]["sector_id"]]}
    brief = {"schema_version": "competition-brief@1.0", "scenario_id": sid, "name": names[number],
        "difficulty": "standard", "status": "candidate_not_competition_accepted", "evaluated_side": "red",
        "duration_seconds": horizon, "physics_dt_seconds": 1., "scoring_deadline_tick": horizon, "adjudication_tick": horizon+1,
        "search_sectors": public_sectors, "suggested_sector_assignments": assignments,
        "own_assets": [{"entity_id": e["id"], "domain": "shore" if e["id"] == "unit.r03" else "surface" if e["id"] == "unit.r02" else "air",
                        "sensor_range_m": 0 if number == 5 and e["id"] == "unit.r03" else 250 if level == "hard" else 450} for e in red],
        "available_actions": ["navigation", "hold", "send_message"],
        "report_protocol": {**delivery, "schema_version": "competition-contact-report@1.0",
            "fields": ["contact_id", "observed_tick"], "report_interval_ticks": 3, "maximum_information_age_ticks": 8},
        "task": "Survey every assigned sector and maintain timely information until the deadline. Report only contacts published in your own observations; no engagement is required.",
        "difficulty_rationale": "One mechanism-specific standard; held-out policy distributions must justify further tiers.",
        "fidelity": "UNVALIDATED synthetic 240-second native candidate; not paper-duration or calibrated real-world reproduction"}
    gaps = ["strict native contact-ID privacy", "complete checkpoint and rename/reorder equivalence",
            "held-out multi-policy distributions and independent review", "competition duration and asset-budget calibration",
            "coverage is cell visitation, not a continuous sensor-footprint map",
            "false-alarm and unnecessary-engagement metrics not yet implemented"]
    if number in (4, 7):
        gaps.append("low observability is an explicit reduced-footprint surrogate, not calibrated target signature")
    if number in (5, 8):
        gaps.append("handoff uses explicit native controller reports; not a claim that automatic shared-contact histories refresh")
    if number in (6, 8):
        gaps.append("controller-visible environment alerts and deliberate recovery planning not yet proven")
    opponent = {"schema_version": "wave-navigation@1.0", "faction_id": "blue",
        "status": "candidate_opponent_plan_not_public", "segments": segments,
        "controller_slots": {e["id"]: e["controller_slot"] for e in actors}}
    return package, brief, {"scenario_id": sid, "competition_accepted": False, "unmet_gates": gaps}, opponent

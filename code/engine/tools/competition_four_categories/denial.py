"""Six native sustained-denial candidates; no fake hit or damage injection."""
from copy import deepcopy
import math

from .build import candidate_catalog, condition, entity, reconnaissance, selector, zone
from .emergency import event
from .denial_metrics_v1 import MODEL_REF


def denial(number):
    if number not in range(1, 7):
        raise ValueError("denial scenario number must be 1..6")
    horizon = 240
    names = {1: "Single Sector Defense", 2: "Dual Sector Defense", 3: "Perimeter Security",
             4: "Communication-Limited Denial", 5: "Mixed-Traffic Denial", 6: "Multi-Zone Sustained Denial"}
    package, _ = reconnaissance("easy")
    s = package["scenario"]
    sid = f"MD-AD-{number:03d}"
    s["scenario_id"] = f"competition.{sid}.standard"
    s["relationships"] = [{"schema_version": "2.0", "source_faction_id": a,
        "target_faction_id": b, "relation": "hostile"} for a, b in (("red", "blue"), ("blue", "red"))]
    zone_y = [0.] if number in (1, 3, 4, 5) else [-650., 650.]
    if number == 6:
        zone_y = [-850., 0., 850.]
    protected_zones = [zone(f"zone.protected{index+1:02d}", 0., y, 160.) for index, y in enumerate(zone_y)]
    zones = deepcopy(protected_zones)
    if number == 3:
        zones.append(zone("zone.outer-warning", 0., 0., 650.))
    red = [entity("unit.r01", "red", "air", [0., -350., 200.], "sensor.competition-denial-air@1.0.0"),
           entity("unit.r02", "red", "shore", [-350., 0., 0.], "sensor.competition-denial-shore@1.0.0"),
           entity("unit.r03", "red", "surface", [0., 400., 0.], "sensor.competition-denial-surface@1.0.0")]
    red[0].update(loadout_ref="loadout.interceptor-uav@2.0.0",
                  ammunition={"ammunition.interceptor-missile@2.0.0": 6 if number == 6 else 10}, target_domains=["air"])
    red[1].update(loadout_ref="loadout.shore-ciws@2.0.0",
                  ammunition={"ammunition.shore-ciws@2.0.0": 12 if number == 6 else 24}, target_domains=["air"])
    red[2].update(platform_ref="platform.competition-armed-usv@1.0.0", dynamics_ref="dynamics.armed-usv@2.0.0",
                  loadout_ref="loadout.armed-usv@2.0.0", ammunition={"ammunition.surface-missile@2.0.0": 6 if number == 6 else 10},
                  target_domains=["surface"])
    if number in (2, 6):
        extra = deepcopy(red[0])
        extra.update(id="unit.r04", controller_slot="slot.unit.r04")
        extra["initial_state"]["position_m"] = [0., 650., 260.]
        red.append(extra)
    events, static_blue, all_blue, intruders, protected, segments = [], [], [], [], [], []
    def add_actor(kind, position, speed, heading, activation=0, preserve=False, route=None):
        identifier = f"unit.x{len(all_blue)+1:02d}"
        velocity = [speed*math.sin(math.radians(heading)), speed*math.cos(math.radians(heading)), 0.]
        actor = entity(identifier, "blue", kind, position, None, velocity)
        actor["initial_state"]["heading_deg"] = heading
        all_blue.append(actor)
        if activation == 0:
            static_blue.append(actor)
        else:
            actor["controller_slot"] = f"controller/{identifier}"
            events.append(event(f"event.spawn-{identifier}", "spawn", activation, {"entity": actor}))
        if preserve:
            protected.append({"entity_id": identifier, "initial_health": 1.})
        else:
            intruders.append(identifier)
        base = {"speed_mps": speed, "heading_deg": heading}
        if kind == "air":
            base["altitude_m"] = position[2]
        for first, last, course in route or [(activation, horizon, heading)]:
            segments.append({"entity_id": identifier, "start_tick": first, "end_tick": last,
                             "payload": {**base, "heading_deg": course}})
    wave_ticks = [0, 90] if number in (1, 4) else [0]
    if number == 6:
        wave_ticks = [0, 75, 145]
    for wave_index, activation in enumerate(wave_ticks):
        for index, y in enumerate(zone_y):
            kind = "surface" if number == 6 and (wave_index+index) % 2 else "air"
            speed = 6. if kind == "surface" else 18.
            distance = 1050. if kind == "surface" else 1500.
            # Ensure even the last wave has time to reach its zone without defence.
            if activation > 100:
                distance = 430. if kind == "surface" else 1100.
            add_actor(kind, [distance, y, 180.+index*50 if kind == "air" else 0.], speed, 270., activation)
    if number in (3, 5):
        add_actor("air", [1750., 100., 280.], 16., 270., 60 if number == 5 else 30)
    if number in (3, 5, 6):
        # Protected traffic has the same faction and public hull signatures.
        # Protection labels exist only in referee scoring, never IDs/tags/briefs.
        add_actor("air", [1000., 780. if number != 6 else 1450., 180.], 12., 270., preserve=True)
    if number == 5:
        add_actor("air", [1550., -600., 240.], 16., 300., preserve=True,
                  route=[(0, 40, 300.), (40, horizon, 90.)])
    if number in (4, 6):
        jammer_id = f"unit.x{len(all_blue)+1:02d}"
        jammer = entity(jammer_id, "blue", "shore", [1900., 1300., 0.], None)
        static_blue.append(jammer)
        all_blue.append(jammer)
        for index, defender in enumerate(red):
            if defender["id"] in {"unit.r01", "unit.r04"}:
                jam_id = f"outage.{index+1}"
                events.extend([event(f"event.jam-start-{index}", "jamming_start", 55,
                    {"session_id": jam_id, "source_entity_id": jammer_id, "target_entity_id": defender["id"]}),
                    event(f"event.jam-end-{index}", "jamming_end", 135, {"session_id": jam_id})])
    s["entities"] = red + static_blue
    for actor in red + all_blue:
        actor["component_refs"] = ["communication.competition-denial@1.0.0" if ref.startswith("communication.") else ref for ref in actor["component_refs"]]
    s["world"].update(duration_ticks=horizon+1, zones=zones)
    s["world"]["roe_rules"] = [{"schema_version": "2.0", "id": "roe.defender-observed-contact",
        "source_faction_id": "red", "target_faction_id": "blue", "relationship": "hostile",
        "engagement_permitted": True}]
    s["events"] = events + [event("event.deadline", "mission_marker", horizon+1, {"marker_id": "marker.deadline"})]
    specs = [("metric.protection", "protection_fraction", 1, horizon+1, .95),
             ("metric.breaches", "breach_free", 1, horizon+1, 1.)]
    if protected:
        specs.append(("metric.protected_integrity", "protected_integrity", 1, horizon+1, 1.))
    if number in (4, 6):
        specs.append(("metric.outage_protection", "protection_fraction", 55, 135, .95))
    if number == 6:
        specs.append(("metric.late_protection", "protection_fraction", 145, horizon+1, .95))
    s["scoring"]["metrics"] = [{"id": mid, "selector": selector([r["id"] for r in red]),
        "aggregation": "mean", "unit": "1", "direction": "maximize", "weight": 1./len(specs),
        "available": True, "value": 0., "required": True, "normalization": {"lower_bound": 0., "upper_bound": 1.},
        "plugin_ref": MODEL_REF, "plugin_parameters": {"metric_id": mid, "kind": kind,
            "zone_ids": [z["id"] for z in protected_zones], "intruder_ids": intruders,
            "protected_entities": deepcopy(protected), "start_tick": first, "end_tick": last,
            "maximum_breaches_per_zone": 0, "unit": "1"}} for mid, kind, first, last, threshold in specs]
    conditions = [{"operator": "time", "parameters": {"comparison": ">=", "tick": horizon+1}}]
    conditions.extend({"operator": "score", "parameters": {"metric_id": mid, "comparison": ">=", "value": threshold}}
                      for mid, kind, first, last, threshold in specs)
    s["mission_rules"] = []
    for name, priority, cond in [("success", 100, condition("all", {"conditions": conditions})),
                                ("timeout", 10, condition("time", {"comparison": ">=", "tick": horizon+1}))]:
        outcome_event = f"event.{name}"
        s["events"].append(event(outcome_event, "mission_marker", horizon+1,
                                 {"marker_id": f"marker.{name}"}))
        s["mission_rules"].append({"schema_version": "2.0", "id": f"rule.{name}", "priority": priority,
            "depends_on": [], "condition": cond, "outcome": {"set_state": f"state.{name}",
                "emit_event": outcome_event, "terminal": True,
                "result": "objective_complete" if name == "success" else "objective_incomplete",
                "ranking": {"red": 1 if name == "success" else 2, "blue": 2 if name == "success" else 1}}})
    template = s["controller_slots"][0]
    s["controller_slots"] = [{**deepcopy(template), "id": e["controller_slot"],
        "controller_id": f"agent.{e['id']}", "faction_id": e["faction_id"],
        "controller_endpoint_ref": e["id"], "selector": selector([e["id"]])} for e in red + static_blue]
    inventory = {}
    resources = {f"{r['id']}@{r['version']}": r for r in candidate_catalog()["resources"]}
    weapon_definitions = {ref: r["content"] for ref, r in resources.items() if r["resource_type"] == "weapons"}
    own_assets = []
    for actor in red:
        platform = resources[actor["platform_ref"]]["content"]
        dynamics = resources[actor["dynamics_ref"]]["content"]
        sensors = [resources[ref]["content"] for ref in actor["component_refs"]
                   if resources[ref]["resource_type"] == "sensors"]
        own_assets.append({"entity_id": actor["id"], "platform_ref": actor["platform_ref"],
            "domain": platform["domain"], "mobile": platform["mobile"] and dynamics["mobile"],
            "initial_position_m": deepcopy(actor["initial_state"]["position_m"]),
            "nominal_sensor_range_m": max(s["range_m"] for s in sensors) if sensors else None,
            "maximum_navigation_speed_mps": dynamics.get("max_speed_mps")})
        kind = "surface" if actor["id"] == "unit.r03" else "air"
        weapon = "weapon.surface-missile@2.0.0" if kind == "surface" else ("weapon.shore-ciws@2.0.0" if actor["id"] == "unit.r02" else "weapon.interceptor-missile@2.0.0")
        inventory[actor["id"]] = {"weapon_ref": weapon, "target_domain": kind,
            "initial_ammunition": deepcopy(actor["ammunition"]),
            "minimum_range_m": weapon_definitions[weapon]["min_range_m"],
            "maximum_range_m": weapon_definitions[weapon]["max_range_m"],
            "cooldown_ticks": weapon_definitions[weapon]["cooldown_ticks"],
            "rounds_per_action": weapon_definitions[weapon].get("rounds_per_action", 1)}
        if weapon_definitions[weapon].get("delivery_model") == "guided_missile":
            inventory[actor["id"]]["delivery_model"] = "guided_missile"
            inventory[actor["id"]]["projectile_profile"] = {
                key: weapon_definitions[weapon]["missile"][key]
                for key in ("launch_speed_mps", "cruise_speed_mps", "max_flight_ticks")}
    brief = {"schema_version": "competition-brief@1.0", "scenario_id": sid, "difficulty": "standard",
        "name": names[number], "status": "candidate_not_competition_accepted", "evaluated_side": "red",
        "duration_seconds": horizon, "physics_dt_seconds": 1., "scoring_deadline_tick": horizon,
        "adjudication_tick": horizon+1, "defenders": [r["id"] for r in red],
        "protected_zones": protected_zones, "warning_zones": [z for z in zones if z not in protected_zones],
        "own_inventory": inventory, "own_assets": own_assets,
        "available_actions": ["navigation", "hold", "fire_weapon", "send_message"],
        "engagement_lookahead_ticks": 60,
        "task": "Preserve each protected zone through the entire deadline. Use observable behavior; do not indiscriminately engage passing traffic.",
        "difficulty_rationale": "One mechanism-specific standard candidate; difficulty tiers require measured policy separation.",
        "fidelity": "UNVALIDATED synthetic 240-second benchmark; inherited native combat models are not real-world calibration"}
    gaps = ["strict native contact-ID privacy", "checkpoint evidence and full hash equivalence",
            "complete fair-agent success/failure distributions", "competition duration and resource calibration",
            "independent review"]
    if protected:
        gaps.append("protected integrity is all-cause harm; defender-only harm attribution and classification-error metrics pending")
    if number in (4, 6):
        gaps.append("receiver-delivered information age and coordination recovery metrics pending")
    if number == 6:
        gaps.append("cross-zone reallocation and complete mixed-role difficulty distribution not yet validated")
    opponent = {"schema_version": "wave-navigation@1.0", "faction_id": "blue",
                "status": "candidate_opponent_plan_not_public", "segments": segments,
                "controller_slots": {e["id"]: e["controller_slot"] for e in all_blue if any(s["entity_id"] == e["id"] for s in segments)}}
    return package, brief, {"scenario_id": sid, "competition_accepted": False, "unmet_gates": gaps}, opponent

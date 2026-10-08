"""Build isolated candidate assets. Existing formal registry and packages are untouched."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import yaml
from .surface_profile import PLATFORM_REF as SURFACE_PLATFORM_REF, DYNAMICS_REF as SURFACE_DYNAMICS_REF, resources as surface_resources
from .candidate_geometry import SITE_PLATFORM_REF, resources as geometry_resources


class LiteralDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def yaml_text(value: dict) -> str:
    return yaml.dump(value, Dumper=LiteralDumper, sort_keys=False)

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "scenarios" / "competition_v1"
CATALOG_PATH = ROOT / "catalog" / "v2" / "competition_four_categories.yaml"


def selector(ids: list[str]) -> dict:
    return {"schema_version": "2.0", "entity_ids": ids}

def condition(operator: str, parameters: dict) -> dict:
    return {"schema_version": "2.0", "operator": operator,
            "selector": selector(["unit.r01"]), "parameters": parameters}

def zone(identifier: str, x: float, y: float, radius: float = 180) -> dict:
    return {"schema_version": "2.0", "id": identifier, "geometry_type": "polygon",
            "coordinates_m": [[x-radius, y-radius], [x+radius, y-radius],
                              [x+radius, y+radius], [x-radius, y+radius]]}

def entity(identifier: str, faction: str, kind: str, position: list, sensor: str | None,
           velocity: list | None = None) -> dict:
    platform = {"air": "interceptor-uav", "surface": "picket-usv",
                "shore": "shore-defence-site"}[kind]
    dynamics = "fixed-site" if kind == "shore" else platform
    components = ["communication.command-network@2.0.0"]
    if sensor:
        components.append(sensor)
    return {"schema_version": "2.0", "id": identifier, "faction_id": faction,
            "platform_ref": SURFACE_PLATFORM_REF if kind == "surface" else SITE_PLATFORM_REF if kind == "shore" else f"platform.{platform}@2.0.0",
            "dynamics_ref": SURFACE_DYNAMICS_REF if kind == "surface" else f"dynamics.{dynamics}@2.0.0",
            "component_refs": components, "controller_slot": f"slot.{identifier}",
            "initial_state": {"schema_version": "2.0", "position_m": position,
                              "velocity_mps": velocity or [0., 0., 0.],
                              "heading_deg": 90., "health": 1., "energy": 1.},
            "tags": []}

def metric(identifier: str, kind: str, observers: list, items: list, horizon: int,
           weight: float) -> dict:
    from .metrics_v1 import MODEL_REF
    return {"id": identifier, "selector": selector(observers), "aggregation": "mean",
            "unit": "1", "direction": "maximize", "weight": weight,
            # Empty cumulative progress starts at zero; the bound plugin supplies every tick.
            # Runtime missing samples still return None and remain unavailable, never zero-filled.
            "available": True, "value": 0., "required": True,
            "normalization": {"lower_bound": 0., "upper_bound": 1.},
            "plugin_ref": MODEL_REF,
            "plugin_parameters": {"metric_id": identifier, "kind": kind,
                                  "observer_ids": observers, "item_ids": items,
                                  "start_tick": 1, "end_tick": horizon+1,
                                  "maximum_age_ticks": 2, "unit": "1"}}

def candidate_catalog() -> dict:
    source = yaml.safe_load((ROOT / "catalog/v2/md_ad_002.yaml").read_text(encoding="utf-8"))
    keep = {"platforms", "dynamics", "collision_shapes", "visualization_assets",
            "energy", "communications", "environments"}
    resources = [deepcopy(r) for r in source["resources"]
                 if r["resource_type"] in keep and r["version"] == "2.0.0"]
    templates = {r["id"]: r for r in source["resources"] if r["version"] == "2.0.0"}
    resources.extend(surface_resources(templates))
    resources.extend(geometry_resources(templates))
    for level, radius in (("easy", 450.), ("medium", 350.), ("hard", 250.)):
        for kind, original in (("air", "sensor.interceptor-eo"),
                               ("surface", "sensor.picket-radar"),
                               ("shore", "sensor.shore-gap-filler")):
            resource = deepcopy(templates[original])
            resource["id"] = f"sensor.competition-{kind}-{level}"
            resource["version"] = "1.0.0"
            resource["content"].update(range_m=radius, probability=0.9, update_ticks=1,
                                         fidelity="UNVALIDATED_BENCHMARK")
            if "low_altitude_range_m" in resource["content"]:
                resource["content"]["low_altitude_range_m"] = radius
            resources.append(resource)
    storm = deepcopy(templates["environment.clear"])
    storm.update(id="environment.competition-storm", version="1.0.0")
    storm["content"] = {"weather": "storm", "motion_speed_multiplier": .65,
                        "sensor_range_multiplier": .6,
                        "fidelity": "UNVALIDATED_BENCHMARK"}
    resources.append(storm)
    dispatch_link = deepcopy(templates["communication.command-network"])
    dispatch_link.update(id="communication.competition-dispatch", version="1.0.0")
    dispatch_link["content"].pop("delay_ticks", None)
    dispatch_link["content"].update(delay_s=1., ttl_s=200., loss_probability=0.,
                                     fidelity="UNVALIDATED_BENCHMARK")
    resources.append(dispatch_link)
    fog = deepcopy(storm)
    fog.update(id="environment.competition-tracking-fog")
    fog["content"] = {"weather": "fog", "sensor_range_multiplier": .5,
                      "sensor_detection_probability_multiplier": .8,
                      "fidelity": "UNVALIDATED_BENCHMARK"}
    resources.append(fog)
    delayed_link = deepcopy(dispatch_link)
    delayed_link.update(id="communication.competition-tracking-delayed")
    delayed_link["content"].update(delay_s=3., ttl_s=8., loss_probability=.1)
    resources.append(delayed_link)
    report_link = deepcopy(dispatch_link)
    report_link.update(id="communication.competition-recon-delayed")
    report_link["content"].update(delay_s=3., ttl_s=12., loss_probability=0.)
    resources.append(report_link)
    # Reuse the native combat graph rather than implementing damage in a scenario.
    combat_types = {"weapons", "ammunition", "loadouts", "effects", "damage_models"}
    resources.extend(deepcopy(r) for r in source["resources"]
                     if r["resource_type"] in combat_types and r["version"] == "2.0.0")
    surface_source = yaml.safe_load((ROOT / "catalog/v2/md_ad_006.yaml").read_text(encoding="utf-8"))
    surface = {f"{r['id']}@{r['version']}": r for r in surface_source["resources"]}
    known = {f"{r['id']}@{r['version']}" for r in resources}
    def resource_refs(value):
        if isinstance(value, str):
            return {value} if value in surface else set()
        if isinstance(value, dict):
            return set().union(*(resource_refs(v) for v in value.values())) if value else set()
        if isinstance(value, list):
            return set().union(*(resource_refs(v) for v in value)) if value else set()
        return set()
    def include_resource(ref):
        if ref in known:
            return
        resource = deepcopy(surface[ref])
        for dependency in sorted(set(resource["dependencies"]) | resource_refs(resource["content"])):
            include_resource(dependency)
        resources.append(resource)
        known.add(ref)
    for ref in ("dynamics.armed-usv@2.0.0", "loadout.armed-usv@2.0.0", "shape.usv-sphere@2.0.0"):
        include_resource(ref)
    energy = deepcopy(templates["energy.normalized"])
    energy.update(id="energy.competition-denial", version="1.0.0")
    energy["content"]["compatible_platform_types"] = sorted(set(energy["content"]["compatible_platform_types"]) | {"armed-usv"})
    resources.append(energy)
    armed = deepcopy(surface["platform.armed-usv@2.0.0"])
    armed.update(id="platform.competition-armed-usv", version="1.0.0")
    armed["content"]["energy_ref"] = "energy.competition-denial@1.0.0"
    resources.append(armed)
    denial_link = deepcopy(dispatch_link)
    denial_link.update(id="communication.competition-denial")
    denial_link["content"]["compatible_platform_types"] = sorted(set(denial_link["content"]["compatible_platform_types"]) | {"armed-usv"})
    resources.append(denial_link)
    for kind, original in (("air", "sensor.interceptor-eo"), ("shore", "sensor.shore-gap-filler"), ("surface", "sensor.picket-radar")):
        sensor = deepcopy(templates[original])
        sensor.update(id=f"sensor.competition-denial-{kind}", version="1.0.0")
        sensor["content"].update(range_m=1000., probability=.9, update_ticks=1, fidelity="UNVALIDATED_BENCHMARK")
        if "low_altitude_range_m" in sensor["content"]:
            sensor["content"]["low_altitude_range_m"] = 1000.
        if kind == "surface":
            sensor["content"]["compatible_platform_types"] = ["armed-usv", "picket-usv"]
        resources.append(sensor)
    return {"schema_version": "catalog-bundle@2.0", "resources": resources}

def reconnaissance(level: str) -> tuple[dict, dict]:
    horizon, count = {"easy": (180, 1), "medium": (160, 2), "hard": (140, 3)}[level]
    observers = ["unit.r01", "unit.r02", "unit.r03"]
    sensor = lambda kind: f"sensor.competition-{kind}-{level}@1.0.0"
    entities = [entity(observers[0], "red", "air", [0., 0., 100.], sensor("air")),
                entity(observers[1], "red", "surface", [0., -400., 0.], sensor("surface")),
                entity(observers[2], "red", "shore", [-300., 0., 0.], sensor("shore"))]
    targets = [f"unit.x{index+1:02d}" for index in range(count)]
    for index, identifier in enumerate(targets):
        entities.append(entity(identifier, "blue", "surface",
                               [1350.+index*160., 100.+index*120., 0.], None, [2., 0., 0.]))
    zones = [zone("zone.s01", 650., 0.), zone("zone.s02", 1500., 0.)]
    rules = []
    events = []
    states = ["state.active", "state.success", "state.timeout"]
    for name, priority, cond, result in (
        ("success", 100, condition("all", {"conditions": [
            {"operator": "score", "parameters": {"metric_id": mid,
             "comparison": ">=", "value": 1.}} for mid in ("metric.recall", "metric.coverage")]}),
         "objective_complete"),
        ("timeout", 10, condition("time", {"comparison": ">=", "tick": horizon+1}),
         "objective_incomplete"),
    ):
        event_id = f"event.{name}"
        events.append({"schema_version": "2.0", "id": event_id,
                       "event_type": "mission_marker", "trigger": {"tick": horizon+1},
                       "payload": {"marker_id": f"marker.{name}"}})
        rules.append({"schema_version": "2.0", "id": f"rule.{name}",
                      "priority": priority, "depends_on": [], "condition": cond,
                      "outcome": {"set_state": f"state.{name}", "emit_event": event_id,
                                  "terminal": True, "result": result,
                                  "ranking": {"red": 1 if name == "success" else 2,
                                              "blue": 2 if name == "success" else 1}}})
    scenario = {"schema_version": "2.0", "scenario_id": f"competition.MD-REC-001.{level}",
                "factions": [{"schema_version": "2.0", "id": side} for side in ("red", "blue")],
                "relationships": [], "entities": entities, "formations": [],
                "world": {"schema_version": "2.0", "coordinate_system": "local_m",
                          "duration_ticks": horizon+1, "tick_seconds": 1., "zones": zones},
                "events": events, "mission_states": states, "mission_rules": rules,
                "scoring": {"aggregation_version": "utility-v1", "aggregation": "sum",
                            "direction": "maximize", "weight_policy": "normalized_sum_one",
                            "metrics": [metric("metric.recall", "contact_recall", observers, targets, horizon, .6),
                                        metric("metric.coverage", "zone_visits", observers,
                                               [z["id"] for z in zones], horizon, .4)]},
                "score_metrics": [], "controller_policy": "explicit_uncontrolled",
                "controller_slots": [{"id": e["controller_slot"],
                                      "controller_id": f"agent.{e['id']}",
                                      "faction_id": e["faction_id"],
                                      "controller_endpoint_ref": e["id"],
                                      "selector": selector([e["id"]]),
                                      "required_capabilities": [],
                                      "action_schema_ref": "action-batch@2.0",
                                      "observation_schema_ref": "observation@2.0",
                                      "exclusive": True} for e in entities],
                "visibility": [{"view": "referee", "scope": "truth", "allow": True},
                               {"view": "public", "scope": "public", "allow": True},
                               *[{"view": "faction", "faction_id": side,
                                  "scope": "own_and_contacts", "allow": True} for side in ("red", "blue")]]}
    # Public brief deliberately excludes contacts, referee goals and future events.
    brief = {"schema_version": "competition-brief@1.0", "scenario_id": "MD-REC-001",
             "difficulty": level, "name": "Harbor Approach Patrol",
             "status": "candidate_not_competition_accepted", "evaluated_side": "red",
             "duration_seconds": horizon, "physics_dt_seconds": 1.,
             "scoring_deadline_tick": horizon, "adjudication_tick": horizon+1,
             "adjudication_note": "One settling tick reads deadline scores; no new actions or score samples after the deadline.",
             "search_zones": zones, "task": "Survey both search zones and identify observable contacts.",
             "available_actions": ["navigation", "hold"],
             "difficulty_pressure": {"sensor_range_m": {"easy": 450, "medium": 350, "hard": 250}[level]},
             "fidelity": "UNVALIDATED synthetic microbenchmark; not paper-duration reproduction"}
    return {"schema_version": "package@2.0", "adapter_id": "adapter.v2",
            "scenario": scenario}, brief

def build() -> list[Path]:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(yaml_text(candidate_catalog()), encoding="utf-8")
    paths = []
    for level in ("easy", "medium", "hard"):
        package, brief = reconnaissance(level)
        target = PACKAGES / f"md_rec_001_{level}"
        target.mkdir(parents=True, exist_ok=True)
        (target / "scenario.yaml").write_text(yaml_text(package), encoding="utf-8")
        # Non-YAML brief cannot be accidentally included in ScenarioPackage's YAML inputs.
        (target / "public_brief.json").write_text(json.dumps(brief, indent=2)+"\n", encoding="utf-8")
        paths.append(target)
    from .emergency import emergency
    for number in range(1, 7):
        package, brief, acceptance = emergency(number)
        source_plan = None
        if number in (3, 5, 6):
            from .response import response
            package, brief, acceptance, source_plan = response(number)
        target = PACKAGES / f"md_er_{number:03d}_standard"
        target.mkdir(parents=True, exist_ok=True)
        (target / "scenario.yaml").write_text(yaml_text(package), encoding="utf-8")
        (target / "public_brief.json").write_text(json.dumps(brief, indent=2)+"\n", encoding="utf-8")
        (target / "acceptance_gaps.json").write_text(json.dumps(acceptance, indent=2)+"\n", encoding="utf-8")
        if source_plan is not None:
            (target / "scripted_message_policy.json").write_text(json.dumps(source_plan, indent=2)+"\n", encoding="utf-8")
        paths.append(target)
    from .tracking import tracking
    for number in range(1, 9):
        package, brief, acceptance, opponent = tracking(number)
        target = PACKAGES / f"md_trk_{number:03d}_standard"
        target.mkdir(parents=True, exist_ok=True)
        (target / "scenario.yaml").write_text(yaml_text(package), encoding="utf-8")
        for filename, content in (("public_brief.json", brief), ("acceptance_gaps.json", acceptance),
                                  ("scripted_blue_policy.json", opponent)):
            (target / filename).write_text(json.dumps(content, indent=2)+"\n", encoding="utf-8")
        paths.append(target)
    from .denial import denial
    for number in range(1, 7):
        package, brief, acceptance, opponent = denial(number)
        target = PACKAGES / f"md_ad_{number:03d}_standard"
        target.mkdir(parents=True, exist_ok=True)
        (target / "scenario.yaml").write_text(yaml_text(package), encoding="utf-8")
        for filename, content in (("public_brief.json", brief), ("acceptance_gaps.json", acceptance),
                                  ("scripted_blue_policy.json", opponent)):
            (target / filename).write_text(json.dumps(content, indent=2)+"\n", encoding="utf-8")
        paths.append(target)
    from .reconnaissance import reconnaissance as expanded_reconnaissance
    for number in range(2, 9):
        package, brief, acceptance, opponent = expanded_reconnaissance(number)
        target = PACKAGES / f"md_rec_{number:03d}_standard"
        target.mkdir(parents=True, exist_ok=True)
        (target / "scenario.yaml").write_text(yaml_text(package), encoding="utf-8")
        for filename, content in (("public_brief.json", brief), ("acceptance_gaps.json", acceptance),
                                  ("scripted_blue_policy.json", opponent)):
            (target / filename).write_text(json.dumps(content, indent=2)+"\n", encoding="utf-8")
        paths.append(target)
    return paths

if __name__ == "__main__":
    for path in build():
        print(path.relative_to(ROOT))

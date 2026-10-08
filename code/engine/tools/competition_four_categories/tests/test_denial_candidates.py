from copy import deepcopy
import json

import pytest

from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from tools.competition_four_categories.runtime import load_candidate_catalog
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.denial_policy import WaveNavigationPolicy, ZoneGuardPolicy
from tools.competition_four_categories.build import zone


@pytest.mark.parametrize("number", range(1, 7))
def test_denial_native_compile_and_full_deadline_requirement(number):
    package, brief, gaps, plan = denial(number)
    catalog = load_candidate_catalog(allow_candidate=True)
    resolved = ScenarioCompilerV2(catalog=catalog).compile(ScenarioPackageV2.from_mapping(package))
    assert resolved.world.duration_ticks == 241
    conditions = package["scenario"]["mission_rules"][0]["condition"]["parameters"]["conditions"]
    assert {"operator": "time", "parameters": {"comparison": ">=", "tick": 241}} in conditions
    assert gaps["competition_accepted"] is False
    assert package["scenario"]["world"]["roe_rules"] == [{"schema_version": "2.0",
        "id": "roe.defender-observed-contact", "source_faction_id": "red",
        "target_faction_id": "blue", "relationship": "hostile", "engagement_permitted": True}]
    assert "unit.x" not in json.dumps(brief)
    assert "segments" not in brief and "events" not in brief
    WaveNavigationPolicy(plan)
    s = package["scenario"]
    static = {e["id"] for e in s["entities"]}
    spawned = {e["payload"]["entity"]["id"]: e for e in s["events"] if e["event_type"] == "spawn"}
    for segment in plan["segments"]:
        identifier = segment["entity_id"]
        assert identifier in static or identifier in spawned
        if identifier in spawned:
            assert segment["start_tick"] >= spawned[identifier]["trigger"]["tick"]
            assert spawned[identifier]["payload"]["entity"]["controller_slot"] == plan["controller_slots"][identifier]
    assert all(actor["tags"] == [] for actor in s["entities"] if actor["faction_id"] == "blue")


def test_six_defence_mechanisms_differ_not_only_by_name():
    signatures = set()
    for n in range(1, 7):
        package, brief, _, plan = denial(n)
        s = package["scenario"]
        signatures.add(json.dumps({"zone_count": len(brief["protected_zones"]),
            "warning_count": len(brief["warning_zones"]),
            "events": [(e["event_type"], e["trigger"]["tick"]) for e in s["events"]],
            "metrics": [(m["plugin_parameters"]["kind"], m["plugin_parameters"]["start_tick"]) for m in s["scoring"]["metrics"]],
            "segments": [{k: v for k, v in segment.items() if k != "entity_id"} for segment in plan["segments"]]}, sort_keys=True))
    assert len(signatures) == 6


def test_late_wave_has_physical_time_to_reach_zone_and_uses_actual_spawn():
    for number in (1, 4, 6):
        package, brief, _, plan = denial(number)
        spawns = [e for e in package["scenario"]["events"] if e["event_type"] == "spawn"]
        assert spawns
        for e in spawns:
            actor = e["payload"]["entity"]
            first = next(s for s in plan["segments"] if s["entity_id"] == actor["id"])
            arrival_bound = e["trigger"]["tick"] + (actor["initial_state"]["position_m"][0]-160)/first["payload"]["speed_mps"]
            assert arrival_bound < brief["scoring_deadline_tick"]


def test_mixed_domain_denial_has_real_surface_weapon_and_finite_ammunition():
    package, brief, _, _ = denial(6)
    surface = next(e for e in package["scenario"]["entities"] if e["id"] == "unit.r03")
    assert surface["loadout_ref"] == "loadout.armed-usv@2.0.0"
    assert surface["ammunition"]["ammunition.surface-missile@2.0.0"] == 6
    assert brief["own_inventory"]["unit.r03"]["weapon_ref"] == "weapon.surface-missile@2.0.0"
    ids = {m["id"] for m in package["scenario"]["scoring"]["metrics"]}
    assert {"metric.late_protection", "metric.outage_protection", "metric.protected_integrity"} <= ids


def test_wave_policy_waits_for_native_activation_and_rejects_foreign_scope():
    plan = denial(1)[3]
    p = WaveNavigationPolicy(plan)
    assert len(p.active_ids(0)) == 1 and len(p.active_ids(90)) == 2
    observed = {i: {"own_entities": [{"entity_id": i}]} for i in p.active_ids(0)}
    assert len(p.commands(0, observed)) == 1
    assert p.commands(89, observed) == {}
    with pytest.raises(ValueError, match="released own-side"):
        p.commands(90, observed)
    late = {i: {"own_entities": [{"entity_id": i}]} for i in p.active_ids(90)}
    assert len(p.commands(90, late)) == 1
    late[p.active_ids(90)[1]]["own_entities"][0]["entity_id"] = "unit.r01"
    with pytest.raises(ValueError, match="another entity"):
        p.commands(90, late)


def observation(tick, x, y=0., token="opaque.target"):
    return {"tick": tick, "own_entities": [{"entity_id": "unit.r02", "position_m": [-350., 0., 0.]}],
            "organic_contacts": [{"contact_id": token, "observed_tick": tick, "age_ticks": 0,
                                  "estimated_position_m": [x, y, 180.]}]}


def test_guard_uses_observed_intersecting_motion_and_opaque_token_only():
    brief = denial(1)[1]
    p = ZoneGuardPolicy(brief, "unit.r02", "guard")
    assert p.action(observation(1, 650)) is None
    action = p.action(observation(2, 620))
    assert action == {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": "opaque.target"}
    assert "target_id" not in action


def test_passing_traffic_is_not_automatically_treated_as_zone_entry():
    brief = denial(1)[1]
    guard = ZoneGuardPolicy(brief, "unit.r02", "guard")
    blind = ZoneGuardPolicy(brief, "unit.r02", "indiscriminate")
    assert guard.action(observation(1, 200, 700)) is None
    assert guard.action(observation(2, 180, 700)) is None
    assert blind.action(observation(2, 180, 700)) is not None


def test_outer_warning_zone_is_consumed_by_perimeter_policy():
    brief = denial(3)[1]
    brief["warning_zones"] = [zone("outer.test", 0., 0., 400.)]
    guard = ZoneGuardPolicy(brief, "unit.r02", "guard")
    assert guard.action(observation(1, 550)) is None
    assert guard.action(observation(2, 500)) is None
    assert guard.action(observation(4, 390)) is not None


def test_reference_policy_does_not_exceed_its_attempt_budget():
    brief = denial(1)[1]
    brief["own_inventory"]["unit.r02"]["initial_ammunition"] = {"ammunition.shore-ciws@2.0.0": 1}
    p = ZoneGuardPolicy(brief, "unit.r02", "indiscriminate")
    assert p.action(observation(1, 650)) is not None
    assert p.action(observation(2, 620)) is None

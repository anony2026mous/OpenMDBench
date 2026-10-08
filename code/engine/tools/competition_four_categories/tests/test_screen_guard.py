from copy import deepcopy
import json
import math

import pytest
import yaml

from tools.competition_four_categories.build import PACKAGES, candidate_catalog
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.denial_policy import ZoneGuardPolicy
from tools.competition_four_categories.salvo_guard_policy import SalvoGuardPolicy
from tools.competition_four_categories.screen_guard_policy import ScreenGuardPolicy, SETTINGS


def observation(tick=1, contacts=(), owner="unit.r03", position=(0., 400., 0.)):
    return {"tick": tick, "own_entities": [{"entity_id": owner, "position_m": list(position),
        "velocity_mps": [0., 0., 0.], "heading_deg": 90., "lifecycle_state": "active"}],
        "organic_contacts": list(contacts)}


def contact(tick=1, point=(800., 0., 0.), token="opaque"):
    return {"observed_tick": tick, "age_ticks": 0, "contact_id": token,
            "estimated_position_m": list(point), "observer_entity_id": "unit.r03"}


def make(mode="screen-guard", owner="unit.r03"):
    return ScreenGuardPolicy(denial(6)[1], owner, mode)


@pytest.mark.parametrize("number", range(1, 7))
def test_public_own_capabilities_match_resources_without_native_scene_changes(number):
    package, brief, _, _ = denial(number)
    stored = yaml.safe_load((PACKAGES/f"md_ad_{number:03d}_standard"/"scenario.yaml").read_text(encoding="utf-8"))
    assert package == stored
    resources = {f"{r['id']}@{r['version']}": r for r in candidate_catalog()["resources"]}
    entities = {e["id"]: e for e in package["scenario"]["entities"]}
    assert {a["entity_id"] for a in brief["own_assets"]} == set(brief["defenders"])
    for asset in brief["own_assets"]:
        entity = entities[asset["entity_id"]]; assert entity["faction_id"] == brief["evaluated_side"]
        platform = resources[entity["platform_ref"]]["content"]
        dynamics = resources[entity["dynamics_ref"]]["content"]
        assert asset["domain"] == platform["domain"]
        assert asset["mobile"] == (platform["mobile"] and dynamics["mobile"])
        assert asset["initial_position_m"] == entity["initial_state"]["position_m"]
        assert asset["maximum_navigation_speed_mps"] == dynamics.get("max_speed_mps")
        ranges = [resources[ref]["content"]["range_m"] for ref in entity["component_refs"] if resources[ref]["resource_type"] == "sensors"]
        assert asset["nominal_sensor_range_m"] == max(ranges)
    assert "unit.x" not in json.dumps(brief)


def test_static_surface_station_has_a_publicly_demonstrable_southern_blind_zone():
    brief = denial(6)[1]; asset = next(a for a in brief["own_assets"] if a["domain"] == "surface")
    south = min(brief["protected_zones"], key=lambda z: max(p[1] for p in z["coordinates_m"]))
    y_nearest = max(p[1] for p in south["coordinates_m"])
    assert asset["initial_position_m"][1]-y_nearest == 1090.
    assert 1090. > asset["nominal_sensor_range_m"] == 1000.


def test_no_detection_means_public_centre_not_an_unseen_attack_position():
    agent = make(); obs = observation(); before = deepcopy(obs)
    command = agent.navigation(obs)
    assert agent.navigation_log[-1]["goal_m"] == [0., 0.]
    assert command["payload"]["speed_mps"] == 8.
    assert command["payload"]["heading_deg"] == 180.
    assert obs == before


def test_observed_approach_can_shift_station_only_within_public_range_margin():
    agent = make(); command = agent.navigation(observation(contacts=[contact()]))
    goal = agent.navigation_log[-1]["goal_m"]
    assert goal[0] > 0 and abs(goal[1]) < 1e-9
    assert all(math.dist(goal, c) <= agent.asset["nominal_sensor_range_m"]*SETTINGS["nominal_range_fraction"] for c in agent.centres)
    assert command["payload"]["speed_mps"] <= agent.asset["maximum_navigation_speed_mps"]


def test_contact_names_order_and_referee_truth_do_not_drive_navigation():
    a, b = make(), make()
    obs = observation(contacts=[contact(point=(800., -50., 0.)), contact(point=(900., 50., 0.), token="other")])
    changed = deepcopy(obs); changed["organic_contacts"].reverse()
    for i, row in enumerate(changed["organic_contacts"]): row.update(contact_id=f"renamed.{i}", hidden_role="civilian")
    changed.update(future_wave_plan=["private"], referee_blue_states={"secret": [9000, 9000]})
    assert a.navigation(obs) == b.navigation(changed)


@pytest.mark.parametrize("when", [-1, True, 4])
def test_unusable_sample_times_never_choose_an_approach(when):
    agent = make(); agent.navigation(observation(contacts=[contact(tick=when)]))
    assert agent.axis is None


def test_no_surface_motion_for_immobile_air_lost_or_foreign_assets():
    for owner in ("unit.r01", "unit.r02"):
        assert make(owner=owner).navigation(observation(owner=owner)) is None
    agent = make(); assert agent.navigation({"tick": 1, "own_entities": []}) is None
    with pytest.raises(ValueError, match="another controller"): agent.navigation(observation(owner="foreign"))
    assert agent.navigation(observation(tick=240)) is None


@pytest.mark.parametrize("mode", ["screen-guard", "screen-salvo"])
def test_movement_does_not_reimplement_or_change_the_selected_weapon_policy(mode):
    agent = make(mode); brief = denial(6)[1]
    reference = ZoneGuardPolicy(brief, "unit.r03", "guard") if mode == "screen-guard" else SalvoGuardPolicy(brief, "unit.r03")
    for tick in (1, 2, 5):
        obs = observation(tick, [contact(tick, (600.-10*tick, 0., 0.))])
        agent.navigation(obs)
        assert agent.action(obs) == reference.action(obs)

from copy import deepcopy

import pytest

from tools.competition_four_categories.observation_search_policy import ObservationSearchPolicy, SETTINGS
from tools.competition_four_categories.reconnaissance import reconnaissance


def observation(tick=1, position=(0., 350., 120.), contacts=(), identifier="unit.r01"):
    return {"tick": tick, "own_entities": [{"entity_id": identifier,
        "position_m": list(position), "heading_deg": 90., "lifecycle_state": "active"}],
        "organic_contacts": list(contacts)}


def contact(position=(1100., 300., 220.), tick=3, token="opaque", **changes):
    return {"estimated_position_m": list(position), "observed_tick": tick,
        "confidence": .9, "age_ticks": 0, "contact_id": token,
        "observer_entity_id": "unit.r01", **changes}


def policy(mode="adaptive"):
    return ObservationSearchPolicy(reconnaissance(6)[1], "unit.r01", mode)


def survey(agent):
    for tick, point in enumerate(agent.search.waypoints, 1):
        agent.navigation(observation(tick, (*point, 120.)))


def test_adaptive_cannot_skip_public_survey_cells_to_chase_a_contact():
    adaptive, patrol = policy(), policy("patrol")
    obs = observation(3, contacts=[contact()])
    before = deepcopy(obs)
    assert adaptive.navigation(obs) == patrol.navigation(obs)
    assert adaptive.diagnostics()["phase"] == "survey"
    assert obs == before


def test_post_survey_navigation_uses_actual_measured_contact_not_future_plan():
    agent = policy(); survey(agent)
    obs = observation(3, (850., 300., 120.), [contact()])
    obs["future_plan"] = {"position": [-9000., -9000., 0.]}
    command = agent.navigation(obs)
    assert command["payload"] == {"speed_mps": 12., "heading_deg": 90., "altitude_m": 220.}
    assert agent.phase == "observe"


def test_token_renaming_and_observation_reordering_do_not_change_navigation():
    a, b = policy(), policy(); survey(a); survey(b)
    contacts = [contact(), contact((1150., 200., 220.), token="second")]
    changed = deepcopy(contacts[::-1])
    for i, row in enumerate(changed):
        row.update(contact_id=f"unrelated-{i}", hidden_role="feint", true_position_m=[0, 0, 0])
    assert a.navigation(observation(3, (850., 300., 120.), contacts)) == b.navigation(observation(3, (850., 300., 120.), changed))


@pytest.mark.parametrize("changes", [
    {"observed_tick": 4}, {"observed_tick": True}, {"observed_tick": 0},
    {"confidence": float("nan")}, {"confidence": 0},
    {"estimated_position_m": [float("inf"), 0, 0]},
    {"observer_entity_id": "foreign"},
])
def test_future_stale_foreign_and_malformed_contacts_never_drive_pursuit(changes):
    a, b = policy(), policy("patrol"); survey(a); survey(b)
    assert a.navigation(observation(3, (850., 300., 120.), [contact(**changes)])) == b.navigation(observation(3, (850., 300., 120.)))
    assert a.phase != "observe"


def test_lost_contact_memory_expires_and_never_creates_reports():
    agent = policy(); survey(agent)
    agent.navigation(observation(3, (850., 300., 120.), [contact()]))
    agent.navigation(observation(8, (850., 300., 120.)))
    assert agent.phase == "observe"
    assert agent.report(observation(9, (850., 300., 120.))) is None
    agent.navigation(observation(12, (850., 300., 120.)))
    assert agent.phase == "reacquire" and agent.last_contact is None


def test_range_hold_keeps_a_small_standoff_instead_of_orbiting_the_contact():
    agent = policy(); survey(agent)
    command = agent.navigation(observation(3, (1000., 300., 120.), [contact()]))
    assert command["payload"]["speed_mps"] == 0
    assert command["payload"]["altitude_m"] == 220


def test_controller_ownership_deadline_and_asset_loss_fail_closed():
    agent = policy()
    with pytest.raises(ValueError, match="another controller"):
        agent.navigation(observation(identifier="unit.r02"))
    assert agent.navigation({"tick": 1, "own_entities": []}) is None
    assert agent.navigation(observation(tick=240)) is None
    obs = observation(); obs["own_entities"][0]["lifecycle_state"] = "destroyed"
    assert agent.navigation(obs) is None


def test_matched_patrol_control_uses_identical_fixed_settings():
    brief = reconnaissance(6)[1]
    a, b = (ObservationSearchPolicy(brief, "unit.r02", mode) for mode in ("patrol", "adaptive"))
    obs = observation(identifier="unit.r02", position=(0., -350., 0.))
    assert a.settings == b.settings == SETTINGS
    assert a.navigation(obs) == b.navigation(obs)
    assert a.navigation(observation(2, identifier="unit.r02", position=(2., -350., 0.)))["payload"]["speed_mps"] == 8.0


@pytest.mark.parametrize("mode", ["patrol", "adaptive"])
def test_both_controls_respect_the_declared_altitude_envelope(mode):
    agent = policy(mode)
    command = agent.navigation(observation(position=(0., 350., 400.)))
    assert command["payload"]["altitude_m"] == SETTINGS["maximum_altitude_m"]


def test_negative_observation_time_cannot_be_treated_as_recent():
    agent = policy()
    assert agent._contact(observation(0, contacts=[contact(tick=-1)]), (0., 350., 120.)) is None


def test_fixed_speeds_and_altitude_are_inside_existing_candidate_dynamics_limits():
    from tools.competition_four_categories.build import candidate_catalog
    resources = {r["id"]: r["content"] for r in candidate_catalog()["resources"]}
    assert SETTINGS["air_speed_mps"] <= resources["dynamics.interceptor-uav"]["max_speed_mps"]
    assert SETTINGS["surface_speed_mps"] <= resources["dynamics.competition-picket-usv"]["max_speed_mps"]
    assert SETTINGS["maximum_altitude_m"] <= resources["dynamics.interceptor-uav"]["max_altitude_m"]

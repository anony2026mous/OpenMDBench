from copy import deepcopy
import math

import pytest

from tools.competition_four_categories.approach_screen_policy import ApproachScreenPolicy
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.screen_guard_policy import SETTINGS, ScreenGuardPolicy
from tools.competition_four_categories.tests.test_screen_guard import contact, observation


def make(brief=None):
    return ApproachScreenPolicy(brief or denial(6)[1], "unit.r03")


def test_parallel_inbound_tracks_do_not_pull_station_to_the_current_northern_contact():
    agent = make()
    for tick in (1, 2):
        agent.navigation(observation(tick, [contact(tick, (800. - 6 * tick, 850., 0.))]))
    goal = agent.navigation_log[-1]["goal_m"]
    assert goal[0] > 0 and abs(goal[1]) < 1e-8
    assert agent.axis == (1., 0.)
    assert all(math.dist(goal, p) <= .9 * 1000 for p in agent.centres)
    old = ScreenGuardPolicy(denial(6)[1], "unit.r03", "screen-salvo")
    old.navigation(observation(2, [contact(2, (788., 850., 0.))]))
    assert old.navigation_log[-1]["goal_m"][1] > 0


def test_geometry_and_observation_translation_preserves_relative_command():
    brief = denial(6)[1]
    moved = deepcopy(brief)
    shift = (1300., -700.)
    for zone in moved["protected_zones"]:
        for point in zone["coordinates_m"]:
            for i in (0, 1):
                point[i] += shift[i]
    a, b = make(brief), make(moved)
    for tick in (1, 2):
        obs = observation(tick, [contact(tick, (800. - 6 * tick, 850., 0.))])
        other = deepcopy(obs)
        for point in (other["own_entities"][0]["position_m"], other["organic_contacts"][0]["estimated_position_m"]):
            for i in (0, 1):
                point[i] += shift[i]
        assert a.navigation(obs) == b.navigation(other)


def test_token_renaming_order_and_extra_referee_data_do_not_change_commands():
    a, b = make(), make()
    for tick in (1, 2, 3):
        obs = observation(tick, [contact(tick, (800. - 6 * tick, 850., 0.), "north"),
                                 contact(tick, (700. - 5 * tick, -850., 0.), "south")])
        other = deepcopy(obs)
        for row in other["organic_contacts"]:
            row["contact_id"] = {"north": "opaque.27", "south": "opaque.93"}[row["contact_id"]]
            row["hidden_role"] = "private"
        other["organic_contacts"].reverse()
        other.update(referee_blue_states={"secret": [1, 2, 3]}, future_wave_plan=[99])
        assert a.navigation(obs) == b.navigation(other)


@pytest.mark.parametrize("change", ["stationary", "outbound", "crossing", "stale", "future", "foreign", "air", "nan"])
def test_unusable_or_nonincoming_contacts_do_not_choose_axis(change):
    agent = make()
    for tick in (1, 2):
        point = [800. - 6 * tick, 850., 0.]
        if change == "stationary": point[0] = 800.
        if change == "outbound": point[0] = 800. + 6 * tick
        if change == "crossing": point[1] = 2000.
        if change == "air": point[2] = 200.
        if change == "nan": point[0] = float("nan")
        row = contact(tick, point)
        if change == "stale": row["observed_tick"] = tick - 4
        if change == "future": row["observed_tick"] = tick + 1
        if change == "foreign": row["observer_entity_id"] = "foreign"
        agent.navigation(observation(tick, [row]))
    assert agent.axis is None


def test_original_weapon_decisions_and_public_settings_are_unchanged():
    new, old = make(), ScreenGuardPolicy(denial(6)[1], "unit.r03", "screen-salvo")
    for tick in range(1, 50):
        obs = observation(tick, [contact(tick, (600. - 6 * tick, 0., 0.))])
        before = deepcopy(obs)
        command = new.navigation(obs)
        assert command["payload"]["speed_mps"] <= SETTINGS["navigation_speed_fraction"] * new.asset["maximum_navigation_speed_mps"]
        assert new.action(obs) == old.action(obs)
        assert obs == before
    assert new.weapon.decisions == old.weapon.decisions


def test_approach_experiment_binds_both_policy_sources():
    from tools.competition_four_categories.audit import denial_extension_sources
    from tools.competition_four_categories.validate_tracking import sha
    from tools.competition_four_categories import approach_screen_policy, screen_guard_policy
    bindings = denial_extension_sources("approach-salvo")
    assert bindings["policy_source_sha256"] == sha(approach_screen_policy.__file__)
    assert bindings["screen_base_policy_sha256"] == sha(screen_guard_policy.__file__)
    assert bindings["screen_settings"] == SETTINGS

from copy import deepcopy

import pytest

from tools.competition_four_categories.progress_response_policy import ProgressResponsePolicy, SETTINGS
from tools.competition_four_categories.response import response
from tools.competition_four_categories.response_policy import center
from tools.competition_four_categories.tests.test_standing_response import observation


def agent():
    brief = response(6)[1]
    obj = ProgressResponsePolicy(brief, "unit.r01")
    duty = next(t for t in brief["initial_requests"] if "unit.r01" in t["observer_ids"])
    point = (*center(duty["destination"]), 100.)
    for tick in (1, 2, 3): obj.command(observation("unit.r01", tick, point))
    return obj, point


def test_stable_owned_velocity_updates_gain_without_weather_truth():
    obj, point = agent()
    obj.previous_command = obj.older_command = 22.
    obj.previous_speed = 14.3
    obs = observation("unit.r01", 4, point); obs["own_entities"][0]["velocity_mps"] = [14.3, 0., 0.]
    command = obj.command(obs)
    assert obj.motion_gain == pytest.approx(.825)
    assert obj.gain_samples == 1
    assert 22. < command["speed_mps"] <= SETTINGS["maximum_command_speed_mps"]


@pytest.mark.parametrize("velocity", [None, [float("nan"), 0., 0.], [0., 0., 0.]])
def test_missing_or_stationary_velocity_is_not_evidence_of_attenuation(velocity):
    obj, point = agent(); obj.previous_command = obj.older_command = 22.; obj.previous_speed = 14.3
    obs = observation("unit.r01", 4, point)
    if velocity is not None: obs["own_entities"][0]["velocity_mps"] = velocity
    obj.command(obs)
    assert obj.motion_gain == 1. and obj.gain_samples == 0


def test_acceleration_transients_do_not_become_weather_estimates():
    obj, point = agent(); obj.previous_command = 22.; obj.older_command = 8.; obj.previous_speed = 0.
    obs = observation("unit.r01", 4, point); obs["own_entities"][0]["velocity_mps"] = [14.3, 0., 0.]
    obj.command(obs)
    assert obj.motion_gain == 1. and obj.gain_samples == 0


def test_hidden_weather_or_future_event_fields_do_not_change_the_control():
    a, point = agent(); b, _ = agent()
    obs = observation("unit.r01", 4, point); obs["own_entities"][0]["velocity_mps"] = [14.3, 0., 0.]
    other = deepcopy(obs); other.update(weather_truth={"speed_scale": .01}, future_events=["fake"])
    assert a.command(obs) == b.command(other)
    assert a.motion_gain == b.motion_gain


def test_compensation_never_exceeds_existing_native_air_speed_limit():
    from tools.competition_four_categories.build import candidate_catalog
    obj, point = agent(); obj.motion_gain = SETTINGS["minimum_gain"]
    command = obj.command(observation("unit.r01", 4, point))
    native = next(r["content"] for r in candidate_catalog()["resources"] if r["id"] == "dynamics.interceptor-uav")
    assert command["speed_mps"] <= SETTINGS["maximum_command_speed_mps"] <= native["max_speed_mps"]

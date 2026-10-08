"""Unit checks for the declared standing task, not native acceptance evidence."""
from copy import deepcopy
import json

import pytest

from tools.competition_four_categories.response import response
from tools.competition_four_categories.response_policy import ResponsePolicy, center
from tools.competition_four_categories.standing_response_policy import StandingResponsePolicy, SETTINGS


def observation(identifier, tick, position, messages=(), contacts=()):
    return {"tick": tick, "own_entities": [{"entity_id": identifier, "position_m": list(position)}],
            "received_messages": list(messages), "organic_contacts": list(contacts)}


def make(identifier="unit.r01"):
    _, brief, _, plan = response(6)
    agent = StandingResponsePolicy(brief, identifier)
    duty = next(t for t in brief["initial_requests"] if identifier in t["observer_ids"])
    point = (*center(duty["destination"]), 100.)
    for tick in (1, 2, 3): agent.command(observation(identifier, tick, point))
    bodies = {}
    for item in plan["messages"]:
        body = json.loads(item["message"])
        if body["status"] == "confirmed": bodies[body["request_id"]] = body
    messages = [{"message_id": f"delivered.{key}", "sender_entity_id": "unit.r03",
        "recipient_controller_slots": [f"slot.{identifier}"], "sent_tick": 3, "delivered_tick": 4,
        "expiry_tick": 240, "payload": json.dumps(body)} for key, body in bodies.items()]
    return agent, brief, bodies, messages


def test_initial_duty_is_not_skipped_for_surveillance():
    brief = response(6)[1]
    old, new = ResponsePolicy(brief, "unit.r01", "coordinated"), StandingResponsePolicy(brief, "unit.r01")
    obs = observation("unit.r01", 1, (0., 0., 100.))
    assert old.command(obs) == new.command(obs)
    assert new.phase == "initial"


def test_completed_incident_does_not_reassign_responder_onto_its_peers_task():
    agent, _, bodies, messages = make()
    primary = max(bodies.values(), key=lambda r: r["priority"])
    point = (*center(primary["destination"]), 100.)
    for tick in (4, 5, 6): agent.command(observation("unit.r01", tick, point, messages))
    assert primary["request_id"] in agent.completed
    assert all(key not in agent.completed for key in bodies if key != primary["request_id"])
    assert agent.phase == "standing_watch"
    assert agent.watch_key[0] == "watch"


def test_second_responder_keeps_the_other_task_assignment():
    agent, _, bodies, messages = make("unit.r02")
    secondary = min(bodies.values(), key=lambda r: r["priority"])
    agent.command(observation("unit.r02", 4, (-100., 300., 100.), messages))
    assert agent.watch_key == ("incident", secondary["request_id"])
    assert agent.phase == "incident"


def test_untrusted_notice_cannot_create_an_incident_or_cancel_the_watch():
    a, _, _, messages = make(); b, _, _, _ = make()
    for message in messages: message["sender_entity_id"] = "untrusted"
    assert a.command(observation("unit.r01", 4, (-100., -100., 100.), messages)) == b.command(observation("unit.r01", 4, (-100., -100., 100.)))
    assert a.phase == "standing_watch"


def test_sensor_token_names_and_extra_hidden_fields_do_not_change_navigation():
    a, _, _, _ = make(); b, _, _, _ = make()
    contact = {"contact_id": "opaque.one", "estimated_position_m": [1200., 0., 0.], "observed_tick": 4, "confidence": .9}
    obs = observation("unit.r01", 4, (1100., 0., 100.), contacts=[contact])
    altered = deepcopy(obs); altered["organic_contacts"][0].update(contact_id="other.spelling", hidden_role="decoy")
    altered["future_plan"] = {"destination": [9000., 9000.]}
    assert a.command(obs) == b.command(altered)
    assert a.watch_contact == b.watch_contact


@pytest.mark.parametrize("when", [-1, 5, True])
def test_negative_future_and_boolean_contact_times_do_not_drive_the_watch(when):
    agent, _, _, _ = make()
    contact = {"estimated_position_m": [1200., 0., 0.], "observed_tick": when}
    agent.command(observation("unit.r01", 4, (1100., 0., 100.), contacts=[contact]))
    assert agent.watch_contact is None


def test_other_response_scenarios_keep_the_original_policy_behavior():
    brief = response(3)[1]
    old, new = ResponsePolicy(brief, "unit.r01", "coordinated"), StandingResponsePolicy(brief, "unit.r01")
    for tick in (1, 2):
        obs = observation("unit.r01", tick, (0., 0., 100.))
        assert old.command(obs) == new.command(obs)


def test_known_world_and_action_limits_are_respected():
    agent, _, _, _ = make()
    command = agent.command(observation("unit.r01", 4, (-100., -100., 100.)))
    assert 0 <= command["speed_mps"] <= SETTINGS["maximum_speed_mps"] == 22.
    assert command["altitude_m"] == SETTINGS["watch_altitude_m"]
    with pytest.raises(ValueError, match="another controller"):
        agent.command(observation("foreign", 5, (0., 0., 100.)))

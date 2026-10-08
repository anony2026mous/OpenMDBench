from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tools.competition_four_categories.build import zone
from tools.competition_four_categories.delivered_dispatch_v1 import DeliveredDispatchMetricV1, PROTOCOL, contract_hash
from tools.competition_four_categories.message_policy import ScheduledMessagePolicy, sample_schedule
from tools.competition_four_categories.response import response
from tools.competition_four_categories.response_policy import ResponsePolicy


def body(status="confirmed"):
    return {"schema_version": PROTOCOL, "request_id": "task.a", "status": status,
        "destination": zone("goal", 100., 0., 20.), "caution_regions": [zone("caution", 50., 0., 10.)],
        "observer_ids": ["own.a", "own.b"], "deadline_tick": 20, "dwell_ticks": 2, "priority": 2}


def plugin(kind="arrival_fraction", initially_known=False):
    p = DeliveredDispatchMetricV1()
    p.bind_session(session_id="unit", seed=601, parameters={"metric_id": "metric.test", "kind": kind,
        "requests": [{"request_id": "task.a", "zone_id": "goal", "deadline_tick": 20, "weight": 1.,
            "dwell_ticks": 2, "observer_ids": ["own.a", "own.b"], "initially_known": initially_known,
            "required": True, "contract_sha256": contract_hash(body()), "caution_zone_ids": ["caution"]}],
        "hazards": [{"zone_id": "hazard", "activation_event_id": "storm"}],
        "source_ids": ["source"], "observer_slots": {"own.a": "slot.a", "own.b": "slot.b"},
        "start_tick": 1, "end_tick": 21, "unit": "1"})
    return p


def delivery(status="confirmed", **changes):
    return {"message_id": "notice.1/a", "sender_entity_id": "source", "recipient_entity_id": "own.a",
        "recipient_controller_slots": ["slot.a"], "generated_tick": 1, "delivered_tick": 2,
        "expiry_tick": 10, "transport_status": "delivered", "payload": json.dumps(body(status)), **changes}


def snap(tick, messages=(), positions=None, events=(), inactive=()):
    return SimpleNamespace(tick=tick, communications=messages, event_ids=events,
        entity_states={o: {"lifecycle": "disabled" if o in inactive else "active"} for o in ("own.a", "own.b")},
        zone_membership=positions or {}, zone_activation={z: True for z in ("goal", "caution", "hazard")})


def value(p, s):
    return p.evaluate(s)["metric.test"]


def test_global_event_or_queued_message_cannot_release_a_task():
    p = plugin()
    for tick in range(1, 5):
        assert value(p, snap(tick, [delivery(transport_status="queued")], {"own.a": ["goal"]}, ["task.a"])) == 0
    assert p.notices["task.a"] == {}


def test_delivery_to_one_receiver_does_not_credit_an_unnotified_teammate():
    p = plugin(); value(p, snap(1))
    for tick in (2, 3):
        assert value(p, snap(tick, [delivery()], {"own.b": ["goal"]})) == 0
    assert value(p, snap(4, [delivery()], {"own.a": ["goal"]})) == 0
    assert value(p, snap(5, [delivery()], {"own.a": ["goal"]})) == 1
    assert p.arrivals["task.a"] == {"tick": 5, "observer_id": "own.a", "eligible_tick": 2, "delivered_tick": 2, "latency_ticks": 3}


@pytest.mark.parametrize("changes", [{"sender_entity_id": "intruder"}, {"recipient_controller_slots": ["wrong"]},
    {"recipient_entity_id": "other"}, {"transport_status": "blocked"}, {"transport_status": "expired"},
    {"expiry_tick": 1}, {"delivered_tick": 6}, {"payload": "bad-json"}])
def test_wrong_sender_scope_or_invalid_transport_cannot_award_response(changes):
    p = plugin(); value(p, snap(1))
    for tick in (2, 3, 4):
        assert value(p, snap(tick, [delivery(**changes)], {"own.a": ["goal"]})) == 0


def test_body_cannot_change_destination_or_deadline_behind_the_task_contract():
    bad = body(); bad["destination"]["coordinates_m"][0][0] += 100
    p = plugin(); value(p, snap(1))
    for tick in (2, 3):
        assert value(p, snap(tick, [delivery(payload=json.dumps(bad))], {"own.a": ["goal"]})) == 0


def test_unverified_notice_and_retraction_never_count_as_completion():
    p = plugin(); value(p, snap(1))
    for tick in (2, 3):
        assert value(p, snap(tick, [delivery("unverified")], {"own.a": ["goal"]})) == 0
    cancel = delivery("cancelled", message_id="notice.2/a", generated_tick=3, delivered_tick=4)
    assert value(p, snap(4, [delivery("unverified"), cancel], {"own.a": ["goal"]})) == 0
    assert p.notices["task.a"]["own.a"]["status"] == "cancelled"


def test_stale_confirmation_delivered_later_cannot_undo_newer_cancellation():
    p = plugin(); value(p, snap(1))
    cancellation = delivery("cancelled", message_id="new", generated_tick=2, delivered_tick=2)
    value(p, snap(2, [cancellation]))
    stale = delivery(message_id="old", generated_tick=1, delivered_tick=3)
    value(p, snap(3, [cancellation, stale], {"own.a": ["goal"]}))
    assert p.notices["task.a"]["own.a"]["status"] == "cancelled"
    assert not p.arrivals


def test_retransmission_does_not_reset_eligibility_or_latency():
    p = plugin(); value(p, snap(1)); value(p, snap(2, [delivery()]))
    again = delivery(message_id="repeat", generated_tick=3, delivered_tick=3)
    value(p, snap(3, [delivery(), again], {"own.a": ["goal"]}))
    assert value(p, snap(4, [delivery(), again], {"own.a": ["goal"]})) == 1
    assert p.arrivals["task.a"]["delivered_tick"] == 2
    assert p.arrivals["task.a"]["latency_ticks"] == 2


def test_initial_public_duty_is_not_fabricated_as_a_delivered_message():
    p = plugin(initially_known=True)
    value(p, snap(1, positions={"own.a": ["goal"]}))
    assert value(p, snap(2, positions={"own.a": ["goal"]})) == 1
    assert p.arrivals["task.a"]["delivered_tick"] is None and not p.seen_messages


def test_cancelled_during_dwell_resets_uncompleted_response():
    p = plugin(); value(p, snap(1)); value(p, snap(2, [delivery()], {"own.a": ["goal"]}))
    cancel = delivery("cancelled", message_id="cancel", generated_tick=3, delivered_tick=3)
    assert value(p, snap(3, [delivery(), cancel], {"own.a": ["goal"]})) == 0
    assert not p.dwell["task.a"]


def test_triage_uses_actual_entry_after_notice_not_existing_occupancy():
    p = plugin("triage_discipline"); value(p, snap(1))
    msg = delivery("unverified")
    assert value(p, snap(2, [msg], {"own.a": ["caution"]})) == 1
    assert value(p, snap(3, [msg], {"own.a": ["caution"]})) == 1
    value(p, snap(4, [msg]))
    assert value(p, snap(5, [msg], {"own.a": ["caution"]})) == 0
    assert p.unverified_entries == 1


def test_hazard_requires_native_activation_and_a_capable_responder():
    p = plugin("route_safety")
    assert value(p, snap(1, positions={"own.a": ["hazard"]})) == 1
    assert value(p, snap(2, positions={"own.a": ["hazard"]}, events=["storm"], inactive=["own.a"])) == 1
    assert value(p, snap(3, positions={"own.a": ["hazard"]}, events=["storm"])) == 0


def test_checkpoint_preserves_partial_dwell_and_delivered_provenance():
    a, b = plugin(), plugin(); value(a, snap(1)); value(a, snap(2, [delivery()], {"own.a": ["goal"]}))
    state = a.snapshot(); b.restore(state)
    assert a.snapshot() == b.snapshot()
    for tick in (3, 4):
        current = snap(tick, [delivery()], {"own.a": ["goal"]})
        assert value(a, current) == value(b, current)
        assert a.snapshot() == b.snapshot()
    again = a.snapshot(); value(a, current); assert a.snapshot() == again
    with pytest.raises(ValueError, match="conflicting"):
        value(a, snap(4))
    assert a.snapshot() == again


def test_checkpoint_rejects_missing_delivery_and_synthetic_arrival():
    p = plugin(); value(p, snap(1)); value(p, snap(2, [delivery()], {"own.a": ["goal"]}))
    value(p, snap(3, [delivery()], {"own.a": ["goal"]}))
    state = p.snapshot(); state["seen_messages"].clear()
    with pytest.raises(ValueError, match="provenance"):
        plugin().restore(state)
    state = p.snapshot(); state["arrivals"]["task.a"]["delivered_tick"] = None
    with pytest.raises(ValueError, match="public-brief"):
        plugin().restore(state)


def test_source_schedule_is_private_owned_and_never_emits_future_messages():
    _, brief, _, plan = response(5)
    policy = ScheduledMessagePolicy(plan)
    def obs(t): return {i: {"tick": t, "own_entities": [{"entity_id": i}]} for i in plan["controller_slots"]}
    assert not policy.actions(0, obs(0))
    tick = plan["messages"][0]["send_tick"]
    assert policy.actions(tick, obs(tick))
    bad = obs(tick); next(iter(bad.values()))["own_entities"][0]["entity_id"] = "unowned"
    with pytest.raises(ValueError, match="another controller"):
        policy.actions(tick, bad)
    assert "messages" not in brief and "send_tick" not in json.dumps(brief)


def test_seeded_notice_times_are_reproducible_bounded_and_genuinely_variable():
    plan = response(5)[3]
    base = {r["message_id"]: r["send_tick"] for r in plan["messages"]}
    realized = sample_schedule(plan, seed=601, maximum_shift_ticks=3)
    assert realized == sample_schedule(plan, seed=601, maximum_shift_ticks=3)
    assert all(abs(r["send_tick"]-base[r["message_id"]]) <= 3 for r in realized["messages"])
    assert len({tuple(r["send_tick"] for r in sample_schedule(plan, seed=s, maximum_shift_ticks=3)["messages"]) for s in range(10)}) > 1
    assert sample_schedule(plan, seed=0, maximum_shift_ticks=0) == plan


@pytest.mark.parametrize("number", [3, 5, 6])
def test_new_response_contract_requires_initial_duties_and_real_source_plan(number):
    package, brief, _, plan = response(number)
    metrics = package["scenario"]["scoring"]["metrics"]
    params = metrics[0]["plugin_parameters"]
    assert sum(r["initially_known"] for r in params["requests"]) == 2
    assert set(brief["responders"]).isdisjoint(plan["controller_slots"])
    assert not any(e["event_type"] == "message" for e in package["scenario"]["events"])
    assert any(r["send_tick"] == 45 for r in plan["messages"])
    if number == 6:
        assert brief["adjudication_tick"] == 241
        assert any(e["id"] == "event.receiver-blackout" for e in package["scenario"]["events"])


def test_responder_does_not_pool_another_receivers_inbox():
    _, brief, _, plan = response(5)
    identifier = brief["responders"][0]
    p = ResponsePolicy(brief, identifier, "coordinated")
    message = plan["messages"][0]
    observed = {"tick": 10, "own_entities": [{"entity_id": identifier, "position_m": [-100., -100., 100.]}],
        "received_messages": [{"message_id": "other-slot", "sender_entity_id": "unit.r03", "recipient_controller_slots": ["slot.unit.r02"],
            "sent_tick": 8, "delivered_tick": 9, "expiry_tick": 100, "payload": message["message"]}]}
    p.command(observed)
    assert set(p.tasks) == {"duty.01"}

from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from openmdbench.missions.engine_v2 import MissionContactFactV2
from tools.competition_four_categories.track_report_metrics_v1 import PROTOCOL, TrackReportMetricV1


def plugin(kind="delivered_coverage", **overrides):
    p = TrackReportMetricV1()
    parameters = {"metric_id": "metric.report", "kind": kind,
        "tracks": [{"track_id": "cue.a", "target_entity_id": "truth.a"}],
        "reporter_ids": ["own.a", "own.b"], "recipient_entity_id": "sink",
        "recipient_controller_slot": "slot.sink", "start_tick": 1, "end_tick": 9,
        "maximum_age_ticks": 4, "unit": "1", **overrides}
    p.bind_session(session_id="unit-test", seed=601, parameters=parameters)
    return p


def fact(contact="opaque.a", target="truth.a", owner="own.a", observed=0):
    return MissionContactFactV2(evidence_id=contact, owner_entity_id=owner, target_entity_id=target,
        observed_tick=observed, max_age_ticks=4, confidence=.9, minimum_confidence=.5, selector_id="native.owner")


def message(contact="opaque.a", track="cue.a", observed=0, generated=0, delivered=1, **changes):
    body = {"schema_version": PROTOCOL, "track_id": track, "contact_id": contact,
            "observed_tick": observed, "reported_tick": generated}
    return {"message_id": f"message.{contact}.{generated}", "sender_entity_id": "own.a",
            "recipient_entity_id": "sink", "recipient_controller_slots": ["slot.sink"],
            "generated_tick": generated, "delivered_tick": delivered, "expiry_tick": 20,
            "transport_status": "delivered", "payload": json.dumps(body), **changes}


def snapshot(tick, facts=(), messages=(), sink_state="active"):
    return SimpleNamespace(tick=tick, contact_facts=tuple(facts), communications=tuple(messages),
        entity_states={"sink": {"lifecycle": sink_state}, "own.a": {"lifecycle": "active"},
                       "own.b": {"lifecycle": "active"}})


def value(p, s):
    return p.evaluate(s)["metric.report"]


@pytest.mark.parametrize("kind,expected", [("delivered_coverage", 1.), ("identity_accuracy", 1.),
    ("identity_switch_rate", 0.), ("delivered_freshness", .8)])
def test_real_delivered_organic_reference_has_auditable_scores(kind, expected):
    p = plugin(kind)
    assert value(p, snapshot(0, [fact()])) is None
    assert value(p, snapshot(1, [fact()], [message()])) == pytest.approx(expected)


@pytest.mark.parametrize("kind,expected", [("delivered_coverage", 0.), ("delivered_freshness", 0.),
                                           ("identity_accuracy", None), ("identity_switch_rate", None)])
def test_detection_without_a_delivered_report_is_not_tracking_report_success(kind, expected):
    p = plugin(kind)
    for t in range(5):
        result = value(p, snapshot(t, [fact(observed=t)]))
    assert result == expected


@pytest.mark.parametrize("changes", [{"transport_status": "queued"}, {"transport_status": "blocked"},
    {"transport_status": "expired"}, {"sender_entity_id": "foreign"},
    {"recipient_entity_id": "other"}, {"recipient_controller_slots": ["slot.other"]},
    {"delivered_tick": 3}, {"expiry_tick": 0}])
def test_wrong_scope_or_not_delivered_never_creates_track_coverage(changes):
    p = plugin()
    value(p, snapshot(0, [fact()]))
    assert value(p, snapshot(1, [fact()], [message(**changes)])) == 0.


@pytest.mark.parametrize("contact,owner,observed", [("invented", "own.a", 0),
    ("opaque.a", "own.b", 0), ("opaque.a", "own.a", 1)])
def test_report_must_reference_the_senders_exact_authoritative_sample(contact, owner, observed):
    p = plugin("identity_accuracy")
    value(p, snapshot(0, [fact(owner=owner)]))
    assert value(p, snapshot(1, [fact(owner=owner)], [message(contact=contact, observed=observed)])) == 0.


def test_switched_identity_is_penalized_even_if_both_targets_remain_detected():
    p = plugin("identity_switch_rate")
    value(p, snapshot(0, [fact()]))
    newer = fact("opaque.b", "truth.b", observed=1)
    assert value(p, snapshot(1, [fact(), newer], [message()])) == 0.
    assert value(p, snapshot(2, [fact(), newer], [message(), message("opaque.b", observed=1, generated=1, delivered=2)])) == 1.
    assert p.switches == 1 and p.comparisons == 1
    assert p.correct_reports == 1 and p.total_reports == 2
    assert p.tracks["cue.a"]["covered_ticks"] == 1


def test_replaying_same_sample_cannot_inflate_accuracy_or_reset_information_age():
    p = plugin("delivered_freshness")
    value(p, snapshot(0, [fact()]))
    for tick in range(1, 6):
        messages = [message()] + [message(generated=t, delivered=t+1) for t in range(1, tick)]
        result = value(p, snapshot(tick, [fact()], messages))
    assert p.total_reports == p.correct_reports == 1
    assert p.tracks["cue.a"]["covered_ticks"] == 4
    assert result == pytest.approx(.4)


def test_post_deadline_report_cannot_rewrite_final_score_or_counters():
    p = plugin("identity_accuracy", end_tick=3)
    value(p, snapshot(0, [fact()]))
    value(p, snapshot(1, [fact()], [message()]))
    value(p, snapshot(2, [fact()], [message()]))
    assert value(p, snapshot(3, [fact()], [message(), message(contact="fake", generated=2, delivered=3)])) == 1.
    assert p.total_reports == 1


def test_expired_measurement_and_forged_report_clock_are_rejected():
    p = plugin("identity_accuracy", maximum_age_ticks=2)
    value(p, snapshot(0, [fact()]))
    value(p, snapshot(1, [fact()]))
    value(p, snapshot(2, [fact()]))
    assert value(p, snapshot(3, [fact()], [message(generated=2, delivered=3)])) == 0.
    q = plugin("identity_accuracy")
    value(q, snapshot(0, [fact()]))
    bad = message(); body = json.loads(bad["payload"]); body["reported_tick"] = 1; bad["payload"] = json.dumps(body)
    assert value(q, snapshot(1, [fact()], [bad])) == 0.


def test_native_first_score_at_one_does_not_invent_a_tick_zero_observation():
    p = plugin("identity_accuracy")
    assert value(p, snapshot(1, [fact()], [message()])) == 0.


def test_receiver_inactivity_stops_delivered_coverage():
    p = plugin()
    value(p, snapshot(0, [fact()]))
    assert value(p, snapshot(1, [fact()], [message()], sink_state="disabled")) == 0.


def test_same_tick_idempotence_reordering_and_conflicting_evidence():
    p = plugin()
    facts = [fact(), fact("opaque.b", "truth.b")]
    value(p, snapshot(0, facts))
    value(p, snapshot(1, facts, [message()]))
    before = p.snapshot()
    value(p, snapshot(1, list(reversed(facts)), [message()]))
    assert p.snapshot() == before
    with pytest.raises(ValueError, match="conflicting"):
        value(p, snapshot(1, facts, [message(contact="other")]))
    with pytest.raises(ValueError, match="every"):
        value(p, snapshot(3, facts))


def test_contact_ids_are_opaque_and_bijective_renaming_does_not_change_scores():
    for token in ["arbitrary-token", "unit.x999.feint", "no-identity-meaning"]:
        p = plugin("identity_accuracy")
        value(p, snapshot(0, [fact(token)]))
        assert value(p, snapshot(1, [fact(token)], [message(token)])) == 1.


def test_plugin_only_checkpoint_restore_preserves_history_and_replay_deduplication():
    p, q = plugin(), plugin()
    value(p, snapshot(0, [fact()]))
    value(p, snapshot(1, [fact()], [message()]))
    q.restore(json.loads(json.dumps(p.snapshot())))
    for t in range(2, 6):
        s = snapshot(t, [fact()], [message(), message(generated=1, delivered=2)])
        assert value(p, s) == value(q, s)
        assert p.snapshot() == q.snapshot()


@pytest.mark.parametrize("field,bad", [("samples", 99), ("correct_reports", 9), ("switches", 9),
                                    ("last_value", float("nan"))])
def test_inconsistent_plugin_checkpoints_are_rejected(field, bad):
    p = plugin(); value(p, snapshot(0, [fact()])); value(p, snapshot(1, [fact()], [message()]))
    state = deepcopy(p.snapshot()); state[field] = bad
    with pytest.raises(ValueError): plugin().restore(state)


def test_lowest_per_track_coverage_cannot_hide_an_unreported_target():
    p = plugin(tracks=[{"track_id": "cue.a", "target_entity_id": "truth.a"},
                       {"track_id": "cue.b", "target_entity_id": "truth.b"}])
    value(p, snapshot(0, [fact()]))
    assert value(p, snapshot(1, [fact()], [message()])) == 0.


def test_native_wrapped_track_bindings_are_accepted_without_changing_identity():
    p = plugin(tracks=[{"values": {"track_id": "cue.a", "target_entity_id": "truth.a"}}])
    assert p.parameters["tracks"] == [{"track_id": "cue.a", "target_entity_id": "truth.a"}]

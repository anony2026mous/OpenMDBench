from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tools.competition_four_categories.recon_metrics_v1 import ReconMetricV1
from tools.competition_four_categories.reconnaissance import group
from tools.competition_four_categories.tests.test_candidate_metrics import fact


def plugin(kind="recall", groups=None):
    p = ReconMetricV1()
    p.bind_session(session_id="test", seed=601, parameters={
        "metric_id": "metric.test", "kind": kind, "unit": "1", "maximum_age_ticks": 8 if kind.startswith("delivered_") else 1,
        "groups": groups or [group("g1", ["own.one", "own.two"], ["target.one"], 1, 7),
                             group("g2", ["own.one", "own.two"], ["target.two"], 1, 7)],
        "delivery": {"recipient_entity_id": "receiver", "recipient_controller_slot": "slot.receiver"} if kind.startswith("delivered_") else None})
    return p


def snap(tick, facts=(), zones=None, activation=None, messages=(), states=None):
    return SimpleNamespace(tick=tick, contact_facts=tuple(facts), communications=tuple(messages),
        zone_membership=zones or {}, zone_activation=activation or {},
        entity_states=states or {i: {"lifecycle": "active"} for i in ("own.one", "own.two", "receiver")})


def result(p, snapshot):
    return p.evaluate(snapshot)["metric.test"]


def message(token="contact.own.one.target.one", observed=1, **changes):
    row = {"message_id": "message.01", "sender_entity_id": "own.one", "recipient_entity_id": "receiver",
        "recipient_controller_slots": ["slot.receiver"], "transport_status": "delivered",
        "generated_tick": 2, "delivered_tick": 4, "expiry_tick": 10,
        "payload": json.dumps({"schema_version": "competition-contact-report@1.0",
                              "contacts": [{"contact_id": token, "observed_tick": observed}]})}
    return {**row, **changes}


def test_worst_group_recall_cannot_sacrifice_a_sector_or_domain():
    p = plugin()
    assert result(p, snap(1, [fact(), fact(owner="own.two")])) == 0
    assert result(p, snap(2, [fact("target.two", tick=2)])) == 1
    assert p.groups["g1"]["items"]["target.one"]["fresh_samples"] == 1


def test_zone_coverage_requires_every_sector_and_active_observers():
    p = plugin("coverage")
    active = {"target.one": True, "target.two": True}
    assert result(p, snap(1, zones={"own.one": ["target.one"]}, activation=active)) == 0
    assert result(p, snap(2, zones={"own.two": ["target.two"]}, activation=active,
                         states={"own.two": {"lifecycle": "disabled"}})) == 0
    assert result(p, snap(3, zones={"own.two": ["target.two"]}, activation=active)) == 1


def test_missing_zone_evidence_is_an_error_not_assumed_active():
    with pytest.raises(ValueError, match="activation evidence"):
        result(plugin("coverage"), snap(1))


def test_future_wave_is_unavailable_and_pre_event_contacts_do_not_count():
    p = plugin(groups=[group("wave1", ["own.one"], ["target.one"], 1, 3),
                       group("wave2", ["own.one"], ["target.one"], 3, 7)])
    assert result(p, snap(1, [fact()])) is None
    assert result(p, snap(2, [fact(tick=2)])) is None
    assert result(p, snap(3, [fact(tick=2)])) == 0
    assert result(p, snap(4, [fact(tick=4)])) == 1


def test_information_age_grows_after_contact_loss_and_never_seen_stays_explicit():
    p = plugin("information_freshness")
    assert result(p, snap(1, [fact()])) == pytest.approx(5/6)
    assert result(p, snap(2)) == pytest.approx(4/6)
    row = p.groups["g2"]["items"]["target.two"]
    assert row["first_seen_tick"] is None and row["last_observed_tick"] is None
    assert row["maximum_gap"] == 2


def test_freshness_not_lifetime_recall_and_disabled_sensors_do_not_count():
    p = plugin("fresh_fraction")
    assert result(p, snap(1, [fact(), fact("target.two")])) == 1
    assert result(p, snap(2, [fact(tick=2), fact("target.two", tick=2)],
                         states={"own.one": {"lifecycle": "disabled"}})) == .5


def test_discovery_timeliness_records_real_first_available_tick():
    p = plugin("discovery_timeliness", [group("g", ["own.one"], ["target.one"], 1, 7)])
    assert result(p, snap(1)) == 0
    assert result(p, snap(2)) == 0
    assert result(p, snap(3, [fact(tick=3)])) == pytest.approx(1-2/6)
    assert p.groups["g"]["items"]["target.one"]["first_seen_tick"] == 3


def test_duplicate_search_effort_is_not_double_coverage():
    p = plugin("nonduplicate_effort", [group("g", ["own.one", "own.two"], ["cell"], 1, 7)])
    assert result(p, snap(1, zones={"own.one": ["cell"], "own.two": ["cell"]}, activation={"cell": True})) == .5
    assert p.groups["g"]["contributions"] == 2 and p.groups["g"]["duplicates"] == 1


def delivered_plugin():
    return plugin("delivered_recall", [group("g", ["own.one"], ["target.one"], 1, 7)])


def test_native_delivery_not_source_union_is_required_for_handoff():
    p = delivered_plugin()
    assert result(p, snap(1, [fact()])) == 0
    assert result(p, snap(2, messages=[message(transport_status="queued")])) == 0
    assert result(p, snap(3, messages=[message()])) == 0
    assert result(p, snap(4, messages=[message()])) == 1
    assert p.groups["g"]["items"]["target.one"]["first_seen_tick"] == 4


@pytest.mark.parametrize("changes", [
    {"transport_status": "blocked"}, {"transport_status": "dropped"}, {"expiry_tick": 3},
    {"recipient_entity_id": "wrong"}, {"recipient_controller_slots": ["slot.wrong"]},
    {"sender_entity_id": "own.two"}, {"generated_tick": 0}, {"delivered_tick": 5},
    {"payload": "not-json"}, {"payload": '{}'},
])
def test_wrong_undelivered_or_forged_reports_do_not_count(changes):
    p = delivered_plugin()
    result(p, snap(1, [fact()]))
    for tick in (2, 3):
        result(p, snap(tick))
    assert result(p, snap(4, messages=[message(**changes)])) == 0


def test_unobserved_or_wrong_timestamp_contact_report_never_counts():
    for body in [message(token="opaque.fake"), message(observed=2)]:
        p = delivered_plugin()
        result(p, snap(1, [fact()]))
        for tick in (2, 3):
            result(p, snap(tick))
        assert result(p, snap(4, messages=[body])) == 0


def test_delivered_checkpoint_preserves_inflight_provenance_and_is_session_local():
    a, b = delivered_plugin(), delivered_plugin()
    result(a, snap(1, [fact()]))
    result(a, snap(2))
    saved = a.snapshot()
    b.restore(saved)
    assert delivered_plugin().contact_history == {}
    for tick in (3, 4, 5):
        evidence = snap(tick, messages=[message()])
        assert result(a, evidence) == result(b, evidence)
        assert a.snapshot() == b.snapshot()
    before = a.snapshot()
    result(a, snap(5, messages=[message()]))
    assert a.snapshot() == before
    with pytest.raises(ValueError, match="conflicting"):
        result(a, snap(5))
    assert a.snapshot() == before


def test_deadline_is_exclusive_and_skipped_ticks_fail():
    p = plugin(groups=[group("g", ["own.one"], ["target.one"], 1, 3)])
    result(p, snap(1)); result(p, snap(2))
    assert result(p, snap(3, [fact(tick=3)])) == 0
    with pytest.raises(ValueError, match="every authoritative tick"):
        result(p, snap(5))


@pytest.mark.parametrize("field,value", [("samples", 0), ("duplicates", 99), ("contributions", -1)])
def test_tampered_checkpoint_counters_fail(field, value):
    p = plugin(); result(p, snap(1, [fact()]))
    state = p.snapshot(); state["groups"]["g1"][field] = value
    with pytest.raises(ValueError):
        plugin().restore(state)


def test_frozen_native_parameter_rows_are_normalized_without_losing_groups():
    a = plugin()
    parameters = deepcopy(a.parameters)
    parameters["groups"] = tuple({"values": r} for r in parameters["groups"])
    b = ReconMetricV1(); b.bind_session(session_id="frozen", seed=2, parameters=parameters)
    assert a.snapshot() == b.snapshot()


def test_never_seen_checkpoint_cannot_claim_perfect_information_freshness():
    p = plugin("information_freshness"); result(p, snap(1))
    state = p.snapshot()
    for row in state["groups"].values():
        for item in row["items"].values():
            item["maximum_gap"] = 0
    state["last_value"] = 1.
    with pytest.raises(ValueError, match="never-observed"):
        plugin("information_freshness").restore(state)


@pytest.mark.parametrize("field,value", [("last_value", False), ("last_input_hash", "fake")])
def test_checkpoint_scalar_types_and_fingerprint_are_checked(field, value):
    p = plugin(); result(p, snap(1))
    state = p.snapshot(); state[field] = value
    with pytest.raises(ValueError):
        plugin().restore(state)

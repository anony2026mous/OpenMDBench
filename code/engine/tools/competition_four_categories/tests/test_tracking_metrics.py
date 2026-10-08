from copy import deepcopy
from types import SimpleNamespace

import pytest

from openmdbench.missions.engine_v2 import MissionContactFactV2
from tools.competition_four_categories.tracking_metrics_v1 import TrackingMetricV1


def plugin(kind="continuity", targets=("target.one",), end=7):
    p = TrackingMetricV1()
    p.bind_session(session_id="tracking-unit", seed=601, parameters={"metric_id": "metric.test", "kind": kind,
        "observer_ids": ["own.a", "own.b"], "target_ids": list(targets),
        "observer_groups": [{"group_id": "air", "observer_ids": ["own.a"]},
                            {"group_id": "surface", "observer_ids": ["own.b"]}],
        "handover_edges": [{"from_group": "air", "to_group": "surface", "minimum_count": 1}],
        "reacquisition_events": [{"event_id": "event.first", "deadline_ticks": 1},
                                 {"event_id": "event.second", "deadline_ticks": 1}],
        "start_tick": 1, "end_tick": end, "maximum_age_ticks": 1, "maximum_gap_ticks": 2, "unit": "1"})
    return p


def contact(tick, owner="own.a", target="target.one", confidence=1.):
    return MissionContactFactV2(evidence_id=f"contact.{owner}.{target}", owner_entity_id=owner, target_entity_id=target,
        observed_tick=tick, max_age_ticks=3, confidence=confidence, minimum_confidence=.5, selector_id="selector.test")


def snap(tick, contacts=(), events=(), states=None):
    return SimpleNamespace(tick=tick, contact_facts=tuple(contacts), event_ids=tuple(events),
        entity_states=states if states is not None else {"own.a": {"lifecycle": "active"}, "own.b": {"lifecycle": "active"}})


def value(p, tick, contacts=(), events=(), states=None):
    return p.evaluate(snap(tick, contacts, events, states))["metric.test"]


def test_minimum_per_target_fraction_cannot_average_away_a_lost_target():
    p = plugin(targets=("target.one", "target.two"))
    # No sampled tick is N/A, distinct from a measured failure to see a target.
    assert value(p, 0) is None
    assert value(p, 1, [contact(1), contact(1, owner="own.b")]) == 0
    assert value(p, 2, [contact(2), contact(2, target="target.two")]) == .5
    assert p.snapshot()["targets"]["target.one"]["seen_ticks"] == 2


def test_stale_low_confidence_disabled_and_unauthorized_contacts_do_not_count():
    p = plugin()
    assert value(p, 1, [contact(1, confidence=.1), contact(1, owner="enemy")]) == 0
    assert value(p, 2, [contact(0)]) == 0
    assert value(p, 3, [contact(3)], states={"own.a": {"lifecycle": "disabled"}}) == 0


def test_gap_includes_initial_and_final_absence_and_latches_failure():
    p = plugin("gap_compliance")
    assert value(p, 1) == 1
    assert value(p, 2) == 1
    assert value(p, 3) == 0
    assert value(p, 4, [contact(4)]) == 0
    assert p.snapshot()["targets"]["target.one"]["longest_gap_ticks"] == 3


def test_handover_requires_actual_owner_change_not_overlapping_detections():
    p = plugin("handover_fraction")
    assert value(p, 1, [contact(1)]) == 0
    assert value(p, 2, [contact(2), contact(2, owner="own.b")]) == 0
    assert value(p, 3) == 0
    assert value(p, 4, [contact(4, owner="own.b")]) == 1
    state = p.snapshot()["targets"]["target.one"]
    assert state["handover_counts"] == {"air->surface": 1}
    assert state["handover_gaps"] == [1]


def test_wrong_direction_does_not_satisfy_handover_requirement():
    p = plugin("handover_fraction")
    value(p, 1, [contact(1, owner="own.b")])
    assert value(p, 2, [contact(2)]) == 0


def test_reacquisition_keeps_future_events_and_all_targets_in_denominator():
    p = plugin("reacquisition_fraction", targets=("target.one", "target.two"))
    assert value(p, 1, [contact(1)], ["event.first"]) == .25
    assert value(p, 2, [contact(2, target="target.two")], ["event.first"]) == .5
    assert value(p, 3, [contact(3), contact(3, target="target.two")], ["event.first", "event.second"]) == 1
    assert p.snapshot()["event_windows"]["event.first"]["reacquired"]["target.two"] == 1


def test_late_reacquisition_and_unrelated_target_do_not_satisfy_event():
    p = plugin("reacquisition_fraction")
    value(p, 1, [], ["event.first"])
    value(p, 2, [contact(2, target="unrelated")], ["event.first"])
    assert value(p, 3, [contact(3)], ["event.first"]) == 0


def test_freshness_penalizes_observation_age_and_missing_samples():
    p = plugin("freshness")
    assert value(p, 1, [contact(1)]) == 1
    assert value(p, 2, [contact(1)]) == .75
    assert value(p, 3) == .5


def test_deadline_freezes_tracking_history():
    p = plugin(end=3)
    value(p, 1, [contact(1)])
    assert value(p, 2, [contact(2)]) == 1
    before = p.snapshot()["targets"]
    assert value(p, 3) == 1
    assert p.snapshot()["targets"] == before


def test_repeated_tick_is_idempotent_but_conflict_skip_and_backwards_fail():
    p = plugin()
    value(p, 1, [contact(1)])
    before = p.snapshot()
    assert value(p, 1, [contact(1)]) == 1
    assert p.snapshot() == before
    with pytest.raises(ValueError, match="conflicting"):
        value(p, 1)
    with pytest.raises(ValueError, match="every authoritative"):
        value(p, 3)
    with pytest.raises(ValueError, match="backwards"):
        value(p, 0)


def test_checkpoint_preserves_partial_gap_handover_and_reacquisition():
    a = plugin()
    value(a, 1, [contact(1)])
    value(a, 2, [], ["event.first"])
    b = plugin()
    b.restore(a.snapshot())
    for p in (a, b):
        value(p, 3, [contact(3, owner="own.b")], ["event.first"])
    assert a.snapshot() == b.snapshot()
    corrupt = a.snapshot()
    corrupt["targets"]["target.one"]["seen_ticks"] = 100
    with pytest.raises(ValueError, match="counters"):
        b.restore(corrupt)


def test_native_frozen_record_adapter_and_session_isolation():
    a, b = plugin(), plugin()
    parameters = deepcopy(a.parameters)
    for key in ("observer_groups", "handover_edges", "reacquisition_events"):
        parameters[key] = [{"values": record} for record in parameters[key]]
    c = TrackingMetricV1()
    c.bind_session(session_id="native", seed=2, parameters=parameters)
    assert c.parameters == a.parameters
    value(a, 1, [contact(1)])
    assert b.snapshot()["samples"] == 0


@pytest.mark.parametrize("kind,field", [("handover_fraction", "handover_edges"), ("reacquisition_fraction", "reacquisition_events")])
def test_empty_requirements_are_not_vacuous_success(kind, field):
    parameters = plugin(kind).parameters
    parameters[field] = []
    with pytest.raises(ValueError):
        TrackingMetricV1().bind_session(session_id="invalid", seed=1, parameters=parameters)

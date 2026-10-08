from copy import deepcopy
from types import SimpleNamespace as N

import pytest

from tools.competition_four_categories.denial_metrics_v1 import DenialMetricV1


def plugin(kind="protection_fraction", zones=("zone.a", "zone.b"), end=7):
    p = DenialMetricV1()
    p.bind_session(session_id="denial-unit", seed=601, parameters={"metric_id": "metric.test", "kind": kind,
        "zone_ids": list(zones), "intruder_ids": ["target.a", "target.b"],
        "protected_entities": [{"entity_id": "traffic.a", "initial_health": 1.}],
        "start_tick": 1, "end_tick": end, "maximum_breaches_per_zone": 0, "unit": "1"})
    return p


def edge(tick, entity="target.a", zone="zone.a", transition="entered", identity=None):
    return N(tick=tick, entity_id=entity, zone_id=zone, transition=transition, evidence_hash=identity or f"edge-{entity}-{zone}-{transition}-{tick}")


def snap(tick, membership=None, transitions=(), activation=None, health=1., states=None):
    entities = {"target.a": {"lifecycle": "active", "health": 1.},
                "target.b": {"lifecycle": "scheduled", "health": 1.},
                "traffic.a": {"lifecycle": "active", "health": health}}
    if states is not None:
        entities = states
    return N(tick=tick, entity_states=entities, zone_membership=membership or {},
             zone_transitions=transitions, zone_activation=activation if activation is not None else {"zone.a": True, "zone.b": True})


def value(p, *args, **kwargs):
    return p.evaluate(snap(*args, **kwargs))["metric.test"]


def test_worst_zone_fraction_prevents_sacrificing_one_sector():
    p = plugin()
    assert value(p, 0) is None
    assert value(p, 1) == 1
    assert value(p, 2, {"target.a": ["zone.a"]}) == .5
    assert value(p, 3, {"target.a": ["zone.a"]}) == pytest.approx(1/3)
    assert p.snapshot()["zones"]["zone.b"]["safe_ticks"] == 3


def test_membership_and_transition_do_not_double_count_an_entry():
    p = plugin("breach_free")
    assert value(p, 1) == 1
    assert value(p, 2, {"target.a": ["zone.a"]}, [edge(2)]) == 0
    assert value(p, 3, {"target.a": ["zone.a"]}, [edge(2)]) == 0
    assert p.snapshot()["zones"]["zone.a"]["breaches"] == 1
    value(p, 4, {}, [edge(4, transition="exited")])
    value(p, 5, {"target.a": ["zone.a"]}, [edge(5)])
    assert p.snapshot()["zones"]["zone.a"]["breaches"] == 2
    assert p.snapshot()["zones"]["zone.a"]["first_breach_tick"] == 2


def test_intra_tick_transit_counts_even_if_no_final_occupancy():
    p = plugin()
    assert value(p, 1) == 1
    assert value(p, 2, {}, [edge(2), edge(2, transition="exited")]) == .5
    assert p.snapshot()["zones"]["zone.a"]["breaches"] == 1


def test_destroying_intruder_after_entry_cannot_erase_breach():
    p = plugin("breach_free")
    value(p, 1)
    states = {"target.a": {"lifecycle": "destroyed", "health": 0.}, "traffic.a": {"lifecycle": "active", "health": 1.}}
    assert value(p, 2, {}, [edge(2)], states=states) == 0
    assert value(p, 3, {}, [], states=states) == 0


def test_inactive_protection_zone_fails_and_missing_zone_fact_errors():
    p = plugin("breach_free")
    assert value(p, 1, activation={"zone.a": False, "zone.b": True}) == 0
    assert value(p, 2) == 0
    with pytest.raises(ValueError, match="activation facts"):
        value(plugin(), 1, activation={})


def test_protected_transit_is_not_enemy_breach_and_harm_latches():
    p = plugin("protected_integrity")
    assert value(p, 1, {"traffic.a": ["zone.a"]}, [edge(1, entity="traffic.a")]) == 1
    assert value(p, 2, health=.6) == .6
    assert value(p, 3, health=1.) == .6
    assert p.snapshot()["zones"]["zone.a"]["breaches"] == 0


def test_missing_protected_state_is_not_filled_with_zero():
    with pytest.raises(ValueError, match="protected entity state"):
        value(plugin("protected_integrity"), 1, states={"target.a": {"lifecycle": "active"}})


def test_destroyed_protected_entity_has_verified_zero_integrity():
    p = plugin("protected_integrity")
    assert value(p, 1, states={"traffic.a": {"lifecycle": "destroyed", "health": 0.}}) == 0


def test_deadline_freezes_even_if_a_later_intruder_arrives():
    p = plugin(end=3)
    value(p, 1)
    assert value(p, 2) == 1
    assert value(p, 3, {"target.a": ["zone.a"]}, [edge(3)], health=0.) == 1
    assert p.snapshot()["samples"] == 2


def test_idempotency_conflict_skip_and_rewind_checks():
    p = plugin()
    value(p, 1)
    before = p.snapshot()
    value(p, 1)
    assert p.snapshot() == before
    with pytest.raises(ValueError, match="conflicting"):
        value(p, 1, {"target.a": ["zone.a"]})
    with pytest.raises(ValueError, match="every authoritative"):
        value(p, 3)
    with pytest.raises(ValueError, match="backwards"):
        value(p, 0)


def test_checkpoint_retains_breach_history_and_transition_deduplication():
    a = plugin()
    value(a, 1)
    value(a, 2, {"target.a": ["zone.a"]}, [edge(2)], health=.7)
    b = plugin()
    b.restore(a.snapshot())
    for p in (a, b):
        value(p, 3, {"target.a": ["zone.a"]}, [edge(2)], health=.9)
    assert a.snapshot() == b.snapshot()
    assert b.snapshot()["zones"]["zone.a"]["breaches"] == 1
    broken = b.snapshot()
    broken["samples"] = 100
    with pytest.raises(ValueError, match="sample count"):
        b.restore(broken)


def test_native_frozen_record_adapter_and_no_shared_state():
    a, b = plugin(), plugin()
    parameters = deepcopy(a.parameters)
    parameters["protected_entities"] = [{"values": r} for r in parameters["protected_entities"]]
    c = DenialMetricV1()
    c.bind_session(session_id="native", seed=1, parameters=parameters)
    assert c.parameters == a.parameters
    value(a, 1, {"target.a": ["zone.a"]})
    assert b.snapshot()["samples"] == 0


def test_protected_integrity_cannot_be_vacuously_satisfied():
    parameters = plugin("protected_integrity").parameters
    parameters["protected_entities"] = []
    with pytest.raises(ValueError, match="real protected cohort"):
        DenialMetricV1().bind_session(session_id="empty", seed=1, parameters=parameters)

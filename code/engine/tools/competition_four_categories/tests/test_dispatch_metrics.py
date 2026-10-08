from copy import deepcopy
from types import SimpleNamespace

import pytest

from tools.competition_four_categories.dispatch_metrics_v1 import DispatchMetricV1
from tools.competition_four_categories.emergency import emergency
from tools.competition_four_categories.runtime import load_candidate_catalog
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2


def plugin(kind="arrival_fraction", second=False):
    requests = [{"request_id": "request.a", "zone_id": "zone.a",
                 "release_event_id": "event.release", "deadline_tick": 6,
                 "weight": 3., "dwell_ticks": 2, "observer_ids": ["asset.a", "asset.b"]}]
    if second:
        requests += [{**deepcopy(requests[0]), "request_id": "request.b",
                      "zone_id": "zone.b", "weight": 1., "release_event_id": "event.later"}]
    p = DispatchMetricV1()
    p.bind_session(session_id="test", seed=601, parameters={"metric_id": "metric.test",
        "kind": kind, "observer_ids": ["asset.a", "asset.b"], "requests": requests,
        "hazards": [{"zone_id": "zone.hazard", "activation_event_id": "event.weather"}],
        "start_tick": 1, "end_tick": 7, "unit": "1"})
    return p


def facts(tick, zones=None, events=(), states=None, activation=None):
    return SimpleNamespace(tick=tick, zone_membership=zones or {}, event_ids=events,
        entity_states=states if states is not None else {"asset.a": {"lifecycle": "active"},
                                                       "asset.b": {"lifecycle": "active"}},
        zone_activation=activation or {})


def value(p, *args, **kwargs):
    return p.evaluate(facts(*args, **kwargs))["metric.test"]


def test_release_dwell_and_future_request_denominator():
    p = plugin(second=True)
    assert value(p, 0) is None
    assert value(p, 1, {"asset.a": ["zone.a"]}) == 0
    assert value(p, 2, {"asset.a": ["zone.a"]}, ["event.release"]) == 0
    assert value(p, 3, {"asset.a": ["zone.a"]}, ["event.release"]) == .75
    assert p.snapshot()["arrivals"]["request.a"]["latency_ticks"] == 1


def test_dwell_cannot_splice_observers_or_survive_departure():
    p = plugin()
    assert value(p, 1, {"asset.a": ["zone.a"]}, ["event.release"]) == 0
    assert value(p, 2, {"asset.b": ["zone.a"]}, ["event.release"]) == 0
    assert value(p, 3, {}, ["event.release"]) == 0
    assert value(p, 4, {"asset.b": ["zone.a"]}, ["event.release"]) == 0
    assert value(p, 5, {"asset.b": ["zone.a"]}, ["event.release"]) == 1


def test_inactive_zone_disabled_and_unauthorized_assets_never_arrive():
    p = plugin()
    assert value(p, 1, {"asset.a": ["zone.a"]}, ["event.release"],
                 activation={"zone.a": False}) == 0
    assert value(p, 2, {"asset.a": ["zone.a"]}, ["event.release"],
                 states={"asset.a": {"lifecycle": "disabled"}}) == 0
    assert value(p, 3, {"other": ["zone.a"]}, ["event.release"],
                 states={"other": {"lifecycle": "active"}}) == 0


def test_hazard_is_event_gated_and_failure_latches():
    p = plugin("route_safety")
    assert value(p, 1, {"asset.a": ["zone.hazard"]}) == 1
    assert value(p, 2, {"asset.a": ["zone.hazard"]}, ["event.weather"]) == 0
    assert value(p, 3, {}, ["event.weather"]) == 0
    assert p.snapshot()["exposure_entity_ticks"] == 1


def test_deadline_is_inclusive_then_metric_freezes():
    p = plugin()
    for tick in range(1, 5):
        value(p, tick, {}, ["event.release"])
    assert value(p, 5, {"asset.a": ["zone.a"]}, ["event.release"]) == 0
    assert value(p, 6, {"asset.a": ["zone.a"]}, ["event.release"]) == 1
    assert value(p, 7, {"asset.a": ["zone.hazard"]}, ["event.weather"]) == 1
    late = plugin()
    for tick in range(1, 6):
        value(late, tick, {}, ["event.release"])
    assert value(late, 6, {"asset.a": ["zone.a"]}, ["event.release"]) == 0
    assert value(late, 7, {"asset.a": ["zone.a"]}, ["event.release"]) == 0


def test_timeliness_uses_first_release_and_does_not_reward_missing_requests():
    p = plugin("timeliness", second=True)
    value(p, 1)
    value(p, 2, {"asset.a": ["zone.a"]}, ["event.release"])
    assert value(p, 3, {"asset.a": ["zone.a"]}, ["event.release"]) == pytest.approx(.6)


def test_checkpoint_and_idempotency_preserve_partial_dwell():
    p = plugin()
    value(p, 1, {"asset.a": ["zone.a"]}, ["event.release"])
    saved = p.snapshot()
    assert value(p, 1, {"asset.a": ["zone.a"]}, ["event.release"]) == 0
    assert p.snapshot() == saved
    restored = plugin()
    restored.restore(saved)
    for candidate in (p, restored):
        assert value(candidate, 2, {"asset.a": ["zone.a"]}, ["event.release"]) == 1
    assert p.snapshot() == restored.snapshot()
    saved["arrivals"]["invalid"] = {}
    with pytest.raises(ValueError, match="identities"):
        restored.restore(saved)


def test_native_nested_frozen_record_parameter_adapter_preserves_values():
    original = plugin()
    params = deepcopy(original.parameters)
    for key in ("requests", "hazards"):
        params[key] = [{"values": record} for record in params[key]]
    adapted = DispatchMetricV1()
    adapted.bind_session(session_id="native", seed=601, parameters=params)
    assert adapted.parameters == original.parameters


@pytest.mark.parametrize("mutation", [
    lambda s: s["released"].update({"request.a": 99}),
    lambda s: s["dwell"]["request.a"].update({"unauthorized": 2}),
    lambda s: s.update(samples=999),
    lambda s: s["arrivals"].update({"request.a": {"tick": 1, "observer_id": "asset.a", "latency_ticks": 0}}),
])
def test_checkpoint_rejects_impossible_dispatch_history(mutation):
    p = plugin()
    value(p, 1, {"asset.a": ["zone.a"]}, ["event.release"])
    saved = p.snapshot()
    mutation(saved)
    with pytest.raises(ValueError):
        plugin().restore(saved)


def test_skipped_conflicting_and_backward_ticks_fail_closed():
    p = plugin()
    value(p, 1)
    with pytest.raises(ValueError, match="every scoring"):
        value(p, 3)
    with pytest.raises(ValueError, match="conflicting"):
        value(p, 1, {"asset.a": ["zone.a"]})
    with pytest.raises(ValueError, match="backward"):
        value(p, 0)


@pytest.mark.parametrize("number", range(1, 7))
def test_each_emergency_compiles_natively_with_finite_scoring_window(number):
    package, brief, acceptance = emergency(number)
    catalog = load_candidate_catalog(allow_candidate=True)
    resolved = ScenarioCompilerV2(catalog=catalog).compile(ScenarioPackageV2.from_mapping(package))
    assert resolved.world.duration_ticks == brief["adjudication_tick"]
    assert acceptance["competition_accepted"] is False
    assert brief["difficulty"] == "standard"
    assert "events" not in brief and "requests" not in brief
    if number in (3, 5, 6):
        assert brief["initial_requests"] == []


def test_six_event_and_metric_contracts_are_distinct():
    import json
    signatures = set()
    for number in range(1, 7):
        package, _, _ = emergency(number)
        s = package["scenario"]
        signatures.add(json.dumps([s["events"], s["scoring"]], sort_keys=True))
    assert len(signatures) == 6

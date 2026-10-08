"""Unmeasured values must stay unavailable; measured zero remains numeric."""
from copy import deepcopy
import importlib.util

import pytest

from tools.competition_four_categories import tracking_metrics_v1, delivered_dispatch_v1
from tools.competition_four_categories.build import ROOT
from tools.competition_four_categories.tests import test_tracking_metrics as tracking
from tools.competition_four_categories.tests import test_delivered_dispatch as dispatch

KINDS = ("continuity", "gap_compliance", "handover_fraction", "reacquisition_fraction", "freshness")
DISPATCH_KINDS = ("arrival_fraction", "timeliness", "route_safety", "triage_discipline")
ARCHIVE = ROOT/"artifacts/competition_four_categories/frozen_versions/calibration-plan-20260930T233933542581Z-complete"


def bind_window(model, start=3, end=8):
    parameters = deepcopy(model.parameters)
    parameters.update(start_tick=start, end_tick=end)
    model.bind_session(session_id="availability-fixture", seed=601, parameters=parameters)
    return parameters


def frozen_module(name):
    path = ARCHIVE/"tools/competition_four_categories"/f"{name}.py"
    assert path.is_file(), "the completed calibration source must remain available"
    spec = importlib.util.spec_from_file_location(f"tools.competition_four_categories._frozen_{name}_100", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", KINDS)
def test_tracking_before_window_is_unavailable_even_when_contacts_exist(kind):
    model = tracking.plugin(kind); parameters = bind_window(model)
    assert model.snapshot()["last_value"] is None
    for tick in (0, 1, 2):
        assert tracking.value(model, tick, [tracking.contact(tick)]) is None
        assert model.samples == 0
    assert all(x["seen_ticks"] == 0 for x in model.targets.values())
    restored = tracking_metrics_v1.TrackingMetricV1()
    restored.bind_session(session_id="restored", seed=601, parameters=parameters)
    restored.restore(model.snapshot())
    expected = 1.0 if kind == "gap_compliance" else 0.0
    assert tracking.value(restored, 3) == expected
    assert restored.samples == 1


@pytest.mark.parametrize("kind", DISPATCH_KINDS)
def test_dispatch_before_window_is_unavailable_and_restores_as_unavailable(kind):
    model = dispatch.plugin(kind); parameters = bind_window(model, end=21)
    assert model.snapshot()["last_value"] is None
    for tick in (0, 1, 2):
        assert dispatch.value(model, dispatch.snap(tick)) is None
        assert model.samples == 0
    restored = delivered_dispatch_v1.DeliveredDispatchMetricV1()
    restored.bind_session(session_id="restored", seed=601, parameters=parameters)
    restored.restore(model.snapshot())
    expected = 1.0 if kind in {"route_safety", "triage_discipline"} else 0.0
    assert dispatch.value(restored, dispatch.snap(3)) == expected


@pytest.mark.parametrize("kind", KINDS)
def test_tracking_in_window_outputs_and_history_match_frozen_calibration(kind):
    old = frozen_module("tracking_metrics_v1").TrackingMetricV1()
    new = tracking.plugin(kind); parameters = bind_window(new)
    old.bind_session(session_id="frozen", seed=601, parameters=parameters)
    for tick in range(10):
        contacts = [] if tick in (3, 6) else [tracking.contact(tick, owner="own.a" if tick < 5 else "own.b")]
        events = ("event.first",) if tick == 4 else ("event.second",) if tick == 7 else ()
        snapshot = tracking.snap(tick, contacts, events)
        before, after = old.evaluate(snapshot), new.evaluate(snapshot)
        if tick >= parameters["start_tick"]:
            assert after == before
            assert new.snapshot() == old.snapshot()


@pytest.mark.parametrize("kind", DISPATCH_KINDS)
def test_dispatch_in_window_outputs_match_frozen_calibration(kind):
    old = frozen_module("delivered_dispatch_v1").DeliveredDispatchMetricV1()
    new = dispatch.plugin(kind); parameters = bind_window(new, end=21)
    old.bind_session(session_id="frozen", seed=601, parameters=parameters)
    for tick in range(7):
        snapshot = dispatch.snap(tick) if tick < 3 else dispatch.snap(tick, [dispatch.delivery()], {"own.a": ["goal"]})
        before, after = old.evaluate(snapshot), new.evaluate(snapshot)
        if tick >= parameters["start_tick"]:
            assert after == before
            assert new.snapshot() == old.snapshot()


@pytest.mark.parametrize("kind", KINDS)
def test_tracking_restore_cannot_resurrect_a_zero_placeholder_before_sampling(kind):
    model = tracking.plugin(kind); bind_window(model)
    saved = model.snapshot(); saved["last_value"] = 0.0
    with pytest.raises(ValueError, match="unavailable"):
        model.restore(saved)


@pytest.mark.parametrize("value,status", [(0., "available"), (None, "available"), (0., "missing")])
def test_native_probe_rejects_prewindow_zero_or_wrong_status(value, status):
    from tools.competition_four_categories.validate_score_availability import receipt_violations
    assert receipt_violations(2, {"metric.x": value}, {"metric.x": status}, {"metric.x": 3})


def test_native_probe_distinguishes_missing_receipt_from_na_and_measured_zero():
    from tools.competition_four_categories.validate_score_availability import receipt_violations
    assert receipt_violations(2, {}, {}, {"metric.x": 3})
    assert not receipt_violations(2, {"metric.x": None}, {"metric.x": "missing"}, {"metric.x": 3})
    assert not receipt_violations(3, {"metric.x": 0.}, {"metric.x": "available"}, {"metric.x": 3})


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), -0.1, 1.1])
def test_native_probe_rejects_invalid_sampled_fractions(value):
    from tools.competition_four_categories.validate_score_availability import receipt_violations
    assert receipt_violations(3, {"metric.x": value}, {"metric.x": "available"}, {"metric.x": 3})

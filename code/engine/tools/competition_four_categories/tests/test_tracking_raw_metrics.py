from copy import deepcopy
import pytest

from tools.competition_four_categories.tracking_raw_metrics import tracking_statistics, report_statistics, temporal_statistics
from tools.competition_four_categories.tests.test_tracking_metrics import plugin as tracking_plugin, value
from tools.competition_four_categories.tests.test_track_report_metrics import plugin as report_plugin, snapshot


def test_gap_compliance_zero_is_not_zero_gap_and_missing_age_is_not_zero():
    model = tracking_plugin("gap_compliance")
    for tick in range(1, 7): value(model, tick)
    raw = tracking_statistics(model.snapshot(), .5); target = raw["targets"]["target.one"]
    assert raw["native_candidate_score_value"] == 0
    assert target["longest_contact_gap_ticks"] == 6 and target["longest_contact_gap_seconds"] == 3
    assert target["fresh_contact_mean_minimum_observer_age_ticks"] is None


def test_unmeasured_counts_and_windows_remain_unavailable():
    raw = tracking_statistics(tracking_plugin().snapshot(), 1)
    assert raw["last_sampled_tick"] is None
    assert raw["targets"]["target.one"]["longest_contact_gap_ticks"] is None
    assert raw["event_windows"]["event.first"]["targets"]["target.one"]["event_to_qualifying_contact_ticks"] is None


def test_gap_series_retains_leading_and_censored_trailing_gap():
    model = tracking_plugin(end=4); states = [model.snapshot()]
    for tick in range(1, 5): value(model, tick); states.append(model.snapshot())
    result = temporal_statistics(states, "tracking", .5)
    assert result["gap_episodes"]["target.one"] == [{"start_tick": 1, "end_tick_inclusive": 3, "gap_ticks": 3,
        "gap_seconds": 1.5, "qualifying_contact_return_tick": None, "censored_at_last_sample": True}]
    assert tracking_statistics(states[-1], .5)["last_sampled_tick"] == 3


def contact_state(initial, tick, seen, gap, longest, owner, *, changes=None, gaps=(), event=None):
    s = deepcopy(initial); s.update(last_tick=tick, samples=tick, last_value=seen/tick)
    h = s["targets"]["target.one"]; h.update(seen_ticks=seen, gap_ticks=gap, longest_gap_ticks=longest,
        owner_group=owner, handover_counts=changes or {}, handover_gaps=list(gaps), last_contact_tick=tick if not gap else tick-gap)
    if event is not None: s["event_windows"] = event
    return s


def test_handover_is_a_group_change_and_event_credit_does_not_invent_a_loss():
    initial = tracking_plugin().snapshot()
    first = contact_state(initial, 1, 1, 0, 0, "air")
    second = contact_state(initial, 2, 2, 0, 0, "air", event={"event.first": {"start_tick": 2, "reacquired": {"target.one": 0}}})
    result = temporal_statistics([initial, first, second], "tracking", 1)
    assert result["event_contact_credits"][0]["prior_gap_observed"] is False
    assert result["event_contact_credits"][0]["event_to_qualifying_contact_ticks"] == 0
    missing = contact_state(initial, 2, 1, 1, 1, "air")
    transferred = contact_state(initial, 3, 2, 0, 1, "surface", changes={"air->surface": 1}, gaps=[1])
    result = temporal_statistics([initial, first, missing, transferred], "tracking", .5)
    assert result["credited_observer_group_changes"][0]["gap_seconds"] == .5
    assert result["gap_episodes"]["target.one"][0]["qualifying_contact_return_tick"] == 3


def test_report_ingestion_and_zero_comparisons_have_separate_availability():
    model = report_plugin("identity_switch_rate", start_tick=3)
    model.evaluate(snapshot(1)); state = model.snapshot()
    state.update(total_reports=1, attributed_reports=1, correct_reports=1, switches=0, comparisons=0)
    raw = report_statistics(state, 1)
    assert raw["sample_count"] == 0 and raw["native_candidate_score_value"] is None
    assert raw["model_report_counters"]["total_reports"] == 1
    assert raw["processed_report_correct_fraction"] == 1
    assert raw["attributed_identity_switch_fraction"] is None
    state.update(samples=1, last_value=0, last_tick=3)
    assert report_statistics(state, 1)["attributed_identity_switch_fraction"] is None


def test_multiple_identity_switches_are_not_erased_by_matching_endpoint_identity():
    state = report_plugin().snapshot(); state.update(last_tick=3, samples=3, switches=2, comparisons=2, attributed_reports=3, total_reports=3)
    raw = report_statistics(state, 1)
    assert raw["model_report_counters"]["switches"] == 2 and raw["attributed_identity_switch_fraction"] == 1


def test_covered_measurement_ages_come_from_ticks_not_inverse_normalization():
    initial = report_plugin().snapshot(); first = deepcopy(initial); second = deepcopy(initial)
    for state, tick, total in [(first,1,.8),(second,2,1.4)]:
        state.update(last_tick=tick, samples=tick)
        state["tracks"]["cue.a"].update(covered_ticks=tick, freshness_sum=total, latest={"observed_tick": 0})
    raw = temporal_statistics([initial,first,second], "reports", .5)
    assert raw["covered_sample_measurement_age"]["cue.a"]["mean_age_ticks"] == 1.5
    assert raw["covered_sample_measurement_age"]["cue.a"]["mean_age_seconds"] == .75
    second["tracks"]["cue.a"]["freshness_sum"] = 1.5
    with pytest.raises(ValueError, match="freshness accumulation"): temporal_statistics([initial,first,second], "reports", 1)


@pytest.mark.parametrize("dt", [0, -1, True, float("nan"), float("inf")])
def test_bad_units_are_rejected(dt):
    with pytest.raises(ValueError): tracking_statistics(tracking_plugin().snapshot(), dt)


def test_missing_state_ticks_fail_closed():
    model = tracking_plugin(); states = [model.snapshot()]
    value(model, 1); value(model, 2); states.append(model.snapshot())
    with pytest.raises(ValueError, match="contiguous"): temporal_statistics(states, "tracking", 1)

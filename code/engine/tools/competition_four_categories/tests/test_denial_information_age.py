from copy import deepcopy
import pytest

from tools.competition_four_categories.denial_information_age import audit, distribution


def fixture():
    brief = {"scenario_id": "fixture", "physics_dt_seconds": .5, "scoring_deadline_tick": 6, "defenders": ["agent.a"]}
    terminal = {"outcome": "fixture_done"}
    trace = [{"tick": t, "terminal": terminal if t == 7 else None,
              "referee_event_evidence": {"active_jamming_sessions": ["jamming"] if 3 <= t < 5 else []},
              "controller_observations": {"agent.a": {"tick": t, "organic_contacts": [], "shared_contacts": []}}}
             for t in range(1, 8)]
    return {"scenario_id": "fixture", "final_tick": 7, "terminal": terminal, "trace": trace, "seed": 1, "policy": "fixture"}, brief


def contact(measured=1, delivered=2, reported=0, source="opaque-stream"):
    return {"source_contact_id": source, "observer_entity_id": "sensor.a",
            "observed_tick": measured, "delivered_tick": delivered, "age_ticks": reported}


def obs(result, tick):
    return result["trace"][tick - 1]["controller_observations"]["agent.a"]


def pooled(report, phase, channel="shared"):
    return next(s for s in report["summaries"] if s["phase"] == phase and s["channel"] == channel and s["controller_entity_id"] == "ALL_CONTROLLERS")


def test_source_timestamp_not_reported_age_determines_information_age():
    result, brief = fixture(); obs(result, 3)["shared_contacts"] = [contact()]
    before = deepcopy(result); report, timeline = audit(result, brief, (3, 5))
    row = pooled(report, "during_outage")
    assert row["measurement_age"]["ticks"]["mean"] == 2
    assert row["measurement_age"]["seconds"]["mean"] == 1
    assert row["reported_age_field_disagreements"] == 1
    assert row["newly_visible_selected_delivery_lag"]["ticks"]["mean"] == 1
    assert result == before and timeline[2]["channels"]["shared"][0]["reported_age_ticks"] == 0


def test_empty_contacts_are_missing_not_perfect_freshness():
    result, brief = fixture(); report, _ = audit(result, brief, (3, 5))
    row = pooled(report, "during_outage")
    assert row["observation_samples"] == row["observations_without_contacts"] == 2
    assert row["measurement_age"]["ticks"] is None
    assert report["post_outage_shared_recovery"]["agent.a"]["first_visible_shared_delivery_tick"] is None


def test_windows_are_exact_and_adjudication_is_not_a_scoring_sample():
    result, brief = fixture(); report, timeline = audit(result, brief, (3, 5))
    assert [x["tick"] for x in timeline] == list(range(1, 7))
    assert [x["phase"] for x in timeline] == ["before_outage"] * 2 + ["during_outage"] * 2 + ["after_outage"] * 2
    assert report["native_jamming_active_observation_ticks"]["during_outage"] == [3, 4]


def test_freshest_source_stream_and_delivery_dedup_do_not_count_history_as_new():
    result, brief = fixture()
    for t in [3, 4]: obs(result, t)["shared_contacts"] = [contact(), contact(measured=2, delivered=3)]
    report, timeline = audit(result, brief, (3, 5)); row = pooled(report, "during_outage")
    assert row["measurement_age"]["sample_count"] == 2
    assert row["measurement_age"]["ticks"]["mean"] == 1.5
    assert row["newly_visible_selected_delivery_lag"]["sample_count"] == 1
    assert all(len(timeline[t-1]["channels"]["shared"]) == 1 for t in [3, 4])


def test_public_source_fusion_does_not_infer_hidden_target_identity():
    result, brief = fixture(); o = obs(result, 3)
    o["shared_contacts"] = [contact(source="sensor.a.opaque"), contact(source="sensor.b.opaque")]
    o["organic_contacts"] = [{"contact_id": "sensor.a.opaque", "observer_entity_id": "sensor.a", "observed_tick": 3, "age_ticks": 0}]
    report, timeline = audit(result, brief); row = pooled(report, "whole_window", "freshest_public_source")
    assert row["measurement_age"]["sample_count"] == 2
    assert sorted(c["measurement_age_ticks"] for c in timeline[2]["channels"]["freshest_public_source"]) == [0, 2]


def test_recovery_distinguishes_new_delivery_from_new_measurement():
    result, brief = fixture()
    obs(result, 5)["shared_contacts"] = [contact(measured=2, delivered=5)]
    obs(result, 6)["shared_contacts"] = [contact(measured=5, delivered=5)]
    report, _ = audit(result, brief, (3, 5)); recovery = report["post_outage_shared_recovery"]["agent.a"]
    assert recovery == {"first_visible_shared_delivery_tick": 5, "first_visible_post_outage_measurement_tick": 6}


@pytest.mark.parametrize("changes", [{"observed_tick": 4}, {"delivered_tick": 4}, {"delivered_tick": 0}, {"observed_tick": True}, {"age_ticks": -1}])
def test_invalid_clocks_fail_closed(changes):
    result, brief = fixture(); c = contact(); c.update(changes); obs(result, 3)["shared_contacts"] = [c]
    with pytest.raises(ValueError): audit(result, brief)


@pytest.mark.parametrize("bad", [0, -1, float("inf"), True])
def test_invalid_time_units_fail_closed(bad):
    result, brief = fixture(); brief["physics_dt_seconds"] = bad
    with pytest.raises(ValueError): audit(result, brief)


def test_trace_gap_missing_controller_and_missing_channel_are_not_empty_data():
    result, brief = fixture(); result["trace"].pop(0)
    with pytest.raises(ValueError, match="not contiguous"): audit(result, brief)
    result, brief = fixture(); result["trace"][0]["controller_observations"] = {}
    with pytest.raises(ValueError, match="missing or unexpected"): audit(result, brief)
    result, brief = fixture(); del obs(result, 1)["shared_contacts"]
    with pytest.raises(KeyError): audit(result, brief)


def test_distribution_uses_declared_nearest_rank_quantile():
    d = distribution(list(range(1, 21)), .5)
    assert d["ticks"]["p95_nearest_rank"] == 19 and d["seconds"]["p95_nearest_rank"] == 9.5

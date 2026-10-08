import pytest
from openmdbench.scoring.md_ad_002 import AD2MetricState, md_ad_002_score, score_metric_state


def test_na_metric_is_reweighted_and_safety_is_independent() -> None:
    score = md_ad_002_score(
        {
            "interception_rate": 1.0,
            "penetration_score": 1.0,
            "usv_early_warning_gain": 1.0,
            "relay_effectiveness": None,
            "resource_efficiency": 1.0,
            "response_time_score": 1.0,
            "usv_online_rate": 1.0,
        },
        safety_violations=2,
    )
    assert score.total_score == pytest.approx(1.0)
    assert score.safety_score == pytest.approx(0.8)
    assert score.rank_eligible


def test_more_than_three_safety_violations_zeroes_gate_not_total() -> None:
    score = md_ad_002_score({}, safety_violations=4)
    assert score.total_score == 0.0
    assert score.safety_score == 0.0
    assert not score.rank_eligible


def test_versioned_early_warning_baseline_and_platform_time_metrics() -> None:
    score = score_metric_state(
        AD2MetricState(
            scenario_id="MD-AD-002-EASY",
            destroyed_blue=6,
            breaches=2,
            initial_ammo=60,
            remaining_ammo=45,
            first_engagement_tick=120,
            usv_detection_distance_m=22_500.0,
            usv_online_platform_ticks=15,
            usv_available_platform_ticks=20,
            safety_violations=0,
        )
    )
    assert score.metrics["usv_early_warning_gain"] == pytest.approx(0.5)
    assert score.metrics["response_time_score"] == pytest.approx(1.0)
    assert score.metrics["usv_online_rate"] == pytest.approx(0.75)


def test_hard_relay_effectiveness_is_available_when_required() -> None:
    score = score_metric_state(
        AD2MetricState(
            scenario_id="MD-AD-002-HARD",
            destroyed_blue=0,
            breaches=0,
            initial_ammo=60,
            remaining_ammo=60,
            first_engagement_tick=None,
            usv_detection_distance_m=None,
            usv_online_platform_ticks=2,
            usv_available_platform_ticks=2,
            safety_violations=0,
            relay_required_ticks=10,
            relay_success_ticks=7,
        )
    )
    assert score.metrics["relay_effectiveness"] == pytest.approx(0.7)
    assert score.availability["relay_effectiveness"]

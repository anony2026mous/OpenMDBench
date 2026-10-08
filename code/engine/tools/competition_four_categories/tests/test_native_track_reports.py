"""Native contract fixtures, not acceptance of the full competitive scenarios."""
import pytest

from tools.competition_four_categories.build import zone
from tools.competition_four_categories.emergency import event
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tracking_policy import ScheduledNavigationPolicy
from tools.competition_four_categories.validate_tracking_reports import execute
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


def fixture():
    package, brief, _, plan = tracking(7)
    s = package["scenario"]; horizon = 24
    s["world"]["duration_ticks"] = horizon+1
    s["events"] = [event(f"event.{name}", "mission_marker", horizon+1,
                         {"marker_id": f"marker.{name}"})
                   for name in ("deadline", "success", "timeout")]
    for metric in s["scoring"]["metrics"]:
        metric["plugin_parameters"].update(start_tick=4, end_tick=horizon+1)
    for rule in s["mission_rules"]:
        condition = rule["condition"]
        children = condition["parameters"]["conditions"] if condition["operator"] == "all" else [condition]
        for c in children:
            if c["operator"] == "time": c["parameters"]["tick"] = horizon+1
    positions = {"unit.x01": [160., -80., 120.], "unit.x02": [160., 80., 120.],
                 "unit.x03": [1400., 600., 220.], "unit.x04": [1400., -600., 320.],
                 "unit.r01": [0., -80., 160.], "unit.r02": [0., 80., 190.],
                 "unit.r03": [0., -220., 0.], "unit.r04": [200., -250., 0.]}
    for item in s["entities"]:
        item["initial_state"]["position_m"] = positions[item["id"]]
        item["initial_state"]["velocity_mps"] = [0., 0., 0.]
    for segment in plan["segments"]:
        segment["end_tick"] = horizon
        segment["payload"].update(speed_mps=0., altitude_m=positions[segment["entity_id"]][2])
    brief.update(duration_seconds=horizon, scoring_deadline_tick=horizon, adjudication_tick=horizon+1, scoring_start_tick=4)
    brief["initial_designation_regions"] = [zone("cue.01", 160., -80., 25.), zone("cue.02", 160., 80., 25.)]
    brief["track_reporting"]["score_window"] = {"start_tick_inclusive": 4, "end_tick_exclusive": horizon+1}
    return package, brief, ScheduledNavigationPolicy(plan)


@pytest.mark.parametrize("mode", ["honest", "silent", "swapped"])
def test_native_reports_distinguish_delivery_and_identity_from_sensor_detection(mode):
    package, brief, opponent = fixture()
    session, _ = session_from(package, f"native-track-report-{mode}")
    try:
        result = execute(session, brief, opponent, mode)
        assert result["failure"] is None
        assert result["final_tick"] == 25
        assert result["visibility_audit"]["last_tick"] == 25
        assert result["scores"]["metric.continuity"] >= .7
        if mode == "honest":
            assert result["terminal"]["outcome"] == "objective_complete"
            assert result["scores"]["metric.report_identity"] == 1.
            assert result["scores"]["metric.report_switch_rate"] == 0.
            assert result["scores"]["metric.report_coverage"] >= .7
            assert any(r["transport_status"] == "delivered" for r in result["report_delivery_evidence"])
        else:
            assert result["terminal"]["outcome"] == "objective_incomplete"
            assert result["scores"]["metric.report_coverage"] == 0.
            if mode == "silent":
                assert result["message_submissions"] == []
                assert result["scores"]["metric.report_identity"] is None
            else:
                assert result["scores"]["metric.report_identity"] == 0.
                assert any(r["transport_status"] == "delivered" for r in result["report_delivery_evidence"])
    finally:
        close(session)

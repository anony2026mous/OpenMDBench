"""Native shore-to-mobile handover fixture, not full scenario acceptance."""
import json

import pytest

from tools.competition_four_categories.build import zone
from tools.competition_four_categories.emergency import event
from tools.competition_four_categories.shore_beacon_policy import ShoreBindingPolicy, BeaconIdentityReportingPolicy
from tools.competition_four_categories.identity_tracking_policy import IdentityReportingPolicy, PEER_PROTOCOL
from tools.competition_four_categories.track_report_metrics_v1 import PROTOCOL
from tools.competition_four_categories.validate_tracking_reports import execute
from tools.competition_four_categories.tests.test_native_track_reports import fixture
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


class TransitObserver(BeaconIdentityReportingPolicy):
    def decide(self, observation):
        result = super().decide(observation)
        if observation["own_entities"] and observation["tick"] < 12:
            result["navigation"] = {"speed_mps": 80., "heading_deg": 90., "altitude_m": 180.}
        return result


def make_fixture():
    package, brief, opponent = fixture();s=package["scenario"];horizon=32
    s["world"]["duration_ticks"]=horizon+1
    s["events"] = [event(f"event.{name}", "mission_marker", horizon+1,
                         {"marker_id": f"marker.{name}"})
                   for name in ("deadline", "success", "timeout")]
    for metric in s["scoring"]["metrics"]:
        metric["plugin_parameters"].update(start_tick=16,end_tick=horizon+1)
        if "reporter_ids" in metric["plugin_parameters"]:metric["plugin_parameters"]["reporter_ids"]=["unit.r01"]
    for rule in s["mission_rules"]:
        c=rule["condition"];children=c["parameters"]["conditions"] if c["operator"]=="all" else [c]
        for child in children:
            if child["operator"]=="time":child["parameters"]["tick"]=horizon+1
    for entity in s["entities"]:
        if entity["id"]=="unit.r01":entity["initial_state"]["position_m"]=[-660.,0.,180.]
        elif entity["id"] in {"unit.r02","unit.r03"}:entity["initial_state"]["position_m"]=[-2000.,-2000.,190. if entity["id"]=="unit.r02" else 0.]
    for segment in opponent.plan["segments"]:
        segment["end_tick"]=horizon
        if segment["entity_id"] in {"unit.x01","unit.x02"}:segment["payload"].update(speed_mps=8.,heading_deg=90.)
    brief.update(duration_seconds=horizon,scoring_deadline_tick=horizon,adjudication_tick=horizon+1,scoring_start_tick=16)
    brief["mobile_observers"]=["unit.r01"]
    brief["track_reporting"]["reporter_ids"]=["unit.r01"]
    brief["initial_designation_regions"]=[zone("cue.01",160.,-80.,65.),zone("cue.02",160.,80.,65.)]
    return package,brief,opponent


@pytest.mark.parametrize("beacon_enabled",[True,False])
def test_native_shore_binding_requires_delivery_then_mobile_organic_report(beacon_enabled):
    package,brief,opponent=make_fixture();session,_=session_from(package,f"native-shore-beacon-{beacon_enabled}")
    mobile=TransitObserver(brief,"unit.r01");support={"unit.r04":ShoreBindingPolicy(brief,"unit.r04")} if beacon_enabled else {}
    try:
        result=execute(session,brief,opponent,"honest",agents={"unit.r01":mobile},support_agents=support)
        assert result["failure"] is None and result["final_tick"]==33
        assert all(x["entity_id"]!="unit.r04" for x in result["submitted_actions"])
        assert all(m["sender_entity_id"]=="unit.r01" for m in result["report_delivery_evidence"])
        shore_messages=[m for m in session.world_view.presentation_snapshot().event_state.message_queue if m["sender_entity_id"]=="unit.r04"]
        if beacon_enabled:
            assert any(m["transport_status"]=="delivered" for m in shore_messages)
            assert all(json.loads(m["payload"])["schema_version"]==PEER_PROTOCOL for m in shore_messages)
            assert result["scores"]["metric.report_identity"]==1.
            assert result["scores"]["metric.report_coverage"]>=.7
            assert any(x["owner"]=="unit.r01" and x["reason"]=="fresh_unique_cross_observer_measurement" for x in mobile.tracker.binding_events)
        else:
            assert shore_messages==[]
            assert result["scores"]["metric.report_coverage"]==0.
        assert result["trace"][0]["scores"]["metric.report_identity"] is None
    finally:
        close(session)

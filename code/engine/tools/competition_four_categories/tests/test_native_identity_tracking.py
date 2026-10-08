"""Native message and identity mechanism fixtures, not full competition acceptance."""
import json

import pytest

from tools.competition_four_categories.identity_tracking_policy import IdentityReportingPolicy, PEER_PROTOCOL
from tools.competition_four_categories.track_report_metrics_v1 import PROTOCOL
from tools.competition_four_categories.validate_tracking_reports import execute
from tools.competition_four_categories.tests.test_native_track_reports import fixture
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


@pytest.mark.parametrize("mode", ["honest", "silent", "swapped"])
def test_native_identity_agents_keep_peer_traffic_real_and_sink_score_correct(mode):
    package, brief, opponent = fixture()
    session, _ = session_from(package, f"native-identity-{mode}")
    agents = {i: IdentityReportingPolicy(brief, i, mode) for i in brief["track_reporting"]["reporter_ids"]}
    try:
        result = execute(session, brief, opponent, mode, agents=agents)
        assert result["failure"] is None and result["final_tick"] == 25
        assert result["scores"]["metric.continuity"] >= .7
        peer_messages = [m for m in session.world_view.presentation_snapshot().event_state.message_queue
                         if json.loads(m["payload"]).get("schema_version") == PEER_PROTOCOL]
        assert any(m["transport_status"] == "delivered" for m in peer_messages)
        assert all(m["recipient_entity_id"] in brief["track_reporting"]["reporter_ids"] for m in peer_messages)
        if mode == "honest":
            assert result["terminal"]["outcome"] == "objective_complete"
            assert result["scores"]["metric.report_identity"] == 1.
            assert result["scores"]["metric.report_switch_rate"] == 0.
        else:
            assert result["terminal"]["outcome"] == "objective_incomplete"
            assert result["scores"]["metric.report_coverage"] == 0.
            if mode == "silent":
                assert result["report_delivery_evidence"] == []
                assert result["scores"]["metric.report_identity"] is None
            else:
                assert result["scores"]["metric.report_identity"] == 0.
    finally:
        close(session)

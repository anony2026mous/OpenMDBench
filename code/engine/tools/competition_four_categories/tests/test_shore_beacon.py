import json
from types import SimpleNamespace

import pytest

from tools.competition_four_categories.identity_tracking_policy import IdentityReportingPolicy, PEER_PROTOCOL
from tools.competition_four_categories.shore_beacon_policy import ShoreBindingPolicy, BeaconIdentityReportingPolicy
from tools.competition_four_categories.track_report_metrics_v1 import PROTOCOL
from tools.competition_four_categories.validate_tracking_reports import execute
from tools.competition_four_categories.tests.test_identity_tracking import brief, contact, obs, peer


def test_shore_broadcasts_actual_own_binding_without_navigation_or_official_report():
    policy = ShoreBindingPolicy(brief(), "sink")
    row = contact("shore-token", [100., -80., 150.], tick=1, owner="sink")
    result = policy.decide(obs(tick=8, own="sink", contacts=[row]))
    assert result["navigation"] is None and len(result["messages"]) == 1
    m = result["messages"][0]; body = json.loads(m["message"])
    assert m["sender_id"] == "sink" and "slot.sink" not in m["recipient_controller_slots"]
    assert body["schema_version"] == PEER_PROTOCOL and body["schema_version"] != PROTOCOL
    assert body["bindings"] == [{"track_id": "cue.a", "contact_id": "shore-token",
        "observed_tick": 1, "estimated_position_m": [100., -80., 150.]}]


def test_shore_keeps_opaque_identity_after_contact_leaves_initial_region():
    policy = ShoreBindingPolicy(brief(), "sink")
    policy.decide(obs(own="sink", contacts=[contact("token", [100., -80., 150.], owner="sink")]))
    result = policy.decide(obs(tick=24, own="sink", contacts=[contact("token", [400., 300., 150.], 23, "sink")]))
    assert json.loads(result["messages"][0]["message"])["bindings"][0]["track_id"] == "cue.a"


@pytest.mark.parametrize("kind", ["foreign", "late", "outside", "ambiguous"])
def test_shore_does_not_invent_bindings(kind):
    rows = [contact("token", [100., -80., 150.], owner="sink")];tick=8
    if kind == "foreign": rows[0]["observer_entity_id"] = "own.a"
    elif kind == "late": rows[0]["observed_tick"] = 23;tick=24
    elif kind == "outside": rows[0]["estimated_position_m"] = [300., 300., 150.]
    else: rows.append(contact("other", [101., -80., 150.], owner="sink"))
    assert ShoreBindingPolicy(brief(), "sink").decide(obs(tick=tick, own="sink", contacts=rows))["messages"] == []


def test_mobile_accepts_real_shore_claim_but_legacy_policy_scope_stays_unchanged():
    envelope = peer(sender_entity_id="sink")
    observation = obs(tick=36, messages=[envelope], contacts=[contact("new-own", [402., -80., 150.], 35)])
    legacy = IdentityReportingPolicy(brief(), "own.a");current = BeaconIdentityReportingPolicy(brief(), "own.a")
    assert legacy.decide(observation)["messages"] == []
    reports = [json.loads(m["message"]) for m in current.decide(observation)["messages"]
               if json.loads(m["message"])["schema_version"] == PROTOCOL]
    assert len(reports) == 1 and reports[0]["contact_id"] == "new-own" and reports[0]["track_id"] == "cue.a"


def test_nonobserver_and_wrong_controller_shore_claims_are_rejected():
    policy = BeaconIdentityReportingPolicy(brief(), "own.a")
    assert policy.decide(obs(tick=36, messages=[peer(sender_entity_id="foreign-shore")]))["messages"] == []
    with pytest.raises(ValueError, match="controller scope"):
        ShoreBindingPolicy(brief(), "sink").decide(obs(own="own.a"))
    with pytest.raises(ValueError, match="non-reporting shore"):
        ShoreBindingPolicy(brief(), "own.a")
    assert ShoreBindingPolicy(brief(), "sink").decide({"own_entities": []}) == {"navigation": None, "messages": []}


def test_executor_support_scope_cannot_promote_an_undeclared_entity():
    agents = {i: SimpleNamespace(identifier=i) for i in brief()["track_reporting"]["reporter_ids"]}
    with pytest.raises(ValueError, match="stationary observer"):
        execute(None, brief(), None, "honest", agents=agents, support_agents={"foreign": SimpleNamespace(identifier="foreign")})


def test_beacon_evidence_requires_actual_support_policy_and_executor_sources():
    from tools.competition_four_categories.audit import tracking_policy_extension_matches
    from tools.competition_four_categories.validate_beacon_tracking import source_fingerprints
    fields = source_fingerprints();record = {"policy": "beacon-honest", **fields}
    assert tracking_policy_extension_matches(record)
    for key in fields:
        missing = dict(record);missing.pop(key)
        assert not tracking_policy_extension_matches(missing)
    assert not tracking_policy_extension_matches({"policy": "beacon-unknown", **fields})

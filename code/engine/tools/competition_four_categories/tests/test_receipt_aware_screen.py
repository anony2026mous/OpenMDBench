from copy import deepcopy

import pytest

from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.receipt_aware_screen_policy import ReceiptAwareSalvoPolicy, own_fire_feedback
from tools.competition_four_categories.tests.test_salvo_guard import contact, obs


def ready():
    agent = ReceiptAwareSalvoPolicy(denial(6)[1], "unit.r03")
    assert agent.action(obs(0, [contact(0, 600.)])) is None
    assert agent.action(obs(1, [contact(1, 592.)])) is not None
    agent.bind_fire_request("own.request.1")
    return agent


def receipt(status="rejected", request_id="own.request.1", tick=1):
    return {"request_id": request_id, "status": status, "tick": tick,
            "error_code": "combat.contact_denied" if status == "rejected" else None}


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_unexecuted_request_releases_only_its_reservation_and_can_retry(status):
    agent = ready(); assert agent.attempts == 1
    assert agent.process_fire_feedback(receipt(status))
    assert agent.attempts == 0 and agent.last_attempt_tick is None and agent.pending_until == {}
    assert agent.action(obs(2, [contact(2, 584.)])) is not None
    assert agent.attempts == 1


def test_executed_request_retains_ammunition_and_flight_wait_without_hit_knowledge():
    agent = ready(); before = deepcopy(agent.pending_until)
    assert agent.process_fire_feedback(receipt("executed"))
    assert agent.attempts == 1 and agent.pending_until == before
    assert agent.action(obs(2, [contact(2, 584.)])) is None
    assert agent.feedback[-1]["reservation_released"] is False


def test_missing_or_foreign_receipt_cannot_refund_or_authorize_more_launches():
    agent = ready(); before = deepcopy(agent.pending_until)
    assert not agent.process_fire_feedback(receipt(request_id="foreign.request"))
    assert agent.action(obs(50, [contact(50, 200.)])) is None
    assert agent.attempts == 1 and agent.pending_until == before


def test_duplicate_receipt_is_idempotent_and_contradictory_receipt_fails_closed():
    agent = ready(); row = receipt()
    assert agent.process_fire_feedback(row)
    assert not agent.process_fire_feedback(row)
    assert agent.attempts == 0
    with pytest.raises(ValueError, match="conflicting"):
        agent.process_fire_feedback(receipt("executed"))


def test_refunding_a_later_request_preserves_the_earlier_executed_launch():
    agent = ready(); agent.process_fire_feedback(receipt("executed"))
    pending = deepcopy(agent.pending_until)
    assert agent.action(obs(5, [contact(5, 350., token="second")])) is None
    assert agent.action(obs(6, [contact(6, 342., token="second")])) is not None
    agent.bind_fire_request("own.request.2")
    assert agent.process_fire_feedback(receipt(request_id="own.request.2", tick=6))
    assert agent.attempts == 1 and agent.last_attempt_tick == 1 and agent.pending_until == pending


def test_executed_launches_cannot_exceed_the_unchanged_inventory():
    agent = ReceiptAwareSalvoPolicy(denial(6)[1], "unit.r03")
    for index in range(7):
        tick = index * 4
        assert agent.action(obs(tick, [contact(tick, 300., token=str(index))])) is None
        action = agent.action(obs(tick + 1, [contact(tick + 1, 290., token=str(index))]))
        if index < 6:
            assert action is not None
            key = f"own.{index}"; agent.bind_fire_request(key)
            agent.process_fire_feedback(receipt("executed", key, tick + 1))
        else:
            assert action is None
    assert agent.attempts == 6


def test_feedback_filter_excludes_other_controllers_and_all_privileged_fields():
    own = {"child_id": "own.request.1", "kind": "discrete", **receipt(),
           "target_id": "secret", "referee_missile_state": {"hit": True}, "future_wave": 999}
    other = {**own, "child_id": "other.request", "request_id": "other.request"}
    forged = {**own, "request_id": "other.request"}
    navigation = {**own, "kind": "persistent"}
    rows = [other, own, forged, navigation]; before = deepcopy(rows)
    assert own_fire_feedback(rows, {"own.request.1"}) == [receipt()]
    assert rows == before
    assert own_fire_feedback(rows, set()) == []


def test_extra_feedback_data_and_unbound_requests_are_rejected():
    agent = ready()
    with pytest.raises(ValueError, match="only own"):
        agent.process_fire_feedback({**receipt(), "hit": True})
    with pytest.raises(ValueError, match="exactly one"):
        agent.bind_fire_request("duplicate")


def test_evidence_binds_feedback_adapter_and_inherited_navigation():
    from tools.competition_four_categories.audit import denial_extension_sources
    from tools.competition_four_categories import receipt_aware_screen_policy, approach_screen_policy
    from tools.competition_four_categories.validate_tracking import sha
    record = denial_extension_sources("receipt-aware-salvo")
    assert record["policy_source_sha256"] == sha(receipt_aware_screen_policy.__file__)
    assert record["approach_base_policy_sha256"] == sha(approach_screen_policy.__file__)
    assert record["fire_feedback_protocol"] == "own-fire-execution-status@1.0"

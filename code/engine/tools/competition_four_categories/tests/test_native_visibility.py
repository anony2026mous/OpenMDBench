"""Native visibility evidence tests; no packet rewriting or kernel patches."""
from copy import deepcopy

from tools.competition_four_categories.visibility_audit import VisibilityAudit
from tools.competition_four_categories.build import reconnaissance
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tests.test_native_candidate import session_from, close, navigate
from tools.competition_four_categories.tests.test_native_recon import report_fixture, send_observed
from tools.competition_four_categories.validate_denial import observe_slots


def test_native_unseen_target_is_absent_and_real_detection_is_accepted_without_editing_dto():
    s, _ = session_from(reconnaissance("easy")[0], "visibility-real-detection")
    slots = {"unit.r01": "slot.unit.r01"}
    auditor = VisibilityAudit(s, slots, faction_id="red")
    try:
        obs = observe_slots(s, slots)
        assert not obs["unit.r01"]["organic_contacts"]
        assert auditor.check(obs) is None
        bad = deepcopy(obs); bad["unit.r01"]["own_entities"][0]["entity_id"] = "unit.x01"
        assert auditor.check(bad)["violation"] == "own_state_scope"
        navigate(s)
        found = False
        for tick in range(80):
            s.step(operation_id=f"tick-{tick}", expected_tick=tick)
            obs = observe_slots(s, slots); original = deepcopy(obs)
            assert auditor.check(obs) is None
            assert obs == original
            if obs["unit.r01"]["organic_contacts"]:
                found = True
                assert any("unit.x01" in c["contact_id"] for c in obs["unit.r01"]["organic_contacts"])
                bad = deepcopy(obs); bad["unit.r01"]["organic_contacts"][0]["estimated_position_m"][0] += 1000
                assert auditor.check(bad)["violation"] == "organic_contact_evidence"
                break
        assert found
        before = (s.world_view.tick, s.world_view.get("unit.r01").state.position_m)
        assert auditor.check(obs) is None
        assert before == (s.world_view.tick, s.world_view.get("unit.r01").state.position_m)
    finally: close(s)


def test_native_shared_contacts_and_report_messages_require_real_delivery():
    package, brief = report_fixture()
    s, _ = session_from(package, "visibility-shared-and-message")
    slots = {"unit.r03": "slot.unit.r03"}
    auditor = VisibilityAudit(s, slots, faction_id="red")
    try:
        assert auditor.check(observe_slots(s, slots)) is None
        for tick in range(10):
            if tick == 3: send_observed(s, brief, "unit.r01")
            s.step(operation_id=f"tick-{tick}", expected_tick=tick)
            obs = observe_slots(s, slots)
            assert auditor.check(obs) is None
            if s.world_view.tick < 4: assert not obs["unit.r03"]["shared_contacts"]
            if s.world_view.tick < 7: assert not obs["unit.r03"]["received_messages"]
        assert obs["unit.r03"]["shared_contacts"]
        assert obs["unit.r03"]["received_messages"]
        assert any("unit.x" in m["payload"] for m in obs["unit.r03"]["received_messages"])
        altered = deepcopy(obs); altered["unit.r03"]["shared_contacts"][0]["recipient_controller_slot"] = "slot.unit.r01"
        assert auditor.check(altered)["violation"] == "shared_inbox_evidence"
        altered = deepcopy(obs); altered["unit.r03"]["received_messages"][0]["payload"] = "invented future report"
        assert auditor.check(altered)["violation"] == "message_inbox_evidence"
    finally: close(s)


def test_visibility_audit_remains_independent_when_recovery_checkpoint_is_valid():
    s, _ = session_from(tracking(1)[0], "visibility-with-valid-checkpoint")
    slots = {"unit.r01": "slot.unit.r01"}
    auditor = VisibilityAudit(s, slots, faction_id="red")
    try:
        assert auditor.check(observe_slots(s, slots)) is None
        for tick in range(10):
            s.step(operation_id=f"tick-{tick}", expected_tick=tick)
            assert auditor.check(observe_slots(s, slots)) is None
        checkpoint = s.checkpoint()
        assert checkpoint.checkpoint_hash
        assert auditor.check(observe_slots(s, slots)) is None
        assert auditor.summary()["checked_frames"] == 11
    finally: close(s)

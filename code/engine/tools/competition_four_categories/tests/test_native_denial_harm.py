"""Real native weapon receipts; these short fixtures are not full episodes."""
import pytest
from math import dist

from tools.competition_four_categories.denial_harm_audit import ProtectedHarmAudit
from tools.competition_four_categories.tests.test_native_candidate import session_from, close
from tools.competition_four_categories.tests.test_native_denial import protected_fixture, advance, state
from tools.competition_four_categories.validate_denial import observe_slots, submit_fire


@pytest.mark.parametrize("shoot", [False, True])
def test_native_protected_damage_is_attributed_and_receipts_replay(shoot):
    package, protected = protected_fixture()
    session, _ = session_from(package, "denial-protected-harm")
    a = ProtectedHarmAudit(["unit.r02"], [protected])
    b = ProtectedHarmAudit(["unit.r02"], [protected])
    try:
        receipts = advance(session, 3)
        # This referee mechanism fixture deliberately targets the civilian's
        # deployed position; it is not a fair competition-policy baseline.
        # The generic first-contact helper can shoot another intruder instead.
        for tick in range(3, 14):
            if shoot:
                observation = observe_slots(session, {"unit.r02": "slot.unit.r02"})["unit.r02"]
                contacts = [c for c in observation["organic_contacts"] if c["age_ticks"] <= 1]
                if contacts:
                    target = min(contacts, key=lambda c: dist(c["estimated_position_m"], [500., 0., 180.]))
                    submit_fire(session, "unit.r02", "red", tick,
                        {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": target["contact_id"]})
            receipts += advance(session, tick + 1)
        ledger = session.world_view.checkpoint().model_dump(mode="json")["combat_ledger"]
        a.consume_checkpoint_ledger(ledger, 14)
        b.consume_checkpoint_ledger(ledger, 14)
        value = a.summary()
        assert value == b.summary()
        assert value["checked_steps"] == 14
        assert value["defender_weapon_harm_rate"] == (1 if shoot else 0), {
            "audit": value, "target_health": state(session, protected).health,
            "combat": [{"status": c.status, "error": c.error_code} for step in receipts for c in step.world_receipt.combat_receipts]}
        assert value["defender_weapon_hull_health_loss"] == pytest.approx(1 - state(session, protected).health)
        assert bool(value["evidence"]) is shoot
        if shoot:
            partial = ProtectedHarmAudit(["unit.r02"], [protected])
            for step in receipts:
                partial.consume(step.world_receipt.start_tick, step.world_receipt.damage_receipts)
            assert partial.summary()["defender_weapon_harm_rate"] == 0
            assert value["defender_weapon_harm_rate"] == 1
    finally:
        close(session)

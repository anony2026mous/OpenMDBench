"""Native mechanism fixtures, not privacy-compliant competition episodes."""
from copy import deepcopy

import pytest

from openmdbench.sessions.lifecycle_v2 import SessionFailureV2, SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.denial_policy import WaveNavigationPolicy
from tools.competition_four_categories.surface_profile import PLATFORM_REF as PICKET_PLATFORM_REF
from tools.competition_four_categories.validate_denial import observe_slots, authority, submit_navigation, submit_fire
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


def advance(session, end, opponent=None, shooter=None):
    receipts = []
    while session.world_view.tick < end:
        tick = session.world_view.tick
        if opponent is not None:
            slots = {i: opponent.plan["controller_slots"][i] for i in opponent.active_ids(tick)}
            for identifier, command in opponent.commands(tick, observe_slots(session, slots)).items():
                submit_navigation(session, identifier, "blue", tick, command)
        if shooter is not None:
            contacts = observe_slots(session, {shooter: f"slot.{shooter}"})[shooter]["organic_contacts"]
            fresh = [c for c in contacts if c["age_ticks"] <= 1]
            if fresh and ammo(session, shooter) > 0:
                submit_fire(session, shooter, "red", tick,
                    {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": fresh[0]["contact_id"]})
        receipts.append(session.step(operation_id=f"tick-{tick}", expected_tick=tick))
    return receipts


def state(session, identifier):
    value = session.world_view.get_optional(identifier)
    assert value is not None
    return value.state


def ammo(session, identifier):
    return sum(state(session, identifier).ammunition.values())


def mission(session):
    return session.world_view.presentation_snapshot().mission_scoring_checkpoint


def short_wave_fixture():
    package, _, _, plan = denial(1)
    s = package["scenario"]
    s["world"]["duration_ticks"] = 36
    for metric in s["scoring"]["metrics"]:
        metric["plugin_parameters"]["end_tick"] = 36
    s["mission_rules"][0]["condition"]["parameters"]["conditions"][0]["parameters"]["tick"] = 36
    s["mission_rules"][1]["condition"]["parameters"]["tick"] = 36
    for event in s["events"]:
        if event["event_type"] == "spawn":
            event["trigger"]["tick"] = 5
            event["payload"]["entity"]["initial_state"]["position_m"] = [550., 0., 180.]
        else:
            event["trigger"]["tick"] = 36
    for segment in plan["segments"]:
        if segment["start_tick"] > 0:
            segment["start_tick"] = 5
        segment["end_tick"] = 35
    return package, WaveNavigationPolicy(plan)


def test_native_spawn_is_absent_before_release_then_gets_real_control():
    package, opponent = short_wave_fixture()
    session, _ = session_from(package, "denial-spawn-control")
    try:
        advance(session, 4, opponent)
        assert session.world_view.get_optional("unit.x02") is None
        with pytest.raises(ValueError, match="authority"):
            authority(session, "unit.x02")
        advance(session, 5, opponent)
        assert session.world_view.get_optional("unit.x02") is not None
        assert authority(session, "unit.x02")
        assert observe_slots(session, {"unit.x02": "controller/unit.x02"})["unit.x02"]["own_entities"]
        receipts = advance(session, 7, opponent)
        assert any("nav-unit.x02-5" in r.activated_command_ids for r in receipts)
        assert state(session, "unit.x02").position_m[0] < 550.
    finally:
        close(session)


def test_unopposed_late_wave_breaches_and_cannot_be_hidden_by_early_success():
    package, opponent = short_wave_fixture()
    session, _ = session_from(package, "denial-idle-late-wave")
    try:
        advance(session, 4, opponent)
        assert mission(session)["score_state"]["metric.protection"] == 1
        assert mission(session)["terminal_result"] is None
        advance(session, 35, opponent)
        assert mission(session)["score_state"]["metric.breaches"] == 0
        assert mission(session)["terminal_result"] is None
        advance(session, 36, opponent)
        assert mission(session)["terminal_result"]["outcome"] == "objective_incomplete"
    finally:
        close(session)


def test_native_combat_can_prevent_a_breach_and_consumes_real_ammunition():
    package, opponent = short_wave_fixture()
    session, _ = session_from(package, "denial-native-defence")
    try:
        original_ammo = ammo(session, "unit.r02")
        receipts = advance(session, 35, opponent, shooter="unit.r02")
        assert ammo(session, "unit.r02") < original_ammo
        assert any(r.world_receipt.combat_receipts for r in receipts)
        assert state(session, "unit.x02").health < 1
        assert state(session, "unit.x02").lifecycle in {"disabled", "destroyed"}
        assert mission(session)["score_state"]["metric.breaches"] == 1
        assert mission(session)["terminal_result"] is None
        advance(session, 36, opponent)
        assert mission(session)["terminal_result"]["outcome"] == "objective_complete"
    finally:
        close(session)


def protected_fixture(ammunition=None):
    package = denial(3)[0]
    protected = package["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["protected_entities"][0]["entity_id"]
    for e in package["scenario"]["entities"]:
        if e["id"] == protected:
            e["initial_state"]["position_m"] = [500., 0., 180.]
            e["initial_state"]["velocity_mps"] = [0., 0., 0.]
        if e["id"] == "unit.r02" and ammunition is not None:
            e["ammunition"] = {"ammunition.shore-ciws@2.0.0": ammunition}
    return package, protected


def test_native_harm_to_protected_traffic_reduces_integrity_score():
    package, protected = protected_fixture()
    session, _ = session_from(package, "denial-protected-harm")
    try:
        advance(session, 3)
        assert mission(session)["score_state"]["metric.protected_integrity"] == 1
        advance(session, 14, shooter="unit.r02")
        health = state(session, protected).health
        assert health < 1
        assert mission(session)["score_state"]["metric.protected_integrity"] == health
    finally:
        close(session)


def test_fake_unobserved_contact_cannot_consume_ammunition_or_advance_world():
    session, _ = session_from(denial(1)[0], "denial-invalid-contact")
    try:
        before = ammo(session, "unit.r02")
        with pytest.raises(SessionFailureV2):
            submit_fire(session, "unit.r02", "red", 0,
                {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": "opaque.never-observed"})
            advance(session, 1)
        assert ammo(session, "unit.r02") == before
        assert session.world_view.tick == 0
    finally:
        close(session)


def test_native_finite_magazine_rejects_shots_after_exhaustion():
    package, protected = protected_fixture(ammunition=1)
    # A single native hit can disable the first target. Keep another real
    # target observable so a subsequent shot can reach the ammunition gate.
    other = next(e for e in package["scenario"]["entities"]
                 if e["faction_id"] == "blue" and e["id"] != protected)
    origin = next(e["initial_state"]["position_m"] for e in package["scenario"]["entities"]
                  if e["id"] == "unit.r02")
    other["initial_state"].update(position_m=[origin[0]+500., origin[1]+200., 180.], velocity_mps=[0., 0., 0.])
    session, _ = session_from(package, "denial-finite-magazine")
    try:
        # Native detection is stochastic and is refreshed before combat. A
        # contact visible at submit time need not still pass at apply time.
        # Wait for real consumption, then require the *ammunition* rejection,
        # rather than accepting any unrelated rejection as proof of exhaustion.
        spent, exhaustion_rejected = False, False
        rejection_codes = set()
        ledger = []
        for tick in range(30):
            contacts = observe_slots(session, {"unit.r02": "slot.unit.r02"})["unit.r02"]["organic_contacts"]
            fresh = [c for c in contacts if c["age_ticks"] <= 1]
            if fresh:
                submit_fire(session, "unit.r02", "red", tick,
                    {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": fresh[0]["contact_id"]})
            result = advance(session, tick+1)[0]
            rejection_codes.update(c.error_code for c in result.child_receipts if c.error_code)
            remaining = ammo(session, "unit.r02")
            ledger.append({"tick": tick, "ammo": remaining,
                "contacts": [c["contact_id"] for c in fresh],
                "receipts": [c.model_dump(mode="json") for c in result.child_receipts],
                "targets": {i: (state(session, i).health, state(session, i).lifecycle)
                            for i in (protected, other["id"])}})
            assert remaining in (0, 1)
            if spent:
                assert remaining == 0
                exhaustion_rejected = any(c.kind == "discrete" and c.status == "rejected"
                    and c.error_code == "combat.ammunition_denied" for c in result.child_receipts)
            spent = spent or remaining == 0
            if exhaustion_rejected:
                break
        assert spent, "No native shot consumed the finite magazine"
        assert exhaustion_rejected, f"Exhausted-ammunition gate not reached; rejections={sorted(rejection_codes)}; ledger={ledger}"
    finally:
        close(session)


def test_native_surface_weapon_creates_flights_and_applies_real_damage():
    package = denial(6)[0]
    target = next(e for e in package["scenario"]["entities"] if e["faction_id"] == "blue" and e["platform_ref"] == PICKET_PLATFORM_REF)
    target_id = target["id"]
    target["initial_state"].update(position_m=[350., 400., 0.], velocity_mps=[0., 0., 0.])
    session, _ = session_from(package, "denial-surface-weapon")
    ever_flight = False
    try:
        advance(session, 3)
        initial = ammo(session, "unit.r03")
        for tick in range(3, 60):
            if tick in (3, 6, 9, 12, 15, 18):
                contacts = observe_slots(session, {"unit.r03": "slot.unit.r03"})["unit.r03"]["organic_contacts"]
                surface = [c for c in contacts if c["estimated_position_m"][2] < 40 and c["age_ticks"] <= 1]
                if surface and ammo(session, "unit.r03") > 0:
                    submit_fire(session, "unit.r03", "red", tick,
                        {"weapon_ref": "weapon.surface-missile@2.0.0", "contact_id": surface[0]["contact_id"]})
            advance(session, tick+1)
            ever_flight = ever_flight or bool(session.world_view.presentation_snapshot().missile_flights)
            if state(session, target_id).health < 1:
                break
        assert ever_flight
        assert ammo(session, "unit.r03") < initial
        assert state(session, target_id).health < 1
    finally:
        close(session)


def test_native_checkpoint_preserves_a_recorded_denial_breach():
    package, opponent = short_wave_fixture()
    original, catalog = session_from(package, "denial-checkpoint")
    restored = None
    try:
        advance(original, 30, opponent)
        assert mission(original)["score_state"]["metric.breaches"] == 0
        checkpoint = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=checkpoint, expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=original.resolved, expected_resolved_hash=original.resolved.resolved_hash,
            model_registry=catalog.model_registry, expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        for tick in range(31, 37):
            advance(original, tick, opponent)
            advance(restored, tick, opponent)
            assert mission(original) == mission(restored)
        assert mission(original)["terminal_result"]["outcome"] == "objective_incomplete"
    finally:
        close(original)
        if restored is not None:
            close(restored)


if __name__ == "__main__":
    # Bounded referee diagnostic; never used as a competition-agent result.
    import json
    from datetime import datetime, timezone
    from tools.competition_four_categories.build import ROOT
    package, target = protected_fixture(ammunition=2)
    session, _ = session_from(package, "denial-combat-diagnostic")
    def contact_evidence():
        records = []
        def visit(value):
            if isinstance(value, dict):
                if value.get("schema_version") == "world-contact@2.0" and value.get("owner_entity_id") == "unit.r02":
                    records.append(value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(session.checkpoint().model_dump(mode="json"))
        return records
    try:
        advance(session, 3)
        observed = observe_slots(session, {"unit.r02": "slot.unit.r02"})["unit.r02"]
        contacts = observed["organic_contacts"]
        assert contacts
        before_evidence = contact_evidence()
        submit_fire(session, "unit.r02", "red", 3,
            {"weapon_ref": "weapon.shore-ciws@2.0.0", "contact_id": contacts[0]["contact_id"]})
        receipt = advance(session, 4)[0].model_dump(mode="json")
        result = {"scope": "native_combat_diagnostic_not_release", "resolved_hash": session.resolved.resolved_hash,
            "contacts": contacts, "ammo_after": ammo(session, "unit.r02"), "target_health": state(session, target).health,
            "contact_evidence_before": before_evidence, "contact_evidence_after": contact_evidence(),
            "action_receipts": receipt["child_receipts"],
            "combat_receipts": receipt["world_receipt"]["combat_receipts"],
            "damage_receipts": receipt["world_receipt"]["damage_receipts"]}
        path = ROOT / "artifacts/competition_four_categories" / ("denial-combat-diagnostic-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        print(path.relative_to(ROOT), flush=True)
    finally:
        close(session)

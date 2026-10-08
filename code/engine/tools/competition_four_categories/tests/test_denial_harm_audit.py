from copy import deepcopy

import pytest

from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.denial_harm_audit import ProtectedHarmAudit


def native_receipt(sources=(("defender", "weapon"),), before=1.0, after=0.7, tick=0, target="civilian"):
    ids = [f"intent-{tick}-{i}" for i in range(len(sources))]
    intents = [{"intent_id": identifier, "tick": tick, "source_entity_id": actor,
                "target_entity_id": target, "effect_ref": "effect.test@1.0.0",
                **({"damage_model_ref": "damage.test@1.0.0", "magnitude": 0.3,
                    "evidence_hash": "sha256:" + "1" * 64, "source_kind": kind} if kind else {})}
               for identifier, (actor, kind) in zip(ids, sources)]
    return {"schema_version": "2.0", "tick": tick, "applied_intents": intents,
            "destroyed_entities": [], "results": [{"schema_version": "2.0", "target_entity_id": target, "tick": tick,
                "applied_intent_ids": ids, "health_before": before, "health_after": after,
                "lifecycle_before": "active", "lifecycle_after": "degraded"}]}


def audit():
    return ProtectedHarmAudit(["defender"], ["civilian"])


def test_actual_native_health_delta_not_intended_magnitude():
    a = audit(); r = native_receipt(before=0.2, after=0.0)
    r["results"][0]["lifecycle_after"] = "destroyed"
    r["applied_intents"][0]["magnitude"] = 8.0
    before = deepcopy(r); a.consume(0, [r]); value = a.summary()
    assert r == before
    assert value["defender_weapon_hull_health_loss"] == 0.2
    assert value["defender_weapon_harm_rate"] == 1
    assert value["native_score_or_terminal_modified"] is False


@pytest.mark.parametrize("source", [("enemy", "weapon"), ("defender", "collision"), ("weather", "environment")])
def test_non_defender_weapon_damage_is_not_false_civilian_fire(source):
    a = audit(); a.consume(0, [native_receipt((source,))]); value = a.summary()
    assert value["all_cause_hull_health_loss"] == pytest.approx(0.3)
    assert value["defender_weapon_harm_rate"] == 0
    assert value["defender_weapon_hull_health_loss"] == 0


@pytest.mark.parametrize("sources", [(("defender", "weapon"), ("storm", "environment")), (("defender", None),)])
def test_mixed_and_missing_source_evidence_report_bounds_not_fake_precise_blame(sources):
    a = audit(); a.consume(0, [native_receipt(sources)]); value = a.summary()
    assert value["defender_weapon_harm_rate"] is None
    assert value["defender_weapon_harm_rate_bounds"] == [0, 1]
    assert value["defender_weapon_hull_health_loss"] is None
    assert value["defender_weapon_hull_health_loss_bounds"] == pytest.approx([0, 0.3])


def test_intent_without_health_loss_and_component_only_are_not_hull_damage():
    a = audit(); r = native_receipt(after=1.0)
    r["applied_intents"][0]["component_id"] = "radar"
    r["results"][0]["component_health"] = {"radar": 0.0}
    a.consume(0, [r]); value = a.summary()
    assert value["defender_weapon_harm_rate"] == 0
    assert value["component_only_harm_covered"] is False
    assert value["classification_error_covered"] is False


def test_repeated_harm_counts_entity_once_and_ignores_nonprotected_targets():
    a = audit(); a.consume(0, [native_receipt()])
    a.consume(1, [native_receipt(before=0.7, after=0.4, tick=1)])
    a.consume(2, [native_receipt(tick=2, target="intruder")])
    value = a.summary()
    assert value["defender_weapon_harmed_ids_lower"] == ["civilian"]
    assert value["defender_weapon_harm_rate"] == 1
    assert value["defender_weapon_hull_health_loss"] == pytest.approx(0.6)


def test_empty_cohort_is_not_claimed_zero_civilian_error_rate():
    a = ProtectedHarmAudit(["defender"], [])
    a.consume(0, [{"tick": 0, "applied_intents": [], "destroyed_entities": [], "results": []}])
    assert a.summary()["defender_weapon_harm_rate"] is None
    assert a.summary()["defender_weapon_harm_rate_bounds"] == [None, None]


@pytest.mark.parametrize("bad", ["receipt_tick", "intent_tick", "result_tick", "missing_intent",
    "missing_result", "target_mismatch", "duplicate_intent", "duplicate_result", "duplicate_reference"])
def test_broken_native_evidence_is_rejected_atomically(bad):
    a = audit(); r = native_receipt()
    if bad == "receipt_tick": r["tick"] = 1
    elif bad == "intent_tick": r["applied_intents"][0]["tick"] = 1
    elif bad == "result_tick": r["results"][0]["tick"] = 1
    elif bad == "missing_intent": r["applied_intents"] = []
    elif bad == "missing_result": r["results"] = []
    elif bad == "target_mismatch": r["results"][0]["target_entity_id"] = "other"
    elif bad == "duplicate_intent": r["applied_intents"].append(deepcopy(r["applied_intents"][0]))
    elif bad == "duplicate_result": r["results"].append(deepcopy(r["results"][0]))
    elif bad == "duplicate_reference": r["results"][0]["applied_intent_ids"] *= 2
    before = a.summary()
    with pytest.raises(ValueError): a.consume(0, [r])
    assert a.summary() == before


def test_duplicate_cross_receipt_and_missing_ticks_are_rejected():
    a = audit(); r = native_receipt()
    with pytest.raises(ValueError, match="duplicate"): a.consume(0, [r, r])
    with pytest.raises(ValueError, match="contiguous"): a.consume(1, [])
    a.consume(0, [r])
    with pytest.raises(ValueError, match="contiguous"): a.consume(0, [])


def test_missing_receipts_cannot_be_reported_as_zero_harm():
    a = audit()
    with pytest.raises(ValueError, match="missing native"): a.consume(0, [])
    assert a.summary()["checked_steps"] == 0


@pytest.mark.parametrize("defenders,protected", [([], []), (["x", "x"], []),
    (["x"], ["x"]), ("defender", []), (["x"], ["y", "y"])])
def test_invalid_cohorts_fail_before_any_harm_evaluation(defenders, protected):
    with pytest.raises(ValueError): ProtectedHarmAudit(defenders, protected)


@pytest.mark.parametrize("number", range(1, 7))
def test_all_six_candidate_cohorts_come_from_existing_private_score_contract(number):
    package, brief, _, _ = denial(number)
    a = ProtectedHarmAudit.from_package(package, brief["defenders"])
    expected = package["scenario"]["scoring"]["metrics"][0]["plugin_parameters"]["protected_entities"]
    assert a.summary()["protected_ids"] == sorted(x["entity_id"] for x in expected)


def test_native_receipt_replay_and_opaque_renaming():
    r = native_receipt(); a = audit(); raw = a.consume(0, [r])
    b = audit(); b.consume(0, raw); assert a.summary() == b.summary()
    renamed = deepcopy(r)
    renamed["applied_intents"][0]["source_entity_id"] = "entity-89"
    renamed["applied_intents"][0]["target_entity_id"] = "entity-12"
    renamed["results"][0]["target_entity_id"] = "entity-12"
    c = ProtectedHarmAudit(["entity-89"], ["entity-12"]); c.consume(0, [renamed])
    assert c.summary()["defender_weapon_harm_rate"] == a.summary()["defender_weapon_harm_rate"]


def ledger_item(receipt, operation="native-operation"):
    return {"operation_id": operation, "fingerprint": "native-fingerprint", "receipt": receipt}


def test_complete_ledger_combines_immediate_and_later_damage_without_double_counting():
    a = audit()
    a.consume_checkpoint_ledger([ledger_item(native_receipt()),
        ledger_item(native_receipt(tick=1, before=0.7, after=0.4), "native-later")], 2)
    assert a.summary()["defender_weapon_hull_health_loss"] == pytest.approx(0.6)
    assert a.summary()["evidence_basis"] == "readonly_world_checkpoint_complete_combat_ledger"
    assert a.summary()["ledger_sha256"]


@pytest.mark.parametrize("failure", ["duplicate_operation", "missing_fingerprint", "missing_tick", "future_tick"])
def test_incomplete_or_duplicate_checkpoint_ledger_fails_atomically(failure):
    a = audit(); item = ledger_item(native_receipt()); ledger = [item]; end = 1
    if failure == "duplicate_operation": ledger.append(deepcopy(item))
    elif failure == "missing_fingerprint": item.pop("fingerprint")
    elif failure == "missing_tick": end = 2
    elif failure == "future_tick": item["receipt"] = native_receipt(tick=2)
    before = a.summary()
    with pytest.raises(ValueError): a.consume_checkpoint_ledger(ledger, end)
    assert a.summary() == before


def test_verified_noncombat_tail_includes_real_delayed_damage():
    a = audit(); a.consume_checkpoint_ledger([ledger_item(native_receipt())], 1)
    a.consume_verified_noncombat_tail(1, [native_receipt(tick=1, before=0.7, after=0.4)], [])
    assert a.summary()["checked_steps"] == 2
    assert a.summary()["defender_weapon_hull_health_loss"] == pytest.approx(0.6)
    assert a.summary()["evidence_basis"] == "complete_checkpoint_prefix_plus_verified_noncombat_tail"


@pytest.mark.parametrize("combat", [[{"status": "executed", "execution": {}}],
    [{"status": "rejected", "execution": {}}], [{"status": "unknown", "execution": None}]])
def test_tail_with_any_possible_immediate_combat_cannot_certify_zero_harm(combat):
    a = audit(); a.consume_checkpoint_ledger([ledger_item(native_receipt())], 1); before = a.summary()
    with pytest.raises(ValueError, match="immediate combat"):
        a.consume_verified_noncombat_tail(1, [native_receipt(tick=1)], combat)
    assert a.summary() == before

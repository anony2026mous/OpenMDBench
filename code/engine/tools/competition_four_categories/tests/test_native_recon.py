"""Referee mechanism fixtures, NOT privacy-passing competition episodes."""
from copy import deepcopy

import pytest

from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.reconnaissance import reconnaissance
from tools.competition_four_categories.recon_policy import SearchPolicy
from tools.competition_four_categories.recon_metrics_v1 import plain
from tools.competition_four_categories.emergency import event
from tools.competition_four_categories.validate_recon import submit_report
from tools.competition_four_categories.validate_denial import observe_slots, submit_navigation, authority
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


def advance(session, end):
    rows = []
    while session.world_view.tick < end:
        tick = session.world_view.tick
        rows.append(session.step(operation_id=f"tick-{tick}", expected_tick=tick))
    return rows


def mission(session):
    return plain(session.world_view.presentation_snapshot().mission_scoring_checkpoint)


def metric_state(session, metric):
    rows = plain(session.world_view.checkpoint().mission_scoring_checkpoint)["plugin_states"]
    return next(r["checkpoint"]["session_state"] for r in rows
                if r["checkpoint"]["session_state"]["parameters"]["metric_id"] == metric)


def report_fixture():
    p, brief, _, _ = reconnaissance(5)
    for e in p["scenario"]["entities"]:
        if e["faction_id"] == "blue":
            pos = [120., 350., 220.] if e["id"] == "unit.x01" else [120., -350., 0.]
            e["initial_state"].update(position_m=pos, velocity_mps=[0., 0., 0.])
    return p, brief


def send_observed(session, brief, sender):
    tick = session.world_view.tick
    observation = observe_slots(session, {sender: f"slot.{sender}"})[sender]
    b = deepcopy(brief); b["report_protocol"]["report_interval_ticks"] = 1
    payload = SearchPolicy(b, sender, "coordinated").report(observation)
    assert payload is not None, "fixture requires a real published native contact"
    submit_report(session, sender, "red", tick, payload)


def test_native_navigation_changes_real_sector_coverage_without_early_success():
    p, brief, _, _ = reconnaissance(2)
    s, _ = session_from(p, "recon-sector-coverage")
    try:
        advance(s, 5)
        assert mission(s)["score_state"]["metric.coverage"] == 0
        for tick in range(5, 110):
            if tick in (5, 60):
                identifier = "unit.r01" if tick == 5 else "unit.r04"
                submit_navigation(s, identifier, "red", tick, {"valid_until_tick": 130,
                    "payload": {"heading_deg": 90., "speed_mps": 12., "altitude_m": 120. if tick == 5 else 160.}})
            advance(s, tick+1)
            if tick == 59:
                state = metric_state(s, "metric.coverage")
                assert any(i["first_seen_tick"] is not None for i in state["groups"]["sector.01"]["items"].values())
                assert mission(s)["score_state"]["metric.coverage"] == 0
        assert s.world_view.get("unit.r01").state.position_m[0] > 500
        assert mission(s)["score_state"]["metric.coverage"] >= .5
        assert mission(s)["terminal_result"] is None
    finally:
        close(s)


def test_native_reports_are_delivered_after_delay_and_both_domains_are_required():
    p, brief = report_fixture()
    s, _ = session_from(p, "recon-report-delivery")
    try:
        advance(s, 3)
        assert mission(s)["score_state"]["metric.delivered_recall"] == 0
        assert not observe_slots(s, {"unit.r03": "slot.unit.r03"})["unit.r03"]["organic_contacts"]
        send_observed(s, brief, "unit.r01")
        advance(s, 6)
        assert not observe_slots(s, {"unit.r03": "slot.unit.r03"})["unit.r03"]["received_messages"]
        advance(s, 7)
        received = observe_slots(s, {"unit.r03": "slot.unit.r03"})["unit.r03"]["received_messages"]
        assert received
        assert mission(s)["score_state"]["metric.delivered_recall"] == 0
        state = metric_state(s, "metric.delivered_recall")
        assert state["groups"]["domain.air"]["items"]["unit.x01"]["first_seen_tick"] is not None
        send_observed(s, brief, "unit.r02")
        advance(s, 12)
        assert mission(s)["score_state"]["metric.delivered_recall"] == 1
    finally:
        close(s)


def test_native_outage_blocks_queued_report_without_awarding_handoff():
    p, brief = report_fixture()
    p["scenario"]["events"].append(event("event.report-outage", "component_suppression", 4,
        {"target_entity_id": "unit.r01", "component_ref": "communication.competition-recon-delayed@1.0.0", "duration_ticks": 20}))
    s, _ = session_from(p, "recon-report-blocked")
    try:
        advance(s, 3); send_observed(s, brief, "unit.r01"); advance(s, 9)
        assert not observe_slots(s, {"unit.r03": "slot.unit.r03"})["unit.r03"]["received_messages"]
        assert mission(s)["score_state"]["metric.delivered_recall"] == 0
        assert metric_state(s, "metric.delivered_recall")["groups"]["domain.air"]["items"]["unit.x01"]["first_seen_tick"] is None
    finally:
        close(s)


def test_native_weather_causes_loss_then_recovery_not_credit_from_old_contacts():
    p, _, _, _ = reconnaissance(6)
    for actor in p["scenario"]["entities"]:
        if actor["id"] == "unit.x01":
            actor["initial_state"].update(position_m=[300., 350., 220.], velocity_mps=[0., 0., 0.])
    for item in p["scenario"]["events"]:
        if item["id"] == "event.weather-onset": item["trigger"]["tick"] = 6
        if item["id"] == "event.weather-clear": item["trigger"]["tick"] = 12
    s, _ = session_from(p, "recon-weather-evidence")
    def sees():
        contacts = observe_slots(s, {"unit.r01": "slot.unit.r01"})["unit.r01"]["organic_contacts"]
        return any("unit.x01" in c["contact_id"] and c["age_ticks"] <= 1 for c in contacts)
    try:
        early = []
        for tick in range(1, 6):
            advance(s, tick); early.append(sees())
        assert any(early), {"visibility": early, "own": observe_slots(s, {"unit.r01": "slot.unit.r01"}),
                            "target_position": s.world_view.get("unit.x01").state.position_m}
        advance(s, 9); assert not sees()
        late = []
        for tick in range(13, 18):
            advance(s, tick); late.append(sees())
        assert any(late)
        assert mission(s)["terminal_result"] is None
    finally:
        close(s)


def test_native_late_wave_has_real_spawn_authority_and_cannot_end_early():
    p, _, _, _ = reconnaissance(7); scenario = p["scenario"]
    scenario["world"]["duration_ticks"] = 21
    for metric in scenario["scoring"]["metrics"]:
        for g in metric["plugin_parameters"]["groups"]:
            if g["start_tick"] == 86: g.update(start_tick=6, end_tick=10)
            elif g["start_tick"] == 166: g.update(start_tick=11, end_tick=21)
            else: g["end_tick"] = 5 if g["end_tick"] == 81 else 21
    scenario["mission_rules"][0]["condition"]["parameters"]["conditions"][0]["parameters"]["tick"] = 21
    scenario["mission_rules"][1]["condition"]["parameters"]["tick"] = 21
    for item in scenario["events"]:
        item["trigger"]["tick"] = {85: 5, 165: 10, 60: 4, 150: 9, 241: 21}[item["trigger"]["tick"]]
        if "duration_ticks" in item["payload"]: item["payload"]["duration_ticks"] = 3
    s, _ = session_from(p, "recon-late-wave")
    try:
        advance(s, 4); assert s.world_view.get_optional("unit.x02") is None
        advance(s, 5); assert s.world_view.get_optional("unit.x02") is not None
        assert authority(s, "unit.x02")
        assert observe_slots(s, {"unit.x02": "controller/unit.x02"})["unit.x02"]["own_entities"]
        advance(s, 20); assert mission(s)["terminal_result"] is None
        advance(s, 21); assert mission(s)["terminal_result"]["outcome"] == "objective_incomplete"
        assert mission(s)["score_state"]["metric.discovery"] == 0
    finally:
        close(s)


def test_native_recon_checkpoint_preserves_nonzero_delivered_history():
    p, brief = report_fixture()
    original, catalog = session_from(p, "recon-delivery-checkpoint")
    restored = None
    try:
        advance(original, 3); send_observed(original, brief, "unit.r01"); advance(original, 7)
        before = metric_state(original, "metric.delivered_recall")
        assert before["groups"]["domain.air"]["items"]["unit.x01"]["first_seen_tick"] is not None
        checkpoint = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=checkpoint, expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=original.resolved, expected_resolved_hash=original.resolved.resolved_hash,
            model_registry=catalog.model_registry, expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        for tick in range(8, 13):
            advance(original, tick); advance(restored, tick)
            assert mission(original) == mission(restored)
    finally:
        close(original)
        if restored is not None: close(restored)


@pytest.mark.parametrize("family", ["REC", "TRK", "AD", "ER"])
def test_native_simultaneous_terminal_rules_keep_distinct_receipt_events(family):
    from tools.competition_four_categories.tracking import tracking
    from tools.competition_four_categories.denial import denial
    from tools.competition_four_categories.emergency import emergency

    factory, number = {"REC": (reconnaissance, 4), "TRK": (tracking, 1),
                       "AD": (denial, 1), "ER": (emergency, 1)}[family]
    package = factory(number)[0]
    # This short fixture isolates terminal arbitration, not task feasibility.
    # Both rules intentionally qualify; native priority must still pick success.
    deadline = deepcopy(package["scenario"]["mission_rules"][1]["condition"])
    deadline["parameters"]["tick"] = 4
    for rule in package["scenario"]["mission_rules"]:
        rule["condition"] = deepcopy(deadline)
    session, _ = session_from(package, f"{family.lower()}-terminal-receipt")
    try:
        advance(session, 4)
        assert mission(session)["terminal_result"]["outcome"] == "objective_complete"
        assert mission(session)["terminal_result"]["rule_id"] == "rule.success"
        checkpoint = session.checkpoint()
        assert checkpoint.checkpoint_hash
        state = plain(session.world_view.checkpoint().mission_scoring_checkpoint)
        terminal_receipt = next(row["receipt"] for row in state["operation_receipts"]
                                if row["kind"] == "mission" and row["receipt"]["tick"] == 4)
        assert terminal_receipt["triggered_rule_ids"] == ["rule.success", "rule.timeout"]
        assert len(terminal_receipt["emitted_event_ids"]) == 2
    finally:
        close(session)

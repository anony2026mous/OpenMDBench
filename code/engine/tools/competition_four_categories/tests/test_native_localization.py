"""Bounded native sensing fixtures, not full competition acceptance."""
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tracking_policy import ScheduledNavigationPolicy
from tools.competition_four_categories.validate_tracking import observe, submit_navigation, score_evidence
from tools.competition_four_categories.native_localization_audit import NativeContactLocalizationAudit, measure
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


def simulate(capture):
    package, brief, _, plan = tracking(1)
    opponent = ScheduledNavigationPolicy(plan)
    session, _ = session_from(package, "native-localization-noninterference")
    audit = NativeContactLocalizationAudit(brief["observers"], opponent.entity_ids)
    projections, truths_before, truths_after = [], {}, {}
    try:
        for tick in range(12):
            for identifier in opponent.entity_ids:
                truths_before[tick, identifier] = list(session.world_view.get(identifier).state.position_m)
            for identifier, command in opponent.commands(tick, observe(session, opponent.entity_ids)).items():
                submit_navigation(session, identifier=identifier, faction=plan["faction_id"], tick=tick,
                    payload=command["payload"], valid_until_tick=command["valid_until_tick"])
            step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            observations = observe(session, brief["observers"])
            frame = session.world_view.presentation_snapshot()
            if capture:
                audit.capture(step.world_receipt, frame, observations)
            for identifier in opponent.entity_ids:
                truths_after[tick, identifier] = list(session.world_view.get(identifier).state.position_m)
            projections.append({"tick": frame.tick, "observations": observations,
                "target_observations": observe(session, opponent.entity_ids), "scores": score_evidence(step)})
        return audit, projections, truths_before, truths_after
    finally:
        close(session)


def test_native_geometry_is_time_aligned_and_audit_does_not_change_projection():
    _, without, _, _ = simulate(False)
    audit, with_audit, before, after = simulate(True)
    assert with_audit == without
    assert audit.summary()["checked_steps"] == 12
    assert audit.summary()["pooled"]["sample_count"] > 0
    moved = False
    for item in audit.evidence()["samples"]:
        source = item["evidence"]["sensor_receipt"]
        key = source["tick"], source["target_entity_id"]
        assert list(source["target_position_m"]) == after[key]
        moved |= before[key] != after[key]
        assert measure(item["evidence"]) == item["measurement"]
    assert moved, "Fixture must actually move a target to distinguish adjacent clocks"

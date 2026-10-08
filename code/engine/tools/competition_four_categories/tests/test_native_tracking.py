"""Native mechanism fixtures, explicitly not fair-agent competition acceptance."""
from copy import deepcopy

from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tracking_policy import ScheduledNavigationPolicy
from tools.competition_four_categories.validate_tracking import observe, submit_navigation
from tools.competition_four_categories.tests.test_native_candidate import session_from, close


def advance(session, end, opponent=None):
    while session.world_view.tick < end:
        tick = session.world_view.tick
        if opponent is not None:
            for identifier, command in opponent.commands(tick, observe(session, opponent.entity_ids)).items():
                submit_navigation(session, identifier=identifier, faction=opponent.plan["faction_id"],
                    tick=tick, payload=command["payload"], valid_until_tick=command["valid_until_tick"])
        session.step(operation_id=f"tick-{tick}", expected_tick=tick)


def own(session, identifier):
    return observe(session, [identifier])[identifier]["own_entities"][0]


def mission(session):
    return session.world_view.presentation_snapshot().mission_scoring_checkpoint


def test_scripted_surface_contact_moves_using_native_mmg_actions():
    package, _, _, plan = tracking(1)
    session, _ = session_from(package, "tracking-mmg-motion")
    try:
        before = own(session, "unit.x01")["position_m"]
        advance(session, 12, ScheduledNavigationPolicy(plan))
        after = own(session, "unit.x01")
        assert after["position_m"][0] > before[0] + .1
        assert after["velocity_mps"][0] > 0
        assert mission(session)["terminal_result"] is None
    finally:
        close(session)


def test_scripted_aircraft_turn_changes_actual_velocity_after_command():
    package, _, _, plan = tracking(4)
    session, _ = session_from(package, "tracking-air-turns")
    opponent = ScheduledNavigationPolicy(plan)
    try:
        advance(session, 69, opponent)
        before = own(session, "unit.x01")["velocity_mps"]
        assert before[0] > 7 and abs(before[1]) < 1
        advance(session, 80, opponent)
        north = own(session, "unit.x01")["velocity_mps"]
        south = own(session, "unit.x02")["velocity_mps"]
        assert north[1] > 7 and south[1] < -7
        assert abs(north[0]) < 1 and abs(south[0]) < 1
        assert "marker.turn-70" in session.world_view.presentation_snapshot().event_state.mission_marker_ledger
    finally:
        close(session)


def test_native_sensor_windows_create_real_air_to_surface_transfer():
    package, _, _, _ = tracking(3)
    # Isolate the transfer mechanism: hold both targets and preposition the USV.
    # This fixture is not a claim that the original full episode is solved.
    for e in package["scenario"]["entities"]:
        if e["id"] == "unit.r03":
            e["initial_state"]["position_m"] = [300., 0., 0.]
        if e["faction_id"] == "blue":
            e["initial_state"]["velocity_mps"] = [0., 0., 0.]
    session, _ = session_from(package, "tracking-native-handover")
    try:
        advance(session, 40)
        assert mission(session)["score_state"]["metric.handover"] == 0
        observed_surface_contacts = set()
        for tick in range(41, 63):
            advance(session, tick)
            contacts = observe(session, ["unit.r03"])["unit.r03"]["organic_contacts"]
            observed_surface_contacts.update(c["contact_id"] for c in contacts if c["age_ticks"] <= 2)
        assert mission(session)["score_state"]["metric.handover"] == 1
        assert mission(session)["terminal_result"] is None
        # A 0.9-probability sensor need not detect every target at one final instant.
        # Require real fresh observations of both throughout the transfer window.
        assert len(observed_surface_contacts) >= 2
    finally:
        close(session)


def test_native_fog_reduces_fresh_detection_not_only_a_label():
    fog = tracking(5)[0]
    for e in fog["scenario"]["entities"]:
        if e["faction_id"] == "blue":
            e["initial_state"]["velocity_mps"] = [0., 0., 0.]
    clear = deepcopy(fog)
    for event in clear["scenario"]["events"]:
        if event["event_type"] == "weather_change":
            event["payload"]["environment_ref"] = "environment.clear@2.0.0"
    a, _ = session_from(fog, "tracking-fog")
    b, _ = session_from(clear, "tracking-clear")
    observers = tracking(5)[1]["observers"]
    try:
        advance(a, 84)
        advance(b, 84)
        def count(session):
            return sum(c["age_ticks"] <= 2 for o in observe(session, observers).values() for c in o["organic_contacts"])
        assert count(a) < count(b)
        assert a.world_view.presentation_snapshot().event_state.weather_state["event_id"] == "event.fog"
    finally:
        close(a)
        close(b)


def test_tracking_cannot_terminate_when_initial_contacts_are_acquired():
    package = tracking(1)[0]
    s = package["scenario"]
    s["world"]["duration_ticks"] = 7
    for metric in s["scoring"]["metrics"]:
        metric["plugin_parameters"].update(start_tick=1, end_tick=7)
    s["mission_rules"][0]["condition"]["parameters"]["conditions"][0]["parameters"]["tick"] = 7
    s["mission_rules"][1]["condition"]["parameters"]["tick"] = 7
    s["events"][0]["trigger"]["tick"] = 7
    session, _ = session_from(package, "tracking-until-horizon")
    try:
        for tick in range(1, 7):
            advance(session, tick)
            assert mission(session)["terminal_result"] is None
        assert mission(session)["score_state"]["metric.continuity"] >= .7
        advance(session, 7)
        assert mission(session)["terminal_result"]["outcome"] == "objective_complete"
        assert mission(session)["terminal_result"]["tick"] == 7
    finally:
        close(session)


def test_native_tracking_checkpoint_preserves_nonzero_per_target_history():
    package, _, _, plan = tracking(1)
    original, catalog = session_from(package, "tracking-checkpoint")
    opponent = ScheduledNavigationPolicy(plan)
    restored = None
    try:
        advance(original, 29, opponent)
        assert mission(original)["score_state"]["metric.continuity"] > 0
        cp = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=cp, expected_checkpoint_hash=cp.checkpoint_hash,
            resolved=original.resolved, expected_resolved_hash=original.resolved.resolved_hash,
            model_registry=catalog.model_registry, expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        for tick in range(30, 40):
            advance(original, tick, opponent)
            advance(restored, tick, opponent)
            assert mission(original) == mission(restored)
            assert own(original, "unit.x01") == own(restored, "unit.x01")
        # Full-world hash equality is a separate failing gate retained in ER tests.
    finally:
        close(original)
        if restored is not None:
            close(restored)


def test_tracking_delayed_link_has_real_transport_delay_and_loss_probability():
    session, _ = session_from(tracking(8)[0], "tracking-delayed-link")
    try:
        for index in range(3):
            label = f"probe.{index}"
            action = DiscreteActionV2(schema_version="2.0", action_id=label, action_type="send_message",
                entity_id="unit.r04", faction_id="red", based_on_tick=0, valid_until_tick=8,
                payload={"recipient_controller_slots": ["slot.unit.r01"], "message": label})
            session.submit_actions(batch=ActionBatchV2(schema_version="2.0", session_id=session.session_id,
                batch_id=label, idempotency_key=label, faction_id="red", based_on_tick=0, valid_until_tick=8, discrete_actions=(action,)),
                authority_token="authority.unit.r04", operation_id=label, expected_tick=0)
        advance(session, 2)
        assert not observe(session, ["unit.r01"])["unit.r01"]["received_messages"]
        advance(session, 5)
        messages = observe(session, ["unit.r01"])["unit.r01"]["received_messages"]
        assert messages and all(m["delivered_tick"] >= 3 for m in messages)
        queued = session.world_view.presentation_snapshot().event_state.message_queue
        records = [r for r in queued if str(r.get("origin_message_id", "")).startswith("probe.")]
        assert len(records) == 3
        assert all(r["delay_ticks"] == 3 and r["loss_probability"] == .1 for r in records)
    finally:
        close(session)

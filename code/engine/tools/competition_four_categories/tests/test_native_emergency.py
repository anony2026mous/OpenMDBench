"""Bounded mechanism evidence, not acceptance of the complete ER contracts."""
from copy import deepcopy
import json

from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.emergency import emergency
from tools.competition_four_categories.message_policy import ScheduledMessagePolicy
from tools.competition_four_categories.response import response
from tools.competition_four_categories.validate_denial import observe_slots
from tools.competition_four_categories.validate_emergency import DispatchPolicy, audit_observations, run
from tools.competition_four_categories.validate_response import submit_source_messages
from tools.competition_four_categories.tests.test_native_candidate import (
    assert_restored_world_semantics_equal,
    close,
    facts,
    navigate,
    session_from,
)


def step_to(session, tick):
    while session.world_view.tick < tick:
        current = session.world_view.tick
        session.step(operation_id=f"tick-{current}", expected_tick=current)


def observation(session, identifier="unit.r01"):
    return session.world_view.controller_observation(controller_slot_id=f"slot.{identifier}").model_dump(mode="json")


def send(session, label):
    tick = session.world_view.tick
    action = DiscreteActionV2(schema_version="2.0", action_id=label, action_type="send_message",
        entity_id="unit.r03", faction_id="red", based_on_tick=tick, valid_until_tick=tick+5,
        payload={"recipient_controller_slots": ["slot.unit.r01"], "message": label})
    return session.submit_actions(batch=ActionBatchV2(schema_version="2.0", session_id=session.session_id,
        batch_id=f"batch-{label}", idempotency_key=f"batch-{label}", faction_id="red",
        based_on_tick=tick, valid_until_tick=tick+5, discrete_actions=(action,)),
        authority_token="authority.unit.r03", operation_id=f"send-{label}", expected_tick=tick)


def test_native_weather_changes_actual_motion_not_only_metadata():
    storm = emergency(1)[0]
    clear = deepcopy(storm)
    clear["scenario"]["events"][0]["payload"]["environment_ref"] = "environment.clear@2.0.0"
    a, _ = session_from(storm, "weather-storm")
    b, _ = session_from(clear, "weather-clear")
    try:
        navigate(a)
        navigate(b)
        step_to(a, 10)
        step_to(b, 10)
        assert facts(a)["own"] == facts(b)["own"]
        step_to(a, 20)
        step_to(b, 20)
        assert observation(a)["own_entities"][0]["position_m"][0] < observation(b)["own_entities"][0]["position_m"][0] - 35
        assert a.world_view.presentation_snapshot().event_state.weather_state["event_id"] == "event.weather"
    finally:
        close(a)
        close(b)


def test_native_radar_outage_removes_fresh_station_contacts():
    session, _ = session_from(emergency(2)[0], "radar-outage")
    try:
        step_to(session, 15)
        before = observation(session, "unit.r03")["organic_contacts"]
        assert any(c["age_ticks"] <= 1 for c in before)
        step_to(session, 22)
        after = observation(session, "unit.r03")["organic_contacts"]
        assert not any(c["age_ticks"] <= 1 for c in after)
        state = session.world_view.presentation_snapshot().event_state
        assert "unit.r03|sensor.competition-shore-easy@1.0.0" in state.component_suppressions
    finally:
        close(session)


def test_native_blackout_blocks_message_and_recovery_restores_delivery():
    session, _ = session_from(emergency(4)[0], "blackout-delivery")
    try:
        send(session, "probe.before")
        step_to(session, 3)
        assert any(m["payload"] == "probe.before" for m in observation(session)["received_messages"])
        step_to(session, 15)
        assert "outage.01" in session.world_view.presentation_snapshot().event_state.jamming_sessions
        send(session, "probe.during")
        step_to(session, 20)
        assert not any(m["payload"] == "probe.during" for m in observation(session)["received_messages"])
        step_to(session, 91)
        assert not session.world_view.presentation_snapshot().event_state.jamming_sessions
        send(session, "probe.after")
        step_to(session, 94)
        assert any(m["payload"] == "probe.after" for m in observation(session)["received_messages"])
    finally:
        close(session)


def test_er003_native_source_notice_reaches_actual_authorized_controllers():
    package, _, _, plan = response(3)
    assert not [event for event in package["scenario"]["events"] if event["event_type"] == "message"]
    source = ScheduledMessagePolicy(plan)
    session, _ = session_from(package, "native-message-gate")
    try:
        while session.world_view.tick < 19:
            tick = session.world_view.tick
            source_observations = observe_slots(session, source.plan["controller_slots"])
            due = source.actions(tick, source_observations)
            submit_source_messages(session, actions=due, faction=source.plan["faction_id"], tick=tick)
            session.step(operation_id=f"tick-{tick}", expected_tick=tick)
        for identifier in ("unit.r01", "unit.r02"):
            messages = observation(session, identifier)["received_messages"]
            delivered = [message for message in messages if json.loads(message["payload"])["request_id"] == "task.01"]
            assert delivered
            assert delivered[0]["sender_entity_id"] == "unit.r03"
    finally:
        close(session)


def test_native_dispatch_checkpoint_preserves_partial_dwell_and_weather():
    package = emergency(1)[0]
    s = package["scenario"]
    s["world"]["zones"][0]["coordinates_m"] = [[-30., -30.], [30., -30.], [30., 30.], [-30., 30.]]
    for metric in s["scoring"]["metrics"]:
        metric["plugin_parameters"]["requests"][0]["dwell_ticks"] = 40
    original, catalog = session_from(package, "dispatch-checkpoint")
    restored = None
    try:
        step_to(original, 16)
        checkpoint = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=checkpoint,
            expected_checkpoint_hash=checkpoint.checkpoint_hash, resolved=original.resolved,
            expected_resolved_hash=original.resolved.resolved_hash, model_registry=catalog.model_registry,
            expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        for tick in range(17, 42):
            step_to(original, tick)
            step_to(restored, tick)
            assert facts(original) == facts(restored)
        assert facts(original)["terminal"]["outcome"] == "objective_complete"
        assert_restored_world_semantics_equal(
            original.checkpoint().world_checkpoint, restored.checkpoint().world_checkpoint
        )
    finally:
        close(original)
        if restored is not None:
            close(restored)


def test_candidate_rename_and_input_reorder_leave_native_behavior_equal():
    package = emergency(1)[0]
    renamed = deepcopy(package)
    renamed["scenario"]["scenario_id"] = "independent-name"
    for field in ("entities", "controller_slots", "events", "mission_rules"):
        renamed["scenario"][field].reverse()
    a, _ = session_from(package, "ordering-original")
    b, _ = session_from(renamed, "ordering-renamed")
    try:
        navigate(a)
        navigate(b)
        for tick in range(1, 21):
            step_to(a, tick)
            step_to(b, tick)
            assert facts(a) == facts(b)
    finally:
        close(a)
        close(b)


def test_safe_route_wins_direct_route_fails_and_idle_cannot_win():
    safe, direct, idle = [run(1, policy, 601) for policy in ("safe", "direct", "idle")]
    assert all(r["failure"] is None for r in (safe, direct, idle))
    assert safe["terminal"]["outcome"] == "objective_complete"
    assert direct["scores"]["metric.arrival"] == 1
    assert direct["scores"]["metric.safety"] == 0
    assert direct["terminal"]["outcome"] == "objective_incomplete"
    assert idle["scores"]["metric.arrival"] == 0
    assert idle["terminal"]["outcome"] == "objective_incomplete"


def test_policy_waits_for_real_inbox_and_ignores_unverified_alert():
    import json
    _, brief, _ = emergency(3)
    policy = DispatchPolicy(brief, "safe")
    obs = {"unit.r01": {"own_entities": [{"position_m": [0, 0, 100]}], "received_messages": []}}
    assert policy.commands(obs) == {}
    body = {"request_id": "alert.01", "priority": 3, "status": "unverified",
            "destination": {"coordinates_m": [[900, -50], [1000, -50], [1000, 50], [900, 50]]}}
    obs["unit.r01"]["received_messages"] = [{"message_id": "message.1", "payload": json.dumps(body)}]
    assert policy.commands(obs) == {}
    body["status"] = "confirmed"
    obs["unit.r01"]["received_messages"] = [{"message_id": "message.2", "payload": json.dumps(body)}]
    assert policy.commands(obs)["unit.r01"]["heading_deg"] == 90


def test_blackout_preissued_command_reaches_destination_without_new_commands():
    result = run(4, "preissued", 601)
    assert result["failure"] is None
    assert result["submitted_command_ticks"] == [0]
    assert result["terminal"]["outcome"] == "objective_complete"
    assert result["final_tick"] < 90
    assert any(row["referee_event_evidence"]["active_jamming_sessions"] for row in result["trace"])


def test_malformed_shared_transport_record_still_fails_and_is_preserved():
    observed = {"organic_contacts": [], "shared_contacts": [{"shared_contact_id": "shared-unit.x01"}]}
    failure = audit_observations({"own": observed})
    assert failure["status"] == "FAILED_PRIVACY_GATE"
    # The record remains invalid for missing schema/scope/transport proof,
    # not merely because a legitimately detected identifier could contain unit.x.
    assert failure["violation"] == "observation_schema"
    assert failure["audit_contract"] == "native-visibility-evidence@1.0"
    assert failure["observed_contact_records"]["shared_contacts"] == observed["shared_contacts"]

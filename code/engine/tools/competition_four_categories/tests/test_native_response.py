"""Native mechanism fixtures; not a blanket competition release claim."""
from copy import deepcopy

from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.response import response
from tools.competition_four_categories.emergency import event
from tools.competition_four_categories.message_policy import ScheduledMessagePolicy
from tools.competition_four_categories.validate_response import submit_source_messages
from tools.competition_four_categories.validate_denial import observe_slots
from tools.competition_four_categories.recon_metrics_v1 import plain
from tools.competition_four_categories.tests.test_native_candidate import (
    assert_restored_world_semantics_equal,
    close,
    session_from,
)


def fixture():
    package, brief, _, plan = response(3)
    for e in package["scenario"]["entities"]:
        if e["id"] == "unit.r01":
            e["initial_state"]["position_m"] = [1200., 0., 100.]
    first = deepcopy(plan["messages"][0]); first.update(send_tick=3, recipient_controller_slots=["slot.unit.r01"])
    plan["messages"] = [first]
    return package, brief, plan


def advance(session, end, plan=None):
    source = ScheduledMessagePolicy(plan) if plan else None
    while session.world_view.tick < end:
        tick = session.world_view.tick
        if source is not None:
            obs = observe_slots(session, source.plan["controller_slots"])
            submit_source_messages(session, actions=source.actions(tick, obs), faction=source.plan["faction_id"], tick=tick)
        session.step(operation_id=f"tick-{tick}", expected_tick=tick)


def model_state(session, identifier="metric.arrival"):
    cp = plain(session.world_view.checkpoint().mission_scoring_checkpoint)
    return next(row["checkpoint"]["session_state"] for row in cp["plugin_states"]
                if row["checkpoint"]["session_state"]["parameters"]["metric_id"] == identifier)


def inbox(session, identifier="unit.r01"):
    return observe_slots(session, {identifier: f"slot.{identifier}"})[identifier]["received_messages"]


def test_native_prepositioned_responder_needs_delivery_then_real_dwell():
    package, _, plan = fixture()
    session, _ = session_from(package, "response-prepositioned")
    try:
        advance(session, 3, plan)
        assert not model_state(session)["arrivals"]
        assert not inbox(session)
        advance(session, 5, plan)
        assert inbox(session)
        state = model_state(session)
        assert state["notices"]["task.01"]["unit.r01"]["origin"] == "native_delivery"
        assert "task.01" not in state["arrivals"]
        advance(session, 8, plan)
        arrived = model_state(session)["arrivals"]["task.01"]
        assert arrived["observer_id"] == "unit.r01"
        assert arrived["delivered_tick"] == inbox(session)[0]["delivered_tick"]
        assert arrived["latency_ticks"] >= 2
    finally: close(session)


def test_native_other_recipient_notification_cannot_credit_prepositioned_peer():
    package, _, plan = fixture()
    plan["messages"][0]["recipient_controller_slots"] = ["slot.unit.r02"]
    plan["messages"].append({**deepcopy(plan["messages"][0]), "message_id": "notice.real-peer",
        "send_tick": 8, "recipient_controller_slots": ["slot.unit.r01"]})
    session, _ = session_from(package, "response-recipient-scope")
    try:
        advance(session, 7, plan)
        state = model_state(session)
        assert "unit.r02" in state["notices"]["task.01"]
        assert "unit.r01" not in state["notices"]["task.01"]
        assert "task.01" not in state["arrivals"]
        advance(session, 13, plan)
        assert model_state(session)["arrivals"]["task.01"]["observer_id"] == "unit.r01"
    finally: close(session)


def test_native_message_from_untrusted_actor_is_delivered_but_does_not_release_task():
    package, _, plan = fixture()
    plan["controller_slots"] = {"unit.r02": "slot.unit.r02"}
    plan["messages"][0]["sender_id"] = "unit.r02"
    session, _ = session_from(package, "response-untrusted-source")
    try:
        advance(session, 9, plan)
        assert inbox(session)
        assert inbox(session)[0]["sender_entity_id"] == "unit.r02"
        assert model_state(session)["notices"]["task.01"] == {}
        assert "task.01" not in model_state(session)["arrivals"]
    finally: close(session)


def test_native_blackout_requires_actual_retransmission_after_recovery():
    package, _, plan = fixture()
    package["scenario"]["events"].append(event("event.blackout-test", "component_suppression", 2,
        {"target_entity_id": "unit.r01", "component_ref": "communication.competition-dispatch@1.0.0", "duration_ticks": 6}))
    plan["messages"].append({**deepcopy(plan["messages"][0]), "message_id": "notice.retry", "send_tick": 10})
    session, _ = session_from(package, "response-blackout-retry")
    try:
        advance(session, 9, plan)
        assert not inbox(session)
        assert model_state(session)["notices"]["task.01"] == {}
        advance(session, 15, plan)
        assert inbox(session)
        arrival = model_state(session)["arrivals"]["task.01"]
        assert arrival["delivered_tick"] >= 10
    finally: close(session)


def test_native_delivered_dwell_checkpoint_preserves_exact_plugin_state():
    package, _, plan = fixture()
    original, catalog = session_from(package, "response-checkpoint")
    restored = None
    try:
        advance(original, 5, plan)
        state = model_state(original)
        assert state["dwell"]["task.01"]["unit.r01"] == 1
        checkpoint = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=checkpoint, expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=original.resolved, expected_resolved_hash=original.resolved.resolved_hash,
            model_registry=catalog.model_registry, expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        assert model_state(restored) == state
        for tick in range(6, 11):
            advance(original, tick, plan); advance(restored, tick, plan)
            for metric in ("metric.arrival", "metric.timeliness", "metric.safety", "metric.triage"):
                assert model_state(original, metric) == model_state(restored, metric)
            assert inbox(original) == inbox(restored)
        assert_restored_world_semantics_equal(
            original.checkpoint().world_checkpoint, restored.checkpoint().world_checkpoint
        )
    finally:
        close(original)
        if restored is not None: close(restored)

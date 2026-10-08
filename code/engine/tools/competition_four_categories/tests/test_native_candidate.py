"""Bounded native checks for the new pilot only, not full-suite acceptance."""
from collections.abc import Mapping
from copy import deepcopy

import pytest

from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2, SessionFailureV2
from openmdbench.world.factory_v2 import WorldFactoryV2
from tools.competition_four_categories.build import reconnaissance
from tools.competition_four_categories.runtime import load_candidate_catalog, compile_package


def session_from(package, name):
    resolved, catalog = compile_package(package)
    session = SessionLifecycleV2.create(session_id=name, seed=601, resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash, catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode="lockstep", physics_dt_seconds=1., decision_interval_ticks=1)
    return session.load().start(), catalog

def close(session):
    if session.state.value == "running":
        session.stop()
    session.close()

def navigate(session, entity_id="unit.r01", faction="red"):
    command = PersistentCommandV2(schema_version="2.0", entity_id=entity_id, faction_id=faction,
        based_on_tick=0, valid_until_tick=180, command_id="navigate", command_type="navigation",
        payload={"heading_deg": 90., "speed_mps": 22., "altitude_m": 100.})
    batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id, batch_id="batch",
        idempotency_key="batch", faction_id=faction, based_on_tick=0, valid_until_tick=180,
        persistent_commands=(command,))
    return session.submit_actions(batch=batch, authority_token="authority.unit.r01",
                                  operation_id="submit", expected_tick=0)

def facts(session):
    obs = session.world_view.controller_observation(controller_slot_id="slot.unit.r01")
    mission = session.world_view.presentation_snapshot().mission_scoring_checkpoint
    return {"own": obs.model_dump(mode="json")["own_entities"],
            "scores": dict(mission["score_state"]),
            "terminal": deepcopy(mission["terminal_result"])}


def assert_restored_world_semantics_equal(left, right):
    """Compare all durable world state except fresh-adapter provenance hashes.

    A restored world creates fresh dynamics adapter instances.  Their private
    instance/output receipt identities are deliberately included in subsequent
    motion fingerprints, although the committed motion receipt and every other
    checkpoint field remain identical.  This assertion permits only that
    provenance-only difference; it does not discard motion, event, mission,
    communication, entity, RNG, or plugin state.
    """
    def thaw(value):
        if isinstance(value, Mapping):
            return {str(key): thaw(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [thaw(item) for item in value]
        return value

    payloads = [thaw(value) for value in (left, right)]
    for payload in payloads:
        payload.pop("checkpoint_hash", None)
        for receipt in payload.get("motion_ledger", ()):
            receipt.pop("fingerprint", None)
    assert payloads[0] == payloads[1]

def test_native_checkpoint_continuation_preserves_nonzero_metric_history():
    original, catalog = session_from(reconnaissance("easy")[0], "checkpoint-candidate")
    restored = None
    try:
        navigate(original)
        for tick in range(50):
            original.step(operation_id=f"tick-{tick}", expected_tick=tick)
        assert facts(original)["scores"]["metric.coverage"] == .5
        checkpoint = original.checkpoint()
        restored = SessionLifecycleV2.restore(checkpoint=checkpoint,
            expected_checkpoint_hash=checkpoint.checkpoint_hash, resolved=original.resolved,
            expected_resolved_hash=original.resolved.resolved_hash,
            model_registry=catalog.model_registry,
            expected_model_registry_hash=original.resolved.model_registry_hash,
            world_factory=WorldFactoryV2(model_registry=catalog.model_registry))
        for tick in range(50, 68):
            for session in (original, restored):
                session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            assert facts(original) == facts(restored)
        assert facts(original)["terminal"]["outcome"] == "objective_complete"
    finally:
        close(original)
        if restored is not None:
            close(restored)

def test_native_deadline_achievement_beats_timeout_during_settling_tick():
    package = reconnaissance("easy")[0]
    scenario = package["scenario"]
    scenario["world"]["duration_ticks"] = 2
    for zone in scenario["world"]["zones"]:
        zone["coordinates_m"] = [[-20., -20.], [20., -20.], [20., 20.], [-20., 20.]]
    for metric in scenario["scoring"]["metrics"]:
        metric["plugin_parameters"]["end_tick"] = 2
    condition = scenario["mission_rules"][0]["condition"]
    condition["operator"] = "score"
    condition["parameters"] = {"metric_id": "metric.coverage", "comparison": ">=", "value": 1.}
    scenario["mission_rules"][1]["condition"]["parameters"]["tick"] = 2
    for event in scenario["events"]:
        event["trigger"]["tick"] = 2
    session, _ = session_from(package, "deadline-candidate")
    try:
        session.step(operation_id="tick-0", expected_tick=0)
        assert facts(session)["scores"]["metric.coverage"] == 1.
        assert facts(session)["terminal"] is None
        session.step(operation_id="tick-1", expected_tick=1)
        assert facts(session)["terminal"]["outcome"] == "objective_complete"
    finally:
        close(session)

def test_native_controller_cannot_navigate_another_faction():
    session, _ = session_from(reconnaissance("easy")[0], "unauthorized-candidate")
    try:
        with pytest.raises(SessionFailureV2):
            navigate(session, entity_id="unit.x01", faction="blue")
        assert session.world_view.tick == 0
    finally:
        close(session)

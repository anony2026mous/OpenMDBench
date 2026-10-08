"""Jamming isolates shared reports without erasing friendly base own-state."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.scenarios.formal_v2 import load_formal_scenario_v2
from openmdbench.schemas.core_v2 import ObservationV2
from openmdbench.sessions.lifecycle_v2 import RunnerModeV2, SessionLifecycleV2
from openmdbench.world.combat_evidence_v2 import WorldContactEvidenceV2
from openmdbench.world.factory_v2 import WorldFactoryV2


def _session_with_short_jamming_window() -> SessionLifecycleV2:
    _package, catalog = load_formal_scenario_v2("MD-AD-002-HARD")
    payload = yaml.safe_load(Path("scenarios/formal/md_ad_002_hard/scenario.yaml").read_bytes())
    document = copy.deepcopy(payload["scenario"])
    document["scenario_id"] = "third-party.communication-observation.v2"
    document["display_name"] = "第三方通信观测隔离示例"
    for event in document["events"]:
        if event["id"] == "event.jamming-start":
            event["trigger"]["tick"] = 2
        elif event["id"] == "event.jamming-end":
            event["trigger"]["tick"] = 3
    resolved = ScenarioCompilerV2(catalog=catalog).compile(
        ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": document})
    )
    return SessionLifecycleV2.create(
        session_id="session.communication-observation",
        seed=73,
        resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=RunnerModeV2.LOCKSTEP,
        physics_dt_seconds=float(resolved.world.tick_seconds or 1.0),
        decision_interval_ticks=1,
    )


def _contact(*, evidence_id: str, owner_entity_id: str) -> WorldContactEvidenceV2:
    return WorldContactEvidenceV2(
        evidence_id=evidence_id,
        owner_entity_id=owner_entity_id,
        target_entity_id="intruder.wave-1-001",
        observed_tick=1,
        age_ticks=0,
        max_age_ticks=3,
        confidence=0.9,
        minimum_confidence=0.0,
        quality=0.9,
    )


def _entity_ids(observation: ObservationV2) -> set[str]:
    return {item["entity_id"] for item in observation.own_entities}


def _contact_owner_ids(observation: ObservationV2) -> set[str]:
    return {
        item["observer_entity_id"] for item in observation.contacts_by_faction["coalition.defender"]
    }


def test_jamming_keeps_target_base_own_state_and_isolates_its_shared_reports() -> None:
    session = _session_with_short_jamming_window()
    session.load().start()
    try:
        session.step(operation_id="tick.before-jamming", expected_tick=0)
        world = session._mutable_world()
        world.install_contact_evidence(
            _contact(
                evidence_id="test.contact.jammed-owner",
                owner_entity_id="defender.interceptor-001",
            )
        )
        world.install_contact_evidence(
            _contact(
                evidence_id="test.contact.connected-owner",
                owner_entity_id="defender.interceptor-002",
            )
        )

        before = session.world_view.observation(observer_faction_id="coalition.defender")
        assert {
            "defender.interceptor-001",
            "defender.interceptor-002",
        } <= _entity_ids(before)
        assert {
            "defender.interceptor-001",
            "defender.interceptor-002",
        } <= _contact_owner_ids(before)

        session.step(operation_id="tick.jamming-start", expected_tick=1)
        isolated = session.world_view.observation(observer_faction_id="coalition.defender")
        assert "defender.interceptor-001" in _entity_ids(isolated)
        assert "defender.interceptor-002" in _entity_ids(isolated)
        assert "defender.interceptor-001" not in _contact_owner_ids(isolated)
        assert "defender.interceptor-002" in _contact_owner_ids(isolated)
        jammed_own = next(
            item
            for item in isolated.own_entities
            if item["entity_id"] == "defender.interceptor-001"
        )
        assert jammed_own["lifecycle_state"] == "active"
        assert len(jammed_own["position_m"]) == len(jammed_own["velocity_mps"]) == 3
        assert isinstance(jammed_own["heading_deg"], float)
        assert jammed_own["health"] == 1.0
        assert jammed_own["energy"] == 1.0

        checkpoint = session.checkpoint()
        recovered = SessionLifecycleV2.restore(
            checkpoint=checkpoint,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            resolved=session.resolved,
            expected_resolved_hash=session.resolved.resolved_hash,
            model_registry=session.world_factory._model_registry,
            expected_model_registry_hash=session.model_registry_hash,
            world_factory=session.world_factory,
        )
        try:
            recovered_observation = recovered.world_view.observation(
                observer_faction_id="coalition.defender"
            )
            assert "defender.interceptor-001" in _entity_ids(recovered_observation)
            assert "defender.interceptor-001" not in _contact_owner_ids(recovered_observation)
        finally:
            recovered.stop().close()

        session.step(operation_id="tick.jamming-end", expected_tick=2)
        restored = session.world_view.observation(observer_faction_id="coalition.defender")
        assert "defender.interceptor-001" in _entity_ids(restored)
        assert "defender.interceptor-001" in _contact_owner_ids(restored)

        session.step(operation_id="tick.contact-still-valid", expected_tick=3)
        assert "test.contact.jammed-owner" in world.contact_store.records

        session.step(operation_id="tick.contact-expiry", expected_tick=4)
        assert "test.contact.jammed-owner" not in world.contact_store.records
    finally:
        session.stop().close()

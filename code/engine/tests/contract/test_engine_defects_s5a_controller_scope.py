"""EF-06A contracts for strict controller scope and explicit endpoints."""

from __future__ import annotations

import pytest
from openmdbench.scenarios import declarative_v2, formal_v2
from openmdbench.scenarios.declarative_v2 import CompilerErrorV2, ScenarioPackageV2
from openmdbench.schemas.interface_v2 import ActionBatchV2, DiscreteActionV2
from openmdbench.sessions.lifecycle_v2 import (
    ActionPipelineV2,
    SessionFailureV2,
    SessionStateV2,
)
from openmdbench.world.factory_v2 import WorldFactoryV2, WorldStateV2
from tests.contract import test_declarative_mission_control_v2 as fixture


def _world() -> WorldStateV2:
    resolved = fixture._compile(fixture._scenario(2))
    return WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(
        resolved, session_id="session.s5a", seed=17
    )


def test_controller_observation_exposes_only_its_claim_and_marks_scope_as_data_contract() -> None:
    world = _world()
    observation = world.controller_observation_snapshot(controller_slot_id="slot.000")

    assert observation.controller_slot_id == "slot.000"
    assert observation.controlled_entity_ids == ("asset.000",)
    assert tuple(item["entity_id"] for item in observation.own_entities) == ("asset.000",)
    assert observation.shared_contacts == ()
    assert observation.received_messages == ()
    assert observation.metadata["scope_is_not_authentication"] is True
    assert observation.metadata["controller_scope_contract"] == "controller-scope@2.0"


def test_legacy_faction_adapter_is_explicitly_marked_and_keeps_basic_own_state() -> None:
    world = _world()
    observation = world.legacy_faction_observation_snapshot(observer_faction_id="faction.alpha")

    assert observation.controller_slot_id is None
    assert observation.metadata["compatibility_adapter"] == "legacy-faction-observation@2.0"
    assert "legacy" in observation.metadata["compatibility_warning"]
    assert tuple(item["entity_id"] for item in observation.own_entities) == (
        "asset.000",
        "asset.001",
    )


def test_controller_authority_cannot_enqueue_action_for_another_claim() -> None:
    world = _world()
    pipeline = ActionPipelineV2(
        session_id="session.s5a",
        world=world,
        state_provider=lambda: SessionStateV2.LOADED,
        physics_dt_seconds=1.0,
    )
    token = next(
        token
        for token, grant in world.authority_tokens.items()
        if grant.entity_ids == ("asset.000",)
    )
    action = DiscreteActionV2(
        schema_version="2.0",
        action_id="action.outside-claim",
        action_type="device_action",
        entity_id="asset.001",
        faction_id="faction.alpha",
        based_on_tick=0,
        valid_until_tick=0,
        payload={"device_ref": "device.example", "operation": "test"},
    )
    batch = ActionBatchV2(
        schema_version="2.0",
        session_id="session.s5a",
        batch_id="batch.outside-claim",
        idempotency_key="idem.outside-claim",
        faction_id="faction.alpha",
        based_on_tick=0,
        valid_until_tick=0,
        discrete_actions=(action,),
    )

    with pytest.raises(SessionFailureV2) as captured:
        pipeline.submit(
            batch=batch,
            authority_token=token,
            operation_id="submit.outside-claim",
            expected_tick=0,
        )
    assert captured.value.code == "session.controller_authority_invalid"


@pytest.mark.parametrize(
    "public_id",
    (
        "MD-AD-002-EASY",
        "MD-AD-002-MEDIUM",
        "MD-AD-002-HARD",
        "MD-INT-003-EASY",
        "MD-INT-003-MEDIUM",
        "MD-INT-003-HARD",
    ),
)
def test_formal_v2_slots_declare_communication_endpoints(public_id: str) -> None:
    resolved, _catalog = formal_v2.compile_formal_scenario_v2(public_id)
    assert all(
        isinstance(slot.values.get("controller_endpoint_ref"), str)
        for slot in resolved.controller_slots
    )


def test_formal_v2_missing_endpoint_fails_without_claim_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, catalog = formal_v2.load_formal_scenario_v2("MD-INT-003-EASY")
    document = declarative_v2._json_value(package.document)
    document["controller_slots"][0].pop("controller_endpoint_ref")
    missing = ScenarioPackageV2.from_mapping(
        {"schema_version": "package@2.0", "scenario": document}
    )
    monkeypatch.setattr(formal_v2, "load_formal_scenario_v2", lambda _public_id: (missing, catalog))

    with pytest.raises(CompilerErrorV2) as captured:
        formal_v2.compile_formal_scenario_v2("MD-INT-003-EASY")
    assert captured.value.code == "scenario.controller_endpoint_required"

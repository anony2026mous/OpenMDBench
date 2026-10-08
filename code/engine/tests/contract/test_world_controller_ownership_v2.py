"""RF-04 controller ownership and reservation-index contracts."""

from __future__ import annotations

import json
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest
from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2
from tests.contract import test_declarative_events_v2 as event_fixture
from tests.contract import test_declarative_mission_control_v2 as mission_fixture


def _api() -> Any:
    from openmdbench.world import factory_v2

    return factory_v2


def _resolved(slot_count: int) -> tuple[Any, Any]:
    resolved = mission_fixture._compile(mission_fixture._scenario(slot_count))
    return resolved, mission_fixture._catalog().model_registry


def _world(slot_count: int) -> Any:
    resolved, registry = _resolved(slot_count)
    return (
        _api()
        .WorldFactoryV2(model_registry=registry)
        .build(
            resolved,
            session_id=f"session.controller.{slot_count}",
            seed=73,
        )
    )


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_controller_ownership_index_scales_with_stable_bidirectional_order(count: int) -> None:
    world = _world(count)
    index = world.controller_ownership
    assert isinstance(index, _api().ControllerOwnershipIndexV2)
    assert index.slot_ids == tuple(f"slot.{value:03d}" for value in range(count))
    assert index.controller_ids == tuple(f"controller.{value:03d}" for value in range(count))
    assert index.claimed_entity_ids == tuple(f"asset.{value:03d}" for value in range(count))
    for value in range(count):
        slot_id = f"slot.{value:03d}"
        controller_id = f"controller.{value:03d}"
        entity_id = f"asset.{value:03d}"
        claim = index.by_slot(slot_id)
        assert claim.controller_id == controller_id
        assert claim.entity_ids == (entity_id,)
        assert index.by_controller(controller_id) == claim
        assert index.by_entity(entity_id) == (claim,)


def test_claim_carries_faction_schemas_exclusivity_and_capability_evidence() -> None:
    world = _world(1)
    claim = world.controller_ownership.by_slot("slot.000")
    assert claim.faction_id == "faction.alpha"
    assert claim.action_schema_ref == "action-batch@2.0"
    assert claim.observation_schema_ref == "observation@2.0"
    assert claim.exclusive is True
    assert claim.required_coarse_capabilities == ("sensor",)
    assert claim.required_exact_capabilities
    entity_tokens = set(world.get("asset.000").capability_tokens)
    assert set(claim.required_exact_capabilities).issubset(entity_tokens)
    assert all(token.role == "sensor" for token in claim.required_exact_capabilities)


def test_uncontrolled_policy_and_partial_claims_are_explicit() -> None:
    payload = mission_fixture._scenario(2)
    payload["controller_slots"] = payload["controller_slots"][:1]
    payload["visibility"] = [
        rule
        for rule in payload["visibility"]
        if rule.get("controller_id") in {None, "controller.000"}
    ]
    resolved = mission_fixture._compile(payload)
    world = (
        _api()
        .WorldFactoryV2(model_registry=mission_fixture._catalog().model_registry)
        .build(resolved, session_id="session.partial", seed=73)
    )
    assert world.controller_ownership.uncontrolled_policy == "explicit_uncontrolled"
    assert world.controller_ownership.claimed_entity_ids == ("asset.000",)
    assert world.controller_ownership.uncontrolled_entity_ids == ("asset.001",)
    assert world.controller_ownership.by_entity("asset.001") == ()


def test_controller_index_and_claims_are_deeply_immutable_public_views() -> None:
    index = _world(1).controller_ownership
    claim = index.by_slot("slot.000")
    with pytest.raises((AttributeError, TypeError)):
        claim.entity_ids += ("asset.forged",)
    with pytest.raises((AttributeError, TypeError)):
        index.slot_ids += ("slot.forged",)
    assert isinstance(index.slot_to_claim, MappingProxyType)
    slot_to_claim: Any = index.slot_to_claim
    with pytest.raises((AttributeError, TypeError)):
        slot_to_claim["slot.forged"] = claim


def test_spawn_controller_binding_is_reserved_without_activating_entity() -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    world = (
        _api()
        .WorldFactoryV2(model_registry=event_fixture._catalog().model_registry)
        .build(resolved, session_id="session.spawn-reservation", seed=73)
    )
    reservations = world.controller_ownership.reservations
    assert tuple(
        (
            item.controller_binding,
            item.entity_id,
            item.activation_tick,
            item.source_event_id,
        )
        for item in reservations
    ) == (("controller/entity.spawned", "entity.spawned", 10, "event.spawn"),)
    assert world.get_optional("entity.spawned") is None
    assert world.controller_ownership.reserved_entity_ids == ("entity.spawned",)
    assert world.controller_ownership.by_reserved_entity("entity.spawned") == reservations[0]


@pytest.mark.parametrize(
    "mutate",
    (
        lambda slot: slot.update(faction_id="faction.beta"),
        lambda slot: slot.update(required_capabilities=["weapon"]),
        lambda slot: slot.update(resolved_entity_ids=["asset.missing"]),
        lambda slot: slot.update(controller_id=""),
        lambda slot: slot.update(exclusive="yes"),
    ),
)
def test_world_boundary_rejects_corrupted_controller_claims_after_outer_rehash(
    mutate: Any,
) -> None:
    resolved, _registry = _resolved(1)
    payload: dict[str, Any] = json.loads(resolved.to_json())
    mutate(payload["controller_slots"][0])
    payload["resolved_hash"] = ResolvedScenarioV2.compute_resolved_hash(payload)
    with pytest.raises(ValueError) as invalid:
        ResolvedScenarioV2.from_json(json.dumps(payload, sort_keys=True))
    assert getattr(invalid.value, "code", None) == "resolved.integrity_invalid"


def test_exclusive_entity_claims_never_have_two_controllers() -> None:
    index = _world(10).controller_ownership
    for entity_id in index.claimed_entity_ids:
        claims = index.by_entity(entity_id)
        assert len(claims) == 1
        assert claims[0].exclusive is True


def _slot(identifier: str, *, exclusive: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=identifier,
        controller_id=f"controller.{identifier}",
        faction_id="faction.alpha",
        resolved_entity_ids=("asset.shared",),
        action_schema_ref="action-batch@2.0",
        observation_schema_ref="observation@2.0",
        exclusive=exclusive,
        required_capabilities=("sensor",),
    )


def _capability_token(resource_ref: str, *, role: str = "sensor") -> Any:
    return _api().CapabilityTokenV2(
        role=role,
        resource_ref=resource_ref,
        model_ref="models.sensor-contract@2.0.0",
        operation="observe" if role == "sensor" else "engage",
        origin="direct" if role == "sensor" else "dependency",
        root_resource_ref=resource_ref,
    )


@pytest.mark.parametrize("exclusive_order", ((True, False), (False, True)))
def test_exclusive_and_nonexclusive_claim_overlap_is_rejected_in_both_orders(
    exclusive_order: tuple[bool, bool],
) -> None:
    token = _capability_token("sensor.shared@2.0.0")
    with pytest.raises(ValueError, match="exclusive"):
        _api().build_controller_ownership(
            slots=tuple(
                _slot(f"slot.{index}", exclusive=exclusive)
                for index, exclusive in enumerate(exclusive_order)
            ),
            uncontrolled_policy="explicit_uncontrolled",
            entity_factions={"asset.shared": "faction.alpha"},
            entity_tokens={"asset.shared": (token,)},
            lifecycle_schedule=(),
        )


def test_two_nonexclusive_claims_may_share_one_entity() -> None:
    token = _capability_token("sensor.shared@2.0.0")
    index = _api().build_controller_ownership(
        slots=(_slot("slot.0", exclusive=False), _slot("slot.1", exclusive=False)),
        uncontrolled_policy="explicit_uncontrolled",
        entity_factions={"asset.shared": "faction.alpha"},
        entity_tokens={"asset.shared": (token,)},
        lifecycle_schedule=(),
    )
    assert tuple(claim.slot_id for claim in index.by_entity("asset.shared")) == (
        "slot.0",
        "slot.1",
    )


@pytest.mark.parametrize("role", ("sensor", "weapon"))
def test_multi_entity_coarse_requirement_preserves_exact_evidence_per_entity(role: str) -> None:
    slot = _slot("slot.shared", exclusive=False)
    slot.resolved_entity_ids = ("asset.alpha", "asset.beta")
    slot.required_capabilities = (role,)
    alpha = _capability_token(f"{role}.alpha@2.0.0", role=role)
    beta = _capability_token(f"{role}.beta@2.0.0", role=role)
    index = _api().build_controller_ownership(
        slots=(slot,),
        uncontrolled_policy="explicit_uncontrolled",
        entity_factions={
            "asset.alpha": "faction.alpha",
            "asset.beta": "faction.alpha",
        },
        entity_tokens={"asset.alpha": (alpha,), "asset.beta": (beta,)},
        lifecycle_schedule=(),
    )
    claim = index.by_slot("slot.shared")
    assert claim.required_coarse_capabilities == (role,)
    assert claim.required_exact_capabilities_by_entity == MappingProxyType(
        {"asset.alpha": (alpha,), "asset.beta": (beta,)}
    )


@pytest.mark.parametrize(
    "binding",
    ("", "slot.unknown", "controller.unknown", 7, ["slot.spawn"]),
)
def test_spawn_reservation_rejects_empty_unknown_or_wrong_typed_binding(binding: Any) -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    payload: dict[str, Any] = json.loads(resolved.to_json())
    spawn = next(event for event in payload["events"] if event["event_type"] == "spawn")
    spawn["payload"]["entity"]["controller_slot"] = binding
    payload["resolved_hash"] = ResolvedScenarioV2.compute_resolved_hash(payload)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(json.dumps(payload, sort_keys=True))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


@pytest.mark.parametrize(
    "mutate",
    (
        lambda entity: entity.update(faction_id="faction.other"),
        lambda entity: entity["resource_bindings"].update(sensors=[]),
        lambda entity: entity["composition"].update(sensor_refs=[]),
        lambda entity: entity.update(controller_slot="controller/entity.existing"),
    ),
)
def test_spawn_reservation_semantics_are_rechecked_after_outer_rehash(mutate: Any) -> None:
    resolved = event_fixture._compile(event_fixture._scenario())
    payload: dict[str, Any] = json.loads(resolved.to_json())
    spawn = next(event for event in payload["events"] if event["event_type"] == "spawn")
    mutate(spawn["payload"]["entity"])
    payload["resolved_hash"] = ResolvedScenarioV2.compute_resolved_hash(payload)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(json.dumps(payload, sort_keys=True))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"

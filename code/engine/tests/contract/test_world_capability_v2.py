"""RF-04 typed capability-token and exact query contracts."""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any

import pytest
from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2
from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
from tests.contract import test_world_entity_factory_v2 as world_fixture


def _api() -> Any:
    from openmdbench.world import factory_v2

    return factory_v2


def _world(count: int) -> Any:
    resolved, registry = world_fixture._resolved(count)
    return (
        _api()
        .WorldFactoryV2(model_registry=registry)
        .build(
            resolved,
            session_id=f"session.capability.{count}",
            seed=73,
        )
    )


def _selector(**values: Any) -> Any:
    return _api().CapabilitySelectorV2(**values)


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_typed_capabilities_scale_and_are_stably_sorted(count: int) -> None:
    world = _world(count)
    assert tuple(view.id for view in world.entities_stable()) == tuple(
        f"asset.{index:03d}" for index in range(count)
    )
    for view in world.entities_stable():
        tokens = view.capability_tokens
        assert isinstance(tokens, tuple)
        assert tokens == tuple(
            sorted(
                tokens,
                key=lambda item: (
                    item.role,
                    item.resource_ref,
                    item.model_ref,
                    item.operation,
                    item.origin,
                    item.root_resource_ref or "",
                ),
            )
        )
        assert all(isinstance(item, _api().CapabilityTokenV2) for item in tokens)
        assert len(tokens) == len(set(tokens))


def test_tokens_include_exact_resource_model_operation_and_origin() -> None:
    world = _world(1)
    tokens = world.get("asset.000").capability_tokens
    sensor_ref = resource_fixture._resources()["sensors"].exact_ref
    communication_ref = resource_fixture._resources()["communications"].exact_ref
    loadout_ref = resource_fixture._resources()["loadouts"].exact_ref
    weapon_ref = resource_fixture._resources()["weapons"].exact_ref
    effect_ref = resource_fixture._resources()["effects"].exact_ref
    damage_ref = resource_fixture._resources()["damage_models"].exact_ref

    assert any(
        token.role == "sensor"
        and token.resource_ref == sensor_ref
        and token.operation == "observe"
        and token.origin == "direct"
        and token.root_resource_ref == sensor_ref
        for token in tokens
    )
    assert any(
        token.role == "communication"
        and token.resource_ref == communication_ref
        and token.operation == "transmit"
        and token.origin == "direct"
        for token in tokens
    )
    assert any(
        token.role == "weapon"
        and token.resource_ref == weapon_ref
        and token.operation == "engage"
        and token.origin == "dependency"
        and token.root_resource_ref == loadout_ref
        for token in tokens
    )
    assert any(
        token.role == "effect"
        and token.resource_ref == effect_ref
        and token.origin == "dependency"
        and token.root_resource_ref == loadout_ref
        for token in tokens
    )
    assert any(
        token.role == "damage"
        and token.resource_ref == damage_ref
        and token.origin == "dependency"
        and token.root_resource_ref == loadout_ref
        for token in tokens
    )
    assert all(token.model_ref.startswith("models.") and "@" in token.model_ref for token in tokens)


def test_all_and_any_capability_queries_use_exact_typed_selectors() -> None:
    world = _world(4)
    resources = resource_fixture._resources()
    sensor = _selector(
        role="sensor",
        resource_ref=resources["sensors"].exact_ref,
        operation="observe",
    )
    weapon = _selector(
        role="weapon",
        resource_ref=resources["weapons"].exact_ref,
        model_ref=resources["weapons"].model_ref,
        operation="engage",
        origin="dependency",
    )
    nonexistent = _selector(role="sensor", operation="jam")
    assert (
        tuple(item.id for item in world.query(all_capabilities=(sensor, weapon)))
        == world.entity_ids
    )
    assert tuple(item.id for item in world.query(all_capabilities=(sensor, nonexistent))) == ()
    assert tuple(item.id for item in world.query(any_capabilities=(nonexistent, weapon))) == (
        world.entity_ids
    )
    assert tuple(
        item.id
        for item in world.query(
            all_capabilities=(sensor,),
            faction_id="coalition.alpha",
            tag="batch-0",
        )
    ) == ("asset.000",)


def test_direct_and_dependency_filters_are_not_interchangeable() -> None:
    world = _world(1)
    weapon_ref = resource_fixture._resources()["weapons"].exact_ref
    direct = _selector(role="weapon", resource_ref=weapon_ref, origin="direct")
    dependency = _selector(role="weapon", resource_ref=weapon_ref, origin="dependency")
    assert world.query(all_capabilities=(direct,)) == ()
    assert tuple(item.id for item in world.query(all_capabilities=(dependency,))) == ("asset.000",)


def test_capability_tokens_and_query_results_are_publicly_immutable() -> None:
    world = _world(1)
    view = world.get("asset.000")
    token = view.capability_tokens[0]
    with pytest.raises((AttributeError, TypeError)):
        token.role = "forged"
    with pytest.raises((AttributeError, TypeError)):
        view.capability_tokens += (token,)
    assert isinstance(world.capability_index, MappingProxyType)
    capability_index: Any = world.capability_index
    with pytest.raises((AttributeError, TypeError)):
        capability_index["forged"] = ("asset.000",)


@pytest.mark.parametrize(
    ("composition_field", "binding_type"),
    (
        ("sensor_refs", "communications"),
        ("communication_refs", "sensors"),
        ("loadout_ref", "weapons"),
    ),
)
def test_rf03_integrity_rejects_sensor_communication_weapon_composition_mismatch(
    composition_field: str,
    binding_type: str,
) -> None:
    resolved = resource_fixture._compile(resource_fixture._catalog())
    payload: dict[str, Any] = json.loads(resolved.to_json())
    wrong_ref = payload["entities"][0]["resource_bindings"][binding_type][0]["exact_ref"]
    if composition_field.endswith("_refs"):
        payload["entities"][0]["composition"][composition_field] = [wrong_ref]
    else:
        payload["entities"][0]["composition"][composition_field] = wrong_ref
    payload["resolved_hash"] = ResolvedScenarioV2.compute_resolved_hash(payload)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(json.dumps(payload, sort_keys=True))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_coarse_capabilities_are_derived_from_typed_tokens_not_a_second_authority() -> None:
    view = _world(1).get("asset.000")
    assert view.capabilities <= frozenset(token.role for token in view.capability_tokens)


@pytest.mark.parametrize(
    ("field", "value"),
    (("role", "senosr"), ("operation", "obesrve")),
)
def test_selector_rejects_unknown_controlled_role_and_operation(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        _selector(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("all_capabilities", "sensor"),
        ("all_capabilities", ["sensor"]),
        ("any_capabilities", {"role": "sensor"}),
        ("capability", 7),
        ("faction_id", ["faction.alpha"]),
    ),
)
def test_query_rejects_wrong_filter_types_with_stable_error(field: str, value: Any) -> None:
    with pytest.raises(_api().FactoryErrorV2) as captured:
        _world(1).query(**{field: value})
    assert captured.value.code == "factory.query_invalid"
    assert captured.value.path[:2] == ("world", "query")

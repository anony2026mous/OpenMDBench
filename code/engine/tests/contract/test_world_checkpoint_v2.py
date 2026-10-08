"""RF-04 complete canonical world-checkpoint contracts."""

from __future__ import annotations

import json
import math
from typing import Any

import pytest
from tests.contract import test_world_entity_factory_v2 as world_fixture


def _api() -> Any:
    from openmdbench.world import factory_v2

    return factory_v2


def _built(count: int, *, seed: int = 73) -> tuple[Any, Any, Any, Any]:
    resolved, registry = world_fixture._resolved(count)
    factory = _api().WorldFactoryV2(model_registry=registry)
    world = factory.build(
        resolved,
        session_id=f"session.checkpoint.{count}",
        seed=seed,
    )
    return world, resolved, registry, factory


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_checkpoint_captures_complete_tick_zero_world_state(count: int) -> None:
    world, resolved, registry, _factory = _built(count)
    checkpoint = world.checkpoint()
    assert isinstance(checkpoint, _api().WorldCheckpointV2)
    assert checkpoint.schema_version == "world-checkpoint@2.0"
    assert checkpoint.resolved_hash == resolved.resolved_hash
    assert checkpoint.catalog_hash == resolved.catalog_hash
    assert checkpoint.model_registry_hash == registry.snapshot_hash
    assert checkpoint.session_id == f"session.checkpoint.{count}"
    assert checkpoint.seed == 73
    assert checkpoint.tick == 0
    assert len(checkpoint.entities) == count
    assert checkpoint.used_entity_ids == tuple(f"asset.{index:03d}" for index in range(count))
    assert checkpoint.schedule_cursor == 0
    assert checkpoint.lifecycle_ledger == ()
    assert checkpoint.tombstones == ()
    assert checkpoint.rng_state
    assert checkpoint.checkpoint_hash == _api().WorldCheckpointV2.compute_checkpoint_hash(
        checkpoint
    )


def test_checkpoint_contains_all_mutable_entity_controller_rng_and_native_state() -> None:
    world, _resolved, _registry, _factory = _built(1)
    checkpoint = world.checkpoint()
    entity = checkpoint.entities[0]
    runtime = world.get("asset.000").state
    assert entity.id == "asset.000"
    assert entity.position_m == tuple(runtime.position_m)
    assert entity.velocity_mps == tuple(runtime.velocity_mps)
    assert math.isfinite(entity.health)
    assert entity.ammunition == runtime.ammunition
    assert entity.component_states == runtime.component_states
    assert entity.lifecycle == "active"
    assert entity.controller_state == {}
    assert checkpoint.controller_ownership
    assert isinstance(checkpoint.native_adapter_snapshots, tuple)


def test_checkpoint_json_is_strict_canonical_roundtrip_and_deeply_immutable() -> None:
    world, _resolved, _registry, _factory = _built(1)
    checkpoint = world.checkpoint()
    encoded = checkpoint.to_json()
    assert encoded == checkpoint.to_json()
    assert encoded == json.dumps(
        json.loads(encoded),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    recovered = _api().WorldCheckpointV2.from_json(encoded)
    assert recovered == checkpoint
    with pytest.raises((AttributeError, TypeError)):
        recovered.entities[0].ammunition["ammo.forged@2.0.0"] = 1


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value["entities"][0].update(health=True),
        lambda value: value["entities"][0]["position_m"].__setitem__(0, float("nan")),
        lambda value: value["entities"].append(value["entities"][0]),
        lambda value: value.update(schedule_cursor=-1),
        lambda value: value.update(schedule_cursor=10_000),
        lambda value: value["rng_state"].append("forged"),
        lambda value: value["controller_ownership"].update(claimed_entity_ids=["asset.missing"]),
    ),
)
def test_nested_corruption_is_rejected_even_after_outer_checkpoint_rehash(mutate: Any) -> None:
    world, _resolved, _registry, _factory = _built(1)
    payload: dict[str, Any] = json.loads(world.checkpoint().to_json())
    mutate(payload)
    payload["checkpoint_hash"] = _api().WorldCheckpointV2.compute_checkpoint_hash(payload)
    encoded = json.dumps(payload, sort_keys=True, allow_nan=True)
    with pytest.raises(ValueError) as captured:
        _api().WorldCheckpointV2.from_json(encoded)
    assert getattr(captured.value, "code", None) == "checkpoint.integrity_invalid"


def test_restore_requires_explicit_resolved_and_registry_trust_anchors() -> None:
    world, resolved, registry, factory = _built(1)
    checkpoint = world.checkpoint()
    with pytest.raises(TypeError):
        factory.restore_checkpoint(checkpoint)
    with pytest.raises(TypeError):
        factory.restore_checkpoint(checkpoint, resolved=resolved)
    with pytest.raises(TypeError):
        factory.restore_checkpoint(checkpoint, model_registry=registry)
    with pytest.raises(TypeError):
        factory.restore_checkpoint(checkpoint, resolved=resolved, model_registry=registry)


def test_checkpoint_captures_complete_native_adapter_snapshots() -> None:
    from tests.integration import test_native_mmg_adapter_v2 as native_fixture

    native_api = native_fixture._native_api()
    catalog = native_fixture._catalog(model_ref=native_api.UAV_MODEL_REF)
    resolved = native_fixture._resolved(catalog)
    world = (
        _api()
        .WorldFactoryV2(model_registry=catalog.model_registry)
        .build(
            resolved,
            session_id="session.checkpoint.native",
            seed=73,
        )
    )
    snapshots = world.checkpoint().native_adapter_snapshots
    assert len(snapshots) == 1
    assert snapshots[0].model_ref == native_api.UAV_MODEL_REF
    assert snapshots[0].resource_ref == "dynamics.synthetic-native@2.0.0"
    assert snapshots[0].snapshot_hash.startswith("sha256:")

    payload: dict[str, Any] = json.loads(world.checkpoint().to_json())
    payload["native_adapter_snapshots"][0]["native_state"]["step_count"] = -1
    payload["native_adapter_snapshots"][0]["snapshot_hash"] = (
        native_api.NativeDynamicsSnapshotV2.compute_snapshot_hash(
            payload["native_adapter_snapshots"][0]
        )
    )
    payload["checkpoint_hash"] = _api().WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError) as captured:
        _api().WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))
    assert getattr(captured.value, "code", None) == "checkpoint.integrity_invalid"


@pytest.mark.parametrize("attack", ("delete", "extra", "wrong_resource_ref"))
def test_restore_requires_exact_active_native_binding_snapshot_key_closure(attack: str) -> None:
    from tests.integration import test_native_mmg_adapter_v2 as native_fixture

    native_api = native_fixture._native_api()
    catalog = native_fixture._catalog(model_ref=native_api.UAV_MODEL_REF)
    resolved = native_fixture._resolved(catalog)
    factory = _api().WorldFactoryV2(model_registry=catalog.model_registry)
    world = factory.build(resolved, session_id="session.checkpoint.native-closure", seed=73)
    payload = world.checkpoint().model_dump(mode="json")
    if attack == "delete":
        payload["native_adapter_snapshots"] = []
    else:
        extra = dict(payload["native_adapter_snapshots"][0])
        extra["resource_ref"] = (
            "dynamics.extra-native@2.0.0" if attack == "extra" else "dynamics.wrong-native@2.0.0"
        )
        typed = native_api.NativeDynamicsSnapshotV2.model_validate(extra)
        extra["binding_identity_hash"] = native_api.compute_native_binding_identity_hash_v2(typed)
        typed = native_api.NativeDynamicsSnapshotV2.model_validate(extra)
        extra["snapshot_hash"] = native_api.NativeDynamicsSnapshotV2.compute_snapshot_hash(typed)
        if attack == "extra":
            payload["native_adapter_snapshots"].append(extra)
        else:
            payload["native_adapter_snapshots"][0] = extra
    payload["checkpoint_hash"] = _api().WorldCheckpointV2.compute_checkpoint_hash(payload)
    attacked = _api().WorldCheckpointV2.model_validate(payload)
    with pytest.raises(_api().FactoryErrorV2) as captured:
        factory.restore_checkpoint(
            attacked,
            resolved=resolved,
            model_registry=catalog.model_registry,
            expected_checkpoint_hash=attacked.checkpoint_hash,
        )
    assert captured.value.code == "factory.checkpoint_native_closure_mismatch"

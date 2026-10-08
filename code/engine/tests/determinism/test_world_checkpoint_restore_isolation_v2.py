"""RF-04 checkpoint trust-anchor and fresh-adapter isolation contracts."""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from tests.contract import test_world_checkpoint_v2 as checkpoint_fixture
from tests.contract import test_world_entity_factory_v2 as world_fixture


def _two_native_entities() -> tuple[Any, Any, Any, Any]:
    from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
    from tests.integration import test_native_mmg_adapter_v2 as native_fixture

    native_api = native_fixture._native_api()
    catalog = native_fixture._catalog(model_ref=native_api.UAV_MODEL_REF)
    entities = []
    for index in range(2):
        entities.append(
            {
                "schema_version": "2.0",
                "id": f"vehicle.native.{index}",
                "faction_id": "faction.synthetic",
                "platform_ref": "platform.synthetic-native@2.0.0",
                "dynamics_ref": "dynamics.synthetic-native@2.0.0",
                "initial_state": {
                    "schema_version": "2.0",
                    "position_m": [float(index), 0.0, 100.0],
                    "velocity_mps": [0.0, 0.0, 0.0],
                    "heading_deg": 0.0,
                },
            }
        )
    package = ScenarioPackageV2.from_mapping(
        {
            "schema_version": "package@2.0",
            "scenario": {
                "schema_version": "2.0",
                "scenario_id": "scenario.checkpoint-replacement",
                "factions": [{"schema_version": "2.0", "id": "faction.synthetic"}],
                "relationships": [],
                "entities": entities,
                "formations": [],
                "world": {
                    "schema_version": "2.0",
                    "coordinate_system": "local_m",
                    "zones": [],
                },
                "events": [],
                "mission_rules": [],
                "score_metrics": [],
            },
        }
    )
    resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
    factory = checkpoint_fixture._api().WorldFactoryV2(model_registry=catalog.model_registry)
    world = factory.build(resolved, session_id="session.replacement-stage", seed=73)
    return world, resolved, catalog.model_registry, factory


def test_restore_builds_fresh_adapters_and_does_not_mutate_source_world() -> None:
    source, resolved, registry, factory = checkpoint_fixture._built(1)
    before = source.semantic_snapshot()
    source_diagnostics = source.get("asset.000").adapter_diagnostics
    checkpoint = source.checkpoint()
    restored = factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    restored_diagnostics = restored.get("asset.000").adapter_diagnostics
    assert {key: value.instance_id for key, value in source_diagnostics.items()} != {
        key: value.instance_id for key, value in restored_diagnostics.items()
    }
    with restored.write_transaction(tick=0) as writer:
        writer.entity("asset.000").health = 0.5
    assert source.semantic_snapshot() == before
    assert restored.get("asset.000").state.health == 0.5


def test_restore_rejects_resolved_registry_session_and_seed_identity_mismatch() -> None:
    source, resolved, registry, factory = checkpoint_fixture._built(1)
    checkpoint = source.checkpoint()
    other_resolved, other_registry = world_fixture._resolved(10)
    for kwargs in (
        {"resolved": other_resolved, "model_registry": registry},
        {"resolved": resolved, "model_registry": other_registry},
    ):
        with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
            factory.restore_checkpoint(
                checkpoint,
                expected_checkpoint_hash=checkpoint.checkpoint_hash,
                **kwargs,
            )
        assert captured.value.code == "factory.checkpoint_anchor_mismatch"

    payload = checkpoint.model_dump(mode="json")
    for field, value in (("session_id", "session.forged"), ("seed", 991)):
        mutated = dict(payload)
        mutated[field] = value
        mutated["checkpoint_hash"] = (
            checkpoint_fixture._api().WorldCheckpointV2.compute_checkpoint_hash(mutated)
        )
        forged = checkpoint_fixture._api().WorldCheckpointV2.model_validate(mutated)
        with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
            factory.restore_checkpoint(
                forged,
                resolved=resolved,
                model_registry=registry,
                expected_session_id=checkpoint.session_id,
                expected_seed=checkpoint.seed,
                expected_checkpoint_hash=checkpoint.checkpoint_hash,
            )
        assert captured.value.code == "factory.checkpoint_anchor_mismatch"


def test_restore_failure_closes_fresh_adapters_in_reverse_order_without_touching_source() -> None:
    source, resolved, registry, factory = checkpoint_fixture._built(10)
    checkpoint = source.checkpoint()
    before = source.semantic_snapshot()
    factory.checkpoint_fault_injector.fail_on_replacement_adapter_index = 5
    with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
        factory.restore_checkpoint(
            checkpoint,
            resolved=resolved,
            model_registry=registry,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        )
    assert captured.value.code == "factory.checkpoint_restore_failed"
    audit = factory.checkpoint_restore_audit[-1]
    assert len(audit.created_adapter_instance_ids) == 4
    assert audit.closed_adapter_instance_ids == tuple(reversed(audit.created_adapter_instance_ids))
    assert audit.failed_adapter_index == 5
    assert audit.failed_adapter_instance_id not in audit.closed_adapter_instance_ids
    assert audit.status == "rolled_back"
    assert source.semantic_snapshot() == before
    assert all(not item.closed for item in source.get("asset.000").adapter_diagnostics.values())


def test_catalog_free_restore_is_never_available() -> None:
    source, _resolved, _registry, _factory = checkpoint_fixture._built(1)
    api: Any = checkpoint_fixture._api()
    assert not hasattr(api.WorldCheckpointV2, "restore")
    assert not hasattr(api.WorldFactoryV2, "restore_checkpoint_without_anchors")
    with pytest.raises(TypeError):
        api.WorldFactoryV2.restore_checkpoint(source.checkpoint())


def test_fully_rehashed_valid_runtime_mutation_is_rejected_by_external_checkpoint_anchor() -> None:
    source, resolved, registry, factory = checkpoint_fixture._built(1)
    original = source.checkpoint()
    payload = original.model_dump(mode="json")
    payload["entities"][0]["health"] = 0.5
    payload["checkpoint_hash"] = (
        checkpoint_fixture._api().WorldCheckpointV2.compute_checkpoint_hash(payload)
    )
    attacked = checkpoint_fixture._api().WorldCheckpointV2.model_validate(payload)
    with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
        factory.restore_checkpoint(
            attacked,
            resolved=resolved,
            model_registry=registry,
            expected_checkpoint_hash=original.checkpoint_hash,
        )
    assert captured.value.code == "factory.checkpoint_anchor_mismatch"


def test_second_native_replacement_failure_audits_global_staging_and_reverse_cleanup() -> None:
    source, resolved, registry, factory = _two_native_entities()
    checkpoint = source.checkpoint()
    before = source.semantic_snapshot()
    source_instance_ids = {
        diagnostic.instance_id
        for entity in source.entities_stable()
        for diagnostic in entity.adapter_diagnostics.values()
    }
    factory.checkpoint_fault_injector.fail_on_native_replacement_index = 2
    with pytest.raises(checkpoint_fixture._api().FactoryErrorV2) as captured:
        factory.restore_checkpoint(
            checkpoint,
            resolved=resolved,
            model_registry=registry,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        )
    assert captured.value.code == "factory.checkpoint_restore_failed"
    audit = factory.checkpoint_restore_audit[-1]
    assert audit.failed_stage == "native_replacement"
    assert audit.failed_adapter_index == 2
    assert audit.adapter_stages.count("native_replacement") == 1
    assert audit.adapter_stages[:4] == ("initial",) * 4
    assert len(audit.created_adapter_instance_ids) == 5
    assert audit.closed_adapter_instance_ids == tuple(reversed(audit.created_adapter_instance_ids))
    assert set(audit.created_adapter_instance_ids).isdisjoint(source_instance_ids)
    assert audit.failed_adapter_instance_id not in audit.closed_adapter_instance_ids
    assert audit.cleanup_errors == ()
    assert source.semantic_snapshot() == before
    assert all(
        not diagnostic.closed
        for entity in source.entities_stable()
        for diagnostic in entity.adapter_diagnostics.values()
    )


def test_native_replacement_helper_participates_in_one_global_adapter_recorder() -> None:
    api = checkpoint_fixture._api()
    signature = inspect.signature(api.WorldFactoryV2._restore_checkpoint_native_adapters)
    assert "record_adapter" in signature.parameters
    source = inspect.getsource(api.WorldFactoryV2._restore_checkpoint_native_adapters)
    assert "record_adapter(" in source
    assert "_cleanup_adapters(" not in source


class _InitialCloseProxy:
    def __init__(self, wrapped: Any, *, fail_close: bool) -> None:
        self._wrapped = wrapped
        self.instance_id = f"initial-proxy:{wrapped.instance_id}"
        self.fail_close = fail_close
        self.close_calls = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def close(self) -> None:
        self.close_calls += 1
        if self.fail_close:
            raise RuntimeError(f"close failed for {self.instance_id}")
        self._wrapped.close()


class _InitialCloseFaultFactory:
    def __init__(self, delegate: Any, *, fail_on_initial_index: int) -> None:
        self._delegate = delegate
        self._fail_on = fail_on_initial_index
        self.initial: list[_InitialCloseProxy] = []

    def build(self, **kwargs: Any) -> _InitialCloseProxy:
        adapter = self._delegate.build(**kwargs)
        proxy = _InitialCloseProxy(
            adapter,
            fail_close=len(self.initial) + 1 == self._fail_on,
        )
        self.initial.append(proxy)
        return proxy

    def restore(self, snapshot: Any, **kwargs: Any) -> Any:
        return self._delegate.restore(snapshot, **kwargs)


def test_successful_replacements_publish_old_initial_close_failure_without_false_closed() -> None:
    source, resolved, registry, _source_factory = _two_native_entities()
    checkpoint = source.checkpoint()
    source_before = source.semantic_snapshot()
    native_api = __import__("openmdbench.dynamics.native_v2", fromlist=["native_v2"])
    native_factory = _InitialCloseFaultFactory(
        native_api.NativeDynamicsAdapterFactoryV2(),
        fail_on_initial_index=2,
    )
    restore_factory = checkpoint_fixture._api().WorldFactoryV2(
        model_registry=registry,
        native_dynamics_factory=native_factory,
    )
    restored = restore_factory.restore_checkpoint(
        checkpoint,
        resolved=resolved,
        model_registry=registry,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    audit = restore_factory.checkpoint_restore_audit[-1]
    initial_ids = tuple(adapter.instance_id for adapter in native_factory.initial)
    assert audit.status == "committed_with_cleanup_errors"
    assert audit.replaced_initial_adapter_instance_ids == initial_ids
    assert audit.closed_replaced_initial_adapter_instance_ids == initial_ids[:1]
    assert audit.failed_replaced_initial_adapter_instance_ids == initial_ids[1:]
    assert len(audit.cleanup_errors) == 1
    cleanup_error = audit.cleanup_errors[0]
    assert cleanup_error.adapter_instance_id == initial_ids[1]
    assert cleanup_error.error_type == "RuntimeError"
    assert cleanup_error.message == f"close failed for {initial_ids[1]}"
    assert native_factory.initial[0].close_calls == 1
    assert native_factory.initial[1].close_calls == 1
    replacement_ids = {
        diagnostic.instance_id
        for entity in restored.entities_stable()
        for resource_ref, diagnostic in entity.adapter_diagnostics.items()
        if resource_ref == "dynamics.synthetic-native@2.0.0"
    }
    assert replacement_ids
    assert replacement_ids.isdisjoint(initial_ids)
    assert all(
        not diagnostic.closed
        for entity in restored.entities_stable()
        for diagnostic in entity.adapter_diagnostics.values()
    )
    assert source.semantic_snapshot() == source_before
    recovered = checkpoint_fixture._api().WorldCheckpointV2.from_json(
        restored.checkpoint().to_json()
    )
    assert recovered.semantic_hash == restored.checkpoint().semantic_hash
    with pytest.raises((AttributeError, TypeError)):
        audit.cleanup_errors += ({"forged": True},)


def test_replacement_cleanup_source_uses_evidence_aware_cleanup_not_suppressing_helper() -> None:
    source = inspect.getsource(
        checkpoint_fixture._api().WorldFactoryV2._restore_checkpoint_native_adapters
    )
    assert "_cleanup_adapters(tuple(replaced" not in source
    assert "cleanup_with_evidence" in source or "record_cleanup" in source

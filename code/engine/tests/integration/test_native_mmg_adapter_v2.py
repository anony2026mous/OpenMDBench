"""Lightweight Catalog/Resolved/World integration for native dynamics bindings."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2


def _native_api() -> Any:
    from openmdbench.dynamics import native_v2

    return native_v2


def _catalog(
    *,
    model_ref: str,
    artifact_manifest: Any = None,
    artifact_sources: Any = None,
) -> CatalogV2:
    api = _native_api()
    registry = ModelRegistryV2(interface_version="2.0")
    schema_metadata = ModelFactoryMetadataV2(
        schema_version="2.0",
        model_id="models.schema-only",
        version="2.0.0",
        interface_version="2.0",
        input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0",
        units={},
        deterministic=True,
        thread_safe=True,
        process_safe=True,
        trusted=True,
        artifact_sha256="sha256:" + "a" * 64,
        resource_types=("platforms",),
        field_units={},
    )
    registry.register(schema_metadata, lambda definition: definition)
    registration_options: dict[str, Any] = {}
    if artifact_manifest is not None:
        registration_options["artifact_manifest"] = artifact_manifest
    if artifact_sources is not None:
        registration_options["artifact_sources"] = artifact_sources
    api.register_native_dynamics_models_v2(registry, **registration_options)
    registry.freeze()
    dynamics = CatalogResourceV2(
        schema_version="2.0",
        resource_type="dynamics",
        id="dynamics.synthetic-native",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id=model_ref,
        content={
            "compatible_platform_types": ["synthetic-airframe"],
            "mobile": True,
            "max_speed_mps": 60.0,
            "max_turn_rate_deg_s": 20.0,
            "max_vertical_speed_mps": 10.0,
            "max_altitude_m": 3000.0,
        },
    )
    platform = CatalogResourceV2(
        schema_version="2.0",
        resource_type="platforms",
        id="platform.synthetic-native",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id=schema_metadata.exact_ref,
        dependencies=(dynamics.exact_ref,),
        content={
            "platform_type": "synthetic-airframe",
            "domain": "air",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": [],
            "payload_capacity_kg": 0.0,
        },
    )
    return CatalogV2(
        (platform, dynamics),
        engine_version="2.0.0",
        model_registry=registry,
    )


def _resolved(catalog: CatalogV2) -> Any:
    package = ScenarioPackageV2.from_mapping(
        {
            "schema_version": "package@2.0",
            "scenario": {
                "schema_version": "2.0",
                "scenario_id": "scenario.synthetic-native",
                "factions": [{"schema_version": "2.0", "id": "faction.arbitrary"}],
                "relationships": [],
                "entities": [
                    {
                        "schema_version": "2.0",
                        "id": "vehicle.native",
                        "faction_id": "faction.arbitrary",
                        "platform_ref": "platform.synthetic-native@2.0.0",
                        "dynamics_ref": "dynamics.synthetic-native@2.0.0",
                        "initial_state": {
                            "schema_version": "2.0",
                            "position_m": [0.0, 0.0, 100.0],
                            "velocity_mps": [0.0, 0.0, 0.0],
                            "heading_deg": 0.0,
                        },
                    }
                ],
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
    return ScenarioCompilerV2(catalog=catalog).compile(package)


def test_catalog_resolved_world_wires_exact_native_dynamics_model_and_parameters() -> None:
    api = _native_api()
    catalog = _catalog(model_ref=api.UAV_MODEL_REF)
    resolved = _resolved(catalog)
    dynamics_binding = resolved.entities[0].resource_bindings["dynamics"][0]
    assert dynamics_binding.model_ref == api.UAV_MODEL_REF
    assert dynamics_binding.normalized_content["max_speed_mps"] == 60.0

    from openmdbench.world.factory_v2 import WorldFactoryV2

    world = WorldFactoryV2(model_registry=catalog.model_registry).build(
        resolved,
        session_id="session.native-integration",
        seed=73,
    )
    diagnostic = world.get("vehicle.native").adapter_diagnostics[dynamics_binding.exact_ref]
    assert diagnostic.model_ref == api.UAV_MODEL_REF
    assert diagnostic.adapter_type.endswith("NativeDynamicsAdapterV2")
    assert diagnostic.details["parameter_hash"].startswith("sha256:")
    world.close()
    assert world.get("vehicle.native").adapter_diagnostics[dynamics_binding.exact_ref].closed


def test_registered_native_catalog_factory_schema_is_compatible_with_registry_protocol() -> None:
    api = _native_api()
    catalog = _catalog(model_ref=api.UAV_MODEL_REF)
    metadata = catalog.model_registry.metadata(api.UAV_MODEL_REF)
    assert metadata.input_schema == "catalog-resource@2.0"
    assert metadata.output_schema == "runtime-component@2.0"
    assert metadata.resource_types == ("dynamics",)
    assert (
        metadata.artifact_sha256
        == api.native_dynamics_metadata_v2()[api.UAV_MODEL_REF].artifact_sha256
    )


def test_world_rejects_native_binding_registered_under_different_exact_model() -> None:
    api = _native_api()
    catalog = _catalog(model_ref=api.UAV_MODEL_REF)
    resolved = _resolved(catalog)
    wrong_catalog = _catalog(model_ref=api.AUV_MODEL_REF)
    from openmdbench.world.factory_v2 import FactoryErrorV2, WorldFactoryV2

    with pytest.raises(FactoryErrorV2) as captured:
        WorldFactoryV2(model_registry=wrong_catalog.model_registry).build(
            resolved,
            session_id="session.native-wrong-model",
            seed=73,
        )
    assert captured.value.code in {
        "factory.model_unknown",
        "factory.model_evidence_mismatch",
        "factory.model_registry_hash_mismatch",
    }


def test_world_rejects_mmg_binding_when_resolved_worker_evidence_is_not_installed() -> None:
    api = _native_api()
    worker_source = api.NativeArtifactSourceV2(
        model_ref=api.MMG_MODEL_REF,
        artifact_path=str(Path(__file__).resolve()),
        artifact_kind="process_worker",
        build_id="world-policy-worker-control",
    )
    manifest = dict(api.native_artifact_manifest_v2())
    manifest[api.MMG_MODEL_REF] = api.build_native_artifact_evidence_v2(worker_source)
    catalog = _catalog(
        model_ref=api.MMG_MODEL_REF,
        artifact_manifest=manifest,
        artifact_sources={api.MMG_MODEL_REF: worker_source},
    )
    resolved = _resolved(catalog)
    from openmdbench.world.factory_v2 import FactoryErrorV2, WorldFactoryV2

    with pytest.raises(FactoryErrorV2) as captured:
        WorldFactoryV2(model_registry=catalog.model_registry).build(
            resolved,
            session_id="session.mmg-without-process-worker",
            seed=73,
        )
    assert captured.value.code == "factory.adapter_creation_failed"


def test_world_native_snapshot_restore_is_anchored_to_resolved_binding_metadata() -> None:
    api = _native_api()
    catalog = _catalog(model_ref=api.UAV_MODEL_REF)
    resolved = _resolved(catalog)
    binding = resolved.entities[0].resource_bindings["dynamics"][0]
    from openmdbench.world.factory_v2 import WorldFactoryV2

    factory = WorldFactoryV2(model_registry=catalog.model_registry)
    world = factory.build(resolved, session_id="session.snapshot-source", seed=73)
    world_api: Any = world
    snapshots = world_api.native_adapter_snapshots()
    snapshot = snapshots[("vehicle.native", binding.exact_ref)]
    world.close()

    factory_api: Any = factory
    restored = factory_api.restore_native_adapter(
        snapshot,
        expected_binding=binding,
        checkpoint_anchor=snapshot.snapshot_hash,
    )
    try:
        recovered = restored.snapshot()
        assert recovered.model_ref == binding.model_ref
        assert recovered.resource_ref == binding.exact_ref
        assert recovered.artifact_sha256 == binding.model_evidence.artifact_sha256
        assert recovered.binding_identity_hash == snapshot.binding_identity_hash
    finally:
        restored.close()


def test_manifest_registry_resolved_world_and_snapshot_share_one_artifact_digest() -> None:
    api = _native_api()
    catalog = _catalog(model_ref=api.UAV_MODEL_REF)
    resolved = _resolved(catalog)
    binding = resolved.entities[0].resource_bindings["dynamics"][0]
    registry_digest = catalog.model_registry.metadata(api.UAV_MODEL_REF).artifact_sha256
    manifest_digest = api.native_artifact_manifest_v2()[api.UAV_MODEL_REF].artifact_sha256
    from openmdbench.world.factory_v2 import WorldFactoryV2

    world = WorldFactoryV2(model_registry=catalog.model_registry).build(
        resolved,
        session_id="session.manifest-evidence",
        seed=73,
    )
    snapshot = world.native_adapter_snapshots()[("vehicle.native", binding.exact_ref)]
    try:
        assert binding.model_evidence.artifact_sha256 == manifest_digest
        assert registry_digest == manifest_digest
        assert snapshot.artifact_sha256 == manifest_digest
    finally:
        world.close()


def test_world_rejects_registry_built_from_drifted_native_artifact_manifest() -> None:
    api = _native_api()
    drifted = dict(api.native_artifact_manifest_v2())
    drifted[api.UAV_MODEL_REF] = drifted[api.UAV_MODEL_REF].model_copy(
        update={"artifact_sha256": "sha256:" + "d" * 64}
    )
    registry = ModelRegistryV2(interface_version="2.0")
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.register_native_dynamics_models_v2(registry, artifact_manifest=drifted)
    assert captured.value.code == "dynamics.artifact_manifest_mismatch"


def test_mmg_worker_artifact_injection_hashes_actual_worker_bytes(tmp_path: Path) -> None:
    api = _native_api()
    worker = tmp_path / "sim2sea-worker.bin"
    worker.write_bytes(b"synthetic trusted isolated worker artifact")
    expected = "sha256:" + hashlib.sha256(worker.read_bytes()).hexdigest()
    manifest = api.native_artifact_manifest_v2(
        worker_artifacts={
            api.MMG_MODEL_REF: api.NativeArtifactSourceV2(
                model_ref=api.MMG_MODEL_REF,
                artifact_path=str(worker),
                artifact_kind="process_worker",
                build_id="worker-build-001",
            )
        }
    )
    evidence = manifest[api.MMG_MODEL_REF]
    assert evidence.artifact_sha256 == expected
    assert evidence.artifact_path == str(worker)
    assert evidence.artifact_kind == "process_worker"
    assert evidence.build_id == "worker-build-001"


def test_mmg_worker_injection_rejects_stale_digest_after_bytes_drift(tmp_path: Path) -> None:
    api = _native_api()
    worker = tmp_path / "sim2sea-worker.bin"
    worker.write_bytes(b"worker version one")
    source = api.NativeArtifactSourceV2(
        model_ref=api.MMG_MODEL_REF,
        artifact_path=str(worker),
        artifact_kind="process_worker",
        build_id="worker-build-002",
    )
    stale = api.build_native_artifact_evidence_v2(source)
    worker.write_bytes(b"worker version two")
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2(
            native_loaders={api.MMG_MODEL_REF: lambda: object()},
            worker_artifacts={api.MMG_MODEL_REF: source},
            artifact_manifest={api.MMG_MODEL_REF: stale},
        )
    assert captured.value.code == "dynamics.artifact_bytes_mismatch"


def test_registry_resolved_then_source_bytes_drift_is_rechecked_by_world(tmp_path: Path) -> None:
    api = _native_api()
    source_path = tmp_path / "uav-runtime-artifact.py"
    source_path.write_bytes(Path(api.step_uav.__code__.co_filename).read_bytes())
    source = api.NativeArtifactSourceV2(
        model_ref=api.UAV_MODEL_REF,
        artifact_path=str(source_path),
        artifact_kind="python_source",
        build_id="runtime-recheck-001",
    )
    manifest = dict(api.native_artifact_manifest_v2())
    manifest[api.UAV_MODEL_REF] = api.build_native_artifact_evidence_v2(source)
    catalog = _catalog(
        model_ref=api.UAV_MODEL_REF,
        artifact_manifest=manifest,
        artifact_sources={api.UAV_MODEL_REF: source},
    )
    resolved = _resolved(catalog)
    native_factory = api.NativeDynamicsAdapterFactoryV2(
        artifact_manifest=manifest,
        artifact_sources={api.UAV_MODEL_REF: source},
    )
    from openmdbench.world.factory_v2 import EntityFactoryV2, FactoryErrorV2, WorldFactoryV2

    entity_factory = EntityFactoryV2(
        model_registry=catalog.model_registry,
        native_dynamics_factory=native_factory,
    )
    control = WorldFactoryV2(
        model_registry=catalog.model_registry,
        entity_factory=entity_factory,
    ).build(resolved, session_id="session.artifact-before-drift", seed=73)
    control.close()

    source_path.write_bytes(source_path.read_bytes() + b"\n# post-resolve drift\n")
    with pytest.raises(FactoryErrorV2) as captured:
        WorldFactoryV2(
            model_registry=catalog.model_registry,
            entity_factory=entity_factory,
        ).build(resolved, session_id="session.artifact-after-drift", seed=73)
    assert getattr(captured.value, "code", None) in {
        "factory.artifact_bytes_mismatch",
        "factory.adapter_creation_failed",
    }


def test_installed_mmg_worker_is_registered_as_executable_metadata() -> None:
    api = _native_api()
    registry = ModelRegistryV2(interface_version="2.0")
    api.register_native_dynamics_models_v2(registry)
    assert registry.metadata(api.MMG_MODEL_REF).trusted is True


def test_explicit_available_worker_bytes_allow_standalone_native_materialization(
    tmp_path: Path,
) -> None:
    api = _native_api()
    from tests.contract.test_native_dynamics_adapter_v2 import _FakeMMGCore

    worker = tmp_path / "isolated-worker.bin"
    worker.write_bytes(b"isolated worker executable bytes")
    source = api.NativeArtifactSourceV2(
        model_ref=api.MMG_MODEL_REF,
        artifact_path=str(worker),
        artifact_kind="process_worker",
        build_id="available-worker-001",
    )
    adapter = api.NativeDynamicsAdapterFactoryV2(
        native_loaders={api.MMG_MODEL_REF: _FakeMMGCore},
        worker_artifacts={api.MMG_MODEL_REF: source},
    ).build(
        model_ref=api.MMG_MODEL_REF,
        entity_id="surface.available-worker",
        parameters={"substeps": 1, "integration_dt_s": 1.0},
        seed=73,
    )
    adapter.close()

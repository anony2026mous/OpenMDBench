"""Candidate-only adapter to the existing immutable compiler and native session."""
from __future__ import annotations

import hashlib
from pathlib import Path

from openmdbench.catalog.formal_v2 import load_catalog_bundle_v2
from openmdbench.catalog.v2 import CatalogV2, CatalogResourceV2, ModelFactoryMetadataV2, ModelRegistryV2
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2, RunnerModeV2
from openmdbench.world.factory_v2 import WorldFactoryV2

from .build import CATALOG_PATH
from . import metrics_v1, dispatch_metrics_v1, tracking_metrics_v1, denial_metrics_v1
from . import recon_metrics_v1
from . import delivered_dispatch_v1
from . import track_report_metrics_v1
from .protected_inputs import verify as verify_protected_inputs


def load_candidate_catalog(*, allow_candidate: bool = False, include_track_reports: bool = False) -> CatalogV2:
    if not allow_candidate:
        raise ValueError("Candidate metric model is not released: explicit local validation opt-in required")
    verify_protected_inputs()
    base = load_catalog_bundle_v2(CATALOG_PATH)
    registry = ModelRegistryV2(interface_version="2.0")
    for metadata in base.model_registry.snapshot():
        def factory(definition, ref=metadata.exact_ref):
            return base.model_registry.create(ref, definition)
        registry.register(metadata, factory)
    source_hash = "sha256:" + hashlib.sha256(Path(metrics_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=metrics_v1.MODEL_ID, version=metrics_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0", units={"score": "1"},
        deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=source_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: metrics_v1.ObservationMetricV1())
    dispatch_hash = "sha256:" + hashlib.sha256(Path(dispatch_metrics_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=dispatch_metrics_v1.MODEL_ID, version=dispatch_metrics_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0", units={"score": "1"},
        deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=dispatch_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: dispatch_metrics_v1.DispatchMetricV1())
    tracking_hash = "sha256:" + hashlib.sha256(Path(tracking_metrics_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=tracking_metrics_v1.MODEL_ID, version=tracking_metrics_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0",
        output_schema="runtime-component@2.0", units={"score": "1"},
        deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=tracking_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: tracking_metrics_v1.TrackingMetricV1())
    denial_hash = "sha256:" + hashlib.sha256(Path(denial_metrics_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=denial_metrics_v1.MODEL_ID, version=denial_metrics_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0", output_schema="runtime-component@2.0",
        units={"score": "1"}, deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=denial_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: denial_metrics_v1.DenialMetricV1())
    recon_hash = "sha256:" + hashlib.sha256(Path(recon_metrics_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=recon_metrics_v1.MODEL_ID, version=recon_metrics_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0", output_schema="runtime-component@2.0",
        units={"score": "1"}, deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=recon_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: recon_metrics_v1.ReconMetricV1())
    delivered_hash = "sha256:" + hashlib.sha256(Path(delivered_dispatch_v1.__file__).read_bytes()).hexdigest()
    registry.register(ModelFactoryMetadataV2(
        schema_version="2.0", model_id=delivered_dispatch_v1.MODEL_ID, version=delivered_dispatch_v1.MODEL_VERSION,
        interface_version="2.0", input_schema="catalog-resource@2.0", output_schema="runtime-component@2.0",
        units={"score": "1"}, deterministic=True, thread_safe=False, process_safe=True, trusted=True,
        artifact_sha256=delivered_hash, resource_types=("scoring",), field_units={"score": "1"}),
        lambda _definition: delivered_dispatch_v1.DeliveredDispatchMetricV1())
    if include_track_reports:
        report_hash = "sha256:" + hashlib.sha256(Path(track_report_metrics_v1.__file__).read_bytes()).hexdigest()
        registry.register(ModelFactoryMetadataV2(
            schema_version="2.0", model_id=track_report_metrics_v1.MODEL_ID, version=track_report_metrics_v1.MODEL_VERSION,
            interface_version="2.0", input_schema="catalog-resource@2.0", output_schema="runtime-component@2.0",
            units={"score": "1"}, deterministic=True, thread_safe=False, process_safe=True, trusted=True,
            artifact_sha256=report_hash, resource_types=("scoring",), field_units={"score": "1"}),
            lambda _definition: track_report_metrics_v1.TrackReportMetricV1())
    registry.freeze()
    score_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-observation",
        version=metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    dispatch_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-dispatch",
        version=dispatch_metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=dispatch_metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    tracking_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-tracking",
        version=tracking_metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=tracking_metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    denial_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-denial",
        version=denial_metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=denial_metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    recon_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-recon",
        version=recon_metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=recon_metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    delivered_resource = CatalogResourceV2(
        schema_version="2.0", resource_type="scoring", id="scoring.competition-delivered-dispatch",
        version=delivered_dispatch_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
        model_id=delivered_dispatch_v1.MODEL_REF, content={"unit": "1", "session_local": True})
    resources = [*base.snapshot(), score_resource, dispatch_resource, tracking_resource, denial_resource, recon_resource, delivered_resource]
    if include_track_reports:
        resources.append(CatalogResourceV2(
            schema_version="2.0", resource_type="scoring", id="scoring.competition-track-report",
            version=track_report_metrics_v1.MODEL_VERSION, engine_compatibility=">=2.0.0,<3.0.0",
            model_id=track_report_metrics_v1.MODEL_REF, content={"unit": "1", "session_local": True}))
    return CatalogV2(resources, engine_version="2.0.0", model_registry=registry)


def compile_package(package):
    if not isinstance(package, ScenarioPackageV2):
        package = ScenarioPackageV2.from_mapping(package)
    required = any(m.get("plugin_ref") == track_report_metrics_v1.MODEL_REF
                   for m in package.document.get("scoring", {}).get("metrics", ()))
    catalog = load_candidate_catalog(allow_candidate=True, include_track_reports=required)
    return ScenarioCompilerV2(catalog=catalog).compile(package), catalog

def compile_candidate(path: Path):
    return compile_package(ScenarioPackageV2.from_directory(path))

def create_candidate(path: Path, *, seed: int, session_id: str):
    resolved, catalog = compile_candidate(path)
    session = SessionLifecycleV2.create(
        session_id=session_id, seed=seed, resolved=resolved,
        expected_resolved_hash=resolved.resolved_hash, catalog_hash=resolved.catalog_hash,
        model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry),
        runner_mode=RunnerModeV2.LOCKSTEP, physics_dt_seconds=resolved.world.tick_seconds,
        decision_interval_ticks=1)
    return session.load().start()

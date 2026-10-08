"""RF-04 contract for exact-ref native dynamics adapters."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from tests.contract import test_world_entity_factory_v2 as world_fixture

UAV_REF = "models.native-uav-kinematics@2.0.0"
AUV_REF = "models.native-auv-kinematics@2.0.0"
FIXED_REF = "models.native-fixed@2.0.0"
MMG_REF = "models.native-sim2sea-mmg@2.0.0"


def _api() -> Any:
    module_name = "openmdbench.dynamics.native_v2"
    try:
        specification = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        specification = None
    assert specification is not None, (
        "RF-04 requires the public openmdbench.dynamics.native_v2 module"
    )
    return importlib.import_module(module_name)


def _mmg_worker_source() -> Any:
    return _api().NativeArtifactSourceV2(
        model_ref=MMG_REF,
        artifact_path=str(Path(__file__).resolve()),
        artifact_kind="process_worker",
        build_id="test-worker-contract",
    )


def _mmg_factory(loader: Any) -> Any:
    return _api().NativeDynamicsAdapterFactoryV2(
        native_loaders={MMG_REF: loader},
        worker_artifacts={MMG_REF: _mmg_worker_source()},
    )


def _state(*, z_m: float = 100.0) -> Any:
    api = _api()
    return api.DynamicsStateV2(
        position_m=(10.0, 20.0, z_m),
        velocity_mps=(0.0, 0.0, 0.0),
        heading_deg=0.0,
    )


def _build(model_ref: str, *, entity_id: str = "vehicle.arbitrary", seed: int = 73) -> Any:
    parameters_by_model = {
        UAV_REF: {
            "max_speed_mps": 80.0,
            "max_turn_rate_deg_s": 30.0,
            "max_vertical_speed_mps": 20.0,
            "max_acceleration_mps2": 8.0,
            "max_deceleration_mps2": 10.0,
            "min_altitude_m": 0.0,
            "max_altitude_m": 3000.0,
        },
        AUV_REF: {
            "max_speed_mps": 4.1,
            "max_turn_rate_deg_s": 15.0,
            "max_vertical_speed_mps": 2.0,
            "min_depth_m": -300.0,
            "max_depth_m": 0.0,
        },
        FIXED_REF: {},
        MMG_REF: {"substeps": 2, "integration_dt_s": 0.5},
    }
    if model_ref == MMG_REF:
        return _mmg_factory(_FakeMMGCore).build(
            model_ref=model_ref,
            entity_id=entity_id,
            parameters=parameters_by_model[model_ref],
            seed=seed,
        )
    return (
        _api()
        .NativeDynamicsAdapterFactoryV2()
        .build(
            model_ref=model_ref,
            entity_id=entity_id,
            parameters=parameters_by_model.get(model_ref, {}),
            seed=seed,
        )
    )


@pytest.mark.parametrize("model_ref", (UAV_REF, AUV_REF, FIXED_REF, MMG_REF))
def test_dispatch_is_exact_model_ref_only(model_ref: str) -> None:
    adapter = _build(model_ref)
    assert adapter.model_ref == model_ref
    assert adapter.entity_id == "vehicle.arbitrary"


@pytest.mark.parametrize(
    "unknown",
    (
        "models.native-uav-kinematics@2.0",
        "models.native-uav-kinematics@9.9.9",
        "air",
        "uav",
        "fixed",
    ),
)
def test_unknown_or_platform_domain_fallback_names_fail_closed(unknown: str) -> None:
    api = _api()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        _build(unknown)
    assert captured.value.code == "dynamics.model_unknown"
    assert captured.value.path and captured.value.reason and captured.value.suggestion


def test_generic_dispatch_source_has_no_platform_domain_or_scenario_fallback() -> None:
    source = inspect.getsource(_api().NativeDynamicsAdapterFactoryV2)
    assert "platform_type" not in source
    assert "domain ==" not in source
    assert "scenario_id" not in source
    assert "red" not in source.lower() and "blue" not in source.lower()


def test_unified_input_output_units_and_tick_contract() -> None:
    api = _api()
    adapter = _build(UAV_REF)
    command = api.DynamicsCommandV2(
        target_speed_mps=20.0,
        target_heading_deg=90.0,
        target_vertical_m=120.0,
    )
    output = adapter.step(state=_state(), command=command, tick_seconds=1.0)
    assert isinstance(output, api.DynamicsStateV2)
    assert len(output.position_m) == len(output.velocity_mps) == 3
    assert all(math.isfinite(value) for value in (*output.position_m, *output.velocity_mps))
    assert 0.0 <= output.heading_deg < 360.0
    assert adapter.units == {
        "position_m": "m",
        "velocity_mps": "m/s",
        "heading_deg": "deg_clockwise_from_north",
        "tick_seconds": "s",
    }


def test_uav_auv_and_fixed_behaviour_are_distinct_and_typed() -> None:
    api = _api()
    command = api.DynamicsCommandV2(
        target_speed_mps=10.0,
        target_heading_deg=45.0,
        target_vertical_m=150.0,
    )
    uav = _build(UAV_REF).step(state=_state(z_m=100.0), command=command, tick_seconds=1.0)
    assert uav.position_m[2] > 100.0

    auv_command = api.DynamicsCommandV2(
        target_speed_mps=3.0,
        target_heading_deg=180.0,
        target_vertical_m=-60.0,
    )
    auv = _build(AUV_REF).step(state=_state(z_m=-50.0), command=auv_command, tick_seconds=1.0)
    assert -300.0 <= auv.position_m[2] < -50.0

    fixed = _build(FIXED_REF)
    unchanged = fixed.step(state=_state(), command=None, tick_seconds=1.0)
    assert unchanged == _state()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        fixed.step(state=_state(), command=command, tick_seconds=1.0)
    assert captured.value.code == "dynamics.fixed_motion_forbidden"


@pytest.mark.parametrize(
    ("state", "command", "tick_seconds"),
    (
        ("not-state", None, 1.0),
        (None, {"target_speed_mps": math.nan}, 1.0),
        (None, {"target_heading_deg": 360.0}, 1.0),
        (None, {"target_speed_mps": -1.0}, 1.0),
        (None, None, 0.0),
        (None, None, True),
    ),
)
def test_illegal_inputs_are_stable_errors(state: Any, command: Any, tick_seconds: Any) -> None:
    api = _api()
    adapter = _build(UAV_REF)
    actual_state = state if state is not None else _state()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        adapter.step(state=actual_state, command=command, tick_seconds=tick_seconds)
    assert captured.value.code in {
        "dynamics.state_invalid",
        "dynamics.command_invalid",
        "dynamics.tick_invalid",
    }
    assert captured.value.path and captured.value.value is not None


def test_same_model_ref_with_different_parameters_changes_only_that_instance() -> None:
    api = _api()
    factory = api.NativeDynamicsAdapterFactoryV2()
    slow = factory.build(
        model_ref=UAV_REF,
        entity_id="vehicle.slow",
        parameters={"max_speed_mps": 5.0, "max_turn_rate_deg_s": 5.0},
        seed=73,
    )
    fast = factory.build(
        model_ref=UAV_REF,
        entity_id="vehicle.fast",
        parameters={"max_speed_mps": 50.0, "max_turn_rate_deg_s": 30.0},
        seed=73,
    )
    command = api.DynamicsCommandV2(
        target_speed_mps=40.0,
        target_heading_deg=90.0,
        target_vertical_m=100.0,
    )
    slow_state = slow.step(state=_state(), command=command, tick_seconds=1.0)
    fast_state = fast.step(state=_state(), command=command, tick_seconds=1.0)
    assert sum(value * value for value in slow_state.velocity_mps) < sum(
        value * value for value in fast_state.velocity_mps
    )
    assert slow.snapshot().parameters != fast.snapshot().parameters


class _FakeMMGCore:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, float]] = []
        self.batch_calls: list[tuple[float, float, float, int]] = []
        self.closed = False

    def step(self, *, nps: float, rudder_rad: float, dt_s: float) -> tuple[float, ...]:
        self.calls.append((nps, rudder_rad, dt_s))
        return (1.0, 2.0, 0.0, 3.0, 0.0, 90.0)

    def step_many(
        self, *, nps: float, rudder_rad: float, dt_s: float, substeps: int
    ) -> tuple[float, ...]:
        self.batch_calls.append((nps, rudder_rad, dt_s, substeps))
        result: tuple[float, ...] = ()
        for _index in range(substeps):
            result = self.step(nps=nps, rudder_rad=rudder_rad, dt_s=dt_s)
        return result

    def snapshot(self) -> dict[str, Any]:
        return {"calls": tuple(self.calls)}

    def restore(self, value: dict[str, Any]) -> None:
        self.calls = list(value["calls"])

    def close(self) -> None:
        self.closed = True


def test_mmg_uses_lightweight_injected_native_core_and_radian_controls() -> None:
    api = _api()
    core = _FakeMMGCore()
    adapter = _mmg_factory(lambda: core).build(
        model_ref=MMG_REF,
        entity_id="surface.arbitrary",
        parameters={"substeps": 2, "integration_dt_s": 0.5},
        seed=73,
    )
    command = api.MMGCommandV2(nps=4.0, rudder_rad=0.2)
    result = adapter.step(state=_state(z_m=0.0), command=command, tick_seconds=1.0)
    assert result.position_m == (1.0, 2.0, 0.0)
    assert core.batch_calls == [(4.0, 0.2, 0.5, 2)]
    assert core.calls == [(4.0, 0.2, 0.5), (4.0, 0.2, 0.5)]
    adapter.close()
    assert core.closed


def test_metadata_declares_exact_interface_units_and_native_safety() -> None:
    metadata = _api().native_dynamics_metadata_v2()
    assert set(metadata) == {UAV_REF, AUV_REF, FIXED_REF, MMG_REF}
    for model_ref, item in metadata.items():
        assert item.exact_ref == model_ref
        assert item.interface_version == "2.0"
        assert item.input_schema == "dynamics-input@2.0"
        assert item.output_schema == "dynamics-output@2.0"
        assert item.deterministic is True
        assert item.trusted is True
        assert item.process_safe is True or item.thread_safe is True
        assert item.units["position_m"] == "m"
        assert item.units["velocity_mps"] == "m/s"


def test_world_public_views_hide_real_adapters_and_close_world_owns_cleanup() -> None:
    world_api = importlib.import_module("openmdbench.world.factory_v2")
    resolved, registry = world_fixture._resolved(1)
    world = world_api.WorldFactoryV2(model_registry=registry).build(
        resolved,
        session_id="session.native-diagnostic",
        seed=73,
    )
    view = world.get("asset.000")
    assert not hasattr(view, "adapters")
    assert view.adapter_diagnostics
    assert all(not hasattr(value, "step") for value in view.adapter_diagnostics.values())
    world.close()
    assert all(value.closed for value in world.snapshot().entities[0].adapter_diagnostics.values())


def test_production_mmg_builds_one_process_isolated_core_without_loader_injection() -> None:
    api = _api()
    factory = api.NativeDynamicsAdapterFactoryV2()
    adapter = factory.build(
        model_ref=MMG_REF,
        entity_id="surface.production",
        parameters={"substeps": 2, "integration_dt_s": 0.5},
        seed=73,
    )
    restored = None
    try:
        command = api.MMGCommandV2(nps=2.0, rudder_rad=0.15)
        state = _state(z_m=0.0)
        for _ in range(4):
            state = adapter.step(
                state=state,
                command=command,
                tick_seconds=1.0,
            )
        assert state.position_m[2] == 0.0
        assert all(math.isfinite(value) for value in (*state.position_m, *state.velocity_mps))
        snapshot = adapter.snapshot()
        assert snapshot.native_state["core"]
        restored = factory.restore(
            snapshot,
            expected_binding_identity=snapshot.binding_identity_hash,
            checkpoint_anchor=snapshot.snapshot_hash,
        )
        assert restored.step(state=state, command=command, tick_seconds=1.0) == adapter.step(
            state=state,
            command=command,
            tick_seconds=1.0,
        )
    finally:
        if restored is not None:
            restored.close()
        adapter.close()


def test_production_mmg_handles_share_one_worker_but_keep_state_isolated() -> None:
    from openmdbench.dynamics.sim2sea_mmg_worker import spawn_sim2sea_mmg_core_v2

    first = spawn_sim2sea_mmg_core_v2()
    second = spawn_sim2sea_mmg_core_v2()
    try:
        assert first is not second
        assert first.worker_process_pid is not None
        assert first.worker_process_pid == second.worker_process_pid
        first.set_state(
            SimpleNamespace(
                position_m=(10.0, 20.0, 0.0),
                velocity_mps=(1.0, 0.0, 0.0),
                heading_deg=0.0,
            )
        )
        second.set_state(
            SimpleNamespace(
                position_m=(30.0, 40.0, 5.0),
                velocity_mps=(0.0, 2.0, 0.0),
                heading_deg=90.0,
            )
        )
        assert first.snapshot()["state"]["position_m"] == [10.0, 20.0, 0.0]
        assert second.snapshot()["state"]["position_m"] == [30.0, 40.0, 5.0]

        first.close()
        assert second.snapshot()["state"]["position_m"] == [30.0, 40.0, 5.0]
    finally:
        first.close()
        second.close()


def test_parameter_validation_precedes_native_allocation() -> None:
    api = _api()
    allocations = 0

    def allocate() -> _FakeMMGCore:
        nonlocal allocations
        allocations += 1
        return _FakeMMGCore()

    factory = _mmg_factory(allocate)
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        factory.build(
            model_ref=MMG_REF,
            entity_id="surface.invalid-before-allocation",
            parameters={"substeps": 0, "integration_dt_s": 0.5},
            seed=73,
        )
    assert captured.value.code == "dynamics.parameters_invalid"
    assert allocations == 0


class _PartiallyInvalidCore:
    def __init__(self) -> None:
        self.closed = False

    def step(self, *, nps: float, rudder_rad: float, dt_s: float) -> tuple[float, ...]:
        del nps, rudder_rad, dt_s
        return ()

    def snapshot(self) -> dict[str, Any]:
        return {}

    def close(self) -> None:
        self.closed = True


def test_native_core_allocated_then_rejected_is_closed() -> None:
    api = _api()
    core = _PartiallyInvalidCore()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        _mmg_factory(lambda: core).build(
            model_ref=MMG_REF,
            entity_id="surface.partial-core",
            parameters={"substeps": 2, "integration_dt_s": 0.5},
            seed=73,
        )
    assert captured.value.code == "dynamics.native_core_invalid"
    assert core.closed is True


@pytest.mark.parametrize(
    ("model_ref", "parameters"),
    (
        (UAV_REF, {"max_speed_mps": 80.000001}),
        (UAV_REF, {"max_turn_rate_deg_s": 30.000001}),
        (UAV_REF, {"max_vertical_speed_mps": 20.000001}),
        (UAV_REF, {"max_altitude_m": 3000.000001}),
        (AUV_REF, {"max_speed_mps": 4.100001}),
        (AUV_REF, {"max_turn_rate_deg_s": 15.000001}),
        (AUV_REF, {"max_vertical_speed_mps": 2.000001}),
        (AUV_REF, {"min_depth_m": -300.000001}),
    ),
)
def test_build_rejects_parameters_above_underlying_algorithm_limits(
    model_ref: str, parameters: dict[str, float]
) -> None:
    api = _api()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2().build(
            model_ref=model_ref,
            entity_id="vehicle.algorithm-limit",
            parameters=parameters,
            seed=73,
        )
    assert captured.value.code == "dynamics.parameters_unsupported"


@pytest.mark.parametrize(
    ("dto", "payload"),
    (
        (
            "state",
            {
                "position_m": (0.0, 0.0, 0.0),
                "velocity_mps": (0.0, 0.0, 0.0),
                "heading_deg": 0.0,
                "native_hidden": "forged",
            },
        ),
        (
            "command",
            {
                "target_speed_mps": 1.0,
                "target_heading_deg": 0.0,
                "target_vertical_m": 10.0,
                "native_hidden": "forged",
            },
        ),
    ),
)
def test_public_state_and_command_reject_undeclared_native_fields(
    dto: str, payload: dict[str, Any]
) -> None:
    api = _api()
    model = api.DynamicsStateV2 if dto == "state" else api.DynamicsCommandV2
    with pytest.raises(ValueError):
        model.model_validate(payload)


def test_execution_policy_matches_declared_native_safety() -> None:
    api = _api()
    policy = api.native_dynamics_execution_policy_v2()
    metadata = api.native_dynamics_metadata_v2()
    assert policy[MMG_REF].isolation == "spawn_process"
    assert policy[MMG_REF].max_in_process_concurrency == 0
    assert metadata[MMG_REF].trusted is True
    for model_ref in (UAV_REF, AUV_REF, FIXED_REF):
        assert policy[model_ref].isolation == "in_process"
        assert policy[model_ref].max_in_process_concurrency == 1
        assert metadata[model_ref].thread_safe is False


def test_thread_safety_metadata_matches_single_writer_adapter_implementation() -> None:
    api = _api()
    metadata = api.native_dynamics_metadata_v2()
    policy = api.native_dynamics_execution_policy_v2()
    for model_ref in (UAV_REF, AUV_REF, FIXED_REF):
        assert metadata[model_ref].thread_safe is False
        assert policy[model_ref].single_writer is True
        assert policy[model_ref].reject_concurrent_step is True


class _SolverIdentityRaisesAfterClaim(_FakeMMGCore):
    @property
    def solver_identity(self) -> str:
        raise RuntimeError("solver identity unavailable after allocation")


def test_solver_identity_failure_after_core_claim_cleans_up_and_releases_claim() -> None:
    api = _api()
    core = _SolverIdentityRaisesAfterClaim()
    factory = _mmg_factory(lambda: core)
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        factory.build(
            model_ref=MMG_REF,
            entity_id="surface.identity-failure",
            parameters={"substeps": 1, "integration_dt_s": 1.0},
            seed=73,
        )
    assert captured.value.code == "dynamics.solver_identity_invalid"
    assert core.closed is True

    replacement = _FakeMMGCore()
    adapter = _mmg_factory(lambda: replacement).build(
        model_ref=MMG_REF,
        entity_id="surface.identity-retry",
        parameters={"substeps": 1, "integration_dt_s": 1.0},
        seed=73,
    )
    adapter.close()


def test_public_restore_requires_both_external_identity_anchors() -> None:
    api = _api()
    adapter = _build(UAV_REF)
    snapshot = adapter.snapshot()
    adapter.close()
    factory = api.NativeDynamicsAdapterFactoryV2()
    with pytest.raises(TypeError):
        factory.restore(snapshot)
    with pytest.raises(TypeError):
        factory.restore(snapshot, expected_binding_identity=snapshot.binding_identity_hash)
    with pytest.raises(TypeError):
        factory.restore(snapshot, checkpoint_anchor=snapshot.snapshot_hash)


def test_builtin_artifact_digest_is_not_derived_from_exact_reference_text() -> None:
    source = inspect.getsource(_api().native_dynamics_metadata_v2)
    assert "sha256(exact_ref.encode" not in source
    assert "sha256(model_ref.encode" not in source
    manifest = _api().native_artifact_manifest_v2()
    metadata = _api().native_dynamics_metadata_v2()
    for model_ref, evidence in manifest.items():
        assert evidence.source in {"signed_manifest", "installed_artifact", "source_digest"}
        assert evidence.artifact_sha256 == metadata[model_ref].artifact_sha256
        exact_ref_digest = "sha256:" + hashlib.sha256(model_ref.encode()).hexdigest()
        assert evidence.artifact_sha256 != exact_ref_digest


def test_artifact_manifest_injection_rejects_digest_drift() -> None:
    api = _api()
    manifest = dict(api.native_artifact_manifest_v2())
    original = manifest[UAV_REF]
    manifest[UAV_REF] = original.model_copy(update={"artifact_sha256": "sha256:" + "f" * 64})
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.native_dynamics_metadata_v2(artifact_manifest=manifest)
    assert captured.value.code == "dynamics.artifact_manifest_mismatch"


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_builtin_artifact_manifest_hashes_real_implementation_file_bytes() -> None:
    api = _api()
    manifest = api.native_artifact_manifest_v2()
    expected_sources = {
        UAV_REF: Path(inspect.getsourcefile(api.step_uav) or ""),
        AUV_REF: Path(inspect.getsourcefile(api.step_auv) or ""),
        FIXED_REF: Path(inspect.getsourcefile(api.NativeDynamicsAdapterV2) or ""),
    }
    for model_ref, source_path in expected_sources.items():
        evidence = manifest[model_ref]
        assert evidence.artifact_kind == "python_source"
        assert evidence.artifact_path
        assert Path(evidence.artifact_path).resolve() == source_path.resolve()
        assert evidence.build_id
        assert evidence.artifact_sha256 == _file_digest(source_path)
    mmg = manifest[MMG_REF]
    assert mmg.artifact_path
    assert mmg.artifact_kind == "process_worker"
    assert mmg.build_id
    assert mmg.available is True
    worker_path = Path(api.__file__).with_name("sim2sea_mmg_worker.py")
    assert Path(mmg.artifact_path).resolve() == worker_path.resolve()
    assert mmg.artifact_sha256 == _file_digest(worker_path)
    assert mmg.artifact_sha256.startswith("sha256:")


def test_source_forbids_description_string_artifact_hashes() -> None:
    source = Path(inspect.getsourcefile(_api()) or "").read_text(encoding="utf-8")
    assert "_NATIVE_SOURCE_ARTIFACTS" not in source
    assert "native-adapter-contract-v2" not in source
    assert "isolated-core-protocol" not in source


def test_source_provider_bytes_change_is_detected_as_artifact_drift(tmp_path: Path) -> None:
    api = _api()
    copied = tmp_path / "uav_impl.py"
    copied.write_bytes(Path(inspect.getsourcefile(api.step_uav) or "").read_bytes())
    source = api.NativeArtifactSourceV2(
        model_ref=UAV_REF,
        artifact_path=str(copied),
        artifact_kind="python_source",
        build_id="test-build-001",
    )
    first = api.build_native_artifact_evidence_v2(source)
    copied.write_bytes(copied.read_bytes() + b"\n# drift\n")
    second = api.build_native_artifact_evidence_v2(source)
    assert second.artifact_sha256 != first.artifact_sha256
    manifest = dict(api.native_artifact_manifest_v2())
    manifest[UAV_REF] = first
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.native_dynamics_metadata_v2(
            artifact_manifest=manifest,
            artifact_sources={UAV_REF: source},
        )
    assert captured.value.code == "dynamics.artifact_bytes_mismatch"


def test_missing_mmg_worker_evidence_is_not_trusted_and_loader_cannot_bypass_it(
    tmp_path: Path,
) -> None:
    api = _api()
    missing_worker = tmp_path / "missing-mmg-worker.py"
    source = api.NativeArtifactSourceV2(
        model_ref=MMG_REF,
        artifact_path=str(missing_worker),
        artifact_kind="process_worker",
        build_id="missing-worker-control",
    )
    evidence = api.native_artifact_manifest_v2(worker_artifacts={MMG_REF: source})[MMG_REF]
    assert evidence.available is False
    metadata = api.native_dynamics_metadata_v2(artifact_sources={MMG_REF: source})
    assert metadata[MMG_REF].trusted is False
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2(
            native_loaders={MMG_REF: _FakeMMGCore},
            artifact_sources={MMG_REF: source},
        ).build(
            model_ref=MMG_REF,
            entity_id="surface.loader-without-worker-artifact",
            parameters={"substeps": 1, "integration_dt_s": 1.0},
            seed=73,
        )
    assert captured.value.code == "dynamics.artifact_unavailable"


def test_substituted_mmg_worker_evidence_requires_a_matching_explicit_loader() -> None:
    api = _api()
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2(
            artifact_sources={MMG_REF: _mmg_worker_source()},
        ).build(
            model_ref=MMG_REF,
            entity_id="surface.unmatched-substituted-worker",
            parameters={"substeps": 1, "integration_dt_s": 1.0},
            seed=73,
        )
    assert captured.value.code == "dynamics.native_core_unavailable"

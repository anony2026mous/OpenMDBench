"""Determinism and native-state isolation contracts for RF-04 dynamics adapters."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

MODEL_REF = "models.native-uav-kinematics@2.0.0"


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


def _mmg_factory(loader: Any) -> Any:
    api = _api()
    source = api.NativeArtifactSourceV2(
        model_ref=api.MMG_MODEL_REF,
        artifact_path=str(Path(__file__).resolve()),
        artifact_kind="process_worker",
        build_id="test-worker-isolation",
    )
    return api.NativeDynamicsAdapterFactoryV2(
        native_loaders={api.MMG_MODEL_REF: loader},
        worker_artifacts={api.MMG_MODEL_REF: source},
    )


def _adapter(index: int, *, seed: int = 73) -> Any:
    return (
        _api()
        .NativeDynamicsAdapterFactoryV2()
        .build(
            model_ref=MODEL_REF,
            entity_id=f"vehicle.{index:03d}",
            parameters={
                "max_speed_mps": 60.0,
                "max_turn_rate_deg_s": 20.0,
                "max_vertical_speed_mps": 10.0,
            },
            seed=seed,
        )
    )


def _initial(index: int) -> Any:
    return _api().DynamicsStateV2(
        position_m=(float(index), 0.0, 100.0),
        velocity_mps=(0.0, 0.0, 0.0),
        heading_deg=0.0,
    )


def _command(index: int) -> Any:
    return _api().DynamicsCommandV2(
        target_speed_mps=20.0 + index % 3,
        target_heading_deg=float((index * 17) % 360),
        target_vertical_m=100.0 + index % 5,
    )


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_native_instances_are_unique_for_zero_one_ten_and_one_hundred(count: int) -> None:
    adapters = tuple(_adapter(index) for index in range(count))
    assert len({id(adapter) for adapter in adapters}) == count
    assert len({adapter.instance_id for adapter in adapters}) == count
    assert tuple(adapter.entity_id for adapter in adapters) == tuple(
        f"vehicle.{index:03d}" for index in range(count)
    )
    for adapter in reversed(adapters):
        adapter.close()


def _run(order: tuple[int, ...], *, seed: int) -> dict[int, Any]:
    adapters = {index: _adapter(index, seed=seed) for index in order}
    states = {index: _initial(index) for index in order}
    try:
        for _tick in range(5):
            for index in order:
                states[index] = adapters[index].step(
                    state=states[index],
                    command=_command(index),
                    tick_seconds=1.0,
                )
        return states
    finally:
        for adapter in adapters.values():
            adapter.close()


def test_interleaving_and_registration_order_do_not_change_results() -> None:
    ascending = _run(tuple(range(10)), seed=73)
    descending = _run(tuple(reversed(range(10))), seed=73)
    assert ascending == descending


def test_same_seed_repeats_and_different_seed_has_independent_rng_stream() -> None:
    first = _run(tuple(range(10)), seed=73)
    repeated = _run(tuple(range(10)), seed=73)
    assert first == repeated
    same_a = _adapter(0, seed=73)
    same_b = _adapter(0, seed=73)
    different = _adapter(0, seed=74)
    try:
        assert same_a.diagnostic().rng_fingerprint == same_b.diagnostic().rng_fingerprint
        assert same_a.diagnostic().rng_fingerprint != different.diagnostic().rng_fingerprint
    finally:
        same_a.close()
        same_b.close()
        different.close()


def test_snapshot_identity_restore_and_close_are_instance_local() -> None:
    api = _api()
    first = _adapter(1)
    second = _adapter(2)
    first_state = first.step(
        state=_initial(1),
        command=_command(1),
        tick_seconds=1.0,
    )
    snapshot = first.snapshot()
    assert snapshot.schema_version == "2.0"
    assert snapshot.model_ref == MODEL_REF
    assert snapshot.entity_id == "vehicle.001"
    assert snapshot.instance_id == first.instance_id
    restored = api.NativeDynamicsAdapterFactoryV2().restore(
        snapshot,
        expected_binding_identity=snapshot.binding_identity_hash,
        checkpoint_anchor=snapshot.snapshot_hash,
    )
    assert restored is not first
    assert restored.instance_id != first.instance_id
    assert restored.restored_from_instance_id == first.instance_id
    assert restored.snapshot().native_state == snapshot.native_state

    next_first = first.step(state=first_state, command=_command(1), tick_seconds=1.0)
    next_restored = restored.step(state=first_state, command=_command(1), tick_seconds=1.0)
    assert next_first == next_restored
    assert second.snapshot().native_state != first.snapshot().native_state

    first.close()
    assert first.diagnostic().closed is True
    assert restored.diagnostic().closed is False
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        first.step(state=first_state, command=_command(1), tick_seconds=1.0)
    assert captured.value.code == "dynamics.adapter_closed"
    restored.close()
    second.close()


def test_snapshot_restore_rejects_model_or_entity_identity_tamper() -> None:
    api = _api()
    adapter = _adapter(3)
    snapshot = adapter.snapshot()
    adapter.close()
    for mutation in (
        snapshot.model_copy(update={"model_ref": "models.unknown@2.0.0"}),
        snapshot.model_copy(update={"entity_id": ""}),
        snapshot.model_copy(update={"instance_id": ""}),
    ):
        with pytest.raises(api.NativeDynamicsErrorV2) as captured:
            api.NativeDynamicsAdapterFactoryV2().restore(
                mutation,
                expected_binding_identity=snapshot.binding_identity_hash,
                checkpoint_anchor=snapshot.snapshot_hash,
            )
        assert captured.value.code in {
            "dynamics.model_unknown",
            "dynamics.snapshot_invalid",
        }


class _IsolatedCore:
    def __init__(self, solver_identity: str) -> None:
        self.solver_identity = solver_identity
        self.state = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.set_state_calls = 0
        self.closed = False

    def set_state(self, state: Any) -> None:
        self.set_state_calls += 1
        self.state = (
            *state.position_m,
            state.velocity_mps[0],
            state.velocity_mps[1],
            state.heading_deg,
        )

    def step(self, *, nps: float, rudder_rad: float, dt_s: float) -> tuple[float, ...]:
        del nps, rudder_rad
        self.state = (
            self.state[0] + dt_s,
            self.state[1],
            self.state[2],
            1.0,
            0.0,
            self.state[5],
        )
        return self.state

    def step_many(
        self, *, nps: float, rudder_rad: float, dt_s: float, substeps: int
    ) -> tuple[float, ...]:
        result: tuple[float, ...] = ()
        for _index in range(substeps):
            result = self.step(nps=nps, rudder_rad=rudder_rad, dt_s=dt_s)
        return result

    def snapshot(self) -> dict[str, Any]:
        return {"solver_identity": self.solver_identity, "state": self.state}

    def restore(self, value: dict[str, Any]) -> None:
        self.state = tuple(value["state"])

    def close(self) -> None:
        self.closed = True


def test_loader_singleton_is_rejected_across_factory_and_session_boundaries() -> None:
    api = _api()
    shared = _IsolatedCore("solver.shared")
    first_factory = _mmg_factory(lambda: shared)
    second_factory = _mmg_factory(lambda: shared)
    first = first_factory.build(
        model_ref=api.MMG_MODEL_REF,
        entity_id="surface.session-one",
        parameters={"substeps": 1, "integration_dt_s": 1.0},
        seed=73,
    )
    try:
        with pytest.raises(api.NativeDynamicsErrorV2) as captured:
            second_factory.build(
                model_ref=api.MMG_MODEL_REF,
                entity_id="surface.session-two",
                parameters={"substeps": 1, "integration_dt_s": 1.0},
                seed=73,
            )
        assert captured.value.code == "dynamics.native_core_reused"
    finally:
        first.close()


def _evidenced_adapter() -> Any:
    api = _api()
    metadata = api.native_dynamics_metadata_v2()[MODEL_REF]
    return api.NativeDynamicsAdapterFactoryV2().build(
        model_ref=MODEL_REF,
        resource_ref="dynamics.synthetic@2.0.0",
        artifact_sha256=metadata.artifact_sha256,
        entity_id="vehicle.snapshot-evidence",
        parameters={"max_speed_mps": 60.0, "max_turn_rate_deg_s": 20.0},
        seed=73,
    )


def test_snapshot_has_complete_canonical_runtime_and_model_evidence() -> None:
    api = _api()
    adapter = _evidenced_adapter()
    snapshot = adapter.snapshot()
    adapter.close()
    metadata = api.native_dynamics_metadata_v2()[MODEL_REF]
    assert snapshot.resource_ref == "dynamics.synthetic@2.0.0"
    assert snapshot.artifact_sha256 == metadata.artifact_sha256
    assert snapshot.interface_version == metadata.interface_version
    assert snapshot.input_schema == metadata.input_schema
    assert snapshot.output_schema == metadata.output_schema
    assert snapshot.units == metadata.units
    assert snapshot.field_units == metadata.field_units
    assert snapshot.parameter_hash.startswith("sha256:")
    assert snapshot.snapshot_hash == api.NativeDynamicsSnapshotV2.compute_snapshot_hash(snapshot)
    assert isinstance(snapshot.units, MappingProxyType)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("resource_ref", "dynamics.forged@2.0.0"),
        ("artifact_sha256", "sha256:" + "f" * 64),
        ("interface_version", "9.0"),
        ("units", {"position_m": "league"}),
        ("parameters", {"max_speed_mps": 1.0}),
        ("native_state", {"step_count": 0, "last_state": None, "extra": "forged"}),
    ),
)
def test_restore_rejects_inner_tamper_even_after_outer_snapshot_rehash(
    field: str, value: Any
) -> None:
    api = _api()
    adapter = _evidenced_adapter()
    original = adapter.snapshot()
    adapter.close()
    tampered = original.model_copy(update={field: value})
    tampered = tampered.model_copy(
        update={"snapshot_hash": api.NativeDynamicsSnapshotV2.compute_snapshot_hash(tampered)}
    )
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2().restore(
            tampered,
            expected_binding_identity=original.binding_identity_hash,
            checkpoint_anchor=original.snapshot_hash,
        )
    assert captured.value.code in {
        "dynamics.snapshot_integrity_invalid",
        "dynamics.snapshot_model_mismatch",
        "dynamics.snapshot_parameters_mismatch",
    }


def test_restore_requires_same_mmg_solver_identity() -> None:
    api = _api()
    source = _IsolatedCore("solver.alpha")
    source_factory = _mmg_factory(lambda: source)
    adapter = source_factory.build(
        model_ref=api.MMG_MODEL_REF,
        entity_id="surface.restore-identity",
        parameters={"substeps": 1, "integration_dt_s": 1.0},
        seed=73,
    )
    snapshot = adapter.snapshot()
    adapter.close()
    target = _IsolatedCore("solver.beta")
    target_factory = _mmg_factory(lambda: target)
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        target_factory.restore(
            snapshot,
            expected_binding_identity=snapshot.binding_identity_hash,
            checkpoint_anchor=snapshot.snapshot_hash,
        )
    assert captured.value.code == "dynamics.solver_identity_mismatch"
    assert target.closed is True


def test_native_solver_state_is_authoritative_after_initialization() -> None:
    api = _api()
    core = _IsolatedCore("solver.authoritative")
    adapter = _mmg_factory(lambda: core).build(
        model_ref=api.MMG_MODEL_REF,
        entity_id="surface.authority",
        parameters={"substeps": 1, "integration_dt_s": 1.0},
        seed=73,
    )
    command = api.MMGCommandV2(nps=1.0, rudder_rad=0.0)
    first = adapter.step(state=_initial(0), command=command, tick_seconds=1.0)
    assert core.set_state_calls == 1
    forged = api.DynamicsStateV2(
        position_m=(999.0, 999.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0),
        heading_deg=0.0,
    )
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        adapter.step(state=forged, command=command, tick_seconds=1.0)
    assert captured.value.code == "dynamics.state_authority_conflict"
    assert adapter.snapshot().native_state["last_state"] == first.model_dump(mode="json")
    assert core.set_state_calls == 1
    adapter.close()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("resource_ref", "dynamics.attacker@2.0.0"),
        ("parameters", {"max_speed_mps": 20.0, "max_turn_rate_deg_s": 5.0}),
        ("artifact_sha256", "sha256:" + "e" * 64),
    ),
)
def test_restore_anchor_rejects_three_layer_fully_rehashed_identity_attack(
    field: str, value: Any
) -> None:
    api = _api()
    adapter = _evidenced_adapter()
    original = adapter.snapshot()
    adapter.close()
    attacked = original.model_copy(update={field: value})
    parameter_hash = api.compute_native_parameter_hash_v2(attacked.parameters)
    attacked = attacked.model_copy(update={"parameter_hash": parameter_hash})
    binding_hash = api.compute_native_binding_identity_hash_v2(attacked)
    attacked = attacked.model_copy(update={"binding_identity_hash": binding_hash})
    attacked = attacked.model_copy(
        update={"snapshot_hash": api.NativeDynamicsSnapshotV2.compute_snapshot_hash(attacked)}
    )
    with pytest.raises(api.NativeDynamicsErrorV2) as captured:
        api.NativeDynamicsAdapterFactoryV2().restore(
            attacked,
            expected_binding_identity=original.binding_identity_hash,
            checkpoint_anchor=original.snapshot_hash,
        )
    assert captured.value.code == "dynamics.snapshot_anchor_mismatch"


def test_snapshot_restore_preserves_catalog_binding_and_model_metadata_exactly() -> None:
    api = _api()
    adapter = _evidenced_adapter()
    snapshot = adapter.snapshot()
    adapter.close()
    restored = api.NativeDynamicsAdapterFactoryV2().restore(
        snapshot,
        expected_binding_identity=snapshot.binding_identity_hash,
        checkpoint_anchor=snapshot.snapshot_hash,
    )
    try:
        recovered = restored.snapshot()
        for field in (
            "model_ref",
            "resource_ref",
            "artifact_sha256",
            "interface_version",
            "input_schema",
            "output_schema",
            "units",
            "field_units",
            "parameter_hash",
            "binding_identity_hash",
        ):
            assert getattr(recovered, field) == getattr(snapshot, field)
    finally:
        restored.close()

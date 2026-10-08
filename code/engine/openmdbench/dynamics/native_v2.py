"""Exact-model native dynamics adapters with isolated lifecycle and state."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from threading import Lock
from types import MappingProxyType
from typing import Any, Literal, Protocol, TypeGuard

from pydantic import Field, model_validator

from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    ModelBindingEvidenceErrorV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)
from openmdbench.domains.air.uav import UAVCommand, UAVState, step_uav
from openmdbench.domains.underwater.auv import AUVCommand, AUVState, step_auv
from openmdbench.schemas.core_v2 import CoreModelV2

UAV_MODEL_REF = "models.native-uav-kinematics@2.0.0"
AUV_MODEL_REF = "models.native-auv-kinematics@2.0.0"
FIXED_MODEL_REF = "models.native-fixed@2.0.0"
MMG_MODEL_REF = "models.native-sim2sea-mmg@2.0.0"

# The Sim2Sea L7 proxy accepts a wider propeller envelope than the original
# 5 rps placeholder. Individual vessel resources still declare their own
# bounds; this is only the native adapter's fail-closed ceiling.
_MAX_MMG_NPS = 240.0
_MAX_MMG_SPEED_MPS = 18.0

_MODEL_REFS = (UAV_MODEL_REF, AUV_MODEL_REF, FIXED_MODEL_REF, MMG_MODEL_REF)
_UNITS = {
    "position_m": "m",
    "velocity_mps": "m/s",
    "heading_deg": "deg_clockwise_from_north",
    "tick_seconds": "s",
}
_KNOWN_PARAMETERS = frozenset(
    {
        "max_speed_mps",
        "max_turn_rate_deg_s",
        "max_vertical_speed_mps",
        "max_acceleration_mps2",
        "max_deceleration_mps2",
        "max_nps",
        "max_rudder_rad",
        "controller_gain",
        "min_altitude_m",
        "max_altitude_m",
        "min_depth_m",
        "max_depth_m",
        "substeps",
        "integration_dt_s",
    }
)


class NativeDynamicsErrorV2(ValueError):
    def __init__(
        self,
        *,
        code: str,
        path: Sequence[str],
        value: object,
        reason: str,
        suggestion: str,
    ) -> None:
        self.code = code
        self.path = tuple(path)
        self.value = value
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"{code} at {'/'.join(self.path)}: {reason}; suggestion: {suggestion}")


def _error(
    code: str,
    path: Sequence[str],
    value: object,
    reason: str,
    suggestion: str,
) -> NativeDynamicsErrorV2:
    return NativeDynamicsErrorV2(
        code=code,
        path=path,
        value=value,
        reason=reason,
        suggestion=suggestion,
    )


def _finite_number(value: object) -> TypeGuard[int | float]:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


class DynamicsStateV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    heading_deg: float = Field(ge=0.0, lt=360.0)

    @model_validator(mode="before")
    @classmethod
    def reject_non_numeric_vectors(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            for field in ("position_m", "velocity_mps"):
                vector = value.get(field)
                if (
                    not isinstance(vector, (list, tuple))
                    or len(vector) != 3
                    or any(not _finite_number(axis) for axis in vector)
                ):
                    raise ValueError(f"{field} must be a finite canonical three-vector")
            if not _finite_number(value.get("heading_deg")):
                raise ValueError("heading_deg must be finite")
        return value


class DynamicsCommandV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    target_speed_mps: float = Field(ge=0.0)
    target_heading_deg: float = Field(ge=0.0, lt=360.0)
    target_vertical_m: float

    @model_validator(mode="before")
    @classmethod
    def reject_non_numeric_fields(cls, value: Any) -> Any:
        if isinstance(value, Mapping) and any(
            not _finite_number(value.get(field))
            for field in ("target_speed_mps", "target_heading_deg", "target_vertical_m")
        ):
            raise ValueError("dynamics command fields must be finite canonical numbers")
        return value


class MMGCommandV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    nps: float = Field(ge=0.0, le=_MAX_MMG_NPS)
    rudder_rad: float = Field(ge=-0.3, le=0.3)

    @model_validator(mode="before")
    @classmethod
    def reject_non_numeric_fields(cls, value: Any) -> Any:
        if isinstance(value, Mapping) and any(
            not _finite_number(value.get(field)) for field in ("nps", "rudder_rad")
        ):
            raise ValueError("MMG command fields must be finite canonical numbers")
        return value


class NativeDynamicsDiagnosticV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    model_ref: str
    entity_id: str
    instance_id: str
    restored_from_instance_id: str | None = None
    rng_fingerprint: str
    parameter_hash: str
    closed: bool


class NativeDynamicsSnapshotV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    model_ref: str
    entity_id: str
    instance_id: str
    restored_from_instance_id: str | None = None
    resource_ref: str
    artifact_sha256: str
    interface_version: str
    input_schema: str
    output_schema: str
    units: dict[str, str]
    field_units: dict[str, str]
    parameters: dict[str, int | float]
    parameter_hash: str
    binding_identity_hash: str
    solver_identity: str
    seed: int
    native_state: dict[str, Any]
    snapshot_hash: str

    @staticmethod
    def compute_snapshot_hash(
        snapshot: NativeDynamicsSnapshotV2 | Mapping[str, Any],
    ) -> str:
        values = snapshot if isinstance(snapshot, Mapping) else snapshot.__dict__
        payload = {key: _plain(value) for key, value in values.items() if key != "snapshot_hash"}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class NativeDynamicsExecutionPolicyV2(CoreModelV2):
    model_ref: str
    isolation: Literal["in_process", "spawn_process"]
    max_in_process_concurrency: int = Field(ge=0)
    single_writer: bool
    reject_concurrent_step: bool


class NativeArtifactEvidenceV2(CoreModelV2):
    model_ref: str
    source: Literal["signed_manifest", "installed_artifact", "source_digest"]
    artifact_path: str
    artifact_kind: Literal["python_source", "process_worker"]
    build_id: str = Field(min_length=1, max_length=256)
    available: bool
    artifact_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class NativeArtifactSourceV2(CoreModelV2):
    schema_version: Literal["2.0"] = "2.0"
    model_ref: str
    artifact_path: str = Field(min_length=1)
    artifact_kind: Literal["python_source", "process_worker"]
    build_id: str = Field(min_length=1, max_length=256)


class NativeDynamicsBindingV2(CoreModelV2):
    """Registry-produced immutable recipe materialized with session identity by World."""

    resource_ref: str
    model_ref: str
    artifact_sha256: str
    interface_version: str
    input_schema: str
    output_schema: str
    units: dict[str, str]
    field_units: dict[str, str]
    parameters: dict[str, int | float]

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> NativeDynamicsBindingV2:
        del memo
        return self


class _MMGCoreV2(Protocol):
    def step(self, *, nps: float, rudder_rad: float, dt_s: float) -> tuple[float, ...]: ...

    def step_many(
        self, *, nps: float, rudder_rad: float, dt_s: float, substeps: int
    ) -> tuple[float, ...]: ...

    def snapshot(self) -> Mapping[str, Any]: ...

    def restore(self, value: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


_INSTANCE_COUNTER = itertools.count()
_INSTANCE_LOCK = Lock()
_CORE_OWNERS: dict[int, object] = {}
_CORE_OWNER_LOCK = Lock()


def _next_instance_id() -> str:
    with _INSTANCE_LOCK:
        ordinal = next(_INSTANCE_COUNTER)
    return f"native-dynamics-{ordinal:016x}"


def _fingerprint(model_ref: str, entity_id: str, seed: int) -> str:
    encoded = f"{model_ref}\0{entity_id}\0{seed}".encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(_plain(value), sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def compute_native_parameter_hash_v2(parameters: Mapping[str, int | float]) -> str:
    return _canonical_hash(parameters)


def compute_native_binding_identity_hash_v2(snapshot: NativeDynamicsSnapshotV2) -> str:
    return _canonical_hash(
        {
            "model_ref": snapshot.model_ref,
            "resource_ref": snapshot.resource_ref,
            "artifact_sha256": snapshot.artifact_sha256,
            "interface_version": snapshot.interface_version,
            "input_schema": snapshot.input_schema,
            "output_schema": snapshot.output_schema,
            "units": snapshot.units,
            "field_units": snapshot.field_units,
            "parameter_hash": snapshot.parameter_hash,
            "solver_identity": snapshot.solver_identity,
        }
    )


def compute_native_resolved_binding_identity_v2(
    *,
    model_ref: str,
    resource_ref: str,
    model_metadata: ModelFactoryMetadataV2,
    normalized_content: Mapping[str, object],
    solver_identity: str | None = None,
) -> str:
    if solver_identity is None and model_ref == MMG_MODEL_REF:
        from openmdbench.dynamics.sim2sea_mmg_worker import MMG_SOLVER_IDENTITY_V2

        solver_identity = MMG_SOLVER_IDENTITY_V2
    parameters = _parameters(
        model_ref,
        {key: value for key, value in normalized_content.items() if key in _KNOWN_PARAMETERS},
    )
    return _canonical_hash(
        {
            "model_ref": model_ref,
            "resource_ref": resource_ref,
            "artifact_sha256": model_metadata.artifact_sha256,
            "interface_version": model_metadata.interface_version,
            "input_schema": model_metadata.input_schema,
            "output_schema": model_metadata.output_schema,
            "units": model_metadata.units,
            "field_units": model_metadata.field_units,
            "parameter_hash": compute_native_parameter_hash_v2(parameters),
            "solver_identity": solver_identity or model_ref,
        }
    )


def _claim_core(core: object) -> None:
    identity = id(core)
    with _CORE_OWNER_LOCK:
        if identity in _CORE_OWNERS:
            raise _error(
                "dynamics.native_core_reused",
                ("native_core", "ownership"),
                identity,
                "native loader reused a core owned by another adapter or factory",
                "allocate one fresh isolated native core for each adapter",
            )
        _CORE_OWNERS[identity] = core


def _release_core(core: object) -> None:
    with _CORE_OWNER_LOCK:
        if _CORE_OWNERS.get(id(core)) is core:
            del _CORE_OWNERS[id(core)]


def _parameters(model_ref: str, value: Mapping[str, object]) -> dict[str, int | float]:
    if set(value) - _KNOWN_PARAMETERS:
        unknown = sorted(set(value) - _KNOWN_PARAMETERS)[0]
        raise _error(
            "dynamics.parameters_invalid",
            ("parameters", unknown),
            unknown,
            "native dynamics parameter is not part of the v2 interface",
            "use only declared unit-suffixed native dynamics parameters",
        )
    result: dict[str, int | float] = {}
    for key, item in value.items():
        if key == "substeps":
            if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
                raise _error(
                    "dynamics.parameters_invalid",
                    ("parameters", key),
                    item,
                    "substeps must be an exact positive integer",
                    "provide a positive integer integration count",
                )
            result[key] = item
            continue
        if not _finite_number(item):
            raise _error(
                "dynamics.parameters_invalid",
                ("parameters", key),
                item,
                "native dynamics parameters must be finite canonical numbers",
                "provide finite values in the units encoded by each field name",
            )
        result[key] = float(item)
    positive = {
        "max_speed_mps",
        "max_turn_rate_deg_s",
        "max_vertical_speed_mps",
        "max_acceleration_mps2",
        "max_deceleration_mps2",
        "integration_dt_s",
        "max_nps",
        "max_rudder_rad",
        "controller_gain",
    }
    if any(float(result[key]) <= 0.0 for key in positive if key in result):
        raise _error(
            "dynamics.parameters_invalid",
            ("parameters", "positive_limits"),
            dict(result),
            "native rates, limits, and integration interval must be positive",
            "provide positive canonical SI limits",
        )
    if (
        "min_altitude_m" in result
        and "max_altitude_m" in result
        and result["min_altitude_m"] > result["max_altitude_m"]
    ) or (
        "min_depth_m" in result
        and "max_depth_m" in result
        and result["min_depth_m"] > result["max_depth_m"]
    ):
        raise _error(
            "dynamics.parameters_invalid",
            ("parameters", "vertical_bounds"),
            dict(result),
            "minimum vertical bound exceeds maximum bound",
            "provide ordered canonical metre bounds",
        )
    algorithm_limits: Mapping[str, Mapping[str, tuple[float, Literal["max", "min"]]]] = {
        UAV_MODEL_REF: {
            "max_speed_mps": (80.0, "max"),
            "max_turn_rate_deg_s": (30.0, "max"),
            "max_vertical_speed_mps": (20.0, "max"),
            "max_acceleration_mps2": (8.0, "max"),
            "max_deceleration_mps2": (10.0, "max"),
            "max_altitude_m": (3000.0, "max"),
            "min_altitude_m": (0.0, "min"),
        },
        AUV_MODEL_REF: {
            "max_speed_mps": (4.1, "max"),
            "max_turn_rate_deg_s": (15.0, "max"),
            "max_vertical_speed_mps": (2.0, "max"),
            "min_depth_m": (-300.0, "min"),
            "max_depth_m": (0.0, "max"),
        },
        MMG_MODEL_REF: {
            "max_speed_mps": (_MAX_MMG_SPEED_MPS, "max"),
            "max_nps": (_MAX_MMG_NPS, "max"),
            "max_rudder_rad": (0.3, "max"),
        },
    }
    for key, (limit, direction) in algorithm_limits.get(model_ref, {}).items():
        if key not in result:
            continue
        actual = float(result[key])
        unsupported = actual > limit if direction == "max" else actual < limit
        if unsupported:
            raise _error(
                "dynamics.parameters_unsupported",
                ("parameters", key),
                actual,
                "parameter exceeds the proven bound of the underlying algorithm",
                f"use {key} within the native algorithm limit {limit}",
            )
    return result


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


class _JsonFrozenTuple(tuple[Any, ...]):
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence) and not isinstance(other, (str, bytes, bytearray)):
            return tuple(self) == tuple(other)
        return False

    __hash__ = tuple.__hash__


def _snapshot_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _snapshot_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _JsonFrozenTuple(_snapshot_freeze(item) for item in value)
    return value


def _validate_snapshot_native_shape(snapshot: NativeDynamicsSnapshotV2) -> None:
    expected = {"step_count", "last_state"}
    if snapshot.model_ref == MMG_MODEL_REF:
        expected.add("core")
    state = snapshot.native_state
    step_count = state.get("step_count")
    last_state = state.get("last_state")
    valid = (
        set(state) == expected
        and isinstance(step_count, int)
        and not isinstance(step_count, bool)
        and step_count >= 0
        and (last_state is None or isinstance(last_state, Mapping))
        and (snapshot.model_ref != MMG_MODEL_REF or isinstance(state.get("core"), Mapping))
    )
    if valid and last_state is not None:
        try:
            DynamicsStateV2.model_validate(_plain(last_state))
        except (TypeError, ValueError):
            valid = False
    if not valid:
        raise _error(
            "dynamics.snapshot_integrity_invalid",
            ("snapshot", "native_state"),
            tuple(sorted(state)),
            "native continuation state has an invalid canonical shape",
            "restore the unmodified model-specific continuation record",
        )


def validate_native_dynamics_snapshot_v2(snapshot: NativeDynamicsSnapshotV2) -> None:
    """Validate complete self-contained snapshot integrity without restoring a core."""

    if not isinstance(snapshot, NativeDynamicsSnapshotV2):
        raise _error(
            "dynamics.snapshot_invalid",
            ("snapshot",),
            type(snapshot).__name__,
            "snapshot integrity validation requires the immutable native DTO",
            "validate NativeDynamicsSnapshotV2 parsed from canonical checkpoint data",
        )
    if snapshot.snapshot_hash != NativeDynamicsSnapshotV2.compute_snapshot_hash(snapshot):
        raise _error(
            "dynamics.snapshot_integrity_invalid",
            ("snapshot", "snapshot_hash"),
            snapshot.snapshot_hash,
            "snapshot canonical hash does not match its complete payload",
            "use the original unmodified native snapshot",
        )
    if snapshot.parameter_hash != compute_native_parameter_hash_v2(snapshot.parameters):
        raise _error(
            "dynamics.snapshot_parameters_mismatch",
            ("snapshot", "parameter_hash"),
            snapshot.parameter_hash,
            "snapshot parameters differ from their canonical identity hash",
            "use the original resolved native parameter set",
        )
    if snapshot.binding_identity_hash != compute_native_binding_identity_hash_v2(snapshot):
        raise _error(
            "dynamics.snapshot_integrity_invalid",
            ("snapshot", "binding_identity_hash"),
            snapshot.binding_identity_hash,
            "snapshot binding identity evidence was modified",
            "use the original complete native snapshot",
        )
    _validate_snapshot_native_shape(snapshot)


class NativeDynamicsAdapterV2:
    units = MappingProxyType(_UNITS)

    def __init__(
        self,
        *,
        model_ref: str,
        entity_id: str,
        parameters: Mapping[str, int | float],
        seed: int,
        resource_ref: str,
        model_metadata: ModelFactoryMetadataV2,
        native_core: _MMGCoreV2 | None = None,
        restored_from_instance_id: str | None = None,
    ) -> None:
        self.model_ref = model_ref
        self.entity_id = entity_id
        self.instance_id = _next_instance_id()
        self.restored_from_instance_id = restored_from_instance_id
        self._parameters = MappingProxyType(dict(parameters))
        self.resource_ref = resource_ref
        self._model_metadata = model_metadata
        self._parameter_hash = compute_native_parameter_hash_v2(self._parameters)
        self._seed = seed
        self._rng_fingerprint = _fingerprint(model_ref, entity_id, seed)
        self._native_core = native_core
        self._closed = False
        self._step_count = 0
        self._last_state: DynamicsStateV2 | None = None
        self._native_initialized = False
        self._step_lock = Lock()
        self._solver_identity = self._resolve_solver_identity(native_core)
        configure = None if native_core is None else getattr(native_core, "configure", None)
        if callable(configure):
            configure(
                {
                    "max_speed_mps": float(
                        self._parameters.get("max_speed_mps", _MAX_MMG_SPEED_MPS)
                    )
                }
            )

    def _resolve_solver_identity(self, native_core: _MMGCoreV2 | None) -> str:
        if native_core is None:
            return self.model_ref
        explicit = getattr(native_core, "solver_identity", None)
        if isinstance(explicit, str) and explicit:
            return explicit
        return f"{type(native_core).__module__}.{type(native_core).__qualname__}"

    def diagnostic(self) -> NativeDynamicsDiagnosticV2:
        return NativeDynamicsDiagnosticV2(
            schema_version="2.0",
            model_ref=self.model_ref,
            entity_id=self.entity_id,
            instance_id=self.instance_id,
            restored_from_instance_id=self.restored_from_instance_id,
            rng_fingerprint=self._rng_fingerprint,
            parameter_hash=self._parameter_hash,
            closed=self._closed,
        )

    def step(
        self,
        *,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
        tick_seconds: float,
    ) -> DynamicsStateV2:
        if not self._step_lock.acquire(blocking=False):
            raise _error(
                "dynamics.concurrent_step_forbidden",
                ("adapter", self.instance_id, "step"),
                self.instance_id,
                "native adapter is a single-writer runtime component",
                "serialize step calls through the owning session scheduler",
            )
        try:
            return self._step_once(
                state=state,
                command=command,
                tick_seconds=tick_seconds,
            )
        finally:
            self._step_lock.release()

    def _step_once(
        self,
        *,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
        tick_seconds: float,
    ) -> DynamicsStateV2:
        if self._closed:
            raise _error(
                "dynamics.adapter_closed",
                ("adapter", self.instance_id),
                self.instance_id,
                "closed native dynamics adapter cannot advance",
                "create or restore a live independently owned adapter",
            )
        if not isinstance(state, DynamicsStateV2):
            raise _error(
                "dynamics.state_invalid",
                ("state",),
                type(state).__name__,
                "step requires a typed finite DynamicsStateV2",
                "construct the canonical v2 dynamics state DTO",
            )
        if not _finite_number(tick_seconds) or float(tick_seconds) <= 0.0:
            raise _error(
                "dynamics.tick_invalid",
                ("tick_seconds",),
                tick_seconds,
                "tick duration must be a finite positive number of seconds",
                "provide the session's positive canonical tick interval",
            )
        try:
            if self.model_ref == FIXED_MODEL_REF:
                result = self._step_fixed(state, command)
            elif self.model_ref == UAV_MODEL_REF:
                result = self._step_uav(state, command, float(tick_seconds))
            elif self.model_ref == AUV_MODEL_REF:
                result = self._step_auv(state, command, float(tick_seconds))
            elif self.model_ref == MMG_MODEL_REF:
                result = self._step_mmg(state, command, float(tick_seconds))
            else:  # Exact-ref construction prevents this defensive path.
                raise _error(
                    "dynamics.model_unknown",
                    ("model_ref",),
                    self.model_ref,
                    "adapter model reference is no longer registered",
                    "restore using a supported exact model reference",
                )
        except NativeDynamicsErrorV2:
            raise
        except (TypeError, ValueError) as error:
            raise _error(
                "dynamics.state_invalid",
                ("step", self.entity_id),
                type(error).__name__,
                "native dynamics function rejected canonical state or parameters",
                "verify model-specific bounds and canonical SI units",
            ) from error
        self._step_count += 1
        self._last_state = result
        return result

    def _require_kinematic_command(
        self, command: DynamicsCommandV2 | MMGCommandV2 | None
    ) -> DynamicsCommandV2:
        if not isinstance(command, DynamicsCommandV2):
            raise _error(
                "dynamics.command_invalid",
                ("command",),
                type(command).__name__,
                "kinematic adapter requires a typed DynamicsCommandV2",
                "construct a finite speed, heading, and vertical target command",
            )
        return command

    def _step_uav(
        self,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
        tick_seconds: float,
    ) -> DynamicsStateV2:
        target = self._require_kinematic_command(command)
        minimum = float(self._parameters.get("min_altitude_m", 0.0))
        maximum = float(self._parameters.get("max_altitude_m", 3000.0))
        if not minimum <= target.target_vertical_m <= maximum:
            raise _error(
                "dynamics.command_invalid",
                ("command", "target_vertical_m"),
                target.target_vertical_m,
                "UAV vertical target is outside configured metre bounds",
                "command an altitude within the resolved dynamics parameters",
            )
        speed = math.hypot(state.velocity_mps[0], state.velocity_mps[1])
        source = UAVState(
            position=state.position_m,
            heading_deg=state.heading_deg,
            speed_mps=min(speed, 80.0),
        )
        output = step_uav(
            source,
            UAVCommand(
                heading_deg=target.target_heading_deg,
                speed_mps=min(target.target_speed_mps, 80.0),
                altitude_m=min(target.target_vertical_m, 3000.0),
            ),
            tick_seconds=tick_seconds,
            max_turn_rate_deg_s=float(self._parameters.get("max_turn_rate_deg_s", 30.0)),
            max_climb_rate_mps=float(self._parameters.get("max_vertical_speed_mps", 20.0)),
            max_acceleration_mps2=float(self._parameters.get("max_acceleration_mps2", 8.0)),
            max_deceleration_mps2=float(self._parameters.get("max_deceleration_mps2", 10.0)),
            max_speed_mps=min(float(self._parameters.get("max_speed_mps", 80.0)), 80.0),
        )
        velocity = (
            (output.position[0] - state.position_m[0]) / tick_seconds,
            (output.position[1] - state.position_m[1]) / tick_seconds,
            (output.position[2] - state.position_m[2]) / tick_seconds,
        )
        return DynamicsStateV2(
            schema_version="2.0",
            position_m=output.position,
            velocity_mps=velocity,
            heading_deg=output.heading_deg,
        )

    def _step_auv(
        self,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
        tick_seconds: float,
    ) -> DynamicsStateV2:
        target = self._require_kinematic_command(command)
        minimum = float(self._parameters.get("min_depth_m", -300.0))
        maximum = float(self._parameters.get("max_depth_m", 0.0))
        if not minimum <= target.target_vertical_m <= maximum:
            raise _error(
                "dynamics.command_invalid",
                ("command", "target_vertical_m"),
                target.target_vertical_m,
                "AUV vertical target is outside configured metre bounds",
                "command a negative z value within the resolved depth bounds",
            )
        speed = math.hypot(state.velocity_mps[0], state.velocity_mps[1])
        output = step_auv(
            AUVState(
                position=state.position_m,
                heading_deg=state.heading_deg,
                speed_mps=min(speed, 4.1),
            ),
            AUVCommand(
                heading_deg=target.target_heading_deg,
                speed_mps=min(
                    target.target_speed_mps,
                    float(self._parameters.get("max_speed_mps", 4.1)),
                    4.1,
                ),
                depth_m=-target.target_vertical_m,
            ),
            tick_seconds=tick_seconds,
            max_turn_rate_deg_s=float(self._parameters.get("max_turn_rate_deg_s", 15.0)),
            max_vertical_rate_mps=float(self._parameters.get("max_vertical_speed_mps", 2.0)),
        )
        velocity = (
            (output.position[0] - state.position_m[0]) / tick_seconds,
            (output.position[1] - state.position_m[1]) / tick_seconds,
            (output.position[2] - state.position_m[2]) / tick_seconds,
        )
        return DynamicsStateV2(
            schema_version="2.0",
            position_m=output.position,
            velocity_mps=velocity,
            heading_deg=output.heading_deg,
        )

    def _step_fixed(
        self,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
    ) -> DynamicsStateV2:
        if command is not None:
            raise _error(
                "dynamics.fixed_motion_forbidden",
                ("command",),
                type(command).__name__,
                "fixed dynamics cannot accept a motion command",
                "send no dynamics command to fixed facilities",
            )
        return state

    def _step_mmg(
        self,
        state: DynamicsStateV2,
        command: DynamicsCommandV2 | MMGCommandV2 | None,
        tick_seconds: float,
    ) -> DynamicsStateV2:
        if not isinstance(command, MMGCommandV2):
            raise _error(
                "dynamics.command_invalid",
                ("command",),
                type(command).__name__,
                "MMG adapter requires typed nps and rudder-radian controls",
                "construct an MMGCommandV2 within declared native limits",
            )
        if self._native_core is None:
            raise _error(
                "dynamics.native_core_unavailable",
                ("model_ref",),
                self.model_ref,
                "MMG native core loader produced no isolated core",
                "inject a per-adapter native core factory",
            )
        substeps = int(self._parameters.get("substeps", 1))
        dt_s = float(self._parameters.get("integration_dt_s", tick_seconds / substeps))
        if not math.isclose(dt_s * substeps, tick_seconds, rel_tol=0.0, abs_tol=1e-12):
            raise _error(
                "dynamics.tick_invalid",
                ("tick_seconds",),
                tick_seconds,
                "MMG substep interval does not exactly cover the public tick",
                "align integration_dt_s times substeps with tick_seconds",
            )
        if self._native_initialized:
            if self._last_state is None or state != self._last_state:
                raise _error(
                    "dynamics.state_authority_conflict",
                    ("state", self.entity_id),
                    state.model_dump(mode="json"),
                    "external state conflicts with the initialized native solver authority",
                    "continue from the adapter's last returned state or restore its snapshot",
                )
        else:
            set_state = getattr(self._native_core, "set_state", None)
            if callable(set_state):
                set_state(state)
            self._native_initialized = True
        step_many = getattr(self._native_core, "step_many", None)
        if not callable(step_many):
            raise _error(
                "dynamics.native_core_invalid",
                ("adapter", self.instance_id, "step_many"),
                type(self._native_core).__name__,
                "MMG native core lacks transactional batch-step support",
                "provide the trusted MMG worker core with step_many",
            )
        values = step_many(
            nps=command.nps,
            rudder_rad=command.rudder_rad,
            dt_s=dt_s,
            substeps=substeps,
        )
        if len(values) != 6 or any(not _finite_number(item) for item in values):
            raise _error(
                "dynamics.native_output_invalid",
                ("native_core", "output"),
                values,
                "MMG native core returned a noncanonical six-value state",
                "return finite x, y, z, east-speed, north-speed, and heading values",
            )
        return DynamicsStateV2(
            schema_version="2.0",
            position_m=(values[0], values[1], values[2]),
            velocity_mps=(values[3], values[4], 0.0),
            heading_deg=values[5] % 360.0,
        )

    def _reconcile_authoritative_state(self, state: DynamicsStateV2) -> None:
        """Adopt a World boundary/collision correction for the next MMG step.

        MMG owns its unconstrained continuation state, while World owns the
        post-adjudication position and velocity.  This private hook is called
        only after a trusted motion candidate has been changed by the generic
        BoundarySystem, so the next solver step starts from the World-authority
        result rather than rejecting that correction as an external override.
        """

        if not self._step_lock.acquire(blocking=False):
            raise _error(
                "dynamics.concurrent_step_forbidden",
                ("adapter", self.instance_id, "reconcile"),
                self.instance_id,
                "native adapter reconciliation must share the single writer",
                "serialize boundary reconciliation through the owning World transaction",
            )
        try:
            if self._closed:
                raise _error(
                    "dynamics.adapter_closed",
                    ("adapter", self.instance_id),
                    self.instance_id,
                    "closed native dynamics adapter cannot reconcile state",
                    "restore or create a live independently owned adapter",
                )
            if self.model_ref != MMG_MODEL_REF or self._native_core is None:
                raise _error(
                    "dynamics.native_core_unavailable",
                    ("adapter", self.instance_id, "reconcile"),
                    self.model_ref,
                    "only a live MMG adapter can reconcile authoritative motion",
                    "invoke reconciliation only for a boundary-corrected MMG candidate",
                )
            if not self._native_initialized or self._last_state is None:
                raise _error(
                    "dynamics.native_core_unavailable",
                    ("adapter", self.instance_id, "reconcile"),
                    self.entity_id,
                    "MMG state cannot reconcile before its first authoritative step",
                    "step the adapter before applying a boundary correction",
                )
            set_state = getattr(self._native_core, "set_state", None)
            if not callable(set_state):
                raise _error(
                    "dynamics.native_core_invalid",
                    ("adapter", self.instance_id, "reconcile"),
                    type(self._native_core).__name__,
                    "MMG core cannot accept authoritative boundary state",
                    "provide a per-adapter MMG core with a set_state protocol",
                )
            try:
                set_state(state)
            except (RuntimeError, TypeError, ValueError) as error:
                raise _error(
                    "dynamics.native_core_failed",
                    ("adapter", self.instance_id, "reconcile"),
                    type(error).__name__,
                    "MMG core rejected the authoritative boundary state",
                    "repair the isolated MMG worker state protocol",
                ) from error
            self._last_state = state
        finally:
            self._step_lock.release()

    def snapshot(self) -> NativeDynamicsSnapshotV2:
        native_state: dict[str, Any] = {
            "step_count": self._step_count,
            "last_state": (
                None if self._last_state is None else self._last_state.model_dump(mode="json")
            ),
        }
        if self._native_core is not None:
            native_state["core"] = _plain(self._native_core.snapshot())
        metadata = self._model_metadata
        identity_payload = {
            "model_ref": self.model_ref,
            "resource_ref": self.resource_ref,
            "artifact_sha256": metadata.artifact_sha256,
            "interface_version": metadata.interface_version,
            "input_schema": metadata.input_schema,
            "output_schema": metadata.output_schema,
            "units": metadata.units,
            "field_units": metadata.field_units,
            "parameter_hash": self._parameter_hash,
            "solver_identity": self._solver_identity,
        }
        snapshot = NativeDynamicsSnapshotV2(
            schema_version="2.0",
            model_ref=self.model_ref,
            entity_id=self.entity_id,
            instance_id=self.instance_id,
            restored_from_instance_id=self.restored_from_instance_id,
            resource_ref=self.resource_ref,
            artifact_sha256=metadata.artifact_sha256,
            interface_version=metadata.interface_version,
            input_schema=metadata.input_schema,
            output_schema=metadata.output_schema,
            units=dict(metadata.units),
            field_units=dict(metadata.field_units),
            parameters=dict(self._parameters),
            parameter_hash=self._parameter_hash,
            binding_identity_hash=_canonical_hash(identity_payload),
            solver_identity=self._solver_identity,
            seed=self._seed,
            native_state=native_state,
            snapshot_hash="sha256:" + "0" * 64,
        )
        object.__setattr__(snapshot, "units", MappingProxyType(dict(snapshot.units)))
        object.__setattr__(snapshot, "field_units", MappingProxyType(dict(snapshot.field_units)))
        object.__setattr__(snapshot, "native_state", _snapshot_freeze(native_state))
        snapshot = snapshot.model_copy(
            update={"snapshot_hash": NativeDynamicsSnapshotV2.compute_snapshot_hash(snapshot)}
        )
        return snapshot

    def _restore_native_state(self, value: Mapping[str, Any]) -> None:
        allowed = {"step_count", "last_state"}
        if self._native_core is not None:
            allowed.add("core")
        if set(value) != allowed:
            raise ValueError("native continuation state has undeclared or missing fields")
        step_count = value.get("step_count")
        last_state = value.get("last_state")
        if not isinstance(step_count, int) or isinstance(step_count, bool) or step_count < 0:
            raise ValueError("invalid native step count")
        self._step_count = step_count
        self._last_state = (
            None if last_state is None else DynamicsStateV2.model_validate(_plain(last_state))
        )
        core_state = value.get("core")
        if core_state is not None:
            if self._native_core is None or not isinstance(core_state, Mapping):
                raise ValueError("native core snapshot cannot be restored")
            self._native_core.restore(_plain(core_state))
        self._native_initialized = self._native_core is not None and step_count > 0

    def _mark_origin(self, instance_id: str) -> None:
        self.restored_from_instance_id = instance_id

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._native_core is not None:
            try:
                self._native_core.close()
            finally:
                _release_core(self._native_core)


NativeCoreLoaderV2 = Callable[[], _MMGCoreV2]


class NativeDynamicsAdapterFactoryV2:
    """Dispatch only by a supported exact executable model reference."""

    def __init__(
        self,
        *,
        native_loaders: Mapping[str, NativeCoreLoaderV2] | None = None,
        worker_artifacts: Mapping[str, NativeArtifactSourceV2] | None = None,
        artifact_sources: Mapping[str, NativeArtifactSourceV2] | None = None,
        artifact_manifest: Mapping[str, NativeArtifactEvidenceV2] | None = None,
    ) -> None:
        self._native_loaders = dict(native_loaders or {})
        self._artifact_sources = dict(artifact_sources or {})
        for model_ref, source in (worker_artifacts or {}).items():
            existing = self._artifact_sources.get(model_ref)
            if existing is not None and existing != source:
                raise _error(
                    "dynamics.artifact_source_invalid",
                    ("artifact_sources", model_ref),
                    model_ref,
                    "native artifact source was injected with conflicting descriptors",
                    "provide one exact source descriptor per native model",
                )
            self._artifact_sources[model_ref] = source
        current = _validated_artifact_manifest(None, self._artifact_sources)
        if artifact_manifest is not None:
            mismatch = next(
                (
                    model_ref
                    for model_ref, evidence in artifact_manifest.items()
                    if model_ref not in current or current[model_ref] != evidence
                ),
                None,
            )
            if mismatch is not None:
                raise _error(
                    (
                        "dynamics.artifact_bytes_mismatch"
                        if mismatch in self._artifact_sources
                        else "dynamics.artifact_manifest_mismatch"
                    ),
                    ("artifact_manifest", str(mismatch)),
                    getattr(artifact_manifest[mismatch], "artifact_sha256", None),
                    "supplied native evidence differs from current artifact bytes",
                    "rebuild evidence after installing the exact source or worker artifact",
                )
        self._artifact_manifest = current

    def build(
        self,
        *,
        model_ref: str,
        entity_id: str,
        parameters: Mapping[str, object],
        seed: int,
        resource_ref: str | None = None,
        artifact_sha256: str | None = None,
        model_metadata: ModelFactoryMetadataV2 | None = None,
    ) -> NativeDynamicsAdapterV2:
        if model_ref not in _MODEL_REFS:
            raise _error(
                "dynamics.model_unknown",
                ("model_ref",),
                model_ref,
                "no native dynamics adapter is available for this exact model reference",
                "use one exact reference returned by native_dynamics_metadata_v2",
            )
        if not isinstance(entity_id, str) or not entity_id:
            raise _error(
                "dynamics.entity_invalid",
                ("entity_id",),
                entity_id,
                "native dynamics entity identity must be a nonempty string",
                "provide the resolved entity identifier",
            )
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise _error(
                "dynamics.seed_invalid",
                ("seed",),
                seed,
                "native dynamics seed must be an exact integer",
                "provide the session's deterministic integer seed",
            )
        if not isinstance(parameters, Mapping):
            raise _error(
                "dynamics.parameters_invalid",
                ("parameters",),
                type(parameters).__name__,
                "native dynamics parameters must be a mapping",
                "provide resolved unit-suffixed model parameters",
            )
        metadata = (
            model_metadata
            or native_dynamics_metadata_v2(
                artifact_manifest=self._artifact_manifest,
                artifact_sources=self._artifact_sources,
            )[model_ref]
        )
        current_evidence = _validated_artifact_manifest(
            self._artifact_manifest,
            self._artifact_sources,
        )[model_ref]
        if not current_evidence.available:
            raise _error(
                "dynamics.artifact_unavailable",
                ("artifact_manifest", model_ref),
                current_evidence.artifact_path,
                "native executable artifact bytes are unavailable",
                "install and explicitly inject the exact trusted native artifact",
            )
        if metadata.exact_ref != model_ref:
            raise _error(
                "dynamics.model_evidence_invalid",
                ("model_metadata", "exact_ref"),
                metadata.exact_ref,
                "model evidence does not name the requested exact executable model",
                "provide metadata for the same exact native model reference",
            )
        expected_artifact = metadata.artifact_sha256
        if current_evidence.artifact_sha256 != expected_artifact:
            raise _error(
                "dynamics.artifact_bytes_mismatch",
                ("artifact_manifest", model_ref, "artifact_sha256"),
                current_evidence.artifact_sha256,
                "installed native artifact bytes drifted from resolved model evidence",
                "rebuild the registry and resolved scenario against the installed artifact",
            )
        if artifact_sha256 is not None and artifact_sha256 != expected_artifact:
            raise _error(
                "dynamics.model_evidence_invalid",
                ("artifact_sha256",),
                artifact_sha256,
                "runtime artifact hash differs from trusted native model evidence",
                "use the artifact hash for this exact installed model",
            )
        validated_parameters = _parameters(model_ref, parameters)
        native_core: _MMGCoreV2 | None = None
        if model_ref == MMG_MODEL_REF:
            loader = self._native_loaders.get(model_ref)
            if loader is None:
                builtin_worker = _builtin_artifact_sources()[model_ref]
                selected_worker = self._artifact_sources.get(model_ref)
                if selected_worker is not None and selected_worker != builtin_worker:
                    raise _error(
                        "dynamics.native_core_unavailable",
                        ("artifact_sources", model_ref),
                        selected_worker.artifact_path,
                        "a substituted MMG worker requires its matching explicit core loader",
                        (
                            "inject the matching isolated worker loader or use the built-in "
                            "trusted worker"
                        ),
                    )
                from openmdbench.dynamics.sim2sea_mmg_worker import spawn_sim2sea_mmg_core_v2

                loader = spawn_sim2sea_mmg_core_v2
            try:
                native_core = loader()
            except Exception as error:
                raise _error(
                    "dynamics.native_core_failed",
                    ("model_ref", model_ref),
                    type(error).__name__,
                    "isolated MMG native core construction failed",
                    "repair the injected per-adapter native core factory",
                ) from error
            protocol_methods = ("step", "snapshot", "restore", "close")
            if any(not callable(getattr(native_core, field, None)) for field in protocol_methods):
                close = getattr(native_core, "close", None)
                if callable(close):
                    with suppress(Exception):
                        close()
                raise _error(
                    "dynamics.native_core_invalid",
                    ("model_ref", model_ref),
                    type(native_core).__name__,
                    "injected MMG core does not implement the isolation protocol",
                    "provide step, snapshot, restore, and close methods",
                )
            _claim_core(native_core)
        try:
            return NativeDynamicsAdapterV2(
                model_ref=model_ref,
                entity_id=entity_id,
                parameters=validated_parameters,
                seed=seed,
                resource_ref=resource_ref or model_ref,
                model_metadata=metadata,
                native_core=native_core,
            )
        except Exception as error:
            if native_core is not None:
                close = getattr(native_core, "close", None)
                if callable(close):
                    with suppress(Exception):
                        close()
                _release_core(native_core)
            raise _error(
                "dynamics.solver_identity_invalid",
                ("native_core", "solver_identity"),
                type(error).__name__,
                "native core did not expose a stable solver identity",
                "provide a finite nonempty solver identity that is safe to inspect",
            ) from error

    def restore(
        self,
        snapshot: NativeDynamicsSnapshotV2,
        *,
        expected_binding_identity: str,
        checkpoint_anchor: str,
        model_metadata: ModelFactoryMetadataV2 | None = None,
    ) -> NativeDynamicsAdapterV2:
        if not isinstance(snapshot, NativeDynamicsSnapshotV2):
            raise _error(
                "dynamics.snapshot_invalid",
                ("snapshot",),
                type(snapshot).__name__,
                "restore requires a typed immutable native dynamics snapshot",
                "pass the exact result of adapter.snapshot",
            )
        if snapshot.model_ref not in _MODEL_REFS:
            raise _error(
                "dynamics.model_unknown",
                ("snapshot", "model_ref"),
                snapshot.model_ref,
                "snapshot names no supported exact native model",
                "restore with the same installed exact model reference",
            )
        if not snapshot.entity_id or not snapshot.instance_id:
            raise _error(
                "dynamics.snapshot_invalid",
                ("snapshot", "identity"),
                snapshot.entity_id or snapshot.instance_id or "empty",
                "snapshot entity and source instance identity must be nonempty",
                "restore an intact adapter snapshot",
            )
        if snapshot.snapshot_hash != NativeDynamicsSnapshotV2.compute_snapshot_hash(snapshot):
            raise _error(
                "dynamics.snapshot_integrity_invalid",
                ("snapshot", "snapshot_hash"),
                snapshot.snapshot_hash,
                "snapshot canonical hash does not match its complete payload",
                "restore an intact snapshot without mutation",
            )
        parameter_hash = compute_native_parameter_hash_v2(snapshot.parameters)
        if snapshot.parameter_hash != parameter_hash:
            raise _error(
                "dynamics.snapshot_parameters_mismatch",
                ("snapshot", "parameter_hash"),
                snapshot.parameter_hash,
                "snapshot parameters differ from their canonical identity hash",
                "restore the original resolved parameter set",
            )
        if snapshot.binding_identity_hash != compute_native_binding_identity_hash_v2(snapshot):
            raise _error(
                "dynamics.snapshot_integrity_invalid",
                ("snapshot", "binding_identity_hash"),
                snapshot.binding_identity_hash,
                "snapshot binding or solver identity evidence was modified",
                "restore the original complete canonical snapshot",
            )
        _validate_snapshot_native_shape(snapshot)
        if (
            expected_binding_identity != snapshot.binding_identity_hash
            or checkpoint_anchor != snapshot.snapshot_hash
        ):
            raise _error(
                "dynamics.snapshot_anchor_mismatch",
                ("snapshot", "checkpoint_anchor"),
                snapshot.snapshot_hash,
                "snapshot identity differs from the trusted external checkpoint anchor",
                "restore the exact checkpoint held by its owner",
            )
        metadata = (
            model_metadata
            or native_dynamics_metadata_v2(
                artifact_manifest=self._artifact_manifest,
                artifact_sources=self._artifact_sources,
            )[snapshot.model_ref]
        )
        model_fields = (
            "artifact_sha256",
            "interface_version",
            "input_schema",
            "output_schema",
            "units",
            "field_units",
        )
        if any(getattr(snapshot, field) != getattr(metadata, field) for field in model_fields):
            raise _error(
                "dynamics.snapshot_model_mismatch",
                ("snapshot", "model_evidence"),
                snapshot.model_ref,
                "installed native model evidence differs from the snapshot",
                "restore with the exact trusted native model artifact and interface",
            )
        adapter = self.build(
            model_ref=snapshot.model_ref,
            entity_id=snapshot.entity_id,
            parameters=snapshot.parameters,
            seed=snapshot.seed,
            resource_ref=snapshot.resource_ref,
            artifact_sha256=snapshot.artifact_sha256,
            model_metadata=metadata,
        )
        adapter._mark_origin(snapshot.instance_id)
        if adapter._solver_identity != snapshot.solver_identity:
            adapter.close()
            raise _error(
                "dynamics.solver_identity_mismatch",
                ("snapshot", "solver_identity"),
                snapshot.solver_identity,
                "target MMG core is not the solver implementation that produced the snapshot",
                "restore using a fresh core with the exact same solver identity",
            )
        try:
            adapter._restore_native_state(snapshot.native_state)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            adapter.close()
            raise _error(
                "dynamics.snapshot_integrity_invalid",
                ("snapshot", "native_state"),
                type(error).__name__,
                "native continuation state is malformed or incompatible",
                "restore an intact snapshot from the same exact model",
            ) from error
        return adapter


def build_native_artifact_evidence_v2(
    source: NativeArtifactSourceV2,
) -> NativeArtifactEvidenceV2:
    """Hash the actual installed artifact bytes named by a trusted source record."""

    if not isinstance(source, NativeArtifactSourceV2):
        raise _error(
            "dynamics.artifact_source_invalid",
            ("artifact_source",),
            type(source).__name__,
            "native artifact evidence requires a validated source descriptor",
            "provide NativeArtifactSourceV2 with an exact model and artifact path",
        )
    path = Path(source.artifact_path)
    try:
        payload = path.read_bytes()
        available = True
    except FileNotFoundError:
        payload = b""
        available = False
    except OSError as error:
        raise _error(
            "dynamics.artifact_unreadable",
            ("artifact_source", source.model_ref, "artifact_path"),
            source.artifact_path,
            "native artifact bytes cannot be read safely",
            "install a readable immutable artifact at the declared path",
        ) from error
    return NativeArtifactEvidenceV2(
        schema_version="2.0",
        model_ref=source.model_ref,
        source=(
            "source_digest" if source.artifact_kind == "python_source" else "installed_artifact"
        ),
        artifact_path=source.artifact_path,
        artifact_kind=source.artifact_kind,
        build_id=source.build_id,
        available=available,
        artifact_sha256=f"sha256:{hashlib.sha256(payload).hexdigest()}",
    )


def _builtin_artifact_sources() -> dict[str, NativeArtifactSourceV2]:
    native_source = str(Path(__file__).resolve())
    return {
        UAV_MODEL_REF: NativeArtifactSourceV2(
            schema_version="2.0",
            model_ref=UAV_MODEL_REF,
            artifact_path=str(Path(step_uav.__code__.co_filename).resolve()),
            artifact_kind="python_source",
            build_id="openmdbench-uav-v2",
        ),
        AUV_MODEL_REF: NativeArtifactSourceV2(
            schema_version="2.0",
            model_ref=AUV_MODEL_REF,
            artifact_path=str(Path(step_auv.__code__.co_filename).resolve()),
            artifact_kind="python_source",
            build_id="openmdbench-auv-v2",
        ),
        FIXED_MODEL_REF: NativeArtifactSourceV2(
            schema_version="2.0",
            model_ref=FIXED_MODEL_REF,
            artifact_path=native_source,
            artifact_kind="python_source",
            build_id="openmdbench-fixed-v2",
        ),
        MMG_MODEL_REF: NativeArtifactSourceV2(
            schema_version="2.0",
            model_ref=MMG_MODEL_REF,
            artifact_path=str(Path(__file__).with_name("sim2sea_mmg_worker.py").resolve()),
            artifact_kind="process_worker",
            build_id="sim2sea-mmg-worker-v2",
        ),
    }


def native_artifact_manifest_v2(
    *,
    worker_artifacts: Mapping[str, NativeArtifactSourceV2] | None = None,
) -> Mapping[str, NativeArtifactEvidenceV2]:
    sources = _builtin_artifact_sources()
    for model_ref, source in (worker_artifacts or {}).items():
        if model_ref != MMG_MODEL_REF or source.model_ref != model_ref:
            raise _error(
                "dynamics.artifact_source_invalid",
                ("worker_artifacts", str(model_ref)),
                getattr(source, "model_ref", None),
                "worker artifact injection must name the exact supported MMG model",
                "inject the MMG worker under its matching exact model reference",
            )
        sources[model_ref] = source
    return MappingProxyType(
        {
            model_ref: build_native_artifact_evidence_v2(sources[model_ref])
            for model_ref in _MODEL_REFS
        }
    )


def _validated_artifact_manifest(
    artifact_manifest: Mapping[str, NativeArtifactEvidenceV2] | None,
    artifact_sources: Mapping[str, NativeArtifactSourceV2] | None = None,
) -> Mapping[str, NativeArtifactEvidenceV2]:
    expected = dict(native_artifact_manifest_v2())
    for model_ref, source in (artifact_sources or {}).items():
        expected_kind = "process_worker" if model_ref == MMG_MODEL_REF else "python_source"
        if (
            model_ref not in expected
            or source.model_ref != model_ref
            or source.artifact_kind != expected_kind
        ):
            raise _error(
                "dynamics.artifact_source_invalid",
                ("artifact_sources", str(model_ref)),
                getattr(source, "model_ref", None),
                "artifact source does not match a supported exact native model",
                "key each source by its matching exact native model reference",
            )
        expected[model_ref] = build_native_artifact_evidence_v2(source)
    supplied = expected if artifact_manifest is None else artifact_manifest
    mismatch = next(
        (
            model_ref
            for model_ref in expected
            if not isinstance(supplied.get(model_ref), NativeArtifactEvidenceV2)
            or supplied[model_ref] != expected[model_ref]
        ),
        None,
    )
    if set(supplied) != set(expected) or mismatch is not None:
        code = (
            "dynamics.artifact_bytes_mismatch"
            if mismatch is not None and mismatch in (artifact_sources or {})
            else "dynamics.artifact_manifest_mismatch"
        )
        raise _error(
            code,
            ("artifact_manifest",),
            tuple(sorted(supplied)),
            "native artifact manifest differs from the currently installed artifact bytes",
            "rebuild trusted evidence from the exact installed source or worker artifact",
        )
    return MappingProxyType(dict(supplied))


def native_dynamics_metadata_v2(
    *,
    artifact_manifest: Mapping[str, NativeArtifactEvidenceV2] | None = None,
    artifact_sources: Mapping[str, NativeArtifactSourceV2] | None = None,
) -> Mapping[str, ModelFactoryMetadataV2]:
    manifest = _validated_artifact_manifest(artifact_manifest, artifact_sources)
    result: dict[str, ModelFactoryMetadataV2] = {}
    for exact_ref in _MODEL_REFS:
        model_id, version = exact_ref.rsplit("@", 1)
        result[exact_ref] = ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id=model_id,
            version=version,
            interface_version="2.0",
            input_schema="dynamics-input@2.0",
            output_schema="dynamics-output@2.0",
            units=dict(_UNITS),
            deterministic=True,
            thread_safe=False,
            process_safe=True,
            trusted=manifest[exact_ref].available,
            artifact_sha256=manifest[exact_ref].artifact_sha256,
            resource_types=("dynamics",),
            field_units={
                "position_m": "m",
                "velocity_mps": "m/s",
                "heading_deg": "deg_clockwise_from_north",
                "tick_seconds": "s",
            },
        )
    return MappingProxyType(result)


def native_dynamics_execution_policy_v2() -> Mapping[str, NativeDynamicsExecutionPolicyV2]:
    return MappingProxyType(
        {
            exact_ref: NativeDynamicsExecutionPolicyV2(
                schema_version="2.0",
                model_ref=exact_ref,
                isolation="spawn_process" if exact_ref == MMG_MODEL_REF else "in_process",
                max_in_process_concurrency=0 if exact_ref == MMG_MODEL_REF else 1,
                single_writer=True,
                reject_concurrent_step=True,
            )
            for exact_ref in _MODEL_REFS
        }
    )


class _RegisteredNativeDynamicsFactoryV2:
    def __init__(self, model_ref: str, metadata: ModelFactoryMetadataV2) -> None:
        self._model_ref = model_ref
        self._metadata = metadata
        self._catalog_bound = False
        self._resource_hashes: dict[str, str] = {}

    def bind_catalog(self, definitions: Sequence[CatalogResourceV2]) -> None:
        self._catalog_bound = True
        self._resource_hashes = {
            definition.exact_ref: definition.content_hash
            for definition in definitions
            if definition.resource_type == "dynamics" and definition.model_ref == self._model_ref
        }

    def binding_evidence(self) -> Mapping[str, str]:
        return dict(sorted(self._resource_hashes.items()))

    def __call__(self, definition: CatalogResourceV2) -> NativeDynamicsBindingV2:
        if definition.resource_type != "dynamics" or definition.model_ref != self._model_ref:
            raise ValueError("native registry definition does not match its exact model binding")
        if (
            self._catalog_bound
            and self._resource_hashes.get(definition.exact_ref) != definition.content_hash
        ):
            raise ModelBindingEvidenceErrorV2(
                "native resource is absent from this registry's bound catalog evidence"
            )
        parameters = {
            key: value for key, value in definition.content.items() if key in _KNOWN_PARAMETERS
        }
        validated = _parameters(self._model_ref, parameters)
        return NativeDynamicsBindingV2(
            schema_version="2.0",
            resource_ref=definition.exact_ref,
            model_ref=self._model_ref,
            artifact_sha256=self._metadata.artifact_sha256,
            interface_version=self._metadata.interface_version,
            input_schema=self._metadata.input_schema,
            output_schema=self._metadata.output_schema,
            units=dict(self._metadata.units),
            field_units=dict(self._metadata.field_units),
            parameters=validated,
        )


def register_native_dynamics_models_v2(
    registry: ModelRegistryV2,
    *,
    artifact_manifest: Mapping[str, NativeArtifactEvidenceV2] | None = None,
    artifact_sources: Mapping[str, NativeArtifactSourceV2] | None = None,
) -> None:
    """Register Catalog-resource factories for every supported exact native model."""

    for model_ref, native_metadata in native_dynamics_metadata_v2(
        artifact_manifest=artifact_manifest,
        artifact_sources=artifact_sources,
    ).items():
        if not native_metadata.trusted:
            continue
        model_id, version = model_ref.rsplit("@", 1)
        metadata = ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id=model_id,
            version=version,
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={
                "position_m": "m",
                "velocity_mps": "m/s",
                "heading_deg": "deg",
                "tick_seconds": "s",
            },
            deterministic=True,
            thread_safe=native_metadata.thread_safe,
            process_safe=native_metadata.process_safe,
            trusted=native_metadata.trusted,
            artifact_sha256=native_metadata.artifact_sha256,
            resource_types=("dynamics",),
            field_units={
                "position_m": "m",
                "velocity_mps": "m/s",
                "heading_deg": "deg",
                "tick_seconds": "s",
            },
        )
        registry.register(metadata, _RegisteredNativeDynamicsFactoryV2(model_ref, metadata))


def materialize_native_dynamics_binding_v2(
    binding: NativeDynamicsBindingV2,
    *,
    entity_id: str,
    seed: int,
    adapter_factory: NativeDynamicsAdapterFactoryV2 | None = None,
) -> NativeDynamicsAdapterV2:
    model_id, version = binding.model_ref.rsplit("@", 1)
    metadata = ModelFactoryMetadataV2(
        schema_version="2.0",
        model_id=model_id,
        version=version,
        interface_version="2.0",
        input_schema=binding.input_schema,
        output_schema=binding.output_schema,
        units=dict(binding.units),
        deterministic=True,
        thread_safe=False,
        process_safe=True,
        trusted=True,
        artifact_sha256=binding.artifact_sha256,
        resource_types=("dynamics",),
        field_units=dict(binding.field_units),
    )
    return (adapter_factory or NativeDynamicsAdapterFactoryV2()).build(
        model_ref=binding.model_ref,
        entity_id=entity_id,
        parameters=binding.parameters,
        seed=seed,
        resource_ref=binding.resource_ref,
        artifact_sha256=binding.artifact_sha256,
        model_metadata=metadata,
    )


__all__ = [
    "AUV_MODEL_REF",
    "DynamicsCommandV2",
    "DynamicsStateV2",
    "FIXED_MODEL_REF",
    "MMGCommandV2",
    "MMG_MODEL_REF",
    "NativeArtifactEvidenceV2",
    "NativeArtifactSourceV2",
    "NativeDynamicsAdapterFactoryV2",
    "NativeDynamicsAdapterV2",
    "NativeDynamicsBindingV2",
    "NativeDynamicsDiagnosticV2",
    "NativeDynamicsErrorV2",
    "NativeDynamicsExecutionPolicyV2",
    "NativeDynamicsSnapshotV2",
    "UAV_MODEL_REF",
    "compute_native_binding_identity_hash_v2",
    "compute_native_parameter_hash_v2",
    "compute_native_resolved_binding_identity_v2",
    "build_native_artifact_evidence_v2",
    "materialize_native_dynamics_binding_v2",
    "native_artifact_manifest_v2",
    "native_dynamics_execution_policy_v2",
    "native_dynamics_metadata_v2",
    "register_native_dynamics_models_v2",
    "validate_native_dynamics_snapshot_v2",
]

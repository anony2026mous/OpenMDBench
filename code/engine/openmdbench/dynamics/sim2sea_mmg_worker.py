"""Process-isolated, handle-multiplexed bridge for the trusted Sim2Sea MMG solver.

The parent process owns only a small, serialisable protocol.  One spawn-process
worker hosts independent per-handle Sim2Sea cores: the Taichi runtime is shared,
but a core's mutable vessel state is never shared between adapters or sessions.
This prevents process-per-entity Taichi runtime replication while preserving
process isolation from the simulation process.
"""

from __future__ import annotations

import contextlib
import io
import math
import tempfile
from collections.abc import Mapping, Sequence
from multiprocessing import get_context
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from threading import Lock
from typing import Any, cast

import numpy as np

from openmdbench.core.units import heading_deg_to_math_rad, math_rad_to_heading_deg

_RESPONSE_TIMEOUT_S = 120.0
MMG_SOLVER_IDENTITY_V2 = "sim2sea-mmg:kvlcc2-l7:rk4:worker-v2"
MMG_BATCH_MAX_SUBSTEPS_V2 = 256
_MAX_MMG_NPS = 240.0
_MAX_MMG_SPEED_MPS = 18.0


def _finite(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("MMG worker values must be finite numbers")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("MMG worker values must be finite numbers")
    return result


def _vector(value: object, *, name: str) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError(f"{name} must be a three-vector")
    return (_finite(value[0]), _finite(value[1]), _finite(value[2]))


def _substep_count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("MMG batch substeps must be an integer")
    if not 1 <= value <= MMG_BATCH_MAX_SUBSTEPS_V2:
        raise ValueError(
            f"MMG batch substeps must be within [1, {MMG_BATCH_MAX_SUBSTEPS_V2}]"
        )
    return value


class _Sim2SeaMMGWorkerEngine:
    """The child-only stateful solver adapter.

    ``Sim2Sea_Core`` derives its step size from ``control_freq`` and ``substeps``.
    We create it lazily on the first substep with ``substeps=1`` and a control
    frequency selected from the declared integration interval.  That makes one
    IPC ``step`` exactly one V2 MMG substep.
    """

    def __init__(self) -> None:
        self._dt_s: float | None = None
        self._max_speed_mps = 12.9
        self._position_m: tuple[float, float, float] | None = None
        self._heading_deg: float | None = None
        # Preserve the solver's float32 angle separately from its public
        # degree projection.  Reconstructing this value via deg->rad during
        # checkpoint restore changes the next Taichi integration result.
        self._heading_math_rad: float | None = None
        self._body_velocity_mps: tuple[float, float, float] | None = None

    def _build_core(self, *, dt_s: float) -> Any:
        import taichi as ti  # type: ignore[import-untyped]
        from config.parallel_args import NavigationEnvArgs
        from env.calibrated_vessels import kvlcc2_l7
        from env.vessel_sim import Sim2Sea_Core

        if ti.lang.impl.get_runtime().prog is None:
            ti.init(
                arch=ti.cpu,
                # The cache only contains Taichi-compiled kernels.  It is not
                # simulation state, and enables restored/checkpointed workers
                # to initialise quickly without weakening per-adapter process
                # isolation or determinism.
                offline_cache=True,
                offline_cache_file_path=str(
                    Path(tempfile.gettempdir()) / "openmdbench-taichi-mmg-worker"
                ),
            )
        arguments = NavigationEnvArgs()
        arguments.max_env = 1
        arguments.max_num = 1
        arguments.solver_type = "mmg"
        arguments.substeps = 1
        cast(Any, arguments).control_freq = 1.0 / dt_s
        arguments.use_bev = False
        arguments.use_ic = False
        arguments.randomization = False
        core: Any = Sim2Sea_Core(arguments)  # type: ignore[no-untyped-call]
        with contextlib.redirect_stdout(io.StringIO()):
            core.load_vessel_params(kvlcc2_l7)
        return core

    def _initialize_core(self, core: Any) -> None:
        if (
            self._position_m is None
            or self._heading_deg is None
            or self._heading_math_rad is None
            or self._body_velocity_mps is None
        ):
            raise ValueError("MMG worker has no state to initialize")
        pose = np.array(
            [[[self._position_m[0], self._position_m[1], self._heading_math_rad]]],
            dtype=np.float32,
        )
        velocity = np.array([[list(self._body_velocity_mps)]], dtype=np.float32)
        camps = np.zeros((1, 1), dtype=np.int32)
        widths = np.full((1, 1), 1.27, dtype=np.float32)
        angle_limits = np.full((1, 1), 0.3, dtype=np.float32)
        max_speeds = np.full((1, 1), self._max_speed_mps, dtype=np.float32)
        core.core_init(pose, velocity, camps, widths, angle_limits, max_speeds)

    def configure(self, value: Mapping[str, object]) -> None:
        if set(value) != {"max_speed_mps"}:
            raise ValueError("MMG worker configuration shape is invalid")
        maximum = _finite(value["max_speed_mps"])
        if not 0.0 < maximum <= _MAX_MMG_SPEED_MPS:
            raise ValueError("MMG worker maximum speed is outside declared solver limits")
        if self._dt_s is not None:
            raise ValueError("MMG worker configuration is immutable after stepping")
        self._max_speed_mps = maximum

    def set_state(self, value: Mapping[str, object]) -> None:
        position = _vector(value.get("position_m"), name="position_m")
        velocity = _vector(value.get("velocity_mps"), name="velocity_mps")
        heading = _finite(value.get("heading_deg")) % 360.0
        heading_math_rad = heading_deg_to_math_rad(heading)
        surge = math.cos(heading_math_rad) * velocity[0] + math.sin(heading_math_rad) * velocity[1]
        sway = -math.sin(heading_math_rad) * velocity[0] + math.cos(heading_math_rad) * velocity[1]
        self._position_m = position
        self._heading_deg = heading
        self._heading_math_rad = heading_math_rad
        self._body_velocity_mps = (surge, sway, 0.0)

    def step(
        self,
        *,
        runtime: _Sim2SeaMMGRuntime,
        nps: object,
        rudder_rad: object,
        dt_s: object,
    ) -> tuple[float, ...]:
        core, action = self._prepare_substep(
            runtime=runtime,
            nps=nps,
            rudder_rad=rudder_rad,
            dt_s=dt_s,
        )
        return self._advance_prepared_substep(core=core, action=action)

    def _prepare_substep(
        self,
        *,
        runtime: _Sim2SeaMMGRuntime,
        nps: object,
        rudder_rad: object,
        dt_s: object,
    ) -> tuple[Any, np.ndarray[Any, Any]]:
        nps_value = _finite(nps)
        rudder_value = _finite(rudder_rad)
        interval = _finite(dt_s)
        if not interval > 0.0:
            raise ValueError("MMG integration interval must be positive")
        if not 0.0 <= nps_value <= _MAX_MMG_NPS or abs(rudder_value) > 0.3:
            raise ValueError("MMG actuator command is outside trusted solver limits")
        if self._position_m is None or self._heading_deg is None or self._body_velocity_mps is None:
            raise ValueError("MMG worker must receive set_state before step")
        if self._dt_s is not None and not math.isclose(self._dt_s, interval, abs_tol=1e-12):
            raise ValueError("MMG integration interval changed during one adapter lifetime")
        self._dt_s = interval
        core = runtime.core_for(self, interval)
        self._initialize_core(core)
        action = np.array([[[nps_value, rudder_value]]], dtype=np.float32)
        return core, action

    def _advance_prepared_substep(
        self, *, core: Any, action: np.ndarray[Any, Any]
    ) -> tuple[float, ...]:
        position = self._position_m
        if position is None:
            raise ValueError("MMG worker has no position to advance")
        core.core_step(action, type="RK")
        pose = core.x.to_numpy()[0, 0]
        body_velocity = core.v.to_numpy()[0, 0]
        self._heading_math_rad = float(pose[2])
        heading = math_rad_to_heading_deg(self._heading_math_rad)
        heading_math_rad = heading_deg_to_math_rad(heading)
        surge, sway, yaw_rate = (float(item) for item in body_velocity)
        east = math.cos(heading_math_rad) * surge - math.sin(heading_math_rad) * sway
        north = math.sin(heading_math_rad) * surge + math.cos(heading_math_rad) * sway
        self._position_m = (float(pose[0]), float(pose[1]), position[2])
        self._heading_deg = heading
        self._body_velocity_mps = (surge, sway, yaw_rate)
        return (
            self._position_m[0],
            self._position_m[1],
            self._position_m[2],
            east,
            north,
            heading,
        )

    def step_many(
        self,
        *,
        runtime: _Sim2SeaMMGRuntime,
        nps: object,
        rudder_rad: object,
        dt_s: object,
        substeps: object,
    ) -> tuple[float, ...]:
        """Advance one handle through a transactional sequence of trusted substeps."""

        count = _substep_count(substeps)
        before = self.snapshot()
        values: tuple[float, ...] = ()
        try:
            core, action = self._prepare_substep(
                runtime=runtime,
                nps=nps,
                rudder_rad=rudder_rad,
                dt_s=dt_s,
            )
            for _index in range(count):
                values = self._advance_prepared_substep(core=core, action=action)
        except Exception:
            # ``step`` reconstructs the Taichi fields from this canonical engine
            # state before every integration.  Restoring it therefore prevents a
            # failed batch from becoming the continuation state of this handle.
            self.restore(before)
            raise
        return values

    def snapshot(self) -> dict[str, object]:
        state: dict[str, object] | None = None
        if self._position_m is not None:
            if (
                self._heading_deg is None
                or self._body_velocity_mps is None
                or self._heading_math_rad is None
            ):
                raise RuntimeError("MMG worker state is incomplete")
            state = {
                "position_m": list(self._position_m),
                "heading_deg": self._heading_deg,
                "heading_math_rad": self._heading_math_rad,
                "body_velocity_mps": list(self._body_velocity_mps),
            }
        return {"integration_dt_s": self._dt_s, "state": state}

    def restore(self, value: Mapping[str, object]) -> None:
        if set(value) != {"integration_dt_s", "state"}:
            raise ValueError("MMG worker snapshot shape is invalid")
        interval = value["integration_dt_s"]
        state = value["state"]
        if state is None:
            if interval is not None:
                raise ValueError("uninitialized MMG snapshot cannot have an integration interval")
            self._dt_s = None
            self._position_m = None
            self._heading_deg = None
            self._heading_math_rad = None
            self._body_velocity_mps = None
            return
        if not isinstance(state, Mapping):
            raise ValueError("MMG worker snapshot state is invalid")
        if interval is None:
            dt_s: float | None = None
        else:
            if not isinstance(interval, (int, float)) or isinstance(interval, bool):
                raise ValueError("MMG worker snapshot interval is invalid")
            dt_s = _finite(interval)
            if not dt_s > 0.0:
                raise ValueError("MMG worker snapshot interval must be positive")
        position = _vector(state.get("position_m"), name="snapshot.position_m")
        body_velocity = _vector(state.get("body_velocity_mps"), name="snapshot.body_velocity_mps")
        heading = _finite(state.get("heading_deg")) % 360.0
        raw_heading = state.get("heading_math_rad")
        heading_math_rad = (
            heading_deg_to_math_rad(heading) if raw_heading is None else _finite(raw_heading)
        )
        self._position_m = position
        self._heading_deg = heading
        self._heading_math_rad = heading_math_rad
        self._body_velocity_mps = body_velocity
        self._dt_s = dt_s

    def reset_for_reuse(self) -> None:
        """Drop all per-adapter state before assigning this handle to another adapter."""

        self._dt_s = None
        self._max_speed_mps = 12.9
        self._position_m = None
        self._heading_deg = None
        self._heading_math_rad = None
        self._body_velocity_mps = None


class _Sim2SeaMMGRuntime:
    """One Taichi field allocation, reinitialized from a handle before each step."""

    def __init__(self) -> None:
        self._core: Any | None = None
        self._dt_s: float | None = None

    def core_for(self, engine: _Sim2SeaMMGWorkerEngine, interval: float) -> Any:
        if (
            self._core is None
            or self._dt_s is None
            or not math.isclose(self._dt_s, interval, abs_tol=1e-12)
        ):
            self._core = engine._build_core(dt_s=interval)
            self._dt_s = interval
        return self._core


def _reply(connection: Connection, payload: Mapping[str, object]) -> None:
    connection.send(dict(payload))


def _worker_core_id(request: Mapping[str, object]) -> str:
    value = request.get("core_id")
    if not isinstance(value, str) or not value:
        raise ValueError("MMG worker request requires a nonempty core_id")
    return value


def _worker_engine(
    engines: Mapping[str, _Sim2SeaMMGWorkerEngine], request: Mapping[str, object]
) -> _Sim2SeaMMGWorkerEngine:
    core_id = _worker_core_id(request)
    engine = engines.get(core_id)
    if engine is None:
        raise ValueError("MMG worker core handle is unknown")
    return engine


def _worker_main(connection: Connection) -> None:
    engines: dict[str, _Sim2SeaMMGWorkerEngine] = {}
    reusable_engines: list[_Sim2SeaMMGWorkerEngine] = []
    runtime = _Sim2SeaMMGRuntime()
    next_core_index = 0
    try:
        while True:
            request = connection.recv()
            if not isinstance(request, Mapping):
                raise ValueError("MMG worker request must be a mapping")
            operation = request.get("operation")
            try:
                if operation == "ping":
                    _reply(
                        connection,
                        {"ok": True, "result": {"solver_identity": MMG_SOLVER_IDENTITY_V2}},
                    )
                elif operation == "allocate":
                    next_core_index += 1
                    core_id = f"mmg-core-{next_core_index:016d}"
                    engine = (
                        reusable_engines.pop() if reusable_engines else _Sim2SeaMMGWorkerEngine()
                    )
                    engine.reset_for_reuse()
                    engines[core_id] = engine
                    _reply(connection, {"ok": True, "result": {"core_id": core_id}})
                elif operation == "set_state":
                    state = request.get("state")
                    if not isinstance(state, Mapping):
                        raise ValueError("MMG worker set_state requires a mapping")
                    _worker_engine(engines, request).set_state(state)
                    _reply(connection, {"ok": True, "result": None})
                elif operation == "configure":
                    parameters = request.get("parameters")
                    if not isinstance(parameters, Mapping):
                        raise ValueError("MMG worker configuration requires a mapping")
                    _worker_engine(engines, request).configure(parameters)
                    _reply(connection, {"ok": True, "result": None})
                elif operation == "step":
                    result = _worker_engine(engines, request).step(
                        runtime=runtime,
                        nps=request.get("nps"),
                        rudder_rad=request.get("rudder_rad"),
                        dt_s=request.get("dt_s"),
                    )
                    _reply(connection, {"ok": True, "result": list(result)})
                elif operation == "step_many":
                    result = _worker_engine(engines, request).step_many(
                        runtime=runtime,
                        nps=request.get("nps"),
                        rudder_rad=request.get("rudder_rad"),
                        dt_s=request.get("dt_s"),
                        substeps=request.get("substeps"),
                    )
                    _reply(connection, {"ok": True, "result": list(result)})
                elif operation == "restore":
                    snapshot = request.get("snapshot")
                    if not isinstance(snapshot, Mapping):
                        raise ValueError("MMG worker restore requires a mapping")
                    _worker_engine(engines, request).restore(snapshot)
                    _reply(connection, {"ok": True, "result": None})
                elif operation == "snapshot":
                    _reply(
                        connection,
                        {"ok": True, "result": _worker_engine(engines, request).snapshot()},
                    )
                elif operation == "release":
                    core_id = _worker_core_id(request)
                    if core_id not in engines:
                        raise ValueError("MMG worker core handle is unknown")
                    engine = engines.pop(core_id)
                    engine.reset_for_reuse()
                    reusable_engines.append(engine)
                    _reply(connection, {"ok": True, "result": None})
                elif operation == "close":
                    _reply(connection, {"ok": True, "result": None})
                    return
                else:
                    raise ValueError("MMG worker operation is unsupported")
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                _reply(connection, {"ok": False, "error": f"{type(error).__name__}: {error}"})
    except EOFError:
        return
    finally:
        connection.close()


class _SharedSim2SeaMMGWorkerV2:
    """Serialize protocol traffic to one process-isolated Taichi runtime."""

    def __init__(self) -> None:
        context = get_context("spawn")
        parent, child = context.Pipe()
        self._connection = parent
        self._process: BaseProcess = context.Process(
            target=_worker_main,
            args=(child,),
            name="openmdbench-sim2sea-mmg",
            daemon=True,
        )
        self._closed = False
        self._lock = Lock()
        self._handle_count = 0
        self._process.start()
        child.close()
        try:
            result = self._rpc_unlocked({"operation": "ping"})
            if result != {"solver_identity": MMG_SOLVER_IDENTITY_V2}:
                raise RuntimeError("MMG worker identity acknowledgement is invalid")
        except Exception:
            self.close()
            raise

    @property
    def process_pid(self) -> int | None:
        return self._process.pid

    @property
    def handle_count(self) -> int:
        return self._handle_count

    def _rpc_unlocked(self, request: Mapping[str, object]) -> object:
        if self._closed:
            raise RuntimeError("MMG worker is closed")
        if not self._process.is_alive():
            raise RuntimeError("MMG worker exited unexpectedly")
        try:
            self._connection.send(dict(request))
            if not self._connection.poll(_RESPONSE_TIMEOUT_S):
                raise RuntimeError("MMG worker did not respond before the timeout")
            response = self._connection.recv()
        except (BrokenPipeError, EOFError, OSError) as error:
            raise RuntimeError("MMG worker connection failed") from error
        if not isinstance(response, Mapping) or not isinstance(response.get("ok"), bool):
            raise RuntimeError("MMG worker response is malformed")
        if response["ok"] is not True:
            raise RuntimeError(str(response.get("error", "MMG worker rejected request")))
        return response.get("result")

    def allocate(self) -> str:
        with self._lock:
            result = self._rpc_unlocked({"operation": "allocate"})
            if not isinstance(result, Mapping) or not isinstance(result.get("core_id"), str):
                raise RuntimeError("MMG worker allocation acknowledgement is invalid")
            self._handle_count += 1
            return str(result["core_id"])

    def request(self, request: Mapping[str, object]) -> object:
        with self._lock:
            return self._rpc_unlocked(request)

    def release(self, core_id: str) -> bool:
        with self._lock:
            if self._closed:
                return self._handle_count == 0
            self._rpc_unlocked({"operation": "release", "core_id": core_id})
            self._handle_count -= 1
            if self._handle_count < 0:
                raise RuntimeError("MMG worker handle count underflow")
            return self._handle_count == 0

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._process.is_alive():
                with contextlib.suppress(RuntimeError):
                    self._rpc_unlocked({"operation": "close"})
            self._closed = True
            with contextlib.suppress(OSError):
                self._connection.close()
            self._process.join(timeout=10.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=10.0)


_SHARED_WORKER_LOCK = Lock()
_SHARED_WORKER: _SharedSim2SeaMMGWorkerV2 | None = None


def _allocate_shared_handle() -> tuple[_SharedSim2SeaMMGWorkerV2, str]:
    global _SHARED_WORKER
    with _SHARED_WORKER_LOCK:
        if (
            _SHARED_WORKER is None
            or _SHARED_WORKER._closed
            or not _SHARED_WORKER._process.is_alive()
        ):
            _SHARED_WORKER = _SharedSim2SeaMMGWorkerV2()
        try:
            return _SHARED_WORKER, _SHARED_WORKER.allocate()
        except Exception:
            if _SHARED_WORKER.handle_count == 0:
                _SHARED_WORKER.close()
                _SHARED_WORKER = None
            raise


def _release_shared_handle(worker: _SharedSim2SeaMMGWorkerV2, core_id: str) -> None:
    global _SHARED_WORKER
    with _SHARED_WORKER_LOCK:
        is_idle = worker.release(core_id)
        if is_idle:
            worker.close()
            if _SHARED_WORKER is worker:
                _SHARED_WORKER = None


class SpawnedSim2SeaMMGCoreV2:
    """Per-adapter handle to a process-isolated, multiplexed MMG worker."""

    solver_identity = MMG_SOLVER_IDENTITY_V2

    def __init__(self) -> None:
        self._worker, self._core_id = _allocate_shared_handle()
        self._closed = False

    @property
    def worker_process_pid(self) -> int | None:
        """Expose worker identity for resource diagnostics, not simulation state."""

        return self._worker.process_pid

    def _rpc(self, request: Mapping[str, object]) -> object:
        if self._closed:
            raise RuntimeError("MMG worker is closed")
        payload = dict(request)
        payload["core_id"] = self._core_id
        return self._worker.request(payload)

    def set_state(self, state: Any) -> None:
        position = _vector(getattr(state, "position_m", None), name="state.position_m")
        velocity = _vector(getattr(state, "velocity_mps", None), name="state.velocity_mps")
        heading = _finite(getattr(state, "heading_deg", None)) % 360.0
        self._rpc(
            {
                "operation": "set_state",
                "state": {
                    "position_m": list(position),
                    "velocity_mps": list(velocity),
                    "heading_deg": heading,
                },
            }
        )

    def configure(self, parameters: Mapping[str, object]) -> None:
        self._rpc({"operation": "configure", "parameters": dict(parameters)})

    def step(self, *, nps: float, rudder_rad: float, dt_s: float) -> tuple[float, ...]:
        try:
            result = self._rpc(
                {
                    "operation": "step",
                    "nps": nps,
                    "rudder_rad": rudder_rad,
                    "dt_s": dt_s,
                }
            )
            if (
                not isinstance(result, Sequence)
                or isinstance(result, (str, bytes))
                or len(result) != 6
            ):
                raise ValueError("MMG worker result must contain six values")
            values = _vector(result[:3], name="result")
            tail = (_finite(result[3]), _finite(result[4]), _finite(result[5]))
            return (*values, *tail)
        except RuntimeError as error:
            raise ValueError(str(error)) from error

    def step_many(
        self, *, nps: float, rudder_rad: float, dt_s: float, substeps: int
    ) -> tuple[float, ...]:
        try:
            result = self._rpc(
                {
                    "operation": "step_many",
                    "nps": nps,
                    "rudder_rad": rudder_rad,
                    "dt_s": dt_s,
                    "substeps": substeps,
                }
            )
            if (
                not isinstance(result, Sequence)
                or isinstance(result, (str, bytes))
                or len(result) != 6
            ):
                raise ValueError("MMG worker result must contain six values")
            values = _vector(result[:3], name="result")
            tail = (_finite(result[3]), _finite(result[4]), _finite(result[5]))
            return (*values, *tail)
        except RuntimeError as error:
            raise ValueError(str(error)) from error

    def snapshot(self) -> Mapping[str, Any]:
        result = self._rpc({"operation": "snapshot"})
        if not isinstance(result, Mapping):
            raise RuntimeError("MMG worker snapshot is malformed")
        return {str(key): value for key, value in result.items()}

    def restore(self, value: dict[str, Any]) -> None:
        self._rpc({"operation": "restore", "snapshot": value})

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        _release_shared_handle(self._worker, self._core_id)


def spawn_sim2sea_mmg_core_v2() -> SpawnedSim2SeaMMGCoreV2:
    """Create one isolated native MMG handle in the shared spawn-process worker."""

    return SpawnedSim2SeaMMGCoreV2()


__all__ = [
    "MMG_BATCH_MAX_SUBSTEPS_V2",
    "MMG_SOLVER_IDENTITY_V2",
    "SpawnedSim2SeaMMGCoreV2",
    "spawn_sim2sea_mmg_core_v2",
]

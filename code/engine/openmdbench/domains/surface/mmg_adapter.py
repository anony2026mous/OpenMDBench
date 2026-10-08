"""Thin single-USV adapter around the existing Sim2Sea MMG solver."""
# mypy: disable-error-code="import-untyped,no-untyped-call"

from __future__ import annotations

import contextlib
import io
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import taichi as ti
from config.parallel_args import NavigationEnvArgs
from env.calibrated_vessels import kvlcc2_l7
from env.vessel_sim import Sim2Sea_Core

from openmdbench.core.units import heading_deg_to_math_rad, math_rad_to_heading_deg
from openmdbench.domains.surface.actions import heading_to_rudder, validate_mmg_actions


@dataclass(frozen=True, slots=True)
class MMGState:
    position_xy_m: tuple[float, float]
    heading_deg: float
    body_velocity_mps: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class MMGTrace:
    solver: str
    integrator: str
    parameter_set: str
    nps: float
    rudder_rad: float


class Sim2SeaMMGAdapter:
    """Convert benchmark targets and delegate integration to ``Sim2Sea_Core``."""

    solver_id = "sim2sea_mmg"
    parameter_set_id = "kvlcc2_l7_wiring_only"
    _shared_core: ClassVar[Any | None] = None
    _shared_program: ClassVar[Any | None] = None
    _shared_owner: ClassVar[object | None] = None

    def __init__(self, state: MMGState, *, substeps: int = 10) -> None:
        self._runtime_token = object()
        runtime = ti.lang.impl.get_runtime()
        if runtime.prog is None:
            ti.init(
                arch=ti.cpu,
                offline_cache=False,
                offline_cache_file_path=str(
                    Path(tempfile.gettempdir()) / "openmdbench-taichi-cache"
                ),
            )
        runtime = ti.lang.impl.get_runtime()
        if self._shared_core is None or self._shared_program is not runtime.prog:
            args = NavigationEnvArgs()
            args.max_env = 1
            args.max_num = 1
            args.solver_type = "mmg"
            args.substeps = substeps
            args.use_bev = False
            args.use_ic = False
            args.randomization = False
            core: Any = Sim2Sea_Core(args)
            with contextlib.redirect_stdout(io.StringIO()):
                core.load_vessel_params(kvlcc2_l7)
            type(self)._shared_core = core
            type(self)._shared_program = runtime.prog
            type(self)._shared_owner = None
        self._core: Any = self._shared_core
        self._state = state
        self.substeps = substeps
        self.last_trace: MMGTrace | None = None
        self._activate_core()

    def _activate_core(self) -> None:
        """Load this adapter only when it becomes the shared core's owner.

        ``Sim2Sea_Core`` keeps its integration state in Taichi fields.  The
        adapter's ``MMGState`` is the serializable source of truth, so a
        switch between vessels must restore that state, while uninterrupted
        steps by the same vessel can safely continue in the already-loaded
        core.
        """
        if type(self)._shared_owner is self._runtime_token:
            return
        self._initialize_core(self._state)
        type(self)._shared_owner = self._runtime_token

    def _initialize_core(self, state: MMGState) -> None:
        pose = np.array(
            [
                [
                    [
                        state.position_xy_m[0],
                        state.position_xy_m[1],
                        heading_deg_to_math_rad(state.heading_deg),
                    ]
                ]
            ],
            dtype=np.float32,
        )
        velocity = np.array([[list(state.body_velocity_mps)]], dtype=np.float32)
        self._core.core_init(
            pose,
            velocity,
            np.zeros((1, 1), dtype=np.int32),
            np.full((1, 1), float(kvlcc2_l7["B"]), dtype=np.float32),
            np.full((1, 1), 0.3, dtype=np.float32),
            np.full((1, 1), 12.9, dtype=np.float32),
        )

    def step_target(self, *, target_speed_mps: float, target_heading_deg: float) -> MMGState:
        """Map speed/heading targets to nps/rudder, then call Sim2Sea RK4."""
        if not 0.0 <= target_speed_mps <= 12.9:
            raise ValueError("target_speed_mps must be within [0, 12.9]")
        self._activate_core()
        current_math_rad = heading_deg_to_math_rad(self._state.heading_deg)
        nps = 5.0 * target_speed_mps / 12.9
        rudder = heading_to_rudder(target_heading_deg, current_math_rad)
        action = validate_mmg_actions(np.array([[[nps, rudder]]], dtype=np.float64)).astype(
            np.float32
        )
        self._core.core_step(action, type="RK")
        pose = self._core.x.to_numpy()[0, 0]
        velocity = self._core.v.to_numpy()[0, 0]
        self.last_trace = MMGTrace(
            solver=self.solver_id,
            integrator="sim2sea_rk4",
            parameter_set=self.parameter_set_id,
            nps=nps,
            rudder_rad=rudder,
        )
        result = MMGState(
            position_xy_m=(float(pose[0]), float(pose[1])),
            heading_deg=math_rad_to_heading_deg(float(pose[2])),
            body_velocity_mps=(
                float(velocity[0]),
                float(velocity[1]),
                float(velocity[2]),
            ),
        )
        self._state = result
        return result

    def snapshot(self) -> dict[str, Any]:
        """Serialize the per-vessel continuation state without shared Taichi state."""
        return {
            "position_xy_m": list(self._state.position_xy_m),
            "heading_deg": self._state.heading_deg,
            "body_velocity_mps": list(self._state.body_velocity_mps),
            "substeps": self.substeps,
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> Sim2SeaMMGAdapter:
        position = tuple(float(value) for value in snapshot["position_xy_m"])
        velocity = tuple(float(value) for value in snapshot["body_velocity_mps"])
        if len(position) != 2 or len(velocity) != 3:
            raise ValueError("invalid MMG adapter snapshot dimensions")
        return cls(
            MMGState(
                position_xy_m=(position[0], position[1]),
                heading_deg=float(snapshot["heading_deg"]),
                body_velocity_mps=(velocity[0], velocity[1], velocity[2]),
            ),
            substeps=int(snapshot["substeps"]),
        )

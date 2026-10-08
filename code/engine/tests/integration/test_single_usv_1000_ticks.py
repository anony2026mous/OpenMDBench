"""CPU smoke test for the Phase-0 batched single-USV dynamics shape."""

import importlib
from pathlib import Path
from typing import Any, cast

import numpy as np
from config.parallel_args import NavigationEnvArgs
from env.vessel_sim import Sim2Sea_Core

ti = cast(Any, importlib.import_module("taichi"))
Sim2SeaCore = cast(Any, Sim2Sea_Core)


def test_two_batches_one_usv_each_run_for_1000_ticks(tmp_path: Path) -> None:
    ti.reset()
    ti.init(arch=ti.cpu, offline_cache=False, offline_cache_file_path=str(tmp_path))

    args = NavigationEnvArgs()
    args.max_env = 2
    args.solver_type = "kinematic"
    args.substeps = 1
    args.use_bev = False
    args.use_ic = False
    core = Sim2SeaCore(args)

    poses = np.zeros((2, 1, 3), dtype=np.float32)
    velocities = np.zeros((2, 1, 3), dtype=np.float32)
    camps = np.zeros((2, 1), dtype=np.int32)
    widths = np.full((2, 1), 10.0, dtype=np.float32)
    angle_limits = np.full((2, 1), 0.5, dtype=np.float32)
    max_speeds = np.full((2, 1), 12.9, dtype=np.float32)
    core.core_init(poses, velocities, camps, widths, angle_limits, max_speeds)

    actions = np.array([[[7.7, 0.0]], [[7.7, 90.0]]], dtype=np.float32)
    for _ in range(1000):
        core.core_step(actions)

    positions = core.x.to_numpy()
    velocities_out = core.v.to_numpy()
    assert positions.shape == (2, 1, 2)
    assert velocities_out.shape == (2, 1, 2)
    assert np.isfinite(positions).all()
    assert np.isfinite(velocities_out).all()
    assert np.count_nonzero(core.active.to_numpy()) == 2

    ti.reset()

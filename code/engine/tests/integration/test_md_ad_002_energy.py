"""MD-AD-002 uses its task-specific endurance calibration."""

import numpy as np
import pytest
from openmdbench.core.entities import PlatformAsset
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.systems.energy import AD2_ENERGY_PROFILES, consume_energy


def test_ad2_world_step_uses_ad2_uav_energy_profile() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=23)
    env.reset(seed=23)
    assert env.world is not None

    env.step(np.array([25.0, 90.0], dtype=np.float32))

    primary = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(primary, PlatformAsset)
    expected = consume_energy(
        "uav",
        1.0,
        25.0,
        sensor_active=True,
        profile=AD2_ENERGY_PROFILES["uav"],
    )
    assert primary.components.energy == pytest.approx(expected.energy)

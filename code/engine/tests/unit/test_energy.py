"""Endurance calibration, depletion, and replenishment tests."""

import pytest
from openmdbench.systems.energy import (
    AD2_ENERGY_PROFILES,
    ENERGY_PROFILES,
    consume_energy,
    replenish_energy,
)


@pytest.mark.parametrize("platform_type", ["uav", "usv", "auv"])
def test_cruise_and_full_endurance_match_profile_within_two_percent(
    platform_type: str,
) -> None:
    profile = ENERGY_PROFILES[platform_type]  # type: ignore[index]
    cruise_duration = 1.0 / profile.propulsion_rate(profile.cruise_speed_mps)
    full_duration = 1.0 / profile.propulsion_rate(profile.full_speed_mps)
    assert cruise_duration == pytest.approx(profile.cruise_endurance_seconds, rel=0.02)
    assert full_duration == pytest.approx(profile.full_endurance_seconds, rel=0.02)


@pytest.mark.parametrize(
    ("platform_type", "expected_status"),
    [("uav", "crashed"), ("usv", "drifting"), ("auv", "drifting")],
)
def test_energy_depletion_applies_platform_behavior(
    platform_type: str, expected_status: str
) -> None:
    profile = ENERGY_PROFILES[platform_type]  # type: ignore[index]
    result = consume_energy(
        platform_type,  # type: ignore[arg-type]
        0.000001,
        profile.full_speed_mps,
        tick_seconds=1000.0,
    )
    assert result.energy == 0.0
    assert result.operational_status == expected_status


def test_additional_modes_consume_more_and_base_replenishes() -> None:
    baseline = consume_energy("uav", 1.0, 40.0)
    loaded = consume_energy("uav", 1.0, 40.0, sensor_active=True, relaying=True, engagements=1)
    assert loaded.energy < baseline.energy
    assert replenish_energy(0.5, in_base=False, tick_seconds=10.0, rate_per_second=0.01) == 0.5
    assert replenish_energy(0.5, in_base=True, tick_seconds=10.0, rate_per_second=0.01) == 0.6


def test_ad2_profiles_match_task_specific_endurance_points() -> None:
    uav = AD2_ENERGY_PROFILES["uav"]
    usv = AD2_ENERGY_PROFILES["usv"]

    assert (uav.cruise_speed_mps, uav.full_speed_mps) == (25.0, 60.0)
    assert 1.0 / uav.propulsion_rate(25.0) == pytest.approx(40 * 60)
    assert 1.0 / uav.propulsion_rate(60.0) == pytest.approx(15 * 60)
    assert (usv.cruise_speed_mps, usv.full_speed_mps) == (6.0, 12.0)
    assert 1.0 / usv.propulsion_rate(6.0) == pytest.approx(8 * 60 * 60)
    assert 1.0 / usv.propulsion_rate(12.0) == pytest.approx(3 * 60 * 60)

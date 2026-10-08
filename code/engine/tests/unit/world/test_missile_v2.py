"""Guided-missile deterministic movement and seeker contracts."""

from __future__ import annotations

import pytest
from openmdbench.world.missile_v2 import (
    GuidedMissileProfileV2,
    MissileFlightV2,
    advance_guided_missile_v2,
)


def _profile(**changes: object) -> GuidedMissileProfileV2:
    values: dict[str, object] = {
        "launch_speed_mps": 20.0,
        "cruise_speed_mps": 100.0,
        "max_acceleration_mps2": 20.0,
        "max_turn_rate_deg_s": 45.0,
        "max_vertical_speed_mps": 20.0,
        "seeker_range_m": 2_000.0,
        "seeker_fov_deg": 360.0,
        "seeker_detection_probability": 1.0,
        "fuse_radius_m": 1.0,
        "max_flight_ticks": 10,
    }
    values.update(changes)
    return GuidedMissileProfileV2.model_validate(values)


def _flight(*, profile: GuidedMissileProfileV2, heading_deg: float = 0.0) -> MissileFlightV2:
    return MissileFlightV2(
        missile_id="missile.test.001",
        request_id="request.test.001",
        launcher_id="launcher.test",
        faction_id="faction.test",
        target_id="target.test",
        weapon_ref="weapon.test@2.0.0",
        ammunition_ref="ammunition.test@2.0.0",
        effect_ref="effect.test@2.0.0",
        damage_model_ref="damage.test@2.0.0",
        magnitude=1.0,
        hit_probability=1.0,
        launch_tick=0,
        flight_ticks=0,
        position_m=(0.0, 0.0, 100.0),
        velocity_mps=(0.0, profile.launch_speed_mps, 0.0),
        heading_deg=heading_deg,
        last_known_target_position_m=(1_000.0, 0.0, 100.0),
        profile=profile,
    )


def test_guided_missile_uses_bounded_aircraft_style_turn_acceleration_and_seeker() -> None:
    advance = advance_guided_missile_v2(
        _flight(profile=_profile()),
        target_start_position_m=(1_000.0, 0.0, 100.0),
        target_end_position_m=(1_000.0, 0.0, 100.0),
        tick=0,
        dt_seconds=1.0,
    )

    assert advance.status == "active"
    assert advance.flight is not None
    assert advance.flight.heading_deg == pytest.approx(45.0)
    assert advance.flight.speed_mps == pytest.approx(40.0)
    assert advance.flight.position_m != (0.0, 0.0, 100.0)
    assert advance.flight.seeker_state == "tracking"
    assert advance.flight.last_detection_tick == 0


def test_guided_missile_uses_continuous_closest_approach_for_high_speed_fuse() -> None:
    profile = _profile(
        launch_speed_mps=50.0,
        cruise_speed_mps=60.0,
        max_acceleration_mps2=10.0,
        max_turn_rate_deg_s=180.0,
    )
    advance = advance_guided_missile_v2(
        _flight(profile=profile, heading_deg=90.0),
        target_start_position_m=(25.0, 0.0, 100.0),
        target_end_position_m=(25.0, 0.0, 100.0),
        tick=0,
        dt_seconds=1.0,
    )

    assert advance.status == "fuse_candidate"
    assert advance.closest_approach_m == pytest.approx(0.0)
    assert advance.position_m == pytest.approx((25.0, 0.0, 100.0))
    assert advance.target_position_m == pytest.approx((25.0, 0.0, 100.0))
    assert advance.missile_velocity_mps is not None
    assert advance.closest_approach_time_fraction == pytest.approx(25.0 / 60.0)

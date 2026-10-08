"""Normalized energy consumption calibrated to platform endurance points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlatformType = Literal["uav", "usv", "auv", "shore_radar"]


@dataclass(frozen=True, slots=True)
class EnergyProfile:
    cruise_speed_mps: float
    full_speed_mps: float
    cruise_endurance_seconds: float
    full_endurance_seconds: float
    sensor_rate_per_second: float = 0.0
    relay_rate_per_second: float = 0.0
    engagement_cost: float = 0.0

    def propulsion_rate(self, speed_mps: float) -> float:
        if not 0.0 <= speed_mps <= self.full_speed_mps:
            raise ValueError("speed is outside the energy profile range")
        cruise_rate = 1.0 / self.cruise_endurance_seconds
        full_rate = 1.0 / self.full_endurance_seconds
        if speed_mps <= self.cruise_speed_mps:
            return cruise_rate * (0.25 + 0.75 * speed_mps / self.cruise_speed_mps)
        fraction = (speed_mps - self.cruise_speed_mps) / (
            self.full_speed_mps - self.cruise_speed_mps
        )
        return cruise_rate + fraction * (full_rate - cruise_rate)


ENERGY_PROFILES: dict[PlatformType, EnergyProfile] = {
    "uav": EnergyProfile(40.0, 80.0, 60 * 60, 30 * 60, 1e-6, 2e-6, 2e-4),
    "usv": EnergyProfile(7.7, 12.9, 24 * 60 * 60, 8 * 60 * 60, 2e-7, 5e-7, 5e-5),
    "auv": EnergyProfile(2.1, 4.1, 12 * 60 * 60, 4 * 60 * 60, 1e-7, 3e-7, 1e-4),
    "shore_radar": EnergyProfile(1.0, 1.0, 10**12, 10**12),
}

AD2_ENERGY_PROFILES: dict[PlatformType, EnergyProfile] = {
    **ENERGY_PROFILES,
    "uav": EnergyProfile(25.0, 60.0, 40 * 60, 15 * 60, 1e-6, 2e-6, 2e-4),
    "usv": EnergyProfile(6.0, 12.0, 8 * 60 * 60, 3 * 60 * 60, 2e-7, 5e-7, 5e-5),
}


@dataclass(frozen=True, slots=True)
class EnergyResult:
    energy: float
    operational_status: Literal["active", "crashed", "drifting", "offline"]


def consume_energy(
    platform_type: PlatformType,
    energy: float,
    speed_mps: float,
    *,
    tick_seconds: float = 1.0,
    sensor_active: bool = False,
    relaying: bool = False,
    engagements: int = 0,
    profile: EnergyProfile | None = None,
) -> EnergyResult:
    if not 0.0 <= energy <= 1.0 or tick_seconds <= 0.0 or engagements < 0:
        raise ValueError("invalid energy-system input")
    profile = profile or ENERGY_PROFILES[platform_type]
    rate = profile.propulsion_rate(speed_mps)
    rate += profile.sensor_rate_per_second if sensor_active else 0.0
    rate += profile.relay_rate_per_second if relaying else 0.0
    used = rate * tick_seconds + engagements * profile.engagement_cost
    remaining = max(0.0, energy - used)
    if remaining > 0.0:
        return EnergyResult(remaining, "active")
    status_by_type = {
        "auv": "drifting",
        "shore_radar": "offline",
        "uav": "crashed",
        "usv": "drifting",
    }
    return EnergyResult(0.0, status_by_type[platform_type])  # type: ignore[arg-type]


def replenish_energy(
    energy: float, *, in_base: bool, tick_seconds: float, rate_per_second: float
) -> float:
    if not 0.0 <= energy <= 1.0 or tick_seconds < 0.0 or rate_per_second < 0.0:
        raise ValueError("invalid replenishment input")
    if not in_base:
        return energy
    return min(1.0, energy + tick_seconds * rate_per_second)

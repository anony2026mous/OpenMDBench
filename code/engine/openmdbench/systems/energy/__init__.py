"""Platform energy and replenishment system."""

from openmdbench.systems.energy.model import (
    AD2_ENERGY_PROFILES,
    ENERGY_PROFILES,
    EnergyProfile,
    EnergyResult,
    consume_energy,
    replenish_energy,
)

__all__ = [
    "AD2_ENERGY_PROFILES",
    "ENERGY_PROFILES",
    "EnergyProfile",
    "EnergyResult",
    "consume_energy",
    "replenish_energy",
]

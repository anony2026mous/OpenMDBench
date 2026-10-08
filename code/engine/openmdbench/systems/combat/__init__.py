"""Abstract deterministic benchmark combat system."""

from openmdbench.systems.combat.damage import (
    DamageEvent,
    DamageIntent,
    apply_simultaneous_damage,
    lifecycle_for_health,
)
from openmdbench.systems.combat.model import (
    WEAPONS,
    Combatant,
    CombatResult,
    LegalityResult,
    RejectionCode,
    ShotResult,
    WeaponSpec,
    engage,
    validate_engagement,
)

__all__ = [
    "WEAPONS",
    "CombatResult",
    "Combatant",
    "DamageEvent",
    "DamageIntent",
    "LegalityResult",
    "RejectionCode",
    "ShotResult",
    "WeaponSpec",
    "apply_simultaneous_damage",
    "engage",
    "validate_engagement",
    "lifecycle_for_health",
]

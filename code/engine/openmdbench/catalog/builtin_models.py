"""Reviewed built-in model factories available to declarative catalog data."""

from __future__ import annotations

from dataclasses import dataclass

from openmdbench.catalog.models import EffectDefinition, ResourceDefinition, WeaponDefinition
from openmdbench.catalog.repository import ModelRegistry


@dataclass(frozen=True, slots=True)
class FractionalDamageModel:
    definition: EffectDefinition


@dataclass(frozen=True, slots=True)
class ProbabilityInstantWeaponModel:
    definition: WeaponDefinition


def _effect(definition: ResourceDefinition) -> FractionalDamageModel:
    if not isinstance(definition, EffectDefinition):
        raise TypeError("fractional damage factory requires EffectDefinition")
    return FractionalDamageModel(definition.model_copy(deep=True))


def _weapon(definition: ResourceDefinition) -> ProbabilityInstantWeaponModel:
    if not isinstance(definition, WeaponDefinition):
        raise TypeError("probability weapon factory requires WeaponDefinition")
    return ProbabilityInstantWeaponModel(definition.model_copy(deep=True))


def builtin_model_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register("effects", "fractional_damage_v1", _effect)
    registry.register("weapons", "probability_instant_v1", _weapon)
    registry.freeze()
    return registry


__all__ = [
    "FractionalDamageModel",
    "ProbabilityInstantWeaponModel",
    "builtin_model_registry",
]

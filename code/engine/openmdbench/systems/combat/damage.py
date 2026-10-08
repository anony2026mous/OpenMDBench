"""Order-independent normalized-health damage application."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from openmdbench.core.entities import Lifecycle, PlatformAsset


@dataclass(frozen=True, slots=True)
class DamageIntent:
    attacker_id: str
    target_id: str
    damage: float


@dataclass(frozen=True, slots=True)
class DamageEvent:
    target_id: str
    health_before: float
    health_after: float
    status_after: Lifecycle
    total_damage: float


def lifecycle_for_health(health: float) -> Lifecycle:
    if health <= 0.0:
        return Lifecycle.DESTROYED
    if health <= 0.5:
        return Lifecycle.DEGRADED
    return Lifecycle.ACTIVE


def apply_simultaneous_damage(
    entities: tuple[PlatformAsset, ...], intents: tuple[DamageIntent, ...]
) -> tuple[tuple[PlatformAsset, ...], tuple[DamageEvent, ...]]:
    damage_by_target: dict[str, float] = defaultdict(float)
    for intent in intents:
        if intent.damage < 0.0:
            raise ValueError("damage cannot be negative")
        damage_by_target[intent.target_id] += intent.damage
    updated: list[PlatformAsset] = []
    events: list[DamageEvent] = []
    for entity in sorted(entities, key=lambda item: item.id):
        total_damage = damage_by_target.get(entity.id, 0.0)
        if total_damage == 0.0:
            updated.append(entity)
            continue
        health_before = entity.components.health
        health_after = max(0.0, health_before - total_damage)
        lifecycle = lifecycle_for_health(health_after)
        updated.append(
            entity.model_copy(
                update={
                    "components": entity.components.model_copy(update={"health": health_after}),
                    "lifecycle": lifecycle,
                }
            )
        )
        events.append(
            DamageEvent(
                entity.id,
                health_before,
                health_after,
                lifecycle,
                total_damage,
            )
        )
    return tuple(updated), tuple(events)

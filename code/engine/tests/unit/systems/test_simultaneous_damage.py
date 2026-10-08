"""Damage is accumulated per target and applied independent of attacker order."""

from openmdbench.core.entities import ComponentState, Domain, Lifecycle, PlatformAsset, Side
from openmdbench.systems.combat import DamageIntent, apply_simultaneous_damage


def _entity(entity_id: str, side: Side) -> PlatformAsset:
    return PlatformAsset(
        id=entity_id,
        side=side,
        domain=Domain.AIR,
        platform_type="uav",
        position=(0.0, 0.0, 1_000.0),
        components=ComponentState(health=1.0),
    )


def test_multiple_attackers_accumulate_damage_independent_of_order() -> None:
    entities = (_entity("blue", Side.BLUE), _entity("red", Side.RED))
    intents = (
        DamageIntent("blue-1", "red", 0.3),
        DamageIntent("blue-2", "red", 0.3),
    )
    forward = apply_simultaneous_damage(entities, intents)
    reverse = apply_simultaneous_damage(tuple(reversed(entities)), tuple(reversed(intents)))
    assert forward == reverse
    red = next(entity for entity in forward[0] if entity.id == "red")
    assert red.components.health == 0.4
    assert red.lifecycle is Lifecycle.DEGRADED


def test_mutual_fire_applies_even_when_both_destroyed_this_tick() -> None:
    entities = (_entity("blue", Side.BLUE), _entity("red", Side.RED))
    updated, events = apply_simultaneous_damage(
        entities,
        (DamageIntent("blue", "red", 1.0), DamageIntent("red", "blue", 1.0)),
    )
    assert all(entity.lifecycle is Lifecycle.DESTROYED for entity in updated)
    assert {event.target_id for event in events} == {"blue", "red"}

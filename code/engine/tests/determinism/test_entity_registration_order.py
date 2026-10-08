"""Entity indexing and traversal cannot depend on registration order."""

from openmdbench.core.entities import Domain, PlatformAsset, Side
from openmdbench.core.world import WorldState


def test_indexes_are_stably_sorted_for_reverse_registration() -> None:
    entities = [
        PlatformAsset(
            id="z",
            side=Side.RED,
            domain=Domain.AIR,
            platform_type="uav",
            position=(0, 0, 1),
        ),
        PlatformAsset(
            id="a",
            side=Side.BLUE,
            domain=Domain.SURFACE,
            platform_type="usv",
            position=(0, 0, 0),
        ),
    ]
    first = WorldState("first")
    second = WorldState("second")
    for entity in entities:
        first.registry.register(entity)
    for entity in reversed(entities):
        second.registry.register(entity)
    assert [item.id for item in first.entities_stable()] == ["a", "z"]
    assert [item.id for item in second.entities_stable()] == ["a", "z"]

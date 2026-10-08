"""View filtering and input immutability for the live frame adapter."""

import copy

from openmdbench.core.entities import (
    Domain,
    DynamicObstacle,
    PlatformAsset,
    Side,
)
from openmdbench.core.world import ContactTrack, WorldState
from openmdbench.visualization import frame_from_world


def _world() -> WorldState:
    world = WorldState(session_id="session", tick=9)
    world.registry.register(
        PlatformAsset(
            id="blue-usv",
            side=Side.BLUE,
            domain=Domain.SURFACE,
            platform_type="usv",
            position=(0.0, 0.0, 0.0),
        )
    )
    world.registry.register(
        PlatformAsset(
            id="red-uav",
            side=Side.RED,
            domain=Domain.AIR,
            platform_type="uav",
            position=(100.0, 100.0, 100.0),
        )
    )
    world.registry.register(
        DynamicObstacle(
            id="neutral-ship",
            side=Side.NEUTRAL,
            domain=Domain.SURFACE,
            obstacle_type="civilian",
            position=(50.0, 50.0, 0.0),
        )
    )
    world.contacts[Side.BLUE] = [
        ContactTrack(
            contact_id="contact-red",
            owner_side=Side.BLUE,
            estimated_domain=Domain.AIR,
            position=(90.0, 80.0, 100.0),
            velocity=(1.0, 0.0, 0.0),
            uncertainty_m=20.0,
            confidence=0.7,
            first_detected_tick=4,
            detected_by=("blue-usv",),
        )
    ]
    return world


def test_side_and_public_views_do_not_leak_ground_truth() -> None:
    world = _world()
    referee = frame_from_world(world, view="referee")
    blue = frame_from_world(world, view="blue")
    red = frame_from_world(world, view="red")
    public = frame_from_world(world, view="public")
    assert {entity.id for entity in referee.entities} == {
        "blue-usv",
        "red-uav",
        "neutral-ship",
    }
    assert {entity.id for entity in blue.entities} == {"blue-usv", "neutral-ship"}
    assert {entity.id for entity in red.entities} == {"red-uav", "neutral-ship"}
    assert {entity.id for entity in public.entities} == {"neutral-ship"}
    assert [contact.id for contact in blue.detections.blue] == ["contact-red"]
    assert red.detections.blue == () and public.detections.blue == ()


def test_adapter_does_not_modify_or_alias_world_state() -> None:
    world = _world()
    entities_before = [entity.model_dump() for entity in world.registry.all_entities()]
    contacts_before = copy.deepcopy(world.contacts)
    frame = frame_from_world(world, view="referee")
    assert [entity.model_dump() for entity in world.registry.all_entities()] == entities_before
    assert world.contacts == contacts_before
    world.contacts[Side.BLUE].clear()
    assert [contact.id for contact in frame.detections.blue] == ["contact-red"]
    assert frame.entities[0].id == "blue-usv"

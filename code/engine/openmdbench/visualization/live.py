"""One-way, view-safe adapter from mutable WorldState to visualization frames."""

from __future__ import annotations

from typing import Literal

from openmdbench.core.entities import (
    DynamicObstacle,
    MissionObject,
    PlatformAsset,
    Side,
    StaticFeature,
    WorldEntity,
)
from openmdbench.core.geography import GeoFrame
from openmdbench.core.world import ContactTrack, WorldState
from openmdbench.visualization.schema import (
    DetectionSets,
    EnvironmentPanel,
    MissionPanel,
    ScoreSets,
    SideScore,
    VisualizationDetection,
    VisualizationEntity,
    VisualizationEvent,
    VisualizationFrame,
)

VisualizationView = Literal["referee", "blue", "red", "public"]


def _profile_and_type(entity: WorldEntity) -> tuple[str, str]:
    if isinstance(entity, PlatformAsset):
        return f"{entity.platform_type}_generic", entity.platform_type
    if isinstance(entity, DynamicObstacle):
        return "civilian_vessel", entity.obstacle_type
    if isinstance(entity, StaticFeature):
        profile = "shore_radar_generic" if entity.domain.value == "shore" else "civilian_vessel"
        return profile, entity.feature_type
    if isinstance(entity, MissionObject):
        return "civilian_vessel", entity.mission_role
    raise TypeError(f"unsupported visualization entity: {type(entity).__name__}")


def _entity(entity: WorldEntity, geo_frame: GeoFrame | None = None) -> VisualizationEntity:
    profile, entity_type = _profile_and_type(entity)
    components = entity.components if isinstance(entity, PlatformAsset) else None
    visual = VisualizationEntity(
        id=entity.id,
        side=entity.side,
        type=entity_type,
        domain=entity.domain,
        position=entity.position,
        velocity=entity.velocity,
        heading=entity.heading_deg,
        health=components.health if components else 1.0,
        energy=components.energy if components else 1.0,
        sensor_mode=components.sensor_mode if components else "none",
        comm_status=components.communication_status if components else "none",
        status=entity.lifecycle,
        visual_profile=profile,
        weapon_inventory=dict(components.weapon_inventory) if components else {},
    )
    if geo_frame is None:
        return visual
    lon, lat = geo_frame.local_to_wgs84(*entity.position[:2])
    return visual.model_copy(update={"position_wgs84": (lon, lat, entity.position[2])})


def _detection(track: ContactTrack) -> VisualizationDetection:
    return VisualizationDetection(
        id=track.contact_id,
        estimated_domain=track.estimated_domain,
        position=track.position,
        position_uncertainty=track.uncertainty_m,
        confidence=track.confidence,
    )


def _visible_entities(
    world: WorldState, view: VisualizationView, geo_frame: GeoFrame | None = None
) -> tuple[VisualizationEntity, ...]:
    entities = world.registry.all_entities()
    if view == "referee":
        visible = entities
    elif view == "blue":
        visible = tuple(entity for entity in entities if entity.side in {Side.BLUE, Side.NEUTRAL})
    elif view == "red":
        visible = tuple(entity for entity in entities if entity.side in {Side.RED, Side.NEUTRAL})
    else:
        visible = tuple(entity for entity in entities if entity.side is Side.NEUTRAL)
    return tuple(_entity(entity, geo_frame) for entity in visible)


def _visible_detections(world: WorldState, view: VisualizationView) -> DetectionSets:
    blue = tuple(_detection(track) for track in world.contacts.get(Side.BLUE, ()))
    red = tuple(_detection(track) for track in world.contacts.get(Side.RED, ()))
    if view == "blue":
        red = ()
    elif view == "red":
        blue = ()
    elif view == "public":
        blue = red = ()
    return DetectionSets(blue=blue, red=red)


def frame_from_world(
    world: WorldState,
    *,
    view: VisualizationView,
    actions: tuple[dict[str, object], ...] = (),
    events: tuple[VisualizationEvent, ...] = (),
    scores: ScoreSets | None = None,
    geo_frame: GeoFrame | None = None,
) -> VisualizationFrame:
    """Copy an authorized projection without retaining or changing WorldState references."""
    if scores is None:
        scores = ScoreSets(blue=SideScore(total=0.0), red=SideScore(total=0.0))
    return VisualizationFrame(
        timestamp=world.tick,
        actions=actions,
        entities=_visible_entities(world, view, geo_frame),
        detections=_visible_detections(world, view),
        events=events,
        scores=scores,
        environment=EnvironmentPanel(weather=world.weather, sea_state=world.sea_state),
        mission=MissionPanel(
            status=world.mission_status,
            objective=world.mission_briefing,
            time_remaining=world.time_remaining,
        ),
    )

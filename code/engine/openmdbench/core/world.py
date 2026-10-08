"""Internal world state and its one-way public observation adapter."""

from __future__ import annotations

from dataclasses import dataclass, field

from openmdbench.core.entities import (
    Domain,
    Entity,
    EntityRegistry,
    Lifecycle,
    PlatformAsset,
    Side,
)
from openmdbench.schemas.observation import (
    DetectedContact,
    EnvironmentObservation,
    FriendlyAsset,
    Observation,
    SituationalData,
)


@dataclass(frozen=True, slots=True)
class ContactTrack:
    contact_id: str
    owner_side: Side
    estimated_domain: Domain
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    uncertainty_m: float
    confidence: float
    first_detected_tick: int
    detected_by: tuple[str, ...]
    inferred_type: str = "unknown"
    message_sent_tick: int | None = None
    message_source: str | None = None
    last_update_tick: int | None = None


@dataclass(slots=True)
class WorldState:
    session_id: str
    registry: EntityRegistry = field(default_factory=EntityRegistry)
    contacts: dict[Side, list[ContactTrack]] = field(default_factory=dict)
    tick: int = 0
    mission_briefing: str = ""
    mission_status: str = "in_progress"
    time_remaining: int = 0
    weather: str = "clear"
    sea_state: int = 2
    referee_intent: dict[str, str] = field(default_factory=dict)
    future_events: list[dict[str, str]] = field(default_factory=list)

    def entities_stable(self) -> tuple[Entity, ...]:
        """Return every entity in the canonical per-tick traversal order."""
        return tuple(sorted(self.registry.all_entities(), key=lambda entity: entity.id))

    def entities_for_side(self, side: Side | str) -> tuple[Entity, ...]:
        selected = Side(side)
        return tuple(entity for entity in self.entities_stable() if entity.side is selected)

    def entities_for_type(self, platform_type: str) -> tuple[PlatformAsset, ...]:
        return tuple(
            entity
            for entity in self.entities_stable()
            if isinstance(entity, PlatformAsset) and entity.platform_type == platform_type
        )


def _friendly_asset(entity: PlatformAsset) -> FriendlyAsset:
    components = entity.components
    return FriendlyAsset(
        id=entity.id,
        type=entity.platform_type,
        domain=entity.domain,
        position=entity.position,
        velocity=entity.velocity,
        heading=entity.heading_deg,
        health=components.health,
        energy=components.energy,
        sensor_mode=components.sensor_mode,
        weapon_count=sum(components.weapon_inventory.values()),
        comm_status=components.communication_status,
    )


def observation_for_side(world: WorldState, side: Side) -> Observation:
    """Copy only explicitly allowed state into an immutable side observation."""
    friendly = tuple(
        _friendly_asset(entity)
        for entity in world.entities_stable()
        if isinstance(entity, PlatformAsset)
        and entity.side is side
        and entity.lifecycle in {Lifecycle.ACTIVE, Lifecycle.DEGRADED, Lifecycle.BREACHED_ACTIVE}
    )
    contacts = tuple(
        DetectedContact(
            id=track.contact_id,
            type=track.inferred_type,
            estimated_domain=track.estimated_domain,
            position=track.position,
            position_uncertainty=track.uncertainty_m,
            velocity=track.velocity,
            confidence=track.confidence,
            first_detected_time=track.first_detected_tick,
            detected_by=track.detected_by,
            message_sent_time=track.message_sent_tick,
            message_source=track.message_source,
            last_update_time=track.last_update_tick,
            age=(
                max(0, world.tick - track.last_update_tick)
                if track.last_update_tick is not None
                else 0
            ),
        )
        for track in sorted(world.contacts.get(side, []), key=lambda item: item.contact_id)
    )
    environment = EnvironmentObservation(
        weather=world.weather,
        weather_trend="stable",
        sea_state=world.sea_state,
        visibility_km=20.0,
        wind_speed=0.0,
        wind_direction=0.0,
    )
    return Observation(
        session_id=world.session_id,
        timestamp=world.tick,
        mission_briefing=world.mission_briefing,
        situational_data=SituationalData(
            friendly_assets=friendly,
            detected_contacts=contacts,
            environment=environment,
        ),
        time_remaining=world.time_remaining,
        mission_status=world.mission_status,
    )

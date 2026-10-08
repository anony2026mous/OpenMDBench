"""Configuration-driven rich frames and Matplotlib display for formal V2 scenarios."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast

from openmdbench.catalog.v2 import CatalogV2
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.visualization.lifecycle_v2 import is_displayable_lifecycle_v2
from openmdbench.visualization.renderer_v2 import MatplotlibRendererV2
from openmdbench.world.checkpoint_v2 import WorldCheckpointV2
from openmdbench.world.factory_v2 import WorldPresentationSnapshotV2
from openmdbench.world.geography_v2 import GeographyServiceV2

ViewV2 = Literal["referee", "faction", "public"]
_ROOT = Path(__file__).resolve().parents[2]
_MapLayersV2 = tuple[
    Mapping[str, Any],
    tuple[tuple[tuple[float, float], ...], ...],
    tuple[tuple[tuple[float, float], ...], ...],
]
_MAP_LAYER_CACHE: dict[tuple[str, str, str], _MapLayersV2] = {}
_TASK_VIEWPORT_MINIMUM_SPAN_M = 1_000.0
_TASK_VIEWPORT_MARGIN_FRACTION = 0.10
_TASK_VIEWPORT_MINIMUM_MARGIN_M = 250.0


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dataclass_fields__"):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _event_state_for_view(event_state: Mapping[str, Any], *, view: ViewV2) -> Mapping[str, Any]:
    """Expose only declared global state outside the referee authority view.

    Event dispatcher internals contain unresolved trigger configuration,
    transport payloads and component-fault targets.  They are valid recovery
    evidence, but are not a faction/public visualization contract.
    """

    if view == "referee":
        return cast(Mapping[str, Any], _plain(event_state))
    return {
        "weather_state": _plain(event_state.get("weather_state", {})),
        "zone_activation_state": _plain(event_state.get("zone_activation_state", {})),
    }


def _map_layers(session: SessionLifecycleV2, catalog: CatalogV2) -> _MapLayersV2:
    map_ref = session.resolved.world.map_ref
    if map_ref is None:
        return {}, (), ()
    resource = catalog.resolve("maps", map_ref)
    source = resource.content.get("visualization_source")
    if not isinstance(source, Mapping):
        return {"exact_ref": map_ref, "content_hash": resource.content_hash}, (), ()
    source_identity = json.dumps(_plain(source), sort_keys=True, separators=(",", ":"))
    cache_key = (map_ref, resource.content_hash, source_identity)
    cached = _MAP_LAYER_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if source.get("format") != "weihai-raw-lonlat@1.0":
        raise ValueError("unsupported map visualization source format")
    relative = source.get("path")
    expected = source.get("sha256")
    if not isinstance(relative, str) or not relative or not isinstance(expected, str):
        raise ValueError("map visualization source identity is incomplete")
    path = (_ROOT / relative).resolve()
    if _ROOT not in path.parents or path.is_symlink() or not path.is_file():
        raise ValueError("map visualization source is outside the repository authority")
    raw = path.read_bytes()
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("map visualization source hash mismatch")
    document = json.loads(raw)
    if not isinstance(document, list) or any(not isinstance(item, list) for item in document):
        raise ValueError("map visualization geometry is invalid")
    geography = GeographyServiceV2.from_config(
        origin_wgs84=resource.content["origin_wgs84"],
        axis_orientation="east_north_up",
        tolerance_m=1e-6,
        # The checked-in map contains the complete Weihai coastline, while the
        # simulation bounds intentionally cover only the task area.
        local_bounds_m=(
            (-1_000_000.0, -1_000_000.0, -10_000.0),
            (1_000_000.0, 1_000_000.0, 10_000.0),
        ),
    )

    def polygon(raw_polygon: Sequence[Sequence[float]]) -> tuple[tuple[float, float], ...]:
        return tuple(
            geography.to_local(frame="wgs84", coordinates=(point[0], point[1], 0.0))[:2]
            for point in raw_polygon
        )

    geometries = tuple(polygon(item) for item in document)
    coastline_start = int(source["coastline_start"])
    coastline_end = int(source["coastline_end"])
    harbor_end = int(source["harbor_end"])
    land_indices = tuple(int(item) for item in source.get("land_polygon_indices", ()))
    if not 0 <= coastline_start <= coastline_end <= harbor_end <= len(geometries):
        raise ValueError("map visualization layer indexes are invalid")
    closed_coasts = tuple(
        item
        for item in geometries[coastline_start:coastline_end]
        if len(item) >= 4 and item[0] == item[-1]
    )
    polygons = tuple(geometries[index] for index in land_indices) + closed_coasts
    lines = geometries[coastline_start:harbor_end]
    identity = {
        "exact_ref": map_ref,
        "content_hash": resource.content_hash,
        "source_hash": actual,
        "geographic_crs": resource.content.get("geographic_crs"),
        "origin_wgs84": resource.content.get("origin_wgs84"),
    }
    result = (identity, polygons, lines)
    _MAP_LAYER_CACHE[cache_key] = result
    return result


def _world_bounds(session: SessionLifecycleV2) -> tuple[float, float, float, float]:
    """Return a stable task-scale viewport without consulting live entity state.

    A coordinate frame can cover a complete source map that is much larger than
    one engagement.  Rendering that full frame makes metre-scale motion appear
    stationary.  Declared non-terrain mission geometry is public scenario data
    and yields the same camera in referee, faction, public, live and replay
    views; live entity positions are intentionally excluded to avoid leaking
    hidden movement through viewport changes.
    """

    world = session.resolved.world
    points: list[tuple[float, float]] = []
    for zone in world.zones:
        tags = tuple(str(tag) for tag in getattr(zone, "tags", ()))
        if any(tag.startswith("terrain:") for tag in tags):
            continue
        geometry = getattr(zone, "geometry", None)
        positions = getattr(zone, "coordinates_m", getattr(geometry, "positions_m", ()))
        points.extend((float(point[0]), float(point[1])) for point in positions)
        if getattr(geometry, "type", None) == "circle":
            center = getattr(geometry, "center_m", None)
            radius = getattr(geometry, "radius_m", None)
            if center is not None and radius is not None:
                center_x, center_y = float(center[0]), float(center[1])
                radius_m = float(radius)
                points.extend(
                    (
                        (center_x - radius_m, center_y),
                        (center_x + radius_m, center_y),
                        (center_x, center_y - radius_m),
                        (center_x, center_y + radius_m),
                    )
                )
    if points:
        minimum_x = min(point[0] for point in points)
        maximum_x = max(point[0] for point in points)
        minimum_y = min(point[1] for point in points)
        maximum_y = max(point[1] for point in points)
        span = max(
            maximum_x - minimum_x,
            maximum_y - minimum_y,
            _TASK_VIEWPORT_MINIMUM_SPAN_M,
        )
        margin = max(
            _TASK_VIEWPORT_MINIMUM_MARGIN_M,
            span * _TASK_VIEWPORT_MARGIN_FRACTION,
        )
        return minimum_x - margin, minimum_y - margin, maximum_x + margin, maximum_y + margin
    frame = world.coordinate_frame
    if frame is not None:
        lower, upper = frame.local_bounds_m
        return float(lower[0]), float(lower[1]), float(upper[0]), float(upper[1])
    return -10_000.0, -10_000.0, 10_000.0, 10_000.0


def _wave_summary(
    session: SessionLifecycleV2, *, tick: int, entities: Sequence[Mapping[str, Any]]
) -> tuple[tuple[Mapping[str, Any], ...], str | None]:
    planned: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for event in session.resolved.events:
        if event.event_type != "spawn":
            continue
        payload = _plain(event.payload)
        entity = payload.get("entity", {})
        tags = tuple(entity.get("tags", ())) if isinstance(entity, Mapping) else ()
        wave_id = next((str(tag) for tag in tags if str(tag).startswith("wave-")), None)
        entity_id = entity.get("id") if isinstance(entity, Mapping) else None
        if wave_id is not None and isinstance(entity_id, str):
            planned[wave_id].append((int(event.trigger.tick), entity_id))
    active_by_wave: dict[str, int] = defaultdict(int)
    for entity in entities:
        for tag in entity.get("tags", ()):
            if str(tag).startswith("wave-"):
                active_by_wave[str(tag)] += 1
    summaries: list[Mapping[str, Any]] = []
    future: list[tuple[int, str]] = []
    for wave_id in sorted(planned):
        members = planned[wave_id]
        trigger_tick = min(item[0] for item in members)
        if trigger_tick > tick:
            future.append((trigger_tick, wave_id))
        summaries.append(
            {
                "wave_id": wave_id,
                "trigger_tick": trigger_tick,
                "planned": len(members),
                "spawned": sum(1 for event_tick, _entity_id in members if event_tick <= tick),
                "active": active_by_wave[wave_id],
            }
        )
    next_wave = min(future)[1] if future else None
    return tuple(summaries), next_wave


def build_formal_frame_v2(
    session: SessionLifecycleV2,
    catalog: CatalogV2,
    *,
    view: ViewV2 = "referee",
    faction_id: str | None = None,
    checkpoint: WorldCheckpointV2 | WorldPresentationSnapshotV2 | None = None,
) -> VisualizationFrameV2:
    """Freeze one rich authority frame; live display and replay store this exact DTO."""

    if view == "faction" and not faction_id:
        raise ValueError("faction visualization requires a faction_id")
    if checkpoint is None:
        checkpoint = session.world_view.presentation_snapshot()
    visible = tuple(
        entity
        for entity in session.world_view.entities_stable()
        if is_displayable_lifecycle_v2(entity.state.lifecycle)
        and (
            view == "referee"
            or (view == "faction" and entity.faction_id == faction_id)
            or view == "public"
            and "public" in entity.tags
        )
    )
    entities: list[dict[str, Any]] = []
    sensor_coverage: list[dict[str, Any]] = []
    weapon_coverage: list[dict[str, Any]] = []
    for entity in visible:
        bindings = entity.definition.resource_bindings
        visual = next(iter(bindings.get("visualization_assets", ())), None)
        platform = next(iter(bindings.get("platforms", ())), None)
        default_profile = {
            "air": "uav_generic",
            "surface": "usv_generic",
            "land": "shore_radar_generic",
            "underwater": "auv_generic",
        }.get(entity.domain, "uav_generic")
        profile = (
            default_profile
            if visual is None
            else visual.normalized_content.get("profile", default_profile)
        )
        communications = tuple(bindings.get("communications", ()))
        energy_profile = next(iter(bindings.get("energy", ())), None)
        comm_status = (
            "unavailable"
            if not communications
            else "offline"
            if entity.state.lifecycle not in {"active", "degraded"}
            or entity.state.energy is not None
            and entity.state.energy <= 0.0
            else "online"
        )
        entities.append(
            {
                "entity_id": entity.id,
                "faction_id": entity.faction_id,
                "domain": entity.domain,
                "platform_type": (
                    entity.domain
                    if platform is None
                    else platform.normalized_content.get("platform_type", entity.domain)
                ),
                "visual_profile": profile,
                "visual_length_m": (
                    10.0 if visual is None else visual.normalized_content.get("length_m", 10.0)
                ),
                "visual_width_m": (
                    10.0 if visual is None else visual.normalized_content.get("width_m", 10.0)
                ),
                "tags": entity.tags,
                "position_m": tuple(entity.state.position_m),
                "velocity_mps": tuple(entity.state.velocity_mps),
                "heading_deg": entity.state.heading_deg,
                "health": entity.state.health,
                "energy": entity.state.energy,
                "endurance_fraction": entity.state.energy,
                "energy_capacity_j": (
                    None
                    if energy_profile is None
                    else energy_profile.normalized_content.get("capacity_j")
                ),
                "sensor_status": (
                    "unavailable"
                    if not bindings.get("sensors")
                    else "online"
                    if entity.state.lifecycle in {"active", "degraded"}
                    else "offline"
                ),
                "communication_status": comm_status,
                "communication_quality": 1.0 if comm_status == "online" else 0.0,
                "lifecycle_state": entity.state.lifecycle,
                "ammunition": dict(entity.state.ammunition),
            }
        )
        if view != "public" and entity.state.lifecycle in {"active", "degraded"}:
            for sensor in bindings.get("sensors", ()):
                sensor_coverage.append(
                    {
                        "entity_id": entity.id,
                        "faction_id": entity.faction_id,
                        "kind": sensor.normalized_content.get("kind", "sensor"),
                        "center_m": tuple(entity.state.position_m[:2]),
                        "radius_m": float(sensor.normalized_content.get("range_m", 0.0)),
                        "resource_ref": sensor.exact_ref,
                    }
                )
            for weapon in bindings.get("weapons", ()):
                weapon_coverage.append(
                    {
                        "entity_id": entity.id,
                        "faction_id": entity.faction_id,
                        "center_m": tuple(entity.state.position_m[:2]),
                        "min_range_m": float(weapon.normalized_content.get("min_range_m", 0.0)),
                        "max_range_m": float(weapon.normalized_content.get("max_range_m", 0.0)),
                        "resource_ref": weapon.exact_ref,
                    }
                )
    if view != "public":
        for flight in checkpoint.missile_flights:
            if view == "faction" and flight.faction_id != faction_id:
                continue
            entities.append(
                {
                    "entity_id": flight.missile_id,
                    "faction_id": flight.faction_id,
                    "domain": "air",
                    "platform_type": "guided-missile",
                    "visual_profile": "missile_generic",
                    "visual_length_m": 4.0,
                    "visual_width_m": 0.8,
                    "tags": ("munition", "guided-missile"),
                    "position_m": flight.position_m,
                    "velocity_mps": flight.velocity_mps,
                    "heading_deg": flight.heading_deg,
                    "health": 1.0,
                    "energy": None,
                    "endurance_fraction": None,
                    "energy_capacity_j": None,
                    "sensor_status": (
                        "tracking" if flight.seeker_state == "tracking" else "searching"
                    ),
                    "communication_status": "unavailable",
                    "communication_quality": 0.0,
                    "lifecycle_state": "active",
                    "ammunition": {},
                }
            )
    map_identity, polygons, lines = _map_layers(session, catalog)
    zones: list[dict[str, Any]] = []
    for zone in session.resolved.world.zones:
        # Terrain is rendered as a checked map layer; it is not a mission zone.
        if "terrain:land" in getattr(zone, "tags", ()):
            continue
        resolved_geometry = getattr(zone, "geometry", None)
        geometry_type = getattr(
            zone, "geometry_type", getattr(resolved_geometry, "type", "polygon")
        )
        coordinates = getattr(zone, "coordinates_m", getattr(resolved_geometry, "positions_m", ()))
        zones.append(
            {
                "id": zone.id,
                "geometry_type": geometry_type,
                "coordinates_m": tuple(coordinates),
                "tags": zone.tags,
                "active": checkpoint.zone_activation_state.get(zone.id, True),
            }
        )
    latest = checkpoint.world_tick_ledger[-1] if checkpoint.world_tick_ledger else None
    positions_by_id = {str(item["entity_id"]): tuple(item["position_m"]) for item in entities}
    events: list[dict[str, Any]] = []
    if latest is not None and view == "referee":
        for receipt in latest.event_receipts:
            events.extend(dict(item) for item in receipt.get("typed_event_receipts", ()))
        for receipt in latest.combat_receipts:
            plain_receipt = _plain(receipt)
            execution = plain_receipt.get("execution") or {}
            attacker_id = execution.get("attacker_id")
            target_id = execution.get("target_id")
            shots = execution.get("shots", ())
            missile_ids = tuple(execution.get("launched_missile_ids", ()))
            if missile_ids:
                events.extend(
                    {
                        "event_type": "missile_launched",
                        "attacker_id": attacker_id,
                        "missile_id": missile_id,
                        "weapon_ref": execution.get("weapon_ref"),
                        "receipt": plain_receipt,
                    }
                    for missile_id in missile_ids
                )
                continue
            if attacker_id in positions_by_id and target_id in positions_by_id:
                events.append(
                    {
                        "event_type": "weapon_fired",
                        "attacker_id": attacker_id,
                        "target_id": target_id,
                        "start_m": positions_by_id[attacker_id],
                        "end_m": positions_by_id[target_id],
                        "hit": any(bool(item.get("hit")) for item in shots),
                        "weapon_ref": execution.get("weapon_ref"),
                        "receipt": plain_receipt,
                    }
                )
            else:
                events.append({"event_type": "combat", "receipt": plain_receipt})
        for receipt in latest.damage_receipts:
            events.append({"event_type": "damage", "receipt": _plain(receipt)})
    mission_checkpoint = checkpoint.mission_scoring_checkpoint or {}
    waves, next_wave = _wave_summary(session, tick=checkpoint.tick, entities=entities)
    event_state = asdict(checkpoint.event_state)
    visible_event_state = _event_state_for_view(event_state, view=view)
    communication_links: list[dict[str, Any]] = []
    for message in event_state.get("message_queue", ()):
        sender_id = message.get("sender_entity_id", message.get("sender_id"))
        recipient_id = message.get("recipient_entity_id", message.get("recipient_id"))
        if sender_id in positions_by_id and recipient_id in positions_by_id:
            communication_links.append(
                {
                    "message_id": message.get("message_id"),
                    "sender_id": sender_id,
                    "recipient_id": recipient_id,
                    "start_m": positions_by_id[sender_id],
                    "end_m": positions_by_id[recipient_id],
                    "status": message.get("status", "queued"),
                }
            )
    best_targeting: dict[str, dict[str, Any]] = {}
    for evidence in checkpoint.combat_contact_evidence:
        if (
            evidence.owner_entity_id not in positions_by_id
            or evidence.target_entity_id not in positions_by_id
        ):
            continue
        candidate = {
            "evidence_id": evidence.evidence_id,
            "owner_entity_id": evidence.owner_entity_id,
            "target_entity_id": evidence.target_entity_id,
            "start_m": positions_by_id[evidence.owner_entity_id],
            "end_m": positions_by_id[evidence.target_entity_id],
            "confidence": evidence.confidence,
            "quality": evidence.quality,
            "fresh": evidence.age_ticks <= evidence.max_age_ticks,
        }
        prior = best_targeting.get(evidence.target_entity_id)
        if prior is None or (
            candidate["fresh"],
            candidate["confidence"],
            candidate["evidence_id"],
        ) > (
            prior["fresh"],
            prior["confidence"],
            prior["evidence_id"],
        ):
            best_targeting[evidence.target_entity_id] = candidate
    targeting_links = tuple(best_targeting[key] for key in sorted(best_targeting))
    current_environment: Mapping[str, Any] = next(
        (
            event.payload.environment_binding.normalized_content
            for event in reversed(session.resolved.events)
            if event.event_type == "weather_change" and event.trigger.tick <= checkpoint.tick
        ),
        {},
    )
    return VisualizationFrameV2(
        schema_version="2.0",
        session_id=session.session_id,
        scenario_id=session.resolved.scenario_id,
        tick=checkpoint.tick,
        sim_time_s=checkpoint.spatial_clock.next_tick_time_seconds,
        view=view,
        view_faction_id=faction_id if view == "faction" else None,
        entities=tuple(entities),
        contacts_by_faction=(
            {}
            if view in {"referee", "public"}
            else session.world_view.observation(
                observer_faction_id=faction_id or ""
            ).contacts_by_faction
        ),
        scores_by_faction={"scenario": dict(mission_checkpoint.get("score_state", {}))},
        map_identity=dict(map_identity),
        world_bounds_m=_world_bounds(session),
        static_polygons=polygons,
        static_lines=lines,
        zones=tuple(zones),
        sensor_coverage=tuple(sensor_coverage),
        weapon_coverage=tuple(weapon_coverage),
        communication_links=tuple(communication_links),
        targeting_links=targeting_links,
        events=tuple(events),
        environment={"declared": _plain(current_environment), **visible_event_state},
        mission={
            "states": tuple(mission_checkpoint.get("mission_states", ())),
            "terminal_result": mission_checkpoint.get("terminal_result"),
            "duration_ticks": session.resolved.world.duration_ticks,
            "remaining_ticks": max(
                0, int(session.resolved.world.duration_ticks or checkpoint.tick) - checkpoint.tick
            ),
            "waves": waves,
            "next_wave": next_wave,
        },
        annotations=tuple(
            {"entity_id": item["entity_id"], "text": item["entity_id"]} for item in entities
        ),
    )


__all__ = ["MatplotlibRendererV2", "ViewV2", "build_formal_frame_v2"]

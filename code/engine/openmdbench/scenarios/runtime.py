"""Configuration-driven scenario world construction shared by formal runtimes.

RF-03: formal runtimes are assembled from ``ResolvedScenario`` artifacts
produced by :class:`openmdbench.scenarios.compiler.ScenarioCompiler`.  The
artifacts embed the frozen component configuration, so world contents,
seeded wave scheduling and map identity are unchanged from the legacy
``load_*_config`` pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from openmdbench.core.entities import ComponentState, Domain, PlatformAsset, Side
from openmdbench.core.geography import GeoFrame, load_weihai_geoframe
from openmdbench.core.rng import SessionRNG
from openmdbench.core.units import heading_deg_to_math_rad
from openmdbench.core.world import WorldState
from openmdbench.scenarios.compiler import ScenarioCompiler
from openmdbench.scenarios.md_ad_002_config import (
    MDAD002_CONFIG_PATHS,
    MDAD002Config,
    load_md_ad_002_config,  # noqa: F401 - kept as a stable monkeypatch target
)
from openmdbench.scenarios.package import ScenarioPackageRef
from openmdbench.scenarios.resolved import (
    ResolvedDeployment,
    ResolvedMap,
    ResolvedScenario,
)
from openmdbench.scenarios.schema import Scenario

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    scenario_id: str
    config_version: str
    config_hash: str
    rules_version: str
    coordinate_system: str
    map_identity: dict[str, object]
    reference_origin_lonlat: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ScheduledEntity:
    entity_id: str
    wave_id: str
    scheduled_tick: int
    position: tuple[float, float, float]
    heading_deg: float
    speed_mps: float
    side: Side = Side.BLUE
    platform_type: Literal["uav", "usv", "shore_radar", "auv"] = "uav"
    weapon_inventory: dict[str, int] | None = None
    required_surface: Literal["water", "land", "any"] = "any"


@dataclass(slots=True)
class ScenarioRuntime:
    scenario: Scenario
    world: WorldState
    geo_frame: GeoFrame
    metadata: RuntimeMetadata
    scheduled_entities: tuple[ScheduledEntity, ...]
    primary_entity_id: str
    protected_point: tuple[float, float]
    compatibility_goal: tuple[float, float]
    time_limit_ticks: int
    threat_entity_id: str | None = None
    protection_radius_m: float | None = None
    md_ad_config: MDAD002Config | None = None
    resolved: ResolvedScenario | None = None


def validate_scheduled_entities(runtime: ScenarioRuntime) -> None:
    """Fail closed on duplicate, terrestrial, out-of-map, or invalid scheduled spawns."""
    ids = [item.entity_id for item in runtime.scheduled_entities]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scheduled entity ID")
    min_x, min_y, max_x, max_y = runtime.geo_frame.visualization_layers.bounds(padding_fraction=0.0)
    for item in runtime.scheduled_entities:
        x, y, altitude = item.position
        if not min_x <= x <= max_x or not min_y <= y <= max_y:
            raise ValueError(f"scheduled entity {item.entity_id} is outside the map")
        on_land = runtime.geo_frame.is_land_local(x, y)
        if item.required_surface == "water" and on_land:
            raise ValueError(f"scheduled entity {item.entity_id} is not over water")
        if item.required_surface == "land" and not on_land:
            raise ValueError(f"scheduled entity {item.entity_id} is not on land")
        if (
            altitude < 0
            or item.scheduled_tick < 0
            or item.scheduled_tick >= runtime.time_limit_ticks
        ):
            raise ValueError(f"scheduled entity {item.entity_id} has invalid time or altitude")


def _formal_map(resolved_map: ResolvedMap) -> GeoFrame:
    """Re-verify the frozen map identity recorded in the artifact."""
    if not resolved_map.verified:
        raise ValueError("formal runtime requires a verified map identity")
    if (
        resolved_map.raw_sha256 is None
        or resolved_map.xy_sha256 is None
        or resolved_map.origin_lonlat is None
        or resolved_map.legacy_scale is None
        or resolved_map.offset_margin is None
    ):
        raise ValueError("formal runtime requires a complete map identity")
    return load_weihai_geoframe(
        map_root=Path(__file__).parents[1].parent / "env/map_data",
        expected_raw_sha256=resolved_map.raw_sha256,
        expected_xy_sha256=resolved_map.xy_sha256,
        origin_lonlat=resolved_map.origin_lonlat,
        legacy_scale=resolved_map.legacy_scale,
        offset_margin=resolved_map.offset_margin,
    )


def _asset_from_resolved(item: ResolvedDeployment, geo_frame: GeoFrame) -> PlatformAsset:
    """Register a resolved deployment through the shared GeoFrame conversion."""
    lon_deg = item.lon_deg
    lat_deg = item.lat_deg
    if lon_deg is None or lat_deg is None:
        raise ValueError(f"deployment {item.entity_id} is missing WGS84 coordinates")
    local = geo_frame.wgs84_to_local(lon_deg, lat_deg)
    heading_rad = heading_deg_to_math_rad(item.heading_deg)
    domain = {
        "uav": Domain.AIR,
        "usv": Domain.SURFACE,
        "shore_radar": Domain.SHORE,
        "auv": Domain.UNDERWATER,
    }[item.platform_type]
    return PlatformAsset(
        id=item.entity_id,
        side=Side(item.side),
        domain=domain,
        platform_type=item.platform_type,
        position=(*local, item.position_m[2]),
        velocity=(
            item.speed_mps * math.cos(heading_rad),
            item.speed_mps * math.sin(heading_rad),
            0.0,
        ),
        heading_deg=item.heading_deg,
        components=ComponentState(
            sensor_mode="active_search", weapon_inventory=dict(item.weapon_inventory)
        ),
    )


def _build_md_ad(
    resolved: ResolvedScenario, scenario: Scenario, config: MDAD002Config, seed: int
) -> ScenarioRuntime:
    geo = _formal_map(resolved.map)
    world = WorldState(
        session_id=f"local-{scenario.scenario_id}",
        mission_briefing=scenario.public.background,
        time_remaining=resolved.clock.time_limit_ticks,
        # Timeline profiles describe future events; every AD2 scenario starts clear.
        weather="clear",
    )
    for item in resolved.deployments:  # already sorted by entity_id
        world.registry.register(_asset_from_resolved(item, geo))
    protected = tuple(resolved.adjudication["protected_point_m"])
    scheduled: list[ScheduledEntity] = []
    spawn_rng = SessionRNG(seed)
    timing_rng = spawn_rng.stream(f"{scenario.scenario_id}:spawn_timing")
    position_rng = spawn_rng.stream(f"{scenario.scenario_id}:spawn_position")
    altitude_rng = spawn_rng.stream(f"{scenario.scenario_id}:spawn_altitude")
    zones = {zone.zone_id: zone for zone in resolved.zones if zone.kind == "spawn"}
    map_bounds = geo.visualization_layers.bounds(padding_fraction=0.0)
    next_index = 1
    for wave in resolved.waves:  # already sorted by (base_tick, wave_id)
        tick = wave.base_tick
        if wave.jitter_ticks:
            tick += int(timing_rng.integers(-wave.jitter_ticks, wave.jitter_ticks + 1))
        for offset, index in enumerate(range(next_index, next_index + wave.count)):
            zone: Literal["east_sea", "northeast_sea"] = (
                "east_sea" if wave.wave_id == "wave-1" or offset < 3 else "northeast_sea"
            )
            spawn_zone = zones[zone]
            centre = spawn_zone.centre_m
            half_width_m = spawn_zone.half_width_m
            if half_width_m is None:
                raise ValueError(f"spawn zone {zone} is missing its half width")
            for _ in range(64):
                x = centre[0] + float(position_rng.uniform(-half_width_m, half_width_m))
                y = centre[1] + float(position_rng.uniform(-half_width_m, half_width_m))
                if (
                    map_bounds[0] <= x <= map_bounds[2]
                    and map_bounds[1] <= y <= map_bounds[3]
                    and not geo.is_land_local(x, y)
                ):
                    break
            else:
                raise ValueError(f"no valid water/air spawn point for {wave.wave_id}")
            altitude = float(altitude_rng.uniform(wave.altitude_min_m, wave.altitude_max_m))
            east = protected[0] - x
            north = protected[1] - y
            heading = math.degrees(math.atan2(east, north)) % 360.0
            speed = (
                45.0
                if wave.wave_id == "wave-3"
                and wave.behavior != "direct"
                and offset >= wave.count - 2
                else 30.0
            )
            scheduled.append(
                ScheduledEntity(
                    entity_id=f"blue-striker-uav-{index:02d}",
                    wave_id=wave.wave_id,
                    scheduled_tick=tick,
                    position=(x, y, altitude),
                    heading_deg=heading,
                    speed_mps=speed,
                    required_surface="water",
                )
            )
        next_index += wave.count
    runtime = ScenarioRuntime(
        scenario=scenario,
        world=world,
        geo_frame=geo,
        metadata=RuntimeMetadata(
            scenario_id=scenario.scenario_id,
            config_version=config.config_version,
            config_hash=resolved.component_hashes["md_ad_002"],
            rules_version=config.adjudication.mode,
            coordinate_system="local_aeqd_metre",
            map_identity=geo.metadata(),
            reference_origin_lonlat=geo.identity.origin_lonlat,
        ),
        scheduled_entities=tuple(scheduled),
        primary_entity_id=str(resolved.adjudication["primary_entity_id"]),
        protected_point=protected,
        compatibility_goal=protected,
        time_limit_ticks=resolved.clock.time_limit_ticks,
        md_ad_config=config,
        resolved=resolved,
    )
    validate_scheduled_entities(runtime)
    return runtime


def _build_composition(
    resolved: ResolvedScenario, scenario: Scenario, seed: int
) -> ScenarioRuntime:
    """Build a catalog-composed world through the existing WorldState/kernel."""
    geo = _formal_map(resolved.map)
    world = WorldState(
        session_id=f"local-{resolved.scenario_id}",
        mission_briefing=scenario.public.background,
        time_remaining=resolved.clock.time_limit_ticks,
        weather=str(resolved.adjudication.get("initial_weather", "clear")),
    )
    for item in resolved.deployments:
        world.registry.register(_asset_from_resolved(item, geo))
    protected = tuple(resolved.adjudication["protected_point_m"])
    rng = SessionRNG(seed)
    timing_rng = rng.stream(f"{resolved.scenario_id}:spawn_timing")
    position_rng = rng.stream(f"{resolved.scenario_id}:spawn_position")
    altitude_rng = rng.stream(f"{resolved.scenario_id}:spawn_altitude")
    zones = {zone.zone_id: zone for zone in resolved.zones if zone.kind == "spawn"}
    bounds = geo.visualization_layers.bounds(padding_fraction=0.0)
    scheduled: list[ScheduledEntity] = []
    used_ids = {item.entity_id for item in resolved.deployments}
    for wave in resolved.waves:
        tick = wave.base_tick
        if wave.jitter_ticks:
            tick += int(timing_rng.integers(-wave.jitter_ticks, wave.jitter_ticks + 1))
        if wave.spawn_zone is None or wave.spawn_zone not in zones:
            raise ValueError(f"wave {wave.wave_id} has no resolved spawn zone")
        zone = zones[wave.spawn_zone]
        if zone.half_width_m is None:
            raise ValueError(f"spawn zone {zone.zone_id} is incomplete")
        for index in range(1, wave.count + 1):
            entity_id = f"{wave.entity_prefix}-{index:02d}"
            if entity_id in used_ids:
                raise ValueError(f"duplicate generated entity ID: {entity_id}")
            used_ids.add(entity_id)
            for _ in range(64):
                x = zone.centre_m[0] + float(
                    position_rng.uniform(-zone.half_width_m, zone.half_width_m)
                )
                y = zone.centre_m[1] + float(
                    position_rng.uniform(-zone.half_width_m, zone.half_width_m)
                )
                terrain_valid = (
                    not geo.is_land_local(x, y)
                    if wave.platform_type in {"usv", "auv"}
                    else geo.is_land_local(x, y)
                    if wave.platform_type == "shore_radar"
                    else True
                )
                if bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3] and terrain_valid:
                    break
            else:
                raise ValueError(f"no valid spawn point for wave {wave.wave_id}")
            altitude = float(altitude_rng.uniform(wave.altitude_min_m, wave.altitude_max_m))
            heading = math.degrees(math.atan2(protected[0] - x, protected[1] - y)) % 360.0
            scheduled.append(
                ScheduledEntity(
                    entity_id=entity_id,
                    wave_id=wave.wave_id,
                    scheduled_tick=tick,
                    position=(x, y, altitude),
                    heading_deg=heading,
                    speed_mps=wave.speed_mps,
                    side=Side(wave.side),
                    platform_type=wave.platform_type,
                    weapon_inventory=dict(wave.weapon_inventory),
                    required_surface=("land" if wave.platform_type == "shore_radar" else "water"),
                )
            )
    runtime = ScenarioRuntime(
        scenario=scenario,
        world=world,
        geo_frame=geo,
        metadata=RuntimeMetadata(
            scenario_id=resolved.scenario_id,
            config_version=resolved.scenario_version,
            config_hash=resolved.component_hashes["composition"],
            rules_version=str(resolved.adjudication.get("mode", "generic_timeline_v1")),
            coordinate_system="local_aeqd_metre",
            map_identity=geo.metadata(),
            reference_origin_lonlat=geo.identity.origin_lonlat,
        ),
        scheduled_entities=tuple(scheduled),
        primary_entity_id=str(resolved.adjudication["primary_entity_id"]),
        protected_point=protected,
        compatibility_goal=protected,
        time_limit_ticks=resolved.clock.time_limit_ticks,
        resolved=resolved,
    )
    validate_scheduled_entities(runtime)
    return runtime


_FORMAL_RUNTIME_IDS = frozenset(MDAD002_CONFIG_PATHS)
_FORMAL_SCENARIO_PATHS = {
    "MD-AD-002-EASY": "openmdbench/scenarios/area_denial/MD-AD-002.yaml",
    "MD-AD-002-MEDIUM": "openmdbench/scenarios/area_denial/MD-AD-002.yaml",
    "MD-AD-002-HARD": "openmdbench/scenarios/area_denial/MD-AD-002.yaml",
}
_FORMAL_COMPONENT_PATHS = {
    **MDAD002_CONFIG_PATHS,
}


def formal_package_ref(scenario_id: str) -> ScenarioPackageRef:
    """Return the installed package boundary for a formal scenario."""
    if scenario_id not in _FORMAL_RUNTIME_IDS:
        raise ValueError(f"scenario has no formal runtime: {scenario_id}")
    return ScenarioPackageRef(
        root=_PACKAGE_ROOT,
        scenario=_FORMAL_SCENARIO_PATHS[scenario_id],
        component=_FORMAL_COMPONENT_PATHS[scenario_id],
    )


def create_runtime_from_resolved(resolved: ResolvedScenario, seed: int = 0) -> ScenarioRuntime:
    """Build the isolated runtime for a compiled formal artifact."""
    if resolved.resolved_hash != resolved.expected_hash():
        raise ValueError("resolved scenario hash does not match its content")
    if not resolved.formal:
        raise ValueError(f"scenario has no formal runtime: {resolved.scenario_id}")
    scenario = Scenario.model_validate(resolved.components["scenario"])
    if "md_ad_002" in resolved.components:
        ad_config = MDAD002Config.model_validate(resolved.components["md_ad_002"])
        return _build_md_ad(resolved, scenario, ad_config, seed)
    if "composition" in resolved.components:
        return _build_composition(resolved, scenario, seed)
    raise ValueError(f"scenario has no formal runtime: {resolved.scenario_id}")


def create_scenario_runtime(scenario_id: str, seed: int = 0) -> ScenarioRuntime:
    """Create an isolated runtime through the registered capability adapter."""
    try:
        ref = formal_package_ref(scenario_id)
    except (KeyError, ValueError) as error:
        raise ValueError(f"scenario has no formal runtime: {scenario_id}") from error
    return create_runtime_from_resolved(ScenarioCompiler().compile_package(ref), seed)


def has_scenario_runtime(scenario_id: str) -> bool:
    return scenario_id in _FORMAL_RUNTIME_IDS

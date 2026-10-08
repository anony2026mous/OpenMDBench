"""ScenarioCompiler: validate, resolve and hash versioned scenario packages.

Implements the RF-03 compile pipeline (requirements CMP-001..CMP-004):
schema -> resource references -> units -> coordinates -> bounds ->
compatibility -> reference closure -> waves/events -> mission/scoring ->
visibility -> immutable, hashable ``ResolvedScenario``.  Formal Weihai
scenarios verify map identity, version and content hash; WGS84 positions are
converted to the unified local metre frame through the existing ``GeoFrame``.
Compiling never depends on timestamps, PIDs, absolute paths or environment,
so the same package always yields the same resolved hash (CMP-004).
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import ValidationError

from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    EntityCompositionV2,
)
from openmdbench.core.entities import Side
from openmdbench.core.geography import GeoFrame, load_weihai_geoframe
from openmdbench.core.rng import configuration_hash
from openmdbench.scenarios.composition import GenericComposition
from openmdbench.scenarios.legacy.catalog_support import (
    legacy_md_ad_catalog,
    load_legacy_composition_catalog_v2,
)
from openmdbench.scenarios.loader import render_briefing
from openmdbench.scenarios.md_ad_002_config import MDAD002Config
from openmdbench.scenarios.package import ScenarioPackageRef
from openmdbench.scenarios.resolved import (
    ResolvedCatalog,
    ResolvedClock,
    ResolvedDeployment,
    ResolvedEvent,
    ResolvedMap,
    ResolvedScenario,
    ResolvedWave,
    ResolvedZone,
    build_resolved_scenario,
)
from openmdbench.scenarios.schema import Scenario

COMPILE_FAILED_CODE = "scenario.compile_failed"

_PACKAGE_ROOT = Path(__file__).parents[3]
PlatformType = Literal["uav", "usv", "shore_radar", "auv"]
Domain = Literal["air", "surface", "shore", "underwater"]

_PLATFORM_DOMAINS: dict[str, Domain] = {
    "uav": "air",
    "usv": "surface",
    "shore_radar": "shore",
    "auv": "underwater",
}
_AD2_PLATFORM_TYPES: dict[str, PlatformType] = {
    "shore_radar": "shore_radar",
    "interceptor_uav": "uav",
    "picket_usv": "usv",
}
_AD2_INVENTORY_WEAPONS = {
    "shore_radar": "shore_ciws",
    "interceptor_uav": "uav_interceptor_missile",
}
_MD_AD_UNITS = {
    "position": "metre",
    "altitude": "metre",
    "heading": "degree",
    "speed": "metre_per_second",
    "range": "metre",
    "radius": "metre",
    "time": "tick",
    "tick_duration": "second",
    "wave_time": "second",
}
_GENERIC_UNITS = {
    "position": "metre",
    "altitude": "metre",
    "heading": "degree",
    "speed": "metre_per_second",
    "time": "tick",
}
ComponentConfig = MDAD002Config


class ScenarioCompileError(ValueError):
    """Stable, machine-readable compile failure without a traceback."""

    def __init__(
        self,
        reason: str,
        message: str,
        *,
        file: str | None = None,
        field_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = COMPILE_FAILED_CODE
        self.reason = reason
        self.file = file
        self.field_path = field_path
        self.details = dict(details or {})
        super().__init__(f"[{reason}] {message}")


@dataclass(frozen=True, slots=True)
class ScenarioCompileIssue:
    code: str
    reason: str
    message: str
    file: str | None
    field_path: str | None
    details: dict[str, Any]


def _schema_error(model: str, error: ValidationError, *, file: str | None) -> ScenarioCompileError:
    first = error.errors()[0]
    loc = [str(part) for part in first.get("loc", ()) if str(part) != "model"]
    field_path = ".".join(loc) or None
    return ScenarioCompileError(
        "schema.invalid",
        f"{model}: {first.get('msg', 'invalid value')}",
        file=file,
        field_path=field_path,
        details={"type": str(first.get("type", ""))},
    )


class ScenarioCompiler:
    """Compiles scenario packages into immutable, hashable ResolvedScenario."""

    def __init__(self, map_root: str | Path | None = None) -> None:
        self._map_root = (
            Path(map_root) if map_root is not None else _PACKAGE_ROOT / "env" / "map_data"
        )

    # -- public library interface (validate / resolve / inspect) --------

    def compile_package(self, ref: ScenarioPackageRef) -> ResolvedScenario:
        """Resolve one package; fail closed with a stable error on any issue."""
        try:
            return self._compile(ref)
        except ScenarioCompileError:
            raise
        except (OSError, ValueError) as error:
            raise ScenarioCompileError(
                "internal.error",
                f"scenario compilation failed closed: {error.__class__.__name__}",
                file=ref.scenario,
            ) from error

    def validate_package(self, ref: ScenarioPackageRef) -> tuple[ScenarioCompileIssue, ...]:
        """Return issues for one package; an empty tuple means it compiles."""
        try:
            self.compile_package(ref)
        except ScenarioCompileError as error:
            return (
                ScenarioCompileIssue(
                    error.code,
                    error.reason,
                    str(error),
                    error.file,
                    error.field_path,
                    error.details,
                ),
            )
        except Exception as error:  # noqa: BLE001 - validation must never raise
            return (
                ScenarioCompileIssue(
                    COMPILE_FAILED_CODE,
                    "internal.error",
                    "scenario compilation failed closed",
                    None,
                    None,
                    {"type": error.__class__.__name__},
                ),
            )
        return ()

    def inspect(self, resolved: ResolvedScenario) -> dict[str, Any]:
        """Return a stable, human-readable summary of a resolved scenario."""
        return {
            "schema_version": resolved.schema_version,
            "scenario_id": resolved.scenario_id,
            "scenario_version": resolved.scenario_version,
            "category": resolved.category,
            "difficulty": resolved.difficulty,
            "formal": resolved.formal,
            "package_hash": resolved.package_hash,
            "resolved_hash": resolved.resolved_hash,
            "coordinate_system": resolved.coordinate_system,
            "units": dict(sorted(resolved.units.items())),
            "map": {key: value for key, value in sorted(resolved.map.model_dump().items())},
            "clock": resolved.clock.model_dump(),
            "counts": {
                "deployments": len(resolved.deployments),
                "zones": len(resolved.zones),
                "waves": len(resolved.waves),
                "events": len(resolved.events),
            },
            "catalog": (
                {
                    "content_hash": resolved.catalog.content_hash,
                    "resources": len(resolved.catalog.resource_hashes),
                }
                if resolved.catalog is not None
                else None
            ),
            "component_hashes": dict(sorted(resolved.component_hashes.items())),
            "entity_ids": [item.entity_id for item in resolved.deployments],
        }

    # -- pipeline ---------------------------------------------------------

    def _compile(self, ref: ScenarioPackageRef) -> ResolvedScenario:
        try:
            files = ref.files()
            package_hash = ref.content_hash()
        except (OSError, ValueError) as error:
            raise ScenarioCompileError("package.invalid", str(error)) from error

        scenario_raw = self._parse_yaml(files, ref.scenario, "scenario")
        try:
            scenario = Scenario.model_validate(scenario_raw)
        except ValidationError as error:
            raise _schema_error("Scenario", error, file=ref.scenario) from error

        component_raw = None
        if ref.component is not None:
            component_raw = self._parse_yaml(files, ref.component, "component")

        self._check_visibility(scenario, ref.scenario)
        if component_raw is None:
            return self._compile_generic(scenario, package_hash, ref.scenario)
        if component_raw.get("schema_version") == "composition@1.0":
            return self._compile_composition(scenario, component_raw, package_hash, ref, files)
        return self._compile_formal(scenario, component_raw, package_hash, ref)

    def _compile_composition(
        self,
        scenario: Scenario,
        raw: dict[str, Any],
        package_hash: str,
        ref: ScenarioPackageRef,
        files: Mapping[str, bytes],
    ) -> ResolvedScenario:
        if ref.component is None:
            raise ScenarioCompileError("package.invalid", "composition entry is missing")
        try:
            composition = GenericComposition.model_validate(raw)
        except ValidationError as error:
            raise _schema_error("GenericComposition", error, file=ref.component) from error
        try:
            repository = load_legacy_composition_catalog_v2(
                {path: files[path] for path in ref.catalogs}
            )
        except ValueError as error:
            raise ScenarioCompileError(
                "catalog.invalid", str(error), file=ref.catalogs[0] if ref.catalogs else None
            ) from error
        if not ref.catalogs:
            raise ScenarioCompileError(
                "catalog.missing", "composition packages require at least one catalog file"
            )
        map_cfg = composition.map
        try:
            geo = load_weihai_geoframe(
                map_root=self._map_root,
                expected_raw_sha256=map_cfg.raw_sha256,
                expected_xy_sha256=map_cfg.xy_sha256,
                origin_lonlat=map_cfg.origin_lonlat,
                legacy_scale=map_cfg.legacy_scale,
                offset_margin=map_cfg.offset_margin,
            )
        except (OSError, ValueError) as error:
            raise ScenarioCompileError(
                "map.hash_mismatch", str(error), file=ref.component, field_path="map"
            ) from error
        if map_cfg.map_id != geo.identity.map_id or map_cfg.version != geo.identity.version:
            raise ScenarioCompileError(
                "map.identity_mismatch",
                "declared map ID/version does not match the verified map",
                file=ref.component,
                field_path="map",
            )
        if scenario.scenario_id != composition.scenario_id:
            raise ScenarioCompileError(
                "reference.mismatch",
                "scenario.yaml and composition.yaml must declare the same scenario_id",
                file=ref.component,
                field_path="scenario_id",
            )

        def resolve_components(
            platform_ref: str,
            dynamics_ref: str,
            loadout_ref: str | None,
            sensor_refs: tuple[str, ...],
            communication_ref: str | None,
            inventory: Mapping[str, int],
            path: str,
            speed_mps: float,
        ) -> CatalogResourceV2:
            try:
                platform = repository.resolve("platforms", platform_ref)
                platform_type = str(platform.content.get("platform_type", ""))
                platform_domain = str(platform.content.get("domain", ""))
                if platform_type not in _PLATFORM_DOMAINS:
                    raise CatalogResolutionErrorV2(
                        f"unsupported engine platform type: {platform_type}"
                    )
                dynamics = repository.resolve("dynamics", dynamics_ref)
                if speed_mps > float(dynamics.content.get("maximum_speed_mps", 0.0)):
                    raise CatalogResolutionErrorV2(
                        "initial speed exceeds dynamics maximum_speed_mps"
                    )
                if platform_domain != _PLATFORM_DOMAINS[platform_type]:
                    raise CatalogResolutionErrorV2(
                        "platform domain conflicts with engine platform type"
                    )
                ammunition: dict[str, int] = {}
                target_domains: set[str] | None = None
                if loadout_ref is not None:
                    loadout = repository.resolve("loadouts", loadout_ref)
                    weapon_refs = tuple(loadout.content.get("weapon_refs", ()))
                    ammunition_by_weapon: dict[str, list[str]] = {}
                    for ammunition_ref in sorted(loadout.content.get("ammunition_refs", ())):
                        ammunition_resource = repository.resolve("ammunition", str(ammunition_ref))
                        weapon_ref = ammunition_resource.content.get("weapon_ref")
                        if not isinstance(weapon_ref, str):
                            raise CatalogResolutionErrorV2(
                                "loadout ammunition weapon_ref is missing"
                            )
                        ammunition_by_weapon.setdefault(weapon_ref, []).append(str(ammunition_ref))
                    for weapon_ref, count in sorted(inventory.items()):
                        if weapon_ref not in weapon_refs:
                            raise CatalogResolutionErrorV2(
                                f"inventory weapon {weapon_ref} is absent from the selected loadout"
                            )
                        candidates = ammunition_by_weapon.get(weapon_ref, [])
                        if len(candidates) != 1:
                            qualifier = "missing" if not candidates else "ambiguous"
                            raise CatalogResolutionErrorV2(
                                f"{qualifier} loadout ammunition for inventory weapon {weapon_ref}"
                            )
                        ammunition[candidates[0]] = count
                    for weapon_ref in sorted(str(item) for item in weapon_refs):
                        weapon = repository.resolve("weapons", weapon_ref)
                        supported = set(
                            str(item) for item in weapon.content.get("target_domains", ())
                        )
                        target_domains = (
                            supported
                            if target_domains is None
                            else target_domains.intersection(supported)
                        )
                elif inventory:
                    raise CatalogResolutionErrorV2("weapon inventory requires a selected loadout")
                repository.validate_full_composition(
                    EntityCompositionV2(
                        schema_version="2.0",
                        platform_ref=platform_ref,
                        dynamics_ref=dynamics_ref,
                        loadout_ref=loadout_ref,
                        sensor_refs=sensor_refs,
                        communication_refs=(
                            () if communication_ref is None else (communication_ref,)
                        ),
                        ammunition=ammunition,
                        energy_ref=cast(str | None, platform.content.get("energy_ref")),
                        collision_shape_ref=cast(
                            str | None, platform.content.get("collision_shape_ref")
                        ),
                        visualization_ref=cast(
                            str | None, platform.content.get("visualization_ref")
                        ),
                        target_domains=tuple(sorted(target_domains or ())),
                    )
                )
                return platform
            except (CatalogResolutionErrorV2, ValueError) as error:
                raise ScenarioCompileError(
                    "compatibility.invalid",
                    str(error),
                    file=ref.component,
                    field_path=path,
                    details={
                        "value": {
                            "platform_ref": platform_ref,
                            "dynamics_ref": dynamics_ref,
                            "loadout_ref": loadout_ref,
                        },
                        "suggestion": "use mutually compatible exact Catalog references",
                    },
                ) from error

        deployments: list[ResolvedDeployment] = []
        for entity in sorted(composition.entities, key=lambda item: item.id):
            platform = resolve_components(
                entity.platform_ref,
                entity.dynamics_ref,
                entity.loadout_ref,
                entity.sensor_refs,
                entity.communication_ref,
                entity.inventory,
                f"entities.{entity.id}",
                entity.initial_state.speed_mps,
            )
            state = entity.initial_state
            local = geo.wgs84_to_local(state.lon_deg, state.lat_deg)
            self._check_in_bounds(entity.id, local, geo, ref.component, f"entities.{entity.id}")
            if self._terrain_mismatch(
                state.terrain, geo.is_land_wgs84(state.lon_deg, state.lat_deg)
            ):
                raise ScenarioCompileError(
                    "deployment.terrain_mismatch",
                    f"deployment {entity.id} does not match map terrain",
                    file=ref.component,
                    field_path=f"entities.{entity.id}.initial_state.terrain",
                )
            deployments.append(
                ResolvedDeployment(
                    entity_id=entity.id,
                    side=entity.side,
                    platform_type=cast(PlatformType, platform.content["platform_type"]),
                    domain=cast(Domain, platform.content["domain"]),
                    lon_deg=state.lon_deg,
                    lat_deg=state.lat_deg,
                    position_m=(*local, state.altitude_m),
                    heading_deg=state.heading_deg,
                    speed_mps=state.speed_mps,
                    weapon_inventory=dict(entity.inventory),
                    terrain=state.terrain,
                    platform_ref=entity.platform_ref,
                    dynamics_ref=entity.dynamics_ref,
                    loadout_ref=entity.loadout_ref,
                    sensor_refs=entity.sensor_refs,
                    communication_ref=entity.communication_ref,
                )
            )
        resolved_zones: list[ResolvedZone] = []
        for zone in sorted(composition.spawn_zones, key=lambda item: item.id):
            centre = geo.wgs84_to_local(zone.lon_deg, zone.lat_deg)
            self._check_in_bounds(zone.id, centre, geo, ref.component, f"spawn_zones.{zone.id}")
            resolved_zones.append(
                ResolvedZone(
                    zone_id=zone.id,
                    kind="spawn",
                    lon_deg=zone.lon_deg,
                    lat_deg=zone.lat_deg,
                    centre_m=centre,
                    half_width_m=zone.half_width_m,
                )
            )
        zones = tuple(resolved_zones)
        zones_by_id = {item.zone_id: item for item in zones}
        waves: list[ResolvedWave] = []
        for wave in sorted(composition.waves, key=lambda item: (item.time_tick, item.id)):
            platform = resolve_components(
                wave.platform_ref,
                wave.dynamics_ref,
                wave.loadout_ref,
                wave.sensor_refs,
                wave.communication_ref,
                wave.inventory,
                f"waves.{wave.id}",
                wave.speed_mps,
            )
            spawn_centre = zones_by_id[wave.spawn_zone].centre_m
            centre_on_land = geo.is_land_local(*spawn_centre)
            if platform.content["domain"] in {"surface", "underwater"} and centre_on_land:
                raise ScenarioCompileError(
                    "wave.terrain_mismatch",
                    f"wave {wave.id} spawn centre is on land",
                    file=ref.component,
                    field_path=f"waves.{wave.id}.spawn_zone",
                )
            if platform.content["domain"] == "shore" and not centre_on_land:
                raise ScenarioCompileError(
                    "wave.terrain_mismatch",
                    f"wave {wave.id} spawn centre is on water",
                    file=ref.component,
                    field_path=f"waves.{wave.id}.spawn_zone",
                )
            if (
                wave.time_tick < wave.time_jitter_ticks
                or wave.time_tick + wave.time_jitter_ticks >= scenario.time_limit_ticks
            ):
                raise ScenarioCompileError(
                    "wave.out_of_range",
                    f"wave {wave.id} jitter leaves the mission time range",
                    file=ref.component,
                    field_path=f"waves.{wave.id}.time_tick",
                )
            waves.append(
                ResolvedWave(
                    wave_id=wave.id,
                    count=wave.count,
                    base_tick=wave.time_tick,
                    jitter_ticks=wave.time_jitter_ticks,
                    behavior=wave.behavior,
                    altitude_min_m=wave.altitude_min_m,
                    altitude_max_m=wave.altitude_max_m,
                    entity_prefix=wave.entity_prefix,
                    side=wave.side,
                    platform_type=cast(PlatformType, platform.content["platform_type"]),
                    spawn_zone=wave.spawn_zone,
                    speed_mps=wave.speed_mps,
                    weapon_inventory=dict(wave.inventory),
                    platform_ref=wave.platform_ref,
                    dynamics_ref=wave.dynamics_ref,
                    loadout_ref=wave.loadout_ref,
                    sensor_refs=wave.sensor_refs,
                    communication_ref=wave.communication_ref,
                )
            )
        events = tuple(
            sorted(
                (
                    ResolvedEvent(
                        tick=item.tick, event_type=item.type, origin="referee", payload=item.payload
                    )
                    for item in composition.events
                ),
                key=lambda item: (item.tick, item.event_type, item.origin),
            )
        )
        if any(item.tick >= scenario.time_limit_ticks for item in events):
            raise ScenarioCompileError(
                "event.out_of_range", "event reaches the time limit", file=ref.component
            )
        protected = geo.wgs84_to_local(*composition.protected_point_lonlat)
        composition_dump = composition.model_dump(mode="json")
        scenario_dump = scenario.model_copy(
            update={"scenario_id": composition.scenario_id}
        ).model_dump(mode="json")
        return build_resolved_scenario(
            {
                "scenario_id": composition.scenario_id,
                "scenario_version": composition.scenario_version,
                "category": scenario.category,
                "difficulty": scenario.difficulty,
                "formal": True,
                "package_hash": package_hash,
                "map": self._resolved_map(geo, map_cfg.offset_margin),
                "clock": ResolvedClock(
                    time_limit_ticks=scenario.time_limit_ticks, tick_seconds=1.0
                ),
                "deployments": tuple(deployments),
                "zones": zones,
                "waves": tuple(waves),
                "events": events,
                "catalog": ResolvedCatalog(
                    content_hash=repository.content_hash,
                    resource_hashes=tuple(
                        (
                            f"{item.resource_type}/{item.exact_ref}",
                            item.content_hash,
                        )
                        for item in repository.snapshot()
                    ),
                ),
                "scoring": scenario.scoring.model_dump(mode="json"),
                "adjudication": {
                    **composition.adjudication,
                    "mode": composition.mission_model,
                    "protected_point_m": list(protected),
                    "primary_entity_id": composition.primary_entity_id,
                },
                "roe": tuple(scenario.roe),
                "public_briefing": render_briefing(scenario),
                "components": {
                    "scenario": scenario_dump,
                    "composition": composition_dump,
                    "catalog": {
                        "resources": [
                            item.model_dump(mode="json") for item in repository.snapshot()
                        ]
                    },
                },
                "component_hashes": {
                    "scenario": configuration_hash(scenario_dump),
                    "composition": configuration_hash(composition_dump),
                    "catalog": repository.content_hash,
                },
                "units": _GENERIC_UNITS,
            }
        )

    @staticmethod
    def _parse_yaml(files: Mapping[str, bytes], file: str, kind: str) -> dict[str, Any]:
        if file not in files:
            raise ScenarioCompileError(
                "package.invalid", f"missing {kind} entry: {file}", file=file
            )
        try:
            raw = yaml.safe_load(files[file])
        except yaml.YAMLError as error:
            raise ScenarioCompileError(
                "package.invalid", f"{kind} YAML is malformed", file=file
            ) from error
        if not isinstance(raw, dict):
            raise ScenarioCompileError(
                "schema.invalid", f"{kind} YAML root must be an object", file=file
            )
        return raw

    @staticmethod
    def _is_id_alias(value: str, scenario_id: str) -> bool:
        """True when a referee value merely references this scenario's own ID."""
        return value == scenario_id or scenario_id.startswith(value)

    def _check_visibility(self, scenario: Scenario, file: str) -> None:
        briefing = render_briefing(scenario)
        candidates: list[tuple[str, str]] = []
        if scenario.referee.opponent_intent:
            candidates.append(("referee.opponent_intent", scenario.referee.opponent_intent))
        for key, value in scenario.referee.ground_truth.items():
            if (
                isinstance(value, str)
                and len(value) >= 6
                and not self._is_id_alias(value, scenario.scenario_id)
            ):
                candidates.append((f"referee.ground_truth.{key}", value))
        for event in scenario.referee.hidden_events:
            for key, value in event.payload.items():
                if (
                    isinstance(value, str)
                    and len(value) >= 6
                    and not self._is_id_alias(value, scenario.scenario_id)
                ):
                    candidates.append((f"referee.hidden_events.{key}", value))
        for path, secret in candidates:
            if secret in briefing:
                raise ScenarioCompileError(
                    "visibility.leak",
                    f"public briefing contains referee-only data from {path}",
                    file=file,
                    field_path=path,
                )

    def _compile_formal(
        self,
        scenario: Scenario,
        component_raw: dict[str, Any],
        package_hash: str,
        ref: ScenarioPackageRef,
    ) -> ResolvedScenario:
        scenario, component, component_id = self._parse_component(component_raw, scenario, ref)
        if ref.component is None:
            raise ScenarioCompileError(
                "package.invalid", "formal compile requires a component entry"
            )
        file = ref.component
        scale = float(component.map.legacy_scale)
        margin = float(component.map.legacy_offset_margin)
        geo = self._verify_map(component.map, scale, margin, file)

        deployments = self._md_ad_deployments(component, geo, file)
        zones = self._md_ad_zones(component, geo, file)
        waves = self._md_ad_waves(component, file)
        events = self._md_ad_events(component, file)
        repo = legacy_md_ad_catalog(component)
        catalog = ResolvedCatalog(
            content_hash=repo.content_hash,
            resource_hashes=tuple(
                (
                    item["id"],
                    repo.resource_content_hash(
                        item["resource_type"], f"{item['id']}@{item['version']}"
                    ),
                )
                for item in repo.snapshot()
            ),
        )
        clock = ResolvedClock(
            time_limit_ticks=component.adjudication.time_limit_seconds,
            tick_seconds=1.0,
        )
        adjudication = {
            "mode": component.adjudication.mode,
            "breach_threshold": component.adjudication.breach_threshold,
            "time_limit_ticks": component.adjudication.time_limit_seconds,
            "protected_point_m": list(
                geo.wgs84_to_local(component.island.lon_deg, component.island.lat_deg)
            ),
            "primary_entity_id": "red-interceptor-uav-1",
        }
        units = _MD_AD_UNITS
        scenario_version = component.config_version
        resolved_scenario_id = component.scenario_id

        self._check_mission(scenario, ref.scenario)
        self._check_scoring(scenario, ref.scenario)

        scenario_dump = self._formal_scenario_dump(scenario, component, component_id)
        component_dump = component.model_dump(mode="json")
        return build_resolved_scenario(
            {
                "scenario_id": resolved_scenario_id,
                "scenario_version": scenario_version,
                "category": scenario.category,
                "difficulty": component.difficulty,
                "formal": True,
                "package_hash": package_hash,
                "map": self._resolved_map(geo, margin),
                "clock": clock,
                "deployments": deployments,
                "zones": zones,
                "waves": waves,
                "events": events,
                "catalog": catalog,
                "scoring": component.scoring.model_dump(mode="json"),
                "adjudication": adjudication,
                "roe": tuple(scenario.roe),
                "public_briefing": render_briefing(scenario),
                "components": {
                    "scenario": scenario_dump,
                    component_id: component_dump,
                },
                "component_hashes": {
                    "scenario": configuration_hash(scenario_dump),
                    component_id: self._component_hash(component_id, component_dump),
                },
                "units": units,
            }
        )
        # formal pipeline ends here

    def _parse_component(
        self,
        raw: dict[str, Any],
        scenario: Scenario,
        ref: ScenarioPackageRef,
    ) -> tuple[Scenario, ComponentConfig, str]:
        if ref.component is None:
            raise ScenarioCompileError(
                "package.invalid", "formal compile requires a component entry"
            )
        file = ref.component
        if "map" in raw and "island" in raw:
            try:
                ad_component = MDAD002Config.model_validate(raw)
            except ValidationError as error:
                raise _schema_error("MDAD002Config", error, file=file) from error
            if scenario.scenario_id != "MD-AD-002":
                raise ScenarioCompileError(
                    "reference.mismatch",
                    f"template {scenario.scenario_id} is not for an MD-AD-002 component",
                    file=file,
                )
            return self._ad_variant_scenario(scenario, ad_component), ad_component, "md_ad_002"
        raise ScenarioCompileError("schema.invalid", "unsupported legacy component", file=file)

    @staticmethod
    def _ad_variant_scenario(scenario: Scenario, component: MDAD002Config) -> Scenario:
        """Apply the AD-002 difficulty variant onto its public template."""
        public = scenario.public.model_copy(
            update={"name": f"海空协同多波次拒止（{component.difficulty.upper()}）"}
        )
        return scenario.model_copy(
            update={
                "scenario_id": component.scenario_id,
                "difficulty": component.difficulty,
                "public": public,
            }
        )

    @staticmethod
    def _check_int_references(component: Any, file: str) -> None:
        ids = {item.id for item in component.deployments}
        for needed in ("blue-uav-1", "red-uav-1"):
            if needed not in ids:
                raise ScenarioCompileError(
                    "reference.missing",
                    f"required entity {needed} is not deployed",
                    file=file,
                    field_path="deployments",
                )

    def _verify_map(
        self,
        map_cfg: object,
        scale: float,
        margin: float,
        file: str,
    ) -> GeoFrame:
        try:
            return load_weihai_geoframe(
                map_root=self._map_root,
                expected_raw_sha256=map_cfg.raw_sha256,  # type: ignore[attr-defined]
                expected_xy_sha256=map_cfg.xy_sha256,  # type: ignore[attr-defined]
                origin_lonlat=tuple(map_cfg.origin_lonlat),  # type: ignore[attr-defined]
                legacy_scale=scale,
                offset_margin=margin,
            )
        except ValueError as error:
            raise ScenarioCompileError(
                "map.hash_mismatch",
                f"Weihai map identity/hash verification failed: {error}",
                file=file,
                field_path="map",
            ) from error
        except OSError as error:
            raise ScenarioCompileError(
                "map.unavailable",
                "Weihai map data files are missing or unreadable",
                file=file,
                field_path="map",
            ) from error

    @staticmethod
    def _resolved_map(geo: GeoFrame, margin: float) -> ResolvedMap:
        identity = geo.identity
        return ResolvedMap(
            map_id=identity.map_id,
            version=identity.version,
            raw_sha256=identity.raw_sha256,
            xy_sha256=identity.xy_sha256,
            geographic_crs=identity.geographic_crs,
            local_crs="WGS84_AEQD",
            legacy_projection=identity.legacy_projection,
            origin_lonlat=identity.origin_lonlat,
            legacy_scale=identity.legacy_scale,
            offset_xy=identity.offset_xy,
            offset_margin=margin,
            verified=True,
        )

    @staticmethod
    def _component_hash(component_id: str, dump: dict[str, Any]) -> str:
        payload = yaml.safe_dump(dump, sort_keys=True, allow_unicode=True).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _formal_scenario_dump(
        scenario: Scenario, component: ComponentConfig, component_id: str
    ) -> dict[str, Any]:
        del component, component_id
        return scenario.model_dump(mode="json")
        # chunk boundary

    def _md_int_deployments(
        self, component: Any, geo: GeoFrame, file: str
    ) -> tuple[ResolvedDeployment, ...]:
        deployments = []
        for item in sorted(component.deployments, key=lambda value: value.id):
            local = geo.wgs84_to_local(item.lon_deg, item.lat_deg)
            self._check_in_bounds(item.id, local, geo, file, f"deployments.{item.id}")
            if item.terrain != "air" and self._terrain_mismatch(
                item.terrain, geo.is_land_wgs84(item.lon_deg, item.lat_deg)
            ):
                raise ScenarioCompileError(
                    "deployment.terrain_mismatch",
                    f"deployment {item.id} terrain {item.terrain} does not match the map",
                    file=file,
                    field_path=f"deployments.{item.id}.terrain",
                )
            heading = 270.0 if item.id == "red-uav-1" else 90.0 if item.type == "uav" else 0.0
            speed = 40.0 if item.type == "uav" else 0.0
            inventory = (
                {"uav_interceptor_missile": 2}
                if item.type == "uav"
                else {"shore_ciws": 100}
                if item.type == "shore_radar"
                else {}
            )
            deployments.append(
                ResolvedDeployment(
                    entity_id=item.id,
                    side=item.side,
                    platform_type=item.type,
                    domain=_PLATFORM_DOMAINS[item.type],
                    lon_deg=item.lon_deg,
                    lat_deg=item.lat_deg,
                    position_m=(local[0], local[1], item.alt_m),
                    heading_deg=heading,
                    speed_mps=speed,
                    weapon_inventory=inventory,
                    terrain=item.terrain,
                )
            )
        return tuple(deployments)

    def _md_ad_deployments(
        self, component: MDAD002Config, geo: GeoFrame, file: str
    ) -> tuple[ResolvedDeployment, ...]:
        deployments = []
        for item in sorted(component.deployments, key=lambda value: value.id):
            local = geo.wgs84_to_local(item.lon_deg, item.lat_deg)
            self._check_in_bounds(item.id, local, geo, file, f"deployments.{item.id}")
            on_land = geo.is_land_wgs84(item.lon_deg, item.lat_deg)
            if self._terrain_mismatch(item.terrain, on_land):
                raise ScenarioCompileError(
                    "deployment.terrain_mismatch",
                    f"deployment {item.id} terrain {item.terrain} does not match the map",
                    file=file,
                    field_path=f"deployments.{item.id}.terrain",
                )
            platform_type = _AD2_PLATFORM_TYPES[item.platform]
            weapon = _AD2_INVENTORY_WEAPONS.get(item.platform)
            deployments.append(
                ResolvedDeployment(
                    entity_id=item.id,
                    side="red",
                    platform_type=platform_type,
                    domain=_PLATFORM_DOMAINS[platform_type],
                    lon_deg=item.lon_deg,
                    lat_deg=item.lat_deg,
                    position_m=(local[0], local[1], item.altitude_m),
                    heading_deg=item.heading_deg,
                    speed_mps=item.speed_mps,
                    weapon_inventory=({weapon: item.inventory} if weapon is not None else {}),
                    terrain=item.terrain,
                )
            )
        return tuple(deployments)
        # chunk boundary

    def _md_ad_zones(
        self, component: MDAD002Config, geo: GeoFrame, file: str
    ) -> tuple[ResolvedZone, ...]:
        zones = [
            ResolvedZone(
                zone_id="denial",
                kind="denial",
                lon_deg=component.denial_zone.lon_deg,
                lat_deg=component.denial_zone.lat_deg,
                centre_m=geo.wgs84_to_local(
                    component.denial_zone.lon_deg, component.denial_zone.lat_deg
                ),
                radius_m=component.denial_zone.radius,
            )
        ]
        for name in sorted(component.spawn_zone_geometry):
            zone = component.spawn_zone_geometry[name]
            centre = geo.wgs84_to_local(zone.lon_deg, zone.lat_deg)
            self._check_in_bounds(name, centre, geo, file, f"spawn_zone_geometry.{name}")
            zones.append(
                ResolvedZone(
                    zone_id=name,
                    kind="spawn",
                    lon_deg=zone.lon_deg,
                    lat_deg=zone.lat_deg,
                    centre_m=centre,
                    half_width_m=zone.half_width_m,
                )
            )
        return tuple(zones)

    def _md_ad_waves(self, component: MDAD002Config, file: str) -> tuple[ResolvedWave, ...]:
        limit = component.adjudication.time_limit_seconds
        waves = []
        for item in sorted(component.waves, key=lambda value: (value.time_seconds, value.id)):
            if not item.time_seconds + item.time_jitter_seconds < limit:
                raise ScenarioCompileError(
                    "wave.out_of_range",
                    f"wave {item.id} ends at or beyond the time limit",
                    file=file,
                    field_path=f"waves.{item.id}",
                )
            waves.append(
                ResolvedWave(
                    wave_id=item.id,
                    count=item.count,
                    base_tick=item.time_seconds,
                    jitter_ticks=item.time_jitter_seconds,
                    behavior=item.behavior,
                    altitude_min_m=item.altitude_min_m,
                    altitude_max_m=item.altitude_max_m,
                )
            )
        return tuple(waves)

    @staticmethod
    def _md_ad_events(component: MDAD002Config, file: str) -> tuple[ResolvedEvent, ...]:
        limit = component.adjudication.time_limit_seconds
        events = []
        for item in component.difficulty_events:
            if not 0 <= item.tick < limit:
                raise ScenarioCompileError(
                    "event.out_of_range",
                    f"difficulty event at tick {item.tick} is outside the mission",
                    file=file,
                    field_path="difficulty_events",
                )
            events.append(
                ResolvedEvent(
                    tick=item.tick,
                    event_type=f"difficulty_{item.component}",
                    origin="difficulty",
                    payload={
                        "component": item.component,
                        "mode": item.mode,
                        "duration_seconds": item.duration_seconds,
                    },
                )
            )
        return tuple(
            sorted(
                events,
                key=lambda value: (value.tick, value.event_type, value.origin),
            )
        )

    def _check_in_bounds(
        self,
        label: str,
        position: tuple[float, float],
        geo: GeoFrame,
        file: str,
        field_path: str,
    ) -> None:
        min_x, min_y, max_x, max_y = geo.visualization_layers.bounds(padding_fraction=0.0)
        if not min_x <= position[0] <= max_x or not min_y <= position[1] <= max_y:
            raise ScenarioCompileError(
                "bounds.out_of_map",
                f"{label} is outside the Weihai map bounds",
                file=file,
                field_path=field_path,
            )

    @staticmethod
    def _terrain_mismatch(terrain: str, on_land: bool) -> bool:
        if terrain == "land":
            return not on_land
        if terrain == "water":
            return on_land
        return False

    @staticmethod
    def _check_mission(scenario: Scenario, file: str) -> None:
        if not scenario.success_conditions or not scenario.failure_conditions:
            raise ScenarioCompileError(
                "mission.incomplete",
                "success and failure conditions are both required",
                file=file,
                field_path="mission",
            )

    @staticmethod
    def _check_scoring(scenario: Scenario, file: str) -> None:
        weights = scenario.scoring.weights
        if not weights:
            raise ScenarioCompileError(
                "scoring.invalid", "scoring requires at least one weight", file=file
            )
        if not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ScenarioCompileError(
                "scoring.invalid",
                "scoring weights must normalise to 1.0",
                file=file,
                field_path="scoring.weights",
            )
        # chunk boundary

    def _compile_generic(
        self, scenario: Scenario, package_hash: str, file: str
    ) -> ResolvedScenario:
        bounds = scenario.world.bounds
        deployments = []
        for item in sorted(scenario.entities, key=lambda value: value.id):
            position = item.position
            if not (
                bounds[0] <= position[0] <= bounds[2] and bounds[1] <= position[1] <= bounds[3]
            ):
                raise ScenarioCompileError(
                    "bounds.out_of_world",
                    f"entity {item.id} is outside the world bounds",
                    file=file,
                    field_path=f"entities.{item.id}.position",
                )
            deployments.append(
                ResolvedDeployment(
                    entity_id=item.id,
                    side="blue" if item.side is Side.BLUE else "red",
                    platform_type=item.type,
                    domain=_PLATFORM_DOMAINS[item.type],
                    position_m=(
                        float(position[0]),
                        float(position[1]),
                        float(position[2]),
                    ),
                    heading_deg=0.0,
                    speed_mps=0.0,
                    terrain=None,
                )
            )
        events: list[ResolvedEvent] = []
        for event in scenario.weather_timeline:
            events.append(
                ResolvedEvent(
                    tick=event.tick,
                    event_type=event.event_type,
                    origin="weather",
                    payload=dict(event.payload),
                )
            )
        for hidden in scenario.referee.hidden_events:
            events.append(
                ResolvedEvent(
                    tick=hidden.tick,
                    event_type=hidden.event_type,
                    origin="referee",
                    payload=dict(hidden.payload),
                )
            )
        limit = scenario.time_limit_ticks
        for scheduled in events:
            if not 0 <= scheduled.tick < limit:
                raise ScenarioCompileError(
                    "event.out_of_range",
                    f"event at tick {scheduled.tick} is outside the mission",
                    file=file,
                    field_path="weather_timeline|referee.hidden_events",
                )
        self._check_mission(scenario, file)
        self._check_scoring(scenario, file)
        return build_resolved_scenario(
            {
                "scenario_id": scenario.scenario_id,
                "scenario_version": "1.0",
                "category": scenario.category,
                "difficulty": scenario.difficulty,
                "formal": False,
                "package_hash": package_hash,
                "map": ResolvedMap(
                    map_id=scenario.world.map_id,
                    version="unversioned",
                    raw_sha256=None,
                    xy_sha256=None,
                    geographic_crs="EPSG:4326",
                    local_crs="local_metre",
                    legacy_projection=None,
                    origin_lonlat=(0.0, 0.0),
                    legacy_scale=1.0,
                    offset_xy=(0.0, 0.0),
                    verified=False,
                ),
                "clock": ResolvedClock(
                    time_limit_ticks=limit,
                    tick_seconds=1.0,
                ),
                "deployments": tuple(deployments),
                "zones": (),
                "waves": (),
                "events": tuple(
                    sorted(
                        events,
                        key=lambda value: (value.tick, value.event_type, value.origin),
                    )
                ),
                "catalog": None,
                "scoring": scenario.scoring.model_dump(mode="json"),
                "adjudication": {"time_limit_ticks": limit},
                "roe": tuple(scenario.roe),
                "public_briefing": render_briefing(scenario),
                "components": {"scenario": scenario.model_dump(mode="json")},
                "component_hashes": {
                    "scenario": configuration_hash(scenario.model_dump(mode="json"))
                },
                "units": _GENERIC_UNITS,
            }
        )
        # generic pipeline ends here

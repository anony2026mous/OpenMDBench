"""Generic, safe, deterministic declarative scenario compilation for schema v2."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import stat
import string
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass, replace
from dataclasses import field as dataclass_field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Literal, NoReturn, Self, cast

import yaml
from pydantic import ValidationError
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, AnchorToken

from openmdbench.catalog.v2 import (
    CatalogResolutionErrorV2,
    CatalogResourceV2,
    CatalogV2,
    EntityCompositionV2,
    ModelFactoryMetadataV2,
    ResourceTypeV2,
)
from openmdbench.map_terrain_v2 import (
    MapTerrainErrorV2,
    MapTerrainV2,
    load_map_terrain_v2,
)
from openmdbench.schemas.core_v2 import (
    EntitySpecV2,
    EventSpecV2,
    FactionV2,
    InitialStateV2,
    MissionRuleV2,
    RelationshipV2,
    RoePolicyV2,
    ScoreMetricV2,
    SpatialDamagePolicyV2,
    WorldSpecV2,
    ZoneV2,
)

COMPILER_VERSION = "2.0.0"
COMPILER_STAGES_V2 = (
    "schema",
    "resource_versions",
    "defaults",
    "units",
    "factions_relationships",
    "formation_expansion",
    "compatibility",
    "coordinates",
    "boundary_deployment",
    "event_dependencies",
    "mission_scoring_controllers",
    "visibility",
    "stable_order",
    "freeze_hash",
)
STAGE_FAILURE_POLICY_V2 = "first_stage_then_file_path"


@dataclass(frozen=True, slots=True)
class StageRecordV2:
    stage: str
    ordinal: int
    status: str = "completed"
    duration_policy: str = "deterministic-none"


@dataclass(frozen=True, slots=True)
class PipelineContextV2:
    package: ScenarioPackageV2
    compiler: ScenarioCompilerV2
    completed_stages: tuple[str, ...] = ()
    resolved: ResolvedScenarioV2 | None = None
    parsed_schema: Mapping[str, Any] | None = None
    event_declarations: Any = None
    event_resource_bindings: Any = None
    event_spawn_entities: Any = None
    mission_declarations: Any = None
    visibility_declarations: Any = None
    extended_mission_control: bool = False
    resolved_resources: Any = None
    materialized_defaults: Any = None
    normalized_units: Any = None
    factions: Any = None
    relationships: Any = None
    expanded_entities: Any = None
    formation_ids: Any = None
    expanded_entity_count: int = 0
    validated_compositions: Any = None
    normalized_world: Any = None
    normalized_coordinates: Any = None
    coordinate_deployments: Any = None
    validated_world: Any = None
    validated_entities: Any = None
    validated_deployments: Any = None
    validated_events: Any = None
    validated_mission: Any = None
    validated_controllers: Any = None
    validated_visibility: Any = None
    ordered_ir: Any = None
    artifact_hash: str = ""
    package_logical_hash: str = ""
    package_content_hash: str = ""
    package_archive_hash: str = ""
    audit_hashes: Any = None
    scenario_id: str = ""
    catalog_hash: str = ""
    model_registry_hash: str = ""
    model_registry_snapshot: Any = None
    world_map_binding: Any = None
    mission_states: Any = None
    score_metrics: Any = None
    scoring: Any = None
    controller_policy: str | None = None


@dataclass(frozen=True, slots=True)
class PackageLimitsV2:
    max_entries: int = 128
    max_entry_bytes: int = 4 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024
    max_yaml_depth: int = 64
    max_yaml_nodes: int = 100_000
    max_yaml_aliases: int = 0
    max_compression_ratio: float = 100.0


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(_json_value(value)).encode()).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_freeze(item) for item in value)
    return value


class CompilerErrorV2(ValueError):
    """Stable package/compiler diagnostic with a machine-readable location."""

    def __init__(
        self,
        code: str,
        *,
        file: str,
        path: tuple[str, ...],
        value: Any,
        reason: str,
        suggestion: str,
        stage: str | None = None,
        trace: tuple[StageRecordV2, ...] = (),
    ) -> None:
        self.code = code
        self.file = file
        self.path = path
        self.value = value
        self.reason = reason
        self.suggestion = suggestion
        self.stage = stage
        self.trace = trace
        super().__init__(f"[{code}] {file}:{'.'.join(path)}: {reason}")


class _ResolvedIntegrityError(ValueError):
    def __init__(self, reason: str) -> None:
        self.code = "resolved.integrity_invalid"
        super().__init__(f"[resolved.integrity_invalid] {reason}")


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueSafeLoader, node: MappingNode, deep: bool = False
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _package_error(file: str, reason: str, *, code: str = "package.invalid") -> CompilerErrorV2:
    return CompilerErrorV2(
        code,
        file=file,
        path=(),
        value=file,
        reason=reason,
        suggestion="use unique relative UTF-8 YAML entries containing data only",
    )


def _safe_yaml(data: bytes, file: str, limits: PackageLimitsV2 | None = None) -> Mapping[str, Any]:
    limits = limits or PackageLimitsV2()
    try:
        text = data.decode("utf-8")
        if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)):
            raise _package_error(
                file,
                "YAML aliases and anchors are not supported",
                code="package.yaml_alias_forbidden",
            )
        # `_UniqueSafeLoader` subclasses SafeLoader only to reject duplicate keys;
        # it does not enable Python/object constructors.
        loaded = yaml.load(text, Loader=_UniqueSafeLoader)  # nosec B506
    except CompilerErrorV2:
        raise
    except UnicodeDecodeError as error:
        raise _package_error(file, "entry is not UTF-8", code="package.encoding_invalid") from error
    except ConstructorError as error:
        code = (
            "package.duplicate_key"
            if "duplicate key" in str(error)
            else "package.yaml_tag_forbidden"
        )
        raise _package_error(file, f"unsafe or invalid YAML: {error}", code=code) from error
    except yaml.YAMLError as error:
        code = "package.yaml_tag_forbidden" if "constructor" in str(error) else "package.invalid"
        raise _package_error(file, f"unsafe or invalid YAML: {error}", code=code) from error
    if not isinstance(loaded, Mapping):
        raise _package_error(file, "YAML document must be a mapping")
    if any(not isinstance(key, str) for key in loaded):
        raise _package_error(file, "YAML mapping keys must be strings")
    stack: list[tuple[Any, int]] = [(loaded, 1)]
    node_count = 0
    while stack:
        value, depth = stack.pop()
        node_count += 1
        if depth > limits.max_yaml_depth:
            raise _package_error(
                file, "YAML depth limit exceeded", code="package.yaml_depth_exceeded"
            )
        if node_count > limits.max_yaml_nodes:
            raise _package_error(
                file, "YAML node limit exceeded", code="package.yaml_nodes_exceeded"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise _package_error(file, "YAML numeric values must be finite")
        if isinstance(value, Mapping):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            stack.extend((item, depth + 1) for item in value)
    return dict(loaded)


def _entry_name(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:[/\\]", name)
        or "\\" in name
        or ".." in path.parts
        or path.as_posix() != name
    ):
        raise _package_error(name or "<entry>", "entry path escapes package root")
    if path.suffix not in {".yaml", ".yml"}:
        raise _package_error(name, "only YAML package entries are accepted")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class ScenarioPackageV2:
    """Normalized semantic document plus separate source/archive provenance."""

    document: Mapping[str, Any]
    logical_hash: str
    content_hash: str
    archive_hash: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> Self:
        if payload.get("adapter_id") not in {None, "adapter.v2"}:
            raise _package_error(
                "scenario.yaml", "adapter is not allowlisted", code="package.adapter_unknown"
            )
        if payload.get("schema_version") != "package@2.0":
            raise _package_error("scenario.yaml", "unsupported package schema version")
        scenario = payload.get("scenario")
        if not isinstance(scenario, Mapping):
            raise _package_error("scenario.yaml", "single-file package requires scenario")
        return cls._from_document(dict(scenario), (("scenario.yaml", _canonical_json(payload)),))

    @classmethod
    def from_entries(
        cls,
        entries: Iterable[tuple[str, bytes]],
        *,
        limits: PackageLimitsV2 | None = None,
    ) -> Self:
        limits = limits or PackageLimitsV2()
        documents: dict[str, Mapping[str, Any]] = {}
        archive: list[tuple[str, str]] = []
        total = 0
        materialized = list(entries)
        if len(materialized) > limits.max_entries:
            raise _package_error(
                "<package>", "entry count limit exceeded", code="package.entry_count_exceeded"
            )
        for raw_name, data in materialized:
            name = _entry_name(raw_name)
            if name in documents:
                raise _package_error(name, "duplicate package entry", code="package.duplicate")
            if len(data) > limits.max_entry_bytes:
                raise _package_error(
                    name, "entry size limit exceeded", code="package.entry_size_exceeded"
                )
            total += len(data)
            if total > limits.max_total_bytes:
                raise _package_error(
                    name, "total size limit exceeded", code="package.total_size_exceeded"
                )
            documents[name] = _safe_yaml(data, name, limits)
            archive.append((name, hashlib.sha256(data).hexdigest()))
        if "scenario.yaml" not in documents:
            raise _package_error("scenario.yaml", "package manifest is missing")
        return cls._from_documents(documents, tuple(archive))

    @classmethod
    def from_directory(cls, root: Path, *, limits: PackageLimitsV2 | None = None) -> Self:
        limits = limits or PackageLimitsV2()
        root = root.resolve()
        manifest = root / "scenario.yaml"
        if manifest.is_symlink():
            raise _package_error(
                "scenario.yaml", "directory symlink forbidden", code="package.directory_symlink"
            )
        if not manifest.is_file():
            raise _package_error("scenario.yaml", "package manifest is missing")
        manifest_document = _safe_yaml(manifest.read_bytes(), "scenario.yaml", limits)
        includes = manifest_document.get("includes", ())
        if not isinstance(includes, Sequence) or isinstance(includes, (str, bytes)):
            raise _package_error("scenario.yaml", "includes must be a list")
        names = ("scenario.yaml", *(str(item) for item in includes))
        entries: list[tuple[str, bytes]] = []
        for raw_name in names:
            name = _entry_name(raw_name)
            unresolved = root / name
            if unresolved.is_symlink():
                raise _package_error(
                    name, "directory symlink forbidden", code="package.directory_symlink"
                )
            candidate = unresolved.resolve()
            if root not in candidate.parents:
                raise _package_error(name, "include escapes package root")
            if not candidate.is_file():
                raise _package_error(name, "included file is missing")
            entries.append((name, candidate.read_bytes()))
        return cls.from_entries(entries, limits=limits)

    @classmethod
    def from_archive(cls, data: bytes, *, limits: PackageLimitsV2 | None = None) -> Self:
        limits = limits or PackageLimitsV2()
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                if len(infos) > limits.max_entries:
                    raise _package_error(
                        "<archive>",
                        "entry count limit exceeded",
                        code="package.entry_count_exceeded",
                    )
                names: set[str] = set()
                entries: list[tuple[str, bytes]] = []
                total = 0
                for info in infos:
                    try:
                        name = _entry_name(info.filename)
                    except CompilerErrorV2 as error:
                        raise _package_error(
                            info.filename, error.reason, code="package.archive_path_invalid"
                        ) from error
                    if name in names:
                        raise _package_error(
                            name, "duplicate archive path", code="package.archive_duplicate"
                        )
                    names.add(name)
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise _package_error(
                            name, "archive symlink forbidden", code="package.archive_symlink"
                        )
                    if info.flag_bits & 1:
                        raise _package_error(
                            name, "encrypted archive forbidden", code="package.archive_encrypted"
                        )
                    ratio = info.file_size / max(info.compress_size, 1)
                    if ratio > limits.max_compression_ratio:
                        raise _package_error(
                            name,
                            "compression ratio exceeded",
                            code="package.archive_ratio_exceeded",
                        )
                    if info.file_size > limits.max_entry_bytes:
                        raise _package_error(
                            name, "entry size limit exceeded", code="package.entry_size_exceeded"
                        )
                    total += info.file_size
                    if total > limits.max_total_bytes:
                        raise _package_error(
                            name, "total size limit exceeded", code="package.total_size_exceeded"
                        )
                    entries.append((name, archive.read(info)))
        except CompilerErrorV2:
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise _package_error(
                "<archive>", "archive is corrupt", code="package.archive_corrupt"
            ) from error
        return cls.from_entries(entries, limits=limits)

    @classmethod
    def _from_documents(
        cls,
        documents: Mapping[str, Mapping[str, Any]],
        archive: tuple[tuple[str, str], ...],
    ) -> Self:
        manifest = documents["scenario.yaml"]
        roles = manifest.get("roles", {})
        allowed_roles = {
            "entities",
            "formations",
            "world",
            "events",
            "mission",
            "scoring",
            "controllers",
            "visibility",
        }
        if isinstance(roles, Mapping) and any(role not in allowed_roles for role in roles):
            raise _package_error(
                "scenario.yaml", "unknown package role", code="package.role_unknown"
            )
        if manifest.get("schema_version") != "package@2.0":
            raise _package_error("scenario.yaml", "unsupported package schema version")
        embedded = manifest.get("scenario")
        if isinstance(embedded, Mapping):
            return cls._from_document(dict(embedded), archive)
        scenario: dict[str, Any] = {
            "schema_version": "2.0",
            "scenario_id": manifest.get("scenario_id"),
            "display_name": manifest.get("display_name"),
        }
        includes = manifest.get("includes", ())
        if not isinstance(includes, Sequence) or isinstance(includes, (str, bytes)):
            raise _package_error("scenario.yaml", "includes must be a list")
        for raw_name in includes:
            name = _entry_name(str(raw_name))
            if name not in documents:
                raise _package_error(name, "included entry is missing")
            for key, value in documents[name].items():
                if key in scenario:
                    raise _package_error(name, f"duplicate semantic section: {key}")
                scenario[key] = value
        return cls._from_document(scenario, archive)

    @classmethod
    def _from_document(
        cls, document: Mapping[str, Any], archive: tuple[tuple[str, str], ...]
    ) -> Self:
        semantic = dict(document)
        logical = dict(semantic)
        logical.pop("display_name", None)
        logical.pop("scenario_id", None)
        logical_hash = _digest(logical)
        return cls(
            document=_freeze(semantic),
            logical_hash=logical_hash,
            content_hash=logical_hash,
            archive_hash=_digest(sorted(archive)),
        )


@dataclass(frozen=True, slots=True)
class _CoordinateFrameV2:
    canonical_frame: str
    origin_wgs84: tuple[float, ...]
    axis_orientation: str
    height_semantics: str
    local_bounds_m: tuple[tuple[float, ...], tuple[float, ...]]
    tolerance_m: float


@dataclass(frozen=True, slots=True)
class _ZoneGeometryV2:
    type: str
    positions_m: tuple[tuple[float, ...], ...] = ()
    center_m: tuple[float, ...] | None = None
    radius_m: float | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedZoneV2:
    id: str
    geometry: _ZoneGeometryV2
    domains: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ResolvedBoundaryV2:
    id: str
    zone_id: str
    action: str
    point_on_edge: str
    priority: int = 0


@dataclass(frozen=True, slots=True)
class _ResolvedWorldV2:
    coordinate_system: str
    map_ref: str | None
    zones: tuple[ZoneV2 | _ResolvedZoneV2, ...]
    boundary_policy: str | None
    spatial_damage_policy: SpatialDamagePolicyV2 | None = None
    roe_rules: tuple[RoePolicyV2, ...] = ()
    coordinate_frame: _CoordinateFrameV2 | None = None
    map_transform: Mapping[str, Any] | None = None
    boundaries: tuple[_ResolvedBoundaryV2, ...] = ()
    duration_ticks: int | None = None
    tick_seconds: float | None = None
    deployment_excluded_zone_ids: tuple[str, ...] = ()

    @classmethod
    def from_spec(cls, world: WorldSpecV2) -> Self:
        return cls(
            coordinate_system=world.coordinate_system,
            map_ref=world.map_ref,
            zones=world.zones,
            boundary_policy=world.boundary_policy,
            spatial_damage_policy=world.spatial_damage_policy,
            roe_rules=world.roe_rules,
            duration_ticks=world.duration_ticks,
            tick_seconds=world.tick_seconds,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> Self:
        coordinate_frame = payload.get("coordinate_frame")
        if isinstance(coordinate_frame, Mapping):
            zones = tuple(
                _ResolvedZoneV2(
                    id=str(item["id"]),
                    geometry=_ZoneGeometryV2(
                        type=str(item["geometry"]["type"]),
                        positions_m=tuple(
                            tuple(float(axis) for axis in point)
                            for point in item["geometry"].get("positions_m", ())
                        ),
                        center_m=(
                            None
                            if item["geometry"].get("center_m") is None
                            else tuple(float(axis) for axis in item["geometry"]["center_m"])
                        ),
                        radius_m=item["geometry"].get("radius_m"),
                    ),
                    domains=tuple(str(value) for value in item.get("domains", ())),
                    tags=tuple(str(value) for value in item.get("tags", ())),
                )
                for item in payload.get("zones", ())
            )
            frame = _CoordinateFrameV2(
                canonical_frame=str(coordinate_frame["canonical_frame"]),
                origin_wgs84=tuple(coordinate_frame["origin_wgs84"]),
                axis_orientation=str(coordinate_frame["axis_orientation"]),
                height_semantics=str(coordinate_frame["height_semantics"]),
                local_bounds_m=cast(
                    tuple[tuple[float, ...], tuple[float, ...]],
                    tuple(tuple(item) for item in coordinate_frame["local_bounds_m"]),
                ),
                tolerance_m=float(coordinate_frame["tolerance_m"]),
            )
            boundaries = tuple(
                _ResolvedBoundaryV2(
                    id=str(item["id"]),
                    zone_id=str(item["zone_id"]),
                    action=str(item["action"]),
                    point_on_edge=str(item["point_on_edge"]),
                    priority=int(item.get("priority", 0)),
                )
                for item in payload.get("boundaries", ())
            )
            map_transform = payload.get("map_transform")
            return cls(
                coordinate_system="local_m",
                map_ref=(None if payload.get("map_ref") is None else str(payload.get("map_ref"))),
                zones=zones,
                boundary_policy=payload.get("boundary_policy"),
                spatial_damage_policy=(
                    None
                    if payload.get("spatial_damage_policy") is None
                    else SpatialDamagePolicyV2.model_validate(payload["spatial_damage_policy"])
                ),
                roe_rules=tuple(
                    RoePolicyV2.model_validate(item) for item in payload.get("roe_rules", ())
                ),
                coordinate_frame=frame,
                map_transform=(
                    _freeze(map_transform) if isinstance(map_transform, Mapping) else None
                ),
                boundaries=boundaries,
                duration_ticks=payload.get("duration_ticks"),
                tick_seconds=payload.get("tick_seconds"),
                deployment_excluded_zone_ids=tuple(
                    str(item) for item in payload.get("deployment_excluded_zone_ids", ())
                ),
            )
        return cls.from_spec(WorldSpecV2.model_validate(payload))

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        del mode
        payload: dict[str, Any] = {
            "schema_version": "2.0",
            "coordinate_system": self.coordinate_system,
            "map_ref": self.map_ref,
            "zones": _json_value(self.zones),
            "boundary_policy": self.boundary_policy,
            "spatial_damage_policy": _json_value(self.spatial_damage_policy),
            "roe_rules": _json_value(self.roe_rules),
            "duration_ticks": self.duration_ticks,
            "tick_seconds": self.tick_seconds,
        }
        if self.coordinate_frame is not None:
            payload["coordinate_frame"] = _json_value(self.coordinate_frame)
            payload["map_transform"] = _json_value(self.map_transform)
            payload["boundaries"] = _json_value(self.boundaries)
            payload["deployment_excluded_zone_ids"] = list(self.deployment_excluded_zone_ids)
        return payload


@dataclass(frozen=True, slots=True)
class _ModelEvidenceV2:
    model_ref: str
    artifact_sha256: str
    interface_version: str
    input_schema: str
    output_schema: str
    trusted: bool
    deterministic: bool
    resource_types: tuple[ResourceTypeV2, ...]


@dataclass(frozen=True, slots=True)
class _DefaultSourceV2:
    kind: str
    id: str


@dataclass(frozen=True, slots=True)
class _DefaultEvidenceV2:
    value: Any
    unit: str
    source: _DefaultSourceV2
    input_value: Any
    input_unit: str
    conversion_ref: str | None
    conversion_scale: float | None
    value_type: str | None


@dataclass(frozen=True, slots=True)
class ResolvedResourceBindingV2:
    schema_version: str
    exact_ref: str
    resource_type: ResourceTypeV2
    id: str
    version: str
    engine_compatibility: str
    content_hash: str
    model_ref: str
    model_evidence: _ModelEvidenceV2
    dependencies: tuple[str, ...]
    content: Mapping[str, Any]
    normalized_content: Mapping[str, Any]
    units: Mapping[str, str]
    field_units: Mapping[str, str]
    defaults: Mapping[str, _DefaultEvidenceV2]


@dataclass(frozen=True, slots=True)
class ResolvedSpatialEffectPolicyV2:
    """Immutable resolved resource chain for spatially generated damage."""

    effect_binding: ResolvedResourceBindingV2
    damage_binding: ResolvedResourceBindingV2
    magnitude_model: str
    magnitude_parameters: Mapping[str, float]
    output_unit: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ResolvedSpatialEffectPolicyV2:
        if set(value) != {
            "effect_binding",
            "damage_binding",
            "magnitude_model",
            "magnitude_parameters",
            "output_unit",
        }:
            raise ValueError("spatial effect policy fields are invalid")
        return cls(
            effect_binding=_resolved_binding_from_json(value["effect_binding"]),
            damage_binding=_resolved_binding_from_json(value["damage_binding"]),
            magnitude_model=str(value["magnitude_model"]),
            magnitude_parameters=_freeze(value["magnitude_parameters"]),
            output_unit=str(value["output_unit"]),
        )


def _resolved_binding_from_json(binding: Mapping[str, Any]) -> ResolvedResourceBindingV2:
    return ResolvedResourceBindingV2(
        schema_version=str(binding["schema_version"]),
        exact_ref=str(binding["exact_ref"]),
        resource_type=cast(ResourceTypeV2, binding["resource_type"]),
        id=str(binding["id"]),
        version=str(binding["version"]),
        engine_compatibility=str(binding["engine_compatibility"]),
        content_hash=str(binding["content_hash"]),
        model_ref=str(binding["model_ref"]),
        model_evidence=_ModelEvidenceV2(
            model_ref=str(binding["model_evidence"]["model_ref"]),
            artifact_sha256=str(binding["model_evidence"]["artifact_sha256"]),
            interface_version=str(binding["model_evidence"]["interface_version"]),
            input_schema=str(binding["model_evidence"]["input_schema"]),
            output_schema=str(binding["model_evidence"]["output_schema"]),
            trusted=bool(binding["model_evidence"]["trusted"]),
            deterministic=bool(binding["model_evidence"]["deterministic"]),
            resource_types=tuple(binding["model_evidence"]["resource_types"]),
        ),
        dependencies=tuple(binding["dependencies"]),
        content=_freeze(binding["content"]),
        normalized_content=_freeze(binding["normalized_content"]),
        units=_freeze(binding["units"]),
        field_units=_freeze(binding["field_units"]),
        defaults=MappingProxyType(
            {
                str(key): _DefaultEvidenceV2(
                    value=_freeze(value["value"]),
                    unit=str(value["unit"]),
                    source=_DefaultSourceV2(
                        kind=str(value["source"]["kind"]),
                        id=str(value["source"]["id"]),
                    ),
                    input_value=_freeze(value["input_value"]),
                    input_unit=str(value["input_unit"]),
                    conversion_ref=(
                        None if value["conversion_ref"] is None else str(value["conversion_ref"])
                    ),
                    conversion_scale=(
                        None
                        if value["conversion_scale"] is None
                        else float(value["conversion_scale"])
                    ),
                    value_type=(None if value["value_type"] is None else str(value["value_type"])),
                )
                for key, value in binding["defaults"].items()
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class _RuntimeInitialV2:
    initial_state: InitialStateV2
    ammunition: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class _FrozenRecordV2:
    values: Mapping[str, Any]

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        del mode
        return cast(dict[str, Any], _json_value(self.values))


def _record(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenRecordV2(
            MappingProxyType({str(key): _record(item) for key, item in value.items()})
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_record(item) for item in value)
    return value


def _mission_rule_record(value: Mapping[str, Any]) -> _FrozenRecordV2:
    payload = dict(value)
    outcome = payload.get("outcome")
    if isinstance(outcome, Mapping):
        outcome_values = dict(outcome)
        ranking = outcome_values.get("ranking", {})
        outcome_values["ranking"] = MappingProxyType(dict(ranking))
        payload["outcome"] = _FrozenRecordV2(
            MappingProxyType(
                {
                    key: (_record(item) if key != "ranking" else item)
                    for key, item in outcome_values.items()
                }
            )
        )
    return cast(_FrozenRecordV2, _record(payload))


_MISSION_RUNTIME_OPERATORS_V2 = frozenset(
    {
        "zone",
        "state",
        "count",
        "survival",
        "time",
        "event",
        "wave",
        "contact",
        "communication",
        "resource",
        "score",
        "all",
        "any",
        "not",
    }
)


def _validated_mission_parameters_v2(
    operator: Any,
    parameters: Any,
    *,
    states: set[str],
    event_ids: set[str],
    zone_ids: set[str],
    entity_ids: set[str],
    metric_ids: set[str],
) -> dict[str, Any]:
    """Validate and canonicalize one compiled mission condition parameter tree."""

    if operator not in _MISSION_RUNTIME_OPERATORS_V2 or not isinstance(parameters, Mapping):
        raise ValueError("mission operator or parameter container is invalid")
    values = cast(dict[str, Any], _json_value(parameters))
    comparisons = {">=", ">", "==", "<=", "<"}

    def exact(fields: set[str]) -> bool:
        return set(values) == fields

    if operator in {"count", "survival"}:
        expected_fields = {"comparison", "value"}
        if operator == "count" and "zone_id" in values:
            expected_fields.add("zone_id")
        if not (
            exact(expected_fields)
            and values.get("comparison") in comparisons
            and isinstance(values.get("value"), int)
            and not isinstance(values.get("value"), bool)
            and int(values["value"]) >= 0
            and (
                "zone_id" not in values
                or isinstance(values.get("zone_id"), str)
                and values["zone_id"] in zone_ids
            )
        ):
            raise ValueError("count or survival parameters are invalid")
    elif operator == "state":
        if not exact({"state"}) or values.get("state") not in states:
            raise ValueError("mission state endpoint is invalid")
    elif operator in {"event", "wave"}:
        field = "event_id" if operator == "event" else "wave_id"
        if not exact({field}) or values.get(field) not in event_ids:
            raise ValueError("mission event endpoint is invalid")
    elif operator == "time":
        if not (
            exact({"comparison", "tick"})
            and values.get("comparison") in comparisons
            and isinstance(values.get("tick"), int)
            and not isinstance(values.get("tick"), bool)
            and int(values["tick"]) >= 0
        ):
            raise ValueError("mission time parameters are invalid")
    elif operator == "zone":
        if not (
            set(values) in ({"zone_id"}, {"zone_id", "transition"})
            and values.get("zone_id") in zone_ids
            and values.get("transition", "entered") in {"entered", "left", "inside", "outside"}
        ):
            raise ValueError("mission zone parameters are invalid")
        values.setdefault("transition", "entered")
    elif operator == "contact":
        if not (
            set(values) in ({"minimum_count"}, {"minimum_count", "maximum_age_ticks"})
            and isinstance(values.get("minimum_count"), int)
            and not isinstance(values.get("minimum_count"), bool)
            and int(values["minimum_count"]) >= 0
            and isinstance(values.get("maximum_age_ticks", 0), int)
            and not isinstance(values.get("maximum_age_ticks", 0), bool)
            and int(values.get("maximum_age_ticks", 0)) >= 0
        ):
            raise ValueError("mission contact parameters are invalid")
    elif operator == "communication":
        if not (
            set(values) in ({"minimum_count"}, {"minimum_count", "owner_entity_id"})
            and isinstance(values.get("minimum_count"), int)
            and not isinstance(values.get("minimum_count"), bool)
            and int(values["minimum_count"]) >= 0
            and ("owner_entity_id" not in values or values.get("owner_entity_id") in entity_ids)
        ):
            raise ValueError("mission communication parameters are invalid")
    elif operator == "resource":
        if not (
            exact({"resource_ref", "field", "comparison", "value", "unit"})
            and isinstance(values.get("resource_ref"), str)
            and "@" in values["resource_ref"]
            and isinstance(values.get("field"), str)
            and bool(values["field"])
            and values.get("comparison") in comparisons
            and isinstance(values.get("value"), (int, float))
            and not isinstance(values.get("value"), bool)
            and math.isfinite(float(values["value"]))
            and isinstance(values.get("unit"), str)
            and bool(values["unit"])
        ):
            raise ValueError("mission resource parameters are invalid")
    elif operator == "score":
        if not (
            exact({"metric_id", "comparison", "value"})
            and values.get("metric_id") in metric_ids
            and values.get("comparison") in comparisons
            and isinstance(values.get("value"), (int, float))
            and not isinstance(values.get("value"), bool)
            and math.isfinite(float(values["value"]))
        ):
            raise ValueError("mission score parameters are invalid")
    elif operator in {"all", "any", "not"}:
        conditions = values.get("conditions")
        if not (
            exact({"conditions"})
            and isinstance(conditions, (list, tuple))
            and (len(conditions) == 1 if operator == "not" else len(conditions) > 0)
        ):
            raise ValueError("nested mission parameters are invalid")
        canonical: list[Any] = []
        for condition in conditions:
            if isinstance(condition, str) and condition:
                canonical.append(condition)
                continue
            if not isinstance(condition, Mapping):
                raise ValueError("nested mission condition is invalid")
            nested = cast(dict[str, Any], _json_value(condition))
            nested_operator = nested.pop("operator", None)
            nested_parameters = nested.pop("parameters", nested)
            canonical.append(
                {
                    "operator": nested_operator,
                    "parameters": _validated_mission_parameters_v2(
                        nested_operator,
                        nested_parameters,
                        states=states,
                        event_ids=event_ids,
                        zone_ids=zone_ids,
                        entity_ids=entity_ids,
                        metric_ids=metric_ids,
                    ),
                }
            )
        values["conditions"] = tuple(canonical)
    return values


def _validate_event_payload(event_type: str, payload: Any) -> None:
    values = payload.values if isinstance(payload, _FrozenRecordV2) else payload
    if not isinstance(values, Mapping):
        raise ValueError("event payload must be an object")
    resolved_weather = "environment_binding" in values
    resolved_effect = "effect_binding" in values or "damage_binding" in values
    schemas: dict[str, tuple[set[str], set[str]]] = {
        "spawn": ({"entity"}, set()),
        "despawn": ({"entity_id"}, set()),
        "weather_change": (
            {"environment_binding"} if resolved_weather else {"environment_ref"},
            set(),
        ),
        "zone_activation": ({"zone_id"}, set()),
        "jamming_start": ({"session_id", "source_entity_id", "target_entity_id"}, set()),
        "jamming_end": ({"session_id"}, set()),
        "component_suppression": ({"target_entity_id", "component_ref", "duration_ticks"}, set()),
        "message": (
            {"body", "visibility"},
            {"sender_entity_id", "recipient_entity_ids", "recipient_controller_slots"},
        ),
        "mission_marker": ({"marker_id"}, {"zone_id", "position_m"}),
        "apply_effect": (
            {"effect_binding", "damage_binding", "target_selector"}
            if resolved_effect
            else {"effect_ref", "target_selector"},
            set(),
        ),
        "spatial_effect_trigger": (
            {
                "source_kind",
                "source_entity_ids",
                "effect_binding",
                "damage_binding",
                "target_selector",
                "source_lifecycle",
            }
            if resolved_effect
            else {
                "source_kind",
                "source_entity_ids",
                "effect_ref",
                "target_selector",
                "source_lifecycle",
            },
            {
                "zone_id",
                "secondary_effect_ref",
                "secondary_effect_binding",
                "secondary_damage_binding",
                "secondary_probability",
                "secondary_target_selector",
            },
        ),
    }
    if event_type not in schemas:
        raise ValueError("event type is not whitelisted")
    required, optional = schemas[event_type]
    if set(values) - (required | optional) or not required.issubset(values):
        raise ValueError("event payload fields do not match its type")

    def bounded_string(value: Any) -> bool:
        return isinstance(value, str) and 0 < len(value) <= 4096

    for field in (
        "entity_id",
        "environment_ref",
        "zone_id",
        "session_id",
        "source_entity_id",
        "target_entity_id",
        "component_ref",
        "sender_entity_id",
        "marker_id",
        "effect_ref",
        "secondary_effect_ref",
    ):
        if field in values and not bounded_string(values[field]):
            raise ValueError(f"{field} must be a bounded nonempty string")
    if event_type == "message":
        if not bounded_string(values["body"]) or values["visibility"] not in {
            "public",
            "recipients",
        }:
            raise ValueError("message body or visibility is invalid")
        for field in ("recipient_entity_ids", "recipient_controller_slots"):
            recipients = values.get(field, ())
            if (
                not isinstance(recipients, (list, tuple))
                or any(not bounded_string(item) for item in recipients)
                or len(recipients) != len(set(recipients))
            ):
                raise ValueError("message recipients must be unique typed strings")
    if event_type == "component_suppression" and (
        not isinstance(values["duration_ticks"], int)
        or isinstance(values["duration_ticks"], bool)
        or values["duration_ticks"] <= 0
    ):
        raise ValueError("suppression duration must be a positive integer")
    if event_type == "apply_effect":
        selector_object = values["target_selector"]
        selector = (
            selector_object.values
            if isinstance(selector_object, _FrozenRecordV2)
            else selector_object
        )
        if (
            not isinstance(selector, Mapping)
            or set(selector) != {"entity_ids"}
            or not isinstance(selector.get("entity_ids"), (list, tuple))
            or not selector["entity_ids"]
            or any(not bounded_string(item) for item in selector["entity_ids"])
            or len(selector["entity_ids"]) != len(set(selector["entity_ids"]))
        ):
            raise ValueError("effect selector is invalid")
    if event_type == "spatial_effect_trigger":
        source_kind = values["source_kind"]
        source_entity_ids = values["source_entity_ids"]
        if source_kind not in {"zone_entry", "collision"}:
            raise ValueError("spatial trigger source kind is invalid")
        if (
            not isinstance(source_entity_ids, (list, tuple))
            or not source_entity_ids
            or any(not bounded_string(item) for item in source_entity_ids)
            or len(source_entity_ids) != len(set(source_entity_ids))
        ):
            raise ValueError("spatial trigger source entities are invalid")
        if (source_kind == "zone_entry") != ("zone_id" in values):
            raise ValueError("zone entry trigger requires exactly one zone identity")
        if "zone_id" in values and not bounded_string(values["zone_id"]):
            raise ValueError("spatial trigger zone identity is invalid")
        if values["source_lifecycle"] not in {"wreck", "despawn"}:
            raise ValueError("spatial trigger lifecycle policy is invalid")

        def validate_spatial_selector(selector_object: Any, *, name: str) -> None:
            selector = (
                selector_object.values
                if isinstance(selector_object, _FrozenRecordV2)
                else selector_object
            )
            if (
                not isinstance(selector, Mapping)
                or set(selector) - {"entity_ids", "exclude_entity_ids"}
                or "entity_ids" not in selector
                or not isinstance(selector["entity_ids"], (list, tuple))
                or not selector["entity_ids"]
                or any(not bounded_string(item) for item in selector["entity_ids"])
                or len(selector["entity_ids"]) != len(set(selector["entity_ids"]))
            ):
                raise ValueError(f"{name} selector is invalid")
            excluded = selector.get("exclude_entity_ids", ())
            if (
                not isinstance(excluded, (list, tuple))
                or any(not bounded_string(item) for item in excluded)
                or len(excluded) != len(set(excluded))
            ):
                raise ValueError(f"{name} exclusion selector is invalid")

        validate_spatial_selector(values["target_selector"], name="spatial trigger")
        secondary_ref = values.get("secondary_effect_ref")
        secondary_binding = values.get("secondary_effect_binding")
        secondary_damage = values.get("secondary_damage_binding")
        has_secondary = (
            secondary_ref is not None
            or secondary_binding is not None
            or secondary_damage is not None
        )
        if has_secondary:
            if (
                "secondary_probability" not in values
                or "secondary_target_selector" not in values
                or (secondary_ref is not None and not bounded_string(secondary_ref))
                or (
                    secondary_binding is not None
                    and (not resolved_effect or secondary_damage is None)
                )
            ):
                raise ValueError("secondary effect chain is incomplete")
            probability = values["secondary_probability"]
            if (
                isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not math.isfinite(float(probability))
                or not 0.0 <= float(probability) <= 1.0
            ):
                raise ValueError("secondary effect probability is invalid")
            validate_spatial_selector(values["secondary_target_selector"], name="secondary")
        elif "secondary_probability" in values or "secondary_target_selector" in values:
            raise ValueError("secondary effect configuration is incomplete")
    if event_type == "mission_marker" and "position_m" in values:
        position = values["position_m"]
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 3
            or any(
                not isinstance(axis, (int, float))
                or isinstance(axis, bool)
                or not math.isfinite(float(axis))
                for axis in position
            )
        ):
            raise ValueError("marker position must be finite canonical 3D metres")


@dataclass(frozen=True, slots=True, eq=False)
class ResolvedEventV2:
    schema_version: str
    id: str
    event_type: str
    trigger: _FrozenRecordV2
    priority: int
    depends_on: tuple[str, ...]
    payload: _FrozenRecordV2

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ResolvedEventV2) and _json_value(self) == _json_value(other)


@dataclass(frozen=True, slots=True)
class ResolvedBoundaryDeploymentV2:
    """Compiler-validated per-entity spatial-zone topology for runtime systems."""

    allowed_zone_ids: tuple[str, ...] = ()
    excluded_zone_ids: tuple[str, ...] = ()
    point_on_edge: str = "inside"


@dataclass(frozen=True, slots=True)
class ResolvedEntityV2:
    id: str
    faction_id: str
    tags: tuple[str, ...]
    controller_slot: str | None
    composition: EntityCompositionV2
    resource_bindings: Mapping[str, tuple[ResolvedResourceBindingV2, ...]]
    runtime_initial: _RuntimeInitialV2
    boundary_deployment: ResolvedBoundaryDeploymentV2 | None = None
    destroyed_lifecycle: Literal["wreck", "despawn"] = "wreck"

    def model_copy(self, *, update: Mapping[str, Any] | None = None) -> ResolvedEntityV2:
        """Pydantic-compatible immutable copy used by integrity/adversarial callers."""

        return replace(self, **dict(update or {}))

    @property
    def initial_state(self) -> InitialStateV2:
        return self.runtime_initial.initial_state

    @property
    def platform_ref(self) -> str:
        return self.composition.platform_ref

    @property
    def dynamics_ref(self) -> str | None:
        return self.composition.dynamics_ref

    @property
    def loadout_ref(self) -> str | None:
        return self.composition.loadout_ref

    @property
    def component_refs(self) -> tuple[str, ...]:
        return (*self.composition.sensor_refs, *self.composition.communication_refs)

    @property
    def domain(self) -> str:
        platform = self.resource_bindings.get("platforms", ())
        value = platform[0].normalized_content.get("domain") if platform else ""
        return value if isinstance(value, str) else ""


def _resolve_declared_spatial_effect_policy(
    world: _ResolvedWorldV2,
    resources: Sequence[ResolvedResourceBindingV2],
) -> ResolvedSpatialEffectPolicyV2 | None:
    declaration = world.spatial_damage_policy
    if declaration is None:
        return None
    bindings = {item.exact_ref: item for item in resources}
    effect = bindings.get(declaration.collision_effect_ref)
    damage_ref = effect.normalized_content.get("damage_model_ref") if effect is not None else None
    damage = bindings.get(damage_ref) if isinstance(damage_ref, str) else None
    if (
        effect is None
        or effect.resource_type != "effects"
        or damage is None
        or damage.resource_type != "damage_models"
    ):
        raise ValueError("declared spatial effect chain is absent from resolved resources")
    return ResolvedSpatialEffectPolicyV2(
        effect_binding=effect,
        damage_binding=damage,
        magnitude_model=declaration.magnitude_model,
        magnitude_parameters=_freeze(declaration.magnitude_parameters),
        output_unit=declaration.output_unit,
    )


def resolve_world_resource_closure_v2(
    policy: ResolvedSpatialEffectPolicyV2 | None,
    resources: Sequence[ResolvedResourceBindingV2],
) -> tuple[ResolvedResourceBindingV2, ...]:
    """Close World-owned roots over the complete resolved dependency graph."""

    if policy is None:
        return ()
    index = {item.exact_ref: item for item in resources}
    if len(index) != len(resources):
        raise ValueError("duplicate world resource candidate")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(reference: str) -> None:
        if reference in visiting:
            raise ValueError(f"world resource dependency cycle at {reference}")
        if reference in visited:
            return
        binding = index.get(reference)
        if binding is None:
            raise ValueError(f"missing world resource dependency: {reference}")
        visiting.add(reference)
        dependencies = set(binding.dependencies)
        damage_reference = binding.normalized_content.get("damage_model_ref")
        if isinstance(damage_reference, str):
            dependencies.add(damage_reference)
        for dependency in sorted(dependencies):
            visit(dependency)
        visiting.remove(reference)
        visited.add(reference)

    visit(policy.effect_binding.exact_ref)
    return tuple(index[reference] for reference in sorted(visited))


@dataclass(frozen=True, slots=True)
class EntityDraftV2:
    """Formation-expanded identity/composition with an unresolved source position."""

    entity: EntitySpecV2
    raw_initial: Mapping[str, Any]
    raw_entity: Mapping[str, Any]
    formation_id: str | None = None
    formation_index: int | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.entity, name)


@dataclass(frozen=True, slots=True)
class ResolvedCompositionDraftV2:
    """Catalog-closed entity whose canonical position is finalized by coordinates."""

    source: EntityDraftV2
    resolved: ResolvedEntityV2

    def __getattr__(self, name: str) -> Any:
        return getattr(self.resolved, name)


@dataclass(frozen=True, slots=True)
class ResolvedScenarioV2:
    schema_version: str
    scenario_id: str
    catalog_hash: str
    model_registry_hash: str
    model_registry_snapshot: tuple[ModelFactoryMetadataV2, ...]
    compiler_version: str
    compile_stage_trace: tuple[StageRecordV2, ...]
    provenance: _FrozenRecordV2 = dataclass_field(compare=False)
    factions: tuple[FactionV2, ...]
    relationships: tuple[RelationshipV2, ...]
    entities: tuple[EntitySpecV2 | ResolvedEntityV2, ...]
    world: _ResolvedWorldV2
    events: tuple[ResolvedEventV2, ...]
    mission_states: tuple[str, ...]
    mission_rules: tuple[MissionRuleV2 | _FrozenRecordV2, ...]
    score_metrics: tuple[ScoreMetricV2, ...]
    scoring: _FrozenRecordV2 | None
    controller_slots: tuple[_FrozenRecordV2, ...]
    controller_policy: str | None
    visibility: _FrozenRecordV2 | None
    world_resource_bindings: tuple[ResolvedResourceBindingV2, ...]
    spatial_effect_policy: ResolvedSpatialEffectPolicyV2 | None
    resolved_hash: str

    def __hash__(self) -> int:
        return hash(self.resolved_hash)

    def _payload(self, *, include_hash: bool) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "catalog_hash": self.catalog_hash,
            "model_registry_hash": self.model_registry_hash,
            "model_registry_snapshot": _json_value(self.model_registry_snapshot),
            "compiler_version": self.compiler_version,
            "compile_stage_trace": _json_value(self.compile_stage_trace),
            "provenance": _json_value(self.provenance),
            "factions": _json_value(self.factions),
            "relationships": _json_value(self.relationships),
            "entities": _json_value(self.entities),
            "world": _json_value(self.world),
            "events": _json_value(self.events),
            "mission_states": self.mission_states,
            "mission_rules": _json_value(self.mission_rules),
            "score_metrics": _json_value(self.score_metrics),
            "scoring": _json_value(self.scoring),
            "controller_slots": _json_value(self.controller_slots),
            "controller_policy": self.controller_policy,
            "visibility": _json_value(self.visibility),
            "world_resource_bindings": _json_value(self.world_resource_bindings),
            "spatial_effect_policy": _json_value(self.spatial_effect_policy),
        }
        if include_hash:
            payload["resolved_hash"] = self.resolved_hash
        return payload

    def to_json(self) -> str:
        self.validate_integrity()
        return _canonical_json(self._payload(include_hash=True))

    def validate_integrity(self) -> None:
        """Revalidate the complete frozen semantic graph and its canonical hash."""
        self._validate_integrity()
        expected = self.compute_resolved_hash(self._payload(include_hash=False))
        if self.resolved_hash != expected:
            raise _ResolvedIntegrityError("resolved scenario hash mismatch")

    @staticmethod
    def compute_resolved_hash(payload: Mapping[str, Any]) -> str:
        semantic = _json_value(payload)
        semantic.pop("resolved_hash", None)
        semantic.pop("scenario_id", None)
        semantic["compiler_version"] = COMPILER_VERSION
        provenance = semantic.get("provenance")
        if isinstance(provenance, dict):
            for field in (
                "package_logical_hash",
                "package_content_hash",
                "package_archive_hash",
                "package_identity_hash",
            ):
                provenance.pop(field, None)
        return _digest(semantic)

    @classmethod
    def from_json(cls, encoded: str) -> Self:
        try:
            payload = json.loads(encoded)
            if not isinstance(payload, dict):
                raise ValueError("resolved payload must be an object")
            entities: list[EntitySpecV2 | ResolvedEntityV2] = []
            for item in payload["entities"]:
                if "resource_bindings" not in item:
                    entities.append(EntitySpecV2.model_validate(item))
                    continue
                bindings = {
                    str(resource_type): tuple(
                        ResolvedResourceBindingV2(
                            schema_version=str(binding["schema_version"]),
                            exact_ref=str(binding["exact_ref"]),
                            resource_type=binding["resource_type"],
                            id=str(binding["id"]),
                            version=str(binding["version"]),
                            engine_compatibility=str(binding["engine_compatibility"]),
                            content_hash=str(binding["content_hash"]),
                            model_ref=str(binding["model_ref"]),
                            model_evidence=_ModelEvidenceV2(
                                model_ref=str(binding["model_evidence"]["model_ref"]),
                                artifact_sha256=str(binding["model_evidence"]["artifact_sha256"]),
                                interface_version=str(
                                    binding["model_evidence"]["interface_version"]
                                ),
                                input_schema=str(binding["model_evidence"]["input_schema"]),
                                output_schema=str(binding["model_evidence"]["output_schema"]),
                                trusted=bool(binding["model_evidence"]["trusted"]),
                                deterministic=bool(binding["model_evidence"]["deterministic"]),
                                resource_types=tuple(binding["model_evidence"]["resource_types"]),
                            ),
                            dependencies=tuple(binding["dependencies"]),
                            content=_freeze(binding["content"]),
                            normalized_content=_freeze(binding["normalized_content"]),
                            units=_freeze(binding["units"]),
                            field_units=_freeze(binding["field_units"]),
                            defaults=MappingProxyType(
                                {
                                    str(key): _DefaultEvidenceV2(
                                        value=_freeze(value["value"]),
                                        unit=str(value["unit"]),
                                        source=_DefaultSourceV2(
                                            kind=str(value["source"]["kind"]),
                                            id=str(value["source"]["id"]),
                                        ),
                                        input_value=_freeze(value["input_value"]),
                                        input_unit=str(value["input_unit"]),
                                        conversion_ref=(
                                            None
                                            if value["conversion_ref"] is None
                                            else str(value["conversion_ref"])
                                        ),
                                        conversion_scale=(
                                            None
                                            if value["conversion_scale"] is None
                                            else float(value["conversion_scale"])
                                        ),
                                        value_type=(
                                            None
                                            if value["value_type"] is None
                                            else str(value["value_type"])
                                        ),
                                    )
                                    for key, value in binding["defaults"].items()
                                }
                            ),
                        )
                        for binding in values
                    )
                    for resource_type, values in item["resource_bindings"].items()
                }
                composition = EntityCompositionV2.model_validate(item["composition"])
                runtime = item["runtime_initial"]
                entities.append(
                    ResolvedEntityV2(
                        id=str(item["id"]),
                        faction_id=str(item["faction_id"]),
                        tags=tuple(item["tags"]),
                        controller_slot=item["controller_slot"],
                        composition=composition,
                        resource_bindings=MappingProxyType(bindings),
                        runtime_initial=_RuntimeInitialV2(
                            initial_state=InitialStateV2.model_validate(runtime["initial_state"]),
                            ammunition=_freeze(runtime["ammunition"]),
                        ),
                        boundary_deployment=(
                            None
                            if item.get("boundary_deployment") is None
                            else ResolvedBoundaryDeploymentV2(
                                allowed_zone_ids=tuple(
                                    item["boundary_deployment"].get("allowed_zone_ids", ())
                                ),
                                excluded_zone_ids=tuple(
                                    item["boundary_deployment"].get("excluded_zone_ids", ())
                                ),
                                point_on_edge=str(
                                    item["boundary_deployment"].get("point_on_edge", "inside")
                                ),
                            )
                        ),
                        destroyed_lifecycle=cast(
                            Literal["wreck", "despawn"],
                            item.get("destroyed_lifecycle", "wreck"),
                        ),
                    )
                )
            resolved_event_values: list[ResolvedEventV2] = []
            for item in payload["events"]:
                event_payload = dict(item["payload"])
                for binding_name in (
                    "environment_binding",
                    "effect_binding",
                    "damage_binding",
                ):
                    binding_payload = event_payload.get(binding_name)
                    if isinstance(binding_payload, Mapping):
                        event_payload[binding_name] = _resolved_binding_from_json(binding_payload)
                resolved_event_values.append(
                    ResolvedEventV2(
                        schema_version=str(item["schema_version"]),
                        id=str(item["id"]),
                        event_type=str(item["event_type"]),
                        trigger=_record(item["trigger"]),
                        priority=int(item["priority"]),
                        depends_on=tuple(item["depends_on"]),
                        payload=_record(event_payload),
                    )
                )
            resolved_events = tuple(resolved_event_values)
            world_resource_bindings = tuple(
                _resolved_binding_from_json(item)
                for item in payload.get("world_resource_bindings", ())
            )
            raw_spatial_effect_policy = payload.get("spatial_effect_policy")
            parsed_spatial_effect_policy = (
                None
                if raw_spatial_effect_policy is None
                else ResolvedSpatialEffectPolicyV2.from_mapping(raw_spatial_effect_policy)
            )
            if parsed_spatial_effect_policy is None:
                spatial_effect_policy = None
            else:
                world_binding_index = {item.exact_ref: item for item in world_resource_bindings}
                effect_binding = world_binding_index.get(
                    parsed_spatial_effect_policy.effect_binding.exact_ref
                )
                damage_binding = world_binding_index.get(
                    parsed_spatial_effect_policy.damage_binding.exact_ref
                )
                if (
                    effect_binding is None
                    or damage_binding is None
                    or _json_value(effect_binding)
                    != _json_value(parsed_spatial_effect_policy.effect_binding)
                    or _json_value(damage_binding)
                    != _json_value(parsed_spatial_effect_policy.damage_binding)
                ):
                    raise ValueError("resolved policy bindings differ from world closure")
                spatial_effect_policy = replace(
                    parsed_spatial_effect_policy,
                    effect_binding=effect_binding,
                    damage_binding=damage_binding,
                )
            resolved = cls(
                schema_version=str(payload["schema_version"]),
                scenario_id=str(payload["scenario_id"]),
                catalog_hash=str(payload["catalog_hash"]),
                model_registry_hash=str(
                    payload.get("model_registry_hash", payload["catalog_hash"])
                ),
                model_registry_snapshot=tuple(
                    ModelFactoryMetadataV2.model_validate(
                        {key: value for key, value in item.items() if key != "exact_ref"}
                    )
                    for item in payload["model_registry_snapshot"]
                ),
                compiler_version=str(payload.get("compiler_version", COMPILER_VERSION)),
                compile_stage_trace=tuple(
                    StageRecordV2(
                        stage=str(item["stage"]),
                        ordinal=int(item["ordinal"]),
                        status=str(item.get("status", "completed")),
                        duration_policy=str(item.get("duration_policy", "deterministic-none")),
                    )
                    for item in payload.get("compile_stage_trace", ())
                ),
                provenance=_record(payload.get("provenance", {})),
                factions=tuple(FactionV2.model_validate(item) for item in payload["factions"]),
                relationships=tuple(
                    RelationshipV2.model_validate(item) for item in payload["relationships"]
                ),
                entities=tuple(entities),
                world=_ResolvedWorldV2.from_mapping(payload["world"]),
                events=resolved_events,
                mission_states=tuple(payload.get("mission_states", ())),
                mission_rules=tuple(
                    _mission_rule_record(item)
                    if "selector_resolution" in item
                    else MissionRuleV2.model_validate(item)
                    for item in payload["mission_rules"]
                ),
                score_metrics=tuple(
                    ScoreMetricV2.model_validate(item) for item in payload["score_metrics"]
                ),
                scoring=(None if payload.get("scoring") is None else _record(payload["scoring"])),
                controller_slots=tuple(
                    _record(item) for item in payload.get("controller_slots", ())
                ),
                controller_policy=payload.get("controller_policy"),
                visibility=(
                    None if payload.get("visibility") is None else _record(payload["visibility"])
                ),
                world_resource_bindings=world_resource_bindings,
                spatial_effect_policy=spatial_effect_policy,
                resolved_hash=str(payload["resolved_hash"]),
            )
        except _ResolvedIntegrityError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise _ResolvedIntegrityError("invalid resolved scenario JSON") from error
        resolved.validate_integrity()
        return resolved

    def _behavior_payload(self) -> dict[str, Any]:
        payload = self._payload(include_hash=False)
        payload.pop("scenario_id", None)
        payload["compiler_version"] = COMPILER_VERSION
        return payload

    def _validate_resource_binding_integrity(
        self,
        binding: Any,
        expected_type: str,
        metadata: Mapping[str, ModelFactoryMetadataV2],
    ) -> None:
        try:
            content = cast(dict[str, Any], _json_value(binding.content))
            normalized_content = cast(dict[str, Any], _json_value(binding.normalized_content))
            rebuilt = CatalogResourceV2(
                schema_version="2.0",
                resource_type=binding.resource_type,
                id=binding.id,
                version=binding.version,
                engine_compatibility=binding.engine_compatibility,
                model_id=binding.model_ref,
                dependencies=tuple(binding.dependencies),
                content=content,
            )
            model = metadata[binding.model_ref]
            evidence = binding.model_evidence
            if not (
                binding.schema_version == "2.0"
                and binding.resource_type == expected_type
                and rebuilt.exact_ref == binding.exact_ref
                and rebuilt.content_hash == binding.content_hash
                and evidence.model_ref == model.exact_ref
                and evidence.artifact_sha256 == model.artifact_sha256
                and evidence.interface_version == model.interface_version == "2.0"
                and evidence.input_schema == model.input_schema
                and evidence.output_schema == model.output_schema
                and evidence.trusted == model.trusted is True
                and evidence.deterministic == model.deterministic is True
                and tuple(evidence.resource_types) == model.resource_types
                and expected_type in evidence.resource_types
                and cast(dict[str, Any], _json_value(binding.units)) == model.units
                and cast(dict[str, Any], _json_value(binding.field_units)) == model.field_units
            ):
                raise _ResolvedIntegrityError("resource binding identity or model mismatch")
            defaults_object = binding.defaults
            defaults = (
                defaults_object.values
                if isinstance(defaults_object, _FrozenRecordV2)
                else defaults_object
            )
            required = content.get("required_defaults", ())
            if (
                not isinstance(required, (list, tuple))
                or any(not isinstance(item, str) or not item for item in required)
                or len(required) != len(set(required))
            ):
                raise _ResolvedIntegrityError("invalid binding default schema")
            expected_normalized = dict(content)
            for key, default in defaults.items():
                source = default.source
                if source.kind != "model_metadata" or source.id != model.exact_ref:
                    raise _ResolvedIntegrityError("binding default source mismatch")
                declaration = content.get("defaults", {}).get(key)
                if not isinstance(declaration, Mapping):
                    raise _ResolvedIntegrityError("binding default declaration missing")
                if (
                    default.input_value != declaration.get("value")
                    or default.input_unit != declaration.get("unit")
                    or default.conversion_ref != declaration.get("conversion_ref")
                    or default.unit != model.field_units.get(key, "1")
                ):
                    raise _ResolvedIntegrityError("binding default evidence mismatch")
                expected_value = default.input_value
                if default.conversion_ref is not None:
                    conversion = content.get("trusted_unit_conversions", {}).get(
                        default.conversion_ref
                    )
                    if not isinstance(conversion, Mapping):
                        raise _ResolvedIntegrityError("binding default conversion missing")
                    scale = conversion.get("scale")
                    if (
                        not isinstance(scale, (int, float))
                        or isinstance(scale, bool)
                        or not math.isfinite(float(scale))
                        or float(scale) <= 0
                        or default.conversion_scale != float(scale)
                        or not isinstance(expected_value, (int, float))
                        or isinstance(expected_value, bool)
                    ):
                        raise _ResolvedIntegrityError("binding default conversion mismatch")
                    expected_value = float(expected_value) * float(scale)
                elif default.conversion_scale is not None:
                    raise _ResolvedIntegrityError("unexpected binding conversion scale")
                if default.value != expected_value:
                    raise _ResolvedIntegrityError("binding default value mismatch")
                expected_normalized[key] = default.value
            if set(defaults) != {key for key in required if key not in content}:
                raise _ResolvedIntegrityError("binding required defaults mismatch")
            if _json_value(expected_normalized) != normalized_content:
                raise _ResolvedIntegrityError("binding normalized content mismatch")
        except _ResolvedIntegrityError:
            raise
        except (AttributeError, KeyError, TypeError, ValidationError, ValueError) as error:
            raise _ResolvedIntegrityError("invalid resource binding") from error

    def _validate_resolved_entity_integrity(
        self,
        entity: Any,
        metadata: Mapping[str, ModelFactoryMetadataV2],
    ) -> None:
        try:
            if entity.destroyed_lifecycle not in {"wreck", "despawn"}:
                raise _ResolvedIntegrityError("entity destroyed lifecycle policy is invalid")
            groups_object = entity.resource_bindings
            groups = (
                groups_object.values
                if isinstance(groups_object, _FrozenRecordV2)
                else groups_object
            )
            flat = [binding for bindings in groups.values() for binding in bindings]
            index = {binding.exact_ref: binding for binding in flat}
            if len(index) != len(flat):
                raise _ResolvedIntegrityError("duplicate entity resource binding")
            for resource_type, bindings in groups.items():
                for binding in bindings:
                    self._validate_resource_binding_integrity(binding, resource_type, metadata)
            composition = entity.composition
            ammunition_object = composition.ammunition
            ammunition = (
                ammunition_object.values
                if isinstance(ammunition_object, _FrozenRecordV2)
                else ammunition_object
            )
            direct: list[tuple[str, Any]] = [
                ("platforms", composition.platform_ref),
                ("dynamics", composition.dynamics_ref),
                ("loadouts", composition.loadout_ref),
                ("energy", composition.energy_ref),
                ("collision_shapes", composition.collision_shape_ref),
                ("visualization_assets", composition.visualization_ref),
                *(("sensors", reference) for reference in composition.sensor_refs),
                *(("communications", reference) for reference in composition.communication_refs),
                *(("ammunition", reference) for reference in ammunition),
            ]
            roots: set[str] = set()
            for resource_type, reference in direct:
                if reference is None:
                    continue
                binding = index.get(reference)
                if binding is None or binding.resource_type != resource_type:
                    raise _ResolvedIntegrityError("entity root binding missing or wrong type")
                roots.add(reference)
            reachable: set[str] = set()
            pending = list(roots)
            implicit_fields = (
                "weapon_refs",
                "ammunition_refs",
                "effect_ref",
                "damage_model_ref",
                "weapon_ref",
                "energy_ref",
                "collision_shape_ref",
                "visualization_ref",
            )
            while pending:
                reference = pending.pop()
                if reference in reachable:
                    continue
                binding = index.get(reference)
                if binding is None:
                    raise _ResolvedIntegrityError("entity dependency binding missing")
                reachable.add(reference)
                references = set(binding.dependencies)
                content = cast(dict[str, Any], _json_value(binding.normalized_content))
                for field in implicit_fields:
                    value = content.get(field)
                    if isinstance(value, str):
                        references.add(value)
                    elif isinstance(value, (list, tuple)):
                        references.update(str(item) for item in value)
                pending.extend(sorted(references))
            if reachable != set(index):
                raise _ResolvedIntegrityError("entity resource closure has orphan bindings")
            runtime = entity.runtime_initial
            position = runtime.initial_state.position_m
            if (
                not isinstance(position, (list, tuple))
                or len(position) != 3
                or any(
                    not isinstance(axis, (int, float))
                    or isinstance(axis, bool)
                    or not math.isfinite(float(axis))
                    for axis in position
                )
            ):
                raise _ResolvedIntegrityError("entity runtime position is invalid")
            runtime_ammunition_object = runtime.ammunition
            runtime_ammunition = (
                runtime_ammunition_object.values
                if isinstance(runtime_ammunition_object, _FrozenRecordV2)
                else runtime_ammunition_object
            )
            if (
                any(
                    not isinstance(count, int) or isinstance(count, bool) or count < 0
                    for count in ammunition.values()
                )
                or dict(runtime_ammunition) != dict(ammunition)
                or any(
                    reference not in index or index[reference].resource_type != "ammunition"
                    for reference in ammunition
                )
            ):
                raise _ResolvedIntegrityError("entity runtime ammunition is invalid")
        except _ResolvedIntegrityError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise _ResolvedIntegrityError("invalid resolved entity") from error

    def _validate_selector_resolution_equivalence(
        self,
        raw_selector: Any,
        resolution: Any,
        *,
        faction_ids: set[str],
        zone_ids: set[str],
        event_ids: set[str],
        allow_empty: bool = False,
    ) -> None:
        if not isinstance(raw_selector, _FrozenRecordV2) or not isinstance(
            resolution, _FrozenRecordV2
        ):
            raise _ResolvedIntegrityError("selector evidence is invalid")
        raw = raw_selector.values
        selector_entities = [
            entity for entity in self.entities if isinstance(entity, ResolvedEntityV2)
        ]
        selector_entities.extend(
            event.payload.entity
            for event in self.events
            if event.event_type == "spawn"
            and isinstance(getattr(event.payload, "entity", None), ResolvedEntityV2)
        )
        entities = {entity.id: entity for entity in selector_entities}
        explicit = "entity_ids" in raw
        candidates = tuple(sorted(raw.get("entity_ids", entities)))
        filters = {
            "faction_ids": tuple(sorted(raw.get("factions", ()))),
            "platforms": tuple(sorted(raw.get("platforms", ()))),
            "domains": tuple(sorted(raw.get("domains", ()))),
            "capabilities": tuple(sorted(raw.get("capabilities", ()))),
            "tags": tuple(sorted(raw.get("tags", ()))),
            "zones": tuple(sorted(raw.get("zones", ()))),
            "events": tuple(sorted(raw.get("events", ()))),
        }
        if (
            any(identifier not in entities for identifier in candidates)
            or any(identifier not in faction_ids for identifier in filters["faction_ids"])
            or any(identifier not in zone_ids for identifier in filters["zones"])
            or any(identifier not in event_ids for identifier in filters["events"])
        ):
            raise _ResolvedIntegrityError("selector endpoint is missing")
        selected: list[str] = []
        for identifier in candidates:
            entity = entities[identifier]
            available: set[str] = set()
            if entity.composition.sensor_refs:
                available.add("sensor")
            if entity.composition.communication_refs:
                available.add("communication")
            if entity.composition.loadout_ref:
                available.add("weapon")
            matches = not (
                (filters["faction_ids"] and entity.faction_id not in filters["faction_ids"])
                or (filters["platforms"] and entity.platform_ref not in filters["platforms"])
                or (filters["domains"] and entity.domain not in filters["domains"])
                or any(item not in entity.tags for item in filters["tags"])
                or any(item not in available for item in filters["capabilities"])
            )
            if explicit and not matches:
                raise _ResolvedIntegrityError("explicit selector does not match")
            if matches:
                selected.append(identifier)
        expected: dict[str, tuple[Any, ...]] = {"entity_ids": tuple(selected), **filters}
        actual = {key: tuple(resolution.values.get(key, ())) for key in expected}
        if (not selected and not allow_empty) or actual != expected:
            raise _ResolvedIntegrityError("selector resolution does not match declaration")

    def _validate_mission_control_integrity(self) -> None:
        """Validate the fully materialized control plane without source or Catalog access."""
        selector_entities = list(self.entities)
        selector_entities.extend(
            event.payload.entity
            for event in self.events
            if event.event_type == "spawn"
            and isinstance(getattr(event.payload, "entity", None), ResolvedEntityV2)
        )
        entity_by_id = {entity.id: entity for entity in selector_entities}
        faction_ids = {faction.id for faction in self.factions}
        event_ids = {event.id for event in self.events}
        event_types = {event.id: event.event_type for event in self.events}
        zone_ids = {zone.id for zone in self.world.zones}
        if (
            len(self.world.deployment_excluded_zone_ids)
            != len(set(self.world.deployment_excluded_zone_ids))
            or set(self.world.deployment_excluded_zone_ids) - zone_ids
        ):
            raise _ResolvedIntegrityError("resolved world deployment zones are invalid")
        rule_ids = {rule.id for rule in self.mission_rules}
        if any(isinstance(rule, _FrozenRecordV2) for rule in self.mission_rules) and (
            not self.mission_states
            or any(not isinstance(state, str) or not state for state in self.mission_states)
            or len(self.mission_states) != len(set(self.mission_states))
        ):
            raise _ResolvedIntegrityError("mission states are invalid")
        mission_states = set(self.mission_states)
        if len(rule_ids) != len(self.mission_rules):
            raise _ResolvedIntegrityError("duplicate mission rule")
        dependencies: dict[str, set[str]] = {}
        declared_metric_ids = (
            {metric.id for metric in self.scoring.metrics} if self.scoring is not None else set()
        )
        for rule in self.mission_rules:
            if not isinstance(rule, _FrozenRecordV2):
                continue
            try:
                condition = rule.condition
                operator = condition.operator
                parameters = condition.parameters
                parameter_values = parameters.values
                canonical_parameters = _validated_mission_parameters_v2(
                    operator,
                    parameter_values,
                    states=mission_states,
                    event_ids=event_ids,
                    zone_ids=zone_ids,
                    entity_ids=set(entity_by_id),
                    metric_ids=declared_metric_ids,
                )
                if _json_value(parameter_values) != _json_value(canonical_parameters):
                    raise _ResolvedIntegrityError("mission condition is invalid")
                outcome = rule.outcome
                ranking = outcome.ranking
                ranking_values = ranking.values if isinstance(ranking, _FrozenRecordV2) else ranking
                if (
                    set(outcome.values)
                    != {"set_state", "emit_event", "terminal", "result", "ranking"}
                    or not isinstance(outcome.set_state, str)
                    or outcome.set_state not in mission_states
                    or outcome.emit_event not in event_ids
                    or not isinstance(outcome.terminal, bool)
                    or not isinstance(ranking_values, Mapping)
                    or any(
                        faction not in faction_ids
                        or not isinstance(rank, int)
                        or isinstance(rank, bool)
                        or rank <= 0
                        for faction, rank in ranking_values.items()
                    )
                    or len(set(ranking_values.values())) != len(ranking_values)
                    or (
                        outcome.terminal
                        and (
                            not isinstance(outcome.result, str)
                            or not outcome.result
                            or set(ranking_values) != faction_ids
                        )
                    )
                    or (
                        not outcome.terminal
                        and (outcome.result is not None or bool(ranking_values))
                    )
                ):
                    raise _ResolvedIntegrityError("mission outcome is invalid")
                resolution = rule.selector_resolution
                self._validate_selector_resolution_equivalence(
                    condition.selector,
                    resolution,
                    faction_ids=faction_ids,
                    zone_ids=zone_ids,
                    event_ids=event_ids,
                )
                selected = tuple(resolution.entity_ids)
                if (
                    not selected
                    or selected != tuple(sorted(selected))
                    or len(selected) != len(set(selected))
                    or any(identifier not in entity_by_id for identifier in selected)
                    or any(item not in faction_ids for item in resolution.faction_ids)
                    or any(item not in zone_ids for item in resolution.zones)
                    or any(item not in event_ids for item in resolution.events)
                ):
                    raise _ResolvedIntegrityError("mission selector resolution is invalid")
                dependencies[rule.id] = set(rule.depends_on)
            except _ResolvedIntegrityError:
                raise
            except (AttributeError, TypeError, ValueError) as error:
                raise _ResolvedIntegrityError("mission rule is invalid") from error
        if any(dep not in rule_ids for deps in dependencies.values() for dep in deps):
            raise _ResolvedIntegrityError("mission dependency endpoint is missing")
        remaining = {key: set(value) for key, value in dependencies.items()}
        while remaining:
            ready = [key for key, value in remaining.items() if not value]
            if not ready:
                raise _ResolvedIntegrityError("mission dependency cycle")
            for key in ready:
                remaining.pop(key)
                for value in remaining.values():
                    value.discard(key)

        if self.scoring is not None:
            aggregation_version = self.scoring.get("aggregation_version", "raw-v1")
            if (
                self.scoring.weight_policy != "normalized_sum_one"
                or self.scoring.aggregation not in {"count", "sum", "mean", "min", "max"}
                or self.scoring.direction not in {"maximize", "minimize"}
                or aggregation_version not in {"raw-v1", "utility-v1"}
                or (
                    aggregation_version == "utility-v1"
                    and (self.scoring.aggregation != "sum" or self.scoring.direction != "maximize")
                )
            ):
                raise _ResolvedIntegrityError("scoring weight policy is invalid")
            metric_ids: set[str] = set()
            weights = 0.0
            for metric in self.scoring.metrics:
                self._validate_selector_resolution_equivalence(
                    metric.selector,
                    metric.selector_resolution,
                    faction_ids=faction_ids,
                    zone_ids=zone_ids,
                    event_ids=event_ids,
                    allow_empty=aggregation_version == "utility-v1",
                )
                if metric.id in metric_ids:
                    raise _ResolvedIntegrityError("duplicate scoring metric")
                metric_ids.add(metric.id)
                weight = metric.weight
                if (
                    not isinstance(weight, (int, float))
                    or isinstance(weight, bool)
                    or not math.isfinite(float(weight))
                    or weight < 0
                    or metric.aggregation not in {"count", "sum", "mean", "min", "max"}
                    or metric.unit not in {"1", "m", "s", "points"}
                    or metric.direction not in {"maximize", "minimize"}
                    or not isinstance(metric.available, bool)
                ):
                    raise _ResolvedIntegrityError("scoring metric contract is invalid")
                if metric.available:
                    if (
                        not isinstance(metric.value, (int, float))
                        or isinstance(metric.value, bool)
                        or not math.isfinite(float(metric.value))
                    ):
                        raise _ResolvedIntegrityError("scoring value is invalid")
                elif metric.value is not None:
                    raise _ResolvedIntegrityError("scoring N/A value is invalid")
                if aggregation_version == "utility-v1":
                    normalization = metric.get("normalization")
                    normalization_values = (
                        normalization.values
                        if isinstance(normalization, _FrozenRecordV2)
                        else normalization
                    )
                    required = metric.get("required")
                    not_applicable_reason = metric.get("not_applicable_reason")
                    if (
                        not isinstance(normalization_values, Mapping)
                        or set(normalization_values) != {"lower_bound", "upper_bound"}
                        or not isinstance(required, bool)
                        or not isinstance(normalization_values.get("lower_bound"), (int, float))
                        or isinstance(normalization_values.get("lower_bound"), bool)
                        or not isinstance(normalization_values.get("upper_bound"), (int, float))
                        or isinstance(normalization_values.get("upper_bound"), bool)
                        or not math.isfinite(float(normalization_values["lower_bound"]))
                        or not math.isfinite(float(normalization_values["upper_bound"]))
                        or (
                            float(normalization_values["lower_bound"])
                            >= float(normalization_values["upper_bound"])
                            and not (
                                float(normalization_values["lower_bound"]) == 0.0
                                and float(normalization_values["upper_bound"]) == 0.0
                                and not metric.available
                                and not_applicable_reason == "selector_cardinality_zero"
                            )
                        )
                        or (metric.available and not_applicable_reason is not None)
                        or (not metric.available and not isinstance(not_applicable_reason, str))
                    ):
                        raise _ResolvedIntegrityError("utility scoring metric contract is invalid")
                plugin_ref = metric.get("plugin_ref")
                plugin_parameters = metric.get("plugin_parameters")
                plugin_evidence = metric.get("plugin_evidence")
                event_source = metric.get("event_source")
                if event_source is not None:
                    event_source_values = (
                        event_source.values
                        if isinstance(event_source, _FrozenRecordV2)
                        else event_source
                    )
                    expected_fields = {
                        "event_id",
                        "event_type",
                        "value_path",
                        "source",
                        "unit",
                        "aggregation",
                    }
                    source_event_id = (
                        event_source_values.get("event_id")
                        if isinstance(event_source_values, Mapping)
                        else None
                    )
                    value_path = (
                        event_source_values.get("value_path")
                        if isinstance(event_source_values, Mapping)
                        else None
                    )
                    if (
                        not isinstance(event_source_values, Mapping)
                        or set(event_source_values) != expected_fields
                        or source_event_id not in event_types
                        or event_source_values.get("event_type") != event_types.get(source_event_id)
                        or event_source_values.get("source") != "world_typed_event_receipt"
                        or not isinstance(value_path, str)
                        or re.fullmatch(
                            r"payload\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*",
                            value_path,
                        )
                        is None
                        or event_source_values.get("unit") != metric.unit
                        or event_source_values.get("aggregation") != "sum"
                        or plugin_ref is not None
                        or metric.available
                        or metric.value is not None
                    ):
                        raise _ResolvedIntegrityError(
                            "scoring event source differs from typed Resolved event policy"
                        )
                if plugin_ref is not None or plugin_parameters is not None:
                    evidence_values = (
                        plugin_evidence.values
                        if isinstance(plugin_evidence, _FrozenRecordV2)
                        else plugin_evidence
                    )
                    parameters_values = (
                        plugin_parameters.values
                        if isinstance(plugin_parameters, _FrozenRecordV2)
                        else plugin_parameters
                    )
                    metadata = next(
                        (
                            item
                            for item in self.model_registry_snapshot
                            if item.exact_ref == plugin_ref
                        ),
                        None,
                    )
                    if (
                        metadata is None
                        or not isinstance(parameters_values, Mapping)
                        or not isinstance(evidence_values, Mapping)
                        or evidence_values.get("model_ref") != metadata.exact_ref
                        or evidence_values.get("artifact_sha256") != metadata.artifact_sha256
                        or evidence_values.get("interface_version") != metadata.interface_version
                        or evidence_values.get("input_schema") != metadata.input_schema
                        or evidence_values.get("output_schema") != metadata.output_schema
                        or evidence_values.get("trusted") != metadata.trusted
                        or evidence_values.get("deterministic") != metadata.deterministic
                        or evidence_values.get("unit") != metric.unit
                        or evidence_values.get("parameters_hash") != _digest(parameters_values)
                    ):
                        raise _ResolvedIntegrityError(
                            "scoring plugin evidence differs from Registry snapshot"
                        )
                weights += float(weight)
            if abs(weights - 1.0) > 1e-9:
                raise _ResolvedIntegrityError("scoring weights are invalid")

        if self.controller_policy not in {None, "explicit_uncontrolled"}:
            raise _ResolvedIntegrityError("controller policy is invalid")
        controller_ids: set[str] = set()
        for slot in self.controller_slots:
            self._validate_selector_resolution_equivalence(
                slot.selector,
                slot.selector_resolution,
                faction_ids=faction_ids,
                zone_ids=zone_ids,
                event_ids=event_ids,
            )
            if (
                slot.action_schema_ref != "action-batch@2.0"
                or slot.observation_schema_ref != "observation@2.0"
            ):
                raise _ResolvedIntegrityError("controller schema is invalid")
            endpoint = slot.values.get("controller_endpoint_ref")
            if endpoint is not None:
                entity = entity_by_id.get(endpoint)
                if (
                    not isinstance(endpoint, str)
                    or not isinstance(entity, ResolvedEntityV2)
                    or entity.faction_id != slot.faction_id
                    or not entity.composition.communication_refs
                ):
                    raise _ResolvedIntegrityError("controller communication endpoint is invalid")
            inbox_capacity = slot.values.get("inbox_capacity", 256)
            if (
                not isinstance(inbox_capacity, int)
                or isinstance(inbox_capacity, bool)
                or not 1 <= inbox_capacity <= 4096
            ):
                raise _ResolvedIntegrityError("controller inbox capacity is invalid")
            controller_ids.add(slot.controller_id)
            for identifier in slot.resolved_entity_ids:
                entity = entity_by_id.get(identifier)
                if not isinstance(entity, ResolvedEntityV2):
                    raise _ResolvedIntegrityError("controller entity endpoint is missing")
                available: set[str] = set()
                if entity.composition.sensor_refs:
                    available.add("sensor")
                if entity.composition.communication_refs:
                    available.add("communication")
                if entity.composition.loadout_ref:
                    available.add("weapon")
                if any(item not in available for item in slot.required_capabilities):
                    raise _ResolvedIntegrityError("controller capability is missing")

        if self.visibility is not None:
            visibility_keys: set[tuple[Any, ...]] = set()
            for item in self.visibility.matrix:
                if item.view not in {"referee", "public", "faction", "controller"}:
                    raise _ResolvedIntegrityError("visibility view is invalid")
                if item.scope not in {"truth", "public", "own_and_contacts", "claimed_entities"}:
                    raise _ResolvedIntegrityError("visibility scope is invalid")
                if not isinstance(item.allow, bool):
                    raise _ResolvedIntegrityError("visibility allow is invalid")
                if (
                    item.view == "faction" and item.values.get("faction_id") not in faction_ids
                ) or (
                    item.view == "controller"
                    and self.controller_slots
                    and item.values.get("controller_id") not in controller_ids
                ):
                    raise _ResolvedIntegrityError("visibility endpoint is missing")
                if item.view == "public" and item.scope == "truth":
                    raise _ResolvedIntegrityError("visibility leaks truth")
                visibility_key = (
                    item.view,
                    item.values.get("faction_id"),
                    item.values.get("controller_id"),
                    item.scope,
                )
                if visibility_key in visibility_keys:
                    raise _ResolvedIntegrityError("duplicate visibility rule")
                visibility_keys.add(visibility_key)

    def _validate_integrity(self) -> None:
        if (
            self.compiler_version != COMPILER_VERSION
            or tuple(record.stage for record in self.compile_stage_trace) != COMPILER_STAGES_V2
            or tuple(record.ordinal for record in self.compile_stage_trace)
            != tuple(range(len(COMPILER_STAGES_V2)))
            or any(
                record.status != "completed" or record.duration_policy != "deterministic-none"
                for record in self.compile_stage_trace
            )
        ):
            raise _ResolvedIntegrityError("compiler trace is invalid")
        provenance = self.provenance.values
        package_fields = (
            "package_logical_hash",
            "package_content_hash",
            "package_archive_hash",
        )
        if (
            provenance.get("compiler_version") != self.compiler_version
            or provenance.get("catalog_hash") != self.catalog_hash
            or provenance.get("model_registry_hash") != self.model_registry_hash
            or any(not isinstance(provenance.get(field), str) for field in package_fields)
            or provenance.get("package_identity_hash")
            != _digest([provenance.get(field) for field in package_fields])
        ):
            raise _ResolvedIntegrityError("compiler provenance is invalid")
        self._validate_mission_control_integrity()
        declaration = self.world.spatial_damage_policy
        policy = self.spatial_effect_policy
        if (declaration is None) != (policy is None):
            raise _ResolvedIntegrityError("resolved spatial effect policy is invalid")
        if (
            declaration is not None
            and policy is not None
            and (
                policy.effect_binding.exact_ref != declaration.collision_effect_ref
                or policy.effect_binding.resource_type != "effects"
                or policy.damage_binding.resource_type != "damage_models"
                or policy.effect_binding.normalized_content.get("damage_model_ref")
                != policy.damage_binding.exact_ref
                or policy.magnitude_model != declaration.magnitude_model
                or dict(policy.magnitude_parameters) != dict(declaration.magnitude_parameters)
                or policy.output_unit != declaration.output_unit
            )
        ):
            raise _ResolvedIntegrityError("resolved spatial effect policy is invalid")
        metadata = {item.exact_ref: item for item in self.model_registry_snapshot}
        if len(metadata) != len(self.model_registry_snapshot):
            raise _ResolvedIntegrityError("duplicate model registry metadata")
        if (
            _digest([item.model_dump(mode="json") for item in self.model_registry_snapshot])
            != self.model_registry_hash
        ):
            raise _ResolvedIntegrityError("model registry hash mismatch")
        world_bindings = tuple(self.world_resource_bindings)
        world_index = {binding.exact_ref: binding for binding in world_bindings}
        if len(world_index) != len(world_bindings):
            raise _ResolvedIntegrityError("duplicate world resource binding")
        if tuple(world_index) != tuple(sorted(world_index)):
            raise _ResolvedIntegrityError("world resource bindings are not canonically ordered")
        for world_binding in world_bindings:
            self._validate_resource_binding_integrity(
                world_binding, world_binding.resource_type, metadata
            )
        map_binding = None if self.world.map_ref is None else world_index.get(self.world.map_ref)
        if self.world.map_ref is None:
            if any(binding.resource_type == "maps" for binding in world_bindings):
                raise _ResolvedIntegrityError("orphan world map binding")
        elif (
            map_binding is None
            or map_binding.resource_type != "maps"
            or map_binding.exact_ref != self.world.map_ref
        ):
            raise _ResolvedIntegrityError("resolved world map binding is invalid")
        policy_bindings = tuple(
            binding for binding in world_bindings if binding.resource_type != "maps"
        )
        if policy is None:
            if policy_bindings:
                raise _ResolvedIntegrityError("orphan world resource binding")
        else:
            if (
                world_index.get(policy.effect_binding.exact_ref) is not policy.effect_binding
                or world_index.get(policy.damage_binding.exact_ref) is not policy.damage_binding
            ):
                raise _ResolvedIntegrityError("world policy binding identity mismatch")
            try:
                expected_world_closure = resolve_world_resource_closure_v2(policy, policy_bindings)
            except ValueError as error:
                raise _ResolvedIntegrityError(
                    "world resource dependency binding missing or cyclic"
                ) from error
            if expected_world_closure != policy_bindings:
                raise _ResolvedIntegrityError("orphan world resource binding")
        implicit_fields = (
            "weapon_refs",
            "ammunition_refs",
            "effect_ref",
            "damage_model_ref",
            "weapon_ref",
            "energy_ref",
            "collision_shape_ref",
            "visualization_ref",
        )
        zone_ids = {zone.id for zone in self.world.zones}
        boundary_ids = [boundary.id for boundary in self.world.boundaries]
        valid_boundary_actions = {
            "reject_command",
            "constrain_motion",
            "stop",
            "reflect",
            "collision_effect",
            "deactivate",
            "mission_event",
        }
        if (
            len(boundary_ids) != len(set(boundary_ids))
            or boundary_ids != sorted(boundary_ids)
            or any(
                boundary.zone_id not in zone_ids
                or boundary.action not in valid_boundary_actions
                or boundary.point_on_edge not in {"inside", "outside"}
                or not isinstance(boundary.priority, int)
                or isinstance(boundary.priority, bool)
                for boundary in self.world.boundaries
            )
        ):
            raise _ResolvedIntegrityError("resolved world boundary topology is invalid")
        for entity in self.entities:
            self._validate_resolved_entity_integrity(entity, metadata)
            if not isinstance(entity, ResolvedEntityV2):
                continue
            deployment = entity.boundary_deployment
            if deployment is not None and (
                deployment.point_on_edge not in {"inside", "outside"}
                or len(deployment.allowed_zone_ids) != len(set(deployment.allowed_zone_ids))
                or len(deployment.excluded_zone_ids) != len(set(deployment.excluded_zone_ids))
                or set(deployment.allowed_zone_ids) & set(deployment.excluded_zone_ids)
                or (set(deployment.allowed_zone_ids) | set(deployment.excluded_zone_ids)) - zone_ids
            ):
                raise _ResolvedIntegrityError("entity boundary deployment is invalid")
            flat = [binding for values in entity.resource_bindings.values() for binding in values]
            index = {binding.exact_ref: binding for binding in flat}
            if len(index) != len(flat):
                raise _ResolvedIntegrityError("duplicate resource binding")
            for group, values in entity.resource_bindings.items():
                for binding in values:
                    self._validate_resource_binding_integrity(binding, group, metadata)
                    if binding.resource_type != group:
                        raise _ResolvedIntegrityError("binding resource type mismatch")
                    if binding.schema_version != "2.0":
                        raise _ResolvedIntegrityError("binding schema version mismatch")
                    try:
                        rebuilt = CatalogResourceV2(
                            schema_version="2.0",
                            resource_type=binding.resource_type,
                            id=binding.id,
                            version=binding.version,
                            engine_compatibility=binding.engine_compatibility,
                            model_id=binding.model_ref,
                            dependencies=binding.dependencies,
                            content=dict(binding.content),
                        )
                    except ValidationError as error:
                        raise _ResolvedIntegrityError("invalid binding identity") from error
                    if (
                        rebuilt.exact_ref != binding.exact_ref
                        or rebuilt.content_hash != binding.content_hash
                    ):
                        raise _ResolvedIntegrityError("binding content identity mismatch")
                    model = metadata.get(binding.model_ref)
                    evidence = binding.model_evidence
                    if model is None or (
                        evidence.model_ref,
                        evidence.artifact_sha256,
                        evidence.interface_version,
                        evidence.input_schema,
                        evidence.output_schema,
                        evidence.trusted,
                        evidence.deterministic,
                        evidence.resource_types,
                    ) != (
                        model.exact_ref,
                        model.artifact_sha256,
                        model.interface_version,
                        model.input_schema,
                        model.output_schema,
                        model.trusted,
                        model.deterministic,
                        model.resource_types,
                    ):
                        raise _ResolvedIntegrityError("binding model evidence mismatch")
                    if (
                        not evidence.trusted
                        or not evidence.deterministic
                        or evidence.interface_version != "2.0"
                        or binding.resource_type not in evidence.resource_types
                    ):
                        raise _ResolvedIntegrityError("model is ineligible for bound resource")
                    if (
                        dict(binding.units) != model.units
                        or dict(binding.field_units) != model.field_units
                    ):
                        raise _ResolvedIntegrityError("binding model units mismatch")
                    normalized = dict(binding.content)
                    required = binding.content.get("required_defaults", ())
                    if (
                        not isinstance(required, (list, tuple))
                        or any(not isinstance(item, str) or not item for item in required)
                        or len(required) != len(set(required))
                    ):
                        raise _ResolvedIntegrityError("invalid required default schema")
                    declared = binding.content.get("defaults", {})
                    for key, default in binding.defaults.items():
                        declaration = declared.get(key) if isinstance(declared, Mapping) else None
                        if (
                            key not in required
                            or not isinstance(declaration, Mapping)
                            or default.source.kind != "model_metadata"
                            or default.source.id != model.exact_ref
                            or default.input_value != declaration.get("value")
                            or default.input_unit != declaration.get("unit")
                            or default.conversion_ref != declaration.get("conversion_ref")
                            or default.unit != model.field_units.get(key, "1")
                        ):
                            raise _ResolvedIntegrityError("default evidence mismatch")
                        value_types = binding.content.get("default_value_types", {})
                        declared_type = (
                            value_types.get(key) if isinstance(value_types, Mapping) else None
                        )
                        if default.unit == "1":
                            valid_type = (
                                declared_type
                                in {
                                    "number",
                                    "integer",
                                    "boolean",
                                    "string",
                                }
                                and default.value_type == declared_type
                            )
                            valid_value = (
                                (
                                    declared_type == "number"
                                    and isinstance(default.input_value, (int, float))
                                    and not isinstance(default.input_value, bool)
                                    and math.isfinite(float(default.input_value))
                                )
                                or (
                                    declared_type == "integer"
                                    and isinstance(default.input_value, int)
                                    and not isinstance(default.input_value, bool)
                                )
                                or (
                                    declared_type == "boolean"
                                    and isinstance(default.input_value, bool)
                                )
                                or (
                                    declared_type == "string"
                                    and isinstance(default.input_value, str)
                                )
                            )
                        else:
                            valid_type = default.value_type is None
                            valid_value = (
                                isinstance(default.input_value, (int, float))
                                and not isinstance(default.input_value, bool)
                                and math.isfinite(float(default.input_value))
                            )
                        if not valid_type or not valid_value:
                            raise _ResolvedIntegrityError("default value contract mismatch")
                        expected_value = default.input_value
                        if default.conversion_ref is not None:
                            conversions = binding.content.get("trusted_unit_conversions", {})
                            conversion = (
                                conversions.get(default.conversion_ref)
                                if isinstance(conversions, Mapping)
                                else None
                            )
                            if (
                                not isinstance(conversion, Mapping)
                                or conversion.get("from") != default.input_unit
                                or conversion.get("to") != default.unit
                                or not isinstance(conversion.get("scale"), (int, float))
                                or isinstance(conversion.get("scale"), bool)
                                or not math.isfinite(float(conversion["scale"]))
                                or float(conversion["scale"]) <= 0.0
                                or not isinstance(expected_value, (int, float))
                                or isinstance(expected_value, bool)
                                or default.conversion_scale != float(conversion["scale"])
                            ):
                                raise _ResolvedIntegrityError("default conversion mismatch")
                            expected_value = float(expected_value) * float(conversion["scale"])
                        elif default.conversion_scale is not None:
                            raise _ResolvedIntegrityError("unexpected conversion scale")
                        if default.value != expected_value:
                            raise _ResolvedIntegrityError("default canonical value mismatch")
                        normalized[key] = default.value
                    if set(binding.defaults) != {
                        key for key in required if key not in binding.content
                    }:
                        raise _ResolvedIntegrityError("required default evidence missing")
                    if _json_value(normalized) != _json_value(binding.normalized_content):
                        raise _ResolvedIntegrityError("binding normalized defaults mismatch")
            composition = entity.composition
            direct: list[tuple[str, str | None]] = [
                ("platforms", composition.platform_ref),
                ("dynamics", composition.dynamics_ref),
                ("loadouts", composition.loadout_ref),
                ("energy", composition.energy_ref),
                ("collision_shapes", composition.collision_shape_ref),
                ("visualization_assets", composition.visualization_ref),
                *(("sensors", ref) for ref in composition.sensor_refs),
                *(("communications", ref) for ref in composition.communication_refs),
                *(("ammunition", ref) for ref in composition.ammunition),
            ]
            roots: set[str] = set()
            for expected_type, reference in direct:
                if reference is None:
                    continue
                direct_binding = index.get(reference)
                if direct_binding is None or direct_binding.resource_type != expected_type:
                    raise _ResolvedIntegrityError("composition binding missing or wrong type")
                roots.add(reference)
            reachable: set[str] = set()
            pending = list(roots)
            while pending:
                reference = pending.pop()
                if reference in reachable:
                    continue
                dependency_binding = index.get(reference)
                if dependency_binding is None:
                    raise _ResolvedIntegrityError("resource dependency missing")
                reachable.add(reference)
                refs = set(dependency_binding.dependencies)
                for field in implicit_fields:
                    value = dependency_binding.normalized_content.get(field)
                    if isinstance(value, str):
                        refs.add(value)
                    elif isinstance(value, Sequence) and not isinstance(
                        value, (str, bytes, bytearray)
                    ):
                        refs.update(str(item) for item in value)
                pending.extend(sorted(refs))
            if reachable != set(index):
                raise _ResolvedIntegrityError("orphan or incomplete resource closure")
            if dict(entity.runtime_initial.ammunition) != dict(composition.ammunition):
                raise _ResolvedIntegrityError("runtime ammunition mismatch")
        allowed_events = {
            "spawn",
            "despawn",
            "weather_change",
            "zone_activation",
            "jamming_start",
            "jamming_end",
            "component_suppression",
            "message",
            "mission_marker",
            "apply_effect",
            "spatial_effect_trigger",
        }
        event_index = {event.id: position for position, event in enumerate(self.events)}
        if len(event_index) != len(self.events):
            raise _ResolvedIntegrityError("duplicate resolved event")
        faction_ids = {faction.id for faction in self.factions}
        static_ids = {entity.id for entity in self.entities}
        active_ids = set(static_ids)
        active_controller_by_id = {
            entity.id: entity.controller_slot
            for entity in self.entities
            if entity.controller_slot is not None
        }
        spawned_ids: set[str] = set()
        spawned_entities: list[ResolvedEntityV2] = []
        controller_bindings = {
            entity.controller_slot for entity in self.entities if entity.controller_slot is not None
        }
        if len(controller_bindings) != sum(
            entity.controller_slot is not None for entity in self.entities
        ):
            raise _ResolvedIntegrityError("duplicate entity controller binding")
        previous_tick = -1

        for position, event in enumerate(self.events):
            if event.event_type not in allowed_events or event.trigger.kind != "tick":
                raise _ResolvedIntegrityError("invalid resolved event type or trigger")
            if not isinstance(event.priority, int) or isinstance(event.priority, bool):
                raise _ResolvedIntegrityError("resolved event priority is invalid")
            tick = event.trigger.tick
            if not isinstance(tick, int) or isinstance(tick, bool) or tick < previous_tick:
                raise _ResolvedIntegrityError("resolved event order is invalid")
            previous_tick = tick
            if any(
                dependency not in event_index or event_index[dependency] >= position
                for dependency in event.depends_on
            ):
                raise _ResolvedIntegrityError("resolved event dependency is invalid")
            payload = event.payload
            try:
                _validate_event_payload(event.event_type, payload)
            except ValueError as error:
                raise _ResolvedIntegrityError("resolved event payload is invalid") from error
            if "health" in payload.values:
                raise _ResolvedIntegrityError("event payload contains forbidden health mutation")
            if event.event_type == "message":
                body = payload.body
                if not isinstance(body, str) or not 0 < len(body) <= 4096:
                    raise _ResolvedIntegrityError("message body contract is invalid")
            if event.event_type == "mission_marker":
                if (
                    set(payload.values) - {"marker_id", "zone_id", "position_m"}
                    or not isinstance(payload.values.get("marker_id"), str)
                    or not payload.values["marker_id"]
                ):
                    raise _ResolvedIntegrityError("mission marker payload is invalid")
                marker_position = payload.values.get("position_m")
                if marker_position is not None and (
                    not isinstance(marker_position, (list, tuple))
                    or len(marker_position) != 3
                    or any(
                        not isinstance(axis, (int, float))
                        or isinstance(axis, bool)
                        or not math.isfinite(float(axis))
                        for axis in marker_position
                    )
                ):
                    raise _ResolvedIntegrityError("mission marker position is invalid")
            if event.event_type == "spawn":
                spawned = payload.entity
                self._validate_resolved_entity_integrity(spawned, metadata)
                if (
                    spawned.id in static_ids
                    or spawned.id in active_ids
                    or spawned.faction_id not in faction_ids
                ):
                    raise _ResolvedIntegrityError("spawn lifecycle conflict")
                binding = spawned.controller_slot
                if binding is not None and (
                    not isinstance(binding, str) or not binding or binding in controller_bindings
                ):
                    raise _ResolvedIntegrityError("spawn controller binding is invalid")
                if binding is not None:
                    controller_bindings.add(binding)
                    active_controller_by_id[spawned.id] = binding
                spawned_ids.add(spawned.id)
                active_ids.add(spawned.id)
                spawned_entities.append(spawned)
                groups = spawned.resource_bindings
                group_values = groups.values if isinstance(groups, _FrozenRecordV2) else groups
                for resource_type, bindings in group_values.items():
                    for binding in bindings:
                        self._validate_resource_binding_integrity(binding, resource_type, metadata)
            if event.event_type == "despawn":
                despawned_id = payload.entity_id
                if despawned_id not in active_ids:
                    raise _ResolvedIntegrityError("despawn lifecycle endpoint is inactive")
                active_ids.remove(despawned_id)
                prior_binding = active_controller_by_id.pop(despawned_id, None)
                if prior_binding is not None:
                    controller_bindings.discard(prior_binding)
            if event.event_type == "weather_change":
                if "environment_ref" in payload.values:
                    raise _ResolvedIntegrityError("weather event contains lazy reference")
                self._validate_resource_binding_integrity(
                    payload.environment_binding, "environments", metadata
                )
            if event.event_type == "apply_effect":
                effect = payload.effect_binding
                damage = payload.damage_binding
                self._validate_resource_binding_integrity(effect, "effects", metadata)
                self._validate_resource_binding_integrity(damage, "damage_models", metadata)
                if (
                    effect.resource_type != "effects"
                    or damage.resource_type != "damage_models"
                    or effect.exact_ref != f"{effect.id}@{effect.version}"
                    or damage.exact_ref != f"{damage.id}@{damage.version}"
                    or effect.content["damage_model_ref"] != damage.exact_ref
                ):
                    raise _ResolvedIntegrityError("effect resource chain is invalid")
            if event.event_type == "spatial_effect_trigger":
                effect = payload.effect_binding
                damage = payload.damage_binding
                self._validate_resource_binding_integrity(effect, "effects", metadata)
                self._validate_resource_binding_integrity(damage, "damage_models", metadata)
                if (
                    effect.resource_type != "effects"
                    or damage.resource_type != "damage_models"
                    or effect.content["damage_model_ref"] != damage.exact_ref
                ):
                    raise _ResolvedIntegrityError("spatial trigger effect chain is invalid")
                secondary_effect = payload.values.get("secondary_effect_binding")
                secondary_damage = payload.values.get("secondary_damage_binding")
                if secondary_effect is not None or secondary_damage is not None:
                    if secondary_effect is None or secondary_damage is None:
                        raise _ResolvedIntegrityError("secondary effect chain is incomplete")
                    self._validate_resource_binding_integrity(secondary_effect, "effects", metadata)
                    self._validate_resource_binding_integrity(
                        secondary_damage, "damage_models", metadata
                    )
                    if (
                        secondary_effect.resource_type != "effects"
                        or secondary_damage.resource_type != "damage_models"
                        or secondary_effect.content["damage_model_ref"]
                        != secondary_damage.exact_ref
                    ):
                        raise _ResolvedIntegrityError("secondary effect chain is invalid")

        # Controller selectors are compiled against the complete immutable endpoint
        # set, including entities materialized by validated spawn events.  Integrity
        # must use that same endpoint universe instead of treating future entities
        # as dangling controller claims.
        entity_by_id = {entity.id: entity for entity in (*self.entities, *spawned_entities)}
        for event in self.events:
            if event.event_type != "spatial_effect_trigger":
                continue
            payload_values = event.payload.values
            source_ids = payload_values["source_entity_ids"]
            selectors = [payload_values["target_selector"].values]
            secondary_selector = payload_values.get("secondary_target_selector")
            if secondary_selector is not None:
                selectors.append(secondary_selector.values)
            if (
                any(entity_id not in entity_by_id for entity_id in source_ids)
                or any(
                    entity_id not in entity_by_id
                    for selector in selectors
                    for field in ("entity_ids", "exclude_entity_ids")
                    for entity_id in selector.get(field, ())
                )
                or (
                    payload_values["source_kind"] == "zone_entry"
                    and payload_values["zone_id"] not in zone_ids
                )
            ):
                raise _ResolvedIntegrityError("spatial trigger endpoint or zone is invalid")
        slot_ids: set[str] = set()
        controller_ids: set[str] = set()
        claimed_exclusivity: dict[str, bool] = {}
        slot_by_endpoint: dict[str, Any] = {}
        for slot in self.controller_slots:
            try:
                slot_id = slot.id
                controller_id = slot.controller_id
                entity_ids = tuple(slot.resolved_entity_ids)
                selector_entity_ids = tuple(slot.selector_resolution.entity_ids)
                if (
                    not isinstance(slot_id, str)
                    or not slot_id
                    or slot_id in slot_ids
                    or not isinstance(controller_id, str)
                    or not controller_id
                    or controller_id in controller_ids
                    or not isinstance(slot.exclusive, bool)
                    or not entity_ids
                    or entity_ids != selector_entity_ids
                    or tuple(sorted(entity_ids)) != entity_ids
                    or len(entity_ids) != len(set(entity_ids))
                    or any(identifier not in entity_by_id for identifier in entity_ids)
                    or any(
                        entity_by_id[identifier].faction_id != slot.faction_id
                        for identifier in entity_ids
                    )
                ):
                    raise _ResolvedIntegrityError("controller slot claim is invalid")
                if any(
                    identifier in claimed_exclusivity
                    and (slot.exclusive or claimed_exclusivity[identifier])
                    for identifier in entity_ids
                ):
                    raise _ResolvedIntegrityError("exclusive controller claims conflict")
                for identifier in entity_ids:
                    claimed_exclusivity[identifier] = (
                        claimed_exclusivity.get(identifier, False) or slot.exclusive
                    )
                slot_ids.add(slot_id)
                controller_ids.add(controller_id)
                slot_by_endpoint[slot_id] = slot
                slot_by_endpoint[controller_id] = slot
            except _ResolvedIntegrityError:
                raise
            except (AttributeError, TypeError, ValueError) as error:
                raise _ResolvedIntegrityError("controller slot is invalid") from error
        reserved_exclusive_slots: set[str] = set()
        for spawned in spawned_entities:
            controller_binding = spawned.controller_slot
            if controller_binding is None:
                continue
            reservation_slot = slot_by_endpoint.get(controller_binding)
            if reservation_slot is None:
                if controller_binding != f"controller/{spawned.id}":
                    raise _ResolvedIntegrityError("spawn controller endpoint is missing")
                continue
            available: set[str] = set()
            if spawned.composition.sensor_refs:
                available.add("sensor")
            if spawned.composition.communication_refs:
                available.add("communication")
            if spawned.composition.loadout_ref:
                available.add("weapon")
            if spawned.faction_id != reservation_slot.faction_id or any(
                item not in available for item in reservation_slot.required_capabilities
            ):
                raise _ResolvedIntegrityError("spawn controller reservation is incompatible")
            if reservation_slot.exclusive and (
                reservation_slot.resolved_entity_ids
                or reservation_slot.id in reserved_exclusive_slots
            ):
                raise _ResolvedIntegrityError("exclusive spawn controller reservation conflicts")
            if reservation_slot.exclusive:
                reserved_exclusive_slots.add(reservation_slot.id)


class ScenarioCompilerV2:
    """Compile one normalized package into a source-independent resolved value."""

    def __init__(self, *, catalog: CatalogV2) -> None:
        self._catalog = catalog

    def compile(self, package: ScenarioPackageV2) -> ResolvedScenarioV2:
        current: Any = package
        completed: list[StageRecordV2] = []
        for ordinal, stage in enumerate(COMPILER_STAGES_V2):
            try:
                current = getattr(self, f"_stage_{stage}")(current)
            except CompilerErrorV2 as error:
                error.stage = stage
                error.trace = tuple(completed)
                raise
            completed.append(StageRecordV2(stage=stage, ordinal=ordinal))
        if not isinstance(current, PipelineContextV2) or current.resolved is None:
            raise self._error(
                "scenario.pipeline_invalid",
                ("freeze_hash",),
                None,
                "pipeline did not produce a resolved scenario",
                "complete freeze_hash stage",
            )
        return current.resolved

    def compile_with_trace(
        self, package: ScenarioPackageV2
    ) -> tuple[ResolvedScenarioV2, tuple[StageRecordV2, ...]]:
        resolved = self.compile(package)
        return resolved, resolved.compile_stage_trace

    @staticmethod
    def _advance(value: Any, stage: str) -> PipelineContextV2:
        if not isinstance(value, PipelineContextV2):
            raise CompilerErrorV2(
                "scenario.pipeline_context_missing",
                file="scenario.yaml",
                path=(stage,),
                value=value,
                reason="stage input is not PipelineContextV2",
                suggestion="preserve typed context",
            )
        ordinal = COMPILER_STAGES_V2.index(stage)
        if value.completed_stages != COMPILER_STAGES_V2[:ordinal]:
            raise CompilerErrorV2(
                "scenario.pipeline_context_missing",
                file="scenario.yaml",
                path=(stage,),
                value=value.completed_stages,
                reason="prior stage transformation is missing",
                suggestion="execute every stage in declared order",
            )
        return replace(value, completed_stages=(*value.completed_stages, stage))

    @staticmethod
    def _pipeline_fail(reason: str) -> NoReturn:
        raise CompilerErrorV2(
            "scenario.pipeline_context_missing",
            file="scenario.yaml",
            path=("pipeline",),
            value=reason,
            reason=reason,
            suggestion="repair the owning stage input",
        )

    @staticmethod
    def _schema_shape_error(path: tuple[str, ...], value: Any, expected: str) -> CompilerErrorV2:
        section = path[0] if path else "scenario"
        file_by_section = {
            "entities": "entities.yaml",
            "formations": "formations.yaml",
            "factions": "factions.yaml",
            "relationships": "factions.yaml",
            "world": "world.yaml",
            "events": "events.yaml",
            "mission_rules": "mission_rules.yaml",
            "score_metrics": "scoring.yaml",
            "scoring": "scoring.yaml",
            "controller_slots": "controller_slots.yaml",
            "visibility": "visibility.yaml",
        }
        return CompilerErrorV2(
            "scenario.schema_shape_invalid",
            file=file_by_section.get(section, "scenario.yaml"),
            path=path or ("scenario",),
            value=value,
            reason=f"{'.'.join(path) or 'scenario'} must be {expected}",
            suggestion="provide the declared JSON container shape for schema version 2.0",
        )

    @classmethod
    def _validate_schema_structure(cls, raw: Any) -> dict[str, Any]:
        """Reject unsafe container shapes before domain stages inspect the document."""

        def mapping(value: Any, path: tuple[str, ...]) -> Mapping[str, Any]:
            if not isinstance(value, Mapping):
                raise cls._schema_shape_error(path, value, "an object")
            return value

        def sequence(value: Any, path: tuple[str, ...]) -> Sequence[Any]:
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
                raise cls._schema_shape_error(path, value, "an array")
            return value

        def member_mappings(value: Any, path: tuple[str, ...]) -> tuple[Mapping[str, Any], ...]:
            values = sequence(value, path)
            resolved: list[Mapping[str, Any]] = []
            for index, item in enumerate(values):
                resolved.append(mapping(item, (*path, str(index))))
            return tuple(resolved)

        def optional_mapping(
            owner: Mapping[str, Any], field: str, path: tuple[str, ...]
        ) -> Mapping[str, Any] | None:
            if field not in owner:
                return None
            return mapping(owner[field], (*path, field))

        def required_mapping(
            owner: Mapping[str, Any], field: str, path: tuple[str, ...]
        ) -> Mapping[str, Any]:
            if field not in owner:
                raise cls._schema_shape_error((*path, field), "<missing>", "an object")
            return mapping(owner[field], (*path, field))

        def optional_sequence(
            owner: Mapping[str, Any], field: str, path: tuple[str, ...]
        ) -> Sequence[Any] | None:
            if field not in owner:
                return None
            return sequence(owner[field], (*path, field))

        def validate_initial(owner: Mapping[str, Any], path: tuple[str, ...]) -> None:
            initial = required_mapping(owner, "initial_state", path)
            optional_mapping(initial, "position", (*path, "initial_state"))
            optional_mapping(initial, "component_states", (*path, "initial_state"))
            optional_mapping(owner, "deployment", path)
            optional_mapping(owner, "ammunition", path)
            for field in ("component_refs", "target_domains", "tags"):
                optional_sequence(owner, field, path)

        def validate_condition(condition: Mapping[str, Any], path: tuple[str, ...]) -> None:
            optional_mapping(condition, "selector", path)
            optional_mapping(condition, "parameters", path)
            operands = optional_sequence(condition, "operands", path)
            if operands is not None:
                for index, operand in enumerate(operands):
                    operand_path = (*path, "operands", str(index))
                    validate_condition(mapping(operand, operand_path), operand_path)

        document = mapping(raw, ("scenario",))
        normalized = dict(document)

        sequence_sections = (
            "entities",
            "formations",
            "factions",
            "relationships",
            "events",
            "mission_rules",
            "score_metrics",
            "controller_slots",
            "visibility",
        )
        sections: dict[str, tuple[Mapping[str, Any], ...]] = {}
        for section in sequence_sections:
            if section in document:
                sections[section] = member_mappings(document[section], (section,))
        if "mission_states" in document:
            sequence(document["mission_states"], ("mission_states",))

        for index, entity in enumerate(sections.get("entities", ())):
            validate_initial(entity, ("entities", str(index)))

        path: tuple[str, ...]
        for index, formation in enumerate(sections.get("formations", ())):
            path = ("formations", str(index))
            template = required_mapping(formation, "entity_template", path)
            validate_initial(template, (*path, "entity_template"))
            offsets = optional_sequence(formation, "offsets_m", path)
            if offsets is not None:
                for offset_index, offset in enumerate(offsets):
                    sequence(offset, (*path, "offsets_m", str(offset_index)))

        for index, faction in enumerate(sections.get("factions", ())):
            optional_sequence(faction, "tags", ("factions", str(index)))

        world = mapping(document["world"], ("world",)) if "world" in document else None
        if world is not None:
            optional_mapping(world, "coordinate_frame", ("world",))
            optional_mapping(world, "map_binding", ("world",))
            optional_mapping(world, "map_transform", ("world",))
            zones = member_mappings(world["zones"], ("world", "zones")) if "zones" in world else ()
            for index, zone in enumerate(zones):
                path = ("world", "zones", str(index))
                optional_mapping(zone, "geometry", path)
                coordinates = optional_sequence(zone, "coordinates_m", path)
                if coordinates is not None:
                    for coordinate_index, coordinate in enumerate(coordinates):
                        sequence(
                            coordinate,
                            (*path, "coordinates_m", str(coordinate_index)),
                        )
                for field in ("domains", "tags"):
                    optional_sequence(zone, field, path)
            boundaries = (
                member_mappings(world["boundaries"], ("world", "boundaries"))
                if "boundaries" in world
                else ()
            )
            for index, boundary in enumerate(boundaries):
                path = ("world", "boundaries", str(index))
                optional_mapping(boundary, "geometry", path)
                optional_sequence(boundary, "domains", path)

        for index, event in enumerate(sections.get("events", ())):
            path = ("events", str(index))
            required_mapping(event, "trigger", path)
            payload = optional_mapping(event, "payload", path)
            optional_sequence(event, "depends_on", path)
            if payload is not None:
                spawned = optional_mapping(payload, "entity", (*path, "payload"))
                if spawned is not None:
                    validate_initial(spawned, (*path, "payload", "entity"))
                optional_mapping(payload, "target_selector", (*path, "payload"))
                optional_mapping(payload, "position", (*path, "payload"))

        for index, rule in enumerate(sections.get("mission_rules", ())):
            path = ("mission_rules", str(index))
            condition = required_mapping(rule, "condition", path)
            validate_condition(condition, (*path, "condition"))
            optional_sequence(rule, "depends_on", path)

        scoring = mapping(document["scoring"], ("scoring",)) if "scoring" in document else None
        if scoring is not None and "metrics" in scoring:
            metrics = member_mappings(scoring["metrics"], ("scoring", "metrics"))
            for index, metric in enumerate(metrics):
                path = ("scoring", "metrics", str(index))
                optional_mapping(metric, "selector", path)
                optional_mapping(metric, "event_source", path)

        for index, slot in enumerate(sections.get("controller_slots", ())):
            path = ("controller_slots", str(index))
            required_mapping(slot, "selector", path)
            optional_sequence(slot, "required_capabilities", path)
            endpoint = slot.get("controller_endpoint_ref")
            if endpoint is not None and not isinstance(endpoint, str):
                raise ValueError("controller endpoint must be a string")
            inbox_capacity = slot.get("inbox_capacity", 256)
            if (
                not isinstance(inbox_capacity, int)
                or isinstance(inbox_capacity, bool)
                or not 1 <= inbox_capacity <= 4096
            ):
                raise ValueError("controller inbox capacity must be within 1..4096")

        return normalized

    def _stage_schema(self, value: Any) -> PipelineContextV2:
        if not isinstance(value, ScenarioPackageV2):
            raise CompilerErrorV2(
                "scenario.pipeline_invalid",
                file="scenario.yaml",
                path=("schema",),
                value=value,
                reason="schema stage input is not ScenarioPackageV2",
                suggestion="provide a V2 package",
            )
        source_value: Any = "<unavailable>"
        try:
            source_value = _json_value(value.document)
            raw = self._validate_schema_structure(source_value)
            return self._schema_context(value, raw)
        except CompilerErrorV2:
            raise
        except (ValidationError, TypeError, AttributeError, KeyError, ValueError) as error:
            raise self._schema_shape_error(
                ("scenario",),
                source_value,
                f"a structurally valid schema 2.0 document ({type(error).__name__}: {error})",
            ) from error

    def _schema_context(self, package: ScenarioPackageV2, raw: dict[str, Any]) -> PipelineContextV2:
        if "schema_version" not in raw or raw["schema_version"] != "2.0":
            self._pipeline_fail("scenario schema version is invalid")
        raw.pop("display_name", None)
        if any(
            not isinstance(entity.get("platform_ref"), str) for entity in raw.get("entities", ())
        ):
            self._pipeline_fail("entity platform_ref must be a string")
        extended_mission_control = any(
            key in raw
            for key in (
                "mission_states",
                "scoring",
                "controller_slots",
                "controller_policy",
            )
        )
        events = _json_value(raw["events"]) if "events" in raw else []
        if not isinstance(events, list):
            raise self._schema_shape_error(("events",), events, "an array")
        if extended_mission_control:
            world = raw.get("world")
            if isinstance(world, dict):
                ticks = [
                    trigger["tick"]
                    for item in events
                    if isinstance(item, Mapping)
                    and isinstance((trigger := item.get("trigger")), Mapping)
                    and isinstance(trigger.get("tick"), int)
                    and not isinstance(trigger["tick"], bool)
                ]
                world.setdefault("duration_ticks", max(ticks, default=0) + 1)
                world.setdefault("tick_seconds", 1.0)
            for item in events:
                if not isinstance(item, dict):
                    continue
                trigger = item.get("trigger")
                if isinstance(trigger, dict) and set(trigger) == {"tick"}:
                    item["trigger"] = {"kind": "tick", "tick": trigger["tick"]}
                if item.get("event_type") == "mission_marker" and item.get("payload") == {}:
                    item["payload"] = {"marker_id": item.get("id")}
            raw["events"] = events
        mission_declarations = {
            key: _json_value(raw.get(key))
            for key in (
                "mission_rules",
                "mission_states",
                "scoring",
                "score_metrics",
                "controller_slots",
                "controller_policy",
            )
            if key in raw
        }
        visibility_declarations = {
            "declared": "visibility" in raw,
            "rules": _json_value(raw.get("visibility", ())),
        }
        return PipelineContextV2(
            package=package,
            compiler=self,
            completed_stages=("schema",),
            parsed_schema=_freeze(raw),
            event_declarations=_freeze(events),
            mission_declarations=_freeze(mission_declarations),
            visibility_declarations=_freeze(visibility_declarations),
            extended_mission_control=extended_mission_control,
            package_logical_hash=package.logical_hash,
            package_content_hash=package.content_hash,
            package_archive_hash=package.archive_hash,
            audit_hashes=_freeze(
                {
                    "logical": package.logical_hash,
                    "content": package.content_hash,
                    "archive": package.archive_hash,
                }
            ),
            scenario_id=str(raw.get("scenario_id", "")),
        )

    def _stage_resource_versions(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "resource_versions")
        raw = context.parsed_schema
        if raw is None:
            self._pipeline_fail("parsed schema is missing")
        refs: list[str] = []
        types = {"platform_ref": "platforms", "dynamics_ref": "dynamics", "loadout_ref": "loadouts"}
        for formation in raw.get("formations", ()):
            template = formation.get("entity_template", {})
            for key, resource_type in types.items():
                ref = template.get(key)
                if isinstance(ref, str):
                    refs.append(ref)
                    try:
                        self._catalog.resolve(resource_type, ref)
                    except CatalogResolutionErrorV2 as error:
                        if key == "dynamics_ref":
                            try:
                                self._catalog.resolve("platforms", ref)
                            except CatalogResolutionErrorV2:
                                pass
                            else:
                                continue
                        raise CompilerErrorV2(
                            "scenario.resource_missing",
                            file="formations.yaml",
                            path=(key,),
                            value=ref,
                            reason=str(error),
                            suggestion="use an exact catalog ref",
                        ) from error
        for entity in raw.get("entities", ()):
            ref = entity.get("platform_ref")
            if isinstance(ref, str):
                refs.append(ref)
                if "@" not in ref:
                    raise CompilerErrorV2(
                        "scenario.resource_ref_invalid",
                        file="entities.yaml",
                        path=("entities", "platform_ref"),
                        value=ref,
                        reason="resource ref must be exact and versioned",
                        suggestion="use resource.id@version",
                    )
                try:
                    self._catalog.resolve("platforms", ref)
                except CatalogResolutionErrorV2 as error:
                    raise CompilerErrorV2(
                        "scenario.resource_missing",
                        file="entities.yaml",
                        path=("entities", "platform_ref"),
                        value=ref,
                        reason=str(error),
                        suggestion="use an exact catalog ref",
                    ) from error
        event_bindings: dict[str, ResolvedResourceBindingV2] = {}
        world_declaration = raw.get("world")
        map_binding: ResolvedResourceBindingV2 | None = None
        map_ref = (
            world_declaration.get("map_ref") if isinstance(world_declaration, Mapping) else None
        )
        if map_ref is not None:
            try:
                if not isinstance(map_ref, str) or "@" not in map_ref:
                    raise TypeError("map ref must be an exact versioned string")
                map_binding = self._resource_binding(self._catalog.resolve("maps", map_ref))
            except (CatalogResolutionErrorV2, TypeError) as error:
                raise CompilerErrorV2(
                    "scenario.map_resource_invalid",
                    file="world.yaml",
                    path=("world", "map_ref"),
                    value=map_ref,
                    reason=str(error),
                    suggestion="reference an exact map Catalog resource",
                ) from error
        spatial_declaration = (
            world_declaration.get("spatial_damage_policy")
            if isinstance(world_declaration, Mapping)
            else None
        )
        if isinstance(spatial_declaration, Mapping):
            effect_ref = spatial_declaration.get("collision_effect_ref")
            try:
                if not isinstance(effect_ref, str):
                    raise TypeError("collision effect ref must be a string")
                effect_resource = self._catalog.resolve("effects", effect_ref)
                damage_ref = effect_resource.content.get("damage_model_ref")
                if not isinstance(damage_ref, str):
                    raise ValueError("effect omits an exact damage model reference")
                damage_resource = self._catalog.resolve("damage_models", damage_ref)
            except (CatalogResolutionErrorV2, TypeError, ValueError) as error:
                raise CompilerErrorV2(
                    "scenario.spatial_damage_policy_invalid",
                    file="world.yaml",
                    path=("world", "spatial_damage_policy", "collision_effect_ref"),
                    value=effect_ref,
                    reason="spatial damage policy must reference an exact effect chain",
                    suggestion="reference a versioned effect whose damage model is available",
                ) from error
            catalog_index = {item.exact_ref: item for item in self._catalog.snapshot()}
            world_visiting: set[str] = set()
            world_visited: set[str] = set()

            def bind_world_dependency(reference: str) -> None:
                if reference in world_visiting:
                    raise CompilerErrorV2(
                        "scenario.spatial_damage_policy_invalid",
                        file="world.yaml",
                        path=("world", "spatial_damage_policy", "collision_effect_ref"),
                        value=reference,
                        reason="world resource dependency cycle",
                        suggestion="remove the cyclic Catalog dependency",
                    )
                if reference in world_visited:
                    return
                resource = catalog_index.get(reference)
                if resource is None:
                    raise CompilerErrorV2(
                        "scenario.spatial_damage_policy_invalid",
                        file="world.yaml",
                        path=("world", "spatial_damage_policy", "collision_effect_ref"),
                        value=reference,
                        reason="world resource dependency is missing",
                        suggestion="install the complete exact Catalog dependency closure",
                    )
                world_visiting.add(reference)
                for dependency in sorted(resource.dependencies):
                    bind_world_dependency(dependency)
                world_visiting.remove(reference)
                world_visited.add(reference)
                event_bindings[reference] = self._resource_binding(resource)

            bind_world_dependency(effect_resource.exact_ref)
            bind_world_dependency(damage_resource.exact_ref)
        for event in context.event_declarations or ():
            if not isinstance(event, Mapping):
                continue
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            references: list[tuple[ResourceTypeV2, str]] = []
            environment_ref = payload.get("environment_ref")
            if isinstance(environment_ref, str):
                references.append(("environments", environment_ref))
            effect_ref = payload.get("effect_ref")
            if isinstance(effect_ref, str):
                references.append(("effects", effect_ref))
            for resource_type, reference in references:
                try:
                    resource = self._catalog.resolve(resource_type, reference)
                    event_bindings[reference] = self._resource_binding(resource)
                    damage_ref = resource.content.get("damage_model_ref")
                    if resource_type == "effects" and isinstance(damage_ref, str):
                        damage = self._catalog.resolve("damage_models", damage_ref)
                        event_bindings[damage_ref] = self._resource_binding(damage)
                except (CatalogResolutionErrorV2, ValueError):
                    continue
        return replace(
            context,
            resolved_resources=tuple(sorted(refs)),
            event_resource_bindings=MappingProxyType(event_bindings),
            catalog_hash=self._catalog.content_hash,
            model_registry_hash=self._catalog.model_registry.content_hash,
            model_registry_snapshot=self._catalog.model_registry.snapshot(),
            world_map_binding=map_binding,
        )

    def _stage_defaults(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "defaults")
        if context.resolved_resources is None or context.parsed_schema is None:
            self._pipeline_fail("resolved resources are missing")
        for formation in context.parsed_schema.get("formations", ()):
            state = formation.get("entity_template", {}).get("initial_state", {})
            if "heading_deg" not in state:
                self._pipeline_fail("required heading default is missing")
        return replace(
            context,
            materialized_defaults=_freeze({"resource_refs": context.resolved_resources}),
        )

    def _stage_units(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "units")
        if context.materialized_defaults is None or context.parsed_schema is None:
            self._pipeline_fail("materialized defaults are missing")
        for formation in context.parsed_schema.get("formations", ()):
            velocity = (
                formation.get("entity_template", {}).get("initial_state", {}).get("velocity_mps")
            )
            if velocity is not None and any(
                not isinstance(axis, (int, float)) or isinstance(axis, bool) for axis in velocity
            ):
                self._pipeline_fail("velocity units are invalid")
        return replace(context, normalized_units=_freeze({"velocity": "m/s", "position": "m"}))

    def _stage_factions_relationships(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "factions_relationships")
        if context.normalized_units is None or context.parsed_schema is None:
            self._pipeline_fail("normalized units are missing")
        try:
            factions = tuple(
                FactionV2.model_validate(item) for item in context.parsed_schema.get("factions", ())
            )
            relationships = tuple(
                RelationshipV2.model_validate(item)
                for item in context.parsed_schema.get("relationships", ())
            )
        except ValidationError as error:
            first = error.errors()[0]
            raise self._error(
                "scenario.schema_invalid",
                tuple(str(item) for item in first.get("loc", ())),
                first.get("input"),
                str(first.get("msg", "invalid faction graph")),
                "correct factions and relationships according to schema 2.0",
                file="factions.yaml",
            ) from error
        faction_ids = {item.id for item in factions}
        if len(faction_ids) != len(factions):
            raise self._error(
                "scenario.faction_duplicate",
                ("factions",),
                tuple(item.id for item in factions),
                "faction IDs must be globally unique",
                "rename duplicate factions",
                file="factions.yaml",
            )
        if any(
            item.source_faction_id not in faction_ids or item.target_faction_id not in faction_ids
            for item in relationships
        ):
            self._pipeline_fail("relationship endpoint is missing")
        return replace(context, factions=factions, relationships=relationships)

    def _stage_formation_expansion(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "formation_expansion")
        if context.factions is None or context.parsed_schema is None:
            self._pipeline_fail("faction graph is missing")
        formations = tuple(context.parsed_schema.get("formations", ()))
        if any("{index" not in str(item.get("id_pattern", "")) for item in formations):
            self._pipeline_fail("formation ID pattern is invalid")
        expanded: list[Any] = []
        for entity in context.parsed_schema.get("entities", ()):
            try:
                normalized = _json_value(entity)
                if not isinstance(normalized, dict):
                    self._pipeline_fail("entity JSON normalization is not an object")
                normalized.pop("deployment", None)
                state = normalized.get("initial_state", {})
                if isinstance(state, dict) and "position" in state:
                    state.pop("position", None)
                    state["position_m"] = [0.0, 0.0, 0.0]
                spec = EntitySpecV2.model_validate(normalized)
                expanded.append(
                    EntityDraftV2(
                        entity=spec,
                        raw_initial=_freeze(_json_value(entity.get("initial_state", {}))),
                        raw_entity=_freeze(_json_value(entity)),
                    )
                )
            except ValidationError:
                expanded.append(_record(entity))
        for formation in formations:
            template = _json_value(formation.get("entity_template", {}))
            pattern = str(formation.get("id_pattern"))
            for index in range(int(formation.get("count", 0))):
                member = dict(template)
                member["id"] = pattern.format(index=index)
                slot = member.get("controller_slot")
                if isinstance(slot, str):
                    member["controller_slot"] = f"{slot}/{member['id']}"
                try:
                    normalized = _json_value(member)
                    if not isinstance(normalized, dict):
                        self._pipeline_fail("formation JSON normalization is not an object")
                    normalized.pop("_formation_offset_m", None)
                    normalized.pop("deployment", None)
                    state = normalized.get("initial_state", {})
                    if isinstance(state, dict) and "position" in state:
                        state.pop("position", None)
                        state["position_m"] = [0.0, 0.0, 0.0]
                    spec = EntitySpecV2.model_validate(normalized)
                    expanded.append(
                        EntityDraftV2(
                            entity=spec,
                            raw_initial=_freeze(_json_value(member.get("initial_state", {}))),
                            raw_entity=_freeze(_json_value(member)),
                            formation_id=str(formation.get("id", "")) or None,
                            formation_index=index,
                        )
                    )
                except ValidationError:
                    expanded.append(_record(member))
        return replace(
            context,
            expanded_entities=tuple(expanded),
            formation_ids=tuple(item.get("id") for item in formations),
            expanded_entity_count=len(expanded),
        )

    def _stage_compatibility(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "compatibility")
        if context.expanded_entities is None:
            self._pipeline_fail("expanded entities are missing")
        if not context.resolved_resources and context.expanded_entities:
            self._pipeline_fail("resolved resources are missing")
        if set(context.materialized_defaults or {}) != {"resource_refs"}:
            self._pipeline_fail("default artifacts are inconsistent")
        if dict(context.normalized_units or {}) != {"velocity": "m/s", "position": "m"}:
            self._pipeline_fail("unit artifacts are inconsistent")
        for entity in context.expanded_entities:
            if str(entity.dynamics_ref or "").startswith("platforms."):
                self._pipeline_fail("dynamics resource type is incompatible")
        drafts: dict[str, Any] = {}
        for index, entity in enumerate(context.expanded_entities):
            if isinstance(entity, EntityDraftV2):
                drafts[entity.id] = ResolvedCompositionDraftV2(
                    source=entity,
                    resolved=self._expand_resource_entity(entity.entity, index),
                )
            else:
                drafts[entity.id] = entity
        spawn_entities: dict[str, ResolvedEntityV2] = {}
        for event_index, event in enumerate(context.event_declarations or ()):
            if not isinstance(event, Mapping) or event.get("event_type") != "spawn":
                continue
            payload = event.get("payload")
            entity_payload = payload.get("entity") if isinstance(payload, Mapping) else None
            try:
                spawned_spec = EntitySpecV2.model_validate(entity_payload)
            except ValidationError:
                continue
            spawn_entities[spawned_spec.id] = self._expand_resource_entity(
                spawned_spec, len(drafts) + event_index
            )
        bindings = {
            binding.exact_ref: binding
            for entity in (
                *(
                    draft.resolved
                    for draft in drafts.values()
                    if isinstance(draft, ResolvedCompositionDraftV2)
                ),
                *spawn_entities.values(),
            )
            for values in entity.resource_bindings.values()
            for binding in values
        }
        bindings.update(context.event_resource_bindings or {})
        units = {
            f"{binding.exact_ref}:{field}": unit
            for binding in bindings.values()
            for field, unit in binding.field_units.items()
        }
        if not units:
            units = {"position": "m", "velocity": "m/s"}
        return replace(
            context,
            resolved_resources=tuple(bindings[key] for key in sorted(bindings)),
            materialized_defaults=MappingProxyType(
                {key: binding.content_hash for key, binding in sorted(bindings.items())}
            ),
            normalized_units=MappingProxyType(dict(sorted(units.items()))),
            validated_compositions=MappingProxyType(drafts),
            event_resource_bindings=MappingProxyType(
                {
                    key: value
                    for key, value in bindings.items()
                    if value.resource_type in {"environments", "effects", "damage_models"}
                }
            ),
            event_spawn_entities=MappingProxyType(spawn_entities),
        )

    def _stage_coordinates(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "coordinates")
        if context.validated_compositions is None or context.parsed_schema is None:
            self._pipeline_fail("validated compositions are missing")
        for formation in context.parsed_schema.get("formations", ()):
            position = (
                formation.get("entity_template", {}).get("initial_state", {}).get("position_m")
            )
            if "position_m" in formation.get("entity_template", {}).get("initial_state", {}) and (
                not isinstance(position, (list, tuple))
                or len(position) != 3
                or any(
                    not isinstance(axis, (int, float))
                    or isinstance(axis, bool)
                    or not math.isfinite(float(axis))
                    for axis in position
                )
            ):
                raise CompilerErrorV2(
                    "scenario.coordinate_invalid",
                    file="entities.yaml",
                    path=("formations",),
                    value=position,
                    reason="position must contain three finite coordinates",
                    suggestion="provide a finite 3D position",
                )
        for entity in context.parsed_schema.get("entities", ()):
            position = entity.get("initial_state", {}).get("position_m")
            if "position_m" in entity.get("initial_state", {}) and (
                not isinstance(position, (list, tuple))
                or len(position) != 3
                or any(
                    not isinstance(axis, (int, float))
                    or isinstance(axis, bool)
                    or not math.isfinite(float(axis))
                    for axis in position
                )
            ):
                raise CompilerErrorV2(
                    "scenario.coordinate_invalid",
                    file="entities.yaml",
                    path=("entities", "initial_state", "position_m"),
                    value=position,
                    reason="position must contain three finite coordinates",
                    suggestion="provide a finite 3D position",
                )
        raw = _json_value(context.parsed_schema)
        if not isinstance(raw, dict):
            self._pipeline_fail("parsed schema JSON normalization is not an object")
        expanded_raw = [
            _json_value(entity.raw_entity)
            if isinstance(entity, EntityDraftV2)
            else entity.model_dump(mode="json")
            for entity in context.expanded_entities
        ]
        raw["entities"] = expanded_raw
        raw["formations"] = []
        resolved_world, deployments = self._normalize_coordinate_world(raw, expanded_raw)
        if resolved_world is None:
            try:
                world_spec = WorldSpecV2.model_validate(raw.get("world"))
            except ValidationError as error:
                first = error.errors()[0]
                raise self._error(
                    "scenario.schema_invalid",
                    ("world", *(str(item) for item in first.get("loc", ()))),
                    first.get("input"),
                    str(first.get("msg", "invalid world declaration")),
                    "correct the world according to schema version 2.0",
                    file="world.yaml",
                ) from error
            resolved_world = _ResolvedWorldV2.from_spec(world_spec)
        resolved_world = self._materialize_map_terrain(
            resolved_world,
            cast(ResolvedResourceBindingV2 | None, context.world_map_binding),
        )
        finalized: list[Any] = []
        coordinates_data: dict[str, tuple[float, float, float]] = {}
        for entity_raw in expanded_raw:
            try:
                spec = EntitySpecV2.model_validate(entity_raw)
            except ValidationError as error:
                first = error.errors()[0]
                raise self._error(
                    "scenario.schema_invalid",
                    tuple(str(item) for item in first.get("loc", ())),
                    first.get("input"),
                    str(first.get("msg", "invalid normalized entity")),
                    "correct the entity according to schema version 2.0",
                    file="entities.yaml",
                ) from error
            composition = context.validated_compositions.get(spec.id)
            if isinstance(composition, ResolvedCompositionDraftV2):
                runtime = replace(
                    composition.resolved.runtime_initial,
                    initial_state=spec.initial_state,
                )
                finalized.append(replace(composition.resolved, runtime_initial=runtime))
            else:
                finalized.append(spec)
            coordinates_data[spec.id] = cast(
                tuple[float, float, float],
                tuple(float(axis) for axis in spec.initial_state.position_m),
            )
        coordinates = MappingProxyType(coordinates_data)
        return replace(
            context,
            expanded_entities=tuple(finalized),
            normalized_world=resolved_world,
            normalized_coordinates=coordinates,
            coordinate_deployments=_freeze(deployments),
            event_declarations=_freeze(raw.get("events", context.event_declarations)),
        )

    def _stage_boundary_deployment(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "boundary_deployment")
        if (
            not isinstance(context.normalized_world, _ResolvedWorldV2)
            or context.normalized_coordinates is None
            or context.coordinate_deployments is None
        ):
            self._pipeline_fail("normalized coordinates are missing")
        if not all(isinstance(entity, ResolvedEntityV2) for entity in context.expanded_entities):
            self._pipeline_fail("coordinate-finalized entities are missing")
        world = context.normalized_world
        entities = tuple(cast(ResolvedEntityV2, entity) for entity in context.expanded_entities)
        terrain_zone_ids = self._terrain_zone_ids(world)
        effective_deployments = {
            entity.id: self._terrain_deployment(
                cast(Mapping[str, Any] | None, context.coordinate_deployments.get(entity.id)),
                domain=entity.domain,
                terrain_zone_ids=terrain_zone_ids,
            )
            for entity in entities
        }
        boundary_policy = world.boundary_policy
        if boundary_policy not in {
            None,
            "constrain_motion",
            "terminate",
            "clamp",
            "reflect",
            "wrap",
            "reject_command",
            "stop",
            "collision_effect",
            "deactivate",
            "mission_event",
        }:
            self._pipeline_fail("boundary policy is invalid")
        faction_ids = {faction.id for faction in context.factions}
        entity_ids: set[str] = set()
        controller_slots: set[str] = set()
        formation_ids = tuple(context.formation_ids or ())
        duplicate_formations = len(formation_ids) != len(set(formation_ids))
        zones = {zone.id: zone for zone in world.zones if isinstance(zone, _ResolvedZoneV2)}
        tolerance = world.coordinate_frame.tolerance_m if world.coordinate_frame else 0.0

        def location(zone: _ResolvedZoneV2, point: tuple[float, float]) -> str:
            if zone.geometry.type == "polygon":
                return self._point_in_polygon(
                    point,
                    cast(tuple[tuple[float, float], ...], zone.geometry.positions_m),
                    tolerance,
                )
            if zone.geometry.center_m is None or zone.geometry.radius_m is None:
                raise _ResolvedIntegrityError("circle zone geometry is incomplete")
            distance = math.hypot(
                point[0] - zone.geometry.center_m[0],
                point[1] - zone.geometry.center_m[1],
            )
            if abs(distance - zone.geometry.radius_m) <= tolerance:
                return "edge"
            return "inside" if distance < zone.geometry.radius_m else "outside"

        for index, entity in enumerate(entities):
            if entity.id in entity_ids:
                if duplicate_formations:
                    continue
                raise self._error(
                    "scenario.entity_duplicate",
                    ("entities", str(index), "id"),
                    entity.id,
                    "entity IDs must be globally unique after formation expansion",
                    "change the entity ID or formation pattern",
                    file="entities.yaml",
                )
            entity_ids.add(entity.id)
            if entity.faction_id not in faction_ids:
                raise self._error(
                    "scenario.entity_faction_missing",
                    ("entities", str(index), "faction_id"),
                    entity.faction_id,
                    "entity references an unknown faction",
                    "use a declared faction ID",
                    file="entities.yaml",
                )
            if entity.controller_slot is not None:
                if entity.controller_slot in controller_slots:
                    if duplicate_formations:
                        continue
                    raise self._error(
                        "scenario.controller_slot_duplicate",
                        ("entities", str(index), "controller_slot"),
                        entity.controller_slot,
                        "controller slot is already assigned",
                        "assign a globally unique controller slot",
                        file="entities.yaml",
                    )
                controller_slots.add(entity.controller_slot)
            deployment = effective_deployments.get(entity.id)
            if deployment is None:
                continue
            allowed_ids = tuple(str(item) for item in deployment.get("allowed_zone_ids", ()))
            excluded_ids = tuple(str(item) for item in deployment.get("excluded_zone_ids", ()))
            edge_policy = deployment.get("point_on_edge", "inside")
            if edge_policy not in {"inside", "outside"}:
                raise self._error(
                    "scenario.edge_policy_invalid",
                    ("entities", str(index), "deployment", "point_on_edge"),
                    edge_policy,
                    "deployment point_on_edge policy is invalid",
                    "use inside or outside",
                    file="entities.yaml",
                )
            unknown = sorted((set(allowed_ids) | set(excluded_ids)) - set(zones))
            if unknown:
                raise self._error(
                    "scenario.deployment_zone_missing",
                    ("entities", str(index), "deployment"),
                    unknown,
                    "deployment references unknown zones",
                    "use declared zone IDs",
                    file="entities.yaml",
                )
            incompatible = [
                zone_id
                for zone_id in allowed_ids
                if zones[zone_id].domains and entity.domain not in zones[zone_id].domains
            ]
            if incompatible:
                raise self._error(
                    "scenario.deployment_domain_incompatible",
                    ("entities", str(index), "deployment", "allowed_zone_ids"),
                    incompatible,
                    "allowed deployment zone does not support platform domain",
                    "select zones whose domains include the platform Catalog domain",
                    file="entities.yaml",
                )
            point = (entity.initial_state.position_m[0], entity.initial_state.position_m[1])
            if any(
                zones[allowed].geometry == zones[excluded].geometry
                for allowed in allowed_ids
                for excluded in excluded_ids
            ):
                raise self._error(
                    "scenario.deployment_feasible_region_empty",
                    ("entities", str(index), "deployment"),
                    deployment,
                    "an excluded zone exactly covers an allowed zone",
                    "change allowed/excluded deployment geometry",
                    file="entities.yaml",
                )
            if allowed_ids and not any(
                (place := location(zones[zone_id], point)) == "inside"
                or (place == "edge" and edge_policy == "inside")
                for zone_id in allowed_ids
            ):
                raise self._error(
                    "scenario.deployment_outside_allowed",
                    ("entities", str(index), "deployment"),
                    deployment,
                    "entity is outside every allowed deployment zone",
                    "move the entity into an allowed zone or change edge policy",
                    file="entities.yaml",
                )
            if any(
                (place := location(zones[zone_id], point)) == "inside"
                or (place == "edge" and edge_policy == "inside")
                for zone_id in excluded_ids
            ):
                raise self._error(
                    "scenario.deployment_excluded",
                    ("entities", str(index), "deployment"),
                    deployment,
                    "entity lies in an excluded deployment zone",
                    "move the entity outside excluded zones",
                    file="entities.yaml",
                )
        resolved_entities = tuple(
            replace(
                entity,
                boundary_deployment=(
                    None
                    if (deployment := effective_deployments.get(entity.id)) is None
                    else ResolvedBoundaryDeploymentV2(
                        allowed_zone_ids=tuple(
                            sorted(str(item) for item in deployment.get("allowed_zone_ids", ()))
                        ),
                        excluded_zone_ids=tuple(
                            sorted(str(item) for item in deployment.get("excluded_zone_ids", ()))
                        ),
                        point_on_edge=str(deployment.get("point_on_edge", "inside")),
                    )
                ),
            )
            for entity in entities
        )
        spawn_entities: dict[str, ResolvedEntityV2] = {}
        for spawn in cast(Mapping[str, ResolvedEntityV2], context.event_spawn_entities).values():
            deployment = self._terrain_deployment(
                None,
                domain=spawn.domain,
                terrain_zone_ids=terrain_zone_ids,
            )
            if deployment is not None:
                point = (spawn.initial_state.position_m[0], spawn.initial_state.position_m[1])
                allowed_ids = tuple(str(item) for item in deployment.get("allowed_zone_ids", ()))
                excluded_ids = tuple(str(item) for item in deployment.get("excluded_zone_ids", ()))
                if allowed_ids and not any(
                    location(zones[zone_id], point) == "inside" for zone_id in allowed_ids
                ):
                    raise self._error(
                        "scenario.deployment_outside_allowed",
                        ("events", "spawn", spawn.id, "deployment"),
                        deployment,
                        "spawned entity is outside map-authoritative land terrain",
                        "place the land platform on land",
                        file="events.yaml",
                    )
                if any(location(zones[zone_id], point) == "inside" for zone_id in excluded_ids):
                    raise self._error(
                        "scenario.deployment_excluded",
                        ("events", "spawn", spawn.id, "deployment"),
                        deployment,
                        "spawned surface or underwater entity is on land terrain",
                        "place the entity on water",
                        file="events.yaml",
                    )
                spawn = replace(
                    spawn,
                    boundary_deployment=ResolvedBoundaryDeploymentV2(
                        allowed_zone_ids=allowed_ids,
                        excluded_zone_ids=excluded_ids,
                        point_on_edge=str(deployment.get("point_on_edge", "inside")),
                    ),
                )
            spawn_entities[spawn.id] = spawn
        deployment_excluded = tuple(
            sorted(
                {
                    *world.deployment_excluded_zone_ids,
                    *(
                        zone_id
                        for deployment in effective_deployments.values()
                        if deployment is not None
                        for zone_id in deployment.get("excluded_zone_ids", ())
                    ),
                }
            )
        )
        return replace(
            context,
            normalized_world=replace(world, deployment_excluded_zone_ids=deployment_excluded),
            coordinate_deployments=_freeze(effective_deployments),
            validated_world=replace(world, deployment_excluded_zone_ids=deployment_excluded),
            validated_entities=resolved_entities,
            validated_deployments=resolved_entities,
            event_spawn_entities=MappingProxyType(spawn_entities),
        )

    def _stage_event_dependencies(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "event_dependencies")
        if (
            context.validated_deployments is None
            or context.validated_entities is None
            or not isinstance(context.validated_world, _ResolvedWorldV2)
            or context.event_declarations is None
            or context.event_resource_bindings is None
            or context.event_spawn_entities is None
        ):
            self._pipeline_fail("validated deployments are missing")
        declarations = tuple(context.event_declarations)
        ids = [item.get("id") for item in declarations if isinstance(item, Mapping)]
        if len(ids) != len(declarations) or len(ids) != len(set(ids)):
            code = (
                "scenario.event_duplicate"
                if len(ids) == len(declarations)
                else "scenario.event_payload_invalid"
            )
            raise self._error(
                code,
                ("events",),
                ids,
                "event declarations must be typed objects with unique IDs",
                "provide unique typed events",
                file="events.yaml",
            )
        specs: list[EventSpecV2] = []
        for index, declaration in enumerate(declarations):
            if not isinstance(declaration, Mapping):
                self._pipeline_fail("event declaration is not a mapping")
            if declaration.get("event_type") not in {
                "spawn",
                "despawn",
                "weather_change",
                "zone_activation",
                "jamming_start",
                "jamming_end",
                "component_suppression",
                "message",
                "mission_marker",
                "apply_effect",
                "spatial_effect_trigger",
            }:
                raise self._error(
                    "scenario.event_type_invalid",
                    ("events", str(index)),
                    declaration.get("event_type"),
                    "event type is not whitelisted",
                    "use a supported event type",
                    file="events.yaml",
                )
            if set(declaration) - {
                "schema_version",
                "id",
                "event_type",
                "trigger",
                "priority",
                "depends_on",
                "payload",
            }:
                raise self._error(
                    "scenario.event_payload_invalid",
                    ("events", str(index)),
                    declaration,
                    "event contains unknown fields",
                    "remove extra event fields",
                    file="events.yaml",
                )
            try:
                specs.append(EventSpecV2.model_validate(declaration))
            except ValidationError as error:
                raise self._error(
                    "scenario.event_payload_invalid",
                    ("events", str(index)),
                    declaration,
                    str(error.errors()[0].get("msg", "invalid event declaration")),
                    "provide a typed event declaration",
                    file="events.yaml",
                ) from error
        entities = tuple(cast(ResolvedEntityV2, entity) for entity in context.validated_entities)
        events = self._resolve_events(
            tuple(specs),
            entities,
            context.validated_world,
            resource_bindings=context.event_resource_bindings,
            spawn_entities=context.event_spawn_entities,
        )
        return replace(context, validated_events=events)

    def _stage_mission_scoring_controllers(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "mission_scoring_controllers")
        if (
            context.validated_events is None
            or context.mission_declarations is None
            or context.validated_entities is None
            or not isinstance(context.validated_world, _ResolvedWorldV2)
        ):
            self._pipeline_fail("validated events are missing")
        entities = tuple(cast(ResolvedEntityV2, entity) for entity in context.validated_entities)
        declarations = _json_value(context.mission_declarations)
        if not isinstance(declarations, dict):
            self._pipeline_fail("mission declarations are invalid")
        rules: tuple[MissionRuleV2 | _FrozenRecordV2, ...]
        if context.extended_mission_control:
            rules, scoring, controllers, controller_policy = (
                self._resolve_mission_scoring_controllers(
                    declarations,
                    entities,
                    {faction.id for faction in context.factions},
                    {zone.id for zone in context.validated_world.zones},
                    tuple(context.validated_events),
                )
            )
            mission_states = tuple(declarations.get("mission_states", ()))
            score_metrics: tuple[ScoreMetricV2, ...] = ()
        else:
            try:
                rules = tuple(
                    sorted(
                        (
                            MissionRuleV2.model_validate(item)
                            for item in declarations.get("mission_rules", ())
                        ),
                        key=lambda item: (-item.priority, item.id),
                    )
                )
                score_metrics = tuple(
                    sorted(
                        (
                            ScoreMetricV2.model_validate(item)
                            for item in declarations.get("score_metrics", ())
                        ),
                        key=lambda item: item.id,
                    )
                )
            except ValidationError as error:
                first = error.errors()[0]
                raise self._error(
                    "scenario.mission_operator_invalid",
                    ("mission_rules",),
                    first.get("input"),
                    str(first.get("msg", "mission declaration is invalid")),
                    "use a supported typed mission or scoring declaration",
                    file="mission_rules.yaml",
                ) from error
            scoring = None
            controllers = ()
            controller_policy = None
            mission_states = ()
        return replace(
            context,
            validated_mission=rules,
            validated_controllers=controllers,
            mission_states=mission_states,
            score_metrics=score_metrics,
            scoring=scoring,
            controller_policy=controller_policy,
        )

    def _stage_visibility(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "visibility")
        if (
            context.validated_mission is None
            or context.validated_controllers is None
            or context.visibility_declarations is None
            or context.factions is None
        ):
            self._pipeline_fail("validated mission is missing")
        if any(
            not isinstance(item, (Mapping, _FrozenRecordV2))
            for item in context.validated_controllers
        ):
            self._pipeline_fail("controller artifacts are invalid")
        visibility = self._resolve_visibility(
            context.visibility_declarations,
            {faction.id for faction in context.factions},
            tuple(context.validated_controllers),
        )
        return replace(context, validated_visibility=visibility)

    def _stage_stable_order(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "stable_order")
        if context.validated_visibility is None:
            self._pipeline_fail("validated visibility is missing")
        formation_ids = list(context.formation_ids or ())
        if len(formation_ids) != len(set(formation_ids)):
            self._pipeline_fail("formation IDs duplicate")
        expected_entities = bool(context.expanded_entities)
        if expected_entities and not context.resolved_resources:
            self._pipeline_fail("resource or entity artifacts are missing")
        if context.materialized_defaults is None:
            self._pipeline_fail("default artifacts are inconsistent")
        if not context.normalized_units:
            self._pipeline_fail("unit artifacts are inconsistent")
        if not context.factions:
            self._pipeline_fail("faction artifacts are missing")
        entity_ids = {entity.id for entity in context.expanded_entities}
        if set(context.validated_compositions or {}) != entity_ids:
            self._pipeline_fail("composition artifacts are inconsistent")
        if set(context.normalized_coordinates or {}) != entity_ids:
            self._pipeline_fail("coordinate artifacts are inconsistent")
        if expected_entities and not context.validated_deployments:
            self._pipeline_fail("deployment artifacts are missing")
        if context.validated_entities is None or context.validated_world is None:
            self._pipeline_fail("validated boundary artifacts are missing")
        if any(
            not isinstance(item, (Mapping, _FrozenRecordV2))
            for item in context.validated_controllers
        ):
            self._pipeline_fail("controller artifacts are invalid")
        if any(
            not isinstance(item, (Mapping, _FrozenRecordV2))
            for item in context.validated_visibility
        ):
            self._pipeline_fail("visibility artifacts are invalid")
        ordered = self._assemble_ordered_ir(context)
        return replace(
            context,
            ordered_ir=ordered,
            artifact_hash=self._ordered_artifact_hash(context),
        )

    def _assemble_ordered_ir(self, context: PipelineContextV2) -> ResolvedScenarioV2:
        resources = context.resolved_resources
        defaults = context.materialized_defaults
        units = context.normalized_units
        expanded_entities = context.expanded_entities
        factions = tuple(sorted(context.factions, key=lambda item: item.id))
        relationships = tuple(
            sorted(
                context.relationships,
                key=lambda item: (item.source_faction_id, item.target_faction_id),
            )
        )
        compositions = context.validated_compositions
        normalized_world = context.normalized_world
        world = context.validated_world
        validated_entities = context.validated_entities
        deployments = context.validated_deployments
        events = tuple(context.validated_events)
        mission = tuple(context.validated_mission)
        controllers = tuple(context.validated_controllers)
        visibility = tuple(context.validated_visibility)
        if not isinstance(world, _ResolvedWorldV2) or not all(
            isinstance(item, ResolvedResourceBindingV2) for item in resources
        ):
            self._pipeline_fail("resolved spatial resources are invalid")
        spatial_effect_policy = _resolve_declared_spatial_effect_policy(
            world,
            tuple(cast(ResolvedResourceBindingV2, item) for item in resources),
        )
        world_resource_bindings = resolve_world_resource_closure_v2(
            spatial_effect_policy,
            tuple(cast(ResolvedResourceBindingV2, item) for item in resources),
        )
        map_binding = context.world_map_binding
        if world.map_ref is not None:
            if (
                not isinstance(map_binding, ResolvedResourceBindingV2)
                or map_binding.resource_type != "maps"
                or map_binding.exact_ref != world.map_ref
            ):
                self._pipeline_fail("resolved world map binding is invalid")
            world_resource_bindings = tuple(
                sorted(
                    {
                        **{item.exact_ref: item for item in world_resource_bindings},
                        map_binding.exact_ref: map_binding,
                    }.values(),
                    key=lambda item: item.exact_ref,
                )
            )
        elif map_binding is not None:
            self._pipeline_fail("world map binding exists without a map reference")
        del (
            resources,
            defaults,
            units,
            expanded_entities,
            compositions,
            normalized_world,
            validated_entities,
            deployments,
        )
        entities: list[EntitySpecV2 | ResolvedEntityV2] = []
        for entity in sorted(context.validated_deployments, key=lambda item: item.id):
            position = context.normalized_coordinates.get(entity.id)
            if (
                isinstance(entity, ResolvedEntityV2)
                and position is not None
                and tuple(position) != (0.0, 0.0, 0.0)
            ):
                initial = entity.runtime_initial.initial_state.model_copy(
                    update={"position_m": tuple(position)}
                )
                runtime = replace(entity.runtime_initial, initial_state=initial)
                entity = replace(entity, runtime_initial=runtime)
            entities.append(entity)
        visibility_record = _record({"matrix": visibility}) if visibility else None
        return ResolvedScenarioV2(
            schema_version="2.0",
            scenario_id=context.scenario_id,
            catalog_hash=context.catalog_hash,
            model_registry_hash=context.model_registry_hash,
            model_registry_snapshot=tuple(context.model_registry_snapshot),
            compiler_version=COMPILER_VERSION,
            compile_stage_trace=(),
            provenance=_record({}),
            factions=factions,
            relationships=relationships,
            entities=tuple(entities),
            world=world,
            events=events,
            mission_states=tuple(context.mission_states),
            mission_rules=mission,
            score_metrics=tuple(context.score_metrics),
            scoring=context.scoring,
            controller_slots=controllers,
            controller_policy=context.controller_policy,
            visibility=visibility_record,
            world_resource_bindings=world_resource_bindings,
            spatial_effect_policy=spatial_effect_policy,
            resolved_hash="",
        )

    @staticmethod
    def _ordered_artifact_hash(context: PipelineContextV2) -> str:
        return _digest(
            {
                "resources": sorted(
                    context.resolved_resources,
                    key=lambda item: getattr(item, "exact_ref", str(item)),
                ),
                "world_map_binding": context.world_map_binding,
                "defaults": context.materialized_defaults,
                "units": context.normalized_units,
                "factions": sorted(
                    context.factions, key=lambda item: getattr(item, "id", str(item))
                ),
                "relationships": sorted(
                    context.relationships,
                    key=lambda item: _canonical_json(_json_value(item)),
                ),
                "entities": sorted(
                    context.expanded_entities,
                    key=lambda item: getattr(item, "id", str(item)),
                ),
                "compositions": context.validated_compositions,
                "world": context.normalized_world,
                "validated_world": context.validated_world,
                "validated_entities": sorted(
                    context.validated_entities,
                    key=lambda item: getattr(item, "id", str(item)),
                ),
                "coordinates": context.normalized_coordinates,
                "deployments": sorted(
                    context.validated_deployments,
                    key=lambda item: getattr(item, "id", str(item)),
                ),
                "events": sorted(
                    context.validated_events,
                    key=lambda item: getattr(item, "id", str(item)),
                ),
                "mission": sorted(
                    context.validated_mission,
                    key=lambda item: getattr(item, "id", str(item)),
                ),
                "controllers": sorted(
                    context.validated_controllers,
                    key=lambda item: _canonical_json(_json_value(item)),
                ),
                "visibility": sorted(
                    context.validated_visibility,
                    key=lambda item: _canonical_json(_json_value(item)),
                ),
            }
        )

    def _stage_freeze_hash(self, value: Any) -> PipelineContextV2:
        context = self._advance(value, "freeze_hash")
        if not isinstance(context.ordered_ir, ResolvedScenarioV2):
            self._pipeline_fail("ordered IR is missing")
        trace = tuple(
            StageRecordV2(stage=stage, ordinal=index)
            for index, stage in enumerate(COMPILER_STAGES_V2)
        )
        audit = context.audit_hashes
        if not isinstance(audit, Mapping):
            self._pipeline_fail("package audit hashes are missing")
        provenance = _record(
            {
                "compiler_version": COMPILER_VERSION,
                "catalog_hash": context.catalog_hash,
                "model_registry_hash": context.model_registry_hash,
                "package_logical_hash": audit["logical"],
                "package_content_hash": audit["content"],
                "package_archive_hash": audit["archive"],
                "package_identity_hash": _digest(
                    [audit["logical"], audit["content"], audit["archive"]]
                ),
                "artifact_hash": context.artifact_hash,
            }
        )
        finalized = replace(
            context.ordered_ir,
            compile_stage_trace=trace,
            provenance=provenance,
        )
        finalized = replace(
            finalized,
            resolved_hash=ResolvedScenarioV2.compute_resolved_hash(
                finalized._payload(include_hash=False)
            ),
        )
        finalized._validate_mission_control_integrity()
        finalized._validate_integrity()
        return replace(context, resolved=finalized)

    @staticmethod
    def _error(
        code: str,
        path: tuple[str, ...],
        value: Any,
        reason: str,
        suggestion: str,
        *,
        file: str | None = None,
    ) -> CompilerErrorV2:
        return CompilerErrorV2(
            code,
            file=file or (f"{path[0]}.yaml" if path else "scenario.yaml"),
            path=path,
            value=value,
            reason=reason,
            suggestion=suggestion,
        )

    @staticmethod
    def _validate_position(entity: Mapping[str, Any], index: int, section: str) -> None:
        state = entity.get("initial_state")
        if isinstance(state, Mapping) and "position" in state:
            return
        value = state.get("position_m") if isinstance(state, Mapping) else None
        valid = (
            isinstance(value, Sequence)
            and not isinstance(value, (str, bytes, bytearray))
            and len(value) == 3
            and all(
                isinstance(item, (int, float))
                and not isinstance(item, bool)
                and math.isfinite(float(item))
                for item in value
            )
        )
        if not valid:
            raise ScenarioCompilerV2._error(
                "scenario.coordinate_invalid",
                (section, str(index), "initial_state", "position_m"),
                value,
                "local position must contain three finite numeric metres",
                "provide [x_m, y_m, z_m] with finite numbers",
                file="entities.yaml",
            )

    def _resource_binding(self, resource: CatalogResourceV2) -> ResolvedResourceBindingV2:
        metadata = self._catalog.model_registry.metadata(resource.model_ref)
        return ResolvedResourceBindingV2(
            schema_version=resource.schema_version,
            exact_ref=resource.exact_ref,
            resource_type=resource.resource_type,
            id=resource.id,
            version=resource.version,
            engine_compatibility=resource.engine_compatibility,
            content_hash=resource.content_hash,
            model_ref=resource.model_ref,
            model_evidence=_ModelEvidenceV2(
                model_ref=metadata.exact_ref,
                artifact_sha256=metadata.artifact_sha256,
                interface_version=metadata.interface_version,
                input_schema=metadata.input_schema,
                output_schema=metadata.output_schema,
                trusted=metadata.trusted,
                deterministic=metadata.deterministic,
                resource_types=metadata.resource_types,
            ),
            dependencies=resource.dependencies,
            content=_freeze(_json_value(resource.content)),
            normalized_content=_freeze(_json_value(resource.content)),
            units=_freeze(metadata.units),
            field_units=_freeze(metadata.field_units),
            defaults=MappingProxyType({}),
        )

    def _resolve_events(
        self,
        specs: tuple[EventSpecV2, ...],
        entities: tuple[ResolvedEntityV2, ...],
        world: _ResolvedWorldV2,
        *,
        resource_bindings: Mapping[str, ResolvedResourceBindingV2],
        spawn_entities: Mapping[str, ResolvedEntityV2],
    ) -> tuple[ResolvedEventV2, ...]:

        allowed: dict[str, tuple[set[str], set[str]]] = {
            "spawn": ({"entity"}, set()),
            "despawn": ({"entity_id"}, set()),
            "weather_change": ({"environment_ref"}, set()),
            "zone_activation": ({"zone_id"}, set()),
            "jamming_start": ({"session_id", "source_entity_id", "target_entity_id"}, set()),
            "jamming_end": ({"session_id"}, set()),
            "component_suppression": (
                {"target_entity_id", "component_ref", "duration_ticks"},
                set(),
            ),
            "message": (
                {"body", "visibility"},
                {"sender_entity_id", "recipient_entity_ids", "recipient_controller_slots"},
            ),
            "mission_marker": ({"marker_id"}, {"zone_id", "position_m"}),
            "apply_effect": ({"effect_ref", "target_selector"}, set()),
            "spatial_effect_trigger": (
                {
                    "source_kind",
                    "source_entity_ids",
                    "effect_ref",
                    "target_selector",
                    "source_lifecycle",
                },
                {
                    "zone_id",
                    "secondary_effect_ref",
                    "secondary_probability",
                    "secondary_target_selector",
                },
            ),
        }
        ids = [item.id for item in specs]
        if len(ids) != len(set(ids)):
            raise self._error(
                "scenario.event_duplicate",
                ("events",),
                ids,
                "event IDs must be unique",
                "rename duplicate event IDs",
                file="events.yaml",
            )
        known_ids = set(ids)
        duration = world.duration_ticks
        zones = {zone.id for zone in world.zones}
        static = {entity.id for entity in entities}
        controllers = {entity.controller_slot for entity in entities if entity.controller_slot}
        components = {
            entity.id: set(entity.composition.sensor_refs + entity.composition.communication_refs)
            for entity in entities
        }
        spawn_ticks: dict[str, int] = {}
        despawn_ticks: dict[str, int] = {}
        event_ticks: dict[str, int] = {}
        for index, event in enumerate(specs):
            path = ("events", str(index))
            if event.event_type not in allowed:
                raise self._error(
                    "scenario.event_type_invalid",
                    path,
                    event.event_type,
                    "event type is not whitelisted",
                    "use a supported declarative event",
                    file="events.yaml",
                )
            if set(event.payload) - (
                allowed[event.event_type][0] | allowed[event.event_type][1]
            ) or not allowed[event.event_type][0].issubset(event.payload):
                code = (
                    "scenario.event_payload_forbidden"
                    if "health" in event.payload
                    else "scenario.event_payload_invalid"
                )
                raise self._error(
                    code,
                    (*path, "payload"),
                    event.payload,
                    "event payload fields do not match its strict type",
                    "use only required and optional typed fields",
                    file="events.yaml",
                )
            if duration is None:
                raise self._error(
                    "scenario.event_time_bounds_missing",
                    ("events",),
                    event.trigger,
                    "typed events require world duration_ticks",
                    "declare positive duration_ticks",
                    file="events.yaml",
                )
            if duration is not None:

                def bounded(value: Any, *, maximum: int = 4096) -> bool:
                    return isinstance(value, str) and 0 < len(value) <= maximum

                values = event.payload
                strings = [
                    values.get(field)
                    for field in (
                        "sender_entity_id",
                        "target_entity_id",
                        "source_entity_id",
                        "session_id",
                        "marker_id",
                    )
                    if field in values
                ]
                if (
                    any(not bounded(value) for value in strings)
                    or (event.event_type == "message" and not bounded(values.get("body")))
                    or (
                        event.event_type == "component_suppression"
                        and (
                            not isinstance(values.get("duration_ticks"), int)
                            or isinstance(values.get("duration_ticks"), bool)
                            or values["duration_ticks"] <= 0
                        )
                    )
                ):
                    raise self._error(
                        "scenario.event_value_invalid",
                        path,
                        values,
                        "event value violates its type or range",
                        "provide bounded nonempty strings and positive durations",
                        file="events.yaml",
                    )
                for recipient_field in ("recipient_entity_ids", "recipient_controller_slots"):
                    recipients = values.get(recipient_field, ())
                    if not isinstance(recipients, (list, tuple)) or any(
                        not bounded(item) for item in recipients
                    ):
                        raise self._error(
                            "scenario.event_value_invalid",
                            path,
                            recipients,
                            "recipients must be a typed string sequence",
                            "provide a list of entity or controller IDs",
                            file="events.yaml",
                        )
                    if len(recipients) != len(set(recipients)):
                        raise self._error(
                            "scenario.event_recipient_duplicate",
                            path,
                            recipients,
                            "message recipients must be unique",
                            "remove duplicate recipients",
                            file="events.yaml",
                        )
                if event.event_type == "apply_effect":
                    selector = values.get("target_selector")
                    if (
                        not isinstance(selector, Mapping)
                        or set(selector) != {"entity_ids"}
                        or not isinstance(selector.get("entity_ids"), (list, tuple))
                        or not selector["entity_ids"]
                        or any(not bounded(item) for item in selector["entity_ids"])
                    ):
                        raise self._error(
                            "scenario.event_selector_invalid",
                            path,
                            selector,
                            "effect selector must contain nonempty typed entity_ids",
                            "provide unique target entity IDs",
                            file="events.yaml",
                        )
                if event.event_type == "spatial_effect_trigger":
                    try:
                        _validate_event_payload(event.event_type, values)
                    except ValueError as error:
                        raise self._error(
                            "scenario.event_selector_invalid",
                            path,
                            values,
                            str(error),
                            "provide typed source, lifecycle, and target selector values",
                            file="events.yaml",
                        ) from error
                if event.event_type == "mission_marker" and "position_m" in values:
                    marker_position = values["position_m"]
                    if (
                        not isinstance(marker_position, (list, tuple))
                        or len(marker_position) != 3
                        or any(
                            not isinstance(axis, (int, float))
                            or isinstance(axis, bool)
                            or not math.isfinite(float(axis))
                            for axis in marker_position
                        )
                    ):
                        raise self._error(
                            "scenario.event_value_invalid",
                            path,
                            marker_position,
                            "mission marker position must be finite canonical 3D metres",
                            "provide a discriminated input position that resolves to three metres",
                            file="events.yaml",
                        )
            try:
                _validate_event_payload(event.event_type, event.payload)
            except ValueError as error:
                if event.event_type == "message" and event.payload.get("visibility") not in {
                    "public",
                    "recipients",
                }:
                    code = "scenario.event_visibility_invalid"
                elif event.event_type in {"apply_effect", "spatial_effect_trigger"}:
                    code = "scenario.event_selector_invalid"
                else:
                    code = "scenario.event_value_invalid"
                raise self._error(
                    code,
                    path,
                    event.payload,
                    str(error),
                    "correct all typed event payload fields",
                    file="events.yaml",
                ) from error
            trigger = event.trigger
            tick = (
                trigger.get("tick")
                if (set(trigger) == {"kind", "tick"} and trigger.get("kind") == "tick")
                else None
            )
            if (
                not isinstance(tick, int)
                or isinstance(tick, bool)
                or tick < 0
                or (duration is not None and tick > duration)
            ):
                raise self._error(
                    "scenario.event_tick_invalid",
                    path,
                    trigger,
                    "event requires an in-range integer tick trigger",
                    "use kind=tick within world duration",
                    file="events.yaml",
                )
            event_ticks[event.id] = tick
            if event.id in event.depends_on:
                raise self._error(
                    "scenario.event_dependency_self",
                    path,
                    event.id,
                    "event cannot depend on itself",
                    "remove the self dependency",
                    file="events.yaml",
                )
            missing = set(event.depends_on) - known_ids
            if missing:
                raise self._error(
                    "scenario.event_dependency_missing",
                    path,
                    tuple(sorted(missing)),
                    "event dependency does not exist",
                    "reference declared event IDs",
                    file="events.yaml",
                )
            if event.event_type == "spawn":
                entity_payload = event.payload["entity"]
                try:
                    spawned = EntitySpecV2.model_validate(entity_payload)
                except ValidationError as error:
                    raise self._error(
                        "scenario.event_payload_invalid",
                        (*path, "payload", "entity"),
                        entity_payload,
                        "spawn entity is invalid",
                        "provide a valid EntitySpecV2",
                        file="events.yaml",
                    ) from error
                if spawned.id in spawn_ticks:
                    prior_despawn = next(
                        (
                            prior
                            for prior in specs[:index]
                            if prior.event_type == "despawn"
                            and prior.payload.get("entity_id") == spawned.id
                            and event_ticks.get(prior.id, tick) < tick
                            and prior.id in event.depends_on
                        ),
                        None,
                    )
                    if prior_despawn is None:
                        raise self._error(
                            "scenario.event_lifecycle_duplicate",
                            path,
                            spawned.id,
                            "entity has duplicate active spawn transitions",
                            "depend on an intervening despawn or use a new entity ID",
                            file="events.yaml",
                        )
                if spawned.id in static:
                    raise self._error(
                        "scenario.event_lifecycle_conflict",
                        path,
                        spawned.id,
                        "spawn conflicts with an existing entity lifetime",
                        "use a unique entity ID",
                        file="events.yaml",
                    )
                spawn_ticks.setdefault(spawned.id, tick)
                controllers.add(spawned.controller_slot) if spawned.controller_slot else None
                components[spawned.id] = set(spawned.component_refs)
            elif event.event_type == "despawn":
                despawn_id = str(event.payload["entity_id"])
                if despawn_id in despawn_ticks:
                    raise self._error(
                        "scenario.event_lifecycle_duplicate",
                        path,
                        despawn_id,
                        "entity has duplicate despawn transitions",
                        "keep one despawn transition",
                        file="events.yaml",
                    )
                despawn_ticks[despawn_id] = tick
        cycle_graph = {event.id: set(event.depends_on) for event in specs}
        cycle_remaining = dict(cycle_graph)
        while cycle_remaining:
            ready = [identifier for identifier, deps in cycle_remaining.items() if not deps]
            if not ready:
                raise self._error(
                    "scenario.event_dependency_cycle",
                    ("events",),
                    tuple(sorted(cycle_remaining)),
                    "event dependency graph contains a cycle",
                    "remove cyclic dependencies",
                    file="events.yaml",
                )
            for identifier in ready:
                cycle_remaining.pop(identifier)
                for dependencies in cycle_remaining.values():
                    dependencies.discard(identifier)
        for event in specs:
            for dependency in event.depends_on:
                if event_ticks[dependency] > event_ticks[event.id]:
                    raise self._error(
                        "scenario.event_dependency_temporal_invalid",
                        ("events",),
                        dependency,
                        "event dependency occurs after its dependent",
                        "move dependencies no later than dependents",
                        file="events.yaml",
                    )
        all_entities = static | set(spawn_ticks)
        for identifier, tick in despawn_ticks.items():
            if identifier not in all_entities or tick <= spawn_ticks.get(identifier, -1):
                raise self._error(
                    "scenario.event_lifecycle_invalid",
                    ("events",),
                    identifier,
                    "despawn is outside a valid entity lifetime",
                    "despawn an active entity after spawn",
                    file="events.yaml",
                )
        starts: dict[str, tuple[int, str, str]] = {}
        ends: dict[str, int] = {}
        resolved: dict[str, ResolvedEventV2] = {}
        for index, event in enumerate(specs):
            path = ("events", str(index))
            tick = event_ticks[event.id]
            payload = dict(event.payload)
            if event.event_type == "spawn":
                spawned_spec = EntitySpecV2.model_validate(payload["entity"])
                resolved_spawn = spawn_entities.get(spawned_spec.id)
                if resolved_spawn is None:
                    self._pipeline_fail("spawn entity compatibility artifact is missing")
                payload["entity"] = resolved_spawn
            references: list[str] = []
            reference_fields = ["sender_entity_id", "target_entity_id", "source_entity_id"]
            if event.event_type != "despawn":
                reference_fields.append("entity_id")
            for field in reference_fields:
                if isinstance(payload.get(field), str):
                    references.append(payload[field])
            references.extend(payload.get("recipient_entity_ids", ()))
            selector = payload.get("target_selector")
            if isinstance(selector, Mapping):
                references.extend(selector.get("entity_ids", ()))
            for reference in references:
                if reference not in all_entities:
                    raise self._error(
                        "scenario.event_reference_missing",
                        path,
                        reference,
                        "event references an unknown entity",
                        "reference a static or spawned entity",
                        file="events.yaml",
                    )
                if tick < spawn_ticks.get(reference, 0) or tick >= despawn_ticks.get(
                    reference, duration + 1 if duration is not None else 2**63
                ):
                    raise self._error(
                        "scenario.event_reference_outside_lifecycle",
                        path,
                        reference,
                        "entity reference is outside its active lifetime",
                        "move the event inside the entity lifetime",
                        file="events.yaml",
                    )
            zone = payload.get("zone_id")
            if zone is not None and zone not in zones:
                raise self._error(
                    "scenario.event_reference_missing",
                    path,
                    zone,
                    "event references an unknown zone",
                    "reference a declared world zone",
                    file="events.yaml",
                )
            slots = payload.get("recipient_controller_slots", ())
            if any(slot not in controllers for slot in slots):
                raise self._error(
                    "scenario.event_reference_missing",
                    path,
                    tuple(slots),
                    "message references an unknown controller slot",
                    "reference an assigned controller slot",
                    file="events.yaml",
                )
            if event.event_type == "message" and payload["visibility"] not in {
                "public",
                "recipients",
            }:
                raise self._error(
                    "scenario.event_visibility_invalid",
                    path,
                    payload["visibility"],
                    "message visibility is invalid",
                    "use public or recipients",
                    file="events.yaml",
                )
            if event.event_type == "component_suppression":
                target, component = payload["target_entity_id"], payload["component_ref"]
                if component not in components.get(target, set()):
                    raise self._error(
                        "scenario.event_component_invalid",
                        path,
                        component,
                        "component is not owned by the target entity",
                        "reference a bound target component",
                        file="events.yaml",
                    )
            if event.event_type == "weather_change":
                environment = resource_bindings.get(str(payload["environment_ref"]))
                if environment is None or environment.resource_type != "environments":
                    raise self._error(
                        "scenario.event_reference_missing",
                        path,
                        payload["environment_ref"],
                        "environment resource binding is missing",
                        "reference an exact environment",
                        file="events.yaml",
                    )
                payload["environment_binding"] = environment
                payload.pop("environment_ref", None)
            if event.event_type == "jamming_start":
                if payload["session_id"] in starts:
                    raise self._error(
                        "scenario.event_jamming_pair_invalid",
                        path,
                        payload["session_id"],
                        "jamming session has duplicate starts",
                        "keep one start per session",
                        file="events.yaml",
                    )
                starts[payload["session_id"]] = (
                    tick,
                    payload["source_entity_id"],
                    payload["target_entity_id"],
                )
            elif event.event_type == "jamming_end":
                if payload["session_id"] in ends:
                    raise self._error(
                        "scenario.event_jamming_pair_invalid",
                        path,
                        payload["session_id"],
                        "jamming session has duplicate ends",
                        "keep one end per session",
                        file="events.yaml",
                    )
                ends[payload["session_id"]] = tick
            if event.event_type in {"apply_effect", "spatial_effect_trigger"}:
                effect = resource_bindings.get(str(payload["effect_ref"]))
                damage_ref = (
                    effect.normalized_content.get("damage_model_ref")
                    if effect is not None
                    else None
                )
                damage = resource_bindings.get(str(damage_ref))
                if (
                    effect is None
                    or effect.resource_type != "effects"
                    or not isinstance(damage_ref, str)
                    or damage is None
                    or damage.resource_type != "damage_models"
                ):
                    raise self._error(
                        "scenario.event_effect_invalid",
                        path,
                        payload["effect_ref"],
                        "effect resource binding has no trusted damage chain",
                        "reference a trusted exact effect with damage chain",
                        file="events.yaml",
                    )
                payload["effect_binding"] = effect
                payload["damage_binding"] = damage
                payload.pop("effect_ref", None)
                if event.event_type == "spatial_effect_trigger":
                    source_ids = tuple(payload["source_entity_ids"])
                    selectors: tuple[Any, ...] = (payload["target_selector"],)
                    secondary_ref = payload.get("secondary_effect_ref")
                    if secondary_ref is not None:
                        secondary_effect = resource_bindings.get(str(secondary_ref))
                        secondary_damage_ref = (
                            secondary_effect.normalized_content.get("damage_model_ref")
                            if secondary_effect is not None
                            else None
                        )
                        secondary_damage = resource_bindings.get(str(secondary_damage_ref))
                        if (
                            secondary_effect is None
                            or secondary_effect.resource_type != "effects"
                            or not isinstance(secondary_damage_ref, str)
                            or secondary_damage is None
                            or secondary_damage.resource_type != "damage_models"
                        ):
                            raise self._error(
                                "scenario.event_effect_invalid",
                                path,
                                secondary_ref,
                                "secondary effect resource has no trusted damage chain",
                                "reference a trusted exact secondary effect with damage chain",
                                file="events.yaml",
                            )
                        payload["secondary_effect_binding"] = secondary_effect
                        payload["secondary_damage_binding"] = secondary_damage
                        payload.pop("secondary_effect_ref", None)
                        selectors = (*selectors, payload["secondary_target_selector"])
                    endpoint_ids = set(static) | set(spawn_entities)
                    if any(item not in endpoint_ids for item in source_ids) or any(
                        item not in endpoint_ids
                        for selector in selectors
                        for field in ("entity_ids", "exclude_entity_ids")
                        for item in selector.get(field, ())
                    ):
                        raise self._error(
                            "scenario.event_reference_missing",
                            path,
                            tuple(sorted(endpoint_ids)),
                            "spatial trigger references an unknown entity endpoint",
                            "reference a static or declared spawn entity",
                            file="events.yaml",
                        )
                    if payload["source_kind"] == "zone_entry" and payload["zone_id"] not in zones:
                        raise self._error(
                            "scenario.event_reference_missing",
                            path,
                            payload["zone_id"],
                            "spatial trigger zone is unknown",
                            "reference a declared world zone",
                            file="events.yaml",
                        )
            resolved_trigger = {"kind": "tick", "tick": tick}
            resolved[event.id] = ResolvedEventV2(
                "2.0",
                event.id,
                event.event_type,
                _record(resolved_trigger),
                event.priority,
                event.depends_on,
                _record(payload),
            )
        if set(starts) != set(ends):
            raise self._error(
                "scenario.event_jamming_pair_invalid",
                ("events",),
                tuple(sorted(set(starts) ^ set(ends))),
                "jamming sessions require one start and end",
                "pair every jamming session",
                file="events.yaml",
            )
        if any(ends[key] <= starts[key][0] for key in starts):
            raise self._error(
                "scenario.event_jamming_order_invalid",
                ("events",),
                starts,
                "jamming end must follow start",
                "move end after its paired start",
                file="events.yaml",
            )
        incoming = {item.id: set(item.depends_on) for item in specs}
        ordered: list[ResolvedEventV2] = []
        while incoming:
            ready = [identifier for identifier, deps in incoming.items() if not deps]
            if not ready:
                raise self._error(
                    "scenario.event_dependency_cycle",
                    ("events",),
                    tuple(sorted(incoming)),
                    "event dependency graph contains a cycle",
                    "remove cyclic dependencies",
                    file="events.yaml",
                )
            identifier = min(
                ready, key=lambda item: (event_ticks[item], -resolved[item].priority, item)
            )
            ordered.append(resolved[identifier])
            incoming.pop(identifier)
            for deps in incoming.values():
                deps.discard(identifier)
        return tuple(ordered)

    def _resolve_mission_scoring_controllers(
        self,
        raw: Mapping[str, Any],
        entities: tuple[ResolvedEntityV2, ...],
        faction_ids: set[str],
        zone_ids: set[str],
        events: tuple[ResolvedEventV2, ...],
    ) -> tuple[
        tuple[_FrozenRecordV2, ...],
        _FrozenRecordV2 | None,
        tuple[_FrozenRecordV2, ...],
        str | None,
    ]:
        selector_entities = list(entities)
        selector_entities.extend(
            event.payload.entity
            for event in events
            if event.event_type == "spawn"
            and isinstance(getattr(event.payload, "entity", None), ResolvedEntityV2)
        )
        by_id = {entity.id: entity for entity in selector_entities}
        event_types = {event.id: event.event_type for event in events}
        event_ids = set(event_types)

        def fail(code: str, section: str, value: Any, reason: str) -> None:
            raise self._error(
                code,
                (section,),
                value,
                reason,
                "correct the declarative references and policy",
                file=f"{section}.yaml",
            )

        def selector(value: Any, section: str, *, allow_empty: bool = False) -> _FrozenRecordV2:
            reference_code = "mission" if section == "mission_rules" else section
            if not isinstance(value, Mapping):
                fail(
                    f"scenario.{reference_code}_reference_missing",
                    section,
                    value,
                    "selector must be an object",
                )
            explicit_ids = "entity_ids" in value
            candidates = tuple(sorted(value.get("entity_ids", by_id)))
            if any(identifier not in by_id for identifier in candidates):
                fail(
                    f"scenario.{reference_code}_reference_missing",
                    section,
                    candidates,
                    "selector entity endpoint is missing",
                )
            factions = tuple(sorted(value.get("factions", ())))
            platforms = tuple(sorted(value.get("platforms", ())))
            domains = tuple(sorted(value.get("domains", ())))
            capabilities = tuple(sorted(value.get("capabilities", ())))
            tags = tuple(sorted(value.get("tags", ())))
            zones = tuple(sorted(value.get("zones", ())))
            events = tuple(sorted(value.get("events", ())))
            # Optional lifecycle filter.  The runtime selector already supports it
            # (``engine_v2`` selector evidence, default includes ``disabled``), and
            # the ``count``/``survival`` operators only ever exclude ``destroyed``.
            # Without a declarative way to narrow it, a rule such as "the intruder
            # has no combat power left" can never fire while any unit merely sits
            # at ``disabled`` -- the engagement is already decided but the episode
            # keeps running to the time limit.  Declaring
            # ``include_lifecycle: [scheduled, active, degraded]`` expresses
            # "units that can still fight", which is exactly the engine's own
            # firing gate (``attacker_lifecycle in {active, degraded}``).
            include_lifecycle = tuple(sorted(set(
                str(item) for item in value.get("include_lifecycle", ()))))
            unknown_lifecycle = sorted(
                item for item in include_lifecycle
                if item not in {"scheduled", "active", "degraded", "disabled",
                                "destroyed", "despawned"}
            )
            if unknown_lifecycle:
                fail(
                    f"scenario.{reference_code}_selector_invalid",
                    section,
                    unknown_lifecycle,
                    "selector include_lifecycle names an unknown lifecycle state",
                )
            if (
                any(item not in faction_ids for item in factions)
                or any(item not in zone_ids for item in zones)
                or any(item not in event_ids for item in events)
            ):
                fail(
                    f"scenario.{reference_code}_reference_missing",
                    section,
                    value,
                    "selector endpoint is missing",
                )
            selected_items: list[str] = []
            for identifier in candidates:
                entity = by_id[identifier]
                matches = not (
                    (factions and entity.faction_id not in factions)
                    or (platforms and entity.platform_ref not in platforms)
                    or (domains and entity.domain not in domains)
                    or any(tag not in entity.tags for tag in tags)
                )
                bound_capabilities: set[str] = set()
                if entity.composition.sensor_refs:
                    bound_capabilities.add("sensor")
                if entity.composition.communication_refs:
                    bound_capabilities.add("communication")
                if entity.composition.loadout_ref:
                    bound_capabilities.add("weapon")
                matches = matches and not any(
                    capability not in bound_capabilities for capability in capabilities
                )
                if explicit_ids and not matches:
                    fail(
                        f"scenario.{reference_code}_reference_missing",
                        section,
                        value,
                        "selector does not match entity",
                    )
                if matches:
                    selected_items.append(identifier)
            selected = tuple(selected_items)
            if not selected and not allow_empty:
                fail(
                    f"scenario.{reference_code}_selector_empty",
                    section,
                    value,
                    "selector filter intersection is empty",
                )
            return cast(
                _FrozenRecordV2,
                _record(
                    {
                        "entity_ids": selected,
                        "faction_ids": factions,
                        "platforms": platforms,
                        "domains": domains,
                        "capabilities": capabilities,
                        "tags": tags,
                        "zones": zones,
                        "events": events,
                        "include_lifecycle": include_lifecycle,
                    }
                ),
            )

        mission_raw = raw.get("mission_rules", ())
        rules: list[_FrozenRecordV2] = []
        rule_ids = [item.get("id") for item in mission_raw]
        if len(rule_ids) != len(set(rule_ids)):
            fail(
                "scenario.mission_rule_duplicate",
                "mission_rules",
                rule_ids,
                "mission rule IDs duplicate",
            )
        state_values = raw.get("mission_states", ())
        if (
            not isinstance(state_values, (list, tuple))
            or not state_values
            or any(not isinstance(value, str) or not value for value in state_values)
        ):
            fail(
                "scenario.mission_state_invalid",
                "mission_rules",
                state_values,
                "mission states must be nonempty identifiers",
            )
        if len(state_values) != len(set(state_values)):
            fail(
                "scenario.mission_state_duplicate",
                "mission_rules",
                state_values,
                "mission states duplicate",
            )
        states = set(state_values)
        scoring_declaration = raw.get("scoring")
        metric_ids = {
            str(metric.get("id"))
            for metric in (
                scoring_declaration.get("metrics", ())
                if isinstance(scoring_declaration, Mapping)
                else ()
            )
            if isinstance(metric, Mapping) and isinstance(metric.get("id"), str)
        }
        dependencies: dict[str, set[str]] = {}

        def nested_rule_references(value: Any) -> set[str]:
            if isinstance(value, Mapping):
                nested_parameters = value.get("parameters", value)
                if not isinstance(nested_parameters, Mapping):
                    return set()
                return nested_rule_references(nested_parameters.get("conditions", ()))
            if isinstance(value, (list, tuple)):
                result: set[str] = set()
                for item in value:
                    if isinstance(item, str):
                        result.add(item)
                    else:
                        result.update(nested_rule_references(item))
                return result
            return set()

        for item in mission_raw:
            condition = item.get("condition", {})
            operator = condition.get("operator")
            if operator not in _MISSION_RUNTIME_OPERATORS_V2:
                fail(
                    "scenario.mission_operator_invalid",
                    "mission_rules",
                    operator,
                    "mission operator is invalid",
                )
            parameters = condition.get("parameters", {})
            try:
                normalized_parameters = _validated_mission_parameters_v2(
                    operator,
                    parameters,
                    states=states,
                    event_ids=event_ids,
                    zone_ids=zone_ids,
                    entity_ids=set(by_id),
                    metric_ids=metric_ids,
                )
            except ValueError:
                if (
                    operator == "state"
                    and isinstance(parameters, Mapping)
                    and isinstance(parameters.get("state"), str)
                    and parameters.get("state") not in states
                ):
                    fail(
                        "scenario.mission_state_reference_missing",
                        "mission_rules",
                        parameters,
                        "mission state endpoint is missing",
                    )
                fail(
                    "scenario.mission_parameter_invalid",
                    "mission_rules",
                    parameters,
                    "mission parameters are invalid",
                )
            outcome = item.get("outcome")
            if not isinstance(outcome, Mapping) or set(outcome) - {
                "set_state",
                "emit_event",
                "terminal",
                "result",
                "ranking",
            }:
                fail(
                    "scenario.mission_outcome_forbidden",
                    "mission_rules",
                    outcome,
                    "mission outcome contains forbidden mutation",
                )
            if outcome.get("set_state") not in states:
                fail(
                    "scenario.mission_state_reference_missing",
                    "mission_rules",
                    outcome,
                    "mission state endpoint is missing",
                )
            if outcome.get("emit_event") not in event_ids:
                fail(
                    "scenario.mission_reference_missing",
                    "mission_rules",
                    outcome,
                    "mission outcome endpoint is missing",
                )
            terminal = outcome.get("terminal", False)
            result = outcome.get("result")
            ranking = outcome.get("ranking", {})
            if (
                not isinstance(terminal, bool)
                or not isinstance(ranking, Mapping)
                or any(
                    faction not in faction_ids
                    or not isinstance(rank, int)
                    or isinstance(rank, bool)
                    or rank <= 0
                    for faction, rank in ranking.items()
                )
                or len(set(ranking.values())) != len(ranking)
                or (
                    terminal
                    and (not isinstance(result, str) or not result or set(ranking) != faction_ids)
                )
                or (not terminal and (result is not None or bool(ranking)))
            ):
                fail(
                    "scenario.mission_outcome_invalid",
                    "mission_rules",
                    outcome,
                    "terminal mission outcome evidence is invalid",
                )
            normalized_outcome = _FrozenRecordV2(
                MappingProxyType(
                    {
                        "set_state": outcome["set_state"],
                        "emit_event": outcome["emit_event"],
                        "terminal": terminal,
                        "result": result,
                        "ranking": MappingProxyType(dict(sorted(ranking.items()))),
                    }
                )
            )
            resolved_selector = selector(condition.get("selector", {}), "mission_rules")
            condition_references = (
                nested_rule_references(normalized_parameters.get("conditions", ()))
                if operator in {"all", "any", "not"}
                else set()
            )
            dependencies[str(item["id"])] = set(item.get("depends_on", ())) | (condition_references)
            rules.append(
                _record(
                    {
                        **item,
                        "depends_on": tuple(sorted(dependencies[str(item["id"])])),
                        "condition": {
                            **condition,
                            "parameters": normalized_parameters,
                        },
                        "outcome": normalized_outcome,
                        "selector_resolution": resolved_selector,
                    }
                )
            )
        if any(dep not in dependencies for deps in dependencies.values() for dep in deps):
            fail(
                "scenario.mission_dependency_missing",
                "mission_rules",
                dependencies,
                "mission dependency endpoint is missing",
            )
        remaining = dict(dependencies)
        while remaining:
            ready = [key for key, deps in remaining.items() if not deps]
            if not ready:
                fail(
                    "scenario.mission_dependency_cycle",
                    "mission_rules",
                    remaining,
                    "mission dependency cycle",
                )
            for key in ready:
                remaining.pop(key)
                for deps in remaining.values():
                    deps.discard(key)
        rules.sort(key=lambda item: (-item.priority, item.id))

        scoring_raw = raw.get("scoring")
        scoring: _FrozenRecordV2 | None = None
        if isinstance(scoring_raw, Mapping):
            metrics = list(scoring_raw.get("metrics", ()))
            aggregation_version = scoring_raw.get("aggregation_version", "raw-v1")
            if aggregation_version not in {"raw-v1", "utility-v1"}:
                fail(
                    "scenario.scoring_contract_version_invalid",
                    "scoring",
                    aggregation_version,
                    "scoring aggregation version is invalid",
                )
            utility_v1 = aggregation_version == "utility-v1"
            ids = [item.get("id") for item in metrics]
            if len(ids) != len(set(ids)):
                fail(
                    "scenario.scoring_metric_duplicate",
                    "scoring",
                    ids,
                    "scoring metric IDs duplicate",
                )
            for metric in metrics:
                weight = metric.get("weight")
                if (
                    not isinstance(weight, (int, float))
                    or isinstance(weight, bool)
                    or not math.isfinite(float(weight))
                    or weight < 0
                ):
                    fail(
                        "scenario.scoring_weight_invalid",
                        "scoring",
                        weight,
                        "weight must be finite nonnegative numeric",
                    )
                for field, allowed_values, code in (
                    (
                        "aggregation",
                        {"count", "sum", "mean", "min", "max"},
                        "scenario.scoring_aggregation_invalid",
                    ),
                    ("unit", {"1", "m", "s", "points"}, "scenario.scoring_unit_invalid"),
                    ("direction", {"maximize", "minimize"}, "scenario.scoring_direction_invalid"),
                ):
                    if metric.get(field) not in allowed_values:
                        fail(code, "scoring", metric.get(field), f"scoring {field} is invalid")
                available = metric.get("available")
                value = metric.get("value")
                if not isinstance(available, bool):
                    fail(
                        "scenario.scoring_value_invalid",
                        "scoring",
                        metric,
                        "N/A availability is inconsistent",
                    )
                if available and (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(float(value))
                ):
                    fail(
                        "scenario.scoring_value_invalid",
                        "scoring",
                        value,
                        "available metric value must be finite numeric",
                    )
                if not available and value is not None:
                    fail(
                        "scenario.scoring_na_invalid",
                        "scoring",
                        value,
                        "unavailable metric must use N/A without a numeric value",
                    )
                event_source = metric.get("event_source")
                if event_source is not None:
                    if not isinstance(event_source, Mapping):
                        fail(
                            "scenario.scoring_event_source_invalid",
                            "scoring",
                            event_source,
                            "event score source must be a typed object",
                        )
                    expected_fields = {
                        "event_id",
                        "event_type",
                        "value_path",
                        "source",
                        "unit",
                        "aggregation",
                    }
                    source_event_id = event_source.get("event_id")
                    value_path = event_source.get("value_path")
                    if (
                        set(event_source) != expected_fields
                        or source_event_id not in event_types
                        or event_source.get("event_type") != event_types.get(source_event_id)
                        or event_source.get("source") != "world_typed_event_receipt"
                        or not isinstance(value_path, str)
                        or re.fullmatch(
                            r"payload\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*",
                            value_path,
                        )
                        is None
                        or event_source.get("unit") != metric.get("unit")
                        or event_source.get("aggregation") != "sum"
                        or metric.get("plugin_ref") is not None
                        or metric.get("plugin_parameters") is not None
                        or available
                        or value is not None
                    ):
                        fail(
                            "scenario.scoring_event_source_invalid",
                            "scoring",
                            event_source,
                            "event score source differs from its typed Resolved event policy",
                        )
                plugin_ref = metric.get("plugin_ref")
                plugin_parameters = metric.get("plugin_parameters")
                if plugin_ref is not None or plugin_parameters is not None:
                    if not isinstance(plugin_ref, str) or not isinstance(
                        plugin_parameters, Mapping
                    ):
                        fail(
                            "scenario.scoring_plugin_invalid",
                            "scoring",
                            metric,
                            "scoring plugin declaration is incomplete",
                        )
                    try:
                        metadata = self._catalog.model_registry.metadata(plugin_ref)
                    except (KeyError, ValueError) as error:
                        fail(
                            "scenario.scoring_plugin_untrusted",
                            "scoring",
                            plugin_ref,
                            f"scoring plugin is absent from trusted Registry: {error}",
                        )
                    plugin_unit = plugin_parameters.get("unit")
                    if (
                        metadata.exact_ref != plugin_ref
                        or metadata.interface_version != "2.0"
                        or not metadata.trusted
                        or not metadata.deterministic
                        or plugin_unit != metric.get("unit")
                    ):
                        fail(
                            "scenario.scoring_plugin_untrusted",
                            "scoring",
                            plugin_ref,
                            "scoring plugin trust, determinism, interface, or unit differs",
                        )
                    metric["plugin_evidence"] = {
                        "model_ref": metadata.exact_ref,
                        "artifact_sha256": metadata.artifact_sha256,
                        "interface_version": metadata.interface_version,
                        "input_schema": metadata.input_schema,
                        "output_schema": metadata.output_schema,
                        "trusted": metadata.trusted,
                        "deterministic": metadata.deterministic,
                        "unit": plugin_unit,
                        "parameters_hash": _digest(plugin_parameters),
                    }
                resolved_selector = selector(
                    metric.get("selector", {}), "scoring", allow_empty=utility_v1
                )
                metric["selector_resolution"] = resolved_selector
                if utility_v1:
                    required = metric.get("required", False)
                    normalization = metric.get("normalization")
                    if (
                        not isinstance(required, bool)
                        or not isinstance(normalization, Mapping)
                        or set(normalization) != {"lower_bound", "upper_bound"}
                    ):
                        fail(
                            "scenario.scoring_normalization_invalid",
                            "scoring",
                            normalization,
                            "utility-v1 metrics require required and explicit normalization bounds",
                        )
                    lower = normalization.get("lower_bound")
                    upper_declaration = normalization.get("upper_bound")
                    if (
                        not isinstance(lower, (int, float))
                        or isinstance(lower, bool)
                        or not math.isfinite(float(lower))
                    ):
                        fail(
                            "scenario.scoring_normalization_invalid",
                            "scoring",
                            lower,
                            "normalization lower bound must be finite numeric",
                        )
                    if upper_declaration == "selector_cardinality":
                        upper = float(len(resolved_selector.entity_ids))
                    elif (
                        isinstance(upper_declaration, (int, float))
                        and not isinstance(upper_declaration, bool)
                        and math.isfinite(float(upper_declaration))
                    ):
                        upper = float(upper_declaration)
                    else:
                        fail(
                            "scenario.scoring_normalization_invalid",
                            "scoring",
                            upper_declaration,
                            (
                                "normalization upper bound must be finite numeric or "
                                "selector_cardinality"
                            ),
                        )
                    if upper <= float(lower):
                        if upper_declaration == "selector_cardinality" and upper == 0.0:
                            if required:
                                fail(
                                    "scenario.scoring_required_metric_unavailable",
                                    "scoring",
                                    metric["id"],
                                    (
                                        "required selector-cardinality metric resolves to "
                                        "zero entities"
                                    ),
                                )
                            metric["available"] = False
                            metric["value"] = None
                            metric["not_applicable_reason"] = "selector_cardinality_zero"
                        else:
                            fail(
                                "scenario.scoring_normalization_invalid",
                                "scoring",
                                normalization,
                                "normalization upper bound must exceed lower bound",
                            )
                    else:
                        metric["not_applicable_reason"] = None
                    metric["required"] = required
                    metric["normalization"] = {
                        "lower_bound": float(lower),
                        "upper_bound": upper,
                    }
                elif "normalization" in metric or "required" in metric:
                    fail(
                        "scenario.scoring_contract_version_invalid",
                        "scoring",
                        metric,
                        "normalization declarations require utility-v1",
                    )
            if scoring_raw.get("weight_policy") != "normalized_sum_one":
                fail(
                    "scenario.scoring_weight_policy_invalid",
                    "scoring",
                    scoring_raw,
                    "weight policy missing or invalid",
                )
            if abs(sum(float(item["weight"]) for item in metrics) - 1.0) > 1e-9:
                fail(
                    "scenario.scoring_weight_policy_invalid",
                    "scoring",
                    metrics,
                    "metric weights must sum to one",
                )
            metric_policies = {
                (str(item["aggregation"]), str(item["direction"])) for item in metrics
            }
            total_aggregation = scoring_raw.get("aggregation")
            total_direction = scoring_raw.get("direction")
            if total_aggregation is None and len(metric_policies) == 1:
                total_aggregation = next(iter(metric_policies))[0]
            if total_direction is None and len(metric_policies) == 1:
                total_direction = next(iter(metric_policies))[1]
            if total_aggregation not in {"count", "sum", "mean", "min", "max"}:
                fail(
                    "scenario.scoring_aggregation_invalid",
                    "scoring",
                    total_aggregation,
                    "mixed metric policies require an explicit total aggregation",
                )
            if total_direction not in {"maximize", "minimize"}:
                fail(
                    "scenario.scoring_direction_invalid",
                    "scoring",
                    total_direction,
                    "mixed metric policies require an explicit total direction",
                )
            if utility_v1 and (total_aggregation != "sum" or total_direction != "maximize"):
                fail(
                    "scenario.scoring_contract_version_invalid",
                    "scoring",
                    {"aggregation": total_aggregation, "direction": total_direction},
                    "utility-v1 requires sum aggregation and maximize total direction",
                )
            metrics.sort(key=lambda item: item["id"])
            scoring = _record(
                {
                    "weight_policy": "normalized_sum_one",
                    "aggregation": total_aggregation,
                    "direction": total_direction,
                    "aggregation_version": aggregation_version,
                    "metrics": metrics,
                }
            )

        policy = raw.get("controller_policy")
        slots_raw = list(raw.get("controller_slots", ()))
        if "controller_policy" not in raw and (slots_raw or "controller_slots" in raw):
            fail(
                "scenario.controller_policy_missing",
                "controller_slots",
                "<missing>",
                "controller policy is required",
            )
        if "controller_policy" in raw and policy != "explicit_uncontrolled":
            fail(
                "scenario.controller_policy_invalid",
                "controller_slots",
                "<null>" if policy is None else policy,
                "controller policy is invalid",
            )
        slots: list[_FrozenRecordV2] = []
        slot_ids = [item.get("id") for item in slots_raw]
        controller_ids = [item.get("controller_id") for item in slots_raw]
        if len(slot_ids) != len(set(slot_ids)):
            fail(
                "scenario.controller_slot_duplicate",
                "controller_slots",
                slot_ids,
                "controller slot IDs duplicate",
            )
        if len(controller_ids) != len(set(controller_ids)):
            fail(
                "scenario.controller_duplicate",
                "controller_slots",
                controller_ids,
                "controller IDs duplicate",
            )
        claimed: set[str] = set()
        for item in slots_raw:
            if (
                item.get("action_schema_ref") != "action-batch@2.0"
                or item.get("observation_schema_ref") != "observation@2.0"
            ):
                fail(
                    "scenario.controller_schema_invalid",
                    "controller_slots",
                    item,
                    "controller schema ref is invalid",
                )
            resolved_selector = selector(item.get("selector", {}), "controller")
            entity_ids = resolved_selector.entity_ids
            endpoint = item.get("controller_endpoint_ref")
            if endpoint is not None:
                endpoint_entity = by_id.get(endpoint)
                if (
                    not isinstance(endpoint, str)
                    or endpoint_entity is None
                    or endpoint_entity.faction_id != item.get("faction_id")
                    or not endpoint_entity.composition.communication_refs
                ):
                    fail(
                        "scenario.controller_endpoint_invalid",
                        "controller_slots",
                        item,
                        "controller endpoint must name a same-faction entity with communications",
                    )
            inbox_capacity = item.get("inbox_capacity", 256)
            if (
                not isinstance(inbox_capacity, int)
                or isinstance(inbox_capacity, bool)
                or not 1 <= inbox_capacity <= 4096
            ):
                fail(
                    "scenario.controller_inbox_capacity_invalid",
                    "controller_slots",
                    item,
                    "controller inbox capacity must be within 1..4096",
                )
            if any(
                by_id[identifier].faction_id != item.get("faction_id") for identifier in entity_ids
            ):
                fail(
                    "scenario.controller_ownership_invalid",
                    "controller_slots",
                    item,
                    "controller faction does not own claim",
                )
            available_capabilities: set[str] = set()
            for identifier in entity_ids:
                composition = by_id[identifier].composition
                if composition.dynamics_ref is not None:
                    available_capabilities.add("dynamics")
                if composition.sensor_refs:
                    available_capabilities.add("sensor")
                if composition.communication_refs:
                    available_capabilities.add("communication")
                if composition.loadout_ref is not None:
                    available_capabilities.add("weapon")
            if any(
                capability not in available_capabilities
                for capability in item.get("required_capabilities", ())
            ):
                fail(
                    "scenario.controller_capability_missing",
                    "controller_slots",
                    item,
                    "required capability is missing",
                )
            if item.get("exclusive") and claimed.intersection(entity_ids):
                fail(
                    "scenario.controller_claim_conflict",
                    "controller_slots",
                    item,
                    "exclusive controller claim conflicts",
                )
            claimed.update(entity_ids)
            slots.append(
                _record(
                    {
                        **item,
                        "inbox_capacity": inbox_capacity,
                        "resolved_entity_ids": entity_ids,
                        "selector_resolution": resolved_selector,
                    }
                )
            )
        slots.sort(key=lambda item: item.id)

        return tuple(rules), scoring, tuple(slots), cast(str | None, policy)

    def _resolve_visibility(
        self,
        declarations: Mapping[str, Any],
        faction_ids: set[str],
        controllers: tuple[_FrozenRecordV2, ...],
    ) -> tuple[_FrozenRecordV2, ...]:
        visibility_raw = list(declarations.get("rules", ()))
        matrix: list[_FrozenRecordV2] = []
        seen: dict[tuple[Any, ...], bool] = {}
        controller_set = {item.controller_id for item in controllers}

        def fail(code: str, value: Any, reason: str) -> NoReturn:
            raise self._error(
                code,
                ("visibility",),
                value,
                reason,
                "correct the declarative visibility policy",
                file="visibility.yaml",
            )

        for item in visibility_raw:
            if not isinstance(item, Mapping):
                fail("scenario.visibility_view_invalid", item, "visibility rule must be an object")
            view, scope = item.get("view"), item.get("scope")
            if view not in {"referee", "public", "faction", "controller"}:
                fail("scenario.visibility_view_invalid", view, "visibility view is invalid")
            if scope not in {"truth", "public", "own_and_contacts", "claimed_entities"}:
                fail("scenario.visibility_scope_invalid", scope, "visibility scope is invalid")
            if not isinstance(item.get("allow"), bool):
                fail(
                    "scenario.visibility_allow_invalid",
                    item.get("allow"),
                    "visibility allow must be boolean",
                )
            if (view == "faction" and item.get("faction_id") not in faction_ids) or (
                view == "controller"
                and bool(controllers)
                and item.get("controller_id") not in controller_set
            ):
                fail("scenario.visibility_endpoint_missing", item, "visibility endpoint missing")
            if view == "public" and scope == "truth":
                fail(
                    "scenario.visibility_leakage", item, "public truth visibility leaks information"
                )
            visibility_key = (view, item.get("faction_id"), item.get("controller_id"), scope)
            if visibility_key in seen and seen[visibility_key] != item.get("allow"):
                fail("scenario.visibility_conflict", item, "visibility rules conflict")
            seen[visibility_key] = bool(item.get("allow"))
            matrix.append(_record(item))
        matrix.sort(
            key=lambda item: (
                item.view,
                str(item.values.get("faction_id", "")),
                str(item.values.get("controller_id", "")),
                item.scope,
            )
        )
        return tuple(matrix)

    @staticmethod
    def _finite_vector(value: Any, dimensions: set[int]) -> tuple[float, ...] | None:
        if (
            not isinstance(value, Sequence)
            or isinstance(value, (str, bytes, bytearray))
            or len(value) not in dimensions
            or any(
                not isinstance(item, (int, float))
                or isinstance(item, bool)
                or not math.isfinite(float(item))
                for item in value
            )
        ):
            return None
        return tuple(float(item) for item in value)

    @staticmethod
    def _point_in_polygon(
        point: tuple[float, float], polygon: tuple[tuple[float, float], ...], tolerance: float
    ) -> str:
        x, y = point
        inside = False
        for index, first in enumerate(polygon):
            second = polygon[(index + 1) % len(polygon)]
            cross = (second[0] - first[0]) * (y - first[1]) - (second[1] - first[1]) * (
                x - first[0]
            )
            if (
                abs(cross) <= tolerance
                and min(first[0], second[0]) - tolerance
                <= x
                <= max(first[0], second[0]) + tolerance
                and min(first[1], second[1]) - tolerance
                <= y
                <= max(first[1], second[1]) + tolerance
            ):
                return "edge"
            if (first[1] > y) != (second[1] > y):
                crossing_x = (second[0] - first[0]) * (y - first[1]) / (
                    second[1] - first[1]
                ) + first[0]
                if x < crossing_x:
                    inside = not inside
        return "inside" if inside else "outside"

    @staticmethod
    def _segments_intersect(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
        tolerance: float,
    ) -> bool:
        def orientation(
            p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]
        ) -> float:
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        def on_segment(
            first: tuple[float, float],
            point: tuple[float, float],
            second: tuple[float, float],
        ) -> bool:
            return (
                abs(orientation(first, second, point)) <= tolerance
                and min(first[0], second[0]) - tolerance
                <= point[0]
                <= max(first[0], second[0]) + tolerance
                and min(first[1], second[1]) - tolerance
                <= point[1]
                <= max(first[1], second[1]) + tolerance
            )

        ac = orientation(a, b, c)
        ad = orientation(a, b, d)
        ca = orientation(c, d, a)
        cb = orientation(c, d, b)
        if ac * ad < 0.0 and ca * cb < 0.0:
            return True
        return (
            (abs(ac) <= tolerance and on_segment(a, c, b))
            or (abs(ad) <= tolerance and on_segment(a, d, b))
            or (abs(ca) <= tolerance and on_segment(c, a, d))
            or (abs(cb) <= tolerance and on_segment(c, b, d))
        )

    def _materialize_map_terrain(
        self,
        world: _ResolvedWorldV2,
        map_binding: ResolvedResourceBindingV2 | None,
    ) -> _ResolvedWorldV2:
        """Expand a map's verified land layer into generic resolved topology."""

        if map_binding is None or world.map_ref is None:
            return world
        if map_binding.resource_type != "maps" or map_binding.exact_ref != world.map_ref:
            self._pipeline_fail("resolved map binding does not match world map reference")
        try:
            terrain = load_map_terrain_v2(map_binding.normalized_content)
        except MapTerrainErrorV2 as error:
            raise self._error(
                "scenario.map_terrain_invalid",
                ("world", "map_ref"),
                world.map_ref,
                str(error),
                "correct the map terrain source and its hash in the Catalog",
                file="world.yaml",
            ) from error
        if terrain is None:
            return world
        return self._world_with_map_terrain(world, terrain)

    def _world_with_map_terrain(
        self, world: _ResolvedWorldV2, terrain: MapTerrainV2
    ) -> _ResolvedWorldV2:
        """Preserve declared zones and add canonical terrain zones/boundaries."""

        frame = world.coordinate_frame
        if frame is None:
            frame = _CoordinateFrameV2(
                canonical_frame="local_m",
                origin_wgs84=terrain.origin_wgs84,
                axis_orientation="east_north_up",
                height_semantics="metres_above_origin",
                local_bounds_m=terrain.bounds_m,
                tolerance_m=1e-6,
            )
        elif (
            frame.canonical_frame != "local_m"
            or frame.axis_orientation != "east_north_up"
            or frame.height_semantics != "metres_above_origin"
            or tuple(frame.origin_wgs84) != terrain.origin_wgs84
            or tuple(frame.local_bounds_m) != terrain.bounds_m
        ):
            raise self._error(
                "scenario.map_terrain_frame_mismatch",
                ("world", "map_ref"),
                world.map_ref,
                "map terrain origin or bounds differ from the resolved coordinate frame",
                "use the map resource's canonical local coordinate frame",
                file="world.yaml",
            )
        transform = world.map_transform
        if transform is None:
            transform = _freeze(
                {
                    "resolution_m_per_unit": [1.0, 1.0, 1.0],
                    "map_origin_local_m": [0.0, 0.0, 0.0],
                    "map_bounds": [list(terrain.bounds_m[0]), list(terrain.bounds_m[1])],
                    "axis_orientation": "east_north_up",
                }
            )
        zones: list[_ResolvedZoneV2] = []
        zone_ids: set[str] = set()
        for item in world.zones:
            if isinstance(item, _ResolvedZoneV2):
                zone = item
            else:
                if item.geometry_type != "polygon" or len(item.coordinates_m) < 3:
                    raise self._error(
                        "scenario.map_terrain_zone_invalid",
                        ("world", "zones", item.id),
                        item.model_dump(mode="json"),
                        (
                            "maps with terrain require polygon zones with at least three "
                            "local vertices"
                        ),
                        "use a polygon local-metre zone or add explicit coordinate metadata",
                        file="world.yaml",
                    )
                zone = _ResolvedZoneV2(
                    id=item.id,
                    geometry=_ZoneGeometryV2(
                        type="polygon",
                        positions_m=tuple(
                            (float(point[0]), float(point[1])) for point in item.coordinates_m
                        ),
                    ),
                    domains=(),
                    tags=tuple(item.tags),
                )
            if zone.id in zone_ids:
                self._pipeline_fail("duplicate zone IDs reached map terrain materialization")
            zone_ids.add(zone.id)
            zones.append(zone)
        terrain_ids: list[str] = []
        for index, polygon in enumerate(terrain.land_polygons_m):
            zone_id = f"terrain.land.{index:03d}"
            if zone_id in zone_ids:
                raise self._error(
                    "scenario.map_terrain_zone_conflict",
                    ("world", "zones"),
                    zone_id,
                    "map-generated terrain zone ID conflicts with a declared zone",
                    "rename the declared zone",
                    file="world.yaml",
                )
            zone_ids.add(zone_id)
            terrain_ids.append(zone_id)
            zones.append(
                _ResolvedZoneV2(
                    id=zone_id,
                    geometry=_ZoneGeometryV2(type="polygon", positions_m=polygon),
                    domains=(),
                    tags=("terrain:land",),
                )
            )
        boundaries = list(world.boundaries)
        boundary_ids = {item.id for item in boundaries}
        for index, zone_id in enumerate(terrain_ids):
            boundary_id = f"terrain.boundary.land.{index:03d}"
            if boundary_id in boundary_ids:
                self._pipeline_fail("duplicate map terrain boundary ID")
            boundary_ids.add(boundary_id)
            boundaries.append(
                _ResolvedBoundaryV2(
                    id=boundary_id,
                    zone_id=zone_id,
                    action="collision_effect",
                    point_on_edge="inside",
                    priority=100,
                )
            )
        return replace(
            world,
            coordinate_system="local_m",
            zones=tuple(sorted(zones, key=lambda item: item.id)),
            coordinate_frame=frame,
            map_transform=transform,
            boundaries=tuple(sorted(boundaries, key=lambda item: item.id)),
        )

    @staticmethod
    def _terrain_zone_ids(world: _ResolvedWorldV2) -> tuple[str, ...]:
        return tuple(
            zone.id
            for zone in world.zones
            if isinstance(zone, _ResolvedZoneV2) and "terrain:land" in zone.tags
        )

    @staticmethod
    def _terrain_deployment(
        deployment: Mapping[str, Any] | None,
        *,
        domain: str,
        terrain_zone_ids: Sequence[str],
    ) -> Mapping[str, Any] | None:
        """Merge generic terrain constraints without overriding air movement."""

        if not terrain_zone_ids or domain not in {"land", "surface", "underwater"}:
            return deployment
        values = dict(deployment or {})
        allowed = {str(item) for item in values.get("allowed_zone_ids", ())}
        excluded = {str(item) for item in values.get("excluded_zone_ids", ())}
        terrain = set(terrain_zone_ids)
        if domain == "land":
            if allowed and not allowed.issubset(terrain):
                raise CompilerErrorV2(
                    "scenario.terrain_deployment_conflict",
                    file="entities.yaml",
                    path=("deployment", "allowed_zone_ids"),
                    value=sorted(allowed),
                    reason=(
                        "land deployment cannot combine an arbitrary allowed-zone union "
                        "with map land"
                    ),
                    suggestion="use the map terrain zones as the land deployment authority",
                )
            allowed.update(terrain)
        else:
            excluded.update(terrain)
        if allowed & excluded:
            raise CompilerErrorV2(
                "scenario.terrain_deployment_conflict",
                file="entities.yaml",
                path=("deployment",),
                value={"allowed_zone_ids": sorted(allowed), "excluded_zone_ids": sorted(excluded)},
                reason="terrain constraints make the deployment region contradictory",
                suggestion="remove conflicting explicit terrain-zone declarations",
            )
        values["allowed_zone_ids"] = tuple(sorted(allowed))
        values["excluded_zone_ids"] = tuple(sorted(excluded))
        values.setdefault("point_on_edge", "inside")
        return cast(Mapping[str, Any], _freeze(values))

    def _normalize_coordinate_world(
        self, raw: dict[str, Any], expanded: list[dict[str, Any]]
    ) -> tuple[_ResolvedWorldV2 | None, dict[str, Mapping[str, Any]]]:
        world = raw.get("world")
        if not isinstance(world, dict):
            return None, {}
        if "coordinate_frame" not in world and "map_transform" not in world:
            coordinate_system = world.get("coordinate_system")
            if coordinate_system == "wgs84":
                raise self._error(
                    "scenario.coordinate_frame_missing",
                    ("world", "coordinate_frame"),
                    world,
                    "WGS84 world requires explicit coordinate frame metadata",
                    "declare origin, axes, bounds, height semantics, and tolerance",
                    file="world.yaml",
                )
            if coordinate_system == "map":
                raise self._error(
                    "scenario.map_transform_missing",
                    ("world", "map_transform"),
                    world,
                    "map world requires explicit transform metadata",
                    "declare resolution, local origin, axes, and map bounds",
                    file="world.yaml",
                )
            return None, {}
        if "coordinate_frame" not in world:
            raise self._error(
                "scenario.coordinate_frame_missing",
                ("world", "coordinate_frame"),
                world,
                "world coordinate_frame is required",
                "declare canonical local frame, origin, bounds, and tolerance",
                file="world.yaml",
            )
        if "map_transform" not in world:
            raise self._error(
                "scenario.map_transform_missing",
                ("world", "map_transform"),
                world,
                "world map_transform is required",
                "declare map resolution, origin, orientation, and bounds",
                file="world.yaml",
            )
        frame_raw = world["coordinate_frame"]
        transform_raw = world["map_transform"]
        if not isinstance(frame_raw, Mapping) or not isinstance(transform_raw, Mapping):
            raise self._error(
                "scenario.coordinate_frame_invalid",
                ("world", "coordinate_frame"),
                frame_raw,
                "coordinate frame and map transform must be mappings",
                "use the documented coordinate frame structure",
                file="world.yaml",
            )
        origin = self._finite_vector(frame_raw.get("origin_wgs84"), {3})
        bounds_raw = frame_raw.get("local_bounds_m")
        bounds = (
            tuple(self._finite_vector(item, {3}) for item in bounds_raw)
            if isinstance(bounds_raw, Sequence)
            and not isinstance(bounds_raw, (str, bytes))
            and len(bounds_raw) == 2
            else ()
        )
        tolerance = frame_raw.get("tolerance_m")
        if (
            origin is None
            or not -180.0 <= origin[0] <= 180.0
            or not -90.0 <= origin[1] <= 90.0
            or len(bounds) != 2
            or any(item is None for item in bounds)
            or not isinstance(tolerance, (int, float))
            or isinstance(tolerance, bool)
            or not math.isfinite(float(tolerance))
            or float(tolerance) <= 0.0
            or frame_raw.get("canonical_frame") != "local_m"
            or frame_raw.get("axis_orientation") != "east_north_up"
            or frame_raw.get("height_semantics") != "metres_above_origin"
        ):
            raise self._error(
                "scenario.coordinate_frame_invalid",
                ("world", "coordinate_frame"),
                frame_raw,
                "coordinate frame values or dimensions are invalid",
                "use finite WGS84 origin, ordered 3D bounds, and positive tolerance",
                file="world.yaml",
            )
        lower = bounds[0]
        upper = bounds[1]
        if lower is None or upper is None:
            raise self._error(
                "scenario.coordinate_frame_invalid",
                ("world", "coordinate_frame", "local_bounds_m"),
                bounds_raw,
                "local bounds are incomplete",
                "declare lower and upper [x,y,z] bounds",
                file="world.yaml",
            )
        if any(lower[axis] >= upper[axis] for axis in range(3)):
            raise self._error(
                "scenario.coordinate_frame_invalid",
                ("world", "coordinate_frame", "local_bounds_m"),
                bounds_raw,
                "local bounds must be strictly ordered",
                "declare lower and upper [x,y,z] bounds",
                file="world.yaml",
            )
        resolution = self._finite_vector(transform_raw.get("resolution_m_per_unit"), {3})
        map_origin = self._finite_vector(transform_raw.get("map_origin_local_m"), {3})
        map_bounds_raw = transform_raw.get("map_bounds")
        map_bounds = (
            tuple(self._finite_vector(item, {3}) for item in map_bounds_raw)
            if isinstance(map_bounds_raw, Sequence)
            and not isinstance(map_bounds_raw, (str, bytes))
            and len(map_bounds_raw) == 2
            else ()
        )
        if resolution is None or any(value <= 0.0 for value in resolution):
            raise self._error(
                "scenario.map_scale_invalid",
                ("world", "map_transform", "resolution_m_per_unit"),
                transform_raw.get("resolution_m_per_unit"),
                "map resolution must contain three positive finite scales",
                "use positive metres-per-unit values",
                file="world.yaml",
            )
        if map_origin is None or len(map_bounds) != 2 or any(item is None for item in map_bounds):
            raise self._error(
                "scenario.map_transform_invalid",
                ("world", "map_transform"),
                transform_raw,
                "map transform dimensions are invalid",
                "declare 3D map origin and lower/upper map bounds",
                file="world.yaml",
            )
        map_lower = map_bounds[0]
        map_upper = map_bounds[1]
        if map_lower is None or map_upper is None:
            raise self._error(
                "scenario.map_transform_invalid",
                ("world", "map_transform", "map_bounds"),
                transform_raw,
                "map bounds are incomplete",
                "declare lower and upper map bounds",
                file="world.yaml",
            )
        if transform_raw.get("axis_orientation") != "east_north_up" or any(
            map_lower[axis] >= map_upper[axis] for axis in range(3)
        ):
            raise self._error(
                "scenario.map_transform_invalid",
                ("world", "map_transform"),
                transform_raw,
                "map axes or bounds are invalid",
                "use east_north_up and strictly ordered map bounds",
                file="world.yaml",
            )

        def normalize(
            position: Any, path: tuple[str, ...], *, dimensions: set[int]
        ) -> tuple[float, ...]:
            if not isinstance(position, Mapping):
                raise self._error(
                    "scenario.coordinate_invalid",
                    path,
                    position,
                    "position must be discriminated by frame and coordinates",
                    "use {frame: local_m|wgs84|map, coordinates: [...]}",
                )
            coordinates = self._finite_vector(position.get("coordinates"), dimensions)
            frame = position.get("frame")
            if coordinates is None or frame not in {"local_m", "wgs84", "map"}:
                raise self._error(
                    "scenario.coordinate_invalid",
                    path,
                    position,
                    "position frame, dimensions, or numeric values are invalid",
                    "use finite 2D/3D coordinates in a supported frame",
                )
            z = coordinates[2] if len(coordinates) == 3 else None
            local: tuple[float, ...]
            if frame == "wgs84":
                if not -180.0 <= coordinates[0] <= 180.0 or not -90.0 <= coordinates[1] <= 90.0:
                    raise self._error(
                        "scenario.coordinate_invalid",
                        path,
                        position,
                        "longitude or latitude is outside WGS84 range",
                        "use longitude [-180,180] and latitude [-90,90]",
                    )
                earth_radius_m = 6_378_137.0
                longitude_delta = (coordinates[0] - origin[0] + 180.0) % 360.0 - 180.0
                x = (
                    math.radians(longitude_delta)
                    * earth_radius_m
                    * math.cos(math.radians(origin[1]))
                )
                y = math.radians(coordinates[1] - origin[1]) * earth_radius_m
                local = (x, y) if z is None else (x, y, z - origin[2])
            elif frame == "map":
                padded = coordinates if z is not None else (*coordinates, 0.0)
                if any(
                    padded[axis] < map_lower[axis] - float(tolerance)
                    or padded[axis] > map_upper[axis] + float(tolerance)
                    for axis in range(3)
                ):
                    raise self._error(
                        "scenario.coordinate_out_of_bounds",
                        path,
                        position,
                        "map position is outside declared map bounds",
                        "place the position within map_bounds",
                    )
                transformed = tuple(
                    map_origin[axis] + padded[axis] * resolution[axis] for axis in range(3)
                )
                local = transformed[: len(coordinates)]
            else:
                local = coordinates
            quantized = tuple(
                0.0
                if (rounded := round(value / float(tolerance)) * float(tolerance)) == 0.0
                else rounded
                for value in local
            )
            padded_local = quantized if len(quantized) == 3 else (*quantized, lower[2])
            if padded_local[2] < lower[2] - float(tolerance) or padded_local[2] > upper[2] + float(
                tolerance
            ):
                raise self._error(
                    "scenario.altitude_out_of_bounds",
                    path,
                    position,
                    "altitude is outside local vertical bounds",
                    "place altitude within world local_bounds_m",
                )
            if any(
                padded_local[axis] < lower[axis] - float(tolerance)
                or padded_local[axis] > upper[axis] + float(tolerance)
                for axis in (0, 1)
            ):
                raise self._error(
                    "scenario.coordinate_out_of_bounds",
                    path,
                    position,
                    "position is outside local horizontal bounds",
                    "place the position within world local_bounds_m",
                )
            return quantized

        deployments: dict[str, Mapping[str, Any]] = {}
        for index, entity in enumerate(expanded):
            state = entity.get("initial_state")
            if not isinstance(state, dict):
                continue
            position = normalize(
                state.pop("position", None),
                ("entities", str(index), "initial_state", "position"),
                dimensions={3},
            )
            formation_offset = entity.pop("_formation_offset_m", None)
            if formation_offset is not None:
                offset = self._finite_vector(formation_offset, {3})
                if offset is None:
                    raise self._error(
                        "scenario.coordinate_invalid",
                        ("formations", str(index), "offsets_m"),
                        formation_offset,
                        "formation offset must contain three finite metres",
                        "provide [x_m, y_m, z_m] offsets",
                        file="entities.yaml",
                    )
                position = normalize(
                    {
                        "frame": "local_m",
                        "coordinates": [position[axis] + offset[axis] for axis in range(3)],
                    },
                    ("formations", str(index), "initial_state", "position"),
                    dimensions={3},
                )
            state["position_m"] = list(position)
            deployment = entity.pop("deployment", None)
            if isinstance(deployment, Mapping):
                deployments[str(entity.get("id"))] = deployment

        zones_raw = world.get("zones", ())
        if not isinstance(zones_raw, Sequence) or isinstance(zones_raw, (str, bytes)):
            zones_raw = ()
        resolved_zones: list[_ResolvedZoneV2] = []
        zone_ids: set[str] = set()
        for index, zone in enumerate(zones_raw):
            path = ("world", "zones", str(index), "geometry")
            if not isinstance(zone, Mapping) or not isinstance(zone.get("geometry"), Mapping):
                raise self._error(
                    "scenario.zone_geometry_invalid",
                    path,
                    zone,
                    "zone and geometry must be mappings",
                    "declare polygon or circle geometry",
                    file="world.yaml",
                )
            zone_id = zone.get("id")
            if not isinstance(zone_id, str) or zone_id in zone_ids:
                raise self._error(
                    "scenario.zone_duplicate",
                    ("world", "zones", str(index), "id"),
                    zone_id,
                    "zone IDs must be unique",
                    "assign a unique zone ID",
                    file="world.yaml",
                )
            zone_ids.add(zone_id)
            geometry = zone["geometry"]
            geometry_type = geometry.get("type")
            if geometry_type == "polygon":
                positions = geometry.get("positions", ())
                if not isinstance(positions, Sequence) or len(positions) < 3:
                    raise self._error(
                        "scenario.zone_geometry_invalid",
                        path,
                        geometry,
                        "polygon requires at least three vertices",
                        "provide a nondegenerate polygon",
                        file="world.yaml",
                    )
                points = tuple(
                    normalize(item, (*path, "positions", str(point_index)), dimensions={2})
                    for point_index, item in enumerate(positions)
                )
                if len(points) >= 2 and points[-1] == points[0]:
                    points = points[:-1]
                if len(points) < 3 or len(points) != len(set(points)):
                    raise self._error(
                        "scenario.zone_geometry_invalid",
                        path,
                        geometry,
                        "polygon has too few or duplicate quantized vertices",
                        "provide at least three unique vertices after tolerance quantization",
                        file="world.yaml",
                    )
                for vertex in range(len(points)):
                    previous = points[(vertex - 1) % len(points)]
                    current = points[vertex]
                    following = points[(vertex + 1) % len(points)]
                    incoming = (current[0] - previous[0], current[1] - previous[1])
                    outgoing = (following[0] - current[0], following[1] - current[1])
                    cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
                    dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1]
                    if abs(cross) <= float(tolerance) and dot < 0.0:
                        raise self._error(
                            "scenario.zone_self_intersection",
                            path,
                            geometry,
                            "adjacent polygon edges retrace or overlap",
                            "remove collinear edge retracing",
                            file="world.yaml",
                        )
                for first in range(len(points)):
                    for second in range(first + 1, len(points)):
                        if second in {first, first + 1} or (
                            first == 0 and second == len(points) - 1
                        ):
                            continue
                        if self._segments_intersect(
                            cast(tuple[float, float], points[first]),
                            cast(tuple[float, float], points[(first + 1) % len(points)]),
                            cast(tuple[float, float], points[second]),
                            cast(tuple[float, float], points[(second + 1) % len(points)]),
                            float(tolerance),
                        ):
                            raise self._error(
                                "scenario.zone_self_intersection",
                                path,
                                geometry,
                                "polygon edges self-intersect",
                                "provide a simple polygon",
                                file="world.yaml",
                            )
                area = (
                    abs(
                        sum(
                            points[item][0] * points[(item + 1) % len(points)][1]
                            - points[(item + 1) % len(points)][0] * points[item][1]
                            for item in range(len(points))
                        )
                    )
                    / 2.0
                )
                if area <= float(tolerance) ** 2:
                    raise self._error(
                        "scenario.zone_geometry_invalid",
                        path,
                        geometry,
                        "polygon area is degenerate",
                        "provide three or more non-collinear vertices",
                        file="world.yaml",
                    )
                zone_geometry = _ZoneGeometryV2(type="polygon", positions_m=points)
            elif geometry_type == "circle":
                center = normalize(geometry.get("center"), (*path, "center"), dimensions={2})
                radius = geometry.get("radius_m")
                if (
                    not isinstance(radius, (int, float))
                    or isinstance(radius, bool)
                    or not math.isfinite(float(radius))
                    or radius <= 0.0
                ):
                    raise self._error(
                        "scenario.zone_geometry_invalid",
                        path,
                        geometry,
                        "circle radius must be positive and finite",
                        "provide radius_m greater than zero",
                        file="world.yaml",
                    )
                if (
                    center[0] - radius < lower[0]
                    or center[0] + radius > upper[0]
                    or center[1] - radius < lower[1]
                    or center[1] + radius > upper[1]
                ):
                    raise self._error(
                        "scenario.zone_out_of_bounds",
                        path,
                        geometry,
                        "circle extends outside world bounds",
                        "move or resize the circle within local bounds",
                        file="world.yaml",
                    )
                zone_geometry = _ZoneGeometryV2(
                    type="circle", center_m=center, radius_m=float(radius)
                )
            else:
                raise self._error(
                    "scenario.zone_geometry_invalid",
                    path,
                    geometry,
                    "unsupported zone geometry type",
                    "use polygon or circle",
                    file="world.yaml",
                )
            domains = tuple(sorted(str(value) for value in zone.get("domains", ())))
            resolved_zones.append(
                _ResolvedZoneV2(
                    id=zone_id,
                    geometry=zone_geometry,
                    domains=domains,
                    tags=tuple(sorted(str(value) for value in zone.get("tags", ()))),
                )
            )

        boundaries_raw = world.get("boundaries", ())
        if not isinstance(boundaries_raw, Sequence) or isinstance(boundaries_raw, (str, bytes)):
            boundaries_raw = ()
        boundaries: list[_ResolvedBoundaryV2] = []
        boundary_ids: set[str] = set()
        valid_actions = {
            "reject_command",
            "constrain_motion",
            "stop",
            "reflect",
            "collision_effect",
            "deactivate",
            "mission_event",
        }
        for index, boundary in enumerate(boundaries_raw):
            boundary_path = ("world", "boundaries", str(index))
            if not isinstance(boundary, Mapping):
                raise self._error(
                    "scenario.boundary_invalid",
                    boundary_path,
                    boundary,
                    "boundary must be a mapping",
                    "declare boundary id, zone, action, and edge policy",
                    file="world.yaml",
                )
            boundary_id = boundary.get("id")
            if not isinstance(boundary_id, str) or boundary_id in boundary_ids:
                raise self._error(
                    "scenario.boundary_duplicate",
                    (*boundary_path, "id"),
                    boundary_id,
                    "boundary IDs must be unique",
                    "assign a unique boundary ID",
                    file="world.yaml",
                )
            boundary_ids.add(boundary_id)
            zone_id = boundary.get("zone_id")
            if zone_id not in zone_ids:
                raise self._error(
                    "scenario.boundary_zone_missing",
                    (*boundary_path, "zone_id"),
                    zone_id,
                    "boundary references an unknown zone",
                    "use a declared zone ID",
                    file="world.yaml",
                )
            action = boundary.get("action")
            if action not in valid_actions:
                raise self._error(
                    "scenario.boundary_action_invalid",
                    (*boundary_path, "action"),
                    action,
                    "boundary action is not allowed",
                    "use a supported declarative boundary action",
                    file="world.yaml",
                )
            edge = boundary.get("point_on_edge", "inside")
            if edge not in {"inside", "outside"}:
                raise self._error(
                    "scenario.edge_policy_invalid",
                    (*boundary_path, "point_on_edge"),
                    edge,
                    "point_on_edge policy is invalid",
                    "use inside or outside",
                    file="world.yaml",
                )
            priority = boundary.get("priority", 0)
            if not isinstance(priority, int) or isinstance(priority, bool):
                raise self._error(
                    "scenario.boundary_priority_invalid",
                    (*boundary_path, "priority"),
                    priority,
                    "boundary priority must be an integer",
                    "use an integer priority; larger values are evaluated first",
                    file="world.yaml",
                )
            boundaries.append(
                _ResolvedBoundaryV2(
                    id=boundary_id,
                    zone_id=str(zone_id),
                    action=str(action),
                    point_on_edge=str(edge),
                    priority=priority,
                )
            )

        for event_index, event in enumerate(raw.get("events", ())):
            if not isinstance(event, dict) or not isinstance(event.get("payload"), dict):
                continue
            payload = event["payload"]
            if "position" in payload:
                payload["position_m"] = list(
                    normalize(
                        payload.pop("position"),
                        ("events", str(event_index), "payload", "position"),
                        dimensions={2, 3},
                    )
                )

        frame = _CoordinateFrameV2(
            canonical_frame="local_m",
            origin_wgs84=origin,
            axis_orientation=str(frame_raw.get("axis_orientation")),
            height_semantics=str(frame_raw.get("height_semantics")),
            local_bounds_m=(lower, upper),
            tolerance_m=float(tolerance),
        )
        sorted_zones: tuple[_ResolvedZoneV2, ...] = tuple(
            sorted(
                resolved_zones,
                key=lambda item: (item.geometry.type != "polygon", item.id),
            )
        )
        try:
            spatial_damage_policy = (
                None
                if world.get("spatial_damage_policy") is None
                else SpatialDamagePolicyV2.model_validate(world["spatial_damage_policy"])
            )
            roe_rules = tuple(
                RoePolicyV2.model_validate(item) for item in world.get("roe_rules", ())
            )
        except ValidationError as error:
            raise self._error(
                "scenario.spatial_damage_policy_invalid",
                ("world", "spatial_damage_policy"),
                world.get("spatial_damage_policy"),
                str(error.errors()[0].get("msg", "invalid spatial damage policy")),
                "declare a finite canonical spatial magnitude model and exact effect ref",
                file="world.yaml",
            ) from error
        resolved_world = _ResolvedWorldV2(
            coordinate_system="local_m",
            map_ref=None,
            zones=sorted_zones,
            boundary_policy=(boundaries[0].action if boundaries else None),
            spatial_damage_policy=spatial_damage_policy,
            roe_rules=roe_rules,
            coordinate_frame=frame,
            map_transform=_freeze(dict(transform_raw)),
            boundaries=tuple(sorted(boundaries, key=lambda item: item.id)),
            duration_ticks=world.get("duration_ticks"),
            tick_seconds=world.get("tick_seconds"),
            deployment_excluded_zone_ids=tuple(
                sorted(
                    {
                        str(zone_id)
                        for deployment in deployments.values()
                        for zone_id in deployment.get("excluded_zone_ids", ())
                    }
                )
            ),
        )
        raw["world"] = {
            "schema_version": "2.0",
            "coordinate_system": "local_m",
            "boundary_policy": resolved_world.boundary_policy,
            "spatial_damage_policy": _json_value(resolved_world.spatial_damage_policy),
            "roe_rules": _json_value(resolved_world.roe_rules),
            "duration_ticks": resolved_world.duration_ticks,
            "tick_seconds": resolved_world.tick_seconds,
            "zones": [
                {
                    "schema_version": "2.0",
                    "id": zone.id,
                    "geometry_type": zone.geometry.type,
                    "coordinates_m": (
                        list(zone.geometry.positions_m)
                        if zone.geometry.positions_m
                        else [list(zone.geometry.center_m or (0.0, 0.0))]
                    ),
                    "tags": list(zone.tags),
                }
                for zone in sorted_zones
            ],
        }
        return resolved_world, deployments

    @staticmethod
    def _pattern(pattern: object, path: tuple[str, ...]) -> str:
        if not isinstance(pattern, str):
            raise ScenarioCompilerV2._error(
                "scenario.formation_pattern_invalid",
                path,
                pattern,
                "formation ID pattern must be a string",
                "use a Python format field such as unit-{index:03d}",
                file="entities.yaml",
            )
        fields = []
        try:
            for _literal, field, spec, conversion in string.Formatter().parse(pattern):
                if field is not None:
                    fields.append(field)
                    if (
                        field != "index"
                        or conversion is not None
                        or spec is None
                        or "{" in spec
                        or "}" in spec
                    ):
                        raise ValueError
            if fields != ["index"]:
                raise ValueError
            pattern.format(index=0)
        except (KeyError, IndexError, ValueError):
            raise ScenarioCompilerV2._error(
                "scenario.formation_pattern_invalid",
                path,
                pattern,
                "formation pattern must contain exactly one plain index field",
                "use a pattern such as unit-{index:03d}",
                file="entities.yaml",
            ) from None
        return pattern

    def _resolve_typed_resource(
        self,
        resource_type: ResourceTypeV2,
        reference: object,
        path: tuple[str, ...],
    ) -> CatalogResourceV2:
        if (
            not isinstance(reference, str)
            or re.fullmatch(
                r"[a-z][a-z0-9_.-]*@(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)",
                reference,
            )
            is None
        ):
            raise self._error(
                "scenario.resource_ref_invalid",
                path,
                reference,
                "resource reference must be exact id@semantic-version",
                "use an exact Catalog reference such as resource.name@2.4.1",
                file="entities.yaml",
            )
        try:
            return self._catalog.resolve(resource_type, reference)
        except CatalogResolutionErrorV2 as error:
            raise self._error(
                "scenario.resource_missing",
                path,
                reference,
                str(error),
                f"add or select an existing {resource_type} Catalog resource",
                file="entities.yaml",
            ) from error

    def _expand_resource_entity(self, entity: EntitySpecV2, index: int) -> ResolvedEntityV2:
        platform = self._resolve_typed_resource(
            "platforms", entity.platform_ref, ("entities", str(index), "platform_ref")
        )
        dynamics = (
            None
            if entity.dynamics_ref is None
            else self._resolve_typed_resource(
                "dynamics",
                entity.dynamics_ref,
                ("entities", str(index), "dynamics_ref"),
            )
        )
        loadout = (
            None
            if entity.loadout_ref is None
            else self._resolve_typed_resource(
                "loadouts",
                entity.loadout_ref,
                ("entities", str(index), "loadout_ref"),
            )
        )
        snapshot = self._catalog.snapshot()
        by_reference: dict[str, list[CatalogResourceV2]] = {}
        for resource in snapshot:
            by_reference.setdefault(resource.exact_ref, []).append(resource)

        sensors: list[str] = []
        communications: list[str] = []
        component_resources: list[CatalogResourceV2] = []
        for component_index, reference in enumerate(entity.component_refs):
            if (
                re.fullmatch(
                    r"[a-z][a-z0-9_.-]*@(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)",
                    reference,
                )
                is None
            ):
                raise self._error(
                    "scenario.resource_ref_invalid",
                    ("entities", str(index), "component_refs", str(component_index)),
                    reference,
                    "component reference must use exact semantic version",
                    "use an exact sensor or communication Catalog reference",
                    file="entities.yaml",
                )
            candidates = by_reference.get(reference, [])
            if not candidates:
                raise self._error(
                    "scenario.resource_missing",
                    ("entities", str(index), "component_refs", str(component_index)),
                    reference,
                    "component resource is missing",
                    "add the exact component resource to Catalog",
                    file="entities.yaml",
                )
            if len(candidates) != 1 or candidates[0].resource_type not in {
                "sensors",
                "communications",
            }:
                raise self._error(
                    "scenario.resource_type_mismatch",
                    ("entities", str(index), "component_refs", str(component_index)),
                    reference,
                    "component reference has an unsupported Catalog resource type",
                    "reference a sensor or communication resource",
                    file="entities.yaml",
                )
            component = candidates[0]
            component_resources.append(component)
            if component.resource_type == "sensors":
                sensors.append(reference)
            else:
                communications.append(reference)

        energy_ref = platform.content.get("energy_ref")
        collision_ref = platform.content.get("collision_shape_ref")
        visualization_ref = platform.content.get("visualization_ref")
        composition = EntityCompositionV2(
            schema_version="2.0",
            platform_ref=platform.exact_ref,
            dynamics_ref=None if dynamics is None else dynamics.exact_ref,
            loadout_ref=None if loadout is None else loadout.exact_ref,
            sensor_refs=tuple(sorted(sensors)),
            communication_refs=tuple(sorted(communications)),
            energy_ref=energy_ref if isinstance(energy_ref, str) else None,
            collision_shape_ref=collision_ref if isinstance(collision_ref, str) else None,
            visualization_ref=(visualization_ref if isinstance(visualization_ref, str) else None),
            ammunition=dict(entity.ammunition),
            target_domains=tuple(sorted(entity.target_domains)),
        )
        try:
            self._catalog.validate_full_composition(composition)
        except (CatalogResolutionErrorV2, ValueError) as error:
            raise self._error(
                "scenario.composition_invalid",
                ("entities", str(index)),
                entity.model_dump(mode="json"),
                str(error),
                "select exact mutually compatible Catalog resources",
                file="entities.yaml",
            ) from error

        roots = [platform, *component_resources]
        if dynamics is not None:
            roots.append(dynamics)
        if loadout is not None:
            roots.append(loadout)
        bound_resources: tuple[tuple[ResourceTypeV2, str | None], ...] = (
            ("energy", composition.energy_ref),
            ("collision_shapes", composition.collision_shape_ref),
            ("visualization_assets", composition.visualization_ref),
        )
        for resource_type, bound_reference in bound_resources:
            if bound_reference is not None:
                roots.append(
                    self._resolve_typed_resource(
                        resource_type,
                        bound_reference,
                        ("entities", str(index), f"{resource_type}_ref"),
                    )
                )
        for ammunition_ref in sorted(composition.ammunition):
            roots.append(
                self._resolve_typed_resource(
                    "ammunition",
                    ammunition_ref,
                    ("entities", str(index), "ammunition", ammunition_ref),
                )
            )

        closure: dict[tuple[ResourceTypeV2, str], CatalogResourceV2] = {}
        pending = list(roots)
        while pending:
            resource = pending.pop()
            key = (resource.resource_type, resource.exact_ref)
            if key in closure:
                continue
            closure[key] = resource
            references = set(resource.dependencies)
            for field in (
                "weapon_refs",
                "ammunition_refs",
                "effect_ref",
                "damage_model_ref",
                "weapon_ref",
                "energy_ref",
                "collision_shape_ref",
                "visualization_ref",
            ):
                value = resource.content.get(field)
                if isinstance(value, str):
                    references.add(value)
                elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    references.update(str(item) for item in value)
            for reference in sorted(references, reverse=True):
                candidates = by_reference.get(reference, [])
                if len(candidates) != 1:
                    raise self._error(
                        "scenario.composition_invalid",
                        ("entities", str(index), "dependencies"),
                        reference,
                        f"missing or ambiguous dependency {reference}",
                        "provide one exact dependency resource in Catalog",
                        file="entities.yaml",
                    )
                pending.append(candidates[0])

        grouped: dict[str, list[ResolvedResourceBindingV2]] = {}
        for closure_key in sorted(closure):
            resource = closure[closure_key]
            metadata = self._catalog.model_registry.metadata(resource.model_ref)
            normalized_content = dict(_json_value(resource.content))
            default_evidence: dict[str, _DefaultEvidenceV2] = {}
            required_defaults = resource.content.get("required_defaults", ())
            declared_defaults = resource.content.get("defaults", {})
            if "required_defaults" in resource.content and (
                not isinstance(required_defaults, (list, tuple))
                or any(not isinstance(item, str) or not item for item in required_defaults)
                or len(required_defaults) != len(set(required_defaults))
            ):
                raise self._error(
                    "scenario.resource_default_schema_invalid",
                    ("entities", str(index), "resource_bindings", resource.exact_ref),
                    required_defaults,
                    "required_defaults must be a unique sequence of nonempty strings",
                    "use a list of unique model field names",
                    file="entities.yaml",
                )
            if isinstance(required_defaults, (list, tuple)):
                for required in required_defaults:
                    field = required
                    if field in normalized_content:
                        continue
                    declaration = (
                        declared_defaults.get(field)
                        if isinstance(declared_defaults, Mapping)
                        else None
                    )
                    if (
                        not isinstance(declaration, Mapping)
                        or "value" not in declaration
                        or not isinstance(declaration.get("unit"), str)
                    ):
                        raise self._error(
                            "scenario.resource_default_missing",
                            (
                                "entities",
                                str(index),
                                "resource_bindings",
                                resource.resource_type,
                                resource.exact_ref,
                                "required_defaults",
                            ),
                            field,
                            f"required default {field} is unresolved for "
                            f"{resource.resource_type[:-1]}",
                            "declare a value, unit, and source for the required default",
                            file="entities.yaml",
                        )
                    source = declaration.get("source")
                    if (
                        not isinstance(source, Mapping)
                        or source.get("kind") != "model_metadata"
                        or source.get("id") != metadata.exact_ref
                    ):
                        raise self._error(
                            "scenario.resource_default_source_invalid",
                            (
                                "entities",
                                str(index),
                                "resource_bindings",
                                resource.exact_ref,
                                field,
                            ),
                            source,
                            "default source must identify the exact trusted model metadata",
                            "use {kind: model_metadata, id: <exact model ref>}",
                            file="entities.yaml",
                        )
                    input_unit = declaration["unit"]
                    canonical_unit = metadata.field_units.get(field)
                    if canonical_unit is None:
                        canonical_unit = "1" if input_unit == "1" else None
                    value = declaration["value"]
                    value_type: str | None = None
                    if canonical_unit == "1":
                        value_types = resource.content.get("default_value_types", {})
                        value_type = (
                            value_types.get(field) if isinstance(value_types, Mapping) else None
                        )
                        if value_type not in {"number", "integer", "boolean", "string"}:
                            raise self._error(
                                "scenario.resource_default_schema_invalid",
                                (
                                    "entities",
                                    str(index),
                                    "resource_bindings",
                                    resource.exact_ref,
                                    field,
                                ),
                                value_type,
                                "dimensionless default requires a controlled value_type",
                                "declare number, integer, boolean, or string",
                                file="entities.yaml",
                            )
                        value_valid = (
                            (
                                value_type == "number"
                                and isinstance(value, (int, float))
                                and not isinstance(value, bool)
                                and math.isfinite(float(value))
                            )
                            or (
                                value_type == "integer"
                                and isinstance(value, int)
                                and not isinstance(value, bool)
                            )
                            or (value_type == "boolean" and isinstance(value, bool))
                            or (value_type == "string" and isinstance(value, str))
                        )
                    else:
                        value_valid = (
                            isinstance(value, (int, float))
                            and not isinstance(value, bool)
                            and math.isfinite(float(value))
                        )
                    if not value_valid:
                        raise self._error(
                            "scenario.resource_default_value_invalid",
                            (
                                "entities",
                                str(index),
                                "resource_bindings",
                                resource.exact_ref,
                                field,
                            ),
                            value,
                            "default value does not satisfy its canonical value contract",
                            "provide a finite value of the declared exact type",
                            file="entities.yaml",
                        )
                    conversion_ref = declaration.get("conversion_ref")
                    conversion_scale: float | None = None
                    if canonical_unit is None:
                        raise self._error(
                            "scenario.resource_default_unit_invalid",
                            (
                                "entities",
                                str(index),
                                "resource_bindings",
                                resource.exact_ref,
                                field,
                            ),
                            input_unit,
                            "default field has no canonical model unit",
                            "declare model field_units or use explicit dimensionless unit 1",
                            file="entities.yaml",
                        )
                    if input_unit != canonical_unit:
                        conversions = resource.content.get("trusted_unit_conversions", {})
                        conversion = (
                            conversions.get(conversion_ref)
                            if isinstance(conversions, Mapping)
                            else None
                        )
                        valid_ref = (
                            isinstance(conversion_ref, str)
                            and re.fullmatch(
                                r"[a-z][a-z0-9_.-]*@(0|[1-9]\d*)\.(0|[1-9]\d*)", conversion_ref
                            )
                            is not None
                        )
                        if (
                            not valid_ref
                            or not isinstance(conversion, Mapping)
                            or conversion.get("from") != input_unit
                            or conversion.get("to") != canonical_unit
                        ):
                            raise self._error(
                                "scenario.resource_default_unit_invalid",
                                (
                                    "entities",
                                    str(index),
                                    "resource_bindings",
                                    resource.exact_ref,
                                    field,
                                ),
                                input_unit,
                                "default unit lacks a trusted deterministic canonical conversion",
                                "use the canonical unit or a declared versioned conversion",
                                file="entities.yaml",
                            )
                        scale = conversion.get("scale")
                        if (
                            not isinstance(scale, (int, float))
                            or isinstance(scale, bool)
                            or not math.isfinite(float(scale))
                            or float(scale) <= 0.0
                        ):
                            raise self._error(
                                "scenario.resource_default_conversion_invalid",
                                (
                                    "entities",
                                    str(index),
                                    "resource_bindings",
                                    resource.exact_ref,
                                    field,
                                ),
                                scale,
                                "conversion scale must be a finite positive number",
                                "declare a deterministic positive numeric scale",
                                file="entities.yaml",
                            )
                        conversion_scale = float(scale)
                        value = float(value) * conversion_scale
                    elif conversion_ref is not None:
                        raise self._error(
                            "scenario.resource_default_unit_invalid",
                            (
                                "entities",
                                str(index),
                                "resource_bindings",
                                resource.exact_ref,
                                field,
                            ),
                            conversion_ref,
                            "unit conversion is unnecessary or incompatible",
                            "remove conversion_ref for canonical input units",
                            file="entities.yaml",
                        )
                    normalized_content[field] = value
                    default_evidence[field] = _DefaultEvidenceV2(
                        value=_freeze(value),
                        unit=canonical_unit,
                        source=_DefaultSourceV2(kind="model_metadata", id=metadata.exact_ref),
                        input_value=_freeze(declaration["value"]),
                        input_unit=input_unit,
                        conversion_ref=conversion_ref,
                        conversion_scale=conversion_scale,
                        value_type=value_type,
                    )
            binding = ResolvedResourceBindingV2(
                schema_version=resource.schema_version,
                exact_ref=resource.exact_ref,
                resource_type=resource.resource_type,
                id=resource.id,
                version=resource.version,
                engine_compatibility=resource.engine_compatibility,
                content_hash=resource.content_hash,
                model_ref=resource.model_ref,
                model_evidence=_ModelEvidenceV2(
                    model_ref=metadata.exact_ref,
                    artifact_sha256=metadata.artifact_sha256,
                    interface_version=metadata.interface_version,
                    input_schema=metadata.input_schema,
                    output_schema=metadata.output_schema,
                    trusted=metadata.trusted,
                    deterministic=metadata.deterministic,
                    resource_types=metadata.resource_types,
                ),
                dependencies=resource.dependencies,
                content=_freeze(_json_value(resource.content)),
                normalized_content=_freeze(normalized_content),
                units=_freeze(_json_value(metadata.units)),
                field_units=_freeze(_json_value(metadata.field_units)),
                defaults=MappingProxyType(default_evidence),
            )
            grouped.setdefault(resource.resource_type, []).append(binding)
        bindings = MappingProxyType(
            {
                resource_type: tuple(sorted(values, key=lambda item: item.exact_ref))
                for resource_type, values in sorted(grouped.items())
            }
        )
        return ResolvedEntityV2(
            id=entity.id,
            faction_id=entity.faction_id,
            tags=entity.tags,
            controller_slot=entity.controller_slot,
            composition=composition,
            resource_bindings=bindings,
            runtime_initial=_RuntimeInitialV2(
                initial_state=entity.initial_state,
                ammunition=_freeze(dict(entity.ammunition)),
            ),
            destroyed_lifecycle=entity.destroyed_lifecycle,
        )


__all__ = [
    "CompilerErrorV2",
    "ResolvedBoundaryDeploymentV2",
    "ResolvedEntityV2",
    "ResolvedResourceBindingV2",
    "ResolvedSpatialEffectPolicyV2",
    "ResolvedScenarioV2",
    "ScenarioCompilerV2",
    "ScenarioPackageV2",
    "resolve_world_resource_closure_v2",
]

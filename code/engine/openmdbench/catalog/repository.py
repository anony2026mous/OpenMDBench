"""Read-only catalog resolution, validation and trusted model factories."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable
from copy import deepcopy
from typing import Any

from openmdbench.catalog.models import (
    CatalogDefinition,
    DynamicsDefinition,
    LoadoutDefinition,
    PlatformDefinition,
    ResourceDefinition,
    ResourceType,
    SensorDefinition,
    WeaponDefinition,
)

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
EXACT_REF_RE = re.compile(
    r"^(?P<id>[a-z][a-z0-9_.-]*)@(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
)


class CatalogResolutionError(ValueError):
    pass


class CatalogConflictError(ValueError):
    pass


def _semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semantic version: {value}")
    return tuple(int(item) for item in match.groups())  # type: ignore[return-value]


def parse_exact_resource_ref(value: str) -> tuple[str, str]:
    match = EXACT_REF_RE.fullmatch(value)
    if match is None:
        raise ValueError("resource reference must use exact id@major.minor.patch")
    return match.group("id"), match.group("version")


def engine_compatible(version: str, constraint: str) -> bool:
    actual = _semver(version)
    operators: tuple[
        tuple[str, Callable[[tuple[int, int, int], tuple[int, int, int]], bool]], ...
    ] = (
        (">=", lambda left, right: left >= right),
        ("<=", lambda left, right: left <= right),
        ("==", lambda left, right: left == right),
        (">", lambda left, right: left > right),
        ("<", lambda left, right: left < right),
    )
    for clause in constraint.split(","):
        for operator, compare in operators:
            if clause.startswith(operator):
                if not compare(actual, _semver(clause[len(operator) :])):
                    return False
                break
        else:
            raise ValueError(f"invalid engine compatibility clause: {clause}")
    return True


Factory = Callable[[ResourceDefinition], object]


class ModelRegistry:
    """Trusted factory registry; resource data never imports arbitrary code."""

    def __init__(self) -> None:
        self._factories: dict[tuple[str, str], Factory] = {}
        self._frozen = False

    def register(self, resource_type: ResourceType, model: str, factory: Factory) -> None:
        if self._frozen:
            raise RuntimeError("model registry is frozen")
        key = (resource_type, model)
        if key in self._factories:
            raise CatalogConflictError(f"duplicate model factory: {resource_type}/{model}")
        self._factories[key] = factory

    def freeze(self) -> None:
        self._frozen = True

    def create(
        self, resource_type: ResourceType, model: str, definition: ResourceDefinition
    ) -> object:
        try:
            factory = self._factories[(resource_type, model)]
        except KeyError as error:
            raise CatalogResolutionError(
                f"unknown trusted model factory: {resource_type}/{model}"
            ) from error
        return factory(definition)


class CatalogRepository:
    """Validated immutable definition store with exact-version resolution."""

    def __init__(
        self,
        definitions: Iterable[CatalogDefinition],
        *,
        engine_version: str,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        _semver(engine_version)
        self.engine_version = engine_version
        self._models = model_registry
        by_key: dict[tuple[str, str, str], CatalogDefinition] = {}
        by_ref: dict[str, list[CatalogDefinition]] = {}
        for definition in definitions:
            key = (definition.resource_type, definition.id, definition.version)
            if key in by_key:
                raise CatalogConflictError(
                    "duplicate resource identity: "
                    f"{definition.resource_type}/{definition.id}@{definition.version}"
                )
            if not engine_compatible(engine_version, definition.compatibility.engine):
                raise CatalogResolutionError(
                    f"incompatible resource {definition.id}@{definition.version} "
                    f"for engine {engine_version}"
                )
            by_key[key] = definition.model_copy(deep=True)
            by_ref.setdefault(f"{definition.id}@{definition.version}", []).append(definition)
        self._definitions = by_key
        self._by_ref = by_ref
        self._validate_dependencies()
        canonical = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))
        self.content_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    def _dependency(self, reference: str) -> CatalogDefinition:
        parse_exact_resource_ref(reference)
        matches = self._by_ref.get(reference, [])
        if not matches:
            raise CatalogResolutionError(f"unknown dependency: {reference}")
        if len(matches) > 1:
            raise CatalogResolutionError(f"ambiguous dependency: {reference}")
        return matches[0]

    def _validate_dependencies(self) -> None:
        visiting: set[tuple[str, str, str]] = set()
        visited: set[tuple[str, str, str]] = set()

        def visit(definition: CatalogDefinition) -> None:
            key = (definition.resource_type, definition.id, definition.version)
            if key in visiting:
                raise CatalogResolutionError(f"cyclic resource dependency at {definition.id}")
            if key in visited:
                return
            visiting.add(key)
            for reference in definition.dependencies:
                visit(self._dependency(reference))
            visiting.remove(key)
            visited.add(key)

        for definition in self._definitions.values():
            visit(definition)

    def resolve(self, resource_type: ResourceType, reference: str) -> CatalogDefinition:
        resource_id, version = parse_exact_resource_ref(reference)
        try:
            return self._definitions[(resource_type, resource_id, version)].model_copy(deep=True)
        except KeyError as error:
            raise CatalogResolutionError(
                f"unknown resource: {resource_type}/{reference}"
            ) from error

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            definition.model_dump(mode="json")
            for _key, definition in sorted(self._definitions.items())
        )

    def instantiate(self, resource_type: ResourceType, reference: str) -> object:
        definition = self.resolve(resource_type, reference)
        if self._models is None:
            return deepcopy(definition)
        return self._models.create(resource_type, definition.model, definition)

    def validate_platform_component(
        self, platform_ref: str, component_type: ResourceType, component_ref: str
    ) -> bool:
        platform = self.resolve("platforms", platform_ref)
        component = self.resolve(component_type, component_ref)
        if not isinstance(platform, PlatformDefinition):
            raise CatalogResolutionError("platform reference does not resolve to a platform")
        compatible: tuple[str, ...]
        if isinstance(component, SensorDefinition):
            compatible = component.compatible_platform_types
        elif isinstance(component, WeaponDefinition):
            compatible = component.allowed_platform_types
        elif isinstance(component, (DynamicsDefinition, LoadoutDefinition)):
            compatible = component.compatible_platform_types
        else:
            raise CatalogResolutionError("unsupported platform component compatibility check")
        if platform.platform_type not in compatible:
            raise CatalogResolutionError(
                f"incompatible {component_type} {component_ref} for {platform.platform_type}"
            )
        if isinstance(component, LoadoutDefinition):
            if component.mass_kg > platform.payload_capacity_kg:
                raise CatalogResolutionError(
                    f"loadout mass exceeds payload capacity for {platform.platform_type}"
                )
            available_slots = list(platform.loadout_slots)
            for required_slot in component.slot_requirements:
                if required_slot not in available_slots:
                    raise CatalogResolutionError(
                        f"loadout requires unavailable slot {required_slot}"
                    )
                available_slots.remove(required_slot)
            for weapon_ref in component.weapon_refs:
                weapon = self.resolve("weapons", weapon_ref)
                if not isinstance(weapon, WeaponDefinition):
                    raise CatalogResolutionError("loadout weapon reference is not a weapon")
                if platform.platform_type not in weapon.allowed_platform_types:
                    raise CatalogResolutionError(
                        f"incompatible weapon {weapon_ref} in loadout for {platform.platform_type}"
                    )
        return True

    def resource_content_hash(self, resource_type: ResourceType, reference: str) -> str:
        definition = self.resolve(resource_type, reference)
        canonical = json.dumps(
            definition.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


__all__ = [
    "CatalogConflictError",
    "CatalogRepository",
    "CatalogResolutionError",
    "ModelRegistry",
    "engine_compatible",
    "parse_exact_resource_ref",
]

"""Read-only Catalog v2 and the sole trusted model-factory registry contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, StrictStr, computed_field, model_validator

from openmdbench.catalog.repository import engine_compatible
from openmdbench.schemas.core_v2 import CoreModelV2

ResourceTypeV2 = Literal[
    "maps",
    "platforms",
    "dynamics",
    "collision_shapes",
    "sensors",
    "communications",
    "weapons",
    "ammunition",
    "effects",
    "damage_models",
    "energy",
    "environments",
    "loadouts",
    "visualization_assets",
    "missions",
    "scoring",
    "trusted_model_plugins",
]

SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_.-]*$"
MODEL_REF_PATTERN = r"^[a-z][a-z0-9_.-]*@(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$"
ENGINE_PATTERN = (
    r"^(?:(?:>=|>|<=|<|==)\d+\.\d+\.\d+)"
    r"(?:,(?:>=|>|<=|<|==)\d+\.\d+\.\d+)*$"
)
RUNTIME_STATE_KEYS = frozenset(
    {"health", "ammo_remaining", "cooldown_remaining", "rng_state", "message_queue"}
)
RUNTIME_STATE_TERMS = re.compile(
    r"^(?:current_|pending_|rng_)|(?:_remaining|_queue|_rng_state)$|"
    r"^(?:sensor_mode|random_generator_state)$"
)
HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"


class CatalogResolutionErrorV2(ValueError):
    pass


class CatalogConflictErrorV2(ValueError):
    pass


class ModelBindingEvidenceErrorV2(CatalogResolutionErrorV2):
    pass


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _reject_runtime_state(value: object) -> None:
    if isinstance(value, Mapping):
        forbidden = RUNTIME_STATE_KEYS.intersection(value)
        patterned = {str(key) for key in value if RUNTIME_STATE_TERMS.search(str(key))}
        if forbidden or patterned:
            names = ", ".join(sorted({*forbidden, *patterned}))
            raise ValueError(f"session runtime mutable state is forbidden in Catalog: {names}")
        for item in value.values():
            _reject_runtime_state(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _reject_runtime_state(item)


class CatalogResourceV2(CoreModelV2):
    resource_type: ResourceTypeV2
    id: str = Field(pattern=IDENTIFIER_PATTERN)
    version: str = Field(pattern=SEMVER_PATTERN)
    engine_compatibility: str = Field(pattern=ENGINE_PATTERN)
    model_id: str = Field(pattern=MODEL_REF_PATTERN)
    dependencies: tuple[str, ...] = ()
    content: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_recomputed_fields(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            cleaned = dict(value)
            cleaned.pop("exact_ref", None)
            cleaned.pop("content_hash", None)
            return cleaned
        return value

    @model_validator(mode="after")
    def validate_resource(self) -> Self:
        _reject_runtime_state(self.content)
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("duplicate resource dependency")
        for reference in self.dependencies:
            if _parse_ref(reference) is None:
                raise ValueError("dependencies must use exact id@semantic-version references")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exact_ref(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def model_ref(self) -> str:
        return self.model_id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json", exclude={"content_hash", "exact_ref"}))


class ModelFactoryMetadataV2(CoreModelV2):
    model_id: str = Field(pattern=IDENTIFIER_PATTERN)
    version: str = Field(pattern=SEMVER_PATTERN)
    interface_version: Literal["2.0"]
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    units: dict[str, str] = Field(default_factory=dict)
    deterministic: bool
    thread_safe: bool
    process_safe: bool
    trusted: bool
    artifact_sha256: str = Field(pattern=HASH_PATTERN)
    resource_types: tuple[ResourceTypeV2, ...] = Field(min_length=1)
    field_units: dict[StrictStr, StrictStr] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_recomputed_fields(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            cleaned = dict(value)
            cleaned.pop("exact_ref", None)
            return cleaned
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exact_ref(self) -> str:
        return f"{self.model_id}@{self.version}"


class EntityCompositionV2(CoreModelV2):
    platform_ref: str = Field(pattern=MODEL_REF_PATTERN)
    dynamics_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    loadout_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    sensor_refs: tuple[str, ...] = ()
    communication_refs: tuple[str, ...] = ()
    energy_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    collision_shape_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    visualization_ref: str | None = Field(default=None, pattern=MODEL_REF_PATTERN)
    ammunition: dict[str, int] = Field(default_factory=dict)
    target_domains: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_composition_refs(self) -> Self:
        refs = (*self.sensor_refs, *self.communication_refs, *self.ammunition)
        if any(_parse_ref(reference) is None for reference in refs):
            raise ValueError("component references must use exact id@version")
        if any(count < 0 for count in self.ammunition.values()):
            raise ValueError("ammunition count cannot be negative")
        return self


FactoryV2 = Callable[[CatalogResourceV2], object]
RegistryEntryV2 = tuple[ModelFactoryMetadataV2, FactoryV2]
RuntimeMaterializerV2 = Callable[[object, ModelFactoryMetadataV2], object]


class ModelRegistryV2:
    """Trusted, immutable-after-freeze model metadata and factory authority."""

    interface_version: str
    _entries: Mapping[str, RegistryEntryV2]
    _frozen: bool
    _sealed: bool
    _catalog_definitions: tuple[CatalogResourceV2, ...]
    _runtime_materializers: dict[str, tuple[CatalogResourceV2, RuntimeMaterializerV2]]

    def __init__(self, *, interface_version: str) -> None:
        if interface_version != "2.0":
            raise CatalogResolutionErrorV2("unsupported model registry interface version")
        object.__setattr__(self, "interface_version", interface_version)
        object.__setattr__(self, "_entries", {})
        object.__setattr__(self, "_frozen", False)
        object.__setattr__(self, "_sealed", False)
        object.__setattr__(self, "_catalog_definitions", ())
        object.__setattr__(self, "_runtime_materializers", {})

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("frozen model registry attributes cannot be rebound")
        object.__setattr__(self, name, value)

    def register(self, metadata: ModelFactoryMetadataV2, factory: FactoryV2) -> None:
        if self._frozen:
            raise CatalogConflictErrorV2("model registry is frozen")
        if metadata.exact_ref in self._entries:
            raise CatalogConflictErrorV2(f"duplicate model factory: {metadata.exact_ref}")
        if not metadata.trusted:
            raise CatalogResolutionErrorV2("model factory must be trusted")
        if metadata.interface_version != self.interface_version:
            raise CatalogResolutionErrorV2("model factory interface is incompatible")
        if not metadata.deterministic:
            raise CatalogResolutionErrorV2("nondeterministic model factories are unsupported")
        if not metadata.thread_safe and not metadata.process_safe:
            raise CatalogResolutionErrorV2("model factory must be thread-safe or process-safe")
        if not isinstance(self._entries, dict):
            raise CatalogConflictErrorV2("frozen model registry cannot accept a factory")
        self._entries[metadata.exact_ref] = (metadata, factory)

    def freeze(self) -> None:
        object.__setattr__(self, "_entries", MappingProxyType(dict(self._entries)))
        object.__setattr__(self, "_frozen", True)
        object.__setattr__(self, "_sealed", True)

    @property
    def frozen(self) -> bool:
        return self._frozen

    def metadata(self, model_ref: str) -> ModelFactoryMetadataV2:
        try:
            return self._entries[model_ref][0]
        except KeyError as error:
            raise CatalogResolutionErrorV2(f"unknown trusted model factory: {model_ref}") from error

    def create(self, model_ref: str, definition: CatalogResourceV2 | None = None) -> Any:
        try:
            metadata, factory = self._entries[model_ref]
        except KeyError as error:
            raise CatalogResolutionErrorV2(f"unknown trusted model factory: {model_ref}") from error
        materializer_entry = self._runtime_materializers.get(model_ref)
        if definition is None and materializer_entry is not None:
            runtime_definition, materializer = materializer_entry
            factory_product = factory(runtime_definition)
            try:
                factory_product = deepcopy(factory_product)
            except TypeError:
                if isinstance(factory_product, BaseModel):
                    factory_product = type(factory_product).model_validate(
                        factory_product.model_dump(mode="json")
                    )
                else:
                    raise
            adapter = materializer(factory_product, metadata)
            if getattr(adapter, "model_ref", None) != model_ref:
                raise CatalogResolutionErrorV2("runtime adapter model identity mismatch")
            return adapter
        if definition is None:
            definition = next(
                (item for item in self._catalog_definitions if item.model_ref == model_ref),
                None,
            )
        if definition is None:
            raise CatalogResolutionErrorV2("model factory requires an exact bound definition")
        if definition.model_ref != model_ref:
            raise CatalogResolutionErrorV2("definition model reference mismatch")
        if metadata.input_schema != "catalog-resource@2.0":
            raise CatalogResolutionErrorV2("model factory input schema is incompatible")
        created = factory(definition)
        try:
            return deepcopy(created)
        except TypeError:
            if isinstance(created, BaseModel):
                return type(created).model_validate(created.model_dump(mode="json"))
            raise

    def materialize_runtime_adapter(
        self,
        model_ref: str,
        definition: CatalogResourceV2,
        materializer: RuntimeMaterializerV2,
    ) -> object:
        """Create and bind one immutable session adapter through the Registry boundary."""

        self.metadata(model_ref)
        if definition.model_ref != model_ref or not callable(materializer):
            raise CatalogResolutionErrorV2("runtime adapter materialization evidence is invalid")
        existing = self._runtime_materializers.get(model_ref)
        if existing is not None and existing[0] != definition:
            raise CatalogResolutionErrorV2("runtime materializer definition mismatch")
        self._runtime_materializers.setdefault(model_ref, (definition, materializer))
        return self.create(model_ref)

    def bind_catalog(self, definitions: Sequence[CatalogResourceV2]) -> None:
        """Give factories optional immutable resource-evidence scope for exact dispatch."""

        snapshot = tuple(definitions)
        object.__setattr__(self, "_catalog_definitions", snapshot)
        for _metadata, factory in self._entries.values():
            binder = getattr(factory, "bind_catalog", None)
            if callable(binder):
                binder(snapshot)

    def snapshot(self) -> tuple[ModelFactoryMetadataV2, ...]:
        return tuple(self._entries[key][0] for key in sorted(self._entries))

    @property
    def content_hash(self) -> str:
        return _canonical_hash([item.model_dump(mode="json") for item in self.snapshot()])

    @property
    def snapshot_hash(self) -> str:
        """Canonical immutable registry snapshot identity."""

        return self.content_hash


def _parse_ref(reference: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"(?P<id>[a-z][a-z0-9_.-]*)@(?P<version>(?:0|[1-9]\d*)\."
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))",
        reference,
    )
    return None if match is None else (match.group("id"), match.group("version"))


class CatalogV2:
    """Stable definition store; every executable model is registry-authorized."""

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("Catalog attributes cannot be rebound")
        object.__setattr__(self, name, value)

    def __init__(
        self,
        resources: Iterable[CatalogResourceV2],
        *,
        engine_version: str,
        model_registry: ModelRegistryV2,
    ) -> None:
        if re.fullmatch(SEMVER_PATTERN, engine_version) is None:
            raise ValueError("engine_version must be semantic version")
        object.__setattr__(self, "_sealed", False)
        self.engine_version = engine_version
        self.model_registry = model_registry
        if not model_registry.frozen:
            raise CatalogResolutionErrorV2("model registry must be frozen before Catalog build")
        definitions: dict[tuple[str, str, str], CatalogResourceV2] = {}
        references: dict[str, CatalogResourceV2] = {}
        for supplied in resources:
            resource = CatalogResourceV2.model_validate(supplied.model_dump())
            identity = (resource.resource_type, resource.id, resource.version)
            if identity in definitions or resource.exact_ref in references:
                raise CatalogConflictErrorV2(f"duplicate resource identity: {resource.exact_ref}")
            if not engine_compatible(engine_version, resource.engine_compatibility):
                raise CatalogResolutionErrorV2(
                    f"resource {resource.exact_ref} is incompatible with engine {engine_version}"
                )
            model_registry.metadata(resource.model_ref)
            definitions[identity] = resource
            references[resource.exact_ref] = resource
        self._definitions: Mapping[tuple[str, str, str], CatalogResourceV2] = MappingProxyType(
            definitions
        )
        self._references: Mapping[str, CatalogResourceV2] = MappingProxyType(references)
        self._validate_dependencies()
        self._validate_typed_resource_chains()
        model_registry.bind_catalog(self.snapshot())
        self.content_hash = _canonical_hash(
            {
                "resources": [item.model_dump(mode="json") for item in self.snapshot()],
                "model_registry_hash": model_registry.content_hash,
            }
        )
        self._validate_model_contracts()
        object.__setattr__(self, "_sealed", True)

    def _validate_typed_resource_chains(self) -> None:
        for resource in self._definitions.values():
            content = resource.content
            if resource.resource_type == "platforms":
                platform_type = str(content.get("platform_type", ""))
                domain = str(content.get("domain", ""))
                energy_ref = content.get("energy_ref")
                if isinstance(energy_ref, str):
                    energy = self.resolve("energy", energy_ref)
                    if platform_type not in self._strings(
                        energy.content, "compatible_platform_types"
                    ):
                        raise CatalogResolutionErrorV2("energy is incompatible with platform")
                for resource_type, field, compatibility_field in (
                    ("collision_shapes", "collision_shape_ref", "compatible_domains"),
                    ("visualization_assets", "visualization_ref", "compatible_domains"),
                ):
                    reference = content.get(field)
                    if not isinstance(reference, str):
                        continue
                    target = self.resolve(resource_type, reference)
                    compatible = self._strings(target.content, compatibility_field)
                    if compatible and domain not in compatible:
                        label = "collision" if resource_type == "collision_shapes" else "visual"
                        raise CatalogResolutionErrorV2(
                            f"{label} resource is incompatible with platform domain"
                        )
            elif resource.resource_type == "weapons":
                effect_ref = content.get("effect_ref")
                if isinstance(effect_ref, str):
                    self.resolve("effects", effect_ref)
            elif resource.resource_type == "ammunition":
                weapon_ref = content.get("weapon_ref")
                if isinstance(weapon_ref, str):
                    self.resolve("weapons", weapon_ref)
            elif resource.resource_type == "effects":
                damage_ref = content.get("damage_model_ref")
                if not isinstance(damage_ref, str):
                    continue
                try:
                    damage = self.resolve("damage_models", damage_ref)
                except CatalogResolutionErrorV2 as error:
                    raise CatalogResolutionErrorV2(
                        f"effect damage model is missing or incompatible: {damage_ref}"
                    ) from error
                effect_type = content.get("effect_type")
                accepted = self._strings(damage.content, "effect_types")
                if accepted and effect_type not in accepted:
                    raise CatalogResolutionErrorV2("effect type is incompatible with damage model")

    def _validate_model_contracts(self) -> None:
        allowed_units = {
            "m",
            "s",
            "m/s",
            "m/s^2",
            "deg",
            "deg/s",
            "kg",
            "J",
            "W",
            "Hz",
            "bps",
            "1",
        }
        for resource in self._definitions.values():
            metadata = self.model_registry.metadata(resource.model_ref)
            if resource.resource_type not in metadata.resource_types:
                raise CatalogResolutionErrorV2("model resource type is incompatible")
            if metadata.input_schema != "catalog-resource@2.0":
                raise CatalogResolutionErrorV2("model input schema is incompatible")
            if metadata.output_schema != "runtime-component@2.0":
                raise CatalogResolutionErrorV2("model output schema is incompatible")
            if any(unit not in allowed_units for unit in metadata.units.values()):
                raise CatalogResolutionErrorV2("model unit contract is incompatible")
            suffix_units = {
                "_m": "m",
                "_s": "s",
                "_mps": "m/s",
                "_kg": "kg",
                "_j": "J",
                "_hz": "Hz",
                "_bps": "bps",
            }
            for field, unit in metadata.field_units.items():
                expected = next(
                    (value for suffix, value in suffix_units.items() if field.endswith(suffix)),
                    None,
                )
                if expected is not None and unit != expected:
                    raise CatalogResolutionErrorV2(
                        f"model field unit is incompatible for {field}: expected {expected}"
                    )

    def _validate_dependencies(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(resource: CatalogResourceV2) -> None:
            if resource.exact_ref in visiting:
                raise CatalogResolutionErrorV2(
                    f"cyclic resource dependency at {resource.exact_ref}"
                )
            if resource.exact_ref in visited:
                return
            visiting.add(resource.exact_ref)
            for dependency in resource.dependencies:
                try:
                    target = self._references[dependency]
                except KeyError as error:
                    raise CatalogResolutionErrorV2(
                        f"missing or unknown dependency: {dependency}"
                    ) from error
                visit(target)
            visiting.remove(resource.exact_ref)
            visited.add(resource.exact_ref)

        for resource in self._definitions.values():
            visit(resource)

    def snapshot(self) -> tuple[CatalogResourceV2, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def resolve(self, resource_type: str, reference: str) -> CatalogResourceV2:
        parsed = _parse_ref(reference)
        if parsed is None:
            raise CatalogResolutionErrorV2("resource reference must use exact id@version")
        resource_id, version = parsed
        try:
            return self._definitions[(resource_type, resource_id, version)]
        except KeyError as error:
            raise CatalogResolutionErrorV2(
                f"unknown resource: {resource_type}/{reference}"
            ) from error

    def instantiate(self, resource_type: str, reference: str) -> Any:
        definition = self.resolve(resource_type, reference)
        return self.model_registry.create(definition.model_ref, definition)

    @staticmethod
    def _strings(content: Mapping[str, Any], key: str) -> tuple[str, ...]:
        value = content.get(key, ())
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise CatalogResolutionErrorV2(f"{key} must be a sequence")
        return tuple(str(item) for item in value)

    def validate_entity_composition(self, composition: EntityCompositionV2) -> bool:
        platform = self.resolve("platforms", composition.platform_ref)
        platform_type = str(platform.content.get("platform_type", ""))
        mobile = platform.content.get("mobile")

        if composition.dynamics_ref is not None:
            dynamics = self.resolve("dynamics", composition.dynamics_ref)
            if mobile is not True:
                raise CatalogResolutionErrorV2("static/fixed platform cannot bind dynamics")
            if composition.dynamics_ref not in self._strings(platform.content, "allowed_dynamics"):
                raise CatalogResolutionErrorV2("incompatible dynamics for platform")
            if platform_type not in self._strings(dynamics.content, "compatible_platform_types"):
                raise CatalogResolutionErrorV2("incompatible platform type for dynamics")

        if composition.loadout_ref is None:
            return True
        loadout = self.resolve("loadouts", composition.loadout_ref)
        if platform_type not in self._strings(loadout.content, "compatible_platform_types"):
            raise CatalogResolutionErrorV2("incompatible loadout for platform type")
        payload_capacity = float(platform.content.get("payload_capacity_kg", 0.0))
        if float(loadout.content.get("mass_kg", 0.0)) > payload_capacity:
            raise CatalogResolutionErrorV2("loadout exceeds platform payload capacity")
        available = Counter(self._strings(platform.content, "component_slots"))
        required = Counter(self._strings(loadout.content, "required_slots"))
        if any(required[name] > available[name] for name in required):
            raise CatalogResolutionErrorV2("loadout requires incompatible or unavailable slot")
        requested_targets = set(composition.target_domains)
        for weapon_ref in self._strings(loadout.content, "weapon_refs"):
            weapon = self.resolve("weapons", weapon_ref)
            if platform_type not in self._strings(weapon.content, "allowed_platform_types"):
                raise CatalogResolutionErrorV2("incompatible weapon for platform")
            supported_targets = set(self._strings(weapon.content, "target_domains"))
            if not requested_targets.issubset(supported_targets):
                raise CatalogResolutionErrorV2("incompatible weapon target domain")
        return True

    def validate_component_compatibility(
        self,
        *,
        platform_ref: str,
        sensor_refs: tuple[str, ...] = (),
        communication_refs: tuple[str, ...] = (),
        energy_ref: str | None = None,
        collision_shape_ref: str | None = None,
        ammunition_refs: tuple[str, ...] = (),
        visualization_ref: str | None = None,
    ) -> bool:
        platform = self.resolve("platforms", platform_ref)
        platform_type = str(platform.content.get("platform_type", ""))
        slots = Counter(self._strings(platform.content, "component_slots"))
        requested_slots: Counter[str] = Counter()
        for resource_type, component_references in (
            ("sensors", sensor_refs),
            ("communications", communication_refs),
        ):
            for reference in component_references:
                component = self.resolve(resource_type, reference)
                if platform_type not in self._strings(
                    component.content, "compatible_platform_types"
                ):
                    raise CatalogResolutionErrorV2(
                        f"incompatible {resource_type} component for platform"
                    )
                slot = component.content.get("slot_type")
                if not isinstance(slot, str):
                    raise CatalogResolutionErrorV2("component slot_type is missing")
                requested_slots[slot] += 1
        if any(requested_slots[name] > slots[name] for name in requested_slots):
            raise CatalogResolutionErrorV2("component requires unavailable platform slot")
        bound_references = (
            ("energy", energy_ref, "energy_ref"),
            ("collision_shapes", collision_shape_ref, "collision_shape_ref"),
            ("visualization_assets", visualization_ref, "visualization_ref"),
        )
        for resource_type, bound_reference, field in bound_references:
            if bound_reference is None:
                continue
            self.resolve(resource_type, bound_reference)
            if platform.content.get(field) != bound_reference:
                raise CatalogResolutionErrorV2(f"incompatible platform {field}")
        for reference in ammunition_refs:
            ammunition = self.resolve("ammunition", reference)
            weapon_ref = ammunition.content.get("weapon_ref")
            if not isinstance(weapon_ref, str):
                raise CatalogResolutionErrorV2("ammunition weapon_ref is missing")
            weapon = self.resolve("weapons", weapon_ref)
            if platform_type not in self._strings(weapon.content, "allowed_platform_types"):
                raise CatalogResolutionErrorV2("incompatible ammunition weapon for platform")
        return True

    def validate_full_composition(self, composition: EntityCompositionV2) -> bool:
        """Atomically validate every resource participating in one entity instance."""
        platform = self.resolve("platforms", composition.platform_ref)
        platform_type = str(platform.content.get("platform_type", ""))
        domain = str(platform.content.get("domain", ""))
        available_slots = Counter(self._strings(platform.content, "component_slots"))
        required_slots: Counter[str] = Counter()

        if composition.dynamics_ref is not None:
            dynamics = self.resolve("dynamics", composition.dynamics_ref)
            if (
                platform.content.get("mobile") is not True
                and dynamics.content.get("mobile") is not False
            ):
                raise CatalogResolutionErrorV2("static/fixed platform cannot bind dynamics")
            if composition.dynamics_ref not in self._strings(
                platform.content, "allowed_dynamics"
            ) or platform_type not in self._strings(dynamics.content, "compatible_platform_types"):
                raise CatalogResolutionErrorV2("dynamics is incompatible with platform")

        loadout: CatalogResourceV2 | None = None
        weapon_refs: set[str] = set()
        ammunition_refs: set[str] = set()
        payload_mass = 0.0
        if composition.loadout_ref is not None:
            loadout = self.resolve("loadouts", composition.loadout_ref)
            if platform_type not in self._strings(loadout.content, "compatible_platform_types"):
                raise CatalogResolutionErrorV2("loadout is incompatible with platform")
            required_slots.update(self._strings(loadout.content, "required_slots"))
            weapon_refs = set(self._strings(loadout.content, "weapon_refs"))
            ammunition_refs = set(self._strings(loadout.content, "ammunition_refs"))
            legacy_ammunition = loadout.content.get("ammunition", {})
            if isinstance(legacy_ammunition, Mapping):
                ammunition_refs.update(str(reference) for reference in legacy_ammunition)
            payload_mass = float(loadout.content.get("mass_kg", 0.0))

        for resource_type, references in (
            ("sensors", composition.sensor_refs),
            ("communications", composition.communication_refs),
        ):
            for reference in references:
                component = self.resolve(resource_type, reference)
                if platform_type not in self._strings(
                    component.content, "compatible_platform_types"
                ):
                    raise CatalogResolutionErrorV2(f"{resource_type} is incompatible with platform")
                slot = component.content.get("slot_type")
                if not isinstance(slot, str):
                    raise CatalogResolutionErrorV2(f"{resource_type} slot is missing")
                required_slots[slot] += 1

        if any(required_slots[name] > available_slots[name] for name in required_slots):
            raise CatalogResolutionErrorV2("combined component slot capacity exceeded")

        for weapon_ref in sorted(weapon_refs):
            weapon = self.resolve("weapons", weapon_ref)
            if platform_type not in self._strings(weapon.content, "allowed_platform_types"):
                raise CatalogResolutionErrorV2("weapon is incompatible with platform")
            if not set(composition.target_domains).issubset(
                self._strings(weapon.content, "target_domains")
            ):
                raise CatalogResolutionErrorV2("weapon target domain is incompatible")
            effect_ref = weapon.content.get("effect_ref")
            if not isinstance(effect_ref, str):
                raise CatalogResolutionErrorV2("weapon effect damage chain is invalid")
            try:
                effect = self.resolve("effects", effect_ref)
                damage_ref = effect.content.get("damage_model_ref")
                if not isinstance(damage_ref, str):
                    raise CatalogResolutionErrorV2("weapon effect damage chain is invalid")
                self.resolve("damage_models", damage_ref)
            except CatalogResolutionErrorV2 as error:
                raise CatalogResolutionErrorV2("weapon effect damage chain is invalid") from error

        for reference, count in composition.ammunition.items():
            if loadout is None or reference not in ammunition_refs:
                raise CatalogResolutionErrorV2("ammunition is absent from selected loadout")
            ammunition = self.resolve("ammunition", reference)
            ammunition_weapon_ref = ammunition.content.get("weapon_ref")
            if (
                not isinstance(ammunition_weapon_ref, str)
                or ammunition_weapon_ref not in weapon_refs
            ):
                raise CatalogResolutionErrorV2("ammunition weapon is absent from loadout")
            payload_mass += float(ammunition.content.get("mass_per_round_kg", 0.0)) * count

        if payload_mass > float(platform.content.get("payload_capacity_kg", 0.0)):
            raise CatalogResolutionErrorV2("combined payload capacity exceeded")

        bound_resources: tuple[tuple[ResourceTypeV2, str | None, str], ...] = (
            ("energy", composition.energy_ref, "energy_ref"),
            ("collision_shapes", composition.collision_shape_ref, "collision_shape_ref"),
            ("visualization_assets", composition.visualization_ref, "visualization_ref"),
        )
        for resource_type, bound_reference, platform_field in bound_resources:
            if bound_reference is None:
                continue
            resource = self.resolve(resource_type, bound_reference)
            if platform.content.get(platform_field) != bound_reference:
                raise CatalogResolutionErrorV2(
                    f"{resource_type} reference is incompatible with platform"
                )
            compatible_domains = self._strings(resource.content, "compatible_domains")
            if compatible_domains and domain not in compatible_domains:
                raise CatalogResolutionErrorV2(
                    f"{resource_type} is incompatible with platform domain"
                )
            compatible_platforms = self._strings(resource.content, "compatible_platform_types")
            if compatible_platforms and platform_type not in compatible_platforms:
                raise CatalogResolutionErrorV2(
                    f"{resource_type} is incompatible with platform type"
                )
        return True


def legacy_composition_model_registry_v2() -> ModelRegistryV2:
    """Registry authority for the reviewed data-only models used by the v1 importer."""
    registry = ModelRegistryV2(interface_version="2.0")
    model_resource_types: dict[str, tuple[ResourceTypeV2, ...]] = {
        "platform_asset_v1": ("platforms",),
        "point_mass_2d_v1": ("dynamics",),
        "point_mass_3d_v1": ("dynamics",),
        "static_v1": ("dynamics",),
        "fixed_loadout_v1": ("loadouts",),
        "probability_sensor_v1": ("sensors",),
        "probability_instant_v1": ("weapons",),
        "fractional_damage_v1": ("effects",),
        "delayed_network_v1": ("communications",),
        "weighted_scoring_v1": ("scoring",),
        "map_asset_v1": ("maps",),
        "normalized_energy_v1": ("energy",),
        "weather_profile_v1": ("environments",),
        "area_denial_v1": ("missions",),
        "vector_profile_v1": ("visualization_assets",),
        "builtin_plugin_v1": ("trusted_model_plugins",),
        "legacy_ammunition_v1": ("ammunition",),
        "legacy_fractional_damage_v1": ("damage_models",),
    }
    for model_id, resource_types in model_resource_types.items():
        registry.register(
            ModelFactoryMetadataV2(
                schema_version="2.0",
                model_id=model_id,
                version="2.0.0",
                interface_version="2.0",
                input_schema="catalog-resource@2.0",
                output_schema="runtime-component@2.0",
                units={},
                deterministic=True,
                thread_safe=True,
                process_safe=True,
                trusted=True,
                artifact_sha256=_canonical_hash({"builtin_model": model_id}),
                resource_types=resource_types,
                field_units={},
            ),
            lambda definition: definition,
        )
    registry.freeze()
    return registry


__all__ = [
    "CatalogConflictErrorV2",
    "CatalogResolutionErrorV2",
    "CatalogResourceV2",
    "CatalogV2",
    "EntityCompositionV2",
    "ModelFactoryMetadataV2",
    "ModelRegistryV2",
    "legacy_composition_model_registry_v2",
]

"""Unified immutable resource catalog public API."""

from openmdbench.catalog.builtin_models import (
    FractionalDamageModel,
    ProbabilityInstantWeaponModel,
    builtin_model_registry,
)
from openmdbench.catalog.models import (
    CommunicationDefinition,
    CommunicationLinkDefinition,
    DynamicsDefinition,
    EffectDefinition,
    EngineCompatibility,
    LoadoutDefinition,
    PlatformDefinition,
    ResourceDefinition,
    ResourceType,
    ScoringDefinition,
    SensorDefinition,
    WeaponDefinition,
)
from openmdbench.catalog.repository import (
    CatalogConflictError,
    CatalogRepository,
    CatalogResolutionError,
    ModelRegistry,
    engine_compatible,
    parse_exact_resource_ref,
)

__all__ = [
    "CatalogConflictError",
    "CommunicationDefinition",
    "CommunicationLinkDefinition",
    "CatalogRepository",
    "CatalogResolutionError",
    "EffectDefinition",
    "DynamicsDefinition",
    "EngineCompatibility",
    "ModelRegistry",
    "LoadoutDefinition",
    "PlatformDefinition",
    "ResourceDefinition",
    "ResourceType",
    "ScoringDefinition",
    "SensorDefinition",
    "WeaponDefinition",
    "FractionalDamageModel",
    "FormalCatalogErrorV2",
    "ProbabilityInstantWeaponModel",
    "builtin_model_registry",
    "engine_compatible",
    "parse_exact_resource_ref",
    "md_ad_002_catalog",
    "md_ad_002_catalog_definitions",
    "load_catalog_bundle_v2",
    "load_md_ad_002_catalog_v2",
]


def __getattr__(name: str) -> object:
    """Lazily expose scenario-facing helpers without cycling into native models."""

    if name in {"FormalCatalogErrorV2", "load_catalog_bundle_v2", "load_md_ad_002_catalog_v2"}:
        from openmdbench.catalog import formal_v2

        return getattr(formal_v2, name)
    if name in {"md_ad_002_catalog", "md_ad_002_catalog_definitions"}:
        from openmdbench.catalog import legacy_adapters

        return getattr(legacy_adapters, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

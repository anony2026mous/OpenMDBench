"""Load reviewed, data-only Catalog v2 resource bundles for formal scenarios."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml

from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
    ResourceTypeV2,
)
from openmdbench.dynamics.native_v2 import register_native_dynamics_models_v2

_ENGINE_VERSION = "2.0.0"
_BUNDLE_ROOT = Path(__file__).resolve().parents[2] / "catalog" / "v2"
_GENERIC_MODEL_REF = "models.formal-data@2.0.0"
_GENERIC_RESOURCE_TYPES: tuple[ResourceTypeV2, ...] = (
    "maps",
    "platforms",
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
)


class FormalCatalogErrorV2(ValueError):
    """Stable failure raised before untrusted bundle data reaches CatalogV2."""


def _registry() -> ModelRegistryV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.formal-data",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256=(
                "sha256:64f522f226c124307f998e6a915d6f61c6e36f7939497137a774013b953c9ab8"
            ),
            resource_types=_GENERIC_RESOURCE_TYPES,
            field_units={},
        ),
        lambda definition: definition,
    )
    register_native_dynamics_models_v2(registry)
    registry.freeze()
    return registry


def load_catalog_bundle_v2(path: Path) -> CatalogV2:
    """Load one finite YAML list containing strict CatalogResourceV2 mappings."""

    resolved = path.resolve()
    root = _BUNDLE_ROOT.resolve()
    if resolved.parent != root or resolved.suffix not in {".yaml", ".yml"}:
        raise FormalCatalogErrorV2("catalog bundle path is outside the approved root")
    if resolved.is_symlink() or not resolved.is_file():
        raise FormalCatalogErrorV2("catalog bundle must be a regular file")
    raw = resolved.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise FormalCatalogErrorV2("catalog bundle exceeds the 2 MiB limit")
    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise FormalCatalogErrorV2("catalog bundle is invalid YAML") from error
    if not isinstance(document, Mapping) or set(document) != {"schema_version", "resources"}:
        raise FormalCatalogErrorV2("catalog bundle fields are invalid")
    if document["schema_version"] != "catalog-bundle@2.0":
        raise FormalCatalogErrorV2("catalog bundle schema version is unsupported")
    values = document["resources"]
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise FormalCatalogErrorV2("catalog resources must be a list")
    if len(values) > 512:
        raise FormalCatalogErrorV2("catalog resource quota exceeded")
    resources = tuple(
        CatalogResourceV2.model_validate(cast(Mapping[str, Any], value)) for value in values
    )
    return CatalogV2(resources, engine_version=_ENGINE_VERSION, model_registry=_registry())


def load_md_ad_002_catalog_v2() -> CatalogV2:
    """Return a fresh immutable Catalog/Registry pair used by all AD2 V2 packages."""

    return load_catalog_bundle_v2(_BUNDLE_ROOT / "md_ad_002.yaml")


__all__ = [
    "FormalCatalogErrorV2",
    "load_catalog_bundle_v2",
    "load_md_ad_002_catalog_v2",
]

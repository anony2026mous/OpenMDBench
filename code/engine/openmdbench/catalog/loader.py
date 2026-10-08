"""Safe YAML loader for package-local catalog definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml
from pydantic import ValidationError

from openmdbench.catalog.models import (
    CatalogDefinition,
    CommunicationDefinition,
    DynamicsDefinition,
    EffectDefinition,
    LoadoutDefinition,
    PlatformDefinition,
    ResourceDefinition,
    ScoringDefinition,
    SensorDefinition,
    WeaponDefinition,
)

_MODELS: dict[str, type[ResourceDefinition]] = {
    "platforms": PlatformDefinition,
    "dynamics": DynamicsDefinition,
    "loadouts": LoadoutDefinition,
    "sensors": SensorDefinition,
    "weapons": WeaponDefinition,
    "effects": EffectDefinition,
    "communications": CommunicationDefinition,
    "scoring": ScoringDefinition,
}


class CatalogLoadError(ValueError):
    """Invalid, unsupported or executable-looking catalog input."""


def load_catalog_documents(documents: Mapping[str, bytes]) -> tuple[CatalogDefinition, ...]:
    definitions: list[CatalogDefinition] = []
    for path, content in sorted(documents.items()):
        try:
            raw: Any = yaml.safe_load(content)
        except yaml.YAMLError as error:
            raise CatalogLoadError(f"malformed catalog YAML: {path}") from error
        if not isinstance(raw, dict) or raw.get("schema_version") != "catalog@1.0":
            raise CatalogLoadError(f"catalog {path} must use schema_version catalog@1.0")
        items = raw.get("resources")
        if not isinstance(items, list):
            raise CatalogLoadError(f"catalog {path} resources must be a list")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise CatalogLoadError(f"catalog {path} resource {index} must be an object")
            resource_type = item.get("resource_type")
            model = _MODELS.get(str(resource_type), ResourceDefinition)
            try:
                definitions.append(model.model_validate(item))
            except ValidationError as error:
                first = error.errors()[0]
                field = ".".join(str(part) for part in first.get("loc", ()))
                raise CatalogLoadError(
                    f"catalog {path} resource {index}.{field}: {first.get('msg')}"
                ) from error
    return tuple(definitions)


__all__ = ["CatalogLoadError", "load_catalog_documents"]

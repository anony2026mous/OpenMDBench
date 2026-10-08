"""Explicit quarantine for pre-v2 Catalog loading and formal scenario adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openmdbench.catalog.legacy_adapters import md_ad_002_catalog
from openmdbench.catalog.loader import load_catalog_documents
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    legacy_composition_model_registry_v2,
)

_LEGACY_RESOURCE_BASE_FIELDS = {
    "schema_version",
    "resource_type",
    "id",
    "version",
    "display_name",
    "model",
    "compatibility",
    "dependencies",
    "metadata_json",
}


def load_legacy_composition_catalog_v2(documents: Mapping[str, bytes]) -> CatalogV2:
    """Translate a legacy data package at the importer boundary, then return only v2."""
    definitions = load_catalog_documents(documents)
    resources: list[CatalogResourceV2] = []
    platform_types = sorted(
        {
            str(definition.model_dump(mode="json").get("platform_type"))
            for definition in definitions
            if definition.resource_type == "platforms"
        }
    )
    sensor_slot_counts = {
        platform_type: sum(
            platform_type
            in tuple(definition.model_dump(mode="json").get("compatible_platform_types", ()))
            for definition in definitions
            if definition.resource_type == "sensors"
        )
        for platform_type in platform_types
    }
    for definition in definitions:
        payload = definition.model_dump(mode="json")
        content = {
            key: value for key, value in payload.items() if key not in _LEGACY_RESOURCE_BASE_FIELDS
        }
        if definition.resource_type == "platforms":
            content["component_slots"] = content.get("loadout_slots", ())
            content["mobile"] = content.get("platform_type") != "shore_radar"
            content["component_slots"] = (
                *content["component_slots"],
                *("legacy_sensor",) * sensor_slot_counts.get(str(content.get("platform_type")), 0),
                "legacy_communication",
            )
            content["energy_ref"] = "ad2_energy@1.0.0"
            # Legacy catalogs treated this as a presentation hint and did not require
            # the referenced asset to be present in the same catalog package.
            content.pop("visualization_ref", None)
        elif definition.resource_type == "loadouts":
            content["required_slots"] = content.get("slot_requirements", ())
        elif definition.resource_type == "dynamics":
            content["mobile"] = definition.model != "static_v1"
        elif definition.resource_type == "sensors":
            content["slot_type"] = "legacy_sensor"
        elif definition.resource_type == "communications":
            content["slot_type"] = "legacy_communication"
            content["compatible_platform_types"] = tuple(platform_types)
        elif definition.resource_type == "energy":
            content["compatible_platform_types"] = tuple(platform_types)
        resources.append(
            CatalogResourceV2(
                schema_version="2.0",
                resource_type=definition.resource_type,
                id=definition.id,
                version=definition.version,
                engine_compatibility=definition.compatibility.engine,
                model_id=f"{definition.model}@2.0.0",
                dependencies=definition.dependencies,
                content=content,
            )
        )
    by_exact_ref = {resource.exact_ref: resource for resource in resources}
    normalized: list[CatalogResourceV2] = []
    synthesized: dict[str, CatalogResourceV2] = {}
    for resource in resources:
        content = dict(resource.content)
        dependencies = list(resource.dependencies)
        if resource.resource_type == "effects" and not isinstance(
            content.get("damage_model_ref"), str
        ):
            damage_ref = f"{resource.id}.damage@{resource.version}"
            content["damage_model_ref"] = damage_ref
            content.setdefault("effect_type", "legacy_fractional")
            dependencies.append(damage_ref)
            synthesized[damage_ref] = CatalogResourceV2(
                schema_version="2.0",
                resource_type="damage_models",
                id=f"{resource.id}.damage",
                version=resource.version,
                engine_compatibility=resource.engine_compatibility,
                model_id="legacy_fractional_damage_v1@2.0.0",
                content={"effect_types": (content["effect_type"],)},
            )
        if resource.resource_type == "loadouts" and not content.get("ammunition_refs"):
            ammunition_refs: list[str] = []
            for weapon_ref in sorted(content.get("weapon_refs", ())):
                weapon = by_exact_ref.get(str(weapon_ref))
                if weapon is None or weapon.resource_type != "weapons":
                    continue
                ammunition_ref = f"{weapon.id}.ammunition@{weapon.version}"
                ammunition_refs.append(ammunition_ref)
                synthesized[ammunition_ref] = CatalogResourceV2(
                    schema_version="2.0",
                    resource_type="ammunition",
                    id=f"{weapon.id}.ammunition",
                    version=weapon.version,
                    engine_compatibility=weapon.engine_compatibility,
                    model_id="legacy_ammunition_v1@2.0.0",
                    dependencies=(weapon.exact_ref,),
                    content={"weapon_ref": weapon.exact_ref, "mass_per_round_kg": 0.0},
                )
            content["ammunition_refs"] = tuple(ammunition_refs)
            dependencies.extend(ammunition_refs)
        normalized.append(
            resource.model_copy(update={"content": content, "dependencies": tuple(dependencies)})
        )
    normalized.extend(synthesized[key] for key in sorted(synthesized))
    return CatalogV2(
        normalized,
        engine_version="0.1.0",
        model_registry=legacy_composition_model_registry_v2(),
    )


def legacy_md_ad_catalog(config: Any) -> Any:
    """Keep the formal legacy adapter out of the generic compiler authority imports."""
    return md_ad_002_catalog(config)


__all__ = ["legacy_md_ad_catalog", "load_legacy_composition_catalog_v2"]

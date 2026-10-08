"""Data-driven discovery and compilation of installed formal V2 scenario packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from openmdbench.catalog.formal_v2 import load_catalog_bundle_v2
from openmdbench.catalog.v2 import CatalogV2
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)

_FORMAL_ROOT = Path(__file__).resolve().parents[2] / "scenarios" / "formal"
_CATALOG_ROOT = Path(__file__).resolve().parents[2] / "catalog" / "v2"


@dataclass(frozen=True, slots=True)
class FormalScenarioEntryV2:
    public_id: str
    package: str
    catalog_bundle: str

    @property
    def package_root(self) -> Path:
        return _FORMAL_ROOT / self.package

    @property
    def catalog_path(self) -> Path:
        return _CATALOG_ROOT / f"{self.catalog_bundle}.yaml"


def formal_scenario_registry_v2() -> MappingProxyType[str, FormalScenarioEntryV2]:
    path = _FORMAL_ROOT / "registry.yaml"
    if path.is_symlink() or not path.is_file():
        raise ValueError("formal scenario registry is unavailable")
    payload: Any = yaml.safe_load(path.read_bytes())
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "scenarios"}:
        raise ValueError("formal scenario registry fields are invalid")
    if payload["schema_version"] != "formal-scenario-registry@2.0":
        raise ValueError("formal scenario registry version is unsupported")
    entries: dict[str, FormalScenarioEntryV2] = {}
    for raw in payload["scenarios"]:
        if not isinstance(raw, dict) or set(raw) != {
            "public_id",
            "package",
            "catalog_bundle",
        }:
            raise ValueError("formal scenario entry fields are invalid")
        entry = FormalScenarioEntryV2(**raw)
        if (
            not entry.public_id
            or not entry.package.isidentifier()
            or not entry.catalog_bundle.isidentifier()
            or entry.public_id in entries
        ):
            raise ValueError("formal scenario entry identity is invalid")
        entries[entry.public_id] = entry
    return MappingProxyType(dict(sorted(entries.items())))


def load_formal_scenario_v2(public_id: str) -> tuple[ScenarioPackageV2, CatalogV2]:
    try:
        entry = formal_scenario_registry_v2()[public_id]
    except KeyError as error:
        raise ValueError(f"unknown formal V2 scenario: {public_id}") from error
    package = ScenarioPackageV2.from_directory(entry.package_root)
    catalog = load_catalog_bundle_v2(entry.catalog_path)
    return package, catalog


def compile_formal_scenario_v2(public_id: str) -> tuple[ResolvedScenarioV2, CatalogV2]:
    package, catalog = load_formal_scenario_v2(public_id)
    resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
    entity_by_id = {entity.id: entity for entity in resolved.entities}
    for event in resolved.events:
        if event.event_type == "spawn":
            entity_by_id[event.payload.entity.id] = event.payload.entity
    for slot in resolved.controller_slots:
        endpoint = slot.values.get("controller_endpoint_ref")
        entity = entity_by_id.get(endpoint) if isinstance(endpoint, str) else None
        if (
            not isinstance(endpoint, str)
            or entity is None
            or entity.faction_id != slot.faction_id
            or not getattr(getattr(entity, "composition", None), "communication_refs", ())
        ):
            raise CompilerErrorV2(
                "scenario.controller_endpoint_required",
                file="controller_slots.yaml",
                path=("controller_slots", slot.id, "controller_endpoint_ref"),
                value=endpoint,
                reason=(
                    "formal V2 controllers require an explicit same-faction communication endpoint"
                ),
                suggestion=(
                    "declare controller_endpoint_ref; do not infer it from the controller claim"
                ),
            )
    return resolved, catalog


__all__ = [
    "FormalScenarioEntryV2",
    "compile_formal_scenario_v2",
    "formal_scenario_registry_v2",
    "load_formal_scenario_v2",
]

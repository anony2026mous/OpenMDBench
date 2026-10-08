"""Small data-only scenario SDK used by CLI and third-party tooling."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import yaml

from openmdbench.catalog.v2 import CatalogV2
from openmdbench.scenarios.declarative_v2 import (
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)

_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic": {
        "schema_version": "2.0",
        "scenario_id": "scenario.new",
        "factions": [{"schema_version": "2.0", "id": "faction.one"}],
        "relationships": [],
        "entities": [],
        "formations": [],
        "world": {"schema_version": "2.0", "coordinate_system": "local_m", "zones": []},
        "events": [],
        "mission_rules": [],
        "score_metrics": [],
    }
}


class ScenarioSdkV2:
    @staticmethod
    def create(root: Path, *, name: str, template: str = "generic") -> Path:
        if template not in _TEMPLATES or not name or root.exists():
            raise ValueError("scenario create target or template is invalid")
        root.mkdir(parents=True)
        document = {**_TEMPLATES[template], "scenario_id": name}
        manifest = {
            "schema_version": "package@2.0",
            "adapter_id": "adapter.v2",
            "scenario": document,
        }
        path = root / "scenario.yaml"
        path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        return path

    @staticmethod
    def validate(root: Path) -> ScenarioPackageV2:
        return ScenarioPackageV2.from_directory(root)

    @staticmethod
    def resolve(root: Path, *, catalog: CatalogV2) -> ResolvedScenarioV2:
        return ScenarioCompilerV2(catalog=catalog).compile(ScenarioSdkV2.validate(root))

    @staticmethod
    def pack(root: Path, target: Path) -> str:
        package = ScenarioSdkV2.validate(root)
        if target.exists():
            raise ValueError("scenario archive target already exists")
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*.yaml")):
                archive.write(path, path.relative_to(root).as_posix())
        recovered = ScenarioPackageV2.from_archive(target.read_bytes())
        if recovered.logical_hash != package.logical_hash:
            target.unlink(missing_ok=True)
            raise ValueError("scenario pack changed logical content")
        return recovered.archive_hash


__all__ = ["ScenarioSdkV2"]

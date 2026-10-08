"""Versioned scenario packages with an explicit include boundary.

A scenario package is a self-contained set of declarative files (the public
scenario declaration plus, for formal benchmark scenarios, the frozen
component configuration).  Every entry is a repository-relative path that must
stay inside the package root; the package content hash covers the entry paths
and file bytes only, never absolute paths, mtimes, or environment state.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from openmdbench.core.rng import configuration_hash


class PackageBoundaryError(ValueError):
    """Raised when a scenario package entry escapes its trust boundary."""


MAX_PACKAGE_FILE_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_TOTAL_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_ENTRIES = 128
MAX_CATALOG_FILES = 64


def _canonical_relative(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute():
        raise PackageBoundaryError(f"package entry must be a relative path: {relative}")
    if any(part == ".." for part in rel.parts):
        raise PackageBoundaryError(f"package entry must not traverse above the root: {relative}")
    resolved_root = root.resolve()
    candidate = (resolved_root / rel).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise PackageBoundaryError(f"package entry escapes the package root: {relative}")
    return candidate


@dataclass(frozen=True, slots=True)
class ScenarioPackageRef:
    """One installed or user-provided scenario package.

    ``root`` is the trust boundary.  ``scenario`` is the public scenario
    declaration (mandatory); ``component`` is the formal component
    configuration (optional, relative to the same root).
    """

    root: Path
    scenario: str
    component: str | None = None
    catalogs: tuple[str, ...] = ()

    def entry_paths(self) -> tuple[tuple[str, Path], ...]:
        """Return (relative_path, absolute_path) pairs, boundary-validated."""
        if len(self.catalogs) > MAX_CATALOG_FILES:
            raise PackageBoundaryError("scenario package may contain at most 64 catalog files")
        entries: tuple[str, ...] = ("scenario", self.scenario)
        if self.component is not None:
            entries = (*entries, "component", self.component)
        for index, catalog in enumerate(self.catalogs):
            entries = (*entries, f"catalog:{index}", catalog)
        return tuple(
            (entries[index], _canonical_relative(self.root, entries[index + 1]))
            for index in range(0, len(entries), 2)
        )

    def files(self) -> dict[str, bytes]:
        """Read every entry keyed by its repository-relative path."""
        result: dict[str, bytes] = {}
        for label, path in self.entry_paths():
            if path.stat().st_size > MAX_PACKAGE_FILE_BYTES:
                raise PackageBoundaryError(
                    f"package entry exceeds 16 MiB: {self._relative_for(label)}"
                )
            result[self._relative_for(label)] = path.read_bytes()
        return result

    def _relative_for(self, label: str) -> str:
        if label == "scenario":
            return self.scenario
        if label.startswith("catalog:"):
            return self.catalogs[int(label.partition(":")[2])]
        if self.component is None:
            raise ValueError("package has no component entry")
        return self.component

    def content_hash(self) -> str:
        """Stable SHA-256 over sorted (relative_path, file_sha256) pairs."""
        manifest = [
            {"path": relative, "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}"}
            for relative, data in sorted(self.files().items())
        ]
        return configuration_hash({"files": manifest})

    def pack(self, destination: str | Path) -> Path:
        """Create a deterministic archive with a hash-bearing manifest."""
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        files = self.files()
        manifest = {
            "scenario": self.scenario,
            "component": self.component,
            "catalogs": list(self.catalogs),
            "content_hash": self.content_hash(),
        }
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, data in sorted(files.items()):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                archive.writestr(info, data)
            info = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
            archive.writestr(info, json.dumps(manifest, sort_keys=True, separators=(",", ":")))
        return target


def unpack_scenario_package(
    archive_path: str | Path, destination: str | Path
) -> ScenarioPackageRef:
    """Safely unpack and verify a scenario archive inside ``destination``."""
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(infos) > MAX_PACKAGE_ENTRIES:
            raise PackageBoundaryError("scenario archive contains too many entries")
        if len(names) != len(set(names)):
            raise PackageBoundaryError("scenario archive contains duplicate paths")
        if names.count("manifest.json") != 1:
            raise PackageBoundaryError("scenario archive must contain one manifest")
        if any(item.file_size > MAX_PACKAGE_FILE_BYTES for item in infos):
            raise PackageBoundaryError("scenario archive entry exceeds 16 MiB")
        if sum(item.file_size for item in infos) > MAX_PACKAGE_TOTAL_BYTES:
            raise PackageBoundaryError("scenario archive exceeds 64 MiB uncompressed")
        if "manifest.json" not in names:
            raise PackageBoundaryError("scenario archive has no manifest")
        for name in names:
            _canonical_relative(target, name)
        manifest = json.loads(archive.read("manifest.json"))
        if not isinstance(manifest, dict):
            raise PackageBoundaryError("scenario archive manifest is invalid")
        archive.extractall(target)
    ref = ScenarioPackageRef(
        root=target,
        scenario=str(manifest["scenario"]),
        component=str(manifest["component"]) if manifest.get("component") else None,
        catalogs=tuple(str(value) for value in manifest.get("catalogs", ())),
    )
    if ref.content_hash() != manifest.get("content_hash"):
        raise PackageBoundaryError("scenario archive content hash mismatch")
    return ref

import zipfile
from pathlib import Path

import pytest
from openmdbench.scenarios.package import (
    PackageBoundaryError,
    ScenarioPackageRef,
    unpack_scenario_package,
)


def test_pack_unpack_preserves_hash(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "scenario.yaml").write_text("scenario_id: demo\n", encoding="utf-8")
    ref = ScenarioPackageRef(source, "scenario.yaml")
    archive = ref.pack(tmp_path / "scenario.omdpkg")
    restored = unpack_scenario_package(archive, tmp_path / "restored")
    assert restored.content_hash() == ref.content_hash()


def test_unpack_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.omdpkg"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape", "bad")
        output.writestr("manifest.json", "{}")
    with pytest.raises(PackageBoundaryError, match="traverse"):
        unpack_scenario_package(archive, tmp_path / "target")

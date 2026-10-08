"""RF-13 third-party scenario SDK smoke."""

from __future__ import annotations

from pathlib import Path

from openmdbench.scenarios.declarative_v2 import ScenarioPackageV2
from openmdbench.scenarios.sdk_v2 import ScenarioSdkV2


def test_new_user_can_create_validate_and_pack_without_python_scenario_code(
    tmp_path: Path,
) -> None:
    root = tmp_path / "third-party"
    ScenarioSdkV2.create(root, name="scenario.third-party")
    package = ScenarioSdkV2.validate(root)
    archive = tmp_path / "third-party.zip"
    archive_hash = ScenarioSdkV2.pack(root, archive)
    recovered = ScenarioPackageV2.from_archive(archive.read_bytes())
    assert recovered.logical_hash == package.logical_hash
    assert recovered.archive_hash == archive_hash
    assert tuple(root.rglob("*.py")) == ()

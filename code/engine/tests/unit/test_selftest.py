"""Self-test report helpers."""

from pathlib import Path

from openmdbench.selftest import configuration_hash


def test_configuration_hash_covers_project_and_scenarios(tmp_path: Path) -> None:
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "pyproject.toml").write_text("version = '1'\n")
    scenario = tmp_path / "scenarios/example.yaml"
    scenario.write_text("id: one\n")
    first = configuration_hash(tmp_path)
    scenario.write_text("id: two\n")
    assert first.startswith("sha256:")
    assert configuration_hash(tmp_path) != first

"""Contract checks for the T0.1 Ubuntu project scaffold."""

import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_declares_supported_python_and_dependency_groups() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    assert project["requires-python"] == ">=3.11,<3.13"
    assert set(project["optional-dependencies"]) >= {
        "core",
        "cuda",
        "dev",
        "server",
        "train",
    }


def test_required_make_targets_are_present() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    for target in ("setup", "lint", "typecheck", "test"):
        assert f"{target}:" in makefile

    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1" in makefile


def test_ci_covers_supported_python_versions() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python-version: ["3.11", "3.12"]' in workflow
    assert "make setup PYTHON=python" in workflow

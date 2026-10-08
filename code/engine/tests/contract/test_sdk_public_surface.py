"""Prevent SDK and examples from reaching into simulation internals."""

import ast
from pathlib import Path


def test_sdk_and_example_import_only_public_surfaces() -> None:
    root = Path(__file__).parents[2]
    paths = (
        *sorted((root / "openmdbench" / "sdk").glob("*.py")),
        root / "examples/sdk_random_policy.py",
    )
    forbidden = ("openmdbench.core", "openmdbench.envs", "openmdbench.replay")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = [
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ]
        assert not any(name.startswith(forbidden) for name in imported), path

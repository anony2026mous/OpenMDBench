"""Installation and package import smoke tests."""

import openmdbench


def test_public_package_imports() -> None:
    assert openmdbench.__version__ == "0.1.0"


def test_public_namespace_is_explicit() -> None:
    assert openmdbench.__all__ == ["__version__"]

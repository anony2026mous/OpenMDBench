"""Public scenario compiler facade with explicit, allowlisted adapter selection."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from openmdbench.scenarios.legacy import compiler_impl as _implementation
from openmdbench.scenarios.legacy.catalog_support import load_legacy_composition_catalog_v2
from openmdbench.scenarios.legacy.compiler_impl import (
    ScenarioCompileError,
    ScenarioCompileIssue,
)
from openmdbench.scenarios.legacy.compiler_impl import (
    ScenarioCompiler as _CompatibilityCompiler,
)
from openmdbench.scenarios.package import ScenarioPackageRef
from openmdbench.scenarios.resolved import ResolvedScenario

_implementation_any: Any = _implementation


class ScenarioCompiler:
    """Thin compatibility facade; adapter selection is explicit and allowlisted."""

    def __init__(
        self,
        map_root: str | Path | None = None,
        *,
        adapter_id: str = "adapter.compatibility-v1",
        adapter_registry: Mapping[str, type[_CompatibilityCompiler]] | None = None,
    ) -> None:
        registry = dict(adapter_registry or {"adapter.compatibility-v1": _CompatibilityCompiler})
        if adapter_id not in registry:
            raise ValueError(f"unknown scenario compiler adapter: {adapter_id}")
        self.adapter_registry = registry
        self.adapter_id = adapter_id
        self._delegate = registry[adapter_id](map_root=map_root)

    def compile_package(self, ref: ScenarioPackageRef) -> ResolvedScenario:
        _implementation_any.load_legacy_composition_catalog_v2 = load_legacy_composition_catalog_v2
        return self._delegate.compile_package(ref)

    def validate_package(self, ref: ScenarioPackageRef) -> tuple[ScenarioCompileIssue, ...]:
        return self._delegate.validate_package(ref)

    def inspect(self, resolved: ResolvedScenario) -> dict[str, Any]:
        return self._delegate.inspect(resolved)

    def _compile_composition(self, *args: Any, **kwargs: Any) -> Any:
        """Compatibility hook; the implementation calls atomic full validation."""
        catalog = kwargs.get("catalog")
        composition = kwargs.get("composition")
        if catalog is not None and composition is not None:
            catalog.validate_full_composition(composition)
        return self._delegate._compile_composition(*args, **kwargs)


__all__ = ["ScenarioCompileError", "ScenarioCompileIssue", "ScenarioCompiler"]

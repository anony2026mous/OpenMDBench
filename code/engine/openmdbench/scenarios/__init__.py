"""Versioned scenario schema and loader."""

from openmdbench.scenarios.declarative_v2 import (
    COMPILER_STAGES_V2,
    CompilerErrorV2,
    PackageLimitsV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
    StageRecordV2,
)
from openmdbench.scenarios.formal_v2 import (
    FormalScenarioEntryV2,
    compile_formal_scenario_v2,
    formal_scenario_registry_v2,
    load_formal_scenario_v2,
)
from openmdbench.scenarios.loader import load_scenario, render_briefing
from openmdbench.scenarios.schema import Scenario

__all__ = [
    "COMPILER_STAGES_V2",
    "CompilerErrorV2",
    "FormalScenarioEntryV2",
    "PackageLimitsV2",
    "ResolvedScenarioV2",
    "Scenario",
    "ScenarioCompilerV2",
    "ScenarioPackageV2",
    "StageRecordV2",
    "compile_formal_scenario_v2",
    "formal_scenario_registry_v2",
    "load_formal_scenario_v2",
    "load_scenario",
    "render_briefing",
]

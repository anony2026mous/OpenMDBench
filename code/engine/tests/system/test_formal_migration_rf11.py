import pytest
from openmdbench.core.session_runtime import SessionRuntime
from openmdbench.scenarios.compiler import ScenarioCompiler
from openmdbench.scenarios.runtime import formal_package_ref


@pytest.mark.parametrize(
    "scenario_id",
    ["MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"],
)
def test_formal_scenarios_compile_and_advance_from_resolved(scenario_id: str) -> None:
    resolved = ScenarioCompiler().compile_package(formal_package_ref(scenario_id))
    runtime = SessionRuntime(resolved, 73, builtin_policies=True)
    try:
        observation, _ = runtime.reset(seed=73)
        assert observation["timestamp"] == 0
        advanced, _, _, _, _ = runtime.step(None)
        assert advanced["timestamp"] == 1
    finally:
        runtime.close()

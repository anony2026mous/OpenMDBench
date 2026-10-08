"""RF-03 contracts for the explicit V2 compiler pipeline and legacy isolation."""

from __future__ import annotations

import copy
import inspect
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from openmdbench.scenarios import compiler as public_compiler
from openmdbench.scenarios import declarative_v2
from openmdbench.schemas.core_v2 import FactionV2
from tests.contract import test_declarative_mission_control_v2 as mission_fixture
from tests.contract import test_declarative_scenario_v2 as scenario_fixture

EXPECTED_STAGES = (
    "schema",
    "resource_versions",
    "defaults",
    "units",
    "factions_relationships",
    "formation_expansion",
    "compatibility",
    "coordinates",
    "boundary_deployment",
    "event_dependencies",
    "mission_scoring_controllers",
    "visibility",
    "stable_order",
    "freeze_hash",
)
DECLARATIVE: Any = declarative_v2


def test_public_stage_contract_has_exact_stable_order() -> None:
    assert DECLARATIVE.COMPILER_STAGES_V2 == EXPECTED_STAGES
    assert len(set(DECLARATIVE.COMPILER_STAGES_V2)) == len(EXPECTED_STAGES)


def test_compiler_exposes_trace_and_stage_local_stable_error_contract() -> None:
    compiler_type: Any = declarative_v2.ScenarioCompilerV2
    assert hasattr(compiler_type, "compile_with_trace")
    error_type: Any = declarative_v2.CompilerErrorV2
    signature = inspect.signature(error_type)
    assert "stage" in signature.parameters
    assert "trace" in signature.parameters


def test_resolved_provenance_contains_compiler_version_and_complete_stage_trace() -> None:
    resolved_type: Any = declarative_v2.ResolvedScenarioV2
    fields = getattr(resolved_type, "__dataclass_fields__", {})
    assert "compiler_version" in fields
    assert "compile_stage_trace" in fields
    assert "provenance" in fields


def test_pipeline_uses_explicit_stage_methods_not_one_hidden_compile_body() -> None:
    source = Path(declarative_v2.__file__).read_text(encoding="utf-8")
    for stage in EXPECTED_STAGES:
        assert f"def _stage_{stage}(" in source
    assert "source_yaml" not in source


@pytest.mark.parametrize(
    "forbidden",
    ("Side", "MD-AD", "MD-INT", "red_force", "blue_force", "scenario_id =="),
)
def test_generic_v2_source_has_no_scenario_or_side_special_cases(forbidden: str) -> None:
    source = Path(declarative_v2.__file__).read_text(encoding="utf-8")
    assert forbidden not in source


def test_generic_v2_does_not_import_legacy_and_legacy_is_physically_isolated() -> None:
    source = Path(declarative_v2.__file__).read_text(encoding="utf-8")
    assert "legacy" not in source.lower()
    root = Path(declarative_v2.__file__).parent
    assert (root / "legacy").is_dir()
    assert not (root / "legacy_catalog_support.py").exists()


def test_old_compiler_is_thin_facade_with_explicit_adapter_registry_only() -> None:
    source = Path(public_compiler.__file__).read_text(encoding="utf-8")
    compiler_source = inspect.getsource(public_compiler.ScenarioCompiler)
    assert len(compiler_source.splitlines()) < 160
    assert "adapter_registry" in compiler_source
    assert "scenario_id" not in compiler_source
    assert "difficulty" not in compiler_source
    assert 'if "waves"' not in compiler_source
    assert "declarative_v2" not in source or "legacy" not in source.lower()


def test_adapter_selection_is_manifest_explicit_and_allowlisted() -> None:
    package_type: Any = declarative_v2.ScenarioPackageV2
    assert hasattr(package_type, "from_mapping")
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        package_type.from_mapping(
            {
                "schema_version": "package@2.0",
                "adapter_id": "adapter.unknown",
                "scenario": {"schema_version": "2.0"},
            }
        )
    assert captured.value.code == "package.adapter_unknown"


def test_pipeline_contract_declares_deterministic_first_failure_policy() -> None:
    assert DECLARATIVE.STAGE_FAILURE_POLICY_V2 == "first_stage_then_file_path"


def _compiler_and_package() -> tuple[Any, Any]:
    return (
        declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog()),
        scenario_fixture._single_file_package(),
    )


def test_stage_handlers_consume_the_previous_typed_context(monkeypatch: pytest.MonkeyPatch) -> None:
    compiler, package = _compiler_and_package()
    expected_input: list[Any] = [package]
    outputs: list[Any] = []

    for ordinal, stage in enumerate(EXPECTED_STAGES):
        output = {"stage": stage, "ordinal": ordinal}
        outputs.append(output)

        def handler(value: Any, *, index: int = ordinal, result: Any = output) -> Any:
            assert value is expected_input[index]
            if index + 1 < len(EXPECTED_STAGES):
                expected_input.append(result)
            return result

        monkeypatch.setattr(type(compiler), f"_stage_{stage}", staticmethod(handler))

    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(package)
    assert captured.value.code == "scenario.pipeline_invalid"
    assert len(expected_input) == len(EXPECTED_STAGES)
    assert expected_input[1:] == outputs[:-1]


@pytest.mark.parametrize(
    "stage",
    (
        "resource_versions",
        "formation_expansion",
        "coordinates",
        "event_dependencies",
        "mission_scoring_controllers",
        "freeze_hash",
    ),
)
def test_disabling_feature_stage_cannot_produce_identical_valid_output(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = scenario_fixture._single_file_package(scenario_fixture._scenario(formation_count=1))
    baseline = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog()).compile(
        package
    )
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    monkeypatch.setattr(type(compiler), f"_stage_{stage}", staticmethod(lambda value: value))
    try:
        disabled = compiler.compile(package)
    except declarative_v2.CompilerErrorV2:
        return
    assert disabled != baseline


@pytest.mark.parametrize("failed_stage", EXPECTED_STAGES)
def test_stage_failure_has_exact_stage_and_completed_prior_trace(
    failed_stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    compiler, package = _compiler_and_package()

    def fail(_value: Any) -> Any:
        raise declarative_v2.CompilerErrorV2(
            "scenario.stage_fixture_invalid",
            file="scenario.yaml",
            path=(failed_stage,),
            value=failed_stage,
            reason="synthetic stage-local failure",
            suggestion="repair this stage input",
        )

    monkeypatch.setattr(type(compiler), f"_stage_{failed_stage}", staticmethod(fail))
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(package)
    error = captured.value
    ordinal = EXPECTED_STAGES.index(failed_stage)
    assert error.stage == failed_stage
    assert tuple(record.stage for record in error.trace) == EXPECTED_STAGES[:ordinal]
    assert all(record.status == "completed" for record in error.trace)


def test_compile_and_compile_with_trace_use_same_exact_pipeline() -> None:
    compiler, package = _compiler_and_package()
    direct = compiler.compile(package)
    traced, trace = compiler.compile_with_trace(package)
    assert direct == traced
    assert trace == direct.compile_stage_trace
    assert tuple(record.stage for record in trace) == EXPECTED_STAGES
    assert tuple(record.ordinal for record in trace) == tuple(range(14))
    assert all(record.status == "completed" for record in trace)
    assert all(hasattr(record, "duration_policy") for record in trace)


def test_stage_handlers_are_not_identity_noops_and_compile_body_is_orchestration_only() -> None:
    for stage in EXPECTED_STAGES:
        source = inspect.getsource(getattr(declarative_v2.ScenarioCompilerV2, f"_stage_{stage}"))
        compact = " ".join(source.split())
        assert "return value" not in compact
    compile_source = inspect.getsource(declarative_v2.ScenarioCompilerV2.compile)
    assert len(compile_source.splitlines()) < 100


def _rehashed_pipeline_json(resolved: Any, mutate: Any) -> str:
    payload: dict[str, Any] = json.loads(resolved.to_json())
    mutate(payload)
    payload["resolved_hash"] = declarative_v2.ResolvedScenarioV2.compute_resolved_hash(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value["compile_stage_trace"].pop(),
        lambda value: value["compile_stage_trace"].reverse(),
        lambda value: value["compile_stage_trace"].append(value["compile_stage_trace"][0]),
        lambda value: value["compile_stage_trace"][0].update(stage="unknown"),
        lambda value: value["compile_stage_trace"][0].update(status="failed"),
        lambda value: value.update(compiler_version="99.0.0"),
        lambda value: value["provenance"].update(compiler_version="99.0.0"),
        lambda value: value["provenance"].update(catalog_hash="sha256:" + "0" * 64),
        lambda value: value["provenance"].update(model_registry_hash="sha256:" + "1" * 64),
        lambda value: value["provenance"].update(package_logical_hash="sha256:" + "2" * 64),
        lambda value: value["provenance"].update(package_content_hash="sha256:" + "3" * 64),
        lambda value: value["provenance"].update(package_archive_hash="sha256:" + "4" * 64),
    ),
)
def test_from_json_rejects_trace_and_provenance_tamper_after_outer_rehash(
    mutate: Any,
) -> None:
    compiler, package = _compiler_and_package()
    with pytest.raises(ValueError) as captured:
        declarative_v2.ResolvedScenarioV2.from_json(
            _rehashed_pipeline_json(compiler.compile(package), mutate)
        )
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_provenance_contains_package_audit_identities_without_source_yaml() -> None:
    compiler, package = _compiler_and_package()
    resolved = compiler.compile(package)
    assert resolved.provenance.package_logical_hash == package.logical_hash
    assert resolved.provenance.package_content_hash == package.content_hash
    assert resolved.provenance.package_archive_hash == package.archive_hash
    encoded = resolved.to_json()
    restored = declarative_v2.ResolvedScenarioV2.from_json(encoded)
    assert restored.provenance == resolved.provenance
    assert "source_yaml" not in encoded and "source_path" not in encoded


def test_public_scenarios_package_exports_v2_pipeline_contract() -> None:
    import openmdbench.scenarios as scenarios

    for name in (
        "ScenarioCompilerV2",
        "ScenarioPackageV2",
        "ResolvedScenarioV2",
        "CompilerErrorV2",
        "StageRecordV2",
        "COMPILER_STAGES_V2",
    ):
        assert hasattr(scenarios, name)


EXPECTED_CONTEXT_FIELDS = {
    "schema": ("parsed_schema",),
    "resource_versions": ("resolved_resources",),
    "defaults": ("materialized_defaults",),
    "units": ("normalized_units",),
    "factions_relationships": ("factions", "relationships"),
    "formation_expansion": ("expanded_entities",),
    "compatibility": ("validated_compositions",),
    "coordinates": ("normalized_world", "normalized_coordinates"),
    "boundary_deployment": ("validated_deployments",),
    "event_dependencies": ("validated_events",),
    "mission_scoring_controllers": ("validated_mission", "validated_controllers"),
    "visibility": ("validated_visibility",),
    "stable_order": ("ordered_ir",),
    "freeze_hash": ("resolved",),
}


def test_each_valid_stage_owns_a_meaningful_typed_context_delta() -> None:
    compiler, package = _compiler_and_package()
    context: Any = package
    seen: set[str] = set()
    for stage in EXPECTED_STAGES:
        context = getattr(compiler, f"_stage_{stage}")(context)
        for field in EXPECTED_CONTEXT_FIELDS[stage]:
            assert hasattr(context, field), f"{stage} must own {field}"
            assert getattr(context, field) is not None
            assert field not in seen
            seen.add(field)
    assert context.resolved is not None


def _invalid_package(mutator: Any) -> Any:
    scenario = copy.deepcopy(scenario_fixture._scenario(formation_count=1))
    mutator(scenario)
    return scenario_fixture._single_file_package(scenario)


SEQUENCE_SECTIONS = (
    "entities",
    "formations",
    "factions",
    "relationships",
    "events",
    "mission_rules",
    "controller_slots",
    "visibility",
)
MAPPING_SECTIONS = ("world", "scoring")


def _hostile_shape_package(section: str, bad_value: Any, *, yaml_path: bool = False) -> Any:
    scenario = copy.deepcopy(mission_fixture._scenario())
    scenario[section] = bad_value
    if not yaml_path:
        return scenario_fixture._single_file_package(scenario)
    manifest = json.dumps(
        {"schema_version": "package@2.0", "scenario": scenario},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return declarative_v2.ScenarioPackageV2.from_entries((("scenario.yaml", manifest),))


def _assert_schema_error(package: Any) -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=mission_fixture._catalog())
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(package)
    error = captured.value
    assert error.stage == "schema"
    assert error.trace == ()
    assert isinstance(error.code, str) and error.code
    assert isinstance(error.file, str) and error.file
    assert isinstance(error.path, tuple) and error.path
    assert repr(error.value)
    assert isinstance(error.reason, str) and error.reason
    assert isinstance(error.suggestion, str) and error.suggestion


@pytest.mark.parametrize("section", SEQUENCE_SECTIONS)
@pytest.mark.parametrize("bad_value", (None, "not-a-list", 7, {"member": "mapping"}))
def test_schema_stage_wraps_hostile_top_level_sequence_shapes(section: str, bad_value: Any) -> None:
    _assert_schema_error(_hostile_shape_package(section, bad_value))


@pytest.mark.parametrize("section", MAPPING_SECTIONS)
@pytest.mark.parametrize("bad_value", (None, "not-a-map", 7, ["list-not-map"]))
def test_schema_stage_wraps_hostile_top_level_mapping_shapes(section: str, bad_value: Any) -> None:
    _assert_schema_error(_hostile_shape_package(section, bad_value))


@pytest.mark.parametrize(
    ("path", "bad_value"),
    (
        (("entities", 0), "entity-string"),
        (("entities", 0), 11),
        (("entities", 0), ["entity-list"]),
        (("entities", 0, "initial_state"), "state-string"),
        (("formations",), ["formation-string"]),
        (("formations",), [19]),
        (("formations",), [["formation-list"]]),
        (("factions", 0), "faction-string"),
        (("factions", 0), 23),
        (("factions", 0), ["faction-list"]),
        (("relationships",), ["relationship-string"]),
        (("relationships",), [29]),
        (("relationships",), [["relationship-list"]]),
        (("world", "zones", 0), "zone-string"),
        (("world", "zones", 0), 31),
        (("world", "zones", 0), ["zone-list"]),
        (("world", "boundaries"), ["boundary-string"]),
        (("world", "boundaries"), [37]),
        (("world", "boundaries"), [["boundary-list"]]),
        (("events", 0), "event-string"),
        (("events", 0), 41),
        (("events", 0), ["event-list"]),
        (("events", 0, "trigger"), "trigger-string"),
        (("events", 0, "payload"), ["payload-list"]),
        (("mission_rules", 0), "rule-string"),
        (("mission_rules", 0), 43),
        (("mission_rules", 0), ["rule-list"]),
        (("mission_rules", 0, "condition"), "condition-string"),
        (("scoring", "metrics", 0), "metric-string"),
        (("scoring", "metrics", 0), 47),
        (("scoring", "metrics", 0), ["metric-list"]),
        (("controller_slots", 0), "controller-string"),
        (("controller_slots", 0), 53),
        (("controller_slots", 0), ["controller-list"]),
        (("controller_slots", 0, "selector"), "selector-string"),
        (("visibility", 0), "visibility-string"),
        (("visibility", 0), 59),
        (("visibility", 0), ["visibility-list"]),
    ),
)
def test_schema_stage_wraps_hostile_member_and_required_mapping_shapes(
    path: tuple[Any, ...], bad_value: Any
) -> None:
    scenario = copy.deepcopy(mission_fixture._scenario())
    target: Any = scenario
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = bad_value
    _assert_schema_error(scenario_fixture._single_file_package(scenario))


@pytest.mark.parametrize(
    ("section", "bad_value"),
    (
        ("entities", "not-a-list"),
        ("formations", 61),
        ("factions", {"not": "a-list"}),
        ("relationships", None),
        ("world", ["not-a-map"]),
        ("events", "not-a-list"),
        ("mission_rules", 67),
        ("scoring", ["not-a-map"]),
        ("controller_slots", {"not": "a-list"}),
        ("visibility", None),
    ),
)
def test_schema_stage_wraps_malformed_shapes_after_yaml_normalization(
    section: str, bad_value: Any
) -> None:
    _assert_schema_error(_hostile_shape_package(section, bad_value, yaml_path=True))


@pytest.mark.parametrize(
    ("owner_stage", "mutator"),
    (
        ("schema", lambda value: value.update(schema_version="99.0")),
        (
            "resource_versions",
            lambda value: value["formations"][0]["entity_template"].update(
                platform_ref="platforms.missing@2.0.0"
            ),
        ),
        (
            "defaults",
            lambda value: value["formations"][0]["entity_template"]["initial_state"].pop(
                "heading_deg"
            ),
        ),
        (
            "units",
            lambda value: value["formations"][0]["entity_template"]["initial_state"].update(
                velocity_mps=["bad-unit", 0.0, 0.0]
            ),
        ),
        (
            "factions_relationships",
            lambda value: value["relationships"][0].update(source_faction_id="faction.missing"),
        ),
        (
            "formation_expansion",
            lambda value: value["formations"][0].update(id_pattern="constant-id"),
        ),
        (
            "compatibility",
            lambda value: value["formations"][0]["entity_template"].update(
                dynamics_ref="platforms.generic@2.0.0"
            ),
        ),
        (
            "coordinates",
            lambda value: value["formations"][0]["entity_template"]["initial_state"].update(
                position_m=[1.0, 2.0]
            ),
        ),
        (
            "boundary_deployment",
            lambda value: value["world"].update(boundary_policy="teleport_anywhere"),
        ),
        (
            "event_dependencies",
            lambda value: value["events"][0].update(depends_on=["event.missing"]),
        ),
        (
            "mission_scoring_controllers",
            lambda value: value["mission_rules"][0]["condition"].update(operator="execute_python"),
        ),
        (
            "visibility",
            lambda value: value.update(
                visibility=[{"view": "public", "scope": "truth", "allow": True}]
            ),
        ),
        (
            "stable_order",
            lambda value: value["formations"].append(copy.deepcopy(value["formations"][0])),
        ),
    ),
)
def test_real_invalid_document_fails_at_its_earliest_owner_stage(
    owner_stage: str, mutator: Any
) -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(_invalid_package(mutator))
    error = captured.value
    ordinal = EXPECTED_STAGES.index(owner_stage)
    assert error.stage == owner_stage
    assert tuple(item.stage for item in error.trace) == EXPECTED_STAGES[:ordinal]


def test_pass_through_stage_is_caught_by_next_stage_missing_owned_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiler, package = _compiler_and_package()
    monkeypatch.setattr(type(compiler), "_stage_coordinates", staticmethod(lambda context: context))
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(package)
    assert captured.value.stage == "boundary_deployment"
    assert captured.value.code == "scenario.pipeline_context_missing"


def test_freeze_stage_only_finalizes_ordered_ir_and_hash() -> None:
    freeze_source = inspect.getsource(declarative_v2.ScenarioCompilerV2._stage_freeze_hash)
    assert "_compile_resolved" not in freeze_source
    assert "package.document" not in freeze_source
    assert "ordered_ir" in freeze_source
    compiler_source = inspect.getsource(declarative_v2.ScenarioCompilerV2)
    assert "def _compile_resolved(" not in compiler_source


@pytest.mark.parametrize(
    ("owner_stage", "mutator"),
    (
        ("schema", lambda value: value["entities"][0].update(platform_ref=7)),
        (
            "resource_versions",
            lambda value: value["entities"][0].update(platform_ref="platforms.missing@2.0.0"),
        ),
        (
            "coordinates",
            lambda value: value["entities"][0]["initial_state"].update(position_m=[1.0, 2.0]),
        ),
        (
            "factions_relationships",
            lambda value: value["relationships"][0].update(target_faction_id="faction.missing"),
        ),
    ),
)
def test_explicit_entity_errors_are_owned_by_exact_earliest_stage(
    owner_stage: str, mutator: Any
) -> None:
    scenario = copy.deepcopy(scenario_fixture._scenario())
    mutator(scenario)
    package = scenario_fixture._single_file_package(scenario)
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    with pytest.raises(declarative_v2.CompilerErrorV2) as captured:
        compiler.compile(package)
    ordinal = EXPECTED_STAGES.index(owner_stage)
    assert captured.value.stage == owner_stage
    assert tuple(item.stage for item in captured.value.trace) == EXPECTED_STAGES[:ordinal]


def test_stage_context_contains_transformed_domain_artifacts_not_raw_sentinels() -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    package = scenario_fixture._single_file_package(scenario_fixture._scenario(formation_count=10))
    context: Any = package
    snapshots: dict[str, Any] = {}
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
        snapshots[stage] = context

    assert isinstance(snapshots["defaults"].materialized_defaults, Mapping)
    assert snapshots["defaults"].materialized_defaults is not package.document
    assert isinstance(snapshots["units"].normalized_units, Mapping)
    assert snapshots["units"].normalized_units is not package.document
    expanded = snapshots["formation_expansion"].expanded_entities
    assert isinstance(expanded, tuple) and len(expanded) == 10
    assert all(
        hasattr(entity, "initial_state") and hasattr(entity, "platform_ref") for entity in expanded
    )
    compositions = snapshots["compatibility"].validated_compositions
    assert isinstance(compositions, Mapping) and set(compositions) == {
        entity.id for entity in expanded
    }
    coordinates = snapshots["coordinates"].normalized_coordinates
    assert isinstance(coordinates, Mapping) and set(coordinates) == {
        entity.id for entity in expanded
    }
    assert all(len(position) == 3 for position in coordinates.values())
    assert isinstance(snapshots["boundary_deployment"].validated_deployments, tuple)
    assert all(
        hasattr(event, "event_type") for event in snapshots["event_dependencies"].validated_events
    )
    assert isinstance(snapshots["mission_scoring_controllers"].validated_mission, tuple)
    assert isinstance(snapshots["visibility"].validated_visibility, tuple)
    for stage, snapshot in snapshots.items():
        for field in EXPECTED_CONTEXT_FIELDS[stage]:
            assert getattr(snapshot, field) is not True


class _UnavailablePackage:
    @property
    def document(self) -> Any:
        raise AssertionError("stable_order must not reread source document")


def test_stable_order_and_freeze_work_after_source_package_becomes_unavailable() -> None:
    compiler, package = _compiler_and_package()
    expected = compiler.compile(package)
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    context = replace(context, package=_UnavailablePackage())
    ordered = compiler._stage_stable_order(context)
    frozen = compiler._stage_freeze_hash(ordered)
    assert frozen.resolved == expected


def test_stable_order_only_sorts_assembled_context_and_never_recompiles_package() -> None:
    source = inspect.getsource(declarative_v2.ScenarioCompilerV2._stage_stable_order)
    for forbidden in ("package", "document", "catalog", "_materialize_ordered_ir"):
        assert forbidden not in source
    compiler_source = inspect.getsource(declarative_v2.ScenarioCompilerV2)
    assert "def _materialize_ordered_ir(self, package" not in compiler_source


def test_all_post_schema_stages_compile_without_source_package_or_document() -> None:
    compiler, package = _compiler_and_package()
    expected = compiler.compile(package)
    context: Any = compiler._stage_schema(package)
    context = replace(context, package=_UnavailablePackage())
    for stage in EXPECTED_STAGES[1:]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    assert context.resolved == expected


def test_post_schema_handlers_and_helpers_cannot_accept_or_read_source_package() -> None:
    compiler_source = inspect.getsource(declarative_v2.ScenarioCompilerV2)
    for stage in EXPECTED_STAGES[1:]:
        source = inspect.getsource(getattr(declarative_v2.ScenarioCompilerV2, f"_stage_{stage}"))
        for forbidden in ("context.package", "package.document", "source.document"):
            assert forbidden not in source
    assert "def _materialize_ir(self, source: ScenarioPackageV2" not in compiler_source
    assert "def _materialize_ir(self, package: ScenarioPackageV2" not in compiler_source
    assert "_materialize_ir(context.package)" not in compiler_source


OWNED_ARTIFACT_FORGERIES: tuple[tuple[str, str, Any], ...] = (
    ("resource_versions", "resolved_resources", ()),
    ("defaults", "materialized_defaults", {"field": "forged-default"}),
    ("units", "normalized_units", {"position_m": "km"}),
    ("factions_relationships", "factions", ()),
    ("formation_expansion", "expanded_entities", ()),
    ("compatibility", "validated_compositions", {}),
    ("coordinates", "normalized_coordinates", {"entity.forged": (9.0, 9.0, 9.0)}),
    ("boundary_deployment", "validated_deployments", ()),
    ("event_dependencies", "validated_events", ()),
    ("mission_scoring_controllers", "validated_mission", ()),
    ("mission_scoring_controllers", "validated_controllers", ("controller.forged",)),
    ("visibility", "validated_visibility", ("visibility.forged",)),
)


@pytest.mark.parametrize(("owner_stage", "field", "forged"), OWNED_ARTIFACT_FORGERIES)
def test_each_owned_artifact_is_consumed_by_downstream_assembly(
    owner_stage: str, field: str, forged: Any
) -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    package = scenario_fixture._single_file_package(scenario_fixture._scenario(formation_count=10))
    baseline = compiler.compile(package)
    context: Any = package
    owner_index = EXPECTED_STAGES.index(owner_stage)
    for stage in EXPECTED_STAGES[: owner_index + 1]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    original = getattr(context, field)
    assert original != forged
    context = replace(context, **{field: forged}, package=_UnavailablePackage())
    try:
        for stage in EXPECTED_STAGES[owner_index + 1 :]:
            context = getattr(compiler, f"_stage_{stage}")(context)
    except (declarative_v2.CompilerErrorV2, TypeError, ValueError):
        return
    assert context.resolved != baseline


def test_visibility_only_normalizes_visibility_and_stable_order_assembles_context() -> None:
    visibility_source = inspect.getsource(declarative_v2.ScenarioCompilerV2._stage_visibility)
    assert "pre_resolved" not in visibility_source
    assert "_materialize" not in visibility_source
    stable_source = inspect.getsource(declarative_v2.ScenarioCompilerV2._stage_stable_order)
    assert "ordered_ir" in stable_source
    assert "context" in stable_source


def test_pre_stable_context_never_contains_a_full_resolved_scenario() -> None:
    fields = getattr(declarative_v2.PipelineContextV2, "__dataclass_fields__", {})
    for forbidden in ("schema_resolved", "pre_resolved", "baseline", "ordered_ir", "resolved"):
        if forbidden in {"ordered_ir", "resolved"}:
            continue
        assert forbidden not in fields
    compiler, package = _compiler_and_package()
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
        for value in vars(context).values() if hasattr(context, "__dict__") else ():
            assert not isinstance(value, declarative_v2.ResolvedScenarioV2)
    assert context.ordered_ir is None and context.resolved is None


def test_resolved_constructor_is_not_called_before_stable_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    compiler, package = _compiler_and_package()
    factory_name = (
        "_assemble_schema_baseline"
        if hasattr(type(compiler), "_assemble_schema_baseline")
        else "_assemble_ordered_ir"
    )
    original = getattr(type(compiler), factory_name)

    def constructing(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append("construct")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(compiler), factory_name, constructing)
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    assert calls == []
    context = compiler._stage_stable_order(context)
    assert calls
    assert context.ordered_ir is not None


def test_no_pre_stable_helper_constructs_resolved_or_compiles_schema_baseline() -> None:
    compiler_source = inspect.getsource(declarative_v2.ScenarioCompilerV2)
    for forbidden in (
        "schema_resolved",
        "pre_resolved",
        "_assemble_schema_baseline",
        "baseline =",
    ):
        assert forbidden not in compiler_source
    for stage in EXPECTED_STAGES[:-2]:
        source = inspect.getsource(getattr(declarative_v2.ScenarioCompilerV2, f"_stage_{stage}"))
        assert "ResolvedScenarioV2(" not in source


def test_consistent_coordinate_artifact_change_is_reflected_in_final_output() -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    package = scenario_fixture._single_file_package(scenario_fixture._scenario())
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    coordinates = dict(context.normalized_coordinates)
    coordinates["entity-independent"] = (901.0, 902.0, 903.0)
    context = replace(context, normalized_coordinates=coordinates)
    context = compiler._stage_stable_order(context)
    context = compiler._stage_freeze_hash(context)
    entity = next(item for item in context.resolved.entities if item.id == "entity-independent")
    assert entity.initial_state.position_m == (901.0, 902.0, 903.0)


def test_order_neutral_artifact_reordering_is_canonicalized() -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    package = scenario_fixture._single_file_package(scenario_fixture._scenario(formation_count=10))
    baseline = compiler.compile(package)
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    context = replace(
        context,
        expanded_entities=tuple(reversed(context.expanded_entities)),
        validated_deployments=tuple(reversed(context.validated_deployments)),
    )
    context = compiler._stage_stable_order(context)
    context = compiler._stage_freeze_hash(context)
    assert context.resolved.resolved_hash == baseline.resolved_hash


def _before_stable(compiler: Any, package: Any) -> Any:
    context: Any = package
    for stage in EXPECTED_STAGES[:-2]:
        context = getattr(compiler, f"_stage_{stage}")(context)
    return context


def _finish(compiler: Any, context: Any) -> Any:
    return compiler._stage_freeze_hash(compiler._stage_stable_order(context)).resolved


def test_stable_assembler_never_recompiles_parsed_schema_or_document() -> None:
    compiler_source = inspect.getsource(declarative_v2.ScenarioCompilerV2)
    assert "_assemble_from_document" not in compiler_source
    stable_source = inspect.getsource(declarative_v2.ScenarioCompilerV2._stage_stable_order)
    for forbidden in ("parsed_schema", "document", "package", "_assemble_schema_baseline"):
        assert forbidden not in stable_source
    assembler = getattr(declarative_v2.ScenarioCompilerV2, "_assemble_ordered_ir", None)
    assert assembler is not None
    assembler_source = inspect.getsource(assembler)
    assert "parsed_schema" not in assembler_source
    assert "document" not in assembler_source
    assert "ScenarioPackageV2" not in str(inspect.signature(assembler))


def test_stable_assembler_explicitly_consumes_every_owned_final_artifact() -> None:
    assembler = getattr(declarative_v2.ScenarioCompilerV2, "_assemble_ordered_ir", None)
    assert assembler is not None
    source = inspect.getsource(assembler)
    for field in (
        "resolved_resources",
        "materialized_defaults",
        "normalized_units",
        "factions",
        "relationships",
        "expanded_entities",
        "validated_compositions",
        "normalized_world",
        "normalized_coordinates",
        "validated_deployments",
        "validated_events",
        "validated_mission",
        "validated_controllers",
        "validated_visibility",
    ):
        assert f"context.{field}" in source


def test_resource_default_unit_and_composition_artifacts_are_runtime_complete() -> None:
    compiler, package = _compiler_and_package()
    context = _before_stable(compiler, package)
    assert context.resolved_resources
    assert all(
        hasattr(resource, "content_hash") and hasattr(resource, "normalized_content")
        for resource in context.resolved_resources
    )
    assert all(not isinstance(value, bool) for value in context.materialized_defaults.values())
    assert context.normalized_units and all(
        isinstance(unit, str) and unit for unit in context.normalized_units.values()
    )
    assert all(
        hasattr(composition, "platform_ref")
        for composition in context.validated_compositions.values()
    )


def test_added_unused_faction_artifact_appears_in_final_resolved() -> None:
    compiler, package = _compiler_and_package()
    context = _before_stable(compiler, package)
    added = FactionV2(schema_version="2.0", id="faction.added")
    context = replace(context, factions=(*context.factions, added))
    resolved = _finish(compiler, context)
    assert "faction.added" in {faction.id for faction in resolved.factions}


def test_consistent_entity_removal_artifacts_remove_final_entity() -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=scenario_fixture._catalog())
    package = scenario_fixture._single_file_package(scenario_fixture._scenario(formation_count=10))
    context = _before_stable(compiler, package)
    removed = context.expanded_entities[-1].id
    entities = tuple(entity for entity in context.expanded_entities if entity.id != removed)
    context = replace(
        context,
        expanded_entities=entities,
        validated_deployments=entities,
        validated_compositions={
            key: value for key, value in context.validated_compositions.items() if key != removed
        },
        normalized_coordinates={
            key: value for key, value in context.normalized_coordinates.items() if key != removed
        },
    )
    resolved = _finish(compiler, context)
    assert removed not in {entity.id for entity in resolved.entities}
    assert len(resolved.entities) == 9


def test_event_and_mission_artifact_changes_reach_final_resolved() -> None:
    compiler, package = _compiler_and_package()
    context = _before_stable(compiler, package)
    context = replace(context, validated_events=(), validated_mission=())
    resolved = _finish(compiler, context)
    assert resolved.events == ()
    assert resolved.mission_rules == ()


def test_visibility_scoring_and_controller_artifacts_reach_final_resolved() -> None:
    compiler = declarative_v2.ScenarioCompilerV2(catalog=mission_fixture._catalog())
    package = declarative_v2.ScenarioPackageV2.from_mapping(
        {"schema_version": "package@2.0", "scenario": mission_fixture._scenario()}
    )
    context = _before_stable(compiler, package)
    context = replace(
        context,
        validated_controllers=(),
        validated_visibility=tuple(
            item for item in context.validated_visibility if item.get("view") != "controller"
        ),
    )
    resolved = _finish(compiler, context)
    assert resolved.controller_slots == ()
    assert all(item.view != "controller" for item in resolved.visibility.matrix)
    assert resolved.scoring.metrics

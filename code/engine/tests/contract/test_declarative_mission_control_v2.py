"""RF-03 RED contracts for mission, scoring, control, and visibility compilation."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest
from openmdbench.catalog.v2 import (
    CatalogResourceV2,
    CatalogV2,
    ModelFactoryMetadataV2,
    ModelRegistryV2,
)
from openmdbench.scenarios import declarative_v2 as declarative_module
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ResolvedScenarioV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)


def _catalog() -> CatalogV2:
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.control-contract",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + "c" * 64,
            resource_types=("platforms", "dynamics", "sensors"),
            field_units={},
        ),
        lambda definition: definition,
    )
    registry.freeze()
    dynamics = CatalogResourceV2(
        schema_version="2.0",
        resource_type="dynamics",
        id="motion.arbitrary",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.control-contract@2.0.0",
        content={"compatible_platform_types": ["generic"], "mobile": True},
    )
    sensor = CatalogResourceV2(
        schema_version="2.0",
        resource_type="sensors",
        id="sensor.arbitrary",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.control-contract@2.0.0",
        content={"compatible_platform_types": ["generic"], "slot_type": "sensor"},
    )
    platform = CatalogResourceV2(
        schema_version="2.0",
        resource_type="platforms",
        id="platform.arbitrary",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.control-contract@2.0.0",
        content={
            "platform_type": "generic",
            "domain": "synthetic-air",
            "mobile": True,
            "allowed_dynamics": [dynamics.exact_ref],
            "component_slots": ["sensor"],
            "payload_capacity_kg": 0.0,
        },
    )
    return CatalogV2((platform, dynamics, sensor), engine_version="2.0.0", model_registry=registry)


def _entity(identifier: str, faction: str = "faction.alpha") -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "id": identifier,
        "faction_id": faction,
        "platform_ref": "platform.arbitrary@2.0.0",
        "dynamics_ref": "motion.arbitrary@2.0.0",
        "component_refs": ["sensor.arbitrary@2.0.0"],
        "initial_state": {
            "schema_version": "2.0",
            "position_m": [1.0, 2.0, 3.0],
            "velocity_mps": [0.0, 0.0, 0.0],
            "heading_deg": 0.0,
        },
        "tags": ["recon"],
    }


def _selector(entity_id: str = "asset.000") -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "factions": ["faction.alpha"],
        "entity_ids": [entity_id],
        "platforms": ["platform.arbitrary@2.0.0"],
        "domains": ["synthetic-air"],
        "capabilities": ["sensor"],
        "zones": ["zone.objective"],
        "events": ["event.marker"],
    }


def _scenario(slot_count: int = 1) -> dict[str, Any]:
    entities = [_entity(f"asset.{index:03d}") for index in range(max(slot_count, 1))]
    slots = [
        {
            "id": f"slot.{index:03d}",
            "controller_id": f"controller.{index:03d}",
            "faction_id": "faction.alpha",
            "selector": _selector(f"asset.{index:03d}"),
            "required_capabilities": ["sensor"],
            "action_schema_ref": "action-batch@2.0",
            "observation_schema_ref": "observation@2.0",
            "exclusive": True,
        }
        for index in range(slot_count)
    ]
    return {
        "schema_version": "2.0",
        "scenario_id": "scenario.mission-control",
        "factions": [
            {"schema_version": "2.0", "id": "faction.alpha"},
            {"schema_version": "2.0", "id": "faction.beta"},
        ],
        "relationships": [],
        "entities": entities,
        "formations": [],
        "world": {
            "schema_version": "2.0",
            "coordinate_system": "local_m",
            "zones": [
                {
                    "schema_version": "2.0",
                    "id": "zone.objective",
                    "geometry_type": "polygon",
                    "coordinates_m": [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]],
                }
            ],
        },
        "events": [
            {
                "schema_version": "2.0",
                "id": "event.marker",
                "event_type": "mission_marker",
                "trigger": {"tick": 1},
                "payload": {},
            }
        ],
        "mission_states": ["state.active", "state.complete"],
        "mission_rules": [
            {
                "schema_version": "2.0",
                "id": "rule.objective",
                "priority": 10,
                "depends_on": [],
                "condition": {
                    "schema_version": "2.0",
                    "operator": "count",
                    "selector": _selector(),
                    "parameters": {"comparison": ">=", "value": 1},
                },
                "outcome": {"set_state": "state.complete", "emit_event": "event.marker"},
            }
        ],
        "scoring": {
            "weight_policy": "normalized_sum_one",
            "metrics": [
                {
                    "id": "metric.objective",
                    "selector": _selector(),
                    "aggregation": "count",
                    "unit": "1",
                    "direction": "maximize",
                    "weight": 1.0,
                    "available": False,
                    "value": None,
                }
            ],
        },
        "score_metrics": [],
        "controller_policy": "explicit_uncontrolled",
        "controller_slots": slots,
        "visibility": [
            {"view": "referee", "scope": "truth", "allow": True},
            {"view": "public", "scope": "public", "allow": True},
            {
                "view": "faction",
                "faction_id": "faction.alpha",
                "scope": "own_and_contacts",
                "allow": True,
            },
            {
                "view": "controller",
                "controller_id": "controller.000",
                "scope": "claimed_entities",
                "allow": True,
            },
        ],
    }


def _compile(payload: dict[str, Any]) -> Any:
    package = ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": payload})
    return ScenarioCompilerV2(catalog=_catalog()).compile(package)


def _assert_error(payload: dict[str, Any], code: str, section: str) -> None:
    with pytest.raises(CompilerErrorV2) as captured:
        _compile(payload)
    error = captured.value
    assert error.code == code
    assert section in error.path
    assert error.file == f"{section}.yaml"
    assert error.value is not None and error.reason and error.suggestion


def test_mission_selectors_conditions_and_outcomes_are_fully_resolved_and_frozen() -> None:
    resolved = _compile(_scenario())
    rule = resolved.mission_rules[0]
    assert rule.selector_resolution.entity_ids == ("asset.000",)
    assert rule.selector_resolution.faction_ids == ("faction.alpha",)
    assert rule.selector_resolution.capabilities == ("sensor",)
    assert rule.condition.operator == "count"
    assert rule.outcome.set_state == "state.complete"
    with pytest.raises((TypeError, AttributeError)):
        rule.selector_resolution.entity_ids += ("injected",)


@pytest.mark.parametrize(
    ("change", "code"),
    (
        ({"operator": "execute_python"}, "scenario.mission_operator_invalid"),
        (
            {"parameters": {"comparison": "approximately", "value": 1}},
            "scenario.mission_parameter_invalid",
        ),
    ),
)
def test_mission_operator_and_typed_parameters_are_whitelisted(
    change: dict[str, Any], code: str
) -> None:
    payload = _scenario()
    payload["mission_rules"][0]["condition"].update(change)
    _assert_error(payload, code, "mission_rules")


def test_mission_references_cycles_duplicate_rules_and_direct_mutation_are_rejected() -> None:
    payload = _scenario()
    payload["mission_rules"][0]["condition"]["selector"]["entity_ids"] = ["missing"]
    _assert_error(payload, "scenario.mission_reference_missing", "mission_rules")
    payload = _scenario()
    duplicate = copy.deepcopy(payload["mission_rules"][0])
    payload["mission_rules"].append(duplicate)
    _assert_error(payload, "scenario.mission_rule_duplicate", "mission_rules")
    payload = _scenario()
    payload["mission_rules"][0]["depends_on"] = ["rule.objective"]
    _assert_error(payload, "scenario.mission_dependency_cycle", "mission_rules")
    payload = _scenario()
    payload["mission_rules"][0]["outcome"] = {"health": 0.0}
    _assert_error(payload, "scenario.mission_outcome_forbidden", "mission_rules")


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_controller_slots_expand_zero_one_ten_hundred_with_exact_claims(count: int) -> None:
    resolved = _compile(_scenario(count))
    assert len(resolved.controller_slots) == count
    assert tuple(slot.id for slot in resolved.controller_slots) == tuple(
        f"slot.{index:03d}" for index in range(count)
    )
    assert all(len(slot.resolved_entity_ids) == 1 for slot in resolved.controller_slots)


def test_controller_claims_ownership_capability_and_schema_refs_are_validated() -> None:
    payload = _scenario(2)
    payload["controller_slots"][1]["selector"] = _selector("asset.000")
    _assert_error(payload, "scenario.controller_claim_conflict", "controller_slots")
    payload = _scenario()
    payload["controller_slots"][0]["faction_id"] = "faction.beta"
    _assert_error(payload, "scenario.controller_ownership_invalid", "controller_slots")
    payload = _scenario()
    payload["controller_slots"][0]["required_capabilities"] = ["weapon"]
    _assert_error(payload, "scenario.controller_capability_missing", "controller_slots")
    payload = _scenario()
    payload["controller_slots"][0]["action_schema_ref"] = "action-batch"
    _assert_error(payload, "scenario.controller_schema_invalid", "controller_slots")


def test_controller_ids_slots_and_uncontrolled_policy_are_explicit_and_unique() -> None:
    payload = _scenario(2)
    payload["controller_slots"][1]["id"] = "slot.000"
    _assert_error(payload, "scenario.controller_slot_duplicate", "controller_slots")
    payload = _scenario(2)
    payload["controller_slots"][1]["controller_id"] = "controller.000"
    _assert_error(payload, "scenario.controller_duplicate", "controller_slots")
    payload = _scenario()
    payload.pop("controller_policy")
    _assert_error(payload, "scenario.controller_policy_missing", "controller_slots")


@pytest.mark.parametrize("weight", (True, "1", math.nan, math.inf, -1.0))
def test_scoring_weight_is_finite_numeric_non_bool_and_policy_is_explicit(weight: Any) -> None:
    payload = _scenario()
    payload["scoring"]["metrics"][0]["weight"] = weight
    _assert_error(payload, "scenario.scoring_weight_invalid", "scoring")


def test_scoring_na_is_distinct_from_zero_and_configuration_is_order_stable() -> None:
    payload = _scenario()
    zero = copy.deepcopy(payload["scoring"]["metrics"][0])
    zero.update(id="metric.zero", available=True, value=0.0, weight=0.0)
    payload["scoring"]["metrics"].append(zero)
    first = _compile(payload)
    reversed_payload = copy.deepcopy(payload)
    reversed_payload["scoring"]["metrics"].reverse()
    second = _compile(reversed_payload)
    assert first.scoring.metrics[0].available is False
    assert first.scoring.metrics[0].value is None
    assert first.scoring.metrics[1].available is True
    assert first.scoring.metrics[1].value == 0.0
    assert first.resolved_hash == second.resolved_hash


def test_scoring_duplicate_refs_aggregation_unit_direction_and_weight_sum_reject() -> None:
    for field, value, code in (
        ("aggregation", "python", "scenario.scoring_aggregation_invalid"),
        ("unit", "fortnight", "scenario.scoring_unit_invalid"),
        ("direction", "sideways", "scenario.scoring_direction_invalid"),
    ):
        payload = _scenario()
        payload["scoring"]["metrics"][0][field] = value
        _assert_error(payload, code, "scoring")
    payload = _scenario()
    payload["scoring"]["metrics"].append(copy.deepcopy(payload["scoring"]["metrics"][0]))
    _assert_error(payload, "scenario.scoring_metric_duplicate", "scoring")
    payload = _scenario()
    payload["scoring"]["metrics"][0]["weight"] = 0.5
    _assert_error(payload, "scenario.scoring_weight_policy_invalid", "scoring")


def test_visibility_endpoints_conflicts_and_information_leakage_are_rejected() -> None:
    payload = _scenario()
    payload["visibility"][2]["faction_id"] = "faction.missing"
    _assert_error(payload, "scenario.visibility_endpoint_missing", "visibility")
    payload = _scenario()
    payload["visibility"].append(copy.deepcopy(payload["visibility"][1]))
    payload["visibility"][-1]["allow"] = False
    _assert_error(payload, "scenario.visibility_conflict", "visibility")
    payload = _scenario()
    payload["visibility"][1]["scope"] = "truth"
    _assert_error(payload, "scenario.visibility_leakage", "visibility")


def test_visibility_matrix_is_normalized_and_input_order_hash_independent() -> None:
    first_payload = _scenario()
    second_payload = copy.deepcopy(first_payload)
    second_payload["visibility"].reverse()
    first = _compile(first_payload)
    second = _compile(second_payload)
    assert first.visibility.matrix == second.visibility.matrix
    assert first.resolved_hash == second.resolved_hash


def test_resolved_control_sections_roundtrip_without_runtime_selectors_or_catalog() -> None:
    resolved = _compile(_scenario())
    encoded = resolved.to_json()
    restored: Any = ResolvedScenarioV2.from_json(encoded)
    assert restored == resolved
    assert "runtime_selector" not in encoded and "catalog_resolver" not in encoded
    payload = json.loads(encoded)
    payload["controller_slots"][0]["resolved_entity_ids"] = ["asset.missing"]
    resolved_type: Any = ResolvedScenarioV2
    payload["resolved_hash"] = resolved_type.compute_resolved_hash(payload)
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(json.dumps(payload))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_selector_without_entity_ids_resolves_full_filter_intersection() -> None:
    payload = _scenario(2)
    payload["entities"].append(_entity("asset.beta", "faction.beta"))
    selector = payload["mission_rules"][0]["condition"]["selector"]
    selector.pop("entity_ids")
    resolved = _compile(payload)
    assert resolved.mission_rules[0].selector_resolution.entity_ids == (
        "asset.000",
        "asset.001",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("factions", ["faction.beta"]),
        ("platforms", ["platform.missing@2.0.0"]),
        ("domains", ["synthetic-surface"]),
        ("capabilities", ["weapon"]),
    ),
)
def test_selector_intersection_empty_match_is_stable(field: str, value: Any) -> None:
    payload = _scenario()
    selector = payload["mission_rules"][0]["condition"]["selector"]
    selector.pop("entity_ids")
    selector[field] = value
    _assert_error(payload, "scenario.mission_selector_empty", "mission_rules")


@pytest.mark.parametrize(
    ("operator", "parameters"),
    (
        ("state", {}),
        ("state", {"state": 7}),
        ("event", {"event_id": 7}),
        ("time", {"comparison": ">=", "tick": "1"}),
        ("count", {"comparison": ">=", "value": True}),
        ("count", {"comparison": ">=", "value": 1, "extra": 0}),
        ("all", {"conditions": "rule.objective"}),
        ("any", {"conditions": []}),
        ("not", {"conditions": ["a", "b"]}),
    ),
)
def test_each_mission_operator_has_strict_typed_parameters_and_arity(
    operator: str, parameters: Any
) -> None:
    payload = _scenario()
    condition = payload["mission_rules"][0]["condition"]
    condition["operator"] = operator
    condition["parameters"] = parameters
    _assert_error(payload, "scenario.mission_parameter_invalid", "mission_rules")


def test_missing_mission_dependency_is_distinct_from_cycle() -> None:
    payload = _scenario()
    payload["mission_rules"][0]["depends_on"] = ["rule.missing"]
    _assert_error(payload, "scenario.mission_dependency_missing", "mission_rules")


@pytest.mark.parametrize("value", ("1", True, math.nan, math.inf, -math.inf))
def test_available_scoring_value_is_finite_typed_numeric(value: Any) -> None:
    payload = _scenario()
    metric = payload["scoring"]["metrics"][0]
    metric.update(available=True, value=value)
    _assert_error(payload, "scenario.scoring_value_invalid", "scoring")


def test_unavailable_scoring_metric_cannot_carry_a_value() -> None:
    payload = _scenario()
    payload["scoring"]["metrics"][0].update(available=False, value=0.0)
    _assert_error(payload, "scenario.scoring_na_invalid", "scoring")


@pytest.mark.parametrize("policy", (None, True, "implicit", "autonomous-everything"))
def test_controller_policy_is_a_controlled_string_enum(policy: Any) -> None:
    payload = _scenario()
    payload["controller_policy"] = policy
    _assert_error(payload, "scenario.controller_policy_invalid", "controller_slots")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("action_schema_ref", "action-batch@99.0"),
        ("observation_schema_ref", "observation"),
        ("required_capabilities", ["sensor.arbitrary@2.0.0"]),
    ),
)
def test_controller_schema_and_capability_contracts_are_exact(field: str, value: Any) -> None:
    payload = _scenario()
    payload["controller_slots"][0][field] = value
    code = (
        "scenario.controller_capability_missing"
        if field == "required_capabilities"
        else "scenario.controller_schema_invalid"
    )
    _assert_error(payload, code, "controller_slots")


@pytest.mark.parametrize(
    ("field", "value", "code"),
    (
        ("view", "oracle", "scenario.visibility_view_invalid"),
        ("scope", "everything", "scenario.visibility_scope_invalid"),
        ("allow", "yes", "scenario.visibility_allow_invalid"),
        ("controller_id", "controller.missing", "scenario.visibility_endpoint_missing"),
    ),
)
def test_visibility_fields_are_controlled_and_typed(field: str, value: Any, code: str) -> None:
    payload = _scenario()
    rule = payload["visibility"][3]
    rule[field] = value
    _assert_error(payload, code, "visibility")


def _rehashed_control_json(resolved: Any, mutate: Any) -> str:
    payload: dict[str, Any] = json.loads(resolved.to_json())
    mutate(payload)
    resolved_type: Any = ResolvedScenarioV2
    payload["resolved_hash"] = resolved_type.compute_resolved_hash(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value["mission_rules"][0]["condition"].update(operator="python"),
        lambda value: value["mission_rules"][0]["condition"].update(parameters={}),
        lambda value: value["mission_rules"][0].update(depends_on=["rule.missing"]),
        lambda value: value["mission_rules"][0]["outcome"].update(health=0),
        lambda value: value["mission_rules"][0]["selector_resolution"].update(
            entity_ids=["asset.missing"]
        ),
        lambda value: value["scoring"]["metrics"][0].update(weight=True),
        lambda value: value["scoring"]["metrics"][0].update(available=False, value=0),
        lambda value: value["scoring"]["metrics"][0].update(unit="fortnight"),
        lambda value: value["controller_slots"][0].update(action_schema_ref="action-batch@99.0"),
        lambda value: value["controller_slots"][0].update(required_capabilities=["weapon"]),
        lambda value: value.update(controller_policy="implicit"),
        lambda value: value["visibility"]["matrix"][0].update(view="oracle"),
        lambda value: value["visibility"]["matrix"][0].update(scope="everything"),
        lambda value: value["visibility"]["matrix"][0].update(allow="yes"),
        lambda value: value["visibility"]["matrix"].append(
            copy.deepcopy(value["visibility"]["matrix"][0])
        ),
    ),
)
def test_from_json_revalidates_all_mission_control_semantics(mutate: Any) -> None:
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(_rehashed_control_json(_compile(_scenario()), mutate))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_compile_and_recovery_share_mission_control_semantic_validator() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    routine = "_validate_mission_control_integrity"
    assert f"def {routine}" in source
    assert source.count(f"{routine}(") >= 3


def test_resolved_retains_frozen_declared_mission_states() -> None:
    resolved = _compile(_scenario())
    assert resolved.mission_states == ("state.active", "state.complete")
    with pytest.raises((AttributeError, TypeError)):
        resolved.mission_states += ("state.injected",)


@pytest.mark.parametrize(
    ("states", "code"),
    (
        (["state.active", "state.active"], "scenario.mission_state_duplicate"),
        (["state.active", ""], "scenario.mission_state_invalid"),
        ([], "scenario.mission_state_invalid"),
    ),
)
def test_mission_state_declarations_are_nonempty_unique_identifiers(
    states: list[str], code: str
) -> None:
    payload = _scenario()
    payload["mission_states"] = states
    _assert_error(payload, code, "mission_rules")


def test_state_condition_and_outcome_reference_declared_states() -> None:
    payload = _scenario()
    payload["mission_rules"][0]["condition"].update(
        operator="state", parameters={"state": "state.missing"}
    )
    _assert_error(payload, "scenario.mission_state_reference_missing", "mission_rules")
    payload = _scenario()
    payload["mission_rules"][0]["outcome"]["set_state"] = "state.missing"
    _assert_error(payload, "scenario.mission_state_reference_missing", "mission_rules")


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value["mission_rules"][0]["selector_resolution"].update(
            faction_ids=["faction.beta"]
        ),
        lambda value: value["mission_rules"][0]["condition"]["selector"].update(
            factions=["faction.beta"]
        ),
        lambda value: value["mission_rules"][0]["condition"]["selector"].update(
            zones=["zone.missing"]
        ),
        lambda value: value["mission_rules"][0]["condition"]["selector"].update(
            events=["event.missing"]
        ),
        lambda value: value["scoring"]["metrics"][0]["selector_resolution"].update(
            entity_ids=["asset.missing"]
        ),
        lambda value: value["scoring"]["metrics"][0]["selector"].update(
            domains=["synthetic-surface"]
        ),
        lambda value: value["controller_slots"][0]["selector_resolution"].update(
            entity_ids=["asset.missing"]
        ),
        lambda value: value["controller_slots"][0]["selector"].update(capabilities=["weapon"]),
        lambda value: value.update(mission_states=["state.active"]),
        lambda value: value["mission_rules"][0]["outcome"].update(set_state="state.missing"),
        lambda value: value["mission_rules"][0]["condition"].update(
            operator="state", parameters={"state": "state.missing"}
        ),
    ),
)
def test_outer_rehash_rejects_selector_evidence_and_mission_state_corruption(
    mutate: Any,
) -> None:
    with pytest.raises(ValueError) as captured:
        ResolvedScenarioV2.from_json(_rehashed_control_json(_compile(_scenario()), mutate))
    assert getattr(captured.value, "code", None) == "resolved.integrity_invalid"


def test_raw_selectors_and_resolutions_use_shared_recovery_equivalence_validator() -> None:
    source = Path(declarative_module.__file__).read_text(encoding="utf-8")
    routine = "_validate_selector_resolution_equivalence"
    assert f"def {routine}" in source
    assert source.count(f"{routine}(") >= 4

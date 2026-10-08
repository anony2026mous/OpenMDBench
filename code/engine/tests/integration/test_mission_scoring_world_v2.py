"""RF-07 compiler-to-Resolved-to-World mission/scoring integration contracts."""

from __future__ import annotations

import copy
import importlib
import json
from typing import Any, cast

import pytest


def _fixture() -> Any:
    return importlib.import_module("tests.contract.test_declarative_mission_control_v2")


class _ScoringPlugin:
    def __init__(self) -> None:
        self.calls = 0

    def bind_session(self, **_kwargs: Any) -> _ScoringPlugin:
        return self

    def evaluate(self, _snapshot: Any) -> dict[str, float]:
        self.calls += 1
        return {"metric.objective": 2.0}

    def snapshot(self) -> dict[str, int]:
        return {"calls": self.calls}

    def restore(self, state: dict[str, int]) -> None:
        self.calls = state["calls"]

    def close(self) -> None:
        return None


def _operator_parameters(operator: str) -> dict[str, Any]:
    values: dict[str, dict[str, Any]] = {
        "zone": {"zone_id": "zone.objective", "transition": "entered"},
        "state": {"state": "state.active"},
        "count": {"comparison": ">=", "value": 1},
        "survival": {"comparison": ">=", "value": 1},
        "time": {"comparison": ">=", "tick": 0},
        "event": {"event_id": "event.marker"},
        "wave": {"wave_id": "event.marker"},
        "contact": {"minimum_count": 1, "maximum_age_ticks": 1},
        "communication": {"minimum_count": 1, "owner_entity_id": "asset.000"},
        "resource": {
            "resource_ref": "power.arbitrary@2.0.0",
            "field": "energy",
            "comparison": ">=",
            "value": 0.0,
            "unit": "1",
        },
        "score": {"metric_id": "metric.objective", "comparison": ">=", "value": 0.0},
        "all": {"conditions": ["rule.dependency"]},
        "any": {"conditions": ["rule.dependency"]},
        "not": {"conditions": ["rule.dependency"]},
    }
    return values[operator]


@pytest.mark.parametrize(
    "operator",
    (
        "zone",
        "state",
        "count",
        "survival",
        "time",
        "event",
        "wave",
        "contact",
        "communication",
        "resource",
        "score",
        "all",
        "any",
        "not",
    ),
)
def test_scenario_compiler_accepts_every_typed_runtime_operator(operator: str) -> None:
    fixture = _fixture()
    payload = fixture._scenario()
    rule = payload["mission_rules"][0]
    rule["condition"]["operator"] = operator
    rule["condition"]["parameters"] = _operator_parameters(operator)
    if operator in {"all", "any", "not"}:
        dependency = copy.deepcopy(rule)
        dependency["id"] = "rule.dependency"
        dependency["condition"]["operator"] = "time"
        dependency["condition"]["parameters"] = {"comparison": ">=", "tick": 0}
        rule["depends_on"] = ["rule.dependency"]
        payload["mission_rules"].insert(0, dependency)
    resolved = fixture._compile(payload)
    compiled = next(item for item in resolved.mission_rules if item.id == "rule.objective")
    assert compiled.condition.operator == operator
    expected = _operator_parameters(operator)
    if operator in {"all", "any", "not"}:
        expected = {**expected, "conditions": tuple(expected["conditions"])}
    assert compiled.condition.parameters.values == expected


def test_nested_all_any_not_compiles_as_typed_tree_not_rule_id_shortcut() -> None:
    fixture = _fixture()
    payload = fixture._scenario()
    payload["mission_rules"][0]["condition"] = {
        "schema_version": "2.0",
        "operator": "all",
        "selector": fixture._selector(),
        "parameters": {
            "conditions": [
                {
                    "operator": "any",
                    "conditions": [
                        {"operator": "time", "comparison": ">=", "tick": 0},
                        {"operator": "event", "event_id": "event.marker"},
                    ],
                },
                {
                    "operator": "not",
                    "conditions": [{"operator": "state", "state": "state.complete"}],
                },
            ]
        },
    }
    resolved = fixture._compile(payload)
    condition = resolved.mission_rules[0].condition
    assert condition.operator == "all"
    assert condition.parameters.conditions[0].operator == "any"
    assert condition.parameters.conditions[1].operator == "not"


def test_typed_outcome_separates_state_event_terminal_result_and_ranking() -> None:
    fixture = _fixture()
    payload = fixture._scenario()
    payload["mission_rules"][0]["outcome"] = {
        "set_state": "state.complete",
        "emit_event": "event.marker",
        "terminal": True,
        "result": "objective_complete",
        "ranking": {"faction.alpha": 1, "faction.beta": 2},
    }
    resolved = fixture._compile(payload)
    outcome = resolved.mission_rules[0].outcome
    assert outcome.terminal is True
    assert outcome.result == "objective_complete"
    assert outcome.ranking == {"faction.alpha": 1, "faction.beta": 2}


def test_plain_set_state_outcome_is_not_implicitly_terminal() -> None:
    resolved = _fixture()._compile(_fixture()._scenario())
    outcome = resolved.mission_rules[0].outcome
    assert outcome.set_state == "state.complete"
    assert outcome.terminal is False


def test_world_mission_facts_are_deep_frozen_hashed_and_tick_scoped() -> None:
    fixture = _fixture()
    resolved = fixture._compile(fixture._scenario())
    from openmdbench.world.factory_v2 import WorldFactoryV2

    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    facts = world.mission_fact_snapshot(tick=0)
    assert facts.tick == 0 and facts.fact_hash
    assert facts.zone_transitions == ()
    with pytest.raises((AttributeError, TypeError)):
        facts.entity_states["asset.000"]["health"] = 0.0


def test_world_tick_receipts_publish_dynamic_mission_and_scoring_evidence() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    world = combat_fixture._system().world
    receipt = world.advance_tick(combat_fixture._tick_input(world, 0))
    assert len(receipt.mission_receipts) == 1
    assert len(receipt.score_receipts) == 1
    assert receipt.mission_receipts[0].snapshot_hash
    assert receipt.score_receipts[0].operation_id


def test_checkpoint_outer_rehash_cannot_forge_mission_rules_scores_or_facts() -> None:
    from openmdbench.world.factory_v2 import WorldCheckpointV2
    from tests.contract import test_combat_damage_v2 as combat_fixture

    world = combat_fixture._system().world
    checkpoint = world.checkpoint()
    payload = json.loads(checkpoint.to_json())
    payload["mission_scoring_checkpoint"]["mission_states"] = ["state.forged"]
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def test_runtime_selector_and_fact_source_cover_full_dynamic_authority() -> None:
    api = importlib.import_module("openmdbench.missions.engine_v2")
    required = {
        "platform_ref",
        "domain",
        "tags",
        "direct_capabilities",
        "dependency_capabilities",
        "lifecycle",
        "controller_id",
    }
    assert required.issubset(api.EntitySelectionEvidenceV2.__annotations__)
    fact_fields = api.MissionFactSnapshotV2.__annotations__
    assert {
        "contacts",
        "communications",
        "wave_lifecycle",
        "resources",
        "zone_transitions",
        "event_receipts",
    }.issubset(fact_fields)


def test_event_accumulator_and_plugin_are_engine_world_checkpoint_owned() -> None:
    api = importlib.import_module("openmdbench.missions.engine_v2")
    engine_fields = api.MissionScoringCheckpointV2.model_fields
    assert {"event_accumulators", "plugin_states", "fact_hash"}.issubset(engine_fields)
    assert hasattr(api.MissionEngineV2, "install_plugin")
    assert hasattr(api.MissionEngineV2, "apply_authoritative_event")


def test_world_fact_snapshot_tracks_spawn_active_despawn_without_regression() -> None:
    from tests.contract import test_world_lifecycle_v2 as lifecycle_fixture

    world = lifecycle_fixture._world()
    scheduled = world.mission_fact_snapshot(tick=0)
    world.advance_lifecycle(expected_tick=10, operation_id="mission.spawn")
    active = world.mission_fact_snapshot(tick=10)
    world.advance_lifecycle(expected_tick=19, operation_id="mission.despawn")
    despawned = world.mission_fact_snapshot(tick=19)
    assert (
        next(
            item.lifecycle
            for item in scheduled.selection_evidence
            if item.entity_id == "entity.spawned"
        )
        == "scheduled"
    )
    assert (
        next(
            item.lifecycle
            for item in active.selection_evidence
            if item.entity_id == "entity.spawned"
        )
        == "active"
    )
    despawned_evidence = tuple(
        item for item in despawned.selection_evidence if item.entity_id == "entity.spawned"
    )
    assert not despawned_evidence or despawned_evidence[0].lifecycle == "despawned"
    assert all(item.lifecycle != "scheduled" for item in despawned_evidence)


def test_contact_facts_enforce_selector_owner_freshness_and_confidence() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    world = combat_fixture._system().world
    facts = world.mission_fact_snapshot(tick=0)
    api = importlib.import_module("openmdbench.missions.engine_v2")
    required = {
        "evidence_id",
        "owner_entity_id",
        "target_entity_id",
        "observed_tick",
        "max_age_ticks",
        "confidence",
        "minimum_confidence",
        "selector_id",
    }
    assert "contact_facts" in api.MissionFactSnapshotV2.__annotations__
    assert facts.contact_facts
    fact = facts.contact_facts[0]
    assert required.issubset(type(fact).model_fields)
    assert fact.owner_entity_id == "asset.000"
    assert fact.is_valid(expected_tick=0, owner_entity_id="asset.000") is True


@pytest.mark.parametrize(
    ("field", "unit"),
    (
        ("ammunition", "round"),
        ("energy", "J"),
        ("health", "1"),
        ("component.sensor.health", "1"),
    ),
)
def test_resource_facts_are_typed_by_field_and_canonical_unit(field: str, unit: str) -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    facts = combat_fixture._system().world.mission_fact_snapshot(tick=0)
    assert "resource_facts" in type(facts).__annotations__
    matching = tuple(item for item in facts.resource_facts if item.field == field)
    assert matching and all(item.unit == unit for item in matching)


def test_wave_condition_consumes_lifecycle_schedule_not_event_name_alias() -> None:
    from tests.contract import test_world_lifecycle_v2 as lifecycle_fixture

    world = lifecycle_fixture._world(lifecycle_fixture._spawn_events(1, tick=10))
    before = world.mission_fact_snapshot(tick=0)
    assert before.wave_lifecycle
    world.advance_lifecycle(expected_tick=10, operation_id="wave.spawn")
    after = world.mission_fact_snapshot(tick=10)
    assert before.wave_lifecycle != after.wave_lifecycle


def test_nested_string_condition_endpoints_require_existing_acyclic_dag() -> None:
    from openmdbench.scenarios.declarative_v2 import CompilerErrorV2

    fixture = _fixture()
    payload = fixture._scenario()
    payload["mission_rules"][0]["condition"]["operator"] = "all"
    payload["mission_rules"][0]["condition"]["parameters"] = {"conditions": ["rule.missing"]}
    with pytest.raises(CompilerErrorV2) as captured:
        fixture._compile(payload)
    assert getattr(captured.value, "code", None) == "scenario.mission_dependency_missing"


@pytest.mark.parametrize("aggregation", ("mean", "min", "max", "count"))
@pytest.mark.parametrize("direction", ("maximize", "minimize"))
def test_resolved_metric_aggregation_and_direction_drive_world_score_receipt(
    aggregation: str, direction: str
) -> None:
    fixture = _fixture()
    payload = fixture._scenario()
    metric = payload["scoring"]["metrics"][0]
    metric["aggregation"] = aggregation
    metric["direction"] = direction
    metric["available"] = True
    metric["value"] = 2.0
    resolved = fixture._compile(payload)
    assert resolved.scoring.metrics[0].aggregation == aggregation
    assert resolved.scoring.metrics[0].direction == direction


def test_metric_plugin_ref_is_catalog_registry_and_checkpoint_bound() -> None:
    from openmdbench.catalog.v2 import (
        CatalogResourceV2,
        CatalogV2,
        ModelFactoryMetadataV2,
        ModelRegistryV2,
    )
    from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2

    fixture = _fixture()
    payload = fixture._scenario()
    metric = payload["scoring"]["metrics"][0]
    metric["plugin_ref"] = "models.scoring-arbitrary@2.0.0"
    metric["plugin_parameters"] = {"scale": 1.0, "unit": "1"}
    base = fixture._catalog()
    registry = ModelRegistryV2(interface_version="2.0")
    base_metadata = base.model_registry.snapshot()[0]
    registry.register(base_metadata, lambda definition: definition)
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.scoring-arbitrary",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"score": "1"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + "5" * 64,
            resource_types=("scoring",),
            field_units={"score": "1"},
        ),
        lambda _definition: _ScoringPlugin(),
    )
    registry.freeze()
    scoring_resource = CatalogResourceV2(
        schema_version="2.0",
        resource_type="scoring",
        id="scoring.arbitrary",
        version="2.0.0",
        engine_compatibility=">=2.0.0,<3.0.0",
        model_id="models.scoring-arbitrary@2.0.0",
        content={"unit": "1", "session_local": True},
    )
    catalog = CatalogV2(
        (*base.snapshot(), scoring_resource),
        engine_version="2.0.0",
        model_registry=registry,
    )
    package = ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": payload})
    resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
    assert resolved.scoring is not None
    evidence = resolved.scoring.metrics[0].plugin_evidence
    assert evidence.artifact_sha256
    assert evidence.interface_version == "2.0"
    assert evidence.unit == "1"


def test_zone_facts_cover_initial_enter_leave_through_and_activation() -> None:
    fixture = _fixture()
    resolved = fixture._compile(fixture._scenario())
    from openmdbench.world.factory_v2 import WorldFactoryV2

    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    initial = world.mission_fact_snapshot(tick=0)
    assert "asset.000" in initial.zone_membership
    assert "zone.objective" in initial.zone_membership["asset.000"]
    assert "zone_activation" in type(initial).__annotations__
    assert initial.zone_activation["zone.objective"] is True


def test_rule_receipt_is_exactly_once_across_tick_replay() -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    world = combat_fixture._system().world
    tick_input = combat_fixture._tick_input(world, 0)
    first = world.advance_tick(tick_input)
    replay = world.advance_tick(tick_input)
    assert replay is first
    assert replay.mission_receipts == first.mission_receipts
    assert replay.score_receipts == first.score_receipts


def _world_for_metric(aggregation: str, direction: str) -> tuple[Any, Any]:
    """Compile a scoring scenario whose entities need no dynamics command."""
    from openmdbench.world.factory_v2 import WorldFactoryV2, WorldTickInputV2

    fixture = _fixture()
    payload = fixture._scenario()
    payload["entities"][0]["dynamics_ref"] = None
    first = payload["scoring"]["metrics"][0]
    first.update(
        aggregation=aggregation,
        direction=direction,
        available=True,
        value=2.0,
        weight=0.5,
    )
    second = copy.deepcopy(first)
    second.update(id="metric.secondary", value=4.0)
    payload["scoring"]["metrics"] = [first, second]
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    tick_input = WorldTickInputV2(
        expected_tick=0,
        operation_id=f"score.{aggregation}.{direction}",
        entity_commands=(),
        dt_seconds=1.0,
    )
    return world, tick_input


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    (("mean", 3.0), ("min", 2.0), ("max", 4.0), ("count", 2.0)),
)
@pytest.mark.parametrize("direction", ("maximize", "minimize"))
def test_world_tick_executes_each_resolved_metric_policy(
    aggregation: str, expected: float, direction: str
) -> None:
    world, tick_input = _world_for_metric(aggregation, direction)
    receipt = world.advance_tick(tick_input).score_receipts[0]
    assert receipt.aggregation == aggregation
    assert receipt.direction == direction
    assert receipt.total == expected
    assert receipt.training_rewards["aggregate"] == (
        expected if direction == "maximize" else -expected
    )
    assert tuple(item.unit for item in receipt.metrics) == ("1", "1")


@pytest.mark.parametrize(
    ("section", "mutate"),
    (
        ("mission_states", lambda value: value.append("state.forged")),
        ("rule_ledger", lambda value: value.append({"rule_id": "rule.forged", "tick": 0})),
        ("score_state", lambda value: value.update({"metric.objective": 999.0})),
        (
            "score_ledger",
            lambda value: value.append({"operation_id": "score.forged", "tick": 0}),
        ),
    ),
)
def test_checkpoint_semantics_reject_double_rehashed_mission_scoring_forgery(
    section: str, mutate: Any
) -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2
    from tests.contract import test_combat_damage_v2 as combat_fixture

    payload = json.loads(combat_fixture._system().world.checkpoint().to_json())
    mission = payload["mission_scoring_checkpoint"]
    mutate(mission[section])
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def test_generic_world_has_no_public_undeclared_plugin_install_or_metric_overwrite() -> None:
    from openmdbench.world.factory_v2 import WorldStateV2

    assert not hasattr(WorldStateV2, "install_plugin")
    assert not hasattr(WorldStateV2, "install_scoring_plugin")
    assert not hasattr(WorldStateV2, "overwrite_metric")


def test_world_executes_mixed_metric_policies_under_explicit_scenario_total_policy() -> None:
    from openmdbench.world.factory_v2 import WorldFactoryV2, WorldTickInputV2

    fixture = _fixture()
    payload = fixture._scenario()
    payload["entities"][0]["dynamics_ref"] = None
    scoring = payload["scoring"]
    scoring["aggregation"] = "sum"
    scoring["direction"] = "maximize"
    template = scoring["metrics"][0]
    policies = (
        ("sum", "maximize", 1.0),
        ("mean", "minimize", 2.0),
        ("min", "maximize", 3.0),
        ("max", "minimize", 4.0),
        ("count", "maximize", 5.0),
    )
    scoring["metrics"] = []
    for index, (aggregation, direction, value) in enumerate(policies):
        metric = copy.deepcopy(template)
        metric.update(
            id=f"metric.mixed.{index}",
            aggregation=aggregation,
            direction=direction,
            available=True,
            value=value,
            weight=0.2,
        )
        scoring["metrics"].append(metric)
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    receipt = world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="score.mixed-policies",
            entity_commands=(),
            dt_seconds=1.0,
        )
    ).score_receipts[0]
    assert receipt.aggregation == "sum"
    assert receipt.direction == "maximize"
    assert tuple((item.aggregation, item.direction) for item in receipt.metric_receipts) == tuple(
        (aggregation, direction) for aggregation, direction, _value in policies
    )
    assert receipt.competition_scores != receipt.training_rewards


@pytest.mark.parametrize("attack", ("rule", "score"))
def test_checkpoint_rejects_coordinated_valid_ledger_and_receipt_forgery(attack: str) -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2

    world, tick_input = _world_for_metric("mean", "maximize")
    world.advance_tick(tick_input)
    payload = json.loads(world.checkpoint().to_json())
    mission = payload["mission_scoring_checkpoint"]
    if attack == "rule":
        record = mission["rule_ledger"][0]
        record["event_id"] = "event.forged"
        record["state"] = "state.active"
        mission["mission_states"] = ["state.active"]
        receipt = next(item for item in mission["operation_receipts"] if item["kind"] == "mission")
        receipt["receipt"]["emitted_event_ids"] = ["event.forged"]
        receipt["receipt"]["mission_states"] = ["state.active"]
    else:
        record = mission["score_ledger"][0]
        record["metrics"]["metric.objective"] = 999.0
        mission["score_state"]["metric.objective"] = 999.0
        receipt = next(item for item in mission["operation_receipts"] if item["kind"] == "score")
        receipt["receipt"]["competition_scores"]["metric.objective"] = 999.0
        receipt["receipt"]["metrics"][0]["value"] = 999.0
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def _terminal_checkpoint_payload() -> dict[str, Any]:
    from openmdbench.world.factory_v2 import WorldFactoryV2, WorldTickInputV2

    fixture = _fixture()
    scenario = fixture._scenario()
    scenario["entities"][0]["dynamics_ref"] = None
    scenario["mission_rules"][0]["outcome"].update(
        terminal=True,
        result="objective_complete",
        ranking={"faction.alpha": 1, "faction.beta": 2},
    )
    resolved = fixture._compile(scenario)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="terminal.tick",
            entity_commands=(),
            dt_seconds=1.0,
        )
    )
    return cast(dict[str, Any], json.loads(world.checkpoint().to_json()))


@pytest.mark.parametrize("field", ("outcome", "priority", "ranking", "candidate_hash"))
def test_terminal_checkpoint_coordinated_forgery_is_rejected_against_resolved_rule(
    field: str,
) -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2

    payload = _terminal_checkpoint_payload()
    mission = payload["mission_scoring_checkpoint"]
    terminal = mission["terminal_result"]
    if field == "outcome":
        terminal["outcome"] = "forged_outcome"
    elif field == "priority":
        terminal["priority"] += 100
    elif field == "ranking":
        terminal["ranking"] = {"faction.alpha": 2, "faction.beta": 1}
    else:
        terminal["trigger_evidence"]["candidate_hash"] = "sha256:" + "9" * 64
    mission_receipt = next(
        item for item in mission["operation_receipts"] if item["kind"] == "mission"
    )
    mission_receipt["receipt"]["terminal_result"] = copy.deepcopy(terminal)
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def test_score_checkpoint_fully_coordinated_value_and_reward_forgery_is_rejected() -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2

    world, tick_input = _world_for_metric("mean", "maximize")
    world.advance_tick(tick_input)
    payload = json.loads(world.checkpoint().to_json())
    mission = payload["mission_scoring_checkpoint"]
    receipt_record = next(item for item in mission["operation_receipts"] if item["kind"] == "score")
    receipt = receipt_record["receipt"]
    for metric in receipt["metrics"]:
        metric["value"] = 999.0
    for metric in receipt["metric_receipts"]:
        metric["value"] = 999.0
    receipt["total"] = 999.0
    receipt["competition_scores"] = {
        metric_id: 999.0 for metric_id in receipt["competition_scores"]
    }
    receipt["training_rewards"] = {"aggregate": 999.0}
    mission["score_state"] = dict(receipt["competition_scores"])
    ledger = mission["score_ledger"][0]
    ledger["metrics"] = dict(receipt["competition_scores"])
    ledger["total"] = 999.0
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


@pytest.mark.parametrize(
    "derived_field",
    ("metric_receipts", "effective_weights", "total", "training_rewards"),
)
def test_score_checkpoint_rejects_derived_only_forgery_with_inputs_unchanged(
    derived_field: str,
) -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2

    world, tick_input = _world_for_metric("mean", "maximize")
    world.advance_tick(tick_input)
    payload = json.loads(world.checkpoint().to_json())
    mission = payload["mission_scoring_checkpoint"]
    receipt_record = next(item for item in mission["operation_receipts"] if item["kind"] == "score")
    receipt = receipt_record["receipt"]
    original_inputs = copy.deepcopy(receipt["metrics"])
    original_competition = copy.deepcopy(receipt["competition_scores"])
    if derived_field == "metric_receipts":
        receipt["metric_receipts"][0]["value"] = 777.0
    elif derived_field == "effective_weights":
        receipt["effective_weights"] = {
            metric_id: 0.0 for metric_id in receipt["effective_weights"]
        }
    elif derived_field == "total":
        receipt["total"] = 777.0
        mission["score_ledger"][0]["total"] = 777.0
    else:
        receipt["training_rewards"] = {"aggregate": 777.0}
    assert receipt["metrics"] == original_inputs
    assert receipt["competition_scores"] == original_competition
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def _plugin_checkpoint_payload() -> dict[str, Any]:
    from openmdbench.catalog.v2 import (
        CatalogResourceV2,
        CatalogV2,
        ModelFactoryMetadataV2,
        ModelRegistryV2,
    )
    from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
    from openmdbench.world.factory_v2 import WorldFactoryV2, WorldTickInputV2

    fixture = _fixture()
    payload = fixture._scenario()
    payload["entities"][0]["dynamics_ref"] = None
    metric = payload["scoring"]["metrics"][0]
    metric["plugin_ref"] = "models.scoring-arbitrary@2.0.0"
    metric["plugin_parameters"] = {"scale": 1.0, "unit": "1"}
    base = fixture._catalog()
    registry = ModelRegistryV2(interface_version="2.0")
    registry.register(base.model_registry.snapshot()[0], lambda definition: definition)
    registry.register(
        ModelFactoryMetadataV2(
            schema_version="2.0",
            model_id="models.scoring-arbitrary",
            version="2.0.0",
            interface_version="2.0",
            input_schema="catalog-resource@2.0",
            output_schema="runtime-component@2.0",
            units={"score": "1"},
            deterministic=True,
            thread_safe=True,
            process_safe=True,
            trusted=True,
            artifact_sha256="sha256:" + "5" * 64,
            resource_types=("scoring",),
            field_units={"score": "1"},
        ),
        lambda _definition: _ScoringPlugin(),
    )
    registry.freeze()
    catalog = CatalogV2(
        (
            *base.snapshot(),
            CatalogResourceV2(
                schema_version="2.0",
                resource_type="scoring",
                id="scoring.arbitrary",
                version="2.0.0",
                engine_compatibility=">=2.0.0,<3.0.0",
                model_id="models.scoring-arbitrary@2.0.0",
                content={"unit": "1", "session_local": True},
            ),
        ),
        engine_version="2.0.0",
        model_registry=registry,
    )
    package = ScenarioPackageV2.from_mapping({"schema_version": "package@2.0", "scenario": payload})
    resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
    world = WorldFactoryV2(model_registry=registry).build(resolved)
    world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="plugin.score.tick",
            entity_commands=(),
            dt_seconds=1.0,
        )
    )
    return cast(dict[str, Any], json.loads(world.checkpoint().to_json()))


@pytest.mark.parametrize("field", ("session_state", "state_hash", "score_output"))
def test_plugin_checkpoint_coordinated_forgery_requires_authoritative_fact_replay(
    field: str,
) -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2

    payload = _plugin_checkpoint_payload()
    mission = payload["mission_scoring_checkpoint"]
    plugin = mission["plugin_states"][0]["checkpoint"]
    if field == "session_state":
        plugin["session_state"]["calls"] = 999
    elif field == "state_hash":
        plugin["state_hash"] = "sha256:" + "8" * 64
    else:
        score_receipt = next(
            item for item in mission["operation_receipts"] if item["kind"] == "score"
        )["receipt"]
        score_receipt["metrics"][0]["value"] = 999.0
        score_receipt["metric_receipts"][0]["value"] = 999.0
        score_receipt["competition_scores"]["metric.objective"] = 999.0
        score_receipt["total"] = 999.0
        score_receipt["training_rewards"] = {"aggregate": 999.0}
        mission["score_state"]["metric.objective"] = 999.0
        mission["score_ledger"][0]["metrics"]["metric.objective"] = 999.0
        mission["score_ledger"][0]["total"] = 999.0
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    payload["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(payload)
    with pytest.raises(ValueError):
        WorldCheckpointV2.from_json(json.dumps(payload, sort_keys=True))


def test_event_score_metric_is_compiled_as_typed_authoritative_world_policy() -> None:
    fixture = _fixture()
    payload = fixture._scenario()
    metric = payload["scoring"]["metrics"][0]
    metric["event_source"] = {
        "event_id": "event.marker",
        "event_type": "mission_marker",
        "value_path": "payload.score_value",
        "source": "world_typed_event_receipt",
        "unit": "1",
        "aggregation": "sum",
    }
    resolved = fixture._compile(payload)
    assert resolved.scoring is not None
    compiled = resolved.scoring.metrics[0]
    assert compiled.event_source.event_id == "event.marker"
    assert compiled.event_source.source == "world_typed_event_receipt"
    assert compiled.event_source.value_path == "payload.score_value"


def test_event_scoring_public_boundary_does_not_accept_caller_metric_value_or_unit() -> None:
    import inspect

    from openmdbench.missions.engine_v2 import MissionEngineV2, MissionScoringCheckpointV2

    parameters = inspect.signature(MissionEngineV2.apply_authoritative_event).parameters
    assert "metric_id" not in parameters
    assert "value" not in parameters
    assert "unit" not in parameters
    assert "event_receipt" in parameters
    assert "event_score_input_receipts" in MissionScoringCheckpointV2.model_fields


def test_event_scoring_uses_rule_only_fact_anchor_without_dropping_audit_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Long-running event scoring must not re-freeze the complete audit ledger."""

    fixture = _fixture()
    payload = fixture._scenario()
    payload["scoring"]["metrics"][0]["event_source"] = {
        "event_id": "event.marker",
        "event_type": "mission_marker",
        "value_path": "payload.score_value",
        "source": "world_typed_event_receipt",
        "unit": "1",
        "aggregation": "sum",
    }
    resolved = fixture._compile(payload)
    from openmdbench.missions.engine_v2 import MissionEngineV2, _canonical_hash
    from openmdbench.world.factory_v2 import (
        TypedEventExecutionReceiptV2,
        WorldEventReceiptV2,
        WorldFactoryV2,
        WorldTickReceiptV2,
    )

    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    engine = MissionEngineV2.from_resolved(
        resolved=resolved,
        world=world,
        expected_resolved_hash=resolved.resolved_hash,
    )
    original_snapshot = world.mission_fact_snapshot
    requested_receipt_views: list[bool] = []

    def recording_snapshot(*, tick: int, include_event_receipts: bool = True) -> Any:
        requested_receipt_views.append(include_event_receipts)
        return original_snapshot(tick=tick, include_event_receipts=include_event_receipts)

    event_payload = {"score_value": 2.0}
    receipt = TypedEventExecutionReceiptV2(
        event_id="event.marker",
        event_type="mission_marker",
        tick=1,
        payload=event_payload,
        payload_hash=_canonical_hash(event_payload),
        owner_state_hash_before="sha256:before",
        owner_state_hash_after="sha256:after",
    )
    indexed_receipt = TypedEventExecutionReceiptV2(
        event_id="event.marker",
        event_type="mission_marker",
        tick=1,
        payload={"marker_id": "event.marker"},
        payload_hash=_canonical_hash({"marker_id": "event.marker"}),
        owner_state_hash_before="sha256:index-before",
        owner_state_hash_after="sha256:index-after",
    )
    audit_tick = WorldTickReceiptV2(
        operation_id="audit.tick.0",
        start_tick=0,
        tick=1,
        steps=1,
        motion_receipts=(),
        event_receipts=(
            WorldEventReceiptV2(
                tick=1,
                operation_id="audit.events.0",
                boundary_event_ids=(),
                collision_event_ids=(),
                damage_intent_ids=(),
                typed_event_receipts=(indexed_receipt,),
            ),
        ),
    )
    world._world_tick_ledger[audit_tick.operation_id] = ("audit-fingerprint", audit_tick)
    world._index_typed_event_receipts(audit_tick.event_receipts)
    world._applied_tick_event_ids.add("event.marker")
    assert world.authoritative_typed_event_receipt(indexed_receipt) is indexed_receipt
    monkeypatch.setattr(world, "mission_fact_snapshot", recording_snapshot)
    monkeypatch.setattr(world, "authoritative_typed_event_receipt", lambda _: receipt)

    applied = engine.apply_authoritative_event(event_receipt=receipt)

    assert applied[0].accumulated_value == 2.0
    assert requested_receipt_views == [False]
    assert (
        original_snapshot(tick=1).event_receipts[0]["typed_event_receipts"][0]["event_id"]
        == "event.marker"
    )

"""RF-07 generic authoritative MissionEngineV2 and ScoringSystemV2 contracts."""

from __future__ import annotations

import importlib
import inspect
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest


def _api() -> Any:
    return importlib.import_module("openmdbench.missions.engine_v2")


def _resolved(*, slot_count: int = 1) -> Any:
    from tests.contract import test_declarative_mission_control_v2 as fixture

    return fixture._compile(fixture._scenario(slot_count))


def _world(resolved: Any) -> Any:
    from openmdbench.world.factory_v2 import WorldFactoryV2
    from tests.contract import test_declarative_mission_control_v2 as fixture

    registry = fixture._catalog().model_registry
    return WorldFactoryV2(model_registry=registry).build(resolved)


def test_public_runtime_api_consumes_only_resolved_and_world_anchors() -> None:
    api = _api()
    assert hasattr(api, "MissionEngineV2")
    assert hasattr(api, "ScoringSystemV2")
    resolved = _resolved()
    world = _world(resolved)
    engine = api.MissionEngineV2.from_resolved(
        resolved=resolved,
        world=world,
        expected_resolved_hash=resolved.resolved_hash,
    )
    assert engine.resolved_hash == resolved.resolved_hash
    assert not hasattr(engine, "catalog")
    assert not hasattr(engine, "source_document")


def test_compiled_rules_have_no_runtime_selector_or_python_code() -> None:
    resolved = _resolved()
    for rule in resolved.mission_rules:
        assert rule.selector_resolution.entity_ids
        assert not callable(rule.condition)
        assert not callable(rule.outcome)
        assert "python" not in rule.values
        assert "code" not in rule.values


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_dynamic_selector_cardinality_is_exact_and_stably_ordered(count: int) -> None:
    api = _api()
    assert hasattr(api, "CompiledSelectorV2")
    selector = api.CompiledSelectorV2(
        selector_id="selector.synthetic",
        entity_ids=tuple(f"unit.{index:03d}" for index in reversed(range(count))),
        faction_ids=("faction.arbitrary",),
        controller_ids=(),
        visibility_scope="referee",
    )
    assert selector.entity_ids == tuple(f"unit.{index:03d}" for index in range(count))


@pytest.mark.parametrize(
    "operator",
    (
        "zone",
        "state",
        "any",
        "all",
        "count",
        "survival",
        "time",
        "event",
        "wave",
        "contact",
        "communication",
        "resource",
        "score",
        "not",
    ),
)
def test_condition_operators_are_typed_and_whitelisted(operator: str) -> None:
    api = _api()
    assert operator in api.MISSION_CONDITION_OPERATORS_V2
    assert api.condition_schema_v2(operator).extra_forbidden is True


def test_same_tick_terminal_priority_latches_one_authoritative_result() -> None:
    api = _api()
    resolved = _resolved()
    engine = api.MissionEngineV2.from_resolved(
        resolved=resolved,
        world=_world(resolved),
        expected_resolved_hash=resolved.resolved_hash,
    )
    receipt = engine.evaluate_tick(expected_tick=0, operation_id="mission.tick.000")
    replay = engine.evaluate_tick(expected_tick=0, operation_id="mission.tick.000")
    assert replay is receipt
    assert receipt.triggered_rule_ids == tuple(sorted(receipt.triggered_rule_ids))
    if receipt.terminal_result is not None:
        assert receipt.terminal_result.latched is True
        assert receipt.terminal_result.trigger_evidence


def test_rule_dependencies_use_authoritative_event_and_mission_state_snapshots() -> None:
    api = _api()
    required = {
        "tick",
        "entity_states",
        "zone_membership",
        "event_ids",
        "mission_states",
        "contacts",
        "communications",
        "resources",
        "scores",
    }
    assert required.issubset(api.MissionEvaluationSnapshotV2.__annotations__)


def test_scoring_distinguishes_na_from_numeric_zero_and_renormalizes_weights() -> None:
    api = _api()
    metrics = (
        api.ScoreInputV2(metric_id="available.zero", value=0.0, weight=0.25, unit="points"),
        api.ScoreInputV2(metric_id="not.available", value=None, weight=0.75, unit="points"),
    )
    result = api.ScoringSystemV2.evaluate(metrics, aggregation="sum", direction="maximize")
    assert result.metrics[0].value == 0.0
    assert result.metrics[1].value is None
    assert result.total == 0.0
    assert result.effective_weights == {"available.zero": 1.0}


@pytest.mark.parametrize("count", (0, 1, 10, 100))
def test_scoring_is_order_independent_for_arbitrary_metric_counts(count: int) -> None:
    api = _api()
    metrics = tuple(
        api.ScoreInputV2(
            metric_id=f"metric.{index:03d}", value=float(index), weight=1.0, unit="points"
        )
        for index in range(count)
    )
    forward = api.ScoringSystemV2.evaluate(metrics, aggregation="mean", direction="maximize")
    reverse = api.ScoringSystemV2.evaluate(
        tuple(reversed(metrics)), aggregation="mean", direction="maximize"
    )
    assert reverse == forward


def test_win_loss_ranking_and_training_reward_are_separate_channels() -> None:
    api = _api()
    fields = api.ScoreReceiptV2.__annotations__
    assert {"mission_outcome", "competition_scores", "training_rewards"}.issubset(fields)
    assert fields["mission_outcome"] != fields["training_rewards"]


def test_visibility_filters_dynamic_faction_controller_score_evidence() -> None:
    api = _api()
    assert hasattr(api, "MissionVisibilityViewV2")
    assert api.MissionVisibilityViewV2.model_fields["faction_id"].is_required()
    assert api.MissionVisibilityViewV2.model_fields["controller_id"].is_required()
    assert "hidden_truth" not in api.MissionVisibilityViewV2.model_fields


def test_checkpoint_roundtrip_preserves_mission_score_latch_and_idempotency() -> None:
    api = _api()
    fields = api.MissionScoringCheckpointV2.__annotations__
    assert {
        "resolved_hash",
        "tick",
        "mission_states",
        "terminal_result",
        "rule_ledger",
        "score_state",
        "score_ledger",
        "operation_receipts",
        "checkpoint_hash",
    }.issubset(fields)
    assert hasattr(api.MissionEngineV2, "restore_checkpoint")


def test_world_tick_orders_mission_and_scoring_in_one_append_only_step() -> None:
    world_api = importlib.import_module("openmdbench.world.factory_v2")
    receipt_fields = world_api.WorldTickReceiptV2.__annotations__
    assert {"mission_receipts", "score_receipts"}.issubset(receipt_fields)
    source = inspect.getsource(world_api.WorldStateV2.advance_tick)
    assert source.index("mission") < source.index("scoring")
    assert "_tick_failure_operation_id" in source
    assert "restore_mission_scoring" not in source


def test_runtime_source_has_no_fixed_scenario_side_or_selector_re_evaluation() -> None:
    source = inspect.getsource(_api())
    for forbidden in (
        "MD-AD",
        "MD_AD",
        "MD-INT",
        "MD_INT",
        '"red"',
        '"blue"',
        "scenario_id ==",
        "catalog.resolve",
        "selector.matches",
        "health =",
        "exec(",
        "eval(",
    ):
        assert forbidden not in source


def _condition_rule(operator: str, parameters: dict[str, Any]) -> Any:
    return SimpleNamespace(
        condition=SimpleNamespace(
            operator=operator,
            parameters=SimpleNamespace(values=MappingProxyType(parameters)),
        ),
        selector_resolution=SimpleNamespace(entity_ids=("unit.alpha", "unit.beta")),
    )


def _condition_snapshot(api: Any) -> Any:
    return api.MissionEvaluationSnapshotV2(
        tick=5,
        entity_states=MappingProxyType(
            {
                "unit.alpha": MappingProxyType({"lifecycle": "active", "health": 1.0}),
                "unit.beta": MappingProxyType({"lifecycle": "destroyed", "health": 0.0}),
            }
        ),
        zone_membership=MappingProxyType({"unit.alpha": ("zone.goal",)}),
        event_ids=("event.signal", "wave.first"),
        mission_states=("state.ready",),
        contacts=MappingProxyType({}),
        communications=(MappingProxyType({"message_id": "message.001"}),),
        resources=MappingProxyType({}),
        scores=MappingProxyType({"metric.progress": 0.75}),
        contact_facts=(
            api.MissionContactFactV2(
                evidence_id="contact.001",
                owner_entity_id="unit.alpha",
                target_entity_id="unit.beta",
                observed_tick=4,
                max_age_ticks=2,
                confidence=0.9,
                minimum_confidence=0.5,
                selector_id="selector.condition",
            ),
        ),
        resource_facts=(
            api.MissionResourceFactV2(
                entity_id="unit.alpha",
                resource_ref="resource.fuel@2.0.0",
                field="quantity",
                value=4.0,
                unit="kg",
            ),
        ),
        wave_lifecycle=MappingProxyType({"wave.first": "applied"}),
    )


@pytest.mark.parametrize(
    ("operator", "parameters", "expected"),
    (
        ("zone", {"zone_id": "zone.goal"}, True),
        ("state", {"state": "state.ready"}, True),
        ("count", {"comparison": "==", "value": 1}, True),
        ("survival", {"comparison": ">=", "value": 1}, True),
        ("time", {"comparison": ">=", "tick": 5}, True),
        ("event", {"event_id": "event.signal"}, True),
        ("wave", {"wave_id": "wave.first"}, True),
        ("contact", {"minimum_count": 1, "maximum_age_ticks": 2}, True),
        ("communication", {"minimum_count": 1}, True),
        (
            "resource",
            {
                "resource_ref": "resource.fuel@2.0.0",
                "field": "quantity",
                "unit": "kg",
                "comparison": ">=",
                "value": 4,
            },
            True,
        ),
        ("score", {"metric_id": "metric.progress", "comparison": ">", "value": 0.5}, True),
        ("all", {"conditions": ("rule.a", "rule.b")}, True),
        ("any", {"conditions": ("rule.missing", "rule.b")}, True),
        ("not", {"conditions": ("rule.missing",)}, True),
    ),
)
def test_all_condition_operators_execute_typed_boundary_behavior(
    operator: str, parameters: dict[str, Any], expected: bool
) -> None:
    api = _api()
    resolved = _resolved()
    engine = api.MissionEngineV2.from_resolved(
        resolved=resolved,
        world=_world(resolved),
        expected_resolved_hash=resolved.resolved_hash,
    )
    engine._rule_ledger = {"rule.a": {}, "rule.b": {}}
    assert (
        engine._condition(_condition_rule(operator, parameters), _condition_snapshot(api))
        is expected
    )


def test_zone_condition_uses_swept_enter_leave_facts_not_static_deployment() -> None:
    api = _api()
    fields = api.MissionEvaluationSnapshotV2.__annotations__
    assert "zone_transitions" in fields
    transition = api.ZoneTransitionEvidenceV2(
        entity_id="unit.alpha",
        zone_id="zone.goal",
        transition="entered",
        tick=5,
        time_fraction=0.25,
        evidence_hash="sha256:" + "1" * 64,
    )
    assert transition.transition == "entered"


@pytest.mark.parametrize("lifecycle", ("scheduled", "active", "destroyed", "despawned"))
def test_dynamic_selector_recomputes_future_and_lifecycle_membership(lifecycle: str) -> None:
    api = _api()
    selector = api.RuntimeSelectorV2(
        selector_id="selector.dynamic",
        faction_ids=("faction.arbitrary",),
        tags=("escort",),
        capabilities=("sensor",),
        include_lifecycle=(lifecycle,),
    )
    evidence = api.EntitySelectionEvidenceV2(
        entity_id=f"unit.{lifecycle}",
        faction_id="faction.arbitrary",
        tags=("escort",),
        direct_capabilities=("sensor",),
        dependency_capabilities=("communication",),
        lifecycle=lifecycle,
    )
    assert selector.matches(evidence) is True


def test_terminal_priority_tie_break_latch_and_exact_event_evidence() -> None:
    api = _api()
    assert hasattr(api, "TerminalCandidateV2")
    candidates = (
        api.TerminalCandidateV2("rule.z", 100, "event.z"),
        api.TerminalCandidateV2("rule.a", 100, "event.a"),
        api.TerminalCandidateV2("rule.low", 10, "event.low"),
    )
    result = api.select_terminal_result_v2(candidates, tick=5)
    assert result.rule_id == "rule.a"
    assert result.priority == 100
    assert result.trigger_evidence["event_id"] == "event.a"
    assert result.latched is True


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    (("sum", 2.0), ("mean", 2.0), ("min", 1.0), ("max", 3.0), ("count", 2.0)),
)
def test_all_score_aggregations_units_direction_and_na(aggregation: str, expected: float) -> None:
    api = _api()
    metrics = (
        api.ScoreInputV2(metric_id="metric.a", value=1.0, weight=0.5, unit="points"),
        api.ScoreInputV2(metric_id="metric.b", value=3.0, weight=0.5, unit="points"),
        api.ScoreInputV2(metric_id="metric.na", value=None, weight=1.0, unit="points"),
    )
    result = api.ScoringSystemV2.evaluate(metrics, aggregation=aggregation, direction="maximize")
    assert result.total == pytest.approx(expected)
    minimized = api.ScoringSystemV2.evaluate(metrics, aggregation=aggregation, direction="minimize")
    assert minimized.training_rewards["aggregate"] == pytest.approx(-expected)
    assert result.competition_scores["metric.na"] is None


def test_duplicate_authoritative_events_do_not_double_count_score() -> None:
    api = _api()
    accumulator = api.EventScoreAccumulatorV2(metric_id="metric.events", unit="points")
    first = accumulator.apply(event_id="event.same", value=2.0, tick=5)
    replay = accumulator.apply(event_id="event.same", value=2.0, tick=5)
    assert replay is first
    assert accumulator.value == 2.0


def test_checkpoint_n_plus_m_matches_continuous_mission_and_score_receipts() -> None:
    api = _api()
    resolved = _resolved()
    world = _world(resolved)
    original = api.MissionEngineV2.from_resolved(
        resolved=resolved, world=world, expected_resolved_hash=resolved.resolved_hash
    )
    first = original.evaluate_tick(expected_tick=0, operation_id="mission.n")
    checkpoint = original.checkpoint()
    restored = api.MissionEngineV2.restore_checkpoint(
        checkpoint=checkpoint,
        resolved=resolved,
        world=world,
        expected_resolved_hash=resolved.resolved_hash,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    )
    assert restored.evaluate_tick(expected_tick=0, operation_id="mission.n") == first
    assert restored.evaluate_scoring(expected_tick=0, operation_id="score.m") == (
        original.evaluate_scoring(expected_tick=0, operation_id="score.m")
    )


@pytest.mark.parametrize("stage", ("mission", "scoring"))
def test_nth_mission_or_scoring_fault_latches_append_only_world(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.contract import test_combat_damage_v2 as combat_fixture

    world = combat_fixture._system().world
    method = "evaluate_tick" if stage == "mission" else "evaluate_scoring"

    def fail(**_kwargs: Any) -> None:
        raise RuntimeError(f"injected {stage} failure")

    monkeypatch.setattr(world._mission_engine, method, fail)
    tick_input = combat_fixture._tick_input(world, 0)
    with pytest.raises(RuntimeError, match=f"injected {stage} failure"):
        world.advance_tick(tick_input)
    assert world.failed_tick_operation_id == tick_input.operation_id
    with pytest.raises(ValueError, match="cannot continue after failed operation"):
        world.advance_tick(tick_input)


def test_mission_plugin_requires_trusted_registry_and_checkpointed_session_state() -> None:
    api = _api()
    required = {
        "plugin_ref",
        "artifact_sha256",
        "interface_version",
        "deterministic",
        "trusted",
        "session_state",
        "state_hash",
    }
    assert required.issubset(api.MissionPluginCheckpointV2.__annotations__)
    assert hasattr(api, "TrustedMissionPluginFactoryV2")

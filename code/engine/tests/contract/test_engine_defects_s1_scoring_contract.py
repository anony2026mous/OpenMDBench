"""EF-02 S1 utility scoring contract tests."""

from __future__ import annotations

import copy
import json
from typing import Any, Literal

import pytest
from openmdbench.missions.engine_v2 import ScoreInputV2, ScoringSystemV2
from openmdbench.scenarios.declarative_v2 import CompilerErrorV2

UTILITY_V1 = "utility-v1"


def _metric(
    metric_id: str,
    raw_value: float | None,
    *,
    weight: float,
    direction: Literal["maximize", "minimize"],
    lower: float = 0.0,
    upper: float = 1.0,
    missing_inputs: tuple[str, ...] = (),
) -> ScoreInputV2:
    return ScoreInputV2(
        metric_id=metric_id,
        value=raw_value,
        weight=weight,
        unit="1",
        direction=direction,
        normalization_lower_bound=lower,
        normalization_upper_bound=upper,
        missing_inputs=missing_inputs,
        missing_evidence_source=("sha256:" + "a" * 64 if missing_inputs else None),
    )


def test_utility_v1_normalizes_mixed_directions_and_never_flips_reward() -> None:
    receipt = ScoringSystemV2.evaluate(
        (
            _metric("score.denial", 1.0, weight=0.6, direction="minimize", upper=4.0),
            _metric("score.efficiency", 0.5, weight=0.2, direction="maximize"),
            _metric("score.survival", 1.0, weight=0.2, direction="maximize"),
        ),
        aggregation="sum",
        direction="maximize",
        aggregation_version=UTILITY_V1,
    )

    assert receipt.aggregation_version == UTILITY_V1
    assert receipt.total == pytest.approx(0.75)
    assert receipt.training_rewards["aggregate"] == pytest.approx(receipt.total)
    assert receipt.competition_scores == {
        "score.denial": pytest.approx(0.75),
        "score.efficiency": pytest.approx(0.5),
        "score.survival": pytest.approx(1.0),
    }
    denial = next(item for item in receipt.metric_receipts if item.metric_id == "score.denial")
    assert denial.raw_value == 1.0
    assert denial.utility_value == pytest.approx(0.75)
    assert denial.effective_weight == pytest.approx(0.6)
    assert denial.weighted_contribution == pytest.approx(0.45)
    assert denial.aggregation_version == UTILITY_V1


def test_utility_v1_reweights_na_and_records_missing_and_out_of_range() -> None:
    receipt = ScoringSystemV2.evaluate(
        (
            _metric("score.denial", 5.0, weight=0.6, direction="minimize", upper=4.0),
            _metric("score.na", None, weight=0.2, direction="maximize"),
            _metric(
                "score.missing",
                0.0,
                weight=0.2,
                direction="maximize",
                missing_inputs=("world.authoritative.metric",),
            ),
        ),
        aggregation="sum",
        direction="maximize",
        aggregation_version=UTILITY_V1,
    )

    assert receipt.total == 0.0
    assert receipt.effective_weights == {
        "score.denial": pytest.approx(0.75),
        "score.missing": pytest.approx(0.25),
    }
    assert receipt.competition_scores["score.na"] is None
    assert receipt.metric_data_missing[0].metric_id == "score.missing"
    assert receipt.metric_value_out_of_range[0].metric_id == "score.denial"
    assert receipt.metric_value_out_of_range[0].raw_value == 5.0
    missing = next(item for item in receipt.metric_receipts if item.metric_id == "score.missing")
    assert missing.utility_value == 0.0


def test_utility_v1_requires_weighted_sum_and_maximize_total_direction() -> None:
    metrics = (_metric("score.metric", 0.5, weight=1.0, direction="maximize"),)
    with pytest.raises(ValueError, match="utility-v1"):
        ScoringSystemV2.evaluate(
            metrics,
            aggregation="mean",
            direction="maximize",
            aggregation_version=UTILITY_V1,
        )
    with pytest.raises(ValueError, match="utility-v1"):
        ScoringSystemV2.evaluate(
            metrics,
            aggregation="sum",
            direction="minimize",
            aggregation_version=UTILITY_V1,
        )


def test_legacy_receipt_is_explicitly_marked_and_retains_legacy_semantics() -> None:
    receipt = ScoringSystemV2.evaluate(
        (ScoreInputV2(metric_id="legacy.metric", value=2.0, weight=1.0, unit="points"),),
        aggregation="sum",
        direction="minimize",
    )

    assert receipt.aggregation_version == "legacy-v1"
    assert receipt.total == 2.0
    assert receipt.training_rewards["aggregate"] == -2.0
    assert receipt.metric_receipts[0].utility_value is None


def _utility_scenario(*, required: bool, selector: dict[str, Any] | None = None) -> dict[str, Any]:
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = fixture._scenario()
    scoring = payload["scoring"]
    scoring.update(aggregation_version=UTILITY_V1, aggregation="sum", direction="maximize")
    metric = scoring["metrics"][0]
    metric.update(
        aggregation="count",
        direction="minimize",
        available=True,
        value=0.0,
        required=required,
        normalization={"lower_bound": 0.0, "upper_bound": "selector_cardinality"},
    )
    if selector is not None:
        metric["selector"] = selector
    return payload


def test_compiler_resolves_selector_cardinality_without_hard_coded_denial_limit() -> None:
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = _utility_scenario(required=True)
    payload["entities"].extend(
        [
            fixture._entity("asset.001"),
            fixture._entity("asset.002"),
            fixture._entity("asset.003"),
        ]
    )
    payload["scoring"]["metrics"][0]["selector"] = {
        **payload["scoring"]["metrics"][0]["selector"],
        "entity_ids": ["asset.000", "asset.001", "asset.002", "asset.003"],
    }
    resolved = fixture._compile(payload)

    metric = resolved.scoring.metrics[0]
    assert resolved.scoring.aggregation_version == UTILITY_V1
    assert metric.normalization.upper_bound == 4.0
    assert metric.normalization.lower_bound == 0.0


@pytest.mark.parametrize(("raw_denial", "expected"), ((0.0, 1.0), (1.0, 0.0)))
def test_world_scoring_uses_the_compiled_utility_contract(
    raw_denial: float, expected: float
) -> None:
    from openmdbench.world.factory_v2 import WorldFactoryV2, WorldTickInputV2
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = _utility_scenario(required=True)
    payload["entities"][0]["dynamics_ref"] = None
    payload["scoring"]["metrics"][0]["value"] = raw_denial
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)

    receipt = world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id=f"utility.denial.{raw_denial}",
            entity_commands=(),
            dt_seconds=1.0,
        )
    ).score_receipts[0]
    assert receipt.aggregation_version == UTILITY_V1
    assert receipt.total == pytest.approx(expected)
    assert receipt.competition_scores["metric.objective"] == pytest.approx(expected)
    assert receipt.training_rewards["aggregate"] == pytest.approx(expected)


def test_utility_checkpoint_recomputes_score_evidence_on_read() -> None:
    from openmdbench.world.factory_v2 import WorldCheckpointV2, WorldFactoryV2, WorldTickInputV2
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = _utility_scenario(required=True)
    payload["entities"][0]["dynamics_ref"] = None
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="utility.checkpoint",
            entity_commands=(),
            dt_seconds=1.0,
        )
    )

    checkpoint = WorldCheckpointV2.from_json(world.checkpoint().to_json())
    assert checkpoint.mission_scoring_checkpoint is not None
    assert (
        checkpoint.mission_scoring_checkpoint["resolved_scoring"]["aggregation_version"]
        == UTILITY_V1
    )


def test_utility_score_output_is_not_reused_as_the_next_tick_raw_input() -> None:
    """A presentation utility must never feed back into a raw metric source."""

    from openmdbench.world.factory_v2 import WorldCheckpointV2, WorldFactoryV2, WorldTickInputV2
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = _utility_scenario(required=True)
    payload["entities"][0]["dynamics_ref"] = None
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)

    first = world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="utility.presentation.0",
            entity_commands=(),
            dt_seconds=1.0,
        )
    ).score_receipts[0]
    second = world.advance_tick(
        WorldTickInputV2(
            expected_tick=1,
            operation_id="utility.presentation.1",
            entity_commands=(),
            dt_seconds=1.0,
        )
    ).score_receipts[0]

    assert first.metrics[0].value == second.metrics[0].value == 0.0
    assert first.competition_scores == second.competition_scores
    checkpoint = WorldCheckpointV2.from_json(world.checkpoint().to_json())
    assert checkpoint.tick == 2


def test_legacy_checkpoint_without_utility_fields_remains_detectably_legacy() -> None:
    from openmdbench.missions.engine_v2 import MissionScoringCheckpointV2
    from openmdbench.world.factory_v2 import WorldCheckpointV2, WorldFactoryV2, WorldTickInputV2
    from tests.contract import test_declarative_mission_control_v2 as fixture

    payload = fixture._scenario()
    payload["entities"][0]["dynamics_ref"] = None
    resolved = fixture._compile(payload)
    world = WorldFactoryV2(model_registry=fixture._catalog().model_registry).build(resolved)
    world.advance_tick(
        WorldTickInputV2(
            expected_tick=0,
            operation_id="legacy.checkpoint",
            entity_commands=(),
            dt_seconds=1.0,
        )
    )
    raw = json.loads(world.checkpoint().to_json())
    mission = raw["mission_scoring_checkpoint"]
    score = next(item for item in mission["operation_receipts"] if item["kind"] == "score")[
        "receipt"
    ]
    score.pop("aggregation_version")
    score.pop("metric_value_out_of_range")
    for metric in score["metrics"]:
        metric.pop("normalization_lower_bound")
        metric.pop("normalization_upper_bound")
        metric.pop("not_applicable_reason")
    for metric_receipt in score["metric_receipts"]:
        for field in (
            "raw_value",
            "utility_value",
            "effective_weight",
            "weighted_contribution",
            "aggregation_version",
            "not_applicable_reason",
        ):
            metric_receipt.pop(field)
    mission["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(mission)
    raw["checkpoint_hash"] = WorldCheckpointV2.compute_checkpoint_hash(raw)

    restored = WorldCheckpointV2.from_json(json.dumps(raw, sort_keys=True))
    assert restored.mission_scoring_checkpoint is not None
    receipt = next(
        item["receipt"]
        for item in restored.mission_scoring_checkpoint["operation_receipts"]
        if item["kind"] == "score"
    )
    assert "aggregation_version" not in receipt


@pytest.mark.parametrize("required", (False, True))
def test_compiler_marks_optional_zero_cardinality_na_or_rejects_required_metric(
    required: bool,
) -> None:
    from tests.contract import test_declarative_mission_control_v2 as fixture

    empty_selector = copy.deepcopy(fixture._selector())
    empty_selector.pop("entity_ids")
    empty_selector["factions"] = ["faction.beta"]
    payload = _utility_scenario(required=required, selector=empty_selector)

    if required:
        with pytest.raises(CompilerErrorV2, match="required"):
            fixture._compile(payload)
    else:
        resolved = fixture._compile(payload)
        metric = resolved.scoring.metrics[0]
        assert metric.available is False
        assert metric.value is None
        assert metric.not_applicable_reason == "selector_cardinality_zero"

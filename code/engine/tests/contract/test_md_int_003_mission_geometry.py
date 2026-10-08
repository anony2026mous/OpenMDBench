"""MD3-05 generic contact guidance, geometry, and score-audit contracts."""

from __future__ import annotations

import importlib
import inspect
from typing import Any

import pytest


def _geometry() -> Any:
    return importlib.import_module("openmdbench.world.interdiction_geometry_v2")


def _sdk() -> Any:
    return importlib.import_module("openmdbench.sdk.intercept_v2")


def test_public_intercept_helper_emits_navigation_evidence_without_world_dependency() -> None:
    api = _sdk()
    proposal = api.predict_intercept_waypoint(
        contact=api.PublicContactEstimateV2(
            contact_id="contact.opaque.track",
            position_m=(100.0, 100.0, 0.0),
            velocity_mps=(0.0, 5.0, 0.0),
            observed_tick=7,
            valid_until_tick=10,
            confidence=0.8,
        ),
        interceptor=api.InterceptorCapabilityV2(
            entity_id="unit.arbitrary.interceptor",
            position_m=(0.0, 0.0, 0.0),
            maximum_speed_mps=30.0,
            preferred_speed_mps=25.0,
        ),
        standoff_m=10.0,
        region=api.InterceptRegionV2(center_m=(100.0, 100.0, 0.0), radius_m=300.0),
    )
    assert proposal.contact_id == "contact.opaque.track"
    assert proposal.suggested_speed_mps == 25.0
    assert 0.0 <= proposal.suggested_heading_deg < 360.0
    source = inspect.getsource(api)
    assert "openmdbench.world" not in source
    assert "factory_v2" not in source


def test_annular_sector_and_radial_crossing_are_continuous_and_wrap_zero_degrees() -> None:
    api = _geometry()
    sector = api.AnnularSectorV2(
        center_m=(0.0, 0.0),
        inner_radius_m=5.0,
        outer_radius_m=10.0,
        start_bearing_deg=350.0,
        end_bearing_deg=10.0,
        direction="clockwise",
    )
    assert sector.contains((0.0, 8.0)) is True
    assert sector.contains((4.0, 8.0)) is False
    occupancy = api.annular_sector_occupancy(
        subject_id="unit.renamed.alpha",
        tick=3,
        start_m=(-2.0, 8.0),
        end_m=(2.0, 8.0),
        sector=sector,
        dt_seconds=2.0,
    )
    assert 0.0 < occupancy.duration_seconds < 2.0
    crossings = api.radial_crossings(
        start_m=(-2.0, 5.0),
        end_m=(2.0, 5.0),
        center_m=(0.0, 0.0),
        bearing_deg=0.0,
        minimum_radius_m=1.0,
        maximum_radius_m=10.0,
    )
    assert crossings[0].time_fraction == pytest.approx(0.5)
    assert crossings[0].direction == "counterclockwise"


def test_front_track_path_conflict_duration_debounce_and_checkpoint_are_generic() -> None:
    api = _geometry()
    front = api.front_of_track_occupancy(
        subject_id="unit.any.defender",
        subject_start_m=(0.0, 5.0),
        subject_end_m=(0.0, 15.0),
        target_id="unit.any.attacker",
        target_start_m=(0.0, 0.0),
        target_end_m=(0.0, 10.0),
        minimum_lead_m=4.0,
        maximum_lead_m=6.0,
        lateral_tolerance_m=1.0,
    )
    assert front is not None
    assert front.lead_m == pytest.approx(5.0)
    conflict = api.path_conflict(
        entity_a_id="unit.any.defender",
        start_a_m=(-5.0, 0.0),
        end_a_m=(5.0, 0.0),
        entity_b_id="unit.any.attacker",
        start_b_m=(0.0, -5.0),
        end_b_m=(0.0, 5.0),
        threshold_m=0.1,
    )
    assert conflict is not None
    assert conflict.time_fraction == pytest.approx(0.5)
    accumulator = api.InterdictionGeometryAccumulatorV2()
    occupancy = api.AnnularSectorOccupancyFactV2("unit.any.defender", 4, 1.5, ((0.0, 0.75),))
    assert accumulator.add_occupancy(occupancy, key="metric.arc").duration_seconds == 1.5
    assert (
        accumulator.add_blocked_or_slow(
            key="metric.blocked", tick=4, blocked_or_slow=True, dt_seconds=1.0
        ).duration_seconds
        == 1.0
    )
    assert (
        accumulator.debounce_path_conflict(
            key="metric.conflict", tick=4, candidate=conflict, debounce_ticks=2
        )
        == conflict
    )
    assert (
        accumulator.debounce_path_conflict(
            key="metric.conflict", tick=5, candidate=conflict, debounce_ticks=2
        )
        is None
    )
    accumulator.mark_replan_trigger(key="unit.any.defender", tick=4)
    assert accumulator.record_replan(key="unit.any.defender", tick=7).latency_ticks == 3
    restored = api.InterdictionGeometryAccumulatorV2.restore(accumulator.snapshot())
    assert restored.snapshot() == accumulator.snapshot()


def test_score_missing_data_is_numeric_zero_with_audit_not_structural_na() -> None:
    api = importlib.import_module("openmdbench.missions.engine_v2")
    receipt = api.ScoringSystemV2.evaluate(
        (
            api.ScoreInputV2(
                metric_id="metric.structural-na",
                value=None,
                weight=0.5,
                unit="points",
            ),
            api.ScoreInputV2(
                metric_id="metric.expected-input-missing",
                value=0.0,
                weight=0.5,
                unit="points",
                missing_inputs=("authoritative.event",),
                missing_evidence_source="sha256:" + "a" * 64,
            ),
        ),
        aggregation="sum",
        direction="maximize",
        tick=8,
        operation_id="score.missing.008",
    )
    assert receipt.competition_scores["metric.structural-na"] is None
    assert receipt.competition_scores["metric.expected-input-missing"] == 0.0
    assert receipt.metric_data_missing[0].missing_inputs == ("authoritative.event",)
    assert {item.data_status for item in receipt.metric_receipts} == {"not_applicable", "missing"}
    with pytest.raises(ValueError, match="numeric zero"):
        api.ScoreInputV2(
            metric_id="metric.invalid-missing",
            value=None,
            weight=1.0,
            unit="points",
            missing_inputs=("authoritative.event",),
            missing_evidence_source="evidence",
        )

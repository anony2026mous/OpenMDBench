"""Planning, execution, range, unavailable, and replay-equivalence tests."""

from openmdbench.scoring import combined_score, execution_metrics, planning_metrics


def _planning() -> dict[str, object]:
    return {
        "understood_objectives": 2,
        "total_objectives": 2,
        "productive_resource_time": 8,
        "allocated_resource_time": 10,
        "successful_adaptations": 1,
        "adaptation_opportunities": 2,
        "coordinated_actions": 3,
        "coordination_opportunities": 4,
        "average_alert_latency": 2,
        "latency_baseline": 10,
        "correctly_filtered_decoys": 3,
        "total_decoys": 4,
        "correct_intent_predictions": 2,
        "total_intent_predictions": 4,
    }


def _execution() -> dict[str, object]:
    return {
        "completed_objectives": 1,
        "total_objectives": 2,
        "elapsed_ticks": 800,
        "baseline_ticks": 1000,
        "energy_used": 0.4,
        "baseline_energy": 0.5,
        "collisions": 0,
        "collision_exposure": 10,
        "tracking_rmse_m": 20,
        "tracking_tolerance_m": 100,
    }


def test_all_metrics_are_bounded_and_oiis_formula_is_exact() -> None:
    planning = planning_metrics(**_planning())  # type: ignore[arg-type]
    execution = execution_metrics(**_execution())  # type: ignore[arg-type]
    assert planning["OIIS"].value == 0.3 * 0.8 + 0.4 * 0.75 + 0.3 * 0.5
    assert all(metric.value is None or 0.0 <= metric.value <= 1.0 for metric in planning.values())
    assert all(metric.value is None or 0.0 <= metric.value <= 1.0 for metric in execution.values())
    assert combined_score(planning, execution)["total"].value is not None


def test_zero_denominators_are_explicitly_unavailable() -> None:
    inputs = _planning()
    inputs["total_objectives"] = 0
    metrics = planning_metrics(**inputs)  # type: ignore[arg-type]
    assert metrics["MUS"].value is None
    assert metrics["MUS"].reason == "no objectives"


def test_online_inputs_and_replay_recalculation_are_identical() -> None:
    online_planning = planning_metrics(**_planning())  # type: ignore[arg-type]
    online_execution = execution_metrics(**_execution())  # type: ignore[arg-type]
    replay_planning = planning_metrics(**dict(_planning()))  # type: ignore[arg-type]
    replay_execution = execution_metrics(**dict(_execution()))  # type: ignore[arg-type]
    assert combined_score(online_planning, online_execution) == combined_score(
        replay_planning, replay_execution
    )

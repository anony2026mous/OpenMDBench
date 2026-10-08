"""Version-1 pure scoring definitions with explicit unavailable states."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Metric:
    value: float | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.value is not None and not 0.0 <= self.value <= 1.0:
            raise ValueError("metric value must be within [0, 1]")
        if self.value is None and not self.reason:
            raise ValueError("unavailable metric requires a reason")


def _ratio(numerator: float, denominator: float, reason: str) -> Metric:
    if denominator <= 0.0:
        return Metric(None, reason)
    return Metric(max(0.0, min(1.0, numerator / denominator)))


def opponent_intent_inference(alt: Metric, fdr: Metric, tpa: Metric) -> Metric:
    if alt.value is None or fdr.value is None or tpa.value is None:
        return Metric(None, "ALT, FDR, and TPA must all be available")
    return Metric(0.3 * alt.value + 0.4 * fdr.value + 0.3 * tpa.value)


def planning_metrics(
    *,
    understood_objectives: float,
    total_objectives: float,
    productive_resource_time: float,
    allocated_resource_time: float,
    successful_adaptations: float,
    adaptation_opportunities: float,
    coordinated_actions: float,
    coordination_opportunities: float,
    average_alert_latency: float,
    latency_baseline: float,
    correctly_filtered_decoys: float,
    total_decoys: float,
    correct_intent_predictions: float,
    total_intent_predictions: float,
) -> dict[str, Metric]:
    alt = (
        Metric(None, "latency baseline is unavailable")
        if latency_baseline <= 0.0
        else Metric(max(0.0, min(1.0, 1.0 - average_alert_latency / latency_baseline)))
    )
    fdr = _ratio(correctly_filtered_decoys, total_decoys, "no decoy ground truth")
    tpa = _ratio(correct_intent_predictions, total_intent_predictions, "no intent predictions")
    return {
        "MUS": _ratio(understood_objectives, total_objectives, "no objectives"),
        "RAE": _ratio(productive_resource_time, allocated_resource_time, "no allocated resources"),
        "AS": _ratio(
            successful_adaptations, adaptation_opportunities, "no adaptation opportunities"
        ),
        "CDCS": _ratio(
            coordinated_actions, coordination_opportunities, "no coordination opportunities"
        ),
        "ALT": alt,
        "FDR": fdr,
        "TPA": tpa,
        "OIIS": opponent_intent_inference(alt, fdr, tpa),
    }


def execution_metrics(
    *,
    completed_objectives: float,
    total_objectives: float,
    elapsed_ticks: float,
    baseline_ticks: float,
    energy_used: float,
    baseline_energy: float,
    collisions: float,
    collision_exposure: float,
    tracking_rmse_m: float,
    tracking_tolerance_m: float,
) -> dict[str, Metric]:
    time_efficiency = (
        Metric(None, "time baseline is unavailable")
        if baseline_ticks <= 0.0
        else Metric(max(0.0, min(1.0, baseline_ticks / max(elapsed_ticks, 1.0))))
    )
    energy_efficiency = (
        Metric(None, "energy baseline is unavailable")
        if baseline_energy <= 0.0
        else Metric(max(0.0, min(1.0, baseline_energy / max(energy_used, 1e-12))))
    )
    tracking_accuracy = (
        Metric(None, "tracking tolerance is unavailable")
        if tracking_tolerance_m <= 0.0
        else Metric(max(0.0, min(1.0, 1.0 - tracking_rmse_m / tracking_tolerance_m)))
    )
    return {
        "TSR": _ratio(completed_objectives, total_objectives, "no objectives"),
        "TE": time_efficiency,
        "EE": energy_efficiency,
        "CSS": Metric(1.0)
        if collision_exposure == 0.0 and collisions == 0.0
        else _ratio(
            max(0.0, collision_exposure - collisions),
            collision_exposure,
            "collision exposure unavailable",
        ),
        "TA": tracking_accuracy,
    }


def _available_mean(metrics: dict[str, Metric], names: tuple[str, ...]) -> Metric:
    values = [metrics[name].value for name in names]
    if any(value is None for value in values):
        return Metric(None, "one or more required component metrics are unavailable")
    numeric = [value for value in values if value is not None]
    return Metric(sum(numeric) / len(numeric))


def combined_score(planning: dict[str, Metric], execution: dict[str, Metric]) -> dict[str, Metric]:
    planning_score = _available_mean(planning, ("MUS", "RAE", "AS", "CDCS", "OIIS"))
    execution_score = _available_mean(execution, ("TSR", "TE", "EE", "CSS", "TA"))
    total = (
        Metric(None, "planning or execution score unavailable")
        if planning_score.value is None or execution_score.value is None
        else Metric(0.5 * planning_score.value + 0.5 * execution_score.value)
    )
    return {"planning": planning_score, "execution": execution_score, "total": total}

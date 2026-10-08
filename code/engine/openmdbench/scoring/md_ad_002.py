"""Seven-metric MD-AD-002 score with N/A reweighting and an independent safety gate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AD2Score:
    metrics: dict[str, float | None]
    availability: dict[str, bool]
    total_score: float
    safety_score: float
    rank_eligible: bool


EARLY_WARNING_BASELINES: dict[str, tuple[str, float]] = {
    "MD-AD-002-EASY": ("shore-low-altitude-envelope-v1", 15_000.0),
    "MD-AD-002-MEDIUM": ("shore-low-altitude-envelope-v1", 15_000.0),
    "MD-AD-002-HARD": ("shore-low-altitude-envelope-v1", 15_000.0),
}


@dataclass(frozen=True, slots=True)
class AD2MetricState:
    scenario_id: str
    destroyed_blue: int
    breaches: int
    initial_ammo: int
    remaining_ammo: int
    first_engagement_tick: int | None
    usv_detection_distance_m: float | None
    usv_online_platform_ticks: int
    usv_available_platform_ticks: int
    safety_violations: int
    relay_required_ticks: int = 0
    relay_success_ticks: int = 0

    def as_payload(self) -> dict[str, Any]:
        version, distance = EARLY_WARNING_BASELINES[self.scenario_id]
        return {
            **asdict(self),
            "early_warning_baseline_version": version,
            "early_warning_baseline_distance_m": distance,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> AD2MetricState:
        """Restore a metric accumulator while validating its scoring baseline."""
        values = dict(payload)
        scenario_id = str(values["scenario_id"])
        version, distance = EARLY_WARNING_BASELINES[scenario_id]
        if values.pop("early_warning_baseline_version") != version:
            raise ValueError("early-warning baseline version mismatch")
        if float(values.pop("early_warning_baseline_distance_m")) != distance:
            raise ValueError("early-warning baseline distance mismatch")
        return cls(**values)


WEIGHTS = {
    "interception_rate": 0.25,
    "penetration_score": 0.20,
    "usv_early_warning_gain": 0.15,
    "relay_effectiveness": 0.10,
    "resource_efficiency": 0.15,
    "response_time_score": 0.10,
    "usv_online_rate": 0.05,
}


def md_ad_002_score(metrics: dict[str, float | None], *, safety_violations: int) -> AD2Score:
    availability = {name: metrics.get(name) is not None for name in WEIGHTS}
    denominator = sum(WEIGHTS[name] for name, available in availability.items() if available)
    weighted = 0.0
    for name, weight in WEIGHTS.items():
        value = metrics.get(name)
        if value is not None:
            weighted += weight * value
    total = weighted / denominator if denominator else 0.0
    safety = 0.0 if safety_violations > 3 else max(0.0, 1.0 - 0.1 * safety_violations)
    return AD2Score(metrics, availability, total, safety, safety >= 0.7)


def score_metric_state(state: AD2MetricState) -> AD2Score:
    _version, baseline_m = EARLY_WARNING_BASELINES[state.scenario_id]
    detected_m = state.usv_detection_distance_m or 0.0
    early_warning = max(0.0, min(1.0, (detected_m - baseline_m) / max(baseline_m, 1e-9)))
    response = (
        0.0
        if state.first_engagement_tick is None
        else max(0.0, min(1.0, (600.0 - state.first_engagement_tick) / 480.0))
    )
    return md_ad_002_score(
        {
            "interception_rate": state.destroyed_blue / 15.0,
            "penetration_score": 1.0 - state.breaches / 15.0,
            "usv_early_warning_gain": early_warning,
            "relay_effectiveness": (
                state.relay_success_ticks / state.relay_required_ticks
                if state.relay_required_ticks
                else None
            ),
            "resource_efficiency": state.remaining_ammo / max(state.initial_ammo, 1),
            "response_time_score": response,
            "usv_online_rate": state.usv_online_platform_ticks
            / max(state.usv_available_platform_ticks, 1),
        },
        safety_violations=state.safety_violations,
    )


def score_authority_records(records: tuple[dict[str, Any], ...]) -> AD2Score:
    ticks = [record for record in records if record.get("record_type") == "tick"]
    if not ticks or "metric_state" not in ticks[-1]["payload"]:
        raise ValueError("authority log has no metric_state")
    return score_metric_state(AD2MetricState.from_payload(ticks[-1]["payload"]["metric_state"]))

"""
OpenMDBench — Layered Metric Engine

Computes the 10 layered evaluation metrics defined in Section 3.5:

High-level planning metrics (LLM-attributable):
  - MUS:  Mission Understanding Score
  - RAE:  Resource Allocation Efficiency
  - AS:   Adaptability Score
  - CDCS: Cross-Domain Coordination Score
  - OIIS: Opponent Intent Inference Score (ALT + FDR + TPA)

Low-level execution metrics (small-model-attributable):
  - TSR:  Task Success Rate
  - TE:   Time Efficiency
  - EE:   Energy Efficiency
  - CSS:  Collision and Safety Score
  - TA:   Tracking Accuracy

Composite: Score_total = α·Score_planning + β·Score_execution (α=β=0.5)

For the grid concept validation, some metrics are approximated since
the grid world doesn't have full MILP solvers or cross-domain sensors.
Mappings are documented per metric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class MetricResult:
    """Result of metric computation."""
    planning_score: float = 0.0
    execution_score: float = 0.0
    composite_score: float = 0.0
    details: Dict[str, float] = field(default_factory=dict)


class MetricEngine:
    """
    Computes layered metrics from episode data.

    For the grid concept validation, metrics are computed from the
    raw episode metrics produced by GridEnv.get_episode_metrics().
    """

    def __init__(self, alpha: float = 0.5, beta: float = 0.5):
        self.alpha = alpha  # planning weight
        self.beta = beta    # execution weight

    def compute(
        self,
        env_metrics: dict,
        max_steps: int = 150,
        total_ammo: int = 5,
        num_blue: int = 3,
    ) -> MetricResult:
        """
        Compute all metrics from raw environment metrics.

        Args:
            env_metrics: Dict from GridEnv.get_episode_metrics()
            max_steps: maximum episode length
            total_ammo: initial ammo per unit
            num_blue: number of blue units

        Returns:
            MetricResult with planning, execution, and composite scores.
        """
        details = {}

        # --- High-level planning metrics ---

        # MUS: Mission Understanding Score
        # Proxy: did the agent prioritize correctly?
        # = mission_success * (1 - rule_violation_rate)
        mission_success = float(env_metrics.get("mission_success", False))
        rule_violation_rate = env_metrics.get("rule_violation_rate", 0.0)
        mus = mission_success * (1.0 - rule_violation_rate)
        details["MUS"] = round(mus, 4)

        # RAE: Resource Allocation Efficiency
        # Proxy: intercepts per blue unit (how well resources were used)
        red_intercepted = env_metrics.get("red_intercepted", 0)
        red_total = env_metrics.get("red_combatants_total", 1)
        rae = min(1.0, red_intercepted / max(red_total, 1))
        details["RAE"] = round(rae, 4)

        # AS: Adaptability Score
        # Proxy: 1 - normalized adaptation latency
        adaptation_latencies = env_metrics.get("adaptation_latencies", [])
        if adaptation_latencies:
            avg_latency = np.mean(adaptation_latencies)
            # Normalize: 0 latency = 1.0, max_steps latency = 0.0
            as_score = max(0.0, 1.0 - avg_latency / max_steps)
        else:
            # No instruction switches = either no updates needed or perfect planning
            as_score = 1.0 if env_metrics.get("instruction_switches", 0) == 0 else 0.5
        details["AS"] = round(as_score, 4)

        # CDCS: Cross-Domain Coordination Score (v2 redefinition, H.8)
        # Three USV↔UAV coupling components measured on the execution
        # trajectory; falls back to the v1 detection proxy when the v2
        # coupling telemetry is absent (e.g. legacy replays):
        #   (a) fraction of intercepts executed under an ACTIVE UAV lock
        #   (b) UAV-detection → USV-engagement handover latency (normalized)
        #   (c) lock maintenance ratio during engagements
        red_detected = env_metrics.get("red_detected", 0)
        v2_coupling = any(k in env_metrics for k in
                          ("intercept_lock_rate", "lock_maintenance_ratio"))
        cdcs_components = []
        if v2_coupling:
            lock_rate = env_metrics.get("intercept_lock_rate", None)
            if lock_rate is not None and env_metrics.get("red_intercepted", 0) > 0:
                cdcs_components.append(float(lock_rate))          # (a)
            handovers = env_metrics.get("handover_latencies", []) or []
            if handovers:
                cdcs_components.append(
                    max(0.0, 1.0 - float(np.mean(handovers)) / max_steps))  # (b)
            maint = env_metrics.get("lock_maintenance_ratio", None)
            if maint is not None and env_metrics.get("red_intercepted", 0) > 0:
                cdcs_components.append(float(maint))             # (c)
        if cdcs_components:
            cdcs = float(np.mean(cdcs_components))
        else:
            cdcs = min(1.0, red_detected / max(red_total, 1))   # v1 proxy
        details["CDCS"] = round(cdcs, 4)
        if v2_coupling:
            details["CDCS_lock_rate"] = round(
                float(env_metrics.get("intercept_lock_rate", 0.0)), 4)
            details["CDCS_handover"] = round(
                float(np.mean(env_metrics.get("handover_latencies", []) or [0])), 4)
            details["CDCS_lock_maint"] = round(
                float(env_metrics.get("lock_maintenance_ratio", 0.0)), 4)

        # OIIS: Opponent Intent Inference Score
        # Sub-metrics: ALT, FDR, TPA
        # ALT: Anticipation Lead Time (proxy: detection early enough)
        # FDR: Feint Detection Rate (proxy: 1 - civilian_violation_rate)
        # TPA: Target Prediction Accuracy (proxy: intercepts / detected)
        alt = min(1.0, red_detected / max(red_total, 1))  # detection rate as proxy
        fdr = 1.0 - env_metrics.get("rule_violation_rate", 0.0)
        tpa = red_intercepted / max(red_detected, 1) if red_detected > 0 else 0.0
        oiis = 0.3 * alt + 0.4 * fdr + 0.3 * tpa
        details["OIIS"] = round(oiis, 4)
        details["ALT"] = round(alt, 4)
        details["FDR"] = round(fdr, 4)
        details["TPA"] = round(tpa, 4)

        # --- Low-level execution metrics ---

        # TSR: Task Success Rate
        tsr = mission_success
        details["TSR"] = round(tsr, 4)

        # TE: Time Efficiency
        # Proxy: 1 - (steps_used / max_steps) — faster = better
        steps_used = env_metrics.get("steps", max_steps)
        if mission_success:
            te = max(0.0, 1.0 - steps_used / max_steps)
        else:
            te = 0.0  # failed mission = no time efficiency
        details["TE"] = round(te, 4)

        # EE: Energy Efficiency
        # v2: ammunition AND fuel — 0.5 × ammo efficiency + 0.5 × fuel
        # score (fraction of the fleet's fuel budget left at the end).
        ammo_used = env_metrics.get("ammo_used", 1)
        ee_ammo = min(1.0, red_intercepted / max(ammo_used, 1))
        fuel_consumed = env_metrics.get("fuel_consumed", None)
        if fuel_consumed is not None:
            fuel_budget = num_blue * 100.0            # FUEL_MAX per unit
            ee_fuel = max(0.0, 1.0 - float(fuel_consumed) / fuel_budget)
            ee = 0.5 * ee_ammo + 0.5 * ee_fuel
            details["EE_ammo"] = round(ee_ammo, 4)
            details["EE_fuel"] = round(ee_fuel, 4)
        else:
            ee = ee_ammo                              # v1 proxy
        details["EE"] = round(ee, 4)

        # CSS: Collision and Safety Score
        # Proxy: 1 - civilian_intercepted / max(civilian_encounters, 1)
        civilian_enc = env_metrics.get("civilian_encounters", 0)
        civilian_intercepted = env_metrics.get("civilian_intercepted", 0)
        if civilian_enc > 0:
            css = 1.0 - civilian_intercepted / civilian_enc
        else:
            css = 1.0  # no civilian encounters = perfect safety
        details["CSS"] = round(css, 4)

        # TA: Tracking Accuracy
        # Proxy: fraction of detected red units that were intercepted
        ta = red_intercepted / max(red_detected, 1) if red_detected > 0 else 0.0
        details["TA"] = round(ta, 4)

        # --- v2 coupling/efficiency raw telemetry (H.8 metrics 6-9) ---
        if "avg_lock_duration" in env_metrics:
            details["lock_duration"] = round(
                float(env_metrics.get("avg_lock_duration", 0.0)), 4)
            details["locks_acquired"] = int(env_metrics.get("locks_acquired", 0))
        if "fuel_consumed" in env_metrics:
            # successes per 100 fuel units (batch level: sum/sum)
            details["fuel_consumed"] = round(
                float(env_metrics.get("fuel_consumed", 0.0)), 2)
            details["fuel_per_success"] = round(
                float(env_metrics.get("fuel_consumed", 0.0))
                / max(red_intercepted, 1), 2)
        if "jam_events" in env_metrics:
            details["jam_events"] = int(env_metrics.get("jam_events", 0))
            details["packets_dropped"] = int(env_metrics.get("packets_dropped", 0))

        # --- Composite scores ---
        planning_metrics = [mus, rae, as_score, cdcs, oiis]
        execution_metrics = [tsr, te, ee, css, ta]

        planning_score = np.mean(planning_metrics)
        execution_score = np.mean(execution_metrics)
        composite = self.alpha * planning_score + self.beta * execution_score

        return MetricResult(
            planning_score=round(planning_score, 4),
            execution_score=round(execution_score, 4),
            composite_score=round(composite, 4),
            details=details,
        )

    def compute_batch(self, episodes: List[dict]) -> Dict[str, float]:
        """
        Compute aggregate metrics over multiple episodes.

        Returns mean and std for each metric, plus v2 ratio aggregates
        (successes per 100 fuel; handover latency pooled over episodes).
        """
        results = [self.compute(ep) for ep in episodes]

        summary = {}
        for field_name in ["planning_score", "execution_score", "composite_score"]:
            values = [getattr(r, field_name) for r in results]
            summary[f"{field_name}_mean"] = round(float(np.mean(values)), 4)
            summary[f"{field_name}_std"] = round(float(np.std(values)), 4)

        # Per-metric aggregation
        all_keys = results[0].details.keys() if results else []
        for key in all_keys:
            values = [r.details[key] for r in results]
            summary[f"{key}_mean"] = round(float(np.mean(values)), 4)
            summary[f"{key}_std"] = round(float(np.std(values)), 4)

        # v2 pooled aggregates
        total_fuel = sum(float(ep.get("fuel_consumed", 0.0)) for ep in episodes)
        total_success = sum(float(ep.get("mission_success", False))
                            for ep in episodes)
        if total_fuel > 0:
            summary["fuel_efficiency_per_100"] = round(
                total_success / total_fuel * 100.0, 4)
        all_handovers = [lat for ep in episodes
                         for lat in (ep.get("handover_latencies") or [])]
        if all_handovers:
            summary["handover_latency_pooled_mean"] = round(
                float(np.mean(all_handovers)), 4)
            summary["handover_latency_pooled_std"] = round(
                float(np.std(all_handovers)), 4)

        return summary


def sample_efficiency(training_history: List[dict],
                      final_perf_frac: float = 0.8) -> Optional[int]:
    """Steps to reach `final_perf_frac` of the final eval performance.

    training_history: entries from train_mappo.py's saved JSON, each with
    {"step": int, "eval_success_rate": float, ...}.
    Returns None when the history never crosses the threshold (agent
    did not learn) or the history is empty.
    """
    if not training_history:
        return None
    history = sorted(training_history, key=lambda h: h.get("step", 0))
    final_perf = max(h.get("eval_success_rate", 0.0) for h in history)
    threshold = final_perf_frac * final_perf
    if final_perf <= 0 or threshold <= 0:
        return None
    for h in history:
        if h.get("eval_success_rate", 0.0) >= threshold:
            return int(h["step"])
    return None

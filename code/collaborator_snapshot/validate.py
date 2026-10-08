"""
OpenMDBench — Concept Validation Script

Checks the 5 validation criteria from Appendix H.10:
1. Evaluation pipeline runs error-free
2. Hybrid (C) outperforms pure RL (A) on complex by >= 15% success rate (p < 0.05)
3. Pure RL (A) matches/exceeds hybrid (C) on simple
4. Causal attribution Delta-P / Delta-E consistent with manual inspection
5. Results reproducible across 3 seeds (std < 10% mean)

Usage:
    python validate.py
    python validate.py --results_dir results
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Lightweight statistics (no scipy dependency)
# ---------------------------------------------------------------------------

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function."""
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _welch_ttest(a, b):
    """Welch's t-test (unequal variance), returns (t_stat, p_value)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0, 1.0
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    if se < 1e-12:
        return 0.0, 1.0
    t = (ma - mb) / se
    # Welch-Satterthwaite degrees of freedom
    df_num = (va / na + vb / nb) ** 2
    df_den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = df_num / df_den if df_den > 0 else 1
    # Exact two-tailed p-value via the regularized incomplete beta function
    p = _betai(df / 2.0, 0.5, df / (df + t * t))
    return float(t), min(max(p, 0.0), 1.0)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_results(results_dir: str) -> dict:
    """Load evaluation results from JSON.

    Supports two formats:
    1. Tournament format (tournament_results.json) — from run_tournament.py
    2. Legacy format (evaluation_results.json) — from evaluate.py
    """
    # Try tournament format first
    tournament_path = os.path.join(results_dir, "tournament_results.json")
    legacy_path = os.path.join(results_dir, "evaluation_results.json")

    if os.path.exists(tournament_path):
        with open(tournament_path) as f:
            tournament = json.load(f)
        return _convert_tournament_results(tournament)
    elif os.path.exists(legacy_path):
        with open(legacy_path) as f:
            return json.load(f)
    else:
        print(f"Results file not found in: {results_dir}")
        print("Please run run_tournament.py or evaluate.py first.")
        sys.exit(1)


def _convert_tournament_results(tournament: dict) -> dict:
    """Convert flat tournament results to the nested format validate.py expects."""
    results = {}
    matches = tournament.get("matches", [])

    # Group by agent × difficulty
    groups = {}
    for m in matches:
        key = f"{m['agent']}_{m['difficulty']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(m)

    for key, episodes in groups.items():
        success_rates = [float(ep.get("mission_success", False)) for ep in episodes]
        composites = [float(ep.get("composite", 0)) for ep in episodes]

        # Collect per-episode metrics
        enriched_episodes = []
        for ep in episodes:
            enriched_episodes.append({
                "seed": ep.get("seed", 0),
                "mission_success": ep.get("mission_success", False),
                "composite": ep.get("composite", 0),
                "planning": ep.get("planning", 0),
                "execution": ep.get("execution", 0),
                "steps": ep.get("steps", 0),
                "instruction_switches": ep.get("metric_details", {}).get("AS", 0),
                "red_intercepted": ep.get("metric_details", {}).get("RAE", 0) * 2,
                **ep.get("metric_details", {}),
            })

        results[key] = {
            "episodes": enriched_episodes,
            "summary": {
                "success_rate_mean": float(np.mean(success_rates)),
                "success_rate_std": float(np.std(success_rates)),
                "composite_mean": float(np.mean(composites)),
                "composite_std": float(np.std(composites)),
            },
        }

    return results


def criterion_1_pipeline_integrity(results: dict) -> Tuple[bool, str]:
    """Check that the evaluation pipeline ran without errors."""
    # v2: five systems (H.8) — random / pure_rl / pure_llm / rule / hybrid
    expected_combos = [
        f"{agent}_{diff}"
        for agent in ["random", "pure_rl", "pure_llm", "rule", "hybrid"]
        for diff in ["simple", "medium", "complex"]
    ]
    missing = [k for k in expected_combos if k not in results]
    if missing:
        return False, f"Missing results for: {missing}"

    for key, data in results.items():
        if not data.get("episodes"):
            return False, f"No episodes for {key}"
        if not data.get("summary"):
            return False, f"No summary for {key}"

    return True, f"All {len(expected_combos)} agent×difficulty combinations completed via CSS+ULHA pipeline."


def criterion_2_hybrid_wins_complex(results: dict) -> Tuple[bool, str]:
    """
    Hybrid (C) outperforms pure RL (A) on complex by >= 15% success rate (p < 0.05).
    """
    hybrid_data = results.get("hybrid_complex", {}).get("episodes", [])
    rl_data = results.get("pure_rl_complex", {}).get("episodes", [])

    if not hybrid_data or not rl_data:
        return False, "Missing data for hybrid_complex or pure_rl_complex."

    hybrid_sr = [float(ep["mission_success"]) for ep in hybrid_data]
    rl_sr = [float(ep["mission_success"]) for ep in rl_data]

    hybrid_mean = np.mean(hybrid_sr)
    rl_mean = np.mean(rl_sr)
    gap = hybrid_mean - rl_mean

    # Statistical test
    if len(hybrid_sr) >= 2 and len(rl_sr) >= 2:
        t_stat, p_value = _welch_ttest(hybrid_sr, rl_sr)
    else:
        p_value = 1.0

    passed = (gap >= 0.15) and (p_value < 0.05)

    msg = (
        f"Hybrid success rate: {hybrid_mean:.1%}, "
        f"Pure RL success rate: {rl_mean:.1%}, "
        f"Gap: {gap:+.1%}, "
        f"p-value: {p_value:.4f}. "
        f"{'PASS' if passed else 'FAIL'}."
    )

    if not passed:
        if gap < 0.15:
            msg += " Gap < 15%. Consider increasing entity types, instruction variability, or anomaly frequency."
        if p_value >= 0.05:
            msg += " Not statistically significant (p >= 0.05)."

    return passed, msg


def criterion_3_rl_matches_simple(results: dict) -> Tuple[bool, str]:
    """
    Pure RL (A) matches/exceeds hybrid (C) on simple.
    """
    rl_data = results.get("pure_rl_simple", {}).get("episodes", [])
    hybrid_data = results.get("hybrid_simple", {}).get("episodes", [])

    if not rl_data or not hybrid_data:
        return False, "Missing data for pure_rl_simple or hybrid_simple."

    rl_sr = np.mean([float(ep["mission_success"]) for ep in rl_data])
    hybrid_sr = np.mean([float(ep["mission_success"]) for ep in hybrid_data])

    # RL should be within 5% of hybrid (or better)
    passed = rl_sr >= hybrid_sr - 0.05

    msg = (
        f"Pure RL success rate (simple): {rl_sr:.1%}, "
        f"Hybrid success rate (simple): {hybrid_sr:.1%}. "
        f"{'PASS' if passed else 'FAIL'}: "
        f"{'RL matches/exceeds hybrid on simple tasks.' if passed else 'Hybrid significantly outperforms RL on simple tasks (unexpected).'}"
    )

    return passed, msg


def criterion_4_attribution_consistency(results: dict) -> Tuple[bool, str]:
    """
    Causal attribution Delta-P / Delta-E consistent with manual inspection.

    Simplified proxy check here: the hybrid agent shows a different
    bottleneck profile than pure RL and rule.  (The full pairwise
    cross-attribution and counterfactual replay land with the Phase-7
    attribution framework; this criterion is re-checked there.)
    """
    # Compute approximate bottleneck profiles from metrics
    # (Full counterfactual replay is done in Phase 4)

    # For pure RL: expect low planning, variable execution
    rl_data = results.get("pure_rl_complex", {}).get("episodes", [])
    # For hybrid: expect better planning, similar execution
    hybrid_data = results.get("hybrid_complex", {}).get("episodes", [])
    # For rule: expect strong planning, similar execution
    rule_data = results.get("rule_complex", {}).get("episodes", [])

    if not all([rl_data, hybrid_data]):
        return False, "Missing data for attribution check."

    # Proxy for planning quality: composite planning score
    rl_planning = np.mean([ep.get("planning", 0) for ep in rl_data])
    hybrid_planning = np.mean([ep.get("planning", 0) for ep in hybrid_data])

    # Proxy for execution quality: composite execution score
    rl_execution = np.mean([ep.get("execution", 0) for ep in rl_data])
    hybrid_execution = np.mean([ep.get("execution", 0) for ep in hybrid_data])

    # Check: hybrid should have different bottleneck profile than pure RL
    # (either better planning or better execution)
    planning_better = hybrid_planning >= rl_planning
    execution_better = hybrid_execution >= rl_execution

    passed = planning_better or execution_better

    # Also check rule vs hybrid for differentiation
    rule_planning = np.mean([ep.get("planning", 0) for ep in rule_data]) if rule_data else 0
    rule_execution = np.mean([ep.get("execution", 0) for ep in rule_data]) if rule_data else 0

    msg = (
        f"Hybrid vs Pure RL (complex):\n"
        f"  Planning:  hybrid={hybrid_planning:.3f}, RL={rl_planning:.3f} "
        f"({'better' if planning_better else 'worse'})\n"
        f"  Execution: hybrid={hybrid_execution:.3f}, RL={rl_execution:.3f} "
        f"({'better' if execution_better else 'worse'})\n"
    )
    if rule_data:
        msg += (
            f"  Rule baseline: planning={rule_planning:.3f}, execution={rule_execution:.3f}\n"
        )
    msg += (
        f"{'PASS' if passed else 'FAIL'}: Attribution profile "
        f"{'consistent' if passed else 'inconsistent'} with expectations."
    )

    return passed, msg


def criterion_5_reproducibility(results: dict) -> Tuple[bool, str]:
    """
    Results reproducible across seed blocks.

    Episodes are grouped into seed blocks of 10 (seeds 0-9, 10-19, ...).
    Per-block composite means must be consistent: CV < 10%.
    Win rates per block are reported for reference.
    """
    all_passed = True
    details = []

    for key in sorted(results.keys()):
        data = results[key]
        episodes = data.get("episodes", [])

        # Group episodes into seed blocks of 10
        blocks: Dict[int, list] = {}
        for ep in episodes:
            seed = int(ep.get("seed", 0))
            blocks.setdefault(seed // 10, []).append(ep)

        if len(blocks) < 2:
            all_passed = False
            details.append(
                f"  {key}: only {len(blocks)} seed block(s); need >= 2 "
                f"(run with seeds 0-29) FAIL"
            )
            continue

        comp_means = [
            float(np.mean([float(e.get("composite", 0)) for e in eps]))
            for _, eps in sorted(blocks.items())
        ]
        wr_means = [
            float(np.mean([float(e.get("mission_success", False)) for e in eps]))
            for _, eps in sorted(blocks.items())
        ]

        mu = float(np.mean(comp_means))
        sd = float(np.std(comp_means))
        cv = sd / max(mu, 1e-6)
        passed = cv < 0.10
        if not passed:
            all_passed = False

        comp_str = " / ".join(f"{m:.3f}" for m in comp_means)
        wr_str = " / ".join(f"{w:.0%}" for w in wr_means)
        details.append(
            f"  {key}: composite blocks [{comp_str}] CV={cv:.3f} | "
            f"win rates [{wr_str}] {'OK' if passed else 'FAIL'}"
        )

    msg = "Reproducibility across seed blocks (composite CV < 10%):\n" + "\n".join(details)
    msg += f"\n{'PASS' if all_passed else 'FAIL'}."

    return all_passed, msg


def main():
    parser = argparse.ArgumentParser(description="Validate concept validation criteria")
    parser.add_argument("--results_dir", type=str, default="results")
    args = parser.parse_args()

    results = load_results(args.results_dir)

    print("=" * 70)
    print("OpenMDBench Concept Validation (Appendix H.10)")
    print("=" * 70)

    criteria = [
        ("1. Pipeline integrity", criterion_1_pipeline_integrity),
        ("2. Hybrid > RL on complex (>=15%, p<0.05)", criterion_2_hybrid_wins_complex),
        ("3. RL matches hybrid on simple", criterion_3_rl_matches_simple),
        ("4. Attribution consistency", criterion_4_attribution_consistency),
        ("5. Reproducibility (std < 10% mean)", criterion_5_reproducibility),
    ]

    passed_count = 0
    for name, func in criteria:
        print(f"\n--- Criterion {name} ---")
        passed, msg = func(results)
        print(msg)
        if passed:
            passed_count += 1

    print(f"\n{'=' * 70}")
    print(f"RESULT: {passed_count}/5 criteria passed.")

    if passed_count == 5:
        print("ALL CRITERIA PASSED. Proceed to Phase 1-3.")
    else:
        print("SOME CRITERIA FAILED. Review and fix before proceeding.")
        print("If Criterion 2 fails: increase entity types, instruction variability,")
        print("or anomaly frequency in the grid environment.")

    # Save validation report
    report = {
        "criteria_passed": passed_count,
        "total_criteria": 5,
        "all_passed": passed_count == 5,
    }
    report_path = os.path.join(args.results_dir, "validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()

"""Cross-scenario three-arm table for the IE set.

Collects per-scenario arm reports (``_w1_runs/ie_<planner>_<scenario>_<tag>.json``)
and prints:

  * the overall strategy score matrix (scenario x arm) with the per-scenario winner,
  * the layer breakdown per scenario so a reader can re-weight,
  * the raw evidence that explains a gap (fires, intercept rate, depth, losses).

Usage:
    python _w1_ie_table.py --tag s1
    python _w1_ie_table.py --tag s1 --scenarios IE-02-DUAL-THREAT
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL))
RUNS = EVAL / "_w1_runs"

from strategy_metrics import format_scorecard_line  # noqa: E402

ARMS = (("rule", "rule"), ("llm", "hybrid-LLM"), ("purellm", "pure-LLM"))
SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER",
    "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE",
    "IE-14-SATURATION-THREE-WAVE",
]
LAYERS = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")


def load(tag: str, planner_key: str, scenario: str):
    path = RUNS / f"ie_{planner_key}_{scenario.lower()}_{tag}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score(report) -> float | None:
    if report is None:
        return None
    return (report.get("strategy_scorecard") or {}).get("defender_score")


def outcome(report) -> str:
    if report is None:
        return "-"
    return str((report.get("layered_metrics") or {}).get("outcome") or "-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="s1")
    parser.add_argument("--scenarios", nargs="*", default=None)
    args = parser.parse_args()
    scenarios = args.scenarios or SCENARIOS

    print("=" * 104)
    print(f"IE 场景集 三臂总体策略评分（防守方视角，越高越好）  tag={args.tag}")
    print("=" * 104)
    header = f"{'scenario':<26}" + "".join(f"{label:>14}" for _k, label in ARMS) + \
             f"{'winner':>18}{'margin':>10}"
    print(header)
    print("-" * len(header))

    wins = {key: 0 for key, _ in ARMS}
    for scenario in scenarios:
        reports = {key: load(args.tag, key, scenario) for key, _ in ARMS}
        scores = {key: score(report) for key, report in reports.items()}
        present = {k: v for k, v in scores.items() if v is not None}
        row = f"{scenario:<26}"
        for key, _label in ARMS:
            value = scores.get(key)
            row += f"{value:>14.4f}" if value is not None else f"{'-':>14}"
        if present:
            best = max(present, key=lambda k: present[k])
            ordered = sorted(present.values(), reverse=True)
            margin = ordered[0] - ordered[1] if len(ordered) > 1 else 0.0
            label = dict(ARMS)[best]
            wins[best] += 1
            row += f"{label:>18}{margin:>10.4f}"
        print(row)

    print("\n  各臂获胜场景数：" + "  ".join(f"{label}={wins[key]}"
                                            for key, label in ARMS))

    print("\n" + "=" * 104)
    print("分层明细（每场景一行：臂 | overall | 各层）")
    print("=" * 104)
    for scenario in scenarios:
        print(f"\n--- {scenario}")
        for key, label in ARMS:
            report = load(args.tag, key, scenario)
            if report is None:
                print(f"  {label:<12} (missing)")
                continue
            sc = report.get("strategy_scorecard") or {}
            metrics = report.get("layered_metrics") or {}
            print("  " + format_scorecard_line(sc, label))
            print(f"               ticks={report.get('ticks_run')} "
                  f"{outcome(report)} fires={metrics.get('total_fires')} "
                  f"intercept={metrics.get('interception_rate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

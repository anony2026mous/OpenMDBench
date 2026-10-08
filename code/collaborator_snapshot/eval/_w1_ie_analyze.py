"""Analyse the exported IE results: which layers create the arm gap?

Reads ``_w1_runs/ie_set_results_<tag>.json`` and reports, per scenario and in
aggregate:

  * layer-wise deltas (arm - rule) so the source of a gap is visible,
  * a per-arm win/loss tally and mean margin,
  * how often each layer decides the outcome (largest weighted contribution to
    the delta).

Usage:
    python _w1_ie_analyze.py --tag s1
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

from strategy_metrics import LayerWeights  # noqa: E402

LAYERS = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")
WEIGHTS = LayerWeights()


def weight(name: str) -> float:
    return float(getattr(WEIGHTS, name))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="s1")
    args = parser.parse_args()

    payload = json.loads((RUNS / f"ie_set_results_{args.tag}.json").read_text("utf-8"))
    rows = payload["rows"]
    by_key = {(row["arm"], row["scenario"]): row for row in rows}
    scenarios = [s for s in payload["scenarios"]
                 if any((arm, s) in by_key for arm in ("rule", "hybrid-llm", "pure-llm"))]
    arms = [a for a in ("hybrid-llm", "pure-llm")
            if any((a, s) in by_key for s in scenarios)]

    print("=" * 108)
    print(f"逐层差额（挑战臂 − rule；正=该臂在该层更好）  tag={args.tag}")
    print("=" * 108)
    header = f"{'scenario':<26}{'arm':<12}{'overall':>9}" + \
             "".join(f"{name[:5]:>8}" for name in LAYERS) + f"{'驱动层':>16}"
    print(header)
    print("-" * len(header))

    decisions: dict[str, dict[str, int]] = {a: {name: 0 for name in LAYERS} for a in arms}
    tally: dict[str, dict[str, float]] = {a: {"win": 0, "loss": 0, "tie": 0, "sum": 0.0}
                                          for a in arms}

    for scenario in scenarios:
        base = by_key.get(("rule", scenario))
        if base is None:
            continue
        for arm in arms:
            row = by_key.get((arm, scenario))
            if row is None:
                continue
            if isinstance(row["defender_score"], (int, float)) and \
                    isinstance(base["defender_score"], (int, float)):
                delta = row["defender_score"] - base["defender_score"]
                bucket = "win" if delta > 0.005 else ("loss" if delta < -0.005 else "tie")
                tally[arm][bucket] += 1
                tally[arm]["sum"] += delta
            else:
                delta = None
            line = f"{scenario:<26}{arm:<12}" + \
                   (f"{delta:>+9.4f}" if delta is not None else f"{'-':>9}")
            contributions = {}
            for name in LAYERS:
                a, b = row.get(f"layer_{name}"), base.get(f"layer_{name}")
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    diff = a - b
                    contributions[name] = weight(name) * diff
                    line += f"{diff:>+8.2f}"
                else:
                    line += f"{'-':>8}"
            if contributions:
                driver = max(contributions, key=lambda k: contributions[k])
                decisions[arm][driver] += 1
                line += f"{driver + f'{contributions[driver]:+.3f}':>16}"
            print(line)

    print("\n" + "=" * 108)
    print("汇总")
    print("=" * 108)
    for arm in arms:
        t = tally[arm]
        played = t["win"] + t["loss"] + t["tie"]
        mean = t["sum"] / played if played else 0.0
        top = sorted(decisions[arm].items(), key=lambda kv: -kv[1])[:3]
        print(f"  {arm:<12} 胜 {int(t['win'])} / 负 {int(t['loss'])} / 平 {int(t['tie'])}"
              f"   平均差额 {mean:+.4f}   最常决定胜负的层: "
              + ", ".join(f"{name}({count})" for name, count in top if count))

    print("\n  层权重（先验固定）：" +
          ", ".join(f"{name}={weight(name):.2f}" for name in LAYERS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

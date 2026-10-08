"""Aggregate the rule arm across several seeds into a difficulty-ladder table.

Why this exists
---------------
The engine derives every missile hit roll from
``sha256([resolved_hash, session_id, missile_id, tick, "terminal"])``
(``openmdbench/combat/system_v2.py:1267``).  A single seed therefore gives one
draw out of a highly bimodal distribution: measured on the IE set, IE-01 scored
**0.8877 at seed 7 and 0.6064 at seed 11** (a 0.28 swing), and IE-08 flipped
between ``defender_success`` and ``intruder_success``.  A one-seed "ladder" is
mostly noise -- chasing per-scenario monotonicity on single draws would be
fitting the RNG.

This script reads the per-seed reports written by ``_w1_ie_sweep.py --seed N``
(non-default seeds carry a ``_s<N>`` suffix) and reports, per scenario:

    n     number of seeds
    mean  mean defender score
    sd    sample standard deviation
    min/max  observed range
    held  how many seeds ended in a defender win

Usage:
    python _w1_multiseed.py --tag p18 --seeds 7 11 13 17 19 [--arm rule]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

IE_SET = [
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
ARM_KEY = {"rule": "rule", "hybrid-llm": "llm", "pure-llm": "purellm"}


def load_row(arm: str, scenario: str, tag: str, seed: int) -> dict | None:
    suffix = "" if seed == 7 else f"_s{seed}"
    path = RUNS / f"ie_{ARM_KEY[arm]}_{scenario.lower()}_{tag}{suffix}.json"
    if not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    card = report.get("strategy_scorecard") or {}
    return {
        "score": card.get("defender_score"),
        "outcome": (card.get("terminal") or {}).get("outcome"),
        "tick": (card.get("terminal") or {}).get("tick"),
        "layers": card.get("layers") or {},
        "facilities": (card.get("facilities") or {}).get("weighted_survival"),
        "fires_blue": report.get("total_fires_defender"),
        "fires_red": report.get("total_fires_intruder"),
        "path": path.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="p18")
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 11, 13, 17, 19])
    parser.add_argument("--arm", default="rule", choices=sorted(ARM_KEY))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    table: dict[str, dict] = {}
    for scenario in IE_SET:
        scores, outcomes, rows = [], [], []
        for seed in args.seeds:
            row = load_row(args.arm, scenario, args.tag, seed)
            if row is None or row["score"] is None:
                continue
            rows.append(row | {"seed": seed})
            scores.append(float(row["score"]))
            outcomes.append(str(row["outcome"]))
        if not scores:
            continue
        held = sum(1 for o in outcomes if o == "defender_success")
        table[scenario] = {
            "n": len(scores),
            "mean": statistics.fmean(scores),
            "sd": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "min": min(scores),
            "max": max(scores),
            "held": held,
            "outcomes": outcomes,
            "seeds": [r["seed"] for r in rows],
            "rows": rows,
        }

    print(f"arm={args.arm} tag={args.tag} seeds={args.seeds}")
    header = (f"{'scenario':<28}{'n':>3}{'mean':>8}{'sd':>7}{'min':>8}{'max':>8}"
              f"{'range':>8}{'守住':>6}  逐 seed 分数")
    print(header)
    print("-" * len(header))
    for scenario in IE_SET:
        entry = table.get(scenario)
        if entry is None:
            print(f"{scenario:<28} (no runs)")
            continue
        per_seed = " ".join(f"{r['score']:.3f}" for r in entry["rows"])
        print(f"{scenario:<28}{entry['n']:>3}{entry['mean']:>8.3f}"
              f"{entry['sd']:>7.3f}{entry['min']:>8.3f}{entry['max']:>8.3f}"
              f"{entry['max'] - entry['min']:>8.3f}"
              f"{entry['held']}/{entry['n']:>4}  {per_seed}")

    means = [table[s]["mean"] for s in IE_SET if s in table]
    sds = [table[s]["sd"] for s in IE_SET if s in table]
    print()
    print(f"平均 seed 标准差 = {statistics.fmean(sds):.3f}"
          f"（最大 {max(sds):.3f}）—— 单 seed 读数不可用于排序")
    monotone = all(means[i] >= means[i + 1] for i in range(len(means) - 1))
    print(f"均值是否随 IE-01→IE-08 单调不增: {monotone}")
    print("均值序列:", " ".join(f"{m:.3f}" for m in means))
    if not monotone:
        print("逆序对（前者应 >= 后者）:")
        for i in range(len(means) - 1):
            if means[i] < means[i + 1]:
                a, b = IE_SET[i], IE_SET[i + 1]
                overlap = (table[a]["mean"] - table[a]["sd"]
                           <= table[b]["mean"] + table[b]["sd"])
                print(f"  {a} {means[i]:.3f} < {b} {means[i+1]:.3f}"
                      f"   1σ 区间重叠={overlap}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Four-arm comparison: rule / hybrid-LLM / pure-LLM / RL on the same scorecard.

Reads the ``_w1_ie_sweep.py`` reports for each arm and prints a per-scenario matrix
with the per-layer breakdown, plus the health metrics that say whether a row is
trustworthy at all (ticks actually advanced, terminal outcome present, aborted
flag, planner call counts).

Why this exists rather than reading numbers by hand: every arm must be scored by
``run_episode.py``'s own scorecard, and a row produced by an aborted episode still
carries a plausible-looking score -- that defect already put a fabricated 0.3889
into a matrix once.  This script refuses such rows and prints ``FAIL`` instead.

Usage:
    python _w1_rl_compare.py --arms rule=R1 llm=H1 pure-llm=P1 rl=RL1 \
        --rl-theta _w1_runs/rl/theta_rl_main1.npz [--seeds 7 11 13 17 19]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

IE_SET = [
    "IE-01-SINGLE-TARGET",
    "IE-02-DUAL-THREAT",
    "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS",
    "IE-05-MULTI-AXIS",
    "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN",
    "IE-08-ISLAND-STRIKE",
]
LAYERS = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")


def report_path(planner: str, scenario: str, tag: str, seed: int) -> Path:
    suffix = "" if seed == 7 else f"_s{seed}"
    return RUNS / f"ie_{planner.replace('-', '')}_{scenario.lower()}_{tag}{suffix}.json"


def load(planner: str, scenario: str, tag: str, seed: int) -> dict | None:
    path = report_path(planner, scenario, tag, seed)
    if not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    card = report.get("strategy_scorecard") or {}
    terminal = card.get("terminal") or {}
    ticks = int(report.get("ticks_run") or 0)
    row = {
        "file": path.name,
        "score": card.get("defender_score"),
        "layers": card.get("layers") or {},
        "outcome": terminal.get("outcome"),
        "consistent": terminal.get("consistent_with_evidence"),
        "ticks": ticks,
        "aborted": report.get("aborted"),
        "fires_blue": report.get("total_fires_defender"),
        "fires_red": report.get("total_fires_intruder"),
        "valid": ticks > 0 and terminal.get("outcome") not in (None, "undecided")
                 and not report.get("aborted"),
    }
    return row


def mean(values: list[float]) -> float | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    return sum(clean) / len(clean) if clean else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", nargs="+", required=True,
                        help="planner=TAG 形式，例如 rule=R1 llm=H1 pure-llm=P1 rl=RL1")
    parser.add_argument("--seeds", nargs="*", type=int, default=[7])
    parser.add_argument("--scenarios", nargs="*", default=IE_SET)
    parser.add_argument("--markdown", default=None,
                        help="把矩阵同时写入该 markdown 文件")
    args = parser.parse_args()

    arms = []
    for spec in args.arms:
        if "=" not in spec:
            print(f"!! --arms 项必须形如 planner=TAG：{spec}")
            return 2
        planner, tag = spec.split("=", 1)
        arms.append((planner, tag))

    lines: list[str] = []

    def emit(text: str = "") -> None:
        print(text)
        lines.append(text)

    for seed in args.seeds:
        emit(f"===== seed {seed} =====")
        header = f"{'scenario':<26}" + "".join(f"{p:>12}" for p, _ in arms)
        emit(header)
        emit("-" * len(header))
        for scenario in args.scenarios:
            cells = []
            for planner, tag in arms:
                row = load(planner, scenario, tag, seed)
                if row is None:
                    cells.append("no-file")
                elif not row["valid"]:
                    cells.append("FAIL")
                else:
                    cells.append(f"{row['score']:.4f}")
            emit(f"{scenario:<26}" + "".join(f"{c:>12}" for c in cells))
        emit()

        for planner, tag in arms:
            rows = [load(planner, s, tag, seed) for s in args.scenarios]
            good = [r for r in rows if r and r["valid"]]
            overall = mean([r["score"] for r in good])
            emit(f"-- {planner} (tag={tag}) valid {len(good)}/{len(rows)}"
                 + (f"  overall={overall:.4f}" if overall is not None else ""))
            if good:
                emit("   " + " ".join(
                    f"{name}={mean([r['layers'].get(name) for r in good]):.3f}"
                    if mean([r["layers"].get(name) for r in good]) is not None
                    else f"{name}=n/a" for name in LAYERS))
                emit(f"   ticks={mean([r['ticks'] for r in good]):.0f}"
                     f" fires_blue={mean([r['fires_blue'] for r in good]):.1f}"
                     f" fires_red={mean([r['fires_red'] for r in good]):.1f}"
                     f" terminal_consistent={sum(1 for r in good if r['consistent'])}"
                     f"/{len(good)}")
            bad = [r for r in rows if r and not r["valid"]]
            for row in bad:
                emit(f"   !! {row['file']}: ticks={row['ticks']} "
                     f"outcome={row['outcome']} aborted={str(row['aborted'])[:80]}")
        emit()

    # cross-seed summary
    if len(args.seeds) > 1:
        emit("===== seed-mean =====")
        for planner, tag in arms:
            per_scenario = []
            for scenario in args.scenarios:
                scores = [load(planner, scenario, tag, s) for s in args.seeds]
                valid = [r["score"] for r in scores
                         if r and r["valid"] and isinstance(r["score"], (int, float))]
                per_scenario.append((scenario, mean(valid), len(valid)))
            overall = mean([v for _, v, _ in per_scenario if v is not None])
            emit(f"-- {planner} (tag={tag}) overall="
                 + (f"{overall:.4f}" if overall is not None else "n/a"))
            for scenario, value, count in per_scenario:
                shown = f"{value:.4f}" if value is not None else "n/a"
                emit(f"   {scenario:<26}{shown:>10}  ({count}/{len(args.seeds)} seeds)")
        emit()

    if args.markdown:
        Path(args.markdown).write_text("```\n" + "\n".join(lines) + "\n```\n",
                                       encoding="utf-8")
        print(f"== 矩阵已写入 {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

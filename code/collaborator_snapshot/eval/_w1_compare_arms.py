"""Compare the ablation arms (rule / hybrid-LLM / pure-LLM) on one scorecard table.

Reads the ``--output`` reports produced by ``run_episode.py`` and prints:

  * the head-to-head overall strategy score per arm,
  * every scorecard layer side by side (so a reader can re-weight),
  * the raw evidence columns the layers are built from.

Usage:
    python _w1_compare_arms.py arm_rule.json arm_hybrid.json arm_pure.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from strategy_metrics import format_scorecard_line  # noqa: E402

LAYER_ORDER = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def arm_label(report: dict, path: Path) -> str:
    """标签用文件名（planner 名会重复，例如两个 LLM 臂都叫 llm）。"""

    stem = path.stem.replace("arm_", "")
    return stem[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    rows = []
    for path in args.reports:
        if not path.is_file():
            print(f"[skip] {path} 不存在")
            continue
        report = load(path)
        scorecard = report.get("strategy_scorecard")
        if not scorecard:
            print(f"[skip] {path} 没有 strategy_scorecard")
            continue
        rows.append((arm_label(report, path), report, scorecard))

    if not rows:
        print("没有可比较的结果")
        return 1

    lines: list[str] = []
    lines.append("=" * 132)
    lines.append("三臂对照（防守方视角；overall 越高越好）")
    lines.append("=" * 132)
    for label, _report, scorecard in rows:
        lines.append(format_scorecard_line(scorecard, label))

    lines.append("")
    lines.append("-" * 132)
    header = f"{'layer':<12}" + "".join(f"{label:>12}" for label, _, _ in rows)
    lines.append(header)
    lines.append("-" * 132)
    for layer in LAYER_ORDER:
        weight = rows[0][2]["layer_weights"][layer]
        cells = "".join(f"{sc['layers'][layer]:>12.3f}" for _l, _r, sc in rows)
        lines.append(f"{layer:<12}{cells}   (w={weight})")
    lines.append("-" * 132)
    lines.append(f"{'OVERALL':<12}" + "".join(
        f"{sc['defender_score']:>12.3f}" for _l, _r, sc in rows))

    lines.append("")
    lines.append("=" * 132)
    lines.append("原始证据")
    lines.append("=" * 132)
    evidence_rows = [
        ("ticks_run", lambda r, sc: r.get("ticks_run")),
        ("aborted", lambda r, sc: str(r.get("aborted"))[:40]),
        ("terminal", lambda r, sc: sc["terminal"]["state"]),
        ("terminal_tick", lambda r, sc: sc["terminal"]["tick"]),
        ("consistent", lambda r, sc: sc["terminal"]["consistent_with_evidence"]),
        ("executed_fires", lambda r, sc: r.get("total_fires")),
        ("shots_blue", lambda r, sc: sc["fire"]["by_faction"][
            "coalition.defender"]["shots"]),
        ("shots_red", lambda r, sc: sc["fire"]["by_faction"][
            "coalition.intruder"]["shots"]),
        ("uav_lost_blue", lambda r, sc: sc["force"]["coalition.defender"]["uav"]["lost"]),
        ("uav_lost_red", lambda r, sc: sc["force"]["coalition.intruder"]["uav"]["lost"]),
        ("usv_lost_blue", lambda r, sc: sc["force"]["coalition.defender"]["usv"]["lost"]),
        ("usv_lost_red", lambda r, sc: sc["force"]["coalition.intruder"]["usv"]["lost"]),
        ("intercept_rate", lambda r, sc: sc["air_layer"]["interception_rate"]),
        ("depth_mean_m", lambda r, sc: sc["air_layer"]["interception_depth_m"]["mean"]),
        ("depth_median_m", lambda r, sc: sc["air_layer"]["interception_depth_m"]["median"]),
        ("release_rate", lambda r, sc: sc["air_layer"]["release_rate"]),
        ("leak_rate", lambda r, sc: sc["air_layer"]["leak_rate"]),
        ("facility_survival", lambda r, sc: sc["facilities"]["weighted_survival"]),
        ("facilities_destroyed", lambda r, sc: sc["facilities"]["destroyed"]),
        ("defender_kills", lambda r, sc: sc["fire"]["defender_kills"]),
        ("attacker_kills", lambda r, sc: sc["fire"]["attacker_kills"]),
        ("def_shots_per_kill", lambda r, sc: sc["fire"]["defender_shots_per_kill"]),
        ("llm_calls", lambda r, sc: (r.get("defender", {}).get("planner", {}) or {}).get(
            "llm", {}).get("total_calls") if isinstance(
                (r.get("defender", {}).get("planner", {}) or {}).get("llm"), dict) else None),
        ("fallback_count", lambda r, sc: (r.get("defender", {}).get("planner", {}) or {}
                                          ).get("fallback_count")),
        ("parse_failures", lambda r, sc: ((r.get("defender", {}).get("planner", {}) or {}
                                           ).get("planner", {}) or {}).get("parse_failures")),
        ("elapsed_s", lambda r, sc: r.get("elapsed_seconds")),
    ]
    lines.append(f"{'metric':<20}" + "".join(f"{label:>18}" for label, _, _ in rows))
    lines.append("-" * 132)
    for name, getter in evidence_rows:
        cells = ""
        for _label, report, scorecard in rows:
            try:
                value = getter(report, scorecard)
            except Exception:  # noqa: BLE001
                value = "n/a"
            cells += f"{str(value):>18}"
        lines.append(f"{name:<20}{cells}")

    text = "\n".join(lines)
    print(text)
    if args.markdown:
        args.markdown.write_text("```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n已写入 {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

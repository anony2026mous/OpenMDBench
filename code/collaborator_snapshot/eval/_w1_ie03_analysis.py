"""IE-03 failure analysis across arms/seeds, from executed-shot evidence.

Reads every IE-03 report and prints the columns that actually explain an outcome:
executed shots, whether any raider died, ammo efficiency, the terminal RULE (not just
the outcome token), first fire tick, defender survival, and how often the executor's
own doctrine suppressed a shot.  The point is to separate "fired and missed" from
"never fired" from "blocked by its own overkill cap", which look identical in a
scorecard.

Usage:
    python _w1_ie03_analysis.py [--glob "*ie-03*"] [--extra ie03_llmrl_v9_seed*.json ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarise(path: Path, report: dict) -> dict:
    card = report.get("strategy_scorecard") or {}
    layers = card.get("layers") or {}
    term = card.get("terminal") or {}
    metrics = report.get("layered_metrics") or {}
    defender = report.get("defender") or {}
    executor = defender.get("executor") or {}
    planner = defender.get("planner") or {}
    doctrine = executor.get("doctrine") or {}
    adherence = executor.get("adherence") or {}
    meta = executor.get("checkpoint_meta") or {}
    theta = executor.get("theta") or ""
    arm = "llm-rl" if executor else (planner.get("planner") or "?")
    if executor and meta.get("goal_source") != "llm":
        arm = "rule-rl"
    return {
        "file": path.name,
        "arm": arm,
        "theta": Path(str(theta)).name if theta else "-",
        "seed": report.get("seed"),
        "score": card.get("defender_score"),
        "outcome": term.get("outcome"),
        "rule": term.get("rule_id"),
        "tick": term.get("tick"),
        "ticks_run": report.get("ticks_run"),
        "fires_def": report.get("total_fires_defender"),
        "fires_int": report.get("total_fires_intruder"),
        "kills": metrics.get("intruder_neutralized_count"),
        "ammo_eff": metrics.get("ammo_efficiency"),
        "first_fire": metrics.get("first_fire_tick_defender"),
        "survival": metrics.get("defender_survival_rate"),
        "facilities": layers.get("facilities"),
        "supp_overkill": doctrine.get("suppressed_overkill"),
        "supp_assess": doctrine.get("suppressed_assess"),
        "on_assigned": adherence.get("on_assigned_ratio"),
        "plans": planner.get("plan_calls"),
        "parse_fail": planner.get("parse_failures"),
        "aborted": "YES" if report.get("aborted") else "no",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", default="*ie-03*")
    parser.add_argument("--extra", nargs="*", default=None,
                        help="额外文件名（相对 _w1_runs），例如 ie03_llmrl_v9_seed*.json")
    args = parser.parse_args()

    paths: list[Path] = []
    for pattern in [args.glob] + (args.extra or []):
        paths.extend(sorted(RUNS.glob(pattern)))
    seen: set[str] = set()
    rows: list[dict] = []
    for path in paths:
        if path.name in seen or path.suffix == ".bak":
            continue
        seen.add(path.name)
        report = load(path)
        if not report:
            continue
        card = report.get("strategy_scorecard") or {}
        if card.get("defender_score") is None:
            continue
        rows.append(summarise(path, report))

    rows.sort(key=lambda r: (str(r["arm"]), str(r["seed"]), str(r["file"])))
    header = (f"{'arm':<8}{'seed':>5}{'score':>8}{'outcome':>18}{'rule':>26}"
              f"{'tick':>6}{'firesD':>7}{'kills':>6}{'ammoEff':>8}{'1stFire':>8}"
              f"{'surv':>7}{'fac':>6}{'suppOK':>7}{'adher':>7}{'theta':>34}")
    print(header)
    print("-" * len(header))
    for row in rows:
        def f(value, width, nd=3):
            if value is None:
                return f"{'-':>{width}}"
            if isinstance(value, float):
                return f"{value:>{width}.{nd}f}"
            return f"{value!s:>{width}}"
        print(f"{row['arm']:<8}{f(row['seed'], 5)}{f(row['score'], 8, 4)}"
              f"{str(row['outcome']):>18}{str(row['rule']):>26}"
              f"{f(row['ticks_run'], 6)}{f(row['fires_def'], 7)}{f(row['kills'], 6)}"
              f"{f(row['ammo_eff'], 8, 2)}{f(row['first_fire'], 8)}"
              f"{f(row['survival'], 7, 2)}{f(row['facilities'], 6, 2)}"
              f"{f(row['supp_overkill'], 7)}{f(row['on_assigned'], 7, 2)}"
              f"{row['theta']:>34}")
    print()
    print("读法：firesD=实际执行射击数；kills=intruder_neutralized_count；")
    print("      ammoEff=kills/firesD；1stFire=守方首次射击 tick；")
    print("      rule.assets-lost = 守方资产被打光（不是设施被毁）；")
    print("      suppOK=执行器自己的超杀上限压制次数（提交级计数，与是否命中无关）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

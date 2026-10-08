"""RL-only results table: the trained policy scored over the seed set.

Reads every ``ie_rl_<scenario>_<tag>*.json`` written by ``_w1_ie_sweep.py`` for
one RL tag and prints score / outcome / variance per scenario, with the recorded
rule baseline as a reference row.

Two things this deliberately does:
  * rejects rows that are not real episodes (``ticks_run <= 0``, no terminal
    outcome, ``aborted``), because ``run_episode`` writes a report even when the
    episode dies and a tick-0 abort was once scored 0.3889;
  * reports the outcome next to the score, so a low score can be read against the
    win/loss bands (measured: wins span 0.4008-1.0, losses 0.0556-0.4723) instead
    of being taken at face value.

Usage:
    python _w1_rl_report.py --tag rl_main5sto [--baseline p18]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from pathlib import Path

EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

SCENARIOS = [
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


def load(path: Path) -> dict | None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    card = report.get("strategy_scorecard") or {}
    terminal = card.get("terminal") or {}
    ticks = int(report.get("ticks_run") or 0)
    outcome = terminal.get("outcome")
    valid = (ticks > 0 and outcome not in (None, "undecided")
             and not report.get("aborted"))
    return {
        "file": path.name,
        "score": card.get("defender_score"),
        "layers": card.get("layers") or {},
        "outcome": outcome,
        "ticks": ticks,
        "fires_blue": report.get("total_fires_defender"),
        "fires_red": report.get("total_fires_intruder"),
        "valid": valid,
    }


def gather(planner: str, tag: str, scenario: str) -> list[dict]:
    """All stored runs for exactly ``planner``+``tag`` and scenario, across seeds.

    The tag MUST be part of the glob.  An earlier version built the pattern from
    ``planner_tag.split('=')[0]``, which dropped the tag entirely -- so the RL
    column silently averaged every RL checkpoint ever evaluated (n=8 where only 4
    files existed) and the rule column averaged ~60 calibration rounds.  The
    suffix is then checked to be either empty or ``_s<digits>`` so a tag that is a
    prefix of another tag cannot leak in either.
    """
    pattern = str(RUNS / f"ie_{planner}_{scenario.lower()}_{tag}*.json")
    prefix = f"ie_{planner}_{scenario.lower()}_{tag}"
    rows = []
    for path in sorted(glob.glob(pattern)):
        name = Path(path).name
        suffix = name[len(prefix):-len(".json")]
        if suffix and not re.fullmatch(r"_s\d+", suffix):
            continue                      # a different tag sharing this prefix
        row = load(Path(path))
        if row is None:
            continue
        match = re.search(r"_s(\d+)\.json$", name)
        row["seed"] = int(match.group(1)) if match else 7
        rows.append(row)
    return rows


def mean(values: list[float]) -> float | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    return sum(clean) / len(clean) if clean else None


def stdev(values: list[float]) -> float | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    if len(clean) < 2:
        return None
    mu = sum(clean) / len(clean)
    return (sum((v - mu) ** 2 for v in clean) / (len(clean) - 1)) ** 0.5


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="rl_main5sto",
                        help="RL tag; files are ie_rl_<scenario>_<tag>[_s<seed>].json")
    parser.add_argument("--baseline", default="rule_p18",
                        help="reference planner_tag for the 'vs' column (planner_tag)")
    parser.add_argument("--scenarios", nargs="*", default=SCENARIOS)
    args = parser.parse_args()
    render(args)
    return 0


def render(args) -> None:
    print(f"RL arm: planner=rl tag={args.tag}  (stochastic sampling; each row is one episode)")
    header = (f"{'scenario':<26}{'n':>3}{'mean':>9}{'sd':>7}{'min':>9}{'max':>9}"
              f"{'kept':>7}{'tick':>7}{'fires':>7}   vs rule/{args.baseline}")
    print(header)
    print("-" * len(header))
    rl_means, base_means = [], []
    for scenario in args.scenarios:
        all_rows = gather("rl", args.tag, scenario)
        rows = [r for r in all_rows if r["valid"]]
        scores = [r["score"] for r in rows]
        mu, sd = mean(scores), stdev(scores)
        if mu is not None:
            rl_means.append(mu)
        kept = sum(1 for r in rows if r["outcome"] == "defender_success")
        ticks = mean([r["ticks"] for r in rows])
        fires = mean([r["fires_blue"] for r in rows])
        base = [r for r in gather("rule", args.baseline, scenario) if r["valid"]]
        base_mu = mean([r["score"] for r in base])
        if base_mu is not None:
            base_means.append(base_mu)
        cells = [
            str(len(rows)),
            f"{mu:.4f}" if mu is not None else "n/a",
            f"{sd:.3f}" if sd is not None else "-",
            f"{min(scores):.4f}" if scores else "-",
            f"{max(scores):.4f}" if scores else "-",
            f"{kept}/{len(rows)}",
            f"{ticks:.0f}" if ticks is not None else "-",
            f"{fires:.1f}" if fires is not None else "-",
            f"{base_mu:.4f}(n={len(base)})" if base_mu is not None else "n/a",
        ]
        print(f"{scenario:<26}{cells[0]:>3}{cells[1]:>9}{cells[2]:>7}{cells[3]:>9}"
              f"{cells[4]:>9}{cells[5]:>7}{cells[6]:>7}{cells[7]:>7}   {cells[8]}")
        for row in all_rows:
            if not row["valid"]:
                print(f"      !! invalid {row['file']}: ticks={row['ticks']} "
                      f"outcome={row['outcome']}")
    print("-" * len(header))
    rl_all, base_all = mean(rl_means), mean(base_means)
    print(f"{'SCENARIO-MEAN':<26}{'':>3}"
          f"{(f'{rl_all:.4f}' if rl_all is not None else 'n/a'):>9}"
          f"{'':>23}{'':>7}{'':>7}   "
          f"{(f'{base_all:.4f}' if base_all is not None else 'n/a')}")

    print()
    print("layer means over all valid RL runs:")
    every = [r for s in args.scenarios for r in gather("rl", args.tag, s) if r["valid"]]
    if every:
        parts = []
        for name in LAYERS:
            value = mean([r["layers"].get(name) for r in every])
            parts.append(f"{name}={'n/a' if value is None else f'{value:.3f}'}")
        print("   " + "  ".join(parts))
        wins = sum(1 for r in every if r["outcome"] == "defender_success")
        print(f"   wins {wins}/{len(every)}")


if __name__ == "__main__":
    raise SystemExit(main())

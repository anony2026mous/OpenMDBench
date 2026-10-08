"""Option 1: the complete 2x2 (headroom tier x planning information) from the E1 gate-screening arms.

Design as the frozen protocol records it
---------------------------------------
* Both arms are the scripted rule planner with the same executor.  ``completion.json`` shows
  ``config.arm == "rule"`` and ``config.dose`` differing (``strong`` vs ``hold``), and
  ``attempt_manifest.json`` shows the invocation carries no LLM flags.  So the contrast is a
  goal-dose (planning-information) manipulation on one task family and one executor, which is
  what the 2x2 design asks for.
* Headroom axis: the four screened interceptor counts.  Their pure baselines span a narrow band,
  so the interaction is expected to be weak; the script reports it either way and never inflates
  it.

Honesty notes carried into the output
-------------------------------------
1. ``dose=hold`` rewrites every non-hold goal to ``hold`` (see the adapter's wrapper).  It is
   therefore "goal information withheld", not merely "less information".  The arms differ in
   behaviour as well as information, which is stated wherever the effect is reported.
2. Four tiers is the whole published grid for this contrast.  The headroom span is computed and
   printed rather than assumed adequate.

Usage:
    python e1_2x2_option1.py [--screen <gate-screening dir>] [--out-dir <dir>]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d2_headroom  # noqa: E402  (project bootstrap convention)

DEFAULT_SCREEN = Path("/mnt/QTJC/chenyi-codex/experiments/E1_device-b_v13_p01_20261004"
                      "/bundle/data/gate-screening")
DEFAULT_OUT = HERE / "artifacts/e4-scenario-family/analysis"
ARM_INFORMATION = "rule-strong-g1"   # goal dose supplied
ARM_WITHHELD = "rule-strong-g0"      # goal dose withheld
PRIMARY_FIELD = "performance_v"


def episode_value(seed_dir: Path) -> tuple[float | None, str]:
    """Return (performance_v, dose) for one episode directory."""
    report = seed_dir / "report.json"
    if not report.is_file():
        return None, ""
    try:
        payload = json.loads(report.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None, ""
    metrics = payload.get("layered_metrics") or {}
    value = metrics.get(PRIMARY_FIELD)
    dose = ""
    completion = seed_dir / "completion.json"
    if completion.is_file():
        try:
            dose = str((json.loads(completion.read_text(encoding="utf-8",
                                                         errors="replace"))
                        .get("config") or {}).get("dose") or "")
        except Exception:
            dose = ""
    return (float(value) if isinstance(value, (int, float)) else None), dose


def read_tier(root: Path, arm: str) -> dict[int, float]:
    values: dict[int, float] = {}
    arm_dir = root / arm
    if not arm_dir.is_dir():
        return values
    for seed_dir in sorted(arm_dir.iterdir()):
        if not seed_dir.is_dir() or not seed_dir.name.startswith("seed-"):
            continue
        try:
            seed = int(seed_dir.name.split("-")[-1])
        except ValueError:
            continue
        value, _ = episode_value(seed_dir)
        if value is not None:
            values[seed] = value
    return values


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def welch_ci(a: list[float], b: list[float], draws: int = 10000,
             seed: int = 20261003) -> tuple[float, float]:
    """Percentile bootstrap CI for mean(a) - mean(b), resampling each arm independently.

    Paired resampling is unavailable here: both arms share the same seed labels, but the
    episodes are independent runs, so the honest interval resamples arms separately.
    """
    rng = random.Random(seed)
    out = []
    for _ in range(draws):
        sa = [a[rng.randrange(len(a))] for _ in range(len(a))]
        sb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        out.append(sum(sa) / len(sa) - sum(sb) / len(sb))
    out.sort()
    return out[int(0.025 * draws)], out[int(0.975 * draws)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, default=DEFAULT_SCREEN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.screen.is_dir():
        raise SystemExit(f"gate-screening directory not found: {args.screen}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    tiers = sorted(p.name for p in args.screen.iterdir() if p.is_dir())
    cells = []
    for tier in tiers:
        root = args.screen / tier
        supplied = read_tier(root, ARM_INFORMATION)
        withheld = read_tier(root, ARM_WITHHELD)
        if not supplied or not withheld:
            print(f"skip {tier}: supplied={len(supplied)} withheld={len(withheld)}")
            continue
        seeds = sorted(set(supplied) & set(withheld))
        diffs = [supplied[s] - withheld[s] for s in seeds]
        lo, hi = welch_ci([supplied[s] for s in seeds], [withheld[s] for s in seeds])
        cells.append({
            "tier": tier,
            "n": len(seeds),
            "seeds": seeds,
            "information_supplied": round(mean(supplied.values()), 4),
            "information_withheld": round(mean(withheld.values()), 4),
            "effect": round(mean(diffs), 4),
            "ci_low": round(lo, 4),
            "ci_high": round(hi, 4),
            "significant": bool(lo > 0 or hi < 0),
            "per_seed_supplied": [round(supplied[s], 4) for s in seeds],
            "per_seed_withheld": [round(withheld[s], 4) for s in seeds],
            "per_seed_effect": [round(supplied[s] - withheld[s], 4) for s in seeds],
        })

    if not cells:
        raise SystemExit("no tier had both arms")

    cells.sort(key=lambda c: c["information_withheld"])  # ascending headroom
    bandwidth = cells[-1]["information_withheld"] - cells[0]["information_withheld"]

    print("=== 2x2（规划信息 × 数量档），rule 臂，同一执行器 ===")
    print(f"{'档位':<32}{'n':>3}{'信息多':>9}{'信息少':>9}{'效应':>9}{'95% CI':>18}")
    for cell in cells:
        print(f"{cell['tier']:<32}{cell['n']:>3}{cell['information_supplied']:>9.4f}"
              f"{cell['information_withheld']:>9.4f}{cell['effect']:>+9.4f}"
              f"{'[' + format(cell['ci_low'], '.3f') + ',' + format(cell['ci_high'], '.3f') + ']':>18}")
    print(f"\n纯基线（信息少）跨度: {cells[0]['information_withheld']:.4f} – "
          f"{cells[-1]['information_withheld']:.4f}  (带宽 {bandwidth:.4f})")

    # interaction: lowest-headroom tier vs highest-headroom tier, difference in differences
    low, high = cells[0], cells[-1]
    pooled_low = low["per_seed_effect"]
    pooled_high = high["per_seed_effect"]
    did_samples = []
    rng = random.Random(20261003)
    for _ in range(10000):
        a = [pooled_high[rng.randrange(len(pooled_high))] for _ in pooled_high]
        b = [pooled_low[rng.randrange(len(pooled_low))] for _ in pooled_low]
        did_samples.append(sum(a) / len(a) - sum(b) / len(b))
    did_samples.sort()
    did = sum(pooled_high) / len(pooled_high) - sum(pooled_low) / len(pooled_low)
    did_lo, did_hi = did_samples[250], did_samples[9750]
    interaction_significant = bool(did_lo > 0 or did_hi < 0)

    print(f"\n=== 交互效应（差中差）===")
    print(f"  最有 headroom: {high['tier']} (基线 {high['information_withheld']:.4f}) 效应 {high['effect']:+.4f}")
    print(f"  最少 headroom: {low['tier']} (基线 {low['information_withheld']:.4f}) 效应 {low['effect']:+.4f}")
    print(f"  交互 = {did:+.4f}  95% CI [{did_lo:+.4f}, {did_hi:+.4f}]  "
          f"{'显著' if interaction_significant else '不显著（CI 跨零）'}")

    payload_interaction = {
        "high_headroom_tier": high["tier"],
        "low_headroom_tier": low["tier"],
        "value": round(did, 4),
        "ci_low": round(did_lo, 4),
        "ci_high": round(did_hi, 4),
        "significant": interaction_significant,
        "bootstrap": {"draws": 10000, "seed": 20261003},
        "selection_rule": ("headroom proxied by the withheld-information baseline V; the "
                           "lowest-V tier is treated as least headroom and the highest-V tier "
                           "as most headroom"),
        "sensitivity_all_pairs": [],
    }

    # Sensitivity: the interaction depends on which two tiers are contrasted, so report every
    # pair instead of only the extreme one.
    print("\n=== 交互效应对所有档位对（敏感性）===")
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            a, b = cells[i], cells[j]
            samples = []
            rng2 = random.Random(20261003)
            ea, eb = a["per_seed_effect"], b["per_seed_effect"]
            for _ in range(2000):
                sa = [eb[rng2.randrange(len(eb))] for _ in eb]
                sb = [ea[rng2.randrange(len(ea))] for _ in ea]
                samples.append(sum(sa) / len(sa) - sum(sb) / len(sb))
            samples.sort()
            val = mean(eb) - mean(ea)
            lo2, hi2 = samples[50], samples[1950]
            sig = bool(lo2 > 0 or hi2 < 0)
            payload_interaction["sensitivity_all_pairs"].append({
                "tier_more_headroom": b["tier"],
                "tier_less_headroom": a["tier"],
                "interaction": round(val, 4),
                "ci_low": round(lo2, 4),
                "ci_high": round(hi2, 4),
                "significant": sig,
            })
            print(f"  {a['tier'][-4:]} vs {b['tier'][-4:]}: {val:+.4f} "
                  f"[{lo2:+.4f}, {hi2:+.4f}] {'显著' if sig else '—'}")

    payload = {
        "schema": "e1-2x2-option1@1",
        "screen_root": str(args.screen),
        "arm_information_supplied": ARM_INFORMATION,
        "arm_information_withheld": ARM_WITHHELD,
        "primary_field": f"report.json:layered_metrics.{PRIMARY_FIELD}",
        "design": ("scripted rule planner, same executor; arms differ only in goal dose "
                   "(strong vs hold)"),
        "caveats": [
            "dose=hold rewrites non-hold goals to hold, so the arms differ in behaviour as well "
            "as in information; the effect is 'goal information supplied vs withheld', not a "
            "pure information delta",
            "four tiers is the entire screened grid for this contrast",
            f"pure-baseline bandwidth across tiers is {bandwidth:.4f}, which limits how much "
            "headroom contrast the interaction can express",
        ],
        "headroom_bandwidth": round(bandwidth, 4),
        "cells": cells,
        "interaction": payload_interaction,
        "per_cell_bootstrap": {"draws": 10000, "seed": 20261003,
                               "implementation": "independent-arm resampling"},
    }
    out = args.out_dir / "e1_2x2_option1.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main()

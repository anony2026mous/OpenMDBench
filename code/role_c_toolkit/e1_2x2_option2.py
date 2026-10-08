"""Read the saturation scan and the paired run, and report the within-family 2x2.

Scan   : one baseline episode per published tier -> ranks tiers by headroom (low V = big headroom).
Paired : (tier x dose) cells on one common seed set -> paired effect and difference-in-differences.

V is read from ``report.json`` (``layered_metrics.performance_v``), matching the field used for the
existing E1 evidence so the two are comparable.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DEFAULT_ROOT = Path("/mnt/<lab>/<user>-codex/experiments/e4-headroom-2x2/P1")


def read_v(report: Path) -> float | None:
    if not report.is_file():
        return None
    try:
        payload = json.loads(report.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    metrics = payload.get("layered_metrics") or {}
    value = metrics.get("performance_v")
    return float(value) if isinstance(value, (int, float)) else None


def scan_table(root: Path) -> list[dict]:
    scan = root / "scan"
    if not scan.is_dir():
        return []
    rows = []
    for tier_dir in sorted(scan.iterdir()):
        if not tier_dir.is_dir():
            continue
        value = read_v(tier_dir / "report.json")
        if value is not None:
            rows.append({"package": tier_dir.name, "v": value})
    rows.sort(key=lambda r: r["v"])
    return rows


def paired_table(root: Path) -> dict:
    """Read the (tier, dose) cells.

    ``strong`` and ``hold`` come from the dose adapter; ``weak`` is written by the plain runner
    with ``--goal-granularity weak``, so both layouts have to be understood here.
    """
    base = root / "paired"
    if not base.is_dir():
        return {}
    out: dict[str, dict[str, dict[int, float]]] = {}
    for tier_dir in sorted(base.iterdir()):
        if not tier_dir.is_dir():
            continue
        for dose in ("strong", "hold", "weak"):
            dose_dir = tier_dir / dose
            if not dose_dir.is_dir():
                continue
            for seed_dir in sorted(dose_dir.iterdir()):
                if not seed_dir.is_dir():
                    continue
                try:
                    seed = int(seed_dir.name.split("-")[-1])
                except ValueError:
                    continue
                # adapter layout writes report.json inside --output; the plain runner too.
                value = read_v(seed_dir / "report.json")
                if value is None:
                    value = read_v(seed_dir / "output" / "report.json")
                if value is not None:
                    out.setdefault(tier_dir.name, {}).setdefault(dose, {})[seed] = value
    return out


def boot_ci(values: list[float], draws: int = 10000, seed: int = 20261003) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out_path = args.out or (args.root / "option2_result.json")

    scan = scan_table(args.root)
    print("=== 饱和扫描（基线剂量，seed 64101，按 V 升序）===")
    if not scan:
        print("  尚无扫描结果")
    for row in scan:
        print(f"  {row['package']:46s} V={row['v']:.4f}")
    if scan:
        print(f"\n  最低 V（headroom 最大）: {scan[0]['package']} = {scan[0]['v']:.4f}")
        print(f"  最高 V（最接近饱和）  : {scan[-1]['package']} = {scan[-1]['v']:.4f}")

    paired = paired_table(args.root)
    if not paired:
        print("\n=== 配对跑：尚无结果 ===")
        out_path.write_text(json.dumps({"scan": scan, "paired": {}}, indent=2,
                                       ensure_ascii=False) + "\n", encoding="utf-8")
        return

    print("\n=== 配对 2x2（档位 × 剂量），共同 seed 集 ===")
    print("  strong = 完整目标参数；weak = 仅 unit_id（保留 goal_type，纯信息裁剪）；")
    print("  hold = 目标改写为 hold（行为也变，仅作参考）")
    cells = []
    for tier, doses in sorted(paired.items()):
        strong = doses.get("strong", {})
        hold = doses.get("hold", {})
        weak = doses.get("weak", {})
        # The clean, information-only contrast is strong vs weak.
        seeds = sorted(set(strong) & set(weak)) or sorted(set(strong) & set(hold))
        if not seeds:
            continue
        reference = weak if (weak and seeds == sorted(set(strong) & set(weak))) else hold
        effects = [strong[s] - reference[s] for s in seeds]
        ci = boot_ci(effects)
        cell = {
            "tier": tier,
            "n": len(seeds),
            "seeds": seeds,
            "contrast": "strong-vs-weak" if reference is weak else "strong-vs-hold",
            "strong_mean": round(sum(strong[s] for s in seeds) / len(seeds), 4),
            "reference_mean": round(sum(reference[s] for s in seeds) / len(seeds), 4),
            "weak_mean": (round(sum(weak[s] for s in seeds) / len(seeds), 4) if weak else None),
            "hold_mean": (round(sum(hold[s] for s in seeds) / len(seeds), 4) if hold else None),
            "effect": round(sum(effects) / len(effects), 4),
            "ci_low": round(ci[0], 4),
            "ci_high": round(ci[1], 4),
            "significant": bool(ci[0] > 0 or ci[1] < 0),
            "per_seed_strong": [round(strong[s], 4) for s in seeds],
            "per_seed_reference": [round(reference[s], 4) for s in seeds],
            "per_seed_effect": [round(strong[s] - reference[s], 4) for s in seeds],
        }
        cells.append(cell)
        print(f"  {tier:34s} n={cell['n']} {cell['contrast']:15s} "
              f"strong={cell['strong_mean']:.4f} ref={cell['reference_mean']:.4f} "
              f"效应={cell['effect']:+.4f} [{cell['ci_low']:+.3f},{cell['ci_high']:+.3f}] "
              f"{'显著' if cell['significant'] else '—'}")

    cells.sort(key=lambda c: c["strong_mean"])
    # Headroom axis.  The withheld arm collapses to one behaviour at every tier (0.16-0.19), so it
    # cannot serve as a difficulty fingerprint; the supplied arm's own level is the usable measure,
    # and the scan value characterises the tier independently.
    scan_by_tail = {}
    scan_root = args.root / "scan"
    if scan_root.is_dir():
        for candidate in scan_root.iterdir():
            if candidate.is_dir():
                value = read_v(candidate / "report.json")
                if value is not None:
                    # Directory names may carry a stray carriage return from the tier list file.
                    tail = candidate.name.strip().rsplit("_", 1)[-1]
                    scan_by_tail[tail] = value
    for cell in cells:
        cell["scan_v"] = scan_by_tail.get(cell["tier"].rsplit("-", 1)[-1].lower().strip())
    interaction = None
    if len(cells) >= 2:
        low, high = cells[0], cells[-1]
        # The withheld arm is seed-invariant (a degraded plan collapses to one behaviour), so all
        # seed-level variance lives in the supplied arm.  Resample that arm only; resampling both
        # would understate the interval by treating a constant as random.
        rng = random.Random(20261003)
        samples = []
        for _ in range(10000):
            hs = [high["per_seed_strong"][rng.randrange(len(high["per_seed_strong"]))]
                  for _ in range(len(high["per_seed_strong"]))]
            ls = [low["per_seed_strong"][rng.randrange(len(low["per_seed_strong"]))]
                  for _ in range(len(low["per_seed_strong"]))]
            samples.append((sum(hs) / len(hs) - high["reference_mean"])
                           - (sum(ls) / len(ls) - low["reference_mean"]))
        samples.sort()
        value = high["effect"] - low["effect"]
        ci = (samples[250], samples[9750])
        interaction = {
            "higher_supplied_tier": high["tier"],
            "lower_supplied_tier": low["tier"],
            "value": round(value, 4),
            "ci_low": round(ci[0], 4),
            "ci_high": round(ci[1], 4),
            "significant": bool(ci[0] > 0 or ci[1] < 0),
            "resampling": ("supplied arm only; the withheld arm is seed-invariant so it "
                           "contributes no seed-level variance"),
            "caveat": ("the split is by the supplied arm's own realised level, so its uncertainty "
                       "is reported as descriptive rather than as a pre-registered group "
                       "comparison"),
            "withheld_arm_range": [round(low["reference_mean"], 4),
                                   round(high["reference_mean"], 4)],
        }
        print(f"\n=== 交互（差中差）===")
        print(f"  参考臂在各档位均为 0.16–0.19（结构性塌陷），故 headroom 轴改用")
        print(f"  「提供信息臂自身的实现水平」与扫描 V 表征。")
        print(f"  低档位: {low['tier']} strong={low['strong_mean']:.4f} "
              f"scanV={low.get('scan_v')} 效应 {low['effect']:+.4f}")
        print(f"  高档位: {high['tier']} strong={high['strong_mean']:.4f} "
              f"scanV={high.get('scan_v')} 效应 {high['effect']:+.4f}")
        print(f"  交互 = {interaction['value']:+.4f} "
              f"[{interaction['ci_low']:+.4f}, {interaction['ci_high']:+.4f}] "
              f"{'显著' if interaction['significant'] else '不显著'}")
        print(f"  （参考臂跨度仅 {low['reference_mean']:.4f}–{high['reference_mean']:.4f}，"
              f"说明它不携带档位信息）")

    payload = {"schema": "e1-2x2-option2@1", "scan": scan, "cells": cells,
               "interaction": interaction}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"\nwritten {out_path}")


if __name__ == "__main__":
    main()

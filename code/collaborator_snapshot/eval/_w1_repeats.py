"""Repeated-run statistics for the LLM-driven arms.

WHY THIS EXISTS.  Measured on IE-03: the FROZEN arm produced 1.0000 and 0.5947 on the
SAME scenario and SAME seed.  The LLM samples, so one reading per (arm, scenario, seed)
is not a measurement of the arm -- it is one draw.  Every earlier "A is better than B"
claim in this project that rested on a single reading per cell is therefore
under-powered, including two of mine (retracted in LLMRL_CURRENT_AUDIT.md).

So this tool reports, per configuration:

  * within-cell spread  -- per (scenario, seed): n, mean, sd, range
  * pooled within-cell sd -- the smallest difference that is worth talking about
  * paired differences  -- same scenario+seed, configuration minus reference
  * the verdict rule    -- |mean difference| must exceed 2 x pooled sd AND have the
                           same sign on every repeat pair before it is called a result

Usage:
    python _w1_repeats.py --cell "frozen=ie_llm_ie-03-surface-raid_(v10_eval_s11|p0c)" ...
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")


def parse_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise SystemExit(f"--cell needs label=<glob>, got {spec!r}")
    label, glob = spec.split("=", 1)
    return label.strip(), glob.strip()


def classify(path: Path, report: dict) -> tuple[str, int]:
    """(configuration label, seed) from the report and file name."""
    executor = (report.get("defender") or {}).get("executor") or {}
    if executor:
        theta = Path(str(executor.get("theta") or "")).name
        mode = "REL" if executor.get("overkill_release") else "cap"
        label = f"rl[{mode}:{theta.replace('theta_', '').replace('.npz', '')}]"
    else:
        label = "llm(frozen)"
    seed = report.get("seed")
    if seed is None:
        match = re.search(r"_s(\d+)$", path.stem)
        seed = int(match.group(1)) if match else 7
    return label, int(seed)


def collect(patterns: list[str]) -> dict[tuple[str, int], list[tuple[float, str]]]:
    cells: dict[tuple[str, int], list[tuple[float, str]]] = defaultdict(list)
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(RUNS.glob(pattern)):
            if path.name in seen or path.suffix == ".bak":
                continue
            seen.add(path.name)
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(report, dict):
                continue
            card = report.get("strategy_scorecard") or {}
            score = card.get("defender_score")
            terminal = (card.get("terminal") or {}).get("outcome")
            if score is None or terminal in (None, "undecided") or report.get("aborted"):
                continue
            label, seed = classify(path, report)
            cells[(label, seed)].append((float(score), path.name))
    return cells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", action="append", required=True,
                        help="label=<glob>，glob 决定把哪些报告算作同一配置")
    parser.add_argument("--scenario", default="ie-03")
    parser.add_argument("--reference", default=None,
                        help="作为参照的 label 前缀（用于配对差）")
    args = parser.parse_args()

    # 一个标签可以对应**多个** glob（同一配置的读数分散在不同命名里，
    # 例如冻结臂既有 `ie03_llm_seed11.json` 又有 `ie_llm_ie-03-..._v10_eval_s11.json`）。
    # 用 dict 会在同名标签上互相覆盖 —— 第一次就因此把 n=2 的格子显示成 n=1。
    specs: dict[str, list[str]] = defaultdict(list)
    for item in args.cell:
        label, glob = parse_spec(item)
        specs[label].append(glob)

    rows: dict[tuple[str, int], list[tuple[float, str]]] = defaultdict(list)
    for label, globs in specs.items():
        for key, values in collect(globs).items():
            rows[(label, key[1])].extend(values)

    print(f"=== 每格（场景含 '{args.scenario}'）重复读数 ===")
    header = f"{'config':<34}{'seed':>5}{'n':>3}{'mean':>9}{'sd':>8}{'min':>9}{'max':>9}   files"
    print(header)
    print("-" * len(header))
    pooled: list[float] = []
    for (label, seed) in sorted(rows):
        values = [v for v, _ in rows[(label, seed)]]
        if not values:
            continue
        mean = statistics.fmean(values)
        sd = statistics.stdev(values) if len(values) > 1 else float("nan")
        if len(values) > 1:
            pooled.append(sd)
        names = ",".join(n[:26] for _, n in rows[(label, seed)][:2])
        print(f"{label:<34}{seed:>5}{len(values):>3}{mean:>9.4f}"
              f"{(sd if not math.isnan(sd) else 0):>8.4f}"
              f"{min(values):>9.4f}{max(values):>9.4f}   {names}")

    if pooled:
        pool_sd = statistics.fmean(pooled)
        print(f"\n  合并格内 sd = {pool_sd:.4f}（只有超过 {2*pool_sd:.4f} 的差才值得讨论）")
    else:
        pool_sd = None
        print("\n  还没有任何格子有 n≥2，无法估计格内方差 —— 此时任何比较都不可判读")

    if args.reference:
        print(f"\n=== 配对差（同 seed，减去参照 {args.reference}）===")
        labels = sorted({label for label, _ in rows})
        for label in labels:
            if label == args.reference:
                continue
            diffs = []
            for (other_label, seed) in sorted(rows):
                if other_label != label:
                    continue
                ref_values = [v for v, _ in rows.get((args.reference, seed), [])]
                if not ref_values:
                    continue
                mine = [v for v, _ in rows[(other_label, seed)]]
                diffs.append((seed, statistics.fmean(mine) - statistics.fmean(ref_values),
                              len(mine), len(ref_values)))
            for seed, diff, n_mine, n_ref in diffs:
                verdict = "不可判读" if pool_sd is None or abs(diff) <= 2 * pool_sd \
                    else ("** 信号 **" if diff > 0 else "** 反号 **")
                print(f"  seed={seed:<4} {label:<34} - {args.reference:<20} "
                      f"= {diff:+.4f}  (n={n_mine} vs {n_ref})  {verdict}")
    print()
    print("规则：|差| > 2×合并格内 sd 才算信号；同号重复才可信。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

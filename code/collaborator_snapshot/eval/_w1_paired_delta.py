"""配对差值汇总：A − B，逐场景 × 逐种子，带符号检验。

和 `_w1_paired_table.py` 的分工：那张表回答"这一格里各臂分别是什么"，本脚本回答
"**臂 A 是否稳定地优于臂 B**"。做法是同 (场景, 种子) 配对求差，再逐场景汇总：

* `rule` / `rl` 在给定种子上基本是定值，所以配对差把"场景难度"整体消掉，
  剩下的就是臂差异 + LLM 采样噪声。
* 逐场景报 wins/losses/ties、平均差、以及**符号检验**的精确 p 值
  （n 小的时候比 t 检验更稳，且不假设正态）。
* 绝不跨 tag 平均：每个臂必须显式给出 (family, tag)，留空则收该 family 的全部 tag
  并**分别**列出，不做合并。

用法::

    python _w1_paired_delta.py --a rule-rl:arm5_v12=pv12 --b rule=p18
    python _w1_paired_delta.py --a rule-rl:arm5_v12=pv12 --b rule=p18 --seed 7 11 13
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import pathlib
import re

from _w1_paired_table import load          # 复用同一套过滤器（口径 + tag 纪律）


def _parse(spec: str) -> tuple[str, str | None]:
    """`family` 或 `family=tag`。"""
    family, _, tag = spec.partition("=")
    return family, (tag or None)


def _binom_two_sided(wins: int, losses: int) -> float:
    """符号检验（精确二项，p=0.5），丢掉 ties。"""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="臂 A：family 或 family=tag")
    parser.add_argument("--b", required=True, help="臂 B：family 或 family=tag")
    parser.add_argument("--scenario", nargs="*", default=None)
    parser.add_argument("--seed", nargs="*", type=int, default=None)
    args = parser.parse_args()

    fam_a, tag_a = _parse(args.a)
    fam_b, tag_b = _parse(args.b)
    rows = load()

    def pick(family: str, tag: str | None):
        out = collections.defaultdict(list)
        for row in rows:
            if row["family"] != family:
                continue
            if tag is not None and row["tag"] != tag:
                continue
            if args.scenario and row["scenario"] not in args.scenario:
                continue
            if args.seed and row["seed"] not in args.seed:
                continue
            out[(row["scenario"], row["seed"], row["tag"])].append(row["score"])
        return out

    a = pick(fam_a, tag_a)
    b = pick(fam_b, tag_b)
    keys = sorted(set((s, sd) for (s, sd, _t) in a) & set((s, sd) for (s, sd, _t) in b))
    if not keys:
        print(f"没有配对格：{args.a} vs {args.b}（检查 tag 与场景过滤）")
        return 1

    print(f"A = {args.a}   B = {args.b}")
    print(f"{'场景':28} {'seed':>4} {'nA':>3} {'nB':>3} {'meanA':>8} {'meanB':>8} {'Δ':>8}")
    print("-" * 74)
    per_scenario: dict = collections.defaultdict(list)
    for scenario, seed in keys:
        va = [v for (s, sd, _t), vals in a.items() if s == scenario and sd == seed for v in vals]
        vb = [v for (s, sd, _t), vals in b.items() if s == scenario and sd == seed for v in vals]
        mean_a, mean_b = sum(va) / len(va), sum(vb) / len(vb)
        delta = mean_a - mean_b
        per_scenario[scenario].append((seed, delta, len(va), len(vb)))
        print(f"{scenario:28} {seed:>4} {len(va):>3} {len(vb):>3} "
              f"{mean_a:>8.4f} {mean_b:>8.4f} {delta:>+8.4f}")

    print()
    print(f"{'场景':28} {'格数':>4} {'胜':>3} {'负':>3} {'平':>3} {'平均Δ':>8} {'符号检验 p':>10}")
    print("-" * 74)
    total_w = total_l = 0
    for scenario in sorted(per_scenario):
        deltas = [d for (_s, d, _na, _nb) in per_scenario[scenario]]
        wins = sum(1 for d in deltas if d > 1e-9)
        losses = sum(1 for d in deltas if d < -1e-9)
        ties = len(deltas) - wins - losses
        total_w += wins
        total_l += losses
        p = _binom_two_sided(wins, losses)
        print(f"{scenario:28} {len(deltas):>4} {wins:>3} {losses:>3} {ties:>3} "
              f"{sum(deltas) / len(deltas):>+8.4f} {p:>10.4f}")
    print("-" * 74)
    print(f"{'合计':28} {'':>4} {total_w:>3} {total_l:>3} {'':>3} {'':>8} "
          f"{_binom_two_sided(total_w, total_l):>10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

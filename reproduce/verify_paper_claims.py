"""Verify the numeric claims in the paper's rewritten (审阅) sentences.

The 审阅 pass rephrased the headline claims and attached numbers to them -- "each layered
stack beats the Rule baseline in 11 of 14 scenarios", "the stricter every-seed criterion
is satisfied in 8/14 LLM+Rule and 9/14 LLM+RL (17/28 overall)", "pure LLM trails LLM+Rule
on 14/14 (median deficit 0.33)". Those numbers are derived from tab:hifi_main, but the
derivation appears nowhere: the paper states them and the 70/70 table check does not cover
them, because they are counts over the table rather than cells of it.

This script recomputes each one from the released episodes and reports which agree.

Two findings worth naming up front:

  * "11 of 14" and "12 of 14" are PER-STACK counts. Each layered stack individually beats
    Rule in 11 and RL in 12. Taking the better of the two stacks per scenario would give
    13/14 against both, which is a different and more flattering number; the paper does
    not use it.
  * The every-seed-win rule is never stated. The natural reading -- all five seeds of the
    stack beat the baseline's own mean -- gives 4/14 and 8/14, not the printed 8/14 and
    9/14. Ten other readings were tested and none reproduces the pair.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reproduce"))
import _w1_common as c  # noqa: E402

PAPER_SEEDS = (7, 11, 13, 17, 19)
LAYERED = ("llm-rule", "llm-rl")
END_TO_END = "pure-llm"
BAND = {"llm-rule": (0.77, 0.78), "llm-rl": (0.77, 0.78),
        "rule-rule": (0.63, 0.72), "rl": (0.63, 0.72), END_TO_END: (0.43, 0.43)}


def build():
    by = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
    base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)
    table: dict[str, dict[str, float]] = {}
    for sc in c.IE:
        row: dict[str, float] = {}
        for arm in c.ARMS:
            if arm in c.LLM_ARMS:
                v = [x for sd in PAPER_SEEDS for x in by.get((sc, arm), {}).get(sd, [])]
            else:
                v = c.vals(base, sc, arm)
            if v:
                row[arm] = st.mean(v)
        table[sc] = row
    return by, base, table


def main() -> int:
    by, base, T = build()

    def seeds(sc, arm):
        return [x for sd in PAPER_SEEDS for x in by.get((sc, arm), {}).get(sd, [])]

    def mean_win(arm, baseline):
        ok = tot = 0
        for sc in c.IE:
            a, b = T.get(sc, {}).get(arm), T.get(sc, {}).get(baseline)
            if a is None or b is None:
                continue
            tot += 1
            ok += a > b
        return ok, tot

    def cross_stack_win(baseline):
        ok = tot = 0
        for sc in c.IE:
            b = T.get(sc, {}).get(baseline)
            v = [T[sc][a] for a in LAYERED if a in T.get(sc, {})]
            if b is None or not v:
                continue
            tot += 1
            ok += max(v) > b
        return ok, tot

    def every_seed_win(arm, baseline):
        ok = tot = 0
        for sc in c.IE:
            a, b = seeds(sc, arm), c.vals(base, sc, baseline)
            if not a or not b:
                continue
            tot += 1
            bm = st.mean(b)
            ok += all(x > bm for x in a)
        return ok, tot

    def overall(arm):
        v = [T[sc][arm] for sc in c.IE if arm in T.get(sc, {})]
        return st.mean(v) if v else None

    fails = 0
    print("=" * 98)
    print("PAPER CLAIM CHECK  --  the 审阅 rewrite's numeric assertions")
    print("=" * 98)

    print("\n  --- A. layered stacks vs the two baselines ---")
    for arm in LAYERED:
        for b in ("rule-rule", "rl"):
            ok, tot = mean_win(arm, b)
            print(f"     {arm:<10} vs {b:<10} {ok}/{tot}")
    for b in ("rule-rule", "rl"):
        ok, tot = cross_stack_win(b)
        print(f"     {'best of both':<10} vs {b:<10} {ok}/{tot}"
              f"   (per-scenario max; the paper does NOT use this)")

    print("\n  --- B. claims that reproduce exactly ---")
    for arm in ("llm-rule", "llm-rl", "rule-rule", "rl", END_TO_END):
        m = overall(arm)
        if m is None:
            continue
        lo, hi = BAND[arm]
        ok = lo - 0.005 <= m <= hi + 0.005
        fails += not ok
        print(f"     overall {arm:<10} {m:.3f}   paper {lo}-{hi}"
              f"{'' if ok else '   <-- DIFFERS'}")

    diffs = [T[sc]["llm-rule"] - T[sc][END_TO_END] for sc in c.IE
             if END_TO_END in T.get(sc, {}) and "llm-rule" in T.get(sc, {})]
    behind, med = sum(1 for x in diffs if x > 0), st.median(diffs)
    ok1, ok2 = behind == len(diffs), abs(med - 0.33) <= 0.005
    fails += (not ok1) + (not ok2)
    print(f"     pure-llm behind llm-rule on {behind}/{len(diffs)}   paper 14/14"
          f"{'' if ok1 else '   <-- DIFFERS'}")
    print(f"     median deficit {med:.3f}   paper 0.33"
          f"{'' if ok2 else '   <-- DIFFERS'}")

    print("\n  --- C. every-seed-win (rule not stated in the paper) ---")
    for arm, b, want in (("llm-rule", "rule-rule", 8), ("llm-rl", "rl", 9)):
        got, tot = every_seed_win(arm, b)
        good = got == want
        fails += not good
        print(f"     {arm:<10} vs {b:<10} {got}/{tot}   paper {want}/{tot}"
              f"{'' if good else '   <-- DIFFERS'}")
    print("     natural reading = all five seeds beat the baseline mean; the paper's")
    print("     printed pair (8/14, 9/14) is not reproduced by this or by any of the ten")
    print("     other readings tested (seed-count thresholds, quantile thresholds, and")
    print("     max/min/median variants).")

    print(f"\n  claims differing from the paper: {fails}")
    return fails


if __name__ == "__main__":
    raise SystemExit(main())

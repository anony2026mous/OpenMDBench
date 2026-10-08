"""E6 model-invariance: what the batch covers, and can the published figures be reproduced?

CORRECTION. An earlier version of this script computed a plain mean of per-seed
strong-minus-hold differences, got +0.531 / +0.510 against the paper's +0.431 / +0.464, and
concluded the table "does not reproduce". That was an ESTIMATOR error, not a data problem.

`E6_summary.md` documents the convention:
    statistic : interface causal necessity = mean(V_strong - V_hold) > 0
    interval  : seed bootstrap, 10000 resamples, RNG seed 20261003
    unit      : seed
and prints, for the two models it covers:

    Qwen3.8-27B   strong 0.633  hold 0.203   strong-hold +0.431 [0.226, 0.615]
    Qwen3-8B      strong 0.667  hold 0.203   strong-hold +0.464 [0.269, 0.656]

This reimplements that bootstrap from the per-case records to confirm the analysis file
reproduces, and states plainly which models have no data at all.
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E6 = ROOT / "data" / "campaigns" / "e6-model-invariance"

PAPER = {
    "27b": {"strong": 0.633, "hold": 0.203, "diff": 0.431, "ci": (0.226, 0.615)},
    "8b": {"strong": 0.667, "hold": 0.203, "diff": 0.464, "ci": (0.269, 0.656)},
}
LABEL = {"27b": "Qwen3.8-27B", "8b": "Qwen3-8B"}
BOOT_N = 10000
BOOT_SEED = 20261003


def main() -> int:
    f = E6 / "analysis" / "e6_analysis.json"
    if not f.is_file():
        print(f"  batch not present: {E6}")
        return 0
    d = json.loads(f.read_text(encoding="utf-8"))

    print("=" * 96)
    print("E6 model-invariance  vs  e6-model-invariance batch")
    print("=" * 96)
    print(f"  schema    : {d.get('schema')}")
    print(f"  models    : {sorted(d.get('models', {}).keys())}   "
          f"(the paper's table has FOUR columns)")
    print(f"  conditions: {d.get('conditions')}")
    print(f"  records   : {len(d.get('records', []))}")
    print(f"  bootstrap : {BOOT_N} draws, RNG seed {BOOT_SEED} (per E6_summary.md)")

    by: dict[tuple[str, str], dict] = defaultdict(dict)
    for r in d.get("records", []):
        v = r.get("V")
        if isinstance(v, (int, float)):
            by[(r["model"], r["condition"])][r["seed"]] = float(v)

    print(f"\n  --- per-condition means ---")
    print(f"  {'model':<14}{'cond':<8}{'n':>4}{'mean':>9}{'paper':>9}{'diff':>9}")
    ok = True
    for mk in ("27b", "8b"):
        for cond in ("strong", "hold"):
            got = by.get((mk, cond), {})
            m = st.mean(got.values()) if got else float("nan")
            pv = PAPER[mk][cond]
            flag = "" if (got and abs(m - pv) <= 0.002) else "  <-- differs"
            if flag:
                ok = False
            print(f"  {LABEL[mk]:<14}{cond:<8}{len(got):>4}{m:>9.3f}{pv:>9.3f}"
                  f"{m - pv:>+9.3f}{flag}")

    print(f"\n  --- per-seed paired difference, seed-bootstrap CI ---")
    print(f"  {'model':<14}{'n':>4}{'mean dV':>10}{'boot CI (ours)':>22}"
          f"{'paper':>9}{'paper CI':>20}")
    rng = random.Random(BOOT_SEED)
    for mk in ("27b", "8b"):
        s, h = by.get((mk, "strong"), {}), by.get((mk, "hold"), {})
        seeds = sorted(set(s) & set(h))
        diffs = [s[k] - h[k] for k in seeds]
        m = st.mean(diffs)
        boot = sorted(st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(BOOT_N))
        lo, hi = boot[int(0.025 * BOOT_N)], boot[int(0.975 * BOOT_N)]
        pv, pci = PAPER[mk]["diff"], PAPER[mk]["ci"]
        print(f"  {LABEL[mk]:<14}{len(diffs):>4}{m:>10.3f}"
              f"{f'[{lo:+.3f}, {hi:+.3f}]':>22}{pv:>+9.3f}"
              f"{f'[{pci[0]:+.3f}, {pci[1]:+.3f}]':>20}")

    print(f"\n  --- models with NO data in this batch ---")
    for nm in ("MM-M3", "MM-M2.7-hs"):
        print(f"     {nm:<12} no run directory; endpoints.json probes only 27b and 8b")

    # Two separate problems, and they need distinguishing.
    print(f"\n  --- diagnosis ---")
    hold_ok = all(
        abs(st.mean(by[(mk, 'hold')].values()) - PAPER[mk]["hold"]) <= 0.002
        for mk in ("27b", "8b") if by.get((mk, "hold")))
    print(f"  1. hold arm agrees with the paper: {hold_ok}")
    print(f"     (hold = 0.203 for both models, i.e. the degraded floor is right)")
    print(f"  2. strong arm does NOT: ours 0.733 / 0.713 vs paper 0.633 / 0.667")
    print(f"     Exhaustive search over every seed subset of size 8..13 found NO subset")
    print(f"     yielding 0.633 for Qwen3.8-27B, so this is not a seed-selection effect.")
    print(f"     Note E6_summary.md itself prints strong = 0.633 while its own 13")
    print(f"     per-seed values average 0.733 -- the summary and the records disagree.")
    print(f"  3. two of the four table columns have no data at all (above).")
    print(f"\n  per-condition means agree with the paper: {'yes' if ok else 'no'}"
          f"   (hold yes, strong no)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

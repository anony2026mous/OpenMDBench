"""P3: console verdict report for the withheld three-arm dataset.

Deliberately thin.  The paper-facing tables are produced by `_w1_withheld_table.py`,
and BOTH scripts load through `_w1_common` - there is exactly one definition of the
口径 filter, the metric, and the baseline policy identity in the project.  An earlier
version of this file re-implemented all three, which is how a doubled normalisation
(0.90 shown as 1.00) and a cross-checkpoint `rl` average got into a printed table.

This report answers the acceptance questions directly:
  Q1  did every arm produce data on every scenario?      -> coverage grid
  Q2  how does each arm compare to each baseline?        -> means + three-part verdict
  Q3  where does a hybrid LOSE?                          -> counterexamples
  Q4  is any of it contaminated?                         -> provenance tally
"""
from __future__ import annotations

import argparse
import statistics as st
from collections import defaultdict

from _w1_common import (ARMS, BASE_ARMS, IE, LABEL, LLM_ARMS, RUNS, SNAP,
                        collect, seeds, vals)

ap = argparse.ArgumentParser()
ap.add_argument("--briefing", default="withheld", choices=("withheld", "declared"))
ap.add_argument("--min-seeds", type=int, default=3,
                help="seed families required before a cell counts as fully populated")
args = ap.parse_args()

drop: dict = defaultdict(int)
_src = RUNS if args.briefing == "withheld" else SNAP
llm_cells = collect(_src, "*_n3*.json" if args.briefing == "withheld" else "*.json",
                    briefing=args.briefing, strict_arms=True, reasons=drop)
base = collect(SNAP, "*.json", briefing=None, strict_arms=True)

main: dict = defaultdict(lambda: defaultdict(list))
for k, v in llm_cells.items():
    for sd, scores in v.items():
        main[k][sd].extend(scores)
for a in BASE_ARMS:
    for sc in IE:
        for sd, scores in base.get((sc, a), {}).items():
            main[(sc, a)][sd].extend(scores)
main = dict(main)

if not any(vals(main, sc, a) for sc in IE for a in BASE_ARMS):
    raise SystemExit("ABORT: archived baseline did not load")

print("=" * 104)
print(f"P3 VERDICT  briefing={args.briefing}  source={'this session' if args.briefing == 'withheld' else 'archive'}")
print("=" * 104)

# ------------------------------------------------------------------ Q1
print("\n--- Q1  覆盖度  (局数 / 种子族数) ---")
print(f"  {'scenario':<28}" + "".join(f"{LABEL[a]:>13}" for a in ARMS))
full = 0
for sc in IE:
    row = f"  {sc:<28}"
    for a in ARMS:
        v = vals(main, sc, a)
        row += f"{(f'{len(v)}/{seeds(main, sc, a)}' if v else '—'):>13}"
    print(row)
print()
for a in ARMS:
    have = [sc for sc in IE if vals(main, sc, a)]
    suff = [sc for sc in IE if seeds(main, sc, a) >= args.min_seeds]
    print(f"  {LABEL[a]:<12} 有数 {len(have):>2}/14   种子>={args.min_seeds} {len(suff):>2}/14")
    if a in LLM_ARMS:
        full += len(have)
print(f"\n  LLM 三臂合计有数格: {full}/42   "
      f"({'P1 达标' if full == 42 else 'P1 未达标'})")

# ------------------------------------------------------------------ Q2
print("\n--- Q2  均值与三合稳定性判据 ---")
print(f"  {'scenario':<26}{'arm':<10}{'opp':<11}{'mean':>8}{'opp_m':>8}{'d':>8}"
      f"{'n':>9}  mean seed split  verdict")
stable = defaultdict(list)
counter = []
insufficient = []
for sc in IE:
    for h in LLM_ARMS:
        for o in BASE_ARMS:
            ha, oa = vals(main, sc, h), vals(main, sc, o)
            if len(ha) < 2 or len(oa) < 2:
                if ha or oa:
                    insufficient.append((sc, h, o, len(ha), len(oa)))
                continue
            hs = {k: st.mean(v) for k, v in main.get((sc, h), {}).items() if v}
            os_ = {k: st.mean(v) for k, v in main.get((sc, o), {}).items() if v}
            mh, mo = st.mean(ha), st.mean(oa)
            mean_ok = mh > mo
            seed_ok = min(hs.values()) > max(os_.values())
            order = sorted(hs)
            split_ok = mean_ok
            if len(order) >= 4:
                h1, h2 = order[:len(order) // 2], order[len(order) // 2:]
                split_ok = (st.mean([hs[x] for x in h1]) > mo
                            and st.mean([hs[x] for x in h2]) > mo)
            verdict = ("STABLE" if (mean_ok and seed_ok and split_ok)
                       else "mean-only" if mean_ok else "LOSES")
            if verdict == "STABLE":
                stable[h].append((sc, o, mh - mo))
            if verdict == "LOSES":
                counter.append((sc, h, o, mh - mo))
            print(f"  {sc:<26}{LABEL[h]:<10}{LABEL[o]:<11}{mh:>8.3f}{mo:>8.3f}"
                  f"{mh - mo:>+8.3f}{f'{len(ha)}/{len(oa)}':>9}  "
                  f"{'Y' if mean_ok else 'n':>4}{'Y' if seed_ok else 'n':>5}"
                  f"{'Y' if split_ok else 'n':>6}  {verdict}")

print("\n--- 稳定性汇总 ---")
for h in LLM_ARMS:
    scs = sorted({x[0] for x in stable[h]})
    print(f"  {LABEL[h]:<12} STABLE {len(stable[h]):>2} 条 / 覆盖 {len(scs)}/14 场景")
    for sc, o, d in stable[h]:
        print(f"      {sc:<28} > {LABEL[o]:<10} Δ{d:+.3f}")

# ------------------------------------------------------------------ Q3
print("\n--- Q3  反例（LLM 臂显著落后于单一架构基线） ---")
if counter:
    for sc, h, o, d in counter:
        print(f"    {sc:<28} {LABEL[h]:<10} < {LABEL[o]:<10} Δ{d:+.3f}")
else:
    print("    （当前数据下无）")
if insufficient:
    print(f"\n  样本不足未判读的格子: {len(insufficient)}")
    for sc, h, o, nh, no in insufficient[:12]:
        print(f"    {sc:<28} {LABEL[h]:<10} vs {LABEL[o]:<10} n={nh}/{no}")

# ------------------------------------------------------------------ Q4
print("\n--- Q4  口径与剔除溯源 ---")
if drop:
    for k, v in sorted(drop.items(), key=lambda kv: -kv[1])[:15]:
        print(f"    {k:<58} {v}")
else:
    print("    （无剔除）")
print("\n  口径读取路径: pure-llm -> defender.briefing;")
print("                llm-rule / llm-rl -> defender.planner.briefing")
print("  基线读取: 归档单源（归档即 _w1_runs 快照，两源相加会重复计数）")
print("  基线策略: rl 锁定 theta_rl_legacy2.npz 且 obs_dim=2866")

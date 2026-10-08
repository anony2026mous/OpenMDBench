"""Seed-by-seed view for `llm-rule`, the arm that already has two seeds.

The question this answers is whether the withheld readings are STABLE across draws
or whether the impressive single-seed numbers were luck.  It prints, per scenario:
both seeds, their spread, and the comparison against the reused baselines.

This is the earliest honest read on whether the paper's claim can survive
multi-seed replication, so it is deliberately blunt about variance.
"""
from __future__ import annotations

import statistics as st

import _w1_common as c

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)

ARM = "llm-rule"
PLANNER = "llm"

print("=" * 100)
print(f"SEED-BY-SEED  arm={c.LABEL[ARM]}  (withheld口径)")
print("=" * 100)

rows = []
for sc in c.IE:
    seeds = llm.get((sc, ARM), {})
    got = {sd: st.mean(v) for sd, v in sorted(seeds.items()) if v}
    bw = c.vals(base, sc, "rule-rule")
    rw = c.vals(base, sc, "rl")
    bm = st.mean(bw) if bw else None
    rm = st.mean(rw) if rw else None
    rows.append((sc, got, bm, rm))

print(f"\n  {'scenario':<28}{'s7':>8}{'s11':>8}{'s13':>8}{'within-sd':>11}"
      f"{'rule+rule':>11}{'RL':>8}   vs baselines")
for sc, got, bm, rm in rows:
    s7 = got.get(7)
    s11 = got.get(11)
    s13 = got.get(13)
    have = [x for x in (s7, s11, s13) if x is not None]
    sd = st.pstdev(have) if len(have) >= 2 else None
    base_best = max([x for x in (bm, rm) if x is not None], default=None)
    if len(have) >= 2 and base_best is not None:
        verdict = ("beats both" if min(have) > base_best
                   else "loses at least one draw" if max(have) < base_best
                   else "STRADDLES the baseline")
    elif have and base_best is not None:
        verdict = "beats" if have[0] > base_best else "loses"
    else:
        verdict = "-"

    def f(x, w=8, p=3):
        return f"{x:>{w}.{p}f}" if x is not None else f"{'-':>{w}}"

    print(f"  {sc:<28}{f(s7)}{f(s11)}{f(s13)}"
          f"{(f'{sd:.4f}' if sd is not None else '-'):>11}"
          f"{(f'{bm:.3f}' if bm is not None else '-'):>11}"
          f"{(f'{rm:.3f}' if rm is not None else '-'):>8}   {verdict}")

# ---- aggregate stability
pairs = []
for sc, got, _b, _r in rows:
    if 7 in got and 11 in got:
        pairs.append((sc, got[7], got[11], got[11] - got[7]))
print(f"\n--- seed 7 vs seed 11 (both available: {len(pairs)}/14) ---")
if pairs:
    ds = [d for *_x, d in pairs]
    both_seeds = [p for p in pairs]
    print(f"    mean |Δ| between seeds : {st.mean([abs(d) for d in ds]):.4f}")
    print(f"    max  |Δ|               : {max(abs(d) for d in ds):.4f}")
    print(f"    mean signed Δ (s11-s7) : {st.mean(ds):+.4f}")
    print(f"    sign flips (s7>s11 vs s11>s7): "
          f"{sum(1 for d in ds if d > 0)} up / {sum(1 for d in ds if d < 0)} down")
    print("\n    per scenario:")
    for sc, a, b, d in sorted(pairs, key=lambda x: -abs(x[3])):
        print(f"      {sc:<28} s7={a:.3f}  s11={b:.3f}  Δ={d:+.3f}")

print("\n  INTERPRETATION")
print("    'within-sd' is the spread across the seeds already run for that scenario.")
print("    If a cell's within-sd is large relative to its margin over the baseline,")
print("    that cell cannot support a claim until more seeds close the gap.")
print("    'STRADDLES the baseline' means some draws beat the baseline and some do")
print("    not - the honest verdict there is 'undecided at this n', not a win.")

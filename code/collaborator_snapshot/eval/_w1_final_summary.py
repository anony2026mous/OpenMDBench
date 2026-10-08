"""Final arm means and margins on the completed three-seed grid.

One line per arm with the overall mean, per-scenario wins, and the margin against
each reused baseline.  This is the summary the paper's claim table is built from,
so it deliberately reports the LOSING scenarios too rather than only the wins.
"""
from __future__ import annotations

import statistics as st

import _w1_common as c

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)

print("=" * 104)
print("FINAL ARM SUMMARY  (withheld口径, 3 seeds x 14 scenarios)")
print("=" * 104)

hdr = f"  {'scenario':<28}" + "".join(f"{c.LABEL[a]:>12}" for a in c.ARMS)
print(f"\n{hdr}")
print("  " + "-" * (len(hdr) - 2))
for sc in c.IE:
    row = f"  {sc:<28}"
    for a in c.ARMS:
        src = llm if a in c.LLM_ARMS else base
        v = c.vals(src, sc, a)
        row += f"{(f'{st.mean(v):.3f}' if v else '-'):>12}"
    print(row)

print("\n--- overall ---")
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    allv = [x for sc in c.IE for x in c.vals(src, sc, a)]
    has3 = sum(1 for sc in c.IE if c.seeds(src, sc, a) >= 3)
    wins_rr = wins_rl = 0
    for sc in c.IE:
        mine = c.vals(src, sc, a)
        rr = c.vals(base, sc, "rule-rule")
        rl = c.vals(base, sc, "rl")
        if mine and rr and st.mean(mine) > st.mean(rr):
            wins_rr += 1
        if mine and rl and st.mean(mine) > st.mean(rl):
            wins_rl += 1
    print(f"  {c.LABEL[a]:<12} mean {st.mean(allv):.4f}  sd {st.pstdev(allv):.4f}  "
          f"n={len(allv):>3}  seeds>=3 in {has3:>2}/14  "
          f"beats rule+rule {wins_rr:>2}/14  beats RL {wins_rl:>2}/14")

print("\n--- margin of each LLM arm over the BEST baseline, per scenario ---")
print(f"  {'scenario':<28}{'beam arm':>10}{'best base':>11}{'margin':>9}   verdict")
for sc in c.IE:
    bb = max([x for x in (st.mean(c.vals(base, sc, "rule-rule") or [0]),
                          st.mean(c.vals(base, sc, "rl") or [0]))])
    for a in c.LLM_ARMS:
        v = c.vals(llm, sc, a)
        if not v:
            continue
        m = st.mean(v)
        d = m - bb
        verdict = "WIN" if d > 0 else "LOSS"
        print(f"  {sc:<28}{c.LABEL[a]:>10}{bb:>11.3f}{d:>+9.3f}   {verdict}")
    print()

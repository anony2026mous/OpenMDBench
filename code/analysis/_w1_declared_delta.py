"""Print the declared-vs-withheld aggregate, for the paper document to quote."""
from __future__ import annotations

import statistics as st

import _w1_common as c

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
decl = c.collect(c.SNAP, "*.json", briefing="declared", strict_arms=True,
                 provenance="legacy-ok")

print(f"  {'arm':<12}{'withheld':>11}{'declared':>11}{'delta':>9}{'better':>9}")
for a in c.LLM_ARMS:
    w = [x for sc in c.IE for x in c.vals(llm, sc, a)]
    d = [x for sc in c.IE for x in c.vals(decl, sc, a)]
    better = 0
    tot = 0
    for sc in c.IE:
        mw, md = c.vals(llm, sc, a), c.vals(decl, sc, a)
        if mw and md:
            tot += 1
            if st.mean(mw) > st.mean(md):
                better += 1
    print(f"  {c.LABEL[a]:<12}{st.mean(w):>11.4f}{st.mean(d):>11.4f}"
          f"{st.mean(w) - st.mean(d):>+9.4f}{better:>6}/{tot}")

print("\n  per-scenario deltas (withheld - declared):")
for sc in c.IE:
    parts = []
    for a in c.LLM_ARMS:
        mw = c.vals(llm, sc, a)
        md = c.vals(decl, sc, a)
        parts.append(f"{st.mean(mw) - st.mean(md):+.3f}" if (mw and md) else "  -  ")
    print(f"    {sc:<28}" + "".join(f"{p:>10}" for p in parts))

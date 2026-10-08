"""Print the current partial-results matrix: 5 arms x 14 scenarios, one line each."""
from __future__ import annotations

import statistics as st

import _w1_common as c

llm = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)

hdr = (f"  {'scenario':<28}" + "".join(f"{c.LABEL[a]:>11}" for a in c.ARMS)
       + "   winner")
print(hdr)
print("  " + "-" * (len(hdr) - 2))
for sc in c.IE:
    row = []
    for a in c.ARMS:
        src = llm if a in c.LLM_ARMS else base
        v = c.vals(src, sc, a)
        row.append(st.mean(v) if v else None)
    def cell(x):
        return f"{x:.3f}" if x is not None else "-"

    cells = "".join(f"{cell(x):>11}" for x in row)
    have = [(v, c.LABEL[a]) for v, a in zip(row, c.ARMS) if v is not None]
    win = max(have)[1] if have else "-"
    print(f"  {sc:<28}{cells}   {win}")

print()
for a in c.ARMS:
    src = llm if a in c.LLM_ARMS else base
    n = sum(1 for sc in c.IE if c.vals(src, sc, a))
    tot = sum(len(c.vals(src, sc, a)) for sc in c.IE)
    print(f"  {c.LABEL[a]:<12} {n:>2}/14 scenarios   {tot:>3} episodes")

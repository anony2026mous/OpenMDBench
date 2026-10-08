"""Declared vs withheld comparison for the LLM arms, on the completed P1 cells.

Answers the question the paper hinges on: does withholding the scenario-declared
enemy plan change measured performance, and in which direction?  The archived
declared episodes and this session's withheld episodes cover the same arms and the
same 14 scenarios, so they are directly comparable.

Both sides are read through `_w1_common`, so the口径 filter and the metric are the
same as everywhere else.
"""
from __future__ import annotations

import statistics as st

import _w1_common as c

withh = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
# legacy-ok: the archived declared episodes predate the `briefing` provenance field,
# so requiring it would empty this column.  See `_w1_common.collect`.
decl = c.collect(c.SNAP, "*.json", briefing="declared", strict_arms=True,
                 provenance="legacy-ok")

print("=" * 100)
print("DECLARED vs WITHHELD  (same arms, same scenarios)")
print("=" * 100)
print(f"\n  {'scenario':<28}{'LLM+rule':>20}{'LLM+RL':>20}{'pure-LLM':>20}")
print(f"  {'':<28}" + "".join(f"{'whd / decl':>20}" for _ in range(3)))
print("  " + "-" * 88)

deltas = {"llm-rule": [], "llm-rl": [], "pure-llm": []}
wins = {"llm-rule": 0, "llm-rl": 0, "pure-llm": 0}
for sc in c.IE:
    row = f"  {sc:<28}"
    for a in c.LLM_ARMS:
        w, d = c.vals(withh, sc, a), c.vals(decl, sc, a)
        mw = st.mean(w) if w else None
        md = st.mean(d) if d else None
        if mw is not None and md is not None:
            deltas[a].append(mw - md)
            if mw > md:
                wins[a] += 1
            arrow = "^" if mw > md else ("v" if mw < md else "=")
            row += f"{f'{mw:.3f} / {md:.3f} {arrow}':>20}"
        else:
            row += f"{((f'{mw:.3f}' if mw is not None else '-') + ' / ' + (f'{md:.3f}' if md is not None else '-')):>20}"
    print(row)

print("\n--- summary ---")
for a in c.LLM_ARMS:
    ds = deltas[a]
    if not ds:
        continue
    print(f"  {c.LABEL[a]:<12} comparable scenarios {len(ds):>2}/14   "
          f"withheld better in {wins[a]:>2}   mean Δ {st.mean(ds):+.4f}   "
          f"median Δ {st.median(ds):+.4f}   range [{min(ds):+.3f}, {max(ds):+.3f}]")

print("\n  '^' = withheld scored higher than declared for that cell.")
print("  Positive Δ means REMOVING the declared intelligence IMPROVED the score,")
print("  which points at the old briefing having contained harmful instructions")
print("  rather than merely redundant information.")

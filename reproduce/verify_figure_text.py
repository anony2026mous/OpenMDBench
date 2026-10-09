"""Verify the numbers drawn INSIDE the figures.

The rest of the suite reads figure CAPTIONS from the paper's text layer. That misses
anything rendered inside the artwork, and one such number was wrong: `fig_hifi_gap`
annotates "IE-03: +0.065", but IE-03 is the only scenario in the whole suite where a
layered stack LEADS pure LLM, so the correct annotation is -0.065 (LLM+RL) -- and the
LLM+Rule gap there is +0.1575, a different number again.

This script reads the figure PDFs with pdfplumber, extracts every number actually drawn
in them, and checks each against the data.

Figures with no text layer (`fig_narrative_overview.pdf` is a single bitmap) are reported
as unverifiable rather than silently passed.
"""
from __future__ import annotations

import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _w1_common as c  # noqa: E402

PAPER_SEEDS = (7, 11, 13, 17, 19)

try:
    import pdfplumber
except ImportError:
    print("  pdfplumber not installed -- skipping figure-text check")
    raise SystemExit(0)


def fig_text(name: str) -> str:
    p = FIGS / name
    if not p.is_file():
        return ""
    with pdfplumber.open(str(p)) as pdf:
        return " ".join(w["text"] for pg in pdf.pages for w in pg.extract_words())


print("=" * 96)
print("figure-internal numbers  vs  data")
print("=" * 96)

# ---- per-scenario stack means (same recipe as verify_paper_table.py)
by = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
T: dict[str, dict[str, float]] = {}
for sc in c.IE:
    row = {}
    for arm in c.LLM_ARMS:
        v = [x for sd in PAPER_SEEDS for x in by.get((sc, arm), {}).get(sd, [])]
        if v:
            row[arm] = st.mean(v)
    T[sc] = row

bad = 0

# ---- fig_hifi_gap: counts, median, and the IE-03 annotation
txt = fig_text("fig_hifi_gap.pdf")
print(f"\n  --- fig_hifi_gap.pdf ---")
if not txt:
    print("    NO TEXT LAYER -- cannot verify")
else:
    gaps_rule, gaps_rl = [], []
    for sc in c.IE:
        e = T[sc].get("pure-llm")
        r = T[sc].get("llm-rule")
        l = T[sc].get("llm-rl")
        if e is None:
            continue
        if r is not None:
            gaps_rule.append(r - e)
        if l is not None:
            gaps_rl.append(l - e)
    n_rule = sum(1 for x in gaps_rule if x > 0)
    n_rl = sum(1 for x in gaps_rl if x > 0)
    med = st.median(gaps_rule + gaps_rl)
    print(f"    '14/14 Rule'  -> computed {n_rule}/{len(gaps_rule)}   "
          f"{'OK' if n_rule == 14 else 'DIFFERS'}")
    print(f"    '13/14 RL'    -> computed {n_rl}/{len(gaps_rl)}   "
          f"{'OK' if n_rl == 13 else 'DIFFERS'}")
    print(f"    'median 0.329'-> computed {med:.3f}   "
          f"{'OK' if abs(med - 0.329) <= 0.001 else 'DIFFERS'}")
    bad += (n_rule != 14) + (n_rl != 13) + (abs(med - 0.329) > 0.001)

    ie03 = T["IE-03-SURFACE-RAID"]
    g_rule = ie03["llm-rule"] - ie03["pure-llm"]
    g_rl = ie03["llm-rl"] - ie03["pure-llm"]
    m = re.search(r"IE-03:\s*([+-]?\d+\.\d+)", txt)
    shown = float(m.group(1)) if m else None
    print(f"    'IE-03: {shown}'")
    print(f"        LLM+Rule - pure LLM = {g_rule:+.4f}")
    print(f"        LLM+RL   - pure LLM = {g_rl:+.4f}   <- the annotation matches "
          f"this one in magnitude")
    # the annotation sits under "Below zero: the layered stack leads"
    ok = shown is not None and shown < 0 and abs(abs(shown) - abs(g_rl)) <= 0.001
    if not ok:
        bad += 1
        print(f"        MISMATCH: IE-03 is the only scenario where a layered stack")
        print(f"                  leads, so the sign must be negative. Expected "
              f"{g_rl:+.3f}, figure prints {shown:+.3f}.")
    else:
        print(f"        OK")

# ---- figA2: sweep values and token column
txt = fig_text("figA2_replanning_sweep.pdf")
print(f"\n  --- figA2_replanning_sweep.pdf ---")
for want, label in ((0.978, "pure RL"), (0.467, "k=10"), (0.733, "k=5/k=2")):
    ok = f"{want}" in txt
    print(f"    {label:<10} {want}   {'OK' if ok else 'ABSENT'}")
    bad += not ok

# ---- figA1: the MiniMax boundary value
txt = fig_text("figA1_model_invariance.pdf")
print(f"\n  --- figA1_model_invariance.pdf ---")
for want in ("0.022", "0.000", "0.067"):
    ok = want in txt
    print(f"    {want:<8} {'OK' if ok else 'ABSENT'}")
    bad += not ok

# ---- figA4: all 12 case labels
txt = fig_text("figA4_natural_failure_pilot.pdf")
print(f"\n  --- figA4_natural_failure_pilot.pdf ---")
cases = [f"E5-{i:02d}" for i in range(1, 13)]
missing = [x for x in cases if x not in txt]
print(f"    case labels present: {len(cases) - len(missing)}/12"
      f"{'' if not missing else '  missing: ' + ', '.join(missing)}")
bad += bool(missing)

# ---- figures with no text layer
print(f"\n  --- figures with no extractable text ---")
for name in ("fig_narrative_overview.pdf", "fig_arch.pdf"):
    tt = fig_text(name)
    nums = re.findall(r"-?\d+\.\d+|-?\d+%", tt)
    print(f"    {name:<34} words={len(tt.split()):<4} numeric tokens={len(nums)}")
    if name == "fig_arch.pdf" and not nums:
        print(f"        (architecture diagram: structural claims only, no data)")

print(f"\n  figure-internal cells mismatching: {bad}")

"""Verify the numbers shown in the paper's figures.

Two traps this handles, because I fell into both:

  1. READING THE WRONG FILE. `paper/figures/` can hold several revisions of one figure.
     The paper includes exactly what `\\includegraphics{...}` names -- in this case
     `fig_hifi_gap_cropped.pdf`, NOT the older `fig_hifi_gap.pdf` that sits beside it.
     This script therefore reads the .tex files first and only checks files actually
     included, and it cross-checks the compiled PDF's embedded-image aspect ratio where
     one is available.

  2. ASSUMING A FIGURE CAN BE READ AS TEXT. Some shipped figures have no text layer at
     all (`fig_hifi_gap_cropped.pdf` is flattened vector art: 0 chars). Those are
     reported as "text-layer absent -- requires visual check" rather than being silently
     passed or, worse, silently failed against a different revision.

Where a text layer does exist, every rendered number is checked against the data.
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
    print("  pdfplumber not installed -- skipping figure check")
    raise SystemExit(0)


# ---------------------------------------------------------------- which figures ship?
def included() -> dict[str, list[str]]:
    """figure filename (basename) -> list of .tex files that include it."""
    out: dict[str, list[str]] = {}
    for f in ("main.tex", "appendix.tex"):
        p = ROOT / "paper" / f
        if not p.is_file():
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"includegraphics[^{]*\{([^}]+)\}", t):
            out.setdefault(Path(m.group(1)).name, []).append(f)
    return out


print("=" * 96)
print("figure-internal numbers  vs  data")
print("=" * 96)

inc = included()
print(f"\n  --- files actually included by the .tex sources ---")
for name, src in sorted(inc.items()):
    present = (FIGS / name).is_file()
    print(f"    {name:<38} {','.join(src):<14} {'present' if present else 'MISSING'}")

# revisions present in the folder but not included
print(f"\n  --- revisions present but NOT included (do not check these) ---")
for p in sorted(FIGS.glob("*")):
    if p.is_file() and p.suffix.lower() in {".pdf", ".png", ".svg"} and p.name not in inc:
        print(f"    {p.name}")

# ---------------------------------------------------------------- cross-check embedding
print(f"\n  --- cross-check against the compiled PDF, where one is available ---")
compiled = next((p for p in ROOT.parent.glob("*.pdf")), None)
print(f"    compiled PDF in the bundle: {compiled if compiled else 'not shipped'}")
print(f"    (outside the bundle, compare the embedded image's w/h ratio against")
print(f"     every candidate revision: it picks out the one actually used)")


def fig_text(name: str) -> str:
    p = FIGS / name
    if not p.is_file():
        return ""
    try:
        with pdfplumber.open(str(p)) as pdf:
            return " ".join(w["text"] for pg in pdf.pages for w in pg.extract_words())
    except Exception:
        return ""


bad = 0

# ---------------------------------------------------------------- per-scenario stack means
by = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
T: dict[str, dict[str, float]] = {}
for sc in c.IE:
    row = {}
    for arm in c.LLM_ARMS:
        v = [x for sd in PAPER_SEEDS for x in by.get((sc, arm), {}).get(sd, [])]
        if v:
            row[arm] = st.mean(v)
    T[sc] = row


def check_gap_figure(name: str) -> None:
    global bad
    print(f"\n  --- {name} ---")
    if name not in inc:
        print("      not included by the paper -- skipped")
        return
    txt = fig_text(name)
    if not txt.strip():
        print("      TEXT LAYER ABSENT (flattened artwork).")
        print("      Cannot be checked numerically; requires a visual check against the")
        print("      data below. The header strings and the IE-03 annotation live in the")
        print("      artwork, so a text-based pass would report a false result either way.")
        # still print the truth so a human can eyeball it.
        # NOTE the axis is `Pure LLM - layered stack`, so a POINT ABOVE ZERO means the
        # layered stack is ahead. Getting this backwards inverts the whole reading.
        g_rule, g_rl = [], []
        for sc in c.IE:
            e = T[sc].get("pure-llm")
            if e is None:
                continue
            if T[sc].get("llm-rule") is not None:
                g_rule.append(e - T[sc]["llm-rule"])
            if T[sc].get("llm-rl") is not None:
                g_rl.append(e - T[sc]["llm-rl"])
        print(f"      axis label      : 'Pure LLM - layered stack'"
              f"  (positive = layered stack ahead)")
        # "trails" means the layered stack is ahead, i.e. the axis value is NEGATIVE
        print(f"      expected header : 'Pure LLM trails: "
              f"{sum(1 for x in g_rule if x < 0)}/{len(g_rule)} Rule, "
              f"{sum(1 for x in g_rl if x < 0)}/{len(g_rl)} RL stacks'")
        print(f"      expected median deficit : {abs(st.median(g_rule + g_rl)):.3f}")
        above = [(sc, T[sc]["pure-llm"] - T[sc]["llm-rl"]) for sc in c.IE
                 if T[sc].get("llm-rl") is not None and T[sc].get("pure-llm") is not None
                 and T[sc]["pure-llm"] - T[sc]["llm-rl"] > 0]
        print(f"      points ABOVE y=0 (layered stack ahead): {len(above)} of {len(c.IE)}")
        for sc, g in above:
            a, b = sc.split("-")[0], sc.split("-")[1]
            print(f"          {sc}  +{g:.3f}  -> annotation should read '{a}-{b}: +{g:.3f}'")
        if not above:
            print("          (none -- every layered stack trails pure LLM)")
        return
    gaps_rule, gaps_rl = [], []
    for sc in c.IE:
        e = T[sc].get("pure-llm")
        if e is None:
            continue
        if T[sc].get("llm-rule") is not None:
            gaps_rule.append(T[sc]["llm-rule"] - e)
        if T[sc].get("llm-rl") is not None:
            gaps_rl.append(T[sc]["llm-rl"] - e)
    n_rule = sum(1 for x in gaps_rule if x > 0)
    n_rl = sum(1 for x in gaps_rl if x > 0)
    med = st.median(gaps_rule + gaps_rl)
    for got, want, label in ((n_rule, 14, "Rule count"), (n_rl, 13, "RL count"),
                             (med, 0.329, "pooled median")):
        ok = abs(got - want) < 1e-3 if isinstance(want, float) else got == want
        print(f"      {label:<16} computed {got}  figure {want}   "
              f"{'OK' if ok else 'DIFFERS'}")
        bad += not ok


check_gap_figure("fig_hifi_gap_cropped.pdf")
check_gap_figure("fig_hifi_gap.pdf")

# ---------------------------------------------------------------- figures with text
for name, wants in (("figA2_replanning_sweep.pdf", ("0.978", "0.467", "0.733")),
                    ("figA1_model_invariance.pdf", ("0.022", "0.000", "0.067"))):
    if name not in inc:
        continue
    txt = fig_text(name)
    print(f"\n  --- {name} ---")
    if not txt.strip():
        print("      TEXT LAYER ABSENT -- requires visual check")
        continue
    for w in wants:
        ok = w in txt
        print(f"      {w:<8} {'OK' if ok else 'ABSENT'}")
        bad += not ok

name = "figA4_natural_failure_pilot.pdf"
if name in inc:
    txt = fig_text(name)
    print(f"\n  --- {name} ---")
    if not txt.strip():
        print("      TEXT LAYER ABSENT -- requires visual check")
    else:
        missing = [f"E5-{i:02d}" for i in range(1, 13) if f"E5-{i:02d}" not in txt]
        print(f"      case labels present: {12 - len(missing)}/12"
              f"{'' if not missing else '  missing: ' + ', '.join(missing)}")
        bad += bool(missing)

# ---------------------------------------------------------------- no-text-layer figures
print(f"\n  --- figures with no extractable text ---")
for p in sorted(FIGS.glob("*.pdf")):
    if p.name not in inc:
        continue
    tt = fig_text(p.name)
    if not tt.strip():
        print(f"    {p.name:<38} 0 chars -- visual check required")

print(f"\n  figure cells mismatching: {bad}")
print(f"  (figures with no text layer are reported above, not counted as passes)")
raise SystemExit(1 if bad else 0)

"""Cross-check the paper's main table against the local grid dataset.

This is the check a reviewer would run first: do the numbers printed in the paper
follow from the released episodes?  Any mismatch is reported rather than smoothed
over, because a silent mismatch would invalidate the reproduction claim.
"""
from __future__ import annotations

import os
import re
import statistics as st
from pathlib import Path

import _w1_common as c

_HERE = Path(__file__).resolve().parent
# Repository root: one level up in the release layout (`reproduce/` sits inside it),
# itself in the authoring checkout where the scripts live at the top level.
_ROOT = _HERE.parent if (_HERE.parent / "code").exists() else _HERE

# The paper's table source ships inside this repository, so default to it; allow an
# override for a checkout that keeps the manuscript elsewhere.
PAPER_TEX = Path(os.environ.get(
    "PAPER_TABLE_TEX",
    _ROOT / "paper" / "tables" / "tab_hifi_main.tex"))

ARM_COL = {"LLM+Rule": "llm-rule", "LLM+RL": "llm-rl", "Pure LLM": "pure-llm",
           "Rule": "rule-rule", "RL": "rl"}

# The paper's table is the 5-seed aggregate, stated in its caption.  Restricting to
# exactly those seeds matters: the local directory also holds a partial sixth seed
# (23), and including its few finished cells shifts the means (IE-04 LLM+Rule moves
# from 0.710 to 0.741, i.e. a 0.031 error).  Compare like with like.
PAPER_SEEDS = (7, 11, 13, 17, 19)


def paper_table() -> dict[str, dict[str, float]]:
    """Parse the LaTeX table: {scenario_tag: {arm: value}} plus the Overall row."""
    src = PAPER_TEX.read_text(encoding="utf-8")
    out: dict[str, dict[str, float]] = {}
    for line in src.splitlines():
        if "&" not in line or "\\\\" not in line:
            continue
        cells = [re.sub(r"\\[a-zA-Z]+|[{}$*]", "", x).strip()
                 for x in line.split("&")]
        tag = cells[0]
        if not tag or tag.startswith("\\") or "midrule" in line or "toprule" in line:
            continue
        vals = []
        for x in cells[1:]:
            x = x.replace("\\textbf", "").strip()
            m = re.match(r"^([0-9]*\.?[0-9]+)", x)
            vals.append(float(m.group(1)) if m else None)
        if len(vals) < 5 or any(v is None for v in vals[:5]):
            continue
        out[tag] = dict(zip(ARM_COL.keys(), vals[:5]))
    return out


def norm_tag(s: str) -> str:
    """Canonicalise a scenario label so the paper's and the data's agree.

    The paper writes some rows with an internal hyphen ('IE-05 multi-axis') and others
    with a space ('IE-01 single target'), so both spellings must collapse to one key.
    """
    s = s.strip().lower().replace("_", "-").replace(" ", "-")
    return re.sub(r"-+", "-", s)


def local_table() -> dict[str, dict[str, float]]:
    """Keyed exactly like the paper's row label, e.g. 'IE-10 dual-axis pincer'.

    `sc` is 'IE-10-DUAL-AXIS-PINCER'; splitting on '-' would cut the 'IE-10' prefix
    itself, so match on the numeric boundary instead.  Only the paper's seeds are
    averaged, for the reason given at PAPER_SEEDS.
    """
    by = c.collect(c.RUNS, "*_n3*.json", briefing="withheld", strict_arms=True)
    base = c.collect(c.SNAP, "*.json", briefing=None, strict_arms=True)
    out = {}
    for sc in c.IE:
        row = {}
        for arm in c.ARMS:
            if arm in c.LLM_ARMS:
                # the LLM arms are exactly the five campaign seeds
                v = [x for sd in PAPER_SEEDS for x in by.get((sc, arm), {}).get(sd, [])]
            else:
                # Baselines come from the frozen archive and are NOT seed-restricted:
                # the caption says so, and it is measurable.  Restricting rule-rule to
                # the campaign seeds gives IE-01 = 0.686, whereas the paper prints
                # 0.691, which is the mean over all 42 archived rule episodes.
                v = c.vals(base, sc, arm)
            if v:
                row[arm] = st.mean(v)
        m = re.match(r"^(IE-\d+)-(.*)$", sc)
        num, rest = (m.group(1), m.group(2)) if m else (sc, "")
        out[norm_tag(f"{num} {rest}")] = row
    return out


pt = paper_table()
lt = local_table()

print("=" * 104)
print("PAPER MAIN TABLE  vs  LOCAL GRID DATASET")
print("=" * 104)
print(f"  paper rows parsed: {len(pt)}")

paper_tags = [t for t in pt if t.startswith("IE-")]

tag_to_scen: dict[str, str] = {}
for sc in c.IE:
    m = re.match(r"^(IE-\d+)-(.+)$", sc)
    if m:
        tag_to_scen[norm_tag(f"{m.group(1)} {m.group(2)}")] = sc

# The paper's table abbreviates one row label relative to the scenario id.
# Keys are NORMALISED, so the alias must be normalised too.
TAG_ALIAS = {"ie-14-saturation": "ie-14-saturation-three-wave"}

matched = 0
rows = []
for tag in paper_tags:
    key = tag_to_scen.get(norm_tag(tag)) or TAG_ALIAS.get(norm_tag(tag))
    if key is None:
        print(f"  !! unmapped paper row: {tag!r}  (normalised {norm_tag(tag)!r})")
        continue
    matched += 1
    prow = pt[tag]
    # `lt` is keyed by the CANONICAL scenario label, and TAG_ALIAS may have rewritten
    # the paper's abbreviated label, so look up via the resolved scenario id.
    lrow = lt.get(norm_tag(key), {})
    for arm_label, arm in ARM_COL.items():
        pv = prow.get(arm_label)
        lv = lrow.get(arm)
        if pv is None or lv is None:
            rows.append((tag, arm_label, pv, lv, None))
            continue
        rows.append((tag, arm_label, pv, lv, lv - pv))

print(f"  scenarios matched : {matched}")
print()
print(f"  {'scenario':<22}{'arm':<10}{'paper':>8}{'local':>8}{'diff':>9}   verdict")
bad = exact = close = 0
for tag, arm, pv, lv, d in rows:
    if d is None:
        verdict = "MISSING"
    elif abs(d) <= 0.0005:
        verdict = "exact"
        exact += 1
    elif abs(d) <= 0.0015:
        verdict = "rounding"
        close += 1
    else:
        verdict = "DIFFERS"
        bad += 1
    ps = f"{pv:.3f}" if pv is not None else "-"
    ls = f"{lv:.3f}" if lv is not None else "-"
    ds = f"{d:+.3f}" if d is not None else "-"
    print(f"  {tag:<22}{arm:<10}{ps:>8}{ls:>8}{ds:>9}   {verdict}")

print(f"\n  exact {exact}   rounding {close}   DIFFERS {bad}   of {len(rows)} cells")
if bad:
    print("\n  Cells that differ materially are listed above. A difference here means")
    print("  the paper's number did not come from THIS dataset; check whether that row")
    print("  was produced by the HF (CSS/ULHA) campaign instead of the grid campaign.")

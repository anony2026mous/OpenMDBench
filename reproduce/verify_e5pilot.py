"""Verify appendix tab:e5pilot -- the 12-case machine counterfactual labels.

The table prints, per case: dP (planner contrast), dE (executor contrast), dI (synergy),
and the machine label. Those live in `attribution.json`, which carries
`delta_planning` / `delta_execution` / `delta_interface` / `machine_label`.

Sources:
  * HF cases      -> e5-hifi-natural-failures-r2 (server A) + e5-hifi-attribution-r3b
  * grid cases    -> e5-grid-natural-failures (need their attribution records)

This reports per case rather than an aggregate, because the table is per case.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Repository root: this script ships in `reproduce/`, one level below it.
_HERE = Path(__file__).resolve().parent
REL = _HERE.parent if (_HERE.parent / "data").is_dir() else _HERE

# appendix tab:e5pilot, verbatim
PAPER = {
    "E5-01": ("IE-03", 5104, 0.34, 0.71, -0.58, "exec"),
    "E5-02": ("IE-08", 5102, 0.01, 0.03, 0.35, "interface"),
    "E5-03": ("IE-08", 5101, -0.03, 0.00, 0.30, "interface"),
    "E5-04": ("grid", 5202, 0.10, 0.00, 0.60, "interface"),
    "E5-05": ("IE-08", 5103, -0.01, 0.08, 0.22, "interface"),
    "E5-06": ("IE-03", 5102, 0.41, 0.01, 0.29, "planning"),
    "E5-07": ("IE-03", 5105, 0.00, 0.01, 0.40, "interface"),
    "E5-08": ("grid", 5201, 0.77, 0.07, -0.67, "planning"),
    "E5-09": ("grid", 5204, 0.20, 0.00, 0.60, "interface"),
    "E5-10": ("IE-03", 5101, 0.48, 0.00, 0.21, "planning"),
    "E5-11": ("IE-08", 5104, 0.02, -0.02, 0.17, "interface"),
    "E5-12": ("IE-08", 5105, -0.24, -0.18, 0.57, "interface"),
}
SCEN = {"IE-03": "ie-03-surface-raid", "IE-08": "ie-08-island-strike"}


def load_dir(d: Path) -> dict | None:
    f = d / "attribution.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def find(src_roots: list[Path], scen: str, seed: int) -> dict | None:
    """Return the COMPLETE attribution record for a case.

    A case can exist in more than one batch: the natural-failures batch holds some
    records with status `counterfactual_incomplete` and all deltas None, while the
    attribution-r3b batch holds the finished ones. Preferring the first directory found
    therefore picks up an incomplete record and reports a false divergence, so scan all
    roots and keep the complete one.
    """
    key = f"{scen}__llm-rl__s{seed}"
    fallback = None
    for root in src_roots:
        d = root / key
        if not d.is_dir():
            continue
        got = load_dir(d)
        if not got:
            continue
        if got.get("status") == "complete" and isinstance(
                got.get("delta_planning"), (int, float)):
            return got
        fallback = fallback or got
    return fallback


ROOTS = [
    # Compact attribution records shipped with the release (17 cases, ~47 KB). The raw
    # batches they come from are ~9 GB of replay evidence, which is why only these
    # records travel: they are the part that carries the table's numbers.
    REL / "data" / "e5-attribution",
    # Optional overrides for an authoring machine that still holds the full trees. Set
    # OPENMD_E5NF_DIR / OPENMD_R3B_DIR to the `attribution` directories of the
    # natural-failures and attribution-r3b batches.
    *[Path(v) for v in filter(None, (
        os.environ.get("OPENMD_E5NF_DIR"), os.environ.get("OPENMD_R3B_DIR")))],
    REL / "data" / "campaigns" / "e5-hifi-attribution-r3b" / "attribution",
    REL / "data" / "campaigns" / "e5-grid-natural-failures",
]

print("=" * 100)
print("appendix tab:e5pilot  vs  attribution.json records")
print("=" * 100)

def fmt(v, dec=2):
    return "None" if not isinstance(v, (int, float)) else f"{v:.{dec}f}"


# The record stores full names; the table abbreviates. Map before comparing labels.
LABEL_ABBR = {"execution": "exec", "planning": "planning",
              "interface": "interface", "balanced": "balanced"}

matched = missing = 0
for cid, (grp, seed, pP, pE, pI, plabel) in PAPER.items():
    if grp == "grid":
        # The grid batch stores its counterfactual under different field names than the
        # high-fidelity batch: `reference_improvement_planning/_execution` and
        # `reference_nonadditivity`, in each seed's summary.json. An earlier version of
        # this script looked only for `attribution.json` and wrongly reported all three
        # grid cases as missing records.
        sp = REL / "data" / "campaigns" / "e5-grid-natural-failures" / f"seed-{seed}" / "summary.json"
        if not sp.is_file():
            print(f"  {cid}  grid s{seed:<6} MISSING (no summary.json)")
            missing += 1
            continue
        g = json.loads(sp.read_text(encoding="utf-8"))
        dP = g.get("reference_improvement_planning")
        dE = g.get("reference_improvement_execution")
        dI = g.get("reference_nonadditivity")
        # the grid batch stores no label; derive it by the same rule the toolchain uses
        cand = {"planning": dP, "execution": dE, "interface": dI}
        ml_abbr = max(cand, key=lambda k: abs(cand[k] or 0.0))
    else:
        rec = find(ROOTS, SCEN[grp], seed)
        if not rec:
            print(f"  {cid}  {grp} s{seed:<6} MISSING (no attribution.json found)")
            missing += 1
            continue
        dP = rec.get("delta_planning")
        dE = rec.get("delta_execution")
        dI = rec.get("delta_interface")
        ml = rec.get("machine_label")
        ml_abbr = LABEL_ABBR.get(ml, ml)
    okP = isinstance(dP, (int, float)) and abs(dP - pP) <= 0.006
    okE = isinstance(dE, (int, float)) and abs(dE - pE) <= 0.006
    okI = isinstance(dI, (int, float)) and abs(dI - pI) <= 0.006
    okL = ml_abbr == plabel
    okay = okP and okE and okI and okL
    if okay:
        matched += 1
    parts = []
    for ok, nm in ((okP, "dP"), (okE, "dE"), (okI, "dI"), (okL, "label")):
        if not ok:
            parts.append(nm)
    flag = "" if okay else "  <-- differs: " + ", ".join(parts)
    print(f"  {cid}  {grp} s{seed:<6} "
          f"dP {fmt(dP):>6}/{pP:<6} dE {fmt(dE):>6}/{pE:<6} "
          f"dI {fmt(dI):>6}/{pI:<6} {str(ml):<10}/{plabel}{flag}")

print(f"\n  cases matched exactly : {matched}/12")
print(f"  cases not checkable   : {missing}/12")

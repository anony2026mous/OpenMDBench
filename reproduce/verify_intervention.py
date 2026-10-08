"""Verify appendix tab:intervention -- the complex-tier four-system intervention study.

Appendix (appendix.tex 293-305):
    System                          SR    Contrast   D SR [95% CI]
    rule + heuristic                65%   --         --
    rule_intel (feint filter)       60%   vs rule    -5  [-15, 0]
    LLM + heuristic                 10%   --         --
    LLM + exclusive intel            5%   vs LLM     -5  [-20, +10]
                                         vs rule    -60 [-85, -30]
"20 paired episodes" on the complex tier.

The experiment script is `code/collaborator_snapshot/grid_info_experiment.py`, whose
docstring names the same four systems and the same anchors ("rule_heuristic 65% anchor",
"hybrid_heuristic LLM planner (5% anchor)"). Its output --
`data/platform-results/grid_info_experiment.json` -- holds the per-system success
lists and the four contrasts.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "data" / "platform-results" / "grid_info_experiment.json"

# system: paper SR
PAPER_SR = {
    "rule_heuristic": 0.65, "rule_intel": 0.60,
    "hybrid_heuristic": 0.10, "hybrid_intel": 0.05,
}
# contrast: (paper delta, paper ci)
PAPER_CONTRAST = {
    "hybrid_intel - hybrid_heuristic": (-0.05, (-0.20, 0.10)),
    "hybrid_intel - rule_heuristic": (-0.60, (-0.85, -0.30)),
    "rule_intel - rule_heuristic": (-0.05, (-0.15, 0.00)),
}


def main() -> int:
    if not RES.is_file():
        print(f"  results not present: {RES}")
        return 0
    d = json.loads(RES.read_text(encoding="utf-8"))

    print("=" * 92)
    print("appendix tab:intervention  vs  grid_info_experiment output")
    print("=" * 92)
    cfg = d.get("config") or {}
    print(f"  config: {json.dumps(cfg, ensure_ascii=False)[:150]}")

    systems = d.get("systems") or {}
    print(f"\n  --- per-system success rate ---")
    print(f"  {'system':<20}{'n':>4}{'SR':>9}{'paper':>8}")
    bad = 0
    for name, pv in PAPER_SR.items():
        blk = systems.get(name)
        if not isinstance(blk, dict):
            print(f"  {name:<20} ABSENT")
            bad += 1
            continue
        lst = blk.get("sr_list") or []
        sr = blk.get("sr")
        if sr is None and lst:
            sr = sum(1 for x in lst if x) / len(lst)
        ok = isinstance(sr, (int, float)) and abs(sr - pv) <= 0.006
        if not ok:
            bad += 1
        print(f"  {name:<20}{len(lst):>4}{(sr if sr is not None else float('nan')):>9.4f}"
              f"{pv:>8.2f}{'' if ok else '   <-- DIFFERS'}")

    print(f"\n  --- contrasts (delta SR and 95% CI) ---")
    print(f"  {'contrast':<34}{'ours':>9}{'paper':>8}{'our CI':>20}{'paper CI':>18}")
    cons = d.get("contrasts") or {}
    for key, (pv, pci) in PAPER_CONTRAST.items():
        blk = cons.get(key)
        if not isinstance(blk, dict):
            print(f"  {key:<34} ABSENT")
            bad += 1
            continue
        ds, ci = blk.get("delta_SR"), blk.get("ci95")
        ok = (isinstance(ds, (int, float)) and abs(ds - pv) <= 0.006
              and ci and abs(ci[0] - pci[0]) <= 0.006 and abs(ci[1] - pci[1]) <= 0.006)
        if not ok:
            bad += 1
        ours_ci = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]" if ci else "-"
        paper_ci = f"[{pci[0]:+.3f}, {pci[1]:+.3f}]"
        print(f"  {key:<34}{ds if ds is not None else float('nan'):>+9.3f}{pv:>+8.2f}"
              f"{ours_ci:>20}{paper_ci:>18}{'' if ok else '  <-- DIFFERS'}")

    print(f"\n  mismatches: {bad}/{len(PAPER_SR) + len(PAPER_CONTRAST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

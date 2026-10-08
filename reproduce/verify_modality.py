"""Verify appendix tab:interface -- the natural-language vs JSON interface ablation.

Appendix H (appendix.tex 241-258):
    Tier (n)      NL SR   JSON SR   D(NL-JSON)   sign test
    simple (15)   93%     87%       +7%          p = 0.50
    medium (45)   69%     84%       -16%         p = 0.98
    complex (45)  11%     7%        +4.4%        p = 0.34
and the prose adds: "JSON accrues parse failures (9 in 45)".

The experiment script is `code/collaborator_snapshot/ablation_nl_json.py` ("A3
natural-language interface ablation (Appendix D, grid-exclusive)"). Its outputs are
three JSON files under `data/platform-results/`: one for the simple tier (15
episodes) and one each for the 45-episode medium and complex runs.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "data" / "platform-results"

# tier: (expected n, paper NL SR, paper JSON SR, source file)
PAPER = {
    "simple": (15, 0.93, 0.87, "ablation_nl_json.json"),
    "medium": (45, 0.69, 0.84, "ablation_nl_json_medium45.json"),
    "complex": (45, 0.11, 0.07, "ablation_nl_json_complex45.json"),
}


def main() -> int:
    if not RES.is_dir():
        print(f"  results not present: {RES}")
        return 0

    print("=" * 92)
    print("appendix tab:interface  vs  the A3 NL-vs-JSON ablation outputs")
    print("=" * 92)

    bad = 0
    print(f"\n  {'tier':<9}{'n':>4}{'NL SR':>9}{'paper':>8}{'JSON SR':>10}{'paper':>8}"
          f"{'D(NL-JSON)':>12}{'paper':>8}")
    for tier, (n, pnl, pjs, fname) in PAPER.items():
        p = RES / fname
        if not p.is_file():
            print(f"  {tier:<9} file absent: {fname}")
            bad += 1
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        blk = (d.get("summary") or {}).get(tier) or {}
        nl = blk.get("nl") or {}
        js = blk.get("json") or {}
        nl_sr, js_sr = nl.get("SR"), js.get("SR")
        n_got = nl.get("episodes") or nl.get("n")
        if not isinstance(nl_sr, (int, float)) or not isinstance(js_sr, (int, float)):
            print(f"  {tier:<9} could not read SR from {fname}")
            bad += 1
            continue
        delta = nl_sr - js_sr
        pd = pnl - pjs
        ok = abs(nl_sr - pnl) <= 0.006 and abs(js_sr - pjs) <= 0.006
        if not ok:
            bad += 1
        print(f"  {tier:<9}{n_got:>4}{nl_sr:>9.4f}{pnl:>8.2f}{js_sr:>10.4f}{pjs:>8.2f}"
              f"{delta:>+12.4f}{pd:>+8.3f}{'' if ok else '   <-- DIFFERS'}")

    # the "9 in 45" parse failures, and the simple-tier anomaly worth naming
    print(f"\n  --- parse failures (paper: 'JSON accrues parse failures (9 in 45)') ---")
    for tier, (_n, _a, _b, fname) in PAPER.items():
        p = RES / fname
        if not p.is_file():
            continue
        blk = (json.loads(p.read_text(encoding="utf-8")).get("summary") or {}).get(tier) or {}
        errs = {c: (blk.get(c) or {}).get("total_llm_errors") for c in ("nl", "json")}
        print(f"     {tier:<9} nl={errs['nl']}  json={errs['json']}")

    print(f"\n  --- note on the simple tier's source file ---")
    p = RES / "ablation_nl_json.json"
    if p.is_file():
        note = (json.loads(p.read_text(encoding="utf-8")).get("config") or {}).get("note")
        if note:
            print(f"     {note}")

    print(f"\n  tiers differing from the paper: {bad}/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

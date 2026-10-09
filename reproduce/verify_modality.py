"""Verify appendix tab:interface -- the natural-language vs JSON interface ablation.

Appendix H:
    Tier (n)      NL SR   JSON SR   D(NL-JSON)   sign test
    simple (15)   93%     87%       +7%          p = 0.50
    medium (45)   69%     84%       -16%         p = 0.98
    complex (45)  11%     7%        +4.4%        p = 0.34

The experiment script is `code/collaborator_snapshot/ablation_nl_json.py`; its outputs are
three JSON files under `data/platform-results/`.

TWO THINGS THIS CHECK EXISTS TO CATCH

1. The stored field is `sign_test_p_nl_gt_json` -- a p-value FOR "NL is better". On the
   medium row the table prints that 0.98 next to a Delta of -16% (JSON better), so the
   printed p-value points the opposite way to the row's own conclusion. The p-value for
   the stated direction is 0.059 one-sided, and that number does not appear in the paper
   at all. A check that only compares SR values passes straight over this.

2. The caption says "JSON wins at low semantic load; NL trends back at high load", but the
   simple tier is the one where NL wins (93% vs 87%). So the caption contradicts its own
   table.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "data" / "platform-results"

# tier: (expected n, paper NL SR, paper JSON SR, source file)
PAPER = {
    "simple": (15, 0.93, 0.87, "ablation_nl_json.json"),
    "medium": (45, 0.69, 0.84, "ablation_nl_json_medium45.json"),
    "complex": (45, 0.11, 0.07, "ablation_nl_json_complex45.json"),
}


def one_sided(k: int, n: int) -> float:
    """Exact one-sided sign-test p for 'k or more wins out of n' at p=0.5."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) * 0.5 ** n


def two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    probs = [math.comb(n, i) * 0.5 ** n for i in range(n + 1)]
    return min(1.0, sum(p for p in probs if p <= probs[k] + 1e-15))


def main() -> int:
    if not RES.is_dir():
        print(f"  results not present: {RES}")
        return 0

    print("=" * 96)
    print("appendix tab:interface  vs  the A3 NL-vs-JSON ablation outputs")
    print("=" * 96)

    bad = 0
    print(f"\n  {'tier':<9}{'n':>4}{'NL SR':>9}{'paper':>7}{'JSON SR':>10}{'paper':>7}"
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
        print(f"  {tier:<9}{n_got:>4}{nl_sr:>9.4f}{pnl:>7.2f}{js_sr:>10.4f}{pjs:>7.2f}"
              f"{delta:>+12.4f}{pd:>+8.3f}{'' if ok else '   <-- DIFFERS'}")

    # ---------------------------------------------------------------- paired + direction
    print(f"\n  --- paired discordant counts and the p-value IN THE STATED DIRECTION ---")
    print(f"  {'tier':<9}{'JSON win':>9}{'NL win':>8}{'same':>6}{'p(JSON>NL)':>12}"
          f"{'p(NL>JSON)':>12}{'stored':>10}  verdict")
    for tier, (_n, _a, _b, fname) in PAPER.items():
        p = RES / fname
        if not p.is_file():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        eps = (d.get("episodes") or {}).get(tier)
        blk = (d.get("summary") or {}).get(tier) or {}
        stored = blk.get("sign_test_p_nl_gt_json")
        if not isinstance(eps, dict) or "nl" not in eps or "json" not in eps:
            print(f"  {tier:<9} no per-episode pairs")
            continue
        nl_l, js_l = eps["nl"], eps["json"]
        if len(nl_l) != len(js_l):
            print(f"  {tier:<9} length mismatch {len(nl_l)} vs {len(js_l)}")
            bad += 1
            continue
        wj = wn = tie = 0
        for a, b in zip(nl_l, js_l):
            na, jb = bool(a.get("mission_success")), bool(b.get("mission_success"))
            if jb and not na:
                wj += 1
            elif na and not jb:
                wn += 1
            else:
                tie += 1
        disc = wj + wn
        p_json = one_sided(wj, disc) if disc else 1.0
        p_nl = one_sided(wn, disc) if disc else 1.0
        nl_sr = sum(bool(x.get("mission_success")) for x in nl_l) / len(nl_l)
        js_sr = sum(bool(x.get("mission_success")) for x in js_l) / len(js_l)
        better = "JSON" if js_sr > nl_sr else ("NL" if nl_sr > js_sr else "tie")
        # The stored field is P(NL > JSON). It is the RIGHT test when NL is the one ahead
        # (a large value then argues against NL), and the WRONG one when JSON is ahead --
        # there the row needs P(JSON > NL) instead.
        aligned = better in ("NL", "tie")
        verdict = "aligned" if aligned else f"WRONG DIRECTION (row favours {better})"
        if not aligned:
            bad += 1
        print(f"  {tier:<9}{wj:>9}{wn:>8}{tie:>6}{p_json:>12.4f}{p_nl:>12.4f}"
              f"{stored if stored is not None else '-':>10}  {verdict}")
        if not aligned:
            print(f"            the table prints {stored} = P(NL>JSON), but the row's own")
            print(f"            direction favours {better}. The matching p-value is "
                  f"{p_json:.4f} one-sided, {two_sided(wj, disc):.4f} two-sided.")
        elif disc and p_nl > 0.05:
            print(f"            (P(NL>JSON)={p_nl:.4f} > 0.05: the simple-tier difference is")
            print(f"             not significant either, so it should be reported as such.)")

    # ---------------------------------------------------------------- caption vs table
    print(f"\n  --- caption claim vs the table ---")
    print("     caption: 'JSON wins at low semantic load; NL trends back at high load'")
    for tier, (_n, _a, _b, fname) in PAPER.items():
        p = RES / fname
        if not p.is_file():
            continue
        blk = (json.loads(p.read_text(encoding="utf-8")).get("summary") or {}).get(tier) or {}
        nl_sr = (blk.get("nl") or {}).get("SR")
        js_sr = (blk.get("json") or {}).get("SR")
        if isinstance(nl_sr, (int, float)) and isinstance(js_sr, (int, float)):
            who = "NL" if nl_sr > js_sr else ("JSON" if js_sr > nl_sr else "tie")
            print(f"     {tier:<9} NL {nl_sr:.2%} vs JSON {js_sr:.2%}  -> {who} higher")
    print("     the caption's 'low load' tier is `simple`, where NL is higher.")

    print(f"\n  --- parse failures (paper: 'JSON accrues parse failures (9 in 45)') ---")
    for tier, (_n, _a, _b, fname) in PAPER.items():
        p = RES / fname
        if not p.is_file():
            continue
        blk = (json.loads(p.read_text(encoding="utf-8")).get("summary") or {}).get(tier) or {}
        errs = {c: (blk.get(c) or {}).get("total_llm_errors") for c in ("nl", "json")}
        print(f"     {tier:<9} nl={errs['nl']}  json={errs['json']}")

    print(f"\n  rows/sections mismatching the paper: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Appendix tab:modelinvariance — what this bundle can and cannot verify.

The table reports FOUR models. This bundle holds run data for TWO (Qwen3.8-27B, Qwen3-8B);
the two MiniMax MoE models were served through a third-party API and their batch is in no
reachable tree.

For the two that are present the contrast does not reproduce exactly, and this script
shows the candidate aggregations rather than asserting one, so the reader can see that the
question was explored rather than skipped.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = (ROOT / "data" / "campaigns" / "e6-model-invariance" / "analysis"
            / "e6_analysis.json")

PAPER = {"27b": 0.431, "8b": 0.464}
LABEL = {"27b": "Qwen3.8-27B", "8b": "Qwen3-8B"}


def main() -> int:
    if not ANALYSIS.is_file():
        print(f"  analysis not present: {ANALYSIS}")
        return 0
    d = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    recs = d.get("records", [])
    ref = set(d.get("reference_seeds") or [])

    print("=" * 92)
    print("appendix tab:modelinvariance  vs  e6-model-invariance")
    print("=" * 92)
    print(f"  schema          : {d.get('schema')}")
    print(f"  models present  : {list(d.get('models', {}).keys())}")
    print(f"  models in paper : Qwen3.8-27B, Qwen3-8B, MM-M3, MM-M2.7-hs")
    print(f"  conditions      : {d.get('conditions')}")
    print(f"  records         : {len(recs)}")
    print(f"  reference seeds : {sorted(ref)}")

    by: dict[tuple[str, str], dict] = defaultdict(dict)
    for r in recs:
        if isinstance(r.get("V"), (int, float)):
            by[(r["model"], r["condition"])][r["seed"]] = float(r["V"])

    subsets = [
        ("all seeds", lambda k: True),
        ("exclude 3 reference seeds", lambda k: k not in ref),
        ("reference seeds only", lambda k: k in ref),
    ]
    print(f"\n  {'model':<14}{'aggregation':<28}{'n':>4}{'strong-hold':>13}"
          f"{'paper':>9}{'diff':>9}")
    best = {}
    for mk, pv in PAPER.items():
        for label, sel in subsets:
            s, h = by.get((mk, "strong"), {}), by.get((mk, "hold"), {})
            seeds = sorted(k for k in set(s) & set(h) if sel(k))
            if not seeds:
                continue
            m = st.mean(s[k] - h[k] for k in seeds)
            if mk not in best or abs(m - pv) < abs(best[mk][0] - pv):
                best[mk] = (m, label, len(seeds))
            print(f"  {LABEL[mk]:<14}{label:<28}{len(seeds):>4}{m:>13.3f}"
                  f"{pv:>9.3f}{m - pv:>+9.3f}")

    print(f"\n  --- closest aggregation per model ---")
    for mk, pv in PAPER.items():
        if mk in best:
            m, label, n = best[mk]
            print(f"     {LABEL[mk]:<14} {label:<28} n={n:<3} {m:+.3f} "
                  f"(paper {pv:+.3f}, gap {m - pv:+.3f})")

    print(f"\n  --- not verifiable from this bundle ---")
    for nm in ("MM-M3", "MM-M2.7-hs"):
        print(f"     {nm:<14} third-party MoE API; no run data in any reachable tree")

    gaps = [abs(best[mk][0] - PAPER[mk]) for mk in PAPER if mk in best]
    print(f"\n  exact match for either present model: "
          f"{'yes' if all(g <= 0.005 for g in gaps) else 'no'}")
    print(f"  closest gaps: {[round(g, 3) for g in gaps]}  (tolerance 0.005)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

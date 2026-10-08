"""Verify appendix tab:complexlayered against the P0_GRID_COMPLEX_LAYERED batch.

Appendix (appendix.tex ~140-150) reports a five-seed paired four-stack batch on the
complex tier, seeds 63101-63105, with a fixed medium checkpoint:

    Rule (rule planner + GOAI heuristic)  0.787   80%
    Pure MAPPO (fixed medium checkpoint)  0.240    0%
    LLM+heuristic                         0.400   20%

The batch is `P0_GRID_COMPLEX_LAYERED_20261006_p01`, whose directory name says nothing
about "complex tier" -- which is why a filename search for this table came up empty while
the data was in the bundle the whole time.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = ROOT / "data" / "collaborator_runs" / "P0_GRID_COMPLEX_LAYERED_20261006_p01"

PAPER = {          # arm tag -> (mean V, success rate)
    "rule": (0.787, 0.80),
    "pure-mappo": (0.240, 0.00),
    "llm-heuristic": (0.400, 0.20),
}


def main() -> int:
    per_seed = BATCH / "analysis" / "a01" / "per_seed.json"
    if not per_seed.is_file():
        print(f"  batch not present: {BATCH}")
        return 0
    rows = json.loads(per_seed.read_text(encoding="utf-8"))

    print("=" * 92)
    print("appendix tab:complexlayered  vs  P0_GRID_COMPLEX_LAYERED_20261006_p01")
    print("=" * 92)
    print(f"  episode records: {len(rows)}")

    by: dict[str, list] = defaultdict(list)
    for r in rows:
        by[r.get("arm")].append(r)

    print(f"\n  {'arm':<16}{'n':>4}{'mean V':>10}{'paper':>9}{'diff':>9}"
          f"{'SR':>7}{'paper':>8}")
    bad = 0
    for arm, (pv, psr) in PAPER.items():
        rs = by.get(arm, [])
        V = [r["V"] for r in rs if isinstance(r.get("V"), (int, float))]
        SR = [r["success"] for r in rs if isinstance(r.get("success"), bool)]
        if not V:
            print(f"  {arm:<16}{0:>4}{'MISSING':>10}")
            bad += 1
            continue
        m = st.mean(V)
        sr = sum(SR) / len(SR) if SR else float("nan")
        ok = abs(m - pv) <= 0.0005 and abs(sr - psr) <= 0.0005
        if not ok:
            bad += 1
        print(f"  {arm:<16}{len(V):>4}{m:>10.3f}{pv:>9.3f}{m - pv:>+9.3f}"
              f"{sr:>7.0%}{psr:>8.0%}{'' if ok else '  <-- DIFFERS'}")

    seeds = sorted({r.get("seed") for r in rows if r.get("seed")})
    print(f"\n  seeds: {seeds}")
    print(f"  arms present: {sorted(by)}")
    print(f"\n  mismatches: {bad}/{len(PAPER)}")
    print(f"  status    : {'ALL AGREE' if bad == 0 else 'REVIEW REQUIRED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

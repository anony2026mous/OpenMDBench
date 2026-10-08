"""A/B: the pre-change code vs the live code, same scenario, same seed.

This is the real baseline-drift test.  Comparing live results against the archived
RESULTS directory proves nothing (that directory is a superset of the live one, so
the two sets agree by construction - a mistake made earlier in this session).  What
actually has to hold is that the CODE that produced the old baseline still produces
the same decisions, i.e. that none of the shared-module edits reached the
single-architecture path.

Method: run the archived `code/` snapshot in a sandbox (PYTHONPATH puts it ahead of
the live tree) and diff its report against a live run of the same cell, field by
field, ignoring wall-clock noise only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")

NOISE = {"elapsed_seconds", "ticks_per_second", "step_mean_seconds",
         "step_max_seconds", "resumed_from", "start_tick", "steps"}


def canon(obj):
    if isinstance(obj, dict):
        return {k: canon(v) for k, v in sorted(obj.items()) if k not in NOISE}
    if isinstance(obj, list):
        items = [canon(x) for x in obj]
        try:
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True,
                                                          ensure_ascii=False))
        except Exception:  # noqa: BLE001
            return items
    if isinstance(obj, float):
        return round(obj, 9)
    return obj


def digest(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        return None
    d = {k: v for k, v in d.items() if k not in NOISE}
    return d


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: _w1_ab_code_compare.py <arch.json> <live.json> [label]")
        return 2
    pa, pb = RUNS / sys.argv[1], RUNS / sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else "A/B"
    print("=" * 96)
    print(f"CODE A/B COMPARISON   {label}")
    print("=" * 96)
    print(f"  A (pre-change) : {pa.name}")
    print(f"  B (live)       : {pb.name}")
    for p in (pa, pb):
        if not p.exists():
            print(f"  MISSING: {p}")
            return 2

    da, db = digest(pa), digest(pb)
    keys = sorted(set(da) | set(db))
    diffs = []
    print(f"\n  {'field':<34}{'verdict'}")
    print("  " + "-" * 70)
    for k in keys:
        va, vb = canon(da.get(k)), canon(db.get(k))
        same = va == vb
        if not same:
            diffs.append(k)
        print(f"  {k:<34}{'IDENTICAL' if same else 'DIFFERS'}")
        if not same:
            sa = json.dumps(va, ensure_ascii=False, sort_keys=True)
            sb = json.dumps(vb, ensure_ascii=False, sort_keys=True)
            print(f"      A: {sa[:200]}")
            print(f"      B: {sb[:200]}")

    print(f"\n  differing fields: {len(diffs)} {diffs if diffs else ''}")
    print("  VERDICT:", "PASS - pre-change and live code agree bit-for-bit"
          if not diffs else f"FAIL - {len(diffs)} field(s) moved")
    return 0 if not diffs else 1


if __name__ == "__main__":
    raise SystemExit(main())

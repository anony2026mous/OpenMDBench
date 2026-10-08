"""Provenance audit of the ARCHIVED baseline runs.

The single-architecture arms (`rule-rule`, `rl`) are reused as controls rather than
re-run, so their configuration has to be shown to match the configuration used for
the LLM arms.  The dangerous mismatch is a different `decision-interval`: for the rl
arm that knob is the action-hold length, and evaluating at 2x the training value is
a documented train/eval mismatch that already invalidated a batch once.

So: read the recorded provenance out of the archived reports and check it against
the values this session uses.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

SNAP = (Path(os.path.expanduser("~")) / "openmd_private_archive"
        / "declared_briefing_snapshot_20260927_1419" / "results")

KEYS = ("checkpoint_meta", "decision_interval", "decision_interval_ticks",
        "speed_source", "speed_source_provenance", "theta", "doctrine",
        "overkill_cap", "overkill_release", "adherence_window_ticks")


def blocks(d):
    de = d.get("defender") or {}
    out = {}
    for blk in ("planner", "executor"):
        b = de.get(blk)
        if isinstance(b, dict):
            out[blk] = b
    return out


def main() -> int:
    arm = sys.argv[1] if len(sys.argv) > 1 else "rl"
    planner = "rl" if arm == "rl" else "rule"
    files = sorted(SNAP.glob(f"ie_{planner}_*.json"))
    print("=" * 100)
    print(f"ARCHIVED BASELINE PROVENANCE   arm={arm}   files={len(files)}")
    print("=" * 100)

    tally: Counter = Counter()
    shown = 0
    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict) or d.get("planner") != planner:
            continue
        card = d.get("strategy_scorecard") or {}
        if int(d.get("ticks_run") or 0) <= 0:
            continue
        if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
            continue
        found = {}
        for blk, b in blocks(d).items():
            for k in KEYS:
                if k in b:
                    v = b[k]
                    if isinstance(v, dict):
                        v = json.dumps(v, sort_keys=True, ensure_ascii=False)
                    found[f"{blk}.{k}"] = v
        sig = tuple(sorted((k, str(v)) for k, v in found.items()))
        tally[sig] += 1
        if shown < 6 and found:
            shown += 1
            print(f"\n  {p.name}")
            for k, v in sorted(found.items()):
                print(f"    {k:<34} {str(v)[:150]}")

    print("\n--- distinct provenance signatures ---")
    for sig, n in tally.most_common():
        print(f"\n  {n} episode(s):")
        if not sig:
            print("    (no provenance fields recorded)")
        for k, v in sig:
            print(f"    {k:<34} {v[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

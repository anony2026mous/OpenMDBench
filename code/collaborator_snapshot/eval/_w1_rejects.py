"""Break down fire submissions vs executed shots per arm report.

Usage:
    python _w1_rejects.py <report.json> [<report.json> ...]

Prints, for each report: how many shots each side submitted, how many were
executed, and the engine error codes carried by the rejected ones.  This is the
quickest way to tell *why* an arm produced no casualties -- a weapon-或 domain-
scoped rejection shows up here long before it shows up in the scorecard.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

def _walk(node, path=""):
    """Yield ``(path, leaf)`` for every scalar in a nested report."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, node


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for raw in argv[1:]:
        path = Path(raw)
        report = json.loads(path.read_text(encoding="utf-8"))
        print(f"=== {path.name} ===")
        print(f"  ticks_run={report.get('ticks_run')} aborted={report.get('aborted')}")
        outcome = report.get("outcome") or report.get("mission_success")
        print(f"  outcome={outcome}")

        tallies = report.get("layered_metrics") or {}
        print(f"  total_fires={tallies.get('total_fires')} "
              f"(blue={tallies.get('total_fires_defender')} "
              f"red={tallies.get('total_fires_intruder')})")

        # Preferred source: the runner's own per-rejection tally.
        rejections = report.get("fire_rejections") or {}
        if rejections:
            print("  fire rejections by side and engine code:")
            for key, count in sorted(rejections.items(), key=lambda kv: -kv[1]):
                print(f"    {key:<46} x{count}")
        else:
            codes: Counter[str] = Counter()
            for key, value in _walk(report):
                if key.endswith("error_code") or key.endswith("reason"):
                    codes[str(value)] += 1
            if codes:
                print("  rejection/evidence reason codes (scanned):")
                for code, count in codes.most_common(12):
                    print(f"    {code:<46} x{count}")
            else:
                print("  no rejection evidence recorded in this report")

        by_role = report.get("engagements_by_target_role") or {}
        if by_role:
            print("  engagement intents by side and target role "
                  "(includes denied attempts):")
            for key, count in sorted(by_role.items()):
                print(f"    {key:<46} x{count}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

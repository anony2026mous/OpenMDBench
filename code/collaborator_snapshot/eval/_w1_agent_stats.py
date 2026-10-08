"""Side-by-side dump of the planner/broker/executor tallies of several arms.

Usage:
    python _w1_agent_stats.py <report.json> [<report.json> ...]

The three-arm scorecard says *what* a defensive method scored; these counters say
*why* -- how many LLM goals were accepted versus rejected, how many the executor
completed, and how much of the episode ran in fallback/safe mode.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return "n/a" if value is None else str(value)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2

    rows: list[tuple[str, dict]] = []
    for raw in argv[1:]:
        path = Path(raw)
        report = json.loads(path.read_text(encoding="utf-8"))
        defender = report.get("defender") or {}
        flat: dict[str, object] = {"outcome": (report.get("layered_metrics") or {}).get("outcome")}
        planner_names = sorted(
            key
            for key in ("planner", "broker", "executor")
            if isinstance(defender.get(key), dict)
        )
        for section in planner_names:
            for key, value in defender[section].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    flat[f"{section}.{key}"] = value
        for key in ("fires", "plan_cycles", "submitted_batches", "name"):
            if key in defender:
                flat[key] = defender[key]
        flat["attack.fires_submitted"] = (report.get("attack") or {}).get("fires_submitted")
        flat["elapsed_s"] = report.get("elapsed_seconds")
        flat["ticks_per_s"] = report.get("ticks_per_second")
        flat["step_mean_s"] = report.get("step_mean_seconds")
        rows.append((path.stem, flat))

    keys = sorted({key for _name, flat in rows for key in flat})
    width = max(len(key) for key in keys) + 2
    header = "metric".ljust(width) + "".join(name.ljust(20) for name, _ in rows)
    print(header)
    print("-" * len(header))
    for key in keys:
        line = key.ljust(width)
        for _name, flat in rows:
            line += _fmt(flat.get(key)).ljust(20)
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

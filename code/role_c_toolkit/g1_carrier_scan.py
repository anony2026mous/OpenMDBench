"""Before declaring G1 terminated, test whether a finer damage carrier shows the dose response.

V (blue_score) is coarse: the pilot produced only a few distinct values.  The checklist's
criterion 2 allows the monotonic trend to be measured on the layer-attributed effect, so any
monotone damage proxy is admissible.  This scans the metrics already stored in every pilot
episode for a carrier whose tier profile is monotone in dose.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_PILOT = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/pilot")
DOSES = ("0.05", "0.10", "0.20", "0.40", "0.60")
CASES = ("planner_wrong_contact", "action_hold")


def episode_metrics(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    metrics = dict(payload.get("metrics") or {})
    metrics["__V"] = payload.get("V")
    metrics["__steps"] = payload.get("steps")
    metrics["__fault_events"] = (payload.get("fault_injection") or {}).get("fault_event_count")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_PILOT)
    args = parser.parse_args()
    PILOT = args.root
    clean = {}
    for seed_dir in sorted((PILOT / "clean").glob("seed-*")):
        seed = seed_dir.name.split("-")[-1]
        metrics = episode_metrics(seed_dir / "episode.json")
        if metrics:
            clean[seed] = metrics
    print(f"clean seeds: {sorted(clean)}")
    if clean:
        sample = next(iter(clean.values()))
        print(f"可用字段: {sorted(k for k in sample if not k.startswith('__'))}")
    print()

    for case in CASES:
        case_dir = PILOT / case
        if not case_dir.is_dir():
            continue
        print(f"=== {case} ===")
        # gather per-tier, per-seed metric values
        table: dict[str, dict[str, dict[str, float]]] = {}
        for seed_dir in sorted(case_dir.glob("seed-*")):
            seed = seed_dir.name.split("-")[-1]
            for dose_dir in sorted(seed_dir.glob("dose-*")):
                dose = dose_dir.name.replace("dose-", "")
                metrics = episode_metrics(dose_dir / "episode.json")
                if metrics:
                    table.setdefault(dose, {})[seed] = metrics

        # candidate carriers = numeric keys present everywhere
        keys: set[str] = set()
        for dose_map in table.values():
            for metrics in dose_map.values():
                keys |= {k for k, v in metrics.items() if isinstance(v, (int, float))}
        keys |= {"__V", "__steps", "__fault_events"}

        rows = []
        for key in sorted(keys):
            profile = []
            complete = True
            for dose in DOSES:
                values = [table.get(dose, {}).get(seed, {}).get(key) for seed in clean]
                values = [v for v in values if isinstance(v, (int, float))]
                if not values:
                    complete = False
                    break
                profile.append(sum(values) / len(values))
            if not complete or len(profile) < 5:
                continue
            # damage should increase with dose; measure both directions
            up = sum(1 for a, b in zip(profile, profile[1:]) if b > a)
            down = sum(1 for a, b in zip(profile, profile[1:]) if b < a)
            rows.append((max(up, down), key, profile, up, down))

        print(f"  {'字段':24s}{'一致对':>7}  {'方向':>4}  逐档均值")
        for consistent, key, profile, up, down in sorted(rows, reverse=True)[:10]:
            arrow = "↑" if up >= down else "↓"
            print(f"  {key:24s}{consistent:>5}/4  {arrow:>4}  "
                  + " ".join(f"{v:.3f}" for v in profile))
        print()


if __name__ == "__main__":
    main()

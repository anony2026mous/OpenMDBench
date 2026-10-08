"""G1 criterion check on the full 10-seed run, reported per carrier.

Motivation: on this base the mission score is ceiling-limited (6 of 10 clean seeds already score
1.0), so a fault cannot move it down.  The full run nevertheless shows that some carriers respond
monotonically to fault dose.  This script separates the two readings:

* **mission-outcome carriers** (V / blue_score): what criterion 2 was written against
* **behavioural carriers** (steps, fuel, locks, ...): what actually responds

For each carrier it reports the tier means, the seed-bootstrap CI of the tier effect, the monotone
adjacent-pair count, and whether the CI excludes zero at the lowest and highest tiers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d2_headroom  # noqa: E402

DEFAULT_ROOT = Path("/mnt/<lab>/<user>-codex/experiments/g1-fault-dose/full")
DOSES = ("0.05", "0.10", "0.20", "0.40", "0.60")
CASES = ("planner_wrong_contact", "action_hold")
MISSION = ("V", "blue_score")
BEHAVIOURAL = ("steps", "fuel_consumed", "red_intercepted", "lock_maintenance_ratio",
               "ammo_efficiency", "intercept_lock_rate", "locks_acquired")


def read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    metrics = dict(payload.get("metrics") or {})
    metrics["V"] = payload.get("V")
    metrics["steps"] = payload.get("steps")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    root = args.root

    clean = {}
    for seed_dir in sorted((root / "clean").glob("seed-*")):
        metrics = read(seed_dir / "episode.json")
        if metrics:
            clean[seed_dir.name.split("-")[-1]] = metrics
    at_ceiling = sum(1 for m in clean.values() if m.get("V") == 1.0)
    print(f"clean seeds={len(clean)}  其中 V=1.0（天花板）的: {at_ceiling}/{len(clean)}")
    print()

    out: dict = {"schema": "g1-criterion-check@1", "root": str(root),
                 "clean_seeds": len(clean), "clean_at_ceiling": at_ceiling, "cases": {}}

    for case in CASES:
        case_dir = root / case
        if not case_dir.is_dir():
            continue
        # tier -> seed -> metrics
        table: dict[str, dict[str, dict]] = {}
        for seed_dir in sorted(case_dir.glob("seed-*")):
            seed = seed_dir.name.split("-")[-1]
            for dose_dir in sorted(seed_dir.glob("dose-*")):
                metrics = read(dose_dir / "episode.json")
                if metrics:
                    table.setdefault(dose_dir.name.replace("dose-", ""), {})[seed] = metrics

        print(f"=== {case} ===")
        case_out: dict = {}
        for carrier in MISSION + BEHAVIOURAL:
            profile, diffs_by_tier, ci_by_tier = [], {}, {}
            for dose in DOSES:
                seeds = sorted(set(table.get(dose, {})) & set(clean))
                diffs = []
                for seed in seeds:
                    a = table[dose][seed].get(carrier)
                    b = clean[seed].get(carrier)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        diffs.append(a - b)
                vals = [table[dose][s].get(carrier) for s in seeds]
                vals = [v for v in vals if isinstance(v, (int, float))]
                if not vals:
                    continue
                profile.append(sum(vals) / len(vals))
                diffs_by_tier[dose] = diffs
                ci = d2_headroom.bootstrap_ci(diffs) if diffs else [None, None]
                ci_by_tier[dose] = [round(ci[0], 4) if ci[0] is not None else None,
                                    round(ci[1], 4) if ci[1] is not None else None]
            if len(profile) < 5:
                continue
            up = sum(1 for a, b in zip(profile, profile[1:]) if b > a)
            down = sum(1 for a, b in zip(profile, profile[1:]) if b < a)
            best = max(up, down)
            direction = "↑" if up >= down else "↓"
            # CI excludes zero at the extreme tiers?
            extreme = []
            for dose in (DOSES[0], DOSES[-1]):
                lo, hi = ci_by_tier.get(dose, [None, None])
                if lo is not None:
                    extreme.append(bool(lo > 0 or hi < 0))
            kind = "任务结果" if carrier in MISSION else "行为学"
            print(f"  [{kind}] {carrier:24s} {direction} {best}/4  "
                  f"极端档CI排除0: {sum(extreme)}/2  "
                  f"profile={' '.join(f'{v:.3f}' for v in profile)}")
            case_out[carrier] = {
                "kind": kind,
                "monotone_consistent": best,
                "monotone_total": 4,
                "direction": direction,
                "profile": [round(v, 4) for v in profile],
                "ci_by_tier": ci_by_tier,
                "extreme_ci_excludes_zero": extreme,
                "per_seed_diffs": diffs_by_tier,
            }
        out["cases"][case] = case_out
        print()

    out_path = args.out or (root / "criterion_check.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written {out_path}")


if __name__ == "__main__":
    main()

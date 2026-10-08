"""Compute the 2x2 headroom x planning-information table from the E1 gate-screening arms.

Cells (all scripted, no LLM, no new episodes):

    planning information present  : rule-strong-g1
    planning information withheld : rule-strong-g0

    headroom axis = interceptor-count condition (N017 ... N027), whose pure-baseline V
    determines whether the scenario still has room.

Reported per cell: mean, per-seed values, paired g1-g0 difference with a seed-bootstrap 95% CI,
and the difference-in-differences between the least-headroom and most-headroom condition.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SCREEN = Path("/mnt/<lab>/<user>-codex/experiments/E1_device-b_v13_p01_20261004"
              "/bundle/data/gate-screening")
ARM_INFO = "rule-strong-g1"
ARM_BASE = "rule-strong-g0"
DRAWS = 20000
SEED = 20261006


def per_seed_value(seed_dir: Path) -> float | None:
    for candidate in sorted(seed_dir.rglob("*.json")):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for source in (payload.get("layered_metrics") or {},
                       payload.get("strategy_scorecard") or {}, payload):
            if not isinstance(source, dict):
                continue
            for key in ("performance_v", "defender_score", "V", "utility", "composite"):
                value = source.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
    return None


def read_arm(root: Path, arm: str) -> dict[int, float]:
    values: dict[int, float] = {}
    arm_dir = root / arm
    if not arm_dir.is_dir():
        return values
    for seed_dir in sorted(arm_dir.iterdir()):
        if not seed_dir.is_dir():
            continue
        try:
            seed = int(seed_dir.name.split("-")[-1])
        except ValueError:
            continue
        value = per_seed_value(seed_dir)
        if value is not None:
            values[seed] = value
    return values


def bootstrap_ci(values: list[float], draws: int = DRAWS, seed: int = SEED) -> list[float]:
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(draws):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return [means[int(0.025 * draws)], means[int(0.975 * draws)]]


def main() -> None:
    if not SCREEN.is_dir():
        print(f"缺失: {SCREEN}")
        return
    conditions = sorted(p.name for p in SCREEN.iterdir() if p.is_dir())
    rows = []
    for condition in conditions:
        root = SCREEN / condition
        info = read_arm(root, ARM_INFO)
        base = read_arm(root, ARM_BASE)
        shared = sorted(set(info) & set(base))
        if not shared:
            print(f"{condition}: 两臂无共同 seed")
            continue
        diffs = [info[s] - base[s] for s in shared]
        rows.append({
            "condition": condition,
            "n": len(shared),
            "mean_info": sum(info[s] for s in shared) / len(shared),
            "mean_base": sum(base[s] for s in shared) / len(shared),
            "per_seed_info": [info[s] for s in shared],
            "per_seed_base": [base[s] for s in shared],
            "per_seed_diff": diffs,
            "mean_diff": sum(diffs) / len(diffs),
            "ci_diff": bootstrap_ci(diffs),
        })

    print(f"规划信息臂 = {ARM_INFO}；基准臂 = {ARM_BASE}（同规划器同执行器，仅差目标信息）\n")
    print(f"{'条件':<30}{'n':>3}{'信息多':>10}{'信息少':>10}{'增益':>10}{'95% CI':>20}")
    for row in rows:
        ci = row["ci_diff"]
        print(f"{row['condition']:<30}{row['n']:>3}{row['mean_info']:>10.4f}"
              f"{row['mean_base']:>10.4f}{row['mean_diff']:>+10.4f}"
              f"{'[' + format(ci[0], '.3f') + ',' + format(ci[1], '.3f') + ']':>20}")

    if len(rows) >= 2:
        low = min(rows, key=lambda r: r["mean_base"])   # least headroom
        high = max(rows, key=lambda r: r["mean_base"])  # most room
        shared = sorted(set(range(len(low["per_seed_diff"]))) & set(range(len(high["per_seed_diff"]))))
        did = [high["per_seed_diff"][i] - low["per_seed_diff"][i] for i in shared]
        mean_did = sum(did) / len(did)
        ci = bootstrap_ci(did)
        print()
        print("=== 差中差（交互效应）===")
        print(f"  最无 headroom 的条件（基准 V 最低）: {low['condition']} 基准 V={low['mean_base']:.4f}")
        print(f"  最有 headroom 的条件（基准 V 最高）: {high['condition']} 基准 V={high['mean_base']:.4f}")
        print(f"  交互效应 (Δ高 − Δ低) = {mean_did:+.4f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")
        print(f"  逐 seed 交互值: {[round(v, 4) for v in did]}")

    out = Path("role_c_toolkit/artifacts/e4-scenario-family/analysis/e1_2x2_planning_information.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "e1-2x2-planning-information@1",
        "source": str(SCREEN),
        "arm_information_present": ARM_INFO,
        "arm_information_withheld": ARM_BASE,
        "note": ("same rule planner and same executor in both arms; the arms differ only in "
                 "whether goal information is supplied, so the contrast is the planning-"
                 "information lever requested by the 2x2 design"),
        "rows": rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main()

"""论文证据覆盖审计：逐 (场景 × 臂) 数有效局数与种子数。

判据：只收当前评分口径（`scored_weight != None`）、非中止、有终局的局。
用途：找出论文里"样本不足以支撑结论"的格子。

用法：python _w1_coverage_audit.py
"""
from __future__ import annotations

import collections
import json
import pathlib

RUNS = pathlib.Path(__file__).resolve().parent / "_w1_runs"

SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE",
]
ARMS = [
    "rule-rule", "rl", "pure-llm", "llm-rule",
    "llm-rl@arm5_llm_reward_v9", "rule-rl",
]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}


def collect():
    count = collections.Counter()
    seeds = collections.defaultdict(set)
    total = 0
    for path in sorted(RUNS.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(report, dict):
            continue
        card = report.get("strategy_scorecard") or {}
        if card.get("scored_weight") is None:
            continue
        if report.get("aborted") or int(report.get("ticks_run") or 0) <= 0:
            continue
        if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
            continue
        scenario = ALIAS.get(str(report.get("scenario")), str(report.get("scenario")))
        if scenario not in SCENARIOS:
            continue
        planner = str(report.get("planner"))
        executor = (report.get("defender") or {}).get("executor") or {}
        ckpt = (executor.get("checkpoint_meta") or {}).get("tag") \
            if isinstance(executor, dict) else None
        arm = {"rule": "rule-rule", "rl": "rl", "pure-llm": "pure-llm",
               "llm": "llm-rule"}.get(planner, planner)
        if planner == "llm-rl":
            arm = "llm-rl@" + str(ckpt)
        if planner == "rule-rl":
            arm = "rule-rl"
        count[(scenario, arm)] += 1
        seeds[(scenario, arm)].add(report.get("seed"))
        total += 1
    return count, seeds, total


def main() -> int:
    count, seeds, total = collect()
    header = f"{'场景':30}" + "".join(f"{a.split('@')[0][:9]:>11}" for a in ARMS)
    print("覆盖矩阵（有效局数 / 种子数）；`--` = 无数据")
    print(header)
    print("-" * len(header))
    for scenario in SCENARIOS:
        row = f"{scenario:30}"
        for arm in ARMS:
            n = count.get((scenario, arm), 0)
            k = len(seeds.get((scenario, arm), set()))
            row += f"{n:>5}/{k:<5}" if n else f"{'--':>10}"
        print(row)

    print()
    zero = [(s, a) for s in SCENARIOS for a in ARMS if count.get((s, a), 0) == 0]
    one = [(s, a) for s in SCENARIOS for a in ARMS if count.get((s, a), 0) == 1]
    two = [(s, a) for s in SCENARIOS for a in ARMS if count.get((s, a), 0) == 2]
    print(f"当前口径有效局总数：{total}")
    print(f"n = 0 的格：{len(zero)}")
    for s, a in zero:
        print(f"    {s:30} {a}")
    print(f"n = 1 的格：{len(one)}（论文里无法判显著性）")
    print(f"n = 2 的格：{len(two)}")
    print(f"n >= 3 的格：{sum(1 for s in SCENARIOS for a in ARMS if count.get((s, a), 0) >= 3)}"
          f" / {len(SCENARIOS) * len(ARMS)}")

    # 主权重之外的权重覆盖（论文需要"为什么选这个权重"的证据）
    print()
    print("各 checkpoint 在争议两格（IE-01 / IE-08）上的覆盖：")
    for tag in ("arm5_llm_reward_v9", "arm5_llm_full_ie03_v10", "arm5_v11",
                "arm5_v12", "arm5_v13_ie08", "arm5_di1"):
        for scenario in ("IE-01-SINGLE-TARGET", "IE-08-ISLAND-STRIKE"):
            n = count.get((scenario, f"llm-rl@{tag}"), 0)
            if n:
                print(f"    {tag:26} {scenario:26} n={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

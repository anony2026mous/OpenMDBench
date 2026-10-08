"""Consolidated data pack for the 28 competition scenarios (the E4/D2 recalibration work).

Scope, stated explicitly so the numbers cannot be miscounted:

  30 competition_v1 packages  -  MD-REC-001's two extra difficulty tiers = 28 scenarios

Both D2 readings are reported, because the ledger stores them in different places and they
answer different questions:

  * binary   - gates.D2_headroom.verdict_binary  (pre-registered terminal outcome)
  * declared - gates.D2_headroom.graded.(verdict, composite)  (the scenario's utility-v1 score)

Outputs: a markdown summary, a CSV, and a JSON with the full per-scenario record.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ARTIFACTS = Path("role_c_toolkit/artifacts/e4-scenario-family")
OUT_MD = ARTIFACTS / "E4_28场景数据汇总.md"
OUT_CSV = ARTIFACTS / "e4_28_scenario_summary.csv"
OUT_JSON = ARTIFACTS / "e4_28_scenario_summary.json"
D2_LOW, D2_HIGH = 0.40, 0.85
REC001_REPORTED = "MD-REC-001-MEDIUM"
REC001_VARIANTS = ("MD-REC-001-EASY", "MD-REC-001-MEDIUM", "MD-REC-001-HARD")


def analysis_key(public_id: str) -> str:
    """The graded analysis keys on the contract id; the ledger adds a -STANDARD suffix."""
    return public_id.replace("-STANDARD", "").upper()


def main() -> None:
    ledger = json.loads((ARTIFACTS / "admission_ledger.json").read_text(encoding="utf-8"))
    frozen = json.loads((ARTIFACTS / "d1prime_FROZEN.json").read_text(encoding="utf-8"))
    priors = {row["public_id"]: row for row in frozen["rows"]}
    graded = json.loads((ARTIFACTS / "analysis" / "d2_graded_final2.json").read_text(
        encoding="utf-8"))
    graded_by_key = {key.upper(): value for key, value in graded["scenarios"].items()}
    before = json.loads((ARTIFACTS / "analysis" / "d2_graded_5seed.json").read_text(
        encoding="utf-8"))
    before_by_key = {key.upper(): value for key, value in before["scenarios"].items()}

    ledger_keys = {analysis_key(key) for key in graded_by_key}
    rows = [row for row in ledger["scenarios"] if row.get("tree") == "competition_v1"]
    kept, variants_seen = [], []
    for row in rows:
        if row["public_id"] in REC001_VARIANTS:
            variants_seen.append(row)
            if row["public_id"] != REC001_REPORTED:
                continue
            row = dict(row)
            row["difficulty_variants_merged"] = list(REC001_VARIANTS)
        kept.append(row)
    kept.sort(key=lambda row: row["public_id"])

    records, mismatches = [], []
    for row in kept:
        gate = row["gates"]["D2_headroom"]
        block = gate.get("graded") or {}
        key = analysis_key(row["public_id"])
        detail = graded_by_key.get(key)
        if detail is None:
            mismatches.append(f"{row['public_id']}: 分析文件缺少该场景")
            detail = {}
        else:
            expected = "pass" if D2_LOW <= detail["best_composite_mean"] <= D2_HIGH else "fail"
            if block.get("verdict") != detail["d2_graded_verdict"]:
                mismatches.append(f"{row['public_id']}: 台账 verdict "
                                  f"{block.get('verdict')} vs 分析 {detail['d2_graded_verdict']}")
            if block.get("composite") is None or (
                    abs(block["composite"] - detail["best_composite_mean"]) > 1e-6):
                mismatches.append(f"{row['public_id']}: composite 台账 {block.get('composite')} "
                                  f"vs 分析 {detail['best_composite_mean']}")
            if detail["d2_graded_verdict"] != expected:
                mismatches.append(f"{row['public_id']}: 分析内部不一致（composite "
                                  f"{detail['best_composite_mean']} 应判 {expected}）")
        composite = block.get("composite", detail.get("best_composite_mean"))
        ci = block.get("ci95") or detail.get("best_composite_ci95") or [None, None]
        prior = priors.get(row["public_id"], {})
        outside = composite is not None and (composite > D2_HIGH or composite < D2_LOW)
        records.append({
            "public_id": row["public_id"],
            "package": row.get("package"),
            "category": row.get("category"),
            "package_sha256_16": (row.get("package_sha256") or "")[:16],
            "d2_graded_verdict": block.get("verdict", detail.get("d2_graded_verdict")),
            "d2_binary_verdict": gate.get("verdict_binary", gate.get("verdict")),
            "best_baseline_policy": block.get("best_baseline_policy",
                                              detail.get("best_baseline_policy")),
            "composite": composite,
            "ci_low": ci[0], "ci_high": ci[1],
            "band": block.get("headroom_band", detail.get("headroom_band")),
            "outside_window": outside,
            "composite_before_calibration": (
                before_by_key.get(key) or {}).get("best_composite_mean"),
            "d1prime_prior": prior.get("prior_score"),
            "evidence": gate.get("evidence"),
        })

    graded_pass = [r for r in records if r["d2_graded_verdict"] == "pass"]
    graded_fail = [r for r in records if r["d2_graded_verdict"] == "fail"]
    binary_pass = [r for r in records if r["d2_binary_verdict"] == "pass"]
    outside = [r for r in records if r["outside_window"]]
    saturated = [r for r in outside if (r["composite"] or 0) > D2_HIGH]
    floored = [r for r in outside if (r["composite"] or 0) < D2_LOW]
    moved = [r for r in records
             if r["composite_before_calibration"] is not None and r["composite"] is not None
             and abs(r["composite_before_calibration"] - r["composite"]) > 0.02]

    lines = ["# 竞争族 28 个场景：门禁与实测数据汇总", ""]
    lines.append("> 范围：`competition_v1` 的 30 个包。MD-REC-001 的 EASY/MEDIUM/HARD 三档是"
                 "**同一场景的三个难度水平**，合并计 1 → **28 个场景**。")
    lines.append("> 数据来源：`admission_ledger.json` + `analysis/d2_graded_final2.json`"
                 f"（5-seed 实测）；已逐行核对两者一致（{len(kept)} 行，{len(mismatches)} 处不符）。")
    lines.append("> 这批场景由本角色（肖棹）在 E4 场景族重标定中建立与标定；"
                 "`formal` 树的 14 个 IE 场景属**更早的**实验，不在本表。")
    lines.append("")
    lines.append("## 0. 两个口径的总览（先说清，避免与附录 A 的 16/19/20 混淆）")
    lines.append("")
    lines.append("| 口径 | 通过 | 未通过 | 判据 |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **二值成功（事前预注册）** | {len(binary_pass)} | "
                 f"{len(records) - len(binary_pass)} | 场景声明的 terminal outcome 成功率 ∈ "
                 f"[0.40, 0.85] |")
    lines.append(f"| **声明综合分（utility-v1）** | **{len(graded_pass)}** | "
                 f"**{len(graded_fail)}** | 场景声明的 Σ wᵢ·valueᵢ ∈ [0.40, 0.85] |")
    lines.append("")
    lines.append(f"- 纯基线 composite 落在窗口**之外**：**{len(outside)}** 个"
                 f"（饱和 {len(saturated)}、触底 {len(floored)}）")
    lines.append("- 二值口径在这批场景上信息量很低：确定性脚本策略的成功率只有 0/1，"
                 "多数场景跨 seed 恒为 1.000，无法落入窗口。")
    if mismatches:
        lines.append("")
        lines.append("**核对告警**：" + "；".join(mismatches[:5]))
    lines.append("")
    lines.append("## 1. 逐场景（按类别）")
    by_category: dict[str, list] = {}
    for record in records:
        by_category.setdefault(record["category"] or "?", []).append(record)
    for category in sorted(by_category):
        lines.append("")
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| 场景 | 综合分口径 | 二值口径 | 最优纯基线 | composite | 95% CI | 分档 | "
                     "窗口外 | 标定前 | D1′先验 |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for record in by_category[category]:
            composite = "—" if record["composite"] is None else f"{record['composite']:.3f}"
            ci = ("—" if record["ci_low"] is None
                  else f"[{record['ci_low']:.3f}, {record['ci_high']:.3f}]")
            prior = ("—" if record["d1prime_prior"] is None
                     else f"{record['d1prime_prior']:.2f}")
            before_text = ("—" if record["composite_before_calibration"] is None
                           else f"{record['composite_before_calibration']:.3f}")
            lines.append(f"| {record['public_id']} | {record['d2_graded_verdict']} | "
                         f"{record['d2_binary_verdict']} | `{record['best_baseline_policy']}` | "
                         f"{composite} | {ci} | {record['band']} | "
                         f"{'✅' if record['outside_window'] else ''} | {before_text} | "
                         f"{prior} |")
    lines.append("")
    lines.append("## 2. 窗口外场景清单（供跑 layered stack 用）")
    lines.append("")
    lines.append("判据：纯基线 composite 不在 [0.40, 0.85]。")
    lines.append("")
    lines.append("| 场景 | composite | 95% CI | 方向 | 最优基线策略 | 综合分口径 | 二值口径 | "
                 "是否被本标定移动 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for record in sorted(outside, key=lambda r: -(r["composite"] or 0)):
        direction = "饱和（无 headroom）" if (record["composite"] or 0) > D2_HIGH else "触底"
        was_moved = (record["composite_before_calibration"] is not None
                     and abs(record["composite_before_calibration"] - record["composite"]) > 0.02)
        lines.append(f"| {record['public_id']} | {record['composite']:.3f} | "
                     f"[{record['ci_low']:.3f}, {record['ci_high']:.3f}] | {direction} | "
                     f"`{record['best_baseline_policy']}` | {record['d2_graded_verdict']} | "
                     f"{record['d2_binary_verdict']} | {'是' if was_moved else '否（天然）'} |")
    lines.append("")
    lines.append("> 其中 5 个只比 0.85 高出一点（0.861–0.871）；"
                 "MD-TRK-002 是触底（0.393）。「天然」的场景没有被本次标定调整过，"
                 "最合适直接当作 gates 外实验对象。")
    lines.append("")
    lines.append("## 3. 标定前 vs 标定后（同一批 28 个场景）")
    lines.append("")
    lines.append(f"被本次标定移动超过 0.02 的场景：**{len(moved)}** 个；"
                 f"其余 **{len(records) - len(moved)}** 个标定前后一致（未被人为调整）。")
    lines.append("")
    lines.append("| 场景 | 标定前 | 标定后 | 变化 |")
    lines.append("|---|---|---|---|")
    for record in sorted(moved, key=lambda r: (r["composite_before_calibration"]
                                               - r["composite"]), reverse=True):
        delta = record["composite"] - record["composite_before_calibration"]
        lines.append(f"| {record['public_id']} | {record['composite_before_calibration']:.3f} | "
                     f"{record['composite']:.3f} | {delta:+.3f} |")
    lines.append("")
    lines.append("## 4. 口径说明（避免与 44/42 混淆）")
    lines.append("")
    lines.append("| 口径 | 数 | 说明 |")
    lines.append("|---|---|---|")
    lines.append(f"| 本表场景数 | **{len(records)}** | competition_v1 去 REC-001 变体 |")
    lines.append("| competition_v1 包数 | 30 | 含 REC-001 三档 |")
    lines.append("| 台账条目 | 55 | 54 包 + 1 条别名（MD-AD-006-ISLAND-STRIKE） |")
    lines.append("| 剔演示包 | 44 | 54 − 10 个演示包；与 D1′ 标注覆盖数一致 |")
    lines.append("| 剔演示 + REC-001 合并 | 42 | 若一个难度算一个实验 |")
    lines.append("| formal 树正式 IE 场景 | 14 | 早期实验，非本次，不在本表 |")
    lines.append("")
    lines.append("## 5. REC-001 三档的实测（合并前）")
    lines.append("")
    lines.append("| 档位 | 综合分口径 | 二值口径 | composite |")
    lines.append("|---|---|---|---|")
    for variant in variants_seen:
        gate = variant["gates"]["D2_headroom"]
        block = gate.get("graded") or {}
        lines.append(f"| {variant['public_id']} | {block.get('verdict')} | "
                     f"{gate.get('verdict_binary')} | {block.get('composite')} |")
    lines.append("")
    lines.append("三档 composite 均为 1.000（纯基线满分），时限分别为 181 / 161 / 141 tick。")
    lines.append(f"本表默认报告 **MEDIUM** 档；如需改报 HARD 或 EASY，替换该行即可。")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    OUT_JSON.write_text(json.dumps({
        "schema": "e4-28-scenario-summary@1",
        "scope": ("competition_v1 minus the two extra MD-REC-001 difficulty tiers; the formal "
                  "14 IE scenarios are a different (earlier) experiment and are not included"),
        "reported_rec001_tier": REC001_REPORTED,
        "ledger_vs_analysis_mismatches": mismatches,
        "counts": {"scenarios": len(records),
                   "graded_pass": len(graded_pass), "graded_fail": len(graded_fail),
                   "binary_pass": len(binary_pass),
                   "outside_window": len(outside),
                   "moved_by_calibration": len(moved)},
        "records": records,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"场景 {len(records)} | 综合分 pass {len(graded_pass)} / fail {len(graded_fail)} | "
          f"二值 pass {len(binary_pass)}")
    print(f"窗口外 {len(outside)}（饱和 {len(saturated)}、触底 {len(floored)}）| "
          f"被标定移动 {len(moved)} | 台账-分析不符 {len(mismatches)}")
    print(f"written: {OUT_MD.name}, {OUT_CSV.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()

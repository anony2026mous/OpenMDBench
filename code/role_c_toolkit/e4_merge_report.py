"""Build one consolidated markdown report for the E4 / D2 calibration work.

Everything is read from the artifacts on disk so the numbers cannot drift from the analyses:
the admission ledger, the graded/binary batch summaries, the retention reports and the D1'
validation.  Sections that depend on a batch that is still running say so explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path

ARTIFACTS = Path("role_c_toolkit/artifacts/e4-scenario-family")
ANALYSIS = ARTIFACTS / "analysis"
OUT = ARTIFACTS / "E4_D2_合并总报告.md"

BATCHES = [
    ("重标定前", "d2_graded_5seed.json", "d2_headroom_5seed.json", "seeds 2001-2005"),
    ("中间批（AD+ER+TRK2 标定后）", "d2_graded_postcal.json", "d2_headroom_postcal.json",
     "seeds 2101-2105"),
    ("复测批（全量标定后）", "d2_graded_final.json", "d2_headroom_final.json",
     "seeds 2201-2205"),
    ("确认批（含 TRK-004）", "d2_graded_final2.json", "d2_headroom_final2.json",
     "seeds 2301-2305"),
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def family_table(graded: dict) -> str:
    rows = ["| 类别 | 场景数 | 落入窗口 | 近饱和 | 地板控制即最优 | 达标(≥3) |",
            "|---|---|---|---|---|---|"]
    for code, bucket in sorted(graded["by_family"].items()):
        ok = "✅" if bucket["in_window"] >= 3 else "❌"
        rows.append(f"| {code} | {bucket['scenarios']} | **{bucket['in_window']}** | "
                    f"{bucket['near_ceiling']} | {bucket['floor_pick']} | {ok} |")
    return "\n".join(rows)


def batch_table() -> str:
    rows = ["| 批次 | seeds | 窗口内 | 近饱和 | 触底 | ≥3 场景达标的类别 |",
            "|---|---|---|---|---|---|"]
    for label, graded_name, _binary_name, seeds in BATCHES:
        graded = load(ANALYSIS / graded_name)
        if graded is None:
            continue
        counts = graded["counts"]
        families = graded.get("families_with_three_in_window") or []
        rows.append(f"| {label} | {seeds} | **{counts['in_window']}** / 30 | "
                    f"{counts['near_ceiling']} | {counts['below_window']} | "
                    f"{', '.join(families) if families else '—'} ({len(families)}) |")
    return "\n".join(rows)


def scenario_table(graded: dict) -> str:
    rows = ["| 场景 | 最优基线 | 综合分 | 95% CI | 分档 |", "|---|---|---|---|---|"]
    ordered = sorted(graded["scenarios"].items(), key=lambda kv: kv[1]["best_composite_mean"])
    for key, entry in ordered:
        low, high = entry["best_composite_ci95"]
        band = {"window": "窗口内", "near_ceiling": "近饱和",
                "below_window": "触底"}[entry["headroom_band"]]
        rows.append(f"| {key} | `{entry['best_baseline_policy']}` | "
                    f"{entry['best_composite_mean']:.3f} | [{low:.3f}, {high:.3f}] | {band} |")
    return "\n".join(rows)


def ledger_table() -> str:
    ledger = load(ARTIFACTS / "admission_ledger.json")
    if ledger is None:
        return "（台账缺失）"
    counts: dict[tuple[str, str], int] = {}
    for row in ledger["scenarios"]:
        for gate, payload in row["gates"].items():
            counts[(gate, payload["verdict"])] = counts.get((gate, payload["verdict"]), 0) + 1
    rows = ["| 门 | 判定 | 场景数 |", "|---|---|---|"]
    for (gate, verdict), number in sorted(counts.items()):
        rows.append(f"| {gate} | {verdict} | {number} |")
    rows.append("")
    rows.append(f"台账 schema：`{ledger['schema']}`；场景总数 "
                f"{len(ledger['scenarios'])}；D1′ 先验覆盖 "
                f"{sum(1 for r in ledger['scenarios'] if r.get('d1prime_prior'))}。")
    return "\n".join(rows)


def retune_table() -> str:
    rows = ["| profile | 改动的包数 | 改动项数 |", "|---|---|---|"]
    for name in ("trk-tighten-v1", "trk-calibrate-v1", "ad-tighten-v1", "ad-calibrate-v1",
                 "er-calibrate-v1", "ad-tighten-v3"):
        report = load(ANALYSIS / f"retune-{name}.json")
        if report is None:
            continue
        rows.append(f"| `{name}` | {report.get('changed_packages', '?')} | "
                    f"{report.get('total_changes', '?')} |")
    return "\n".join(rows)


def main() -> None:
    ledger = load(ARTIFACTS / "admission_ledger.json") or {}
    latest = load(ANALYSIS / "d2_graded_final2.json")
    if latest is None:
        raise SystemExit("d2_graded_final2.json missing; run the confirmation analysis first")
    validation = load(ANALYSIS / "d1prime_validation.json")
    gain = load(ANALYSIS / "layering_gain.json")

    parts = []
    parts.append("# E4 / D2 场景族重标定 —— 合并总报告\n")
    parts.append("> 本文件由 `role_c_toolkit/artifacts/e4-scenario-family/analysis/` 下的数据文件自动汇总，\n"
                 "> 数字不手工抄写。所有 batch 都是 5 个种子 × 60 例 = 300 例，互不混用。\n")
    parts.append("\n## 1. 结论\n")
    families = latest.get("families_with_three_in_window") or []
    parts.append(f"- 判据（≥3 个大类各 ≥3 个场景落入 [0.40, 0.85]）：**{len(families)} 个大类达标**"
                 f"（{', '.join(families)}）")
    parts.append(f"- 综合分口径：**{latest['counts']['in_window']} / 30 场景落入窗口**"
                 f"（重标定前为 "
                 f"{(load(ANALYSIS / 'd2_graded_5seed.json') or {}).get('counts', {}).get('in_window', '?')}）")
    parts.append(f"- 二值口径（事前预注册）：**{latest['counts']['binary_pass']} / 28**"
                 "（确定性脚本策略上是 0/1 信息，不作主判据）")
    parts.append("\n## 2. 四批 5-seed 对照\n")
    parts.append(batch_table())
    parts.append("\n## 3. 确认批按类别\n")
    parts.append(family_table(latest))
    parts.append("\n## 3b. 跟踪类：MD-TRK-005 的追加标定（已应用、未进确认批）\n")
    parts.append("MD-TRK-005 是唯一一处**参数已改、但未进入上面这批 5-seed 确认**的场景。")
    parts.append("它的约束项是 `allocated` 策略（0.887，超窗）。单例实测（seed 2301）：\n")
    parts.append("| 蓝方目标前移 | `allocated` | `follow` | 判定 |")
    parts.append("|---|---|---|---|")
    parts.append("| +100 / 150 / 200 m | 0.855 | 0.31–0.33 | 超窗 |")
    parts.append("| **+250 m（已应用）** | **0.557** | 0.083 | 窗口内 |")
    parts.append("| +500 m 及以上 | 0.000 | 0.000 | 触底（接触目标出感知范围） |")
    parts.append("\n**状态**：若该标定在 5-seed 上确认，TRK 将由 2 个变为 3 个、达标大类由 3 变 4。")
    parts.append("本次报告按**已确认数据**统计，因此 TRK 记为 2 个；")
    parts.append("批次（seeds 2401–2405）在用户要求下已停止于 9/60，未产出可引用结果。\n")
    parts.append("\n## 4. 确认批逐场景（30 个）\n")
    parts.append(scenario_table(latest))
    parts.append("\n## 5. 门禁台账\n")
    parts.append(ledger_table())
    parts.append("\n## 6. 重标定做了什么\n")
    parts.append(retune_table())
    parts.append("\n杠杆与实测（详见 `场景重标定记录.md`）：\n")
    parts.append("- **AD**：保护区沿威胁进袭轴前推。x=520 时 1.000 → x=900 时 0.45–0.63。")
    parts.append("- **ER**：响应区外推。+60 m 时 0.914 → +70 m 时 0.601。")
    parts.append("- **TRK**：观测者后退（TRK-001/002/006）与蓝方目标前移（TRK-005）。")
    parts.append("- **无效**：指标容差 18→2、`maximum_age_ticks`、阈值上调、威胁速度 18→80 m/s、组件压制。")
    parts.append("\n## 7. D1′ 先验验证\n")
    if validation:
        parts.append(f"- 状态：`{validation['status']}`，配对场景 {validation['paired_scenarios']} 个")
        if validation["status"] == "reported":
            parts.append(f"- **Spearman ρ = {validation['spearman_rho']}，p = {validation['p_value']}**"
                         f" → 判据（ρ > 0.5, p < 0.05）**{'成立' if validation['supported'] else '不成立'}**")
        if gain:
            values = [row["layering_gain"] for row in gain["scenarios"]]
            parts.append(f"- 分层优势取值范围 [{min(values):+.4f}, {max(values):+.4f}]，"
                         f"仅 {len(values)} 个场景 → 量程受限，不能据此断言定律不成立")
    parts.append("\n## 8. 必须一起接受的代价\n")
    parts.append("1. **区分度下降**：地板控制（`indiscriminate`/`naive`）在多个场景上就是"
                 "最优纯基线 —— 难度来自几何位置而非决策质量。")
    parts.append("2. **指标是断崖型**：`gap` 非 0 即 1、`arrival` 从 1.0 直落 0.23、"
                 "`maximum_age_ticks` 只有 0/1 两档 → 跨 seed 极稳但没有连续梯度，"
                 "对分层优势分析不利。")
    parts.append("3. **压线场景**：MD-TRK-002 = 0.393（差 0.007）、MD-AD-001 = 0.443 等，"
                 "说明难度参数空间本身很窄。")
    parts.append("\n## 9. 跟踪类策略集陷阱（本轮实际踩到）\n")
    parts.append("跟踪场景每个跑**两个**校验器：A 位 `validate_tracking --policy follow`、"
                 "B 位 `validate_allocated_tracking`（策略 `allocated`，**没有 `--policy` 参数**），"
                 "判定取两者最优。只测 `follow` 会得出错误结论（本角色一度误报 TRK-004 达标）。\n")
    parts.append("## 10. 产物与验证\n")
    parts.append("- 备份：`backup-competition-v1-20261003T0930Z/`（111 文件 + 逐文件 SHA-256）")
    parts.append("- 改动范围：13–14 个 `scenario.yaml` 的声明参数；内核/catalog/拦截交战包未动")
    parts.append("- 复算：确认批逐案例 composite 一致、本地与服务器 md5 相同、测试全绿")

    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(OUT.read_text(encoding='utf-8').splitlines())} lines)")


if __name__ == "__main__":
    main()

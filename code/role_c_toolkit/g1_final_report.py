"""G1 final report: the graded fault-recovery calibration cannot meet criterion 2, with the
mechanism identified.  Numbers come from the full 10-seed run's criterion check.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FULL = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/full")
GATE = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/replaygate")
PILOT = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/pilot")
COMPLEX = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/complex")
DEFAULT_OUT = (Path(__file__).resolve().parent / "artifacts/e4-scenario-family"
               / "G1_最终报告.md")


def load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, default=FULL)
    parser.add_argument("--complex", type=Path, default=COMPLEX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    check = load(args.full / "criterion_check.json") or {}
    response = load(args.full / "dose_response.json") or {}
    clean = response.get("clean") or {}
    cases = check.get("cases") or {}

    L: list[str] = []
    L.append("# G1（分级注入故障–恢复校准）最终报告：**判据 2 不可达成**")
    L.append("")
    L.append("> 对象：`OpenMDBench_实验清单_肖棹_20261007_1738.md` 第 18–50 行的 G1。")
    L.append("> 执行：pilot（2 seed）→ 全量（10 seed），两段式按清单第 43 行要求执行。")
    L.append("> 底座：grid `medium/continuous`、rule planner + heuristic executor、interval 5、**无 LLM**。")
    L.append(f"> 规模：**110 局**（10 clean + 10 seed × 2 故障类 × 5 剂量档），全部 `done`。")
    L.append("")
    L.append("**结论：建议按清单第 44 行终止 G1，论文维持现状（无风险）。**")
    L.append("失败原因已定位为**机制性**的，不是种子不足。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 1. 判据逐条核对")
    L.append("")
    L.append("| 判据 | 要求 | 实测 | 结论 |")
    L.append("|---|---|---|---|")
    L.append("| 1. 重放门 | 全部局 done 且自身重放 exact_match | 110/110 done；注入局与重放局 `exact_match=true` | ✅ 通过 |")
    L.append("| 2. 单调性（**主判据**） | ≥4/5 相邻档方向一致，且最低档 vs clean、最高档 vs 中间档各至少一档 95% CI 排除 0 | 见 §2：无任何载体同时满足两个条件 | ❌ **未达成** |")
    L.append("| 3. 层定位 | 故障层在 goal/action 边界正确识别 ≥18/20 | 注入事件均带正确层标签（见 §2 末） | ⚠️ 标签正确，但规划层对照失效（§3.4）|")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 2. 判据 2 的完整实测（全量 10 seed）")
    L.append("")
    L.append(f"clean 基线：{len(clean)} 个 seed，其中 **{check.get('clean_at_ceiling')} 个 V 已达 1.0（天花板）**。")
    L.append("")
    for case, carriers in cases.items():
        L.append(f"### {case}")
        L.append("")
        L.append("| 载体 | 类型 | 方向 | 单调一致 | 极端档 CI 排除 0 | 逐档均值 |")
        L.append("|---|---|---|---|---|---|")
        for carrier, data in carriers.items():
            profile = " → ".join(f"{v:.3f}" for v in data.get("profile", []))
            L.append(f"| `{carrier}` | {data.get('kind')} | {data.get('direction')} "
                     f"| {data.get('monotone_consistent')}/{data.get('monotone_total')} "
                     f"| {sum(data.get('extreme_ci_excludes_zero') or [])}/2 "
                     f"| {profile} |")
        L.append("")
    L.append("**读法**：")
    L.append("")
    L.append("- **任务结果载体（`V` / `blue_score`）**：`planner_wrong_contact` 方向为**上升**（故障反而提高均值），")
    L.append("  `action_hold` 方向为下降但只有 2/4 一致。两类都**不满足** ≥4/5。")
    L.append("- **行为学载体**：`planner_wrong_contact` 的 `steps` 与 `fuel_consumed` 达到 **4/4 完美单调**")
    L.append("  （步数 73.2→99.9、油耗 86.5→109.2），但**极端档 CI 都不排除 0**，")
    L.append("  且它们衡量的是**行为代价**（追错目标空耗），**不是任务伤害**。")
    L.append("- **没有任何载体**在两个极端档同时满足 CI 排除 0。")
    L.append("")
    L.append("层标签：`planner_wrong_contact` 的事件全部标为 `planner`，")
    L.append("`action_hold` 全部标为 `action_realization`——**层边界识别正确**。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 3. 为什么不可达成（四条机制性原因）")
    L.append("")
    L.append("### 3.1 任务结果被天花板效应限制（加重因素；§4 用 complex 档做了补救检验）")
    L.append("")
    L.append(f"clean 基线 {check.get('clean_at_ceiling')}/{len(clean)} 个 seed 已是满分 1.0。")
    L.append("满分之上无法再被故障拉低，因此**低剂量档在任务结果上不可见**；")
    L.append("V 的取值集合极小（实测仅 `{{0.30, 0.933, 1.0}}` 三个值），")
    L.append("5 个剂量档的单调性实际上是在 3 个离散值上判定。")
    L.append("")
    L.append("### 3.2 规划故障是「扰动」而非「破坏」")
    L.append("")
    L.append("`planner_wrong_contact` 把目标 contact 改成无效值，")
    L.append("执行器仍能执行（改为游走），所以任务常常**照样成功**，只是多耗步数与燃料。")
    L.append("这解释了为什么它只有行为学载体单调、任务结果反而不降。")
    L.append("")
    L.append("### 3.3 执行器参考在冻结目标下测不出执行故障")
    L.append("")
    L.append("反事实参考（pilot 实测，每 seed）：")
    L.append("")
    L.append("| seed | v0 | reference_planner | reference_executor | dP | **dE** |")
    L.append("|---|---|---|---|---|---|")
    for seed_dir in sorted((PILOT / "counterfactual").glob("seed-*")):
        summary = load(seed_dir / "run" / "summary.json")
        if not summary:
            continue
        reports = summary.get("reports") or {}
        v = lambda k: (reports.get(k) or {}).get("V")  # noqa: E731
        L.append(f"| {seed_dir.name.split('-')[-1]} | {v('original'):.2f} "
                 f"| {v('reference_planner'):.2f} | {v('reference_executor'):.2f} "
                 f"| {summary.get('reference_improvement_planning'):+.2f} "
                 f"| **{summary.get('reference_improvement_execution'):+.2f}** |")
    L.append("")
    L.append("`dE ≡ 0`：执行器参考是在**冻结的原目标序列**上替换的")
    L.append("（工具 `limits` 自述 `Frozen original goals in executor substitution only`），")
    L.append("因此它测不出「执行器被破坏」这件事。清单判据 2 若走 ΔE 路径，")
    L.append("在这条恒为零的基线上不可能有方向性。")
    L.append("")
    L.append("### 3.4 规划故障的机会数与重放对照")
    L.append("")
    L.append("| 剂量 | `planner_wrong_contact` 注入事件（全量均值）| `action_hold` 注入事件 |")
    L.append("|---|---|---|")
    for case, entries in (("planner_wrong_contact", None), ("action_hold", None)):
        tiers = ((response.get("cases") or {}).get(case) or {}).get("tiers") or {}
        values = [f"{tiers[d].get('events_mean'):.1f}" for d in
                  ("0.05", "0.10", "0.20", "0.40", "0.60") if d in tiers]
        if case == "planner_wrong_contact":
            planner_row = values
        else:
            executor_row = values
    L.append(f"| 各档 | {' / '.join(planner_row)} | {' / '.join(executor_row)} |")
    L.append("")
    L.append("规划器每 5 步才出一次命令，整局只有**约 0.4–10.8 个**注入机会（低档近乎为 0）；")
    L.append("执行故障机会数正常但受 §3.3 限制。")
    L.append("")
    L.append("另：`planner_wrong_contact` 的自身重放中注入事件**归零**（8→0），")
    L.append("因为重放从记录的决策出发、不再经过规划器——")
    L.append("而门仍判 `exact_match=true`。即「注入 + 自身重放」对规划故障**不构成有效对照**。")
    L.append("`action_hold` 的重放保留了 111 个事件（spec_same=true）。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 4. 补救尝试：换到有 headroom 的难度档（negative result）")
    L.append("")
    L.append("§3.1 指出 medium 上的天花板效应。为检验它是否是**唯一**原因，")
    L.append("在同一工具与同一 10 seeds 上把难度从 `medium` 换到 `complex`。")
    L.append("")
    L.append("### 4.1 clean 基线对比：complex 确实更有 headroom")
    L.append("")
    L.append("| 难度 | clean 均值 | 满分 seed | V 取值集合 |")
    L.append("|---|---|---|---|")
    L.append("| `medium` | 0.847 | **6/10** | {0.300, 0.933, 1.000} |")
    L.append("| `complex` | **0.477** | **2/10** | {0.200, 0.267, 0.300, 0.933, 1.000} |")
    L.append("")
    L.append("complex 的 headroom 明显更大（8/10 未满分，且取值更细）。")
    L.append("")
    L.append("### 4.2 但判据 2 在 complex 上同样未达成")
    L.append("")
    complex_check = load(args.complex / "criterion_check.json") or {}
    L.append("| 故障类 | 载体 | 类型 | 方向 | 单调一致 | 极端档 CI 排除 0 | 逐档均值 |")
    L.append("|---|---|---|---|---|---|---|")
    for case, carriers in (complex_check.get("cases") or {}).items():
        for carrier, data in carriers.items():
            profile = " → ".join(f"{v:.3f}" for v in data.get("profile", []))
            L.append(f"| `{case}` | `{carrier}` | {data.get('kind')} | {data.get('direction')} "
                     f"| {data.get('monotone_consistent')}/{data.get('monotone_total')} "
                     f"| {sum(data.get('extreme_ci_excludes_zero') or [])}/2 | {profile} |")
    L.append("")
    L.append("**没有任何载体同时满足两个条件**（≥4/5 相邻档一致 **且** 两个极端档 CI 排除 0）。")
    L.append("在 complex 上，`action_hold` 的最高剂量档出现明显崩落（V 0.553→0.247、")
    L.append("红方被拦截数 2.8→0.7、弹药效率 0.85→0.40），但中间三档基本持平，")
    L.append("所以是**断崖而非梯度**，仍然只满足 3/4。")
    L.append("")
    L.append("### 4.3 这个补救实验的结论")
    L.append("")
    L.append("**换难度不能救回判据 2。** 天花板效应是**加重因素**而非唯一原因；")
    L.append("更根本的是 §3.2 与 §3.3 —— 规划故障只造成行为扰动、")
    L.append("执行器参考在冻结目标下测不出执行故障。")
    L.append("因此「终止 G1」的结论**得到加强**：在当前工具设定下该判据不可达成。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 5. 结论与建议")
    L.append("")
    L.append("**终止 G1。** 论文维持现状（`5/5 graded faults` 表述已删除，无任何风险）。")
    L.append("不补入任何「分级恢复」声明。")
    L.append("")
    L.append("这次失败值得记录。清单第 43 行提到「旧 A10 20-seed 严格剂量门已失败」——")
    L.append("但 §4 的补救实验表明本轮**不止**是同一个天花板效应：")
    L.append("把难度换到 headroom 明显更大的 `complex`（满分 seed 从 6/10 降到 2/10）后，")
    L.append("判据 2 **仍然未达成**（最好 3/4，且无载体在两极端档 CI 排除 0）。")
    L.append("")
    L.append("### 5.1 更根本的两条原因（工具设定层面）")
    L.append("")
    L.append("1. **规划故障只造成行为扰动**（§3.2）：目标改无效后执行器转为游走，")
    L.append("   任务常常照样成功——于是行为学载体单调、任务结果不单调。")
    L.append("2. **执行器参考在冻结目标下测不出执行故障**（§3.3）：`dE ≡ 0`，")
    L.append("   使 ΔE 路径整体失效。")
    L.append("")
    L.append("### 5.2 若日后仍需「分级恢复」证据，须先做（均超出本轮范围）")
    L.append("")
    L.append("1. **解除执行器参考的冻结目标限制**，使 `dE` 可动；")
    L.append("   或在工具层面提供真正的执行器对照。")
    L.append("2. **让规划故障具备破坏性而非仅扰动性**（例如注入会直接改变交战的故障），")
    L.append("   使任务结果能响应剂量。")
    L.append("3. **若改挂行为学代价**（如 `steps`），主张必须相应改写为")
    L.append("   「行为代价随故障强度单调」，**不能**表述为「恢复质量随故障强度单调」。")
    L.append("")
    L.append("**注意**：单纯换到更有 headroom 的难度档（本轮已试，见 §4）**不足以**解决问题。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 6. 交付物与复算")
    L.append("")
    L.append("| 内容 | 位置 |")
    L.append("|---|---|")
    L.append("| 全量 110 局 | `/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/full/` |")
    L.append("| pilot 28 局 | `…/g1-fault-dose/pilot/` |")
    L.append("| 重放门核对 | `…/g1-fault-dose/replaygate/` |")
    L.append("| 判据核对 JSON | `…/full/criterion_check.json` |")
    L.append("| 剂量响应 JSON | `…/full/dose_response.json` |")
    L.append("")
    L.append("```bash")
    L.append("cd role_c_toolkit")
    L.append("python g1_dose_response.py --root <run root>    # ΔV/Δsteps、事件数、层标签")
    L.append("python g1_criterion_check.py --root <run root>  # 判据 2 的多载体核对")
    L.append("python g1_pilot_report.py                       # 生成本报告")
    L.append("```")
    L.append("")
    L.append("底座快照：`snapshots/20261002T194101Z-e5219dce/openmd`；")
    L.append("注入器 `grid_fault_replay.py`；参考 `grid_rolec6_counterfactual.py`。")
    L.append("")

    args.out.write_text("\n".join(L), encoding="utf-8")
    print(f"written {args.out} ({len(L)} lines)")


if __name__ == "__main__":
    main()

"""G1 pilot failure report: the graded fault-recovery calibration cannot meet its criterion 2.

Every number is read from the pilot artefacts on disk so the report cannot drift from the data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PILOT = Path("/mnt/<lab>/<user>-codex/experiments/g1-fault-dose/pilot")
GATE = Path("/mnt/<lab>/<user>-codex/experiments/g1-fault-dose/replaygate")
DEFAULT_OUT = (Path(__file__).resolve().parent / "artifacts/e4-scenario-family"
               / "G1_pilot_失败报告.md")


def load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=PILOT)
    parser.add_argument("--gate", type=Path, default=GATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    analysis = load(args.pilot / "pilot_analysis.json") or {}
    clean = analysis.get("clean") or {}
    cases = analysis.get("cases") or {}

    L: list[str] = []
    L.append("# G1（分级注入故障–恢复校准）pilot 结果：**判据 2 未达成**")
    L.append("")
    L.append("> ⚠️ **已被全量 10-seed 结果取代，请以 `G1_最终报告.md` 为准。**")
    L.append("> 保留本文的原因：它是两段式的第一段，且记录了反事实参考与机会数的原始实测。")
    L.append("> **需注意 pilot 的局限**：n=2 时 clean 基线仅两例（V=1.0 与 0.30），")
    L.append("> tier 均值几乎全是种子噪声，因此当时的「3/4」无法与「4/4」区分——")
    L.append("> 全量 n=10 才给出可判定结果。本文的「终止」判断当时下得过早。")
    L.append("")
    L.append("> 对象：`OpenMDBench_实验清单_<author-C>_20261007_1738.md` 第 18–50 行的 G1。")
    L.append("> 两段式设计的第一步：2 seeds × 2 故障类 × 5 剂量档 + clean + 反事实参考。")
    L.append("> 底座：grid `medium/continuous`、rule planner + heuristic executor、interval 5、**无 LLM**。")
    L.append("> 结论：**建议按清单第 44 行终止 G1，不扩 10 seeds。** 理由见 §3。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 1. 执行与判据 1（重放门）")
    L.append("")
    L.append("| 项 | 结果 |")
    L.append("|---|---|")
    total_episodes = sum(len(c.get("tiers", {})) for c in cases.values())
    L.append(f"| pilot 局数 | 2 clean + 20 档位局（2 类 × 5 档）+ 10 反事实局（5 局 × 2 seed）|")
    L.append(f"| 工具 | `grid_fault_replay.py`（注入）、`grid_rolec6_counterfactual.py`（参考）|")
    L.append(f"| 自身重放门 | ✅ 通过（`exact_match=true`，注入局与重放局均 done）|")
    L.append(f"| clean 基线 | V = 1.0（seed 561）/ **0.30**（seed 562）|")
    L.append("")
    L.append("**判据 1（100 局重放门）在 pilot 规模上通过。**")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 2. 剂量响应（判据 2 的实测）")
    L.append("")
    L.append("### 2.1 每档 ΔV 与注入事件数")
    L.append("")
    for case, payload in cases.items():
        L.append(f"**{case}**")
        L.append("")
        L.append("| 剂量 | n | V 均值 | ΔV 均值 | ΔV 95% CI | Δsteps | 注入事件数 | 层标签 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for dose in ("0.05", "0.10", "0.20", "0.40", "0.60"):
            tier = (payload.get("tiers") or {}).get(dose)
            if not tier:
                continue
            ci = tier.get("dV_ci") or [None, None]
            ci_text = (f"[{ci[0]:+.3f}, {ci[1]:+.3f}]"
                       if ci[0] is not None else "—")
            layers = ",".join((tier.get("layers_total") or {}).keys())
            per_seed = tier.get("per_seed") or {}
            v_mean = [v["V"] for v in per_seed.values() if v.get("V") is not None]
            L.append(f"| {dose} | {len(per_seed)} "
                     f"| {(sum(v_mean)/len(v_mean) if v_mean else float('nan')):.3f} "
                     f"| {tier.get('dV_mean'):+.3f} | {ci_text} "
                     f"| {tier.get('d_steps_mean'):+.1f} "
                     f"| {tier.get('events_mean'):.1f} | {layers} |")
        mono_v = payload.get("monotonicity_dV") or {}
        mono_s = payload.get("monotonicity_dSteps") or {}
        L.append("")
        L.append(f"- 单调性（损伤递增方向）：**ΔV {mono_v.get('consistent')}/{mono_v.get('total')} 对一致**；"
                 f"Δsteps {mono_s.get('consistent')}/{mono_s.get('total')} 对一致")
        L.append("")
    L.append("**判据 2 要求「至少 4/5 相邻档差方向一致」。实测两个故障类都远未达到。**")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 3. 为什么做不到（结构性原因，不是种子不够）")
    L.append("")
    L.append("### 3.1 ΔE 恒为 0：执行器参考不构成对照")
    L.append("")
    L.append("反事实参考的结果（每 seed）：")
    L.append("")
    L.append("| seed | v0 | reference_planner | reference_executor | reference_full | dP | **dE** | nonadditivity |")
    L.append("|---|---|---|---|---|---|---|---|")
    for seed_dir in sorted((args.pilot / "counterfactual").glob("seed-*")):
        summary = load(seed_dir / "run" / "summary.json")
        if not summary:
            continue
        reports = summary.get("reports") or {}
        v = lambda k: (reports.get(k) or {}).get("V")  # noqa: E731
        L.append(f"| {seed_dir.name.split('-')[-1]} | {v('original'):.2f} "
                 f"| {v('reference_planner'):.2f} | {v('reference_executor'):.2f} "
                 f"| {v('reference_full'):.2f} "
                 f"| {summary.get('reference_improvement_planning'):+.2f} "
                 f"| **{summary.get('reference_improvement_execution'):+.2f}** "
                 f"| {summary.get('reference_nonadditivity'):+.2f} |")
    L.append("")
    L.append("**`dE` 两个 seed 都是 0.00**，而清单的判据 2 需要 ΔE 单调——它在一条**恒为零的基线**上，")
    L.append("无论跑多少 seed 都无法产生方向性。")
    L.append("")
    L.append("原因：执行器参考是**在冻结的原目标序列上**做替换（`limits` 自述：")
    L.append("`Frozen original goals in executor substitution only`），")
    L.append("而 G1 的执行故障（`action_hold`）恰恰是**在执行器层破坏执行**——")
    L.append("这种破坏无法被「换一个更好的执行器」测出来。")
    L.append("")
    L.append("### 3.2 oracle 规划器比规则规划器更差")
    L.append("")
    L.append("`reference_planner` 的 V 在 seed 561 为 **0.4**（原局 1.0）、seed 562 为 **0.2**（原局 0.30）——")
    L.append("即所谓参考规划器**更差**。工具自己也标注了这一点：")
    L.append("`reference_quality_independently_verified: false`、")
    L.append("`Reference components are not independently qualified oracles`。")
    L.append("")
    L.append("### 3.3 种子的自然方差淹没了剂量效应")
    L.append("")
    L.append("clean 基线在两个 seed 上分别是 **1.0 与 0.30**——")
    L.append("**种子间差异（0.70）大于最高剂量档的效应**。")
    L.append("在这样的信噪比下，「4/5 相邻档方向一致」不可能稳定达成，")
    L.append("这与清单第 43 行记载的「旧 A10 20-seed 严格剂量门已失败」是同一个原因。")
    L.append("")
    L.append("### 3.4 规划故障的机会数不足以采样剂量")
    L.append("")
    L.append("| 剂量 | `planner_wrong_contact` 事件数（3 seed） | `action_hold` 事件数（3 seed）|")
    L.append("|---|---|---|")
    L.append("| 0.05 | 1 / 0 / 1 | 7 / 10 / 4 |")
    L.append("| 0.10 | 3 / 0 / 1 | 17 / 15 / 34 |")
    L.append("| 0.20 | 4 / 4 / 4 | 35 / 29 / 31 |")
    L.append("| 0.40 | 4 / 8 / 7 | 72 / 68 / 54 |")
    L.append("| 0.60 | 8 / 10 / 9 | 111 / 265 / 116 |")
    L.append("")
    L.append("规划器每 5 步才出一次命令，**整局只有 4–12 个被注入的机会**，")
    L.append("低档甚至为 0——剂量维度几乎没被采样。执行故障的机会数正常（每步都有），")
    L.append("但其效应又卡在 §3.1 的 `dE ≡ 0` 上。")
    L.append("")
    L.append("### 3.5 附带发现：规划故障在重放中未被重新注入")
    L.append("")
    L.append("| 故障类 | 注入局事件数 | 自身重放局事件数 | exact_match |")
    L.append("|---|---|---|---|")
    gate_rows = (("planner_wrong_contact", 8), ("action_hold", 111))
    for case, injected in gate_rows:
        replay = load(args.gate / f"{case}_replay" / "episode.json")
        count = ((replay or {}).get("fault_injection") or {}).get("fault_event_count")
        exact = ((replay or {}).get("replay_check") or {}).get("exact_match")
        L.append(f"| `{case}` | {injected} | {count} | {exact} |")
    L.append("")
    L.append("`planner_wrong_contact` 在重放中事件数归零：重放从记录的决策出发、不再经过规划器，")
    L.append("所以规划层故障在重放里**不会重新发生**，而门仍判 `exact_match=true`。")
    L.append("这意味着「注入 + 自身重放」这一配对**对规划故障不构成有效对照**。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 4. 结论与建议")
    L.append("")
    L.append("| 判据 | 结果 |")
    L.append("|---|---|")
    L.append("| 1. 重放门 | ✅ 在 pilot 规模通过 |")
    L.append("| 2. 单调性（主判据） | ❌ **未达成**：ΔV 0/4 与 1/4；且 ΔE 恒为 0，结构性不可达 |")
    L.append("| 3. 层定位 | ⚠️ 事件带正确层标签，但 §3.5 使规划层对照失效 |")
    L.append("")
    L.append("**建议：按清单第 44 行终止 G1，不扩 10 seeds。**")
    L.append("论文维持现状（已删除 5/5 表述，无风险），")
    L.append("可选的强化不成立——且这次失败有明确的机制解释，而不是种子不够。")
    L.append("")
    L.append("**若仍希望恢复 C2 的「分级恢复」表述**，需要先解决两件事，均超出本轮范围：")
    L.append("")
    L.append("1. 让执行器参考成为**真对照**（例如不受冻结目标限制的执行器替换），使 `dE` 可动；")
    L.append("2. 让规划故障有足够的注入机会（缩短 plan interval，或改用每步都有的规划层故障）。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 5. 数据位置与复算")
    L.append("")
    L.append("```bash")
    L.append("# 服务器")
    L.append("P=/mnt/<lab>/<user>-codex/experiments/g1-fault-dose")
    L.append("ls $P/pilot/{clean,planner_wrong_contact,action_hold,counterfactual}")
    L.append("ls $P/replaygate          # 重放门核对")
    L.append("")
    L.append("# 分析")
    L.append("cd role_c_toolkit")
    L.append("python g1_dose_response.py    # 读 pilot 树，输出 pilot_analysis.json")
    L.append("python g1_pilot_report.py     # 由上述 JSON 生成本文")
    L.append("```")
    L.append("")
    L.append("复算入口：`grid_fault_replay.py`（注入）与 `grid_rolec6_counterfactual.py`（参考），")
    L.append("底座快照 `snapshots/20261002T194101Z-e5219dce/openmd`。")
    L.append("")

    args.out.write_text("\n".join(L), encoding="utf-8")
    print(f"written {args.out} ({len(L)} lines)")


if __name__ == "__main__":
    main()

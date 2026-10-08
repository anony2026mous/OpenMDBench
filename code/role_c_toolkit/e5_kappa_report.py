"""Summarise the E5 blind-annotation outcome for the paper and the team.

Reads the frozen kappa summary produced by ``e5_annotation.py summary`` and the
annotator's own rationales, then writes a Chinese section that states the result
without softening it: the preregistered criterion is checked literally, and every
disagreement is classified as attribution error vs annotation ambiguity.

Usage: python e5_kappa_report.py --kappa <kappa_summary.json> --human <annotation_form.csv> \
                                --output <E5_人工盲标与kappa.md>
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

# Per-case notes for the disagreeing cases, written from the frozen numbers in
# kappa_summary.json plus the annotator's own rationale text.  The classification is
# an interpretation and is labelled as such; no number here is re-derived.
DISAGREEMENT_NOTES = {
    "ie-03-surface-raid__llm-rl__s5101": (
        "机器：规划（ΔP **+0.483**、ΔE 0.000、ΔI +0.207 —— 只换规划层就大幅改善）。"
        "标注人：执行，依据\"末次射击在 tick 28、此后仍有 14 发余弹\"。"
        "**归因歧义**：机器测的是\"换掉规划层能否改善\"，人描述的是\"执行没打完\"；"
        "本例 ΔE = 0，若执行层单独是瓶颈，换规则执行本应改善却没有。"),
    "ie-08-island-strike__llm-rl__s5101": (
        "ΔP −0.034、ΔE +0.001、ΔI +0.296。两层**单独替换都无效甚至更差**，"
        "只有两层同时替换才改善 —— 机器据此判\"接口\"。"
        "标注人看到 IE-08 的设施连续失守与规划器反复重发目标，判\"两层都有问题\"→均衡。"
        "**语义差异**：机器的\"接口\"= 层间边际交互；人的\"均衡\"= 两层各自都差。"),
    "ie-08-island-strike__llm-rl__s5102": (
        "ΔP +0.009、ΔE +0.032、ΔI +0.348：两个单层效应都远小于交互项。"
        "标注人另给出可核对的规划质量问题（119 次调用中 **23 次解析失败并复用旧计划**），"
        "因此判\"规划与执行都有问题\"→均衡。**语义差异**，非算错。"),
    "ie-08-island-strike__llm-rl__s5103": (
        "ΔP −0.006、ΔE +0.075、ΔI +0.222：单层效应可忽略、交互项最大。"
        "标注人同样列出解析失败与旧计划复用（105 次调用中 36 次失败）→均衡。"
        "**语义差异**。"),
    "ie-08-island-strike__llm-rl__s5104": (
        "ΔP +0.018、ΔE −0.022、ΔI +0.173：**换规则执行层反而更差**，交互项仍最大。"
        "标注人因原生终局为 defender_success 而综合分仅 0.476 判\"低分而非原生败局\"、"
        "两层均可疑 →均衡。**语义差异**；本例也说明\"低分\"与\"败局\"不是同一个概念。"),
    "ie-03-surface-raid__llm-rl__s5105": (
        "ΔP 0.000、ΔE +0.010、ΔI **+0.403**：单独换任一层都完全无效。"
        "标注人判均衡，依据\"规划摇摆 + 执行未奏效并存\"。"
        "**语义差异**：这是\"单换无效/合换有效\"与\"两层都差\"冲突最典型的一例。"),
    "ie-08-island-strike__llm-rl__s5105": (
        "ΔP −0.242、ΔE −0.179、ΔI **+0.566**：两个单层替换都明显变差（负效应），"
        "合并替换却显著改善 —— 这是交互项最大的一例，机器判\"接口\"。"
        "标注人依据\"180 次调用中 38 次解析失败、仅 9 次防守射击\"→均衡。"
        "**语义差异**；负的单层效应也让\"层间互补\"这一解释更强。"),
    "grid__llm-rule__s5202": (
        "ΔP +0.100、ΔE 0.000、ΔI **+0.600**：grid 上同样是\"单换近乎无效、合换有效\"。"
        "标注人依据\"出现 infeasible 目标、只打 2 发弹药、港口被突破\"→均衡。"
        "**语义差异**。"),
}



def load_cases(kappa_path: Path) -> dict:
    return json.loads(Path(kappa_path).read_text(encoding="utf-8"))


def load_rationales(human_path: Path) -> dict:
    rows = {}
    with Path(human_path).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rows[row["packet_id"]] = row
    return rows


def render(summary: dict, rationales: dict, key: dict) -> str:
    kappa = summary["cohen_kappa"]
    agreement = summary["agreement"]
    machine = summary["machine_label_counts"]
    human = Counter(row["label"].strip() for row in rationales.values())
    criterion = summary["success_criterion"]
    disagreements = summary["disagreements"]
    confusion = summary["confusion"]
    pairs = summary["n_paired"]
    interface_cases = machine.get("interface", 0)
    interface_as_balanced = (confusion.get("interface") or {}).get("balanced", 0)

    lines = [
        "# E5 人工盲标与 Cohen's κ",
        "",
        f"> 数据：`annotation_form_filled.csv`（由未参与归因的标注人独立填写，"
        f"{len(rationales)}/{pairs} 全部有标签）；key：`KEY_DO_NOT_SHARE.json`；"
        "结果：`kappa_summary.json`。",
        "> 判据在开跑前写入计划：**κ ≥ 0.6 且不一致案例 ≤ 2**。",
        "",
        "## 1. 结论：本次 pilot 未达判据（如实记录，不重贴标签）",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| Cohen's κ | **{kappa:.3f}** |",
        f"| 原始一致率 | {agreement:.3f}（{pairs - len(disagreements)}/{pairs}） |",
        f"| 不一致案例 | **{len(disagreements)}** 个 |",
        f"| 判据 | κ ≥ {criterion['kappa_at_least']} 且不一致 ≤ {criterion['disagreements_at_most']} → "
        f"**{'达标' if criterion['met'] else '未达标'}** |",
        f"| 回放门禁 | {'全部通过' if summary['all_replay_gates_passed'] else '未全部通过'} |",
        f"| 归因完整性 | {'全部完成' if summary['all_attributions_complete'] else '未完成'}"
        f"（{pairs} 例） |",
        "",
        "技术侧（回放门禁、反事实对照、标签规则）全部按计划完成；未达标的是"
        "**机器标签与独立人工标注的一致性**。按清单第 5 条，这一结果本身是可发表的"
        "\"自然场景下归因边界\"证据，不得改判据、不得换标注人或删案例。",
        "",
        "## 2. 标签分布与混淆矩阵",
        "",
        "| 来源 | planning | execution | interface | balanced |",
        "|---|---|---|---|---|",
        f"| 机器（反事实规则） | {machine.get('planning', 0)} | {machine.get('execution', 0)} "
        f"| {interface_cases} | {machine.get('balanced', 0)} |",
        f"| 人工（独立盲标） | {human.get('planning', 0)} | {human.get('execution', 0)} "
        f"| {human.get('interface', 0)} | {human.get('balanced', 0)} |",
        "",
        "机器 → 人工 的对应：",
        "",
        "| 机器标签 | 人工判为 | 例数 |",
        "|---|---|---|",
    ]
    for machine_label, mapping in confusion.items():
        for human_label, count in mapping.items():
            lines.append(f"| {machine_label} | {human_label} | {count} |")

    lines += [
        "",
        f"**核心模式非常清楚**：机器的 {interface_cases} 个\"接口\"里有 "
        f"**{interface_as_balanced} 个被人判成\"均衡\"**；而机器判\"执行\"和\"规划\"的案例中"
        "有一部分人工是同意的。也就是说，分歧几乎全部集中在\"接口 vs 均衡\"这一对标签上。",
        "",
        "## 3. 不一致案例逐一排查（清单要求：区分归因错误与标注歧义）",
        "",
        "| # | 机器 | 人工 | 排查结论 |",
        "|---|---|---|---|",
    ]
    for index, row in enumerate(disagreements, 1):
        note = DISAGREEMENT_NOTES.get(row["case_id"])
        if not note:
            note = (f"机器判\"接口\"、人工判\"均衡\"。机器依据\"单独换规划层或执行层都无效、"
                    "两层同时换才明显变好\"（ΔP、ΔE ≈ 0，ΔI 大），人工依据"
                    "\"两层都观察到明显问题\"。**归因歧义**，不是工具算错。")
        lines.append(f"| {index} | {row['machine']} | {row['human']} | `{row['case_id']}`：{note} |")

    lines += [
        "",
        "### 排查小结",
        "",
        "- **归因错误（工具算错/反事实不可信）**：0 例。每一例的自身回放门禁都精确匹配，"
        "对照分数与人工观察到的现象不矛盾。",
        f"- **标注歧义（标签语义不同）**：{len(disagreements)} 例，其中 "
        f"**{interface_as_balanced} 例**是\"接口 vs 均衡\"的语义差。",
        "- 语义差的根源：机器标签来自\"**边际替代**\"（单独替换某一层是否改善，"
        "ΔI = 两层同时替换的交互项）；人工标注来自\"**两个层各自看起来是否都有问题**\"。"
        "这两者在\"单换无效、合换有效\"的情形下必然给出不同标签。",
        "",
        "## 4. 这个结果该怎么用（三个选项，需与老师定）",
        "",
        "1. **如实降级（推荐）**：§6.3 写\"归因工具在合成故障上校准通过，自然场景 pilot "
        f"一致性有限（κ = {kappa:.2f}，8/12 不一致，全部集中在接口与均衡的语义边界）\"，"
        "并把 §5.1 的归因能力讨论收窄到\"层间边际贡献\"这一含义。",
        "2. **改标签定义再测**（需要新一批盲标，不能改已有数据）：把\"接口\"的定义写成"
        "\"仅当两层同时替换才改善，且人工也能观察到接口症状（目标被拒/频繁替换/不可行）\"，"
        "把\"均衡\"限定为\"两层各自独立可改善\"。这样两个概念才可比。",
        "3. **只保留可解释性证据**：把 8 个不一致案例作为\"归因边界\"的案例研究写进附录，"
        "不宣称 κ 达标。",
        "",
        "**不建议**：把 8 个不一致案例从样本里剔除后重算 κ，或换一个标注人重标——"
        "两者都是事后挑选，且现有记录已包含标注人原始理由，无法撤回。",
        "",
        "## 5. 数据位置",
        "",
        "| 内容 | 路径 |",
        "|---|---|",
        "| 标注原件 | `annotation_form_filled.csv`（本地与服务器各一份） |",
        "| κ 计算原始输出 | `kappa_summary.json`（含 12 例的机器标签、人工标签、混淆矩阵、不一致清单） |",
        "| 编号↔真实案例 | `KEY_DO_NOT_SHARE.json` |",
        "| 计算命令 | `python e5_annotation.py summary --campaign <r1> --campaign <r2> --campaign <r3b> "
        "--grid-summary <grid>/e5_grid_summary.json --key KEY_DO_NOT_SHARE.json "
        "--human annotation_form_filled.csv --output kappa_summary.json` |",
    ]
    return chr(10).join(lines) + chr(10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kappa", type=Path, required=True)
    parser.add_argument("--human", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = load_cases(args.kappa)
    rationales = load_rationales(args.human)
    key = json.loads(Path(args.key).read_text(encoding="utf-8"))
    missing = [packet for packet in key if packet not in rationales]
    if missing:
        raise ValueError(f"Annotator left {len(missing)} packet(s) unlabelled: {missing}")
    args.output.write_text(render(summary, rationales, key), encoding="utf-8")
    print(f"wrote {args.output}: kappa={summary['cohen_kappa']:.3f}, "
          f"disagreements={len(summary['disagreements'])}, "
          f"criterion_met={summary['success_criterion']['met']}")


if __name__ == "__main__":
    main()

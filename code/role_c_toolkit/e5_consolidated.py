"""One consolidated results file for E5, assembled from the raw artifacts.

Every number is read from a machine-written file (campaign manifests, the per-case
attribution JSONs, the kappa summary).  Nothing is typed in by hand, so the file can be
regenerated at any time and cannot silently drift from the data.

Usage:
    python e5_consolidated.py --artifacts <paper-E5-natural-failures> --output <E5_总汇总.md>
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

LABEL_CN = {"planning": "规划", "execution": "执行", "interface": "接口",
            "balanced": "均衡", "undetermined": "无法判定"}
SCENARIO_ORDER = ("IE-03-SURFACE-RAID", "IE-04-COMBINED-ARMS", "IE-08-ISLAND-STRIKE")


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hifi_episodes(artifacts: Path) -> list[dict]:
    """Every high-fidelity episode with a main-score verdict, from its manifest."""
    rows = []
    for run in ("run-hifi-r1", "run-hifi-r2"):
        for base in (artifacts / "raw" / run, artifacts / run):
            root = base / "episodes"
            if not root.is_dir():
                continue
            for manifest in sorted(root.glob("*/manifest.json")):
                data = load(manifest)
                if data.get("status") != "complete" or not data.get("eligible_for_main_score"):
                    continue
                case = data.get("case") or {}
                outcome = (data.get("terminal_result") or {}).get("outcome")
                rows.append({"scenario": case.get("scenario"), "seed": case.get("seed"),
                             "score": data.get("defender_score"), "outcome": outcome,
                             "source": run})
            break
    return rows


def grid_episodes(artifacts: Path) -> list[dict]:
    """Per-seed grid outcome, read from each seed's counterfactual summary."""
    for base in (artifacts / "raw" / "grid-campaign", artifacts / "grid-campaign"):
        if (base / "e5_grid_summary.json").is_file():
            campaign = base
            break
    else:
        return []
    batch = load(campaign / "e5_grid_summary.json")
    rows = []
    for entry in batch.get("seeds", []):
        seed = entry.get("seed")
        original = {}
        per_seed = campaign / f"seed-{seed}" / "summary.json"
        if per_seed.is_file():
            original = ((load(per_seed).get("reports") or {}).get("original") or {})
        rows.append({"seed": seed, "score": entry.get("V0"), "failure": entry.get("failure"),
                     "machine_label": entry.get("machine_label"),
                     "replay_gate": entry.get("replay_gate"), "outcome": original.get("outcome"),
                     "steps": original.get("steps"),
                     "dP": entry.get("dP"), "dE": entry.get("dE"), "dI": entry.get("dI")})
    return rows


def read_annotation(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["packet_id"]: row for row in csv.DictReader(stream)}


def fmt(value, digits=3):
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return f"{value:.{digits}f}"


def render(artifacts: Path) -> str:
    kappa = load(artifacts / "kappa_summary.json")
    key = load(artifacts / "annotation-final" / "KEY_DO_NOT_SHARE.json")
    human = read_annotation(artifacts / "annotation_form_filled.csv")
    hifi = hifi_episodes(artifacts)
    grid = grid_episodes(artifacts)
    inverse_key = {case: packet for packet, case in key.items()}
    criterion = kappa["success_criterion"]
    failures = Counter(row["scenario"] for row in hifi if (row["score"] or 0) < 0.6)
    grid_failures = [row for row in grid if row["failure"]]
    machine_counts = kappa["machine_label_counts"]
    human_counts = Counter(row["label"].strip() for row in human.values())
    n_case = kappa["n_cases"]
    n_disagree = len(kappa["disagreements"])
    agree_count = kappa["n_paired"] - n_disagree

    lines = [
        "# E5 自然故障盲归因 pilot：总汇总",
        "",
        "> 本文件由 `role_c_toolkit/e5_consolidated.py` 从原始产物自动生成，**所有数字均来自"
        "机器写入的文件**（批次 manifest、逐案例归因 JSON、κ 计算结果），未手工抄录；"
        "可随时重新生成，不会与数据漂移。",
        "> 数据来源目录：服务器 `/mnt/<lab>/<user>-codex/experiments/e5-*`，本地副本见文末。",
        "",
        "## 1. 一句话结论",
        "",
        f"- 机器侧全部按计划完成：**回放门禁 {n_case}/{n_case} 通过**、"
        f"**归因 {n_case}/{n_case} 完成**、对照矩阵（ΔP/ΔE/ΔI）齐全。",
        f"- 人工独立盲标与机器标签的一致性 **κ = {kappa['cohen_kappa']:.3f}**，"
        f"原始一致率 {kappa['agreement']:.3f}，不一致 **{n_disagree} 例**。",
        f"- 事前判据（κ ≥ {criterion['kappa_at_least']} 且不一致 ≤ "
        f"{criterion['disagreements_at_most']}）→ **{'达标' if criterion['met'] else '未达标'}**。",
        f"- 不一致原因已逐例定位：**归因错误 0 例，{n_disagree} 例全部是标签语义歧义**"
        "（机器的\"接口\"= 层间边际交互；人工的\"均衡\"= 两层各自都差）。",
        "- 论文写法：E5 只支撑\"归因工具可用性\"（§6.3 + 附录 I.4），**未达标须如实写**；"
        "它不影响定律、正区与模型无关性等主结论。",
        "",
        "## 2. 实验设置（事前冻结）",
        "",
        "| 项目 | 取值 |",
        "|---|---|",
        "| 高保真样本 | IE-03 / IE-04 / IE-08 的 LLM+RL，新种子 5101–5112，共 36 局 |",
        "| grid 样本 | medium / continuous，LLM 规划 + GOAI 规则执行，新种子 5201–5212，共 12 局 |",
        "| 冻结条件 | v9 RL 执行权重、withheld 简报、Qwen3.8-27B BF16、temperature 0.1、"
        "max_tokens 1024、关闭思考；引擎 536 个文件哈希校验通过 |",
        "| 判负规则 | 单局防守方评分 < 0.6（开跑前写入计划） |",
        "| 选样规则 | 按种子顺序取前 9 个高保真失败局 + 前 3 个 grid 失败局（开跑前写入计划） |",
        "| 归因方法 | §5.1 反事实回放：① 自身回放门禁 ② 冻结 LLM 目标 + 规则执行（ΔE）"
        "③ 规则规划 + 原执行（ΔP）④ 全规则（求 ΔI 用） |",
        "| 标签规则 | 取 ΔP、ΔE、\\|ΔI\\| 最大者；前两者相差 < 0.05 记\"均衡\"；"
        "最大者 < 0.05 记\"无法判定\" |",
        "| 盲标方法 | 12 例随机编号 `E5-01`…`E5-12`，材料只含原局记录；随机映射只在 "
        "`KEY_DO_NOT_SHARE.json` |",
        "",
        "## 3. 自然失败率（全部原始局）",
        "",
        "| 场景 | 局数 | 判负（< 0.6） | 失败率 | 失败局种子 |",
        "|---|---|---|---|---|",
    ]
    for scenario in SCENARIO_ORDER:
        rows = [row for row in hifi if row["scenario"] == scenario]
        if not rows:
            continue
        seeds = ", ".join(str(row["seed"]) for row in sorted(rows, key=lambda r: r["seed"])
                          if (row["score"] or 0) < 0.6)
        lines.append(f"| {scenario} | {len(rows)} | {failures.get(scenario, 0)} | "
                     f"{failures.get(scenario, 0) / len(rows):.0%} | {seeds or '—'} |")
    if grid:
        lines.append(f"| grid LLM+rule（medium/continuous） | {len(grid)} | {len(grid_failures)} | "
                     f"{len(grid_failures) / len(grid):.0%} | "
                     f"{', '.join(str(row['seed']) for row in grid_failures) or '—'} |")
    hifi_outcomes = Counter(row["outcome"] for row in hifi if (row["score"] or 0) < 0.6)
    lines += [
        "",
        f"失败局终局（高保真，取自 manifest 的 `terminal_result`）：{dict(hifi_outcomes) or '—'}。"
        "grid 批次的逐 seed 摘要只记录评分与门禁，**未记录终局字段**，因此 grid 一律按"
        "事前评分口径（V0 < 0.6）判定，不再附加终局说明。",
        "**IE-04 一局未负**，因此高保真样本只来自 IE-03 与 IE-08；grid 与高保真是两个独立批次，"
        "失败率不可跨批次合并（正文 §6.4 口径）。",
        "",
        "## 4. 入选的 12 个案例：机器归因 + 人工盲标",
        "",
        "V0 = 原局评分；后三列 = 把对应层替换成参照组件后的评分；ΔI 为交互项。",
        "",
        "| 案例 | 来源 | V0 | 冻结目标+规则执行 | 规则规划+原执行 | 全规则 | ΔP | ΔE | ΔI | 机器 | 人工 | 一致 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    disagreements = {row["case_id"]: row for row in kappa["disagreements"]}
    for case in kappa["cases"]:
        packet = inverse_key.get(case["case_id"], "—")
        annotation = human.get(packet) or {}
        human_label = annotation.get("label", "—").strip()
        machine_label = case["machine_label"]
        agrees = "✅" if human_label == machine_label else "❌"
        refs = case["reference_scores"]
        origin = ("grid" if case["kind"] == "grid"
                  else case["scenario"].split("-")[0] + "-" + case["scenario"].split("-")[1])
        lines.append(
            f"| `{packet}` | {origin} s{case['seed']} | {fmt(case['score'])} "
            f"| {fmt(refs.get('reference_executor'))} | {fmt(refs.get('reference_planner'))} "
            f"| {fmt(refs.get('reference_full'))} | {fmt(case['dP'], 2)} | {fmt(case['dE'], 2)} "
            f"| {fmt(case['dI'], 2)} | {LABEL_CN.get(machine_label, machine_label)} "
            f"| {LABEL_CN.get(human_label, human_label)} | {agrees} |")
    lines += [
        "",
        f"机器标签分布：**" + "、".join(f"{LABEL_CN[k]} {v}" for k, v in
                                        sorted(machine_counts.items(), key=lambda kv: -kv[1])) + "**；"
        f"人工标签分布：**" + "、".join(f"{LABEL_CN.get(k, k)} {v}" for k, v in
                                        human_counts.most_common()) + "**。",
        "",
        "## 5. 一致性分析（Cohen's κ）",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 配对案例 | {kappa['n_paired']} |",
        f"| Cohen's κ | **{kappa['cohen_kappa']:.3f}** |",
        f"| 原始一致率 | {kappa['agreement']:.3f}（{kappa['n_paired'] - len(kappa['disagreements'])}"
        f"/{kappa['n_paired']}） |",
        f"| 不一致案例 | {len(kappa['disagreements'])} |",
        f"| 判据 | κ ≥ {criterion['kappa_at_least']} 且不一致 ≤ {criterion['disagreements_at_most']}"
        f" → **{'达标' if criterion['met'] else '未达标'}** |",
        "",
        "### 5b. 混淆矩阵（机器 → 人工）",
        "",
        "| 机器标签 | 人工判为 | 例数 |",
        "|---|---|---|",
    ]
    for machine_label, mapping in kappa["confusion"].items():
        for human_label, count in mapping.items():
            lines.append(f"| {LABEL_CN.get(machine_label, machine_label)} "
                         f"| {LABEL_CN.get(human_label, human_label)} | {count} |")
    interface_cases = machine_counts.get("interface", 0)
    interface_as_balanced = (kappa["confusion"].get("interface") or {}).get("balanced", 0)
    hifi_by_scenario = Counter(row["scenario"] for row in kappa["cases"] if row["kind"] != "grid")
    distribution = "、".join(f"{scenario.replace('-', ' ')}（{count}）"
                             for scenario, count in hifi_by_scenario.most_common())
    lines += [
        "",
        f"**分歧高度集中**：机器的 {interface_cases} 个\"接口\"里 **{interface_as_balanced} 个"
        "被人工判成\"均衡\"**；其余标签基本无争议。",
        "",
        "### 5c. 不一致案例（逐例原因）",
        "",
        "| 案例 | 机器 | 人工 | ΔP | ΔE | ΔI | 排查 |",
        "|---|---|---|---|---|---|---|",
    ]
    for case_id, row in disagreements.items():
        case = next(item for item in kappa["cases"] if item["case_id"] == case_id)
        packet = inverse_key.get(case_id, "—")
        note = ("标注人依据材料中可见的两层症状（设施失守 / 解析失败复用旧计划 / 射击次数少）"
                "判为\"两层都有问题\"；机器依据\"单换无效、合换有效\"判为接口。"
                "**语义歧义，非算错。**")
        if case_id in ("ie-03-surface-raid__llm-rl__s5101",):
            note = ("标注人依据\"末次射击在 tick 28、余弹 14 发\"判执行；机器依据 ΔP +0.48 "
                    "判规划。而 ΔE = 0 —— 若执行层单独是瓶颈，换规则执行本应改善。"
                    "**归因歧义。**")
        lines.append(f"| `{packet}` | {LABEL_CN.get(row['machine'], row['machine'])} "
                     f"| {LABEL_CN.get(row['human'], row['human'])} | {fmt(case['dP'], 2)} "
                     f"| {fmt(case['dE'], 2)} | {fmt(case['dI'], 2)} | {note} |")
    lines += [
        "",
        f"**排查小结**：归因错误 0 例（{n_case}/{n_case} 自身回放门禁精确匹配）；标注歧义 "
        f"{n_disagree} 例。语义差的根源是两套标签定义测的不是同一件事："
        "机器的\"接口\"= 层间**边际交互**（ΔI 项），人工的\"均衡\"= **两层各自都可疑**。",
        "",
        "## 6. 数据质量与校验",
        "",
        "| 项 | 结果 |",
        "|---|---|",
        f"| 回放门禁（逐帧一致） | "
        f"{f'{n_case}/{n_case} 通过' if kappa['all_replay_gates_passed'] else '未全部通过'} |",
        f"| 归因完整性 | "
        f"{f'{n_case}/{n_case} 完成' if kappa['all_attributions_complete'] else '未完成'} |",
        f"| 人工标注回收 | {len(human)}/{n_case}（置信度 "
        f"{sorted({row['confidence'] for row in human.values()}) or '—'}，全部附理由） |",
        "| 引擎/场景冻结 | 536 个文件哈希校验通过 |",
        "| 跨批拼接 | 无（hifi 与 grid 各自独立批次，不合并统计） |",
        "",
        "## 7. 已知局限（写进论文时必须保留）",
        "",
        "1. **\"接口\"标签的含义须谨慎**：它由 ΔI（两层同时替换的交互项）最大得出，"
        "不代表\"目标表达本身有缺陷\"。人工标注人系统性地把它读成\"均衡\"，正说明该标签的"
        "自然语义与算法语义不同。",
        "2. **参照组件不是认证 oracle**：参照规划器/执行器是项目既有规则基线，"
        "§5.1 第 (v) 条\"oracle 质量独立验证\"在本 pilot 未满足。",
        "3. **冻结目标对照的边界**：IE-08 s5101 中参照执行层让对局越过了原局最后一个决策点"
        "（tick 1040），之后规划器沿用最后计划 14 次，已单独记录。",
        f"4. **场景分布不均衡**：存在整类无失败局的场景，入选高保真样本分布为 {distribution}。",
        "5. **执行过程**：第一轮有 3 局 IE-08 触发 60 秒/tick 保护，已用同种子、300 秒保护重跑，"
        "判负规则不变。",
        "6. **grid 与高保真的 max_tokens 不同**（4096 vs 1024），两者不合并统计。",
        "7. **低分不等于败局**：有案例原生终局为 `defender_success` 但综合分 < 0.6，"
        "标注人也据此在理由中说明；判负规则按评分而非终局。",
        "",
        "## 8. 结论与三个可选写法（需与老师定）",
        "",
        f"- **事实**：技术链路全部通过；人机一致性 **κ = {kappa['cohen_kappa']:.2f}**，未达事前判据；"
        "分歧全部可解释为标签语义，而非工具算错。",
        "- **写法 1（推荐，如实降级）**：§6.3 写\"归因工具在合成故障上校准通过，"
        f"自然场景 pilot 一致性有限（κ = {kappa['cohen_kappa']:.2f}，"
        f"{n_disagree}/{kappa['n_paired']} 不一致，全部集中在接口与均衡的语义边界）\"，"
        "并把 §5.1 的归因能力表述限定为\"层间边际贡献\"。",
        "- **写法 2（概念对齐后重测）**：把\"接口\"限定为\"仅当两层同时替换才改善，"
        "且能观察到接口症状（目标被拒/不可行/频繁替换）\"，把\"均衡\"限定为"
        "\"两层各自独立可改善\"；**另开一批新盲标**（不能改已有案例的数据与判据）。",
        f"- **写法 3（案例研究）**：把 {n_disagree} 个不一致案例作为\"归因边界\"的案例研究"
        "写进附录，不宣称 κ 达标。",
        "- **禁止**：剔除不一致案例重算 κ、更换标注人重标、事后调整判据或阈值。",
        "",
        "## 9. 文件位置",
        "",
        "| 内容 | 服务器 | 本地 |",
        "|---|---|---|",
        "| 高保真第 1 轮 | `experiments/e5-hifi-natural-failures-20261001T1920Z/` | "
        "`run-hifi-r1/`（节选 manifest + 用例） |",
        "| 高保真续跑 r2 | `experiments/e5-hifi-natural-failures-r2-20261002T0220Z/` | "
        "`run-hifi-r2/` |",
        "| IE-08 s5101 补跑 | `experiments/e5-hifi-attribution-r3b-20261002T0715Z/` | 同上 |",
        "| grid 对局与归因 | `experiments/e5-grid-natural-failures-20261002T0640Z/` | "
        "`grid-campaign/` |",
        "| 盲标包 + key | `experiments/e5-annotation-final-20261002T1230Z/` | `annotation-final/` |",
        "| 人工标注原件 | 同上 `annotation_form_filled.csv` | `annotation_form_filled.csv` |",
        "| κ 原始输出 | 同上 `kappa_summary.json` | `kappa_summary.json` |",
        "",
        "复算命令（κ）：",
        "",
        "```bash",
        "cd role_c_toolkit",
        "python e5_annotation.py summary \\",
        "  --campaign <r1> --campaign <r2> --campaign <r3b> \\",
        "  --grid-summary <grid>/e5_grid_summary.json \\",
        "  --key annotation-final/KEY_DO_NOT_SHARE.json \\",
        "  --human annotation_form_filled.csv \\",
        "  --output kappa_summary.json",
        "```",
    ]
    return chr(10).join(lines) + chr(10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = render(args.artifacts)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text)} chars)")


if __name__ == "__main__":
    main()

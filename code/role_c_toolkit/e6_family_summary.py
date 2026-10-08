"""One side-by-side overview of every model in the E6 family.

The four models ran as **separate, independently frozen batches**.  This module only
places their numbers next to each other: it never pools means, never runs a joint
bootstrap and never computes a cross-batch p-value.  Where the batches differ
(output-token ceiling, serving form, thinking policy) the table says so, because those
differences are the reason a pooled statistic would be wrong.

Usage: python e6_family_summary.py --analysis <a.json> <b.json> ... --output <file.md>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LABELS = {"passed": "通过", "failed": "未通过",
          "not_significant_ci_includes_zero": "方向正确但区间跨零",
          "not_evaluable_insufficient_valid_seeds": "不可判定（有效 seed 不足）",
          "not_evaluable_no_reference": "不可判定（缺纯 RL 参照）",
          "reproduced": "复现", "not_reproduced": "未复现", "deployment_behind_baseline": "部署落后基线"}


def fmt(value, digits=3):
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return f"{value:.{digits}f}"


def ci(block):
    interval = (block or {}).get("ci95")
    if not interval:
        return "—"
    return f"[{fmt(interval[0])}, {fmt(interval[1])}]"


def collect(analysis_path: Path, plan_path: Path) -> list[dict]:
    summary = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    remote = any((entry or {}).get("kind") == "remote-provider"
                 for entry in summary["models"].values())
    rows = []
    for name, entry in summary["models"].items():
        group = summary["group_summary"][name]
        thinking = (summary.get("thinking_summary") or {}).get(name) or {}
        rows.append({
            "name": entry.get("served_name"),
            "batch": Path(plan_path).parent.name,
            "serving": "第三方 API" if remote else "本机 vLLM 副本",
            "endpoint": entry.get("base_url") or entry.get("directory"),
            "max_tokens": plan.get("max_tokens"),
            "seeds": len(plan.get("seeds") or []),
            "reference_seeds": len(plan.get("reference_seeds") or []),
            "conditions": "/".join(plan.get("conditions") or ["strong", "hold"]),
            "thinking_required_off": thinking.get("expect_no_thinking"),
            "thinking_blocks": thinking.get("thinking_blocks"),
            "cases_with_thinking": thinking.get("cases_with_thinking"),
            "strong": group["strong"]["mean"], "strong_ci": ci(group["strong"]),
            "hold": group["hold"]["mean"], "hold_ci": ci(group["hold"]),
            "delta": group["strong_minus_hold"]["mean"],
            "delta_ci": ci(group["strong_minus_hold"]),
            "delta_n": group["strong_minus_hold"].get("n"),
            "rl_delta": group["strong_minus_pure_rl"]["mean"],
            "rl_ci": ci(group["strong_minus_pure_rl"]),
            "rl_n": len(group["strong_minus_pure_rl"].get("seeds_used") or []),
            "verdicts": summary["verdicts"].get(name, {}),
            "per_seed": group["strong_minus_hold"].get("per_seed") or {},
        })
    return rows


def render(rows: list[dict]) -> str:
    batches = sorted({row["batch"] for row in rows})
    lines = [
        "# E6 家族四模型总览（并置，不合并统计）",
        "",
        f"> 来源批次：{', '.join(batches)}；每个批次各自独立冻结、独立执行。",
        "> **本文件只做并置展示**：不合并均值、不做联合 bootstrap、不计算跨批次显著性——"
        "各批次的输出上限、服务形态与思考策略不同，合并会得出错误结论。",
        "",
        "## 1. 四模型结论并置",
        "",
        "| 模型 | 服务 | 输出上限 | seeds | 条件 | 接口因果必要（strong − hold） | 部署落后基线（strong − 纯 RL） | 判定 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['serving']} | {row['max_tokens']} | {row['seeds']} "
            f"(参照 {row['reference_seeds']}) | {row['conditions']} "
            f"| {LABELS.get(row['verdicts'].get('interface_causal_necessity'), '—')}"
            f"（{fmt(row['delta'])}, 95% CI {row['delta_ci']}） "
            f"| {LABELS.get(row['verdicts'].get('deployment_behind_baseline'), '—')}"
            f"（{fmt(row['rl_delta'])}, 95% CI {row['rl_ci']}） "
            f"| {LABELS.get(row['verdicts'].get('overall'), '—')} |")
    lines += [
        "",
        "判据（事前写入各批次 `plan.json`）：接口因果必要 = mean(V_strong − V_hold) > 0 且 "
        "seed-bootstrap 95% CI 下界 > 0；部署落后基线 = mean(V_strong − V_纯RL) < 0。",
        "任一模型未通过即如实记为定律边界，不重贴标签、不改判据、不换种子。",
        "",
        "## 2. 分组均值",
        "",
        "| 模型 | strong 均值 | 95% CI | hold 均值 | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['name']} | {fmt(row['strong'])} | {row['strong_ci']} "
                     f"| {fmt(row['hold'])} | {row['hold_ci']} |")

    lines += ["", "## 3. 逐 seed 配对差值（strong − hold）", "",
              "| 模型 | 逐 seed ΔV | 正效应 | 均值 |", "|---|---|---|---|"]
    for row in rows:
        per = row["per_seed"]
        positives = sum(1 for value in per.values() if value > 0)
        detail = "、".join(f"{seed % 1000}:{fmt(value, 2)}" for seed, value in sorted(
            ((int(k), v) for k, v in per.items())))
        lines.append(f"| {row['name']} | {detail} | {positives}/{len(per)} | {fmt(row['delta'])} |")

    lines += ["", "## 4. 思考策略与实际行为", "",
              "| 模型 | 要求关闭思考 | 实际思考块 | 出现思考的案例数 |", "|---|---|---|---|"]
    for row in rows:
        required = row["thinking_required_off"]
        lines.append(f"| {row['name']} | "
                     f"{'是' if required else ('否' if required is not None else '不适用（无此开关）')} "
                     f"| {row['thinking_blocks'] if row['thinking_blocks'] is not None else '—'} "
                     f"| {row['cases_with_thinking'] if row['cases_with_thinking'] is not None else '—'} |")

    borderline = [row for row in rows
                  if row["rl_ci"] != "—" and row["rl_delta"] is not None]
    lines += ["", "## 5. 必须一起读的三点", ""]
    for row in rows:
        if row["verdicts"].get("deployment_behind_baseline") == "failed":
            lines.append(f"- **{row['name']} 未通过\"部署落后基线\"**：均值 {fmt(row['rl_delta'])}，"
                         f"95% CI {row['rl_ci']}，即该模型在 strong 档已追平纯 RL。"
                         f"这是定律适用前提（存在性能落差）在该模型上消失，属于边界证据。")
    lines += [
        "- **\"部署落后基线\"整体比另一条判据脆**：各批次该判据都只有 3 个参照 seed，"
        "区间普遍很宽（上界贴近零或跨零）。扩增 strong/hold 的种子并不会提高它的精度。",
        "- **不同批次不可合并**：输出上限（1024 vs 8192）、服务形态（本机 vLLM vs 第三方 API）、"
        "思考策略（可关闭 vs 不可关闭）都不同；论文里可以并置成表、并列讨论，"
        "但不能把四个模型并成一个均值或一个联合区间。",
        "- **MoE 的\"规模\"含两个变量**：MiniMax 系列是 MoE（428B/A23B、230B/A10B），"
        "与 Qwen 的稠密 8B/27B 相比，总参与激活量同时变化，"
        "因此本表不能用来主张\"参数规模的单调性\"。",
    ]
    return chr(10).join(lines) + chr(10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for analysis in args.analysis:
        plan = Path(analysis).parent.parent / "plan.json"
        if not plan.is_file():
            raise FileNotFoundError("Missing sibling plan.json for " + str(analysis))
        rows += collect(analysis, plan)
    args.output.write_text(render(rows), encoding="utf-8")
    print(f"wrote {args.output} with {len(rows)} models from "
          f"{len({row['batch'] for row in rows})} batches")


if __name__ == "__main__":
    main()

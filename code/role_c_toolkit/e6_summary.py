"""Render the E6 analysis dictionary as the Chinese summary handed to the paper."""
from __future__ import annotations

LABELS = {"passed": "通过", "failed": "未通过",
          "not_significant_ci_includes_zero": "方向正确但区间跨零（未达显著）",
          "not_evaluable_insufficient_valid_seeds": "不可判定（有效 seed 不足）",
          "not_evaluable_no_reference": "不可判定（缺纯 RL 参照）",
          "reproduced": "复现", "not_reproduced": "未复现"}


def fmt(value, digits=3):
    if value is None:
        return "—"
    if isinstance(value, (int, str)):
        return str(value)
    return f"{value:.{digits}f}"


def ci(block):
    interval = block.get("ci95")
    if not interval:
        return "—"
    return f"[{fmt(interval[0])}, {fmt(interval[1])}]"


def render(summary: dict, plan: dict | None = None) -> str:
    plan_models = summary["models"]
    groups = summary["group_summary"]
    plan = plan or {}
    status = ", ".join(f"{name}={value}" for name, value in summary["run_status"].items())
    lines = [
        f"# {plan.get('title') or 'E6b 第三方模型消融：结果汇总'}",
        "",
        "> 生成：由 `role_c_toolkit/e6_analyze.py` + `e6_summary.py` 自动生成，数字全部来自"
        " `analysis/e6_analysis.json`，未手工改动。",
        f"> 运行状态：{status}；全部预注册案例有效："
        f"**{'是' if summary['all_preregistered_cases_valid'] else '否'}**。",
        "",
        "## 1. 结论",
        "",
        "| 模型 | 接口因果必要（strong − hold） | 部署落后纯基线（strong − 纯 RL） | 定律是否复现 |",
        "|---|---|---|---|",
    ]
    for model, entry in plan_models.items():
        verdict = summary["verdicts"].get(model, {})
        lines.append(
            f"| {entry['served_name']} | {LABELS.get(verdict.get('interface_causal_necessity'), '—')} "
            f"（{fmt(groups[model]['strong_minus_hold']['mean'])}, 95% CI {ci(groups[model]['strong_minus_hold'])}） "
            f"| {LABELS.get(verdict.get('deployment_behind_baseline'), '—')} "
            f"（{fmt(groups[model]['strong_minus_pure_rl']['mean'])}, 95% CI {ci(groups[model]['strong_minus_pure_rl'])}） "
            f"| {LABELS.get(verdict.get('overall'), '—')} |")
    lines += ["", "判据在开跑前写入 `plan.json`：接口因果必要 = mean(V_strong − V_hold) > 0 且 "
              "seed-bootstrap 95% CI 下界 > 0；部署落后基线 = mean(V_strong − V_纯RL) < 0。"
              "任一模型未通过即如实记为定律边界，不重贴标签、不改判据。", ""]

    lines += ["## 2. 冻结条件", "",
              "| 项目 | 取值 |", "|---|---|",
              f"| 栈 | grid medium / continuous，`llm-rl`（LLM 规划 + 固定 v9 RL 执行，每 10 步重规划） |",
              f"| 条件 | strong / hold 两档（本管线不存在 masked 档，见 §5） |",
              f"| seeds | {', '.join(str(seed) for seed in summary['seeds'])} |",
              f"| 纯 RL 参照 seeds | {', '.join(str(seed) for seed in summary['reference_seeds'])} |",
              f"| 采样 | temperature 0.1，max_tokens {plan.get('max_tokens', '—')}，规划器重试 0 |",
              (f"| 传输 | Anthropic Messages 兼容路径，只取 `text` block 作为规划器回答 |"
               if any(e.get("kind") == "remote-provider" for e in plan_models.values()) else
               f"| 服务 | 本机独立的 vLLM 推理副本，OpenAI 兼容 `/chat/completions` |"),
              f"| 效用 | {summary['utility_definition']} |",
              f"| 统计 | seed 为抽样单位，bootstrap {summary['group_summary'][next(iter(groups))]['strong_minus_hold'].get('draws')} 次，"
              f"RNG 种子 {summary['group_summary'][next(iter(groups))]['strong_minus_hold'].get('seed')} |",
              ""]
    if plan.get("max_tokens_measurement"):
        lines += ["> **max_tokens 说明**：实测 M3 在关闭思考时每次只输出约 130–175 token；"
                  "M2.x 无法关闭思考，思考加回答约需 1500–1800 token，1024 会被截断、"
                  "4096 起才完整。两模型共用同一上限（8192），避免预算成为混淆变量；"
                  "E6 的 27B/8B 批次用的是 1024，两组**不可跨批拼接**。", ""]
    for model, entry in plan_models.items():
        directory = entry.get('directory') or entry.get('base_url') or '—'
        manifest = entry.get('manifest_sha256')
        lines.append(f"- {entry['served_name']}：{directory}"
                     + (f"，manifest SHA-256 `{manifest[:16]}…`" if manifest else "")
                     + (f"，kind={entry['kind']}" if entry.get('kind') else ""))

    thinking = summary.get('thinking_summary') or {}
    if any((row or {}).get('expect_no_thinking') is not None for row in thinking.values()):
        lines += ["", "### 2b. 思考策略与实际行为", "",
                  "| 模型 | 要求关闭思考 | 实际思考块 | 出现思考的案例数 |", "|---|---|---|---|"]
        for model, entry in plan_models.items():
            row = thinking.get(model) or {}
            requirement = row.get('expect_no_thinking')
            lines.append(f"| {entry['served_name']} | "
                         f"{'是' if requirement else ('否' if requirement is not None else '—')} | "
                         f"{row.get('thinking_blocks', '—')} | {row.get('cases_with_thinking', '—')} |")
        lines.append("")
    lines += ["", "## 3. 分组结果", ""]
    for model, entry in plan_models.items():
        lines += [f"### {entry['served_name']}", "",
                  "| 条件 | 均值 V | 95% CI | 有效 seed |", "|---|---|---|---|"]
        for condition in summary["conditions"]:
            block = groups[model][condition]
            lines.append(f"| {condition} | {fmt(block['mean'])} | {ci(block)} | "
                         f"{len(block.get('seeds_used') or [])} |")
        lines += ["", f"strong − hold（逐 seed 配对）：", "",
                  "| seed | ΔV |", "|---|---|"]
        for seed, value in (groups[model]["strong_minus_hold"].get("per_seed") or {}).items():
            lines.append(f"| {seed} | {fmt(value)} |")
        lines += ["", f"strong − 纯 RL 参照：均值 {fmt(groups[model]['strong_minus_pure_rl']['mean'])}，"
                  f"95% CI {ci(groups[model]['strong_minus_pure_rl'])}，"
                  f"有效参照 {len(groups[model]['strong_minus_pure_rl'].get('seeds_used') or [])} 个。", ""]

    invalid = [row for row in summary["records"] if not row["analysis_valid"]]
    lines += ["## 4. 数据质量", "",
              f"- 预注册案例齐全：{'是' if summary['all_preregistered_cases_present'] else '否'}",
              f"- 有效案例：{len(summary['records']) - len(invalid)}/{len(summary['records'])}",
              f"- 无效案例：{len(invalid)}" + ("" if not invalid else
                                          "（" + "; ".join(f"{row['case_id']}:{','.join(row['invalid_reasons'])}"
                                                          for row in invalid) + "）"),
              f"- 数据问题：{summary['data_problems'] or '无'}",
              f"- 批次拼接：{'未跨批次拼接' if summary['no_cross_batch_data_merged'] else '存在拼接'}",
              ""]
    if summary.get("endpoint_continuity"):
        lines += ["### 4b. 服务部署与服务进程连续性", "",
                  "| 模型 | 副本 | PID | 同进程起止一致 |", "|---|---|---|---|"]
        for row in summary["endpoint_continuity"]:
            lines.append(f"| {row['model']} | {row['replica']} | {row['pid']} | "
                         f"{'是' if row['same_process_start'] else '否'} |")
        lines.append("")
    elif summary.get("endpoint_continuity_note"):
        lines += ["### 4b. 服务进程连续性", "",
                  "未核验：本机没有 /proc（分析在 Windows 上重跑），进程连续性需在服务器上复核。", ""]
    if summary.get("provider_identity"):
        lines += ["### 4c. 提供商身份（probe 时记录）", "",
                  "| 模型 | 端点 | 该账号可用模型 |", "|---|---|---|"]
        for row in summary["provider_identity"]:
            available = row.get("available_models") or []
            lines.append(f"| {row.get('served_name')} | `{row.get('base_url') or '—'}` | "
                         f"{len(available)} 个：{', '.join(available[:4])}"
                         f"{' …' if len(available) > 4 else ''} |")
        lines.append("")

    lines += ["### 4d. 调用与耗时（按模型汇总）", "",
              "| 模型 | 案例 | LLM 调用 | API tokens | LLM 秒 | 单局墙钟秒（均值） |",
              "|---|---|---|---|---|---|"]
    for model in plan_models:
        rows = [row for row in summary["records"]
                if row["model"] == model and row["arm"] == "llm-rl"]
        calls = sum(row["llm_calls"] or 0 for row in rows)
        tokens = sum(row["API_total_tokens"] or 0 for row in rows)
        llm_seconds = sum(row["llm_seconds"] or 0 for row in rows)
        walls = [row["wall_seconds"] for row in rows if row["wall_seconds"]]
        mean_wall = sum(walls) / len(walls) if walls else None
        lines.append(f"| {plan_models[model]['served_name']} | {len(rows)} | {calls} | {tokens} | "
                     f"{fmt(llm_seconds, 1)} | {fmt(mean_wall, 1)} |")
    lines.append("")

    # The preregistered criteria are evaluated literally; where an interval nearly
    # touches zero the reader has to see that, not just the verdict word.
    borderline = []
    for model, entry in plan_models.items():
        behind = groups[model]["strong_minus_pure_rl"]
        interval = behind.get("ci95")
        if interval and interval[1] >= 0 and behind["mean"] < 0:
            borderline.append(f"{entry['served_name']}：strong − 纯 RL 均值 {fmt(behind['mean'])}，"
                              f"区间上界 {fmt(interval[1])} ≥ 0（仅 {len(behind.get('seeds_used') or [])} 个参照 seed）")
    if borderline:
        lines += ["### 4e. 判据的边界情形（不得省略）", "",
                  "判据按事前字面执行（均值方向），但下列情形必须连同数字与不确定性一起报告：", ""]
        lines += [f"- {row}" for row in borderline]
        lines.append("")
    failed_baseline = [model for model in plan_models
                       if summary["verdicts"].get(model, {}).get("deployment_behind_baseline")
                       not in (None, "passed", "not_evaluable_no_reference")]
    if failed_baseline:
        lines += ["### 4f. 未通过判据的模型（如实记录，不重贴标签）", ""]
        for model in failed_baseline:
            behind = groups[model]["strong_minus_pure_rl"]
            lines.append(f"- **{plan_models[model]['served_name']}**：strong − 纯 RL 均值 "
                         f"{fmt(behind['mean'])}，95% CI {ci(behind)} —— 该模型上"
                         f"\"部署落后纯基线\"不成立（均值 ≥ 0），按事前约定记为定律边界。")
        lines.append("")

    remote = any(plan_models[model].get("kind") == "remote-provider" for model in plan_models)
    local = any(plan_models[model].get("kind") == "local" for model in plan_models)
    lines += ["## 5. 局限（必须如实写进论文）", ""]
    if remote:
        lines += [
            "- **第三方 API 模型不是本机受控服务**：提供商侧的批调度、内核与量化实现未知，"
            "本批只能主张\"换到该提供商服务后方向是否复现\"，不能声称与自建 27B/8B 完全同条件。",
            "- **思考不可关闭的模型必须单独说明**：官方契约写明 M2.x 的 `thinking=disabled` "
            "\"accepted but ignored\"；本批把\"要求关闭\"与\"实测思考块\"分开记录（见 §2b），"
            "对照里同时含\"代际\"和\"是否思考\"两个变量，不得解释成纯粹的规模效应。",
            "- **参照 seed 只有 3 个**：\"部署落后纯基线\"的区间因此很宽，未通过的模型也要"
            "连同区间一起报告，不得只报均值方向。",
        ]
    if local:
        lines += [
            "- 两模型使用不同副本与不同权重，服务端内核/批调度差异未被消融；本实验只主张"
            "\"同一冻结评测管线下换模型后定律方向是否复现\"。",
        ]
    if not summary.get("masked_condition_available"):
        note = summary["condition_note"]
        if note.startswith("The pipeline exposes only"):
            note = ("本管线只暴露 strong/hold 两种目标档；旧清单里的 masked 剂量点在本代码中"
                    "不存在")
        lines.append("- **只跑了 strong/hold 两档**：" + note + "；论文不能写成三档剂量曲线。")
    lines += [
        f"- {len(summary['seeds'])} 个 seed 的区间是探索性精度，不足以宣称普遍性或精确定位；"
        "各模型各自独立批次，不与历史批次拼接统计。",
        "- 纯 RL 参照与 strong 臂共享同一 seed，参照臂不调用 LLM，因此只检验"
        "\"部署是否落后于纯基线\"，不构成对 LLM 组件贡献的因果分解。",
    ]
    if plan.get("seed_set_extended_after_first_batch") and plan.get("extension_note"):
        lines.append("- **种子集扩增**：" + plan["extension_note"])
    for note in plan.get("service_notes") or []:
        lines.append("- " + note)
    if summary["verdicts"].get("_run"):
        lines.append(f"- **运行未完成**：{summary['verdicts']['_run']}。")
    if summary["verdicts"].get("_services"):
        lines.append("- **服务进程在批次中途变化**：两批次的对照条件可能不一致，需重跑。")
    return chr(10).join(lines) + chr(10)

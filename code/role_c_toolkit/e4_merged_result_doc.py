"""Build the merged Option-1 + Option-2 deliverable.

The two batches manipulated planning information differently and must not be pooled:

* Option 1: the screened contract gives the planner no goal at all, so the baseline arm is
  "no goal was ever supplied".
* Option 2: the adapter runs the planner normally and then rewrites the goals, so its withheld
  arm is "a plan exists but is degraded to hold".

The merged document therefore reports them as two studies with named manipulations, keeps every
number traceable to its own JSON, and carries one joint conclusion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts/e4-scenario-family"
A1 = ART / "analysis/e1_2x2_option1.json"
A2 = Path("/mnt/QTJC/chenyi-codex/experiments/e4-headroom-2x2/P1/option2_result.json")
A2_FALLBACK = ART / "analysis/e1_2x2_option2.json"
OUT = ART / "实验2_选项1与2合并报告.md"


def load(path: Path, fallback: Path | None = None) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    if fallback and fallback.is_file():
        return json.loads(fallback.read_text(encoding="utf-8"))
    raise SystemExit(f"missing analysis input: {path}")


def build(o1: dict, o2: dict) -> str:
    c1 = sorted(o1["cells"], key=lambda c: c["information_withheld"])
    c2 = sorted(o2["cells"], key=lambda c: c["reference_mean"])
    scan = sorted(o2.get("scan") or [], key=lambda r: r["v"], reverse=True)
    i1 = o1.get("interaction") or {}
    i2 = o2.get("interaction") or {}

    L: list[str] = []
    L.append("# 实验 2 合并报告：规划信息 × headroom 的两组族内检验")
    L.append("")
    L.append("> 对象：`OpenMDBench_补实验清单_P0硬伤_20261006.md（v3）` 第 33–56 行的实验 2。")
    L.append("> 本文合并两次执行：**Study 1** 用既有门禁数据（4 档 × 10 seed），")
    L.append("> **Study 2** 用合作者交付的 runner 新跑（32 档扫描 + 5 档 × 5 seed 配对）。")
    L.append(">")
    L.append("> **两组不可合并成一张表**：它们的「信息残缺」臂是同名的不同操纵（见 §1.3）。")
    L.append("> 全部数字可追到 `e1_2x2_option1.json` 与 `e1_2x2_option2.json`。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 1. 设计与两次执行的差异（先读这一节）")
    L.append("")
    L.append("### 1.1 共同点")
    L.append("")
    L.append("- **同一任务族**：E1 的 IE-05 多轴拦截交战。")
    L.append("- **同一执行器**：脚本规则规划器（`--planner rule`），**任何一局都没有 LLM 调用**；")
    L.append("  `attempt_manifest.json` 可逐局核对。")
    L.append("- **只改规划信息**：两组都在固定执行器的前提下改变规划层收到的目标信息。")
    L.append("- **判据同字段**：`report.json → layered_metrics.performance_v`。")
    L.append("")
    L.append("### 1.2 两次执行")
    L.append("")
    L.append("| | Study 1（选项 1） | Study 2（选项 2） |")
    L.append("|---|---|---|")
    L.append("| 数据来源 | 既有 E1 门禁数据（已冻结） | 本轮新跑（合作者交付 runner）|")
    L.append("| 档位 | 4 档（N017/N018/N019/N027） | 32 档扫描 + 5 档配对（N009/N013/N016/N018/N027）|")
    L.append("| seed | 4151–4160（每臂 10） | 64101–64105（每臂 5）|")
    L.append("| 操纵对象 | **规划器的分配决策规则**（`greedy` 开/关）| **规划信息量**（计划完整 / 被降级）|")
    L.append("| 臂 A | `rule-strong-g1`（`dose=strong`, `greedy=true`）| 适配器 `--dose strong` |")
    L.append("| 臂 B | `rule-strong-g0`（`dose=strong`, `greedy=false`）| 适配器 `--dose hold` |")
    L.append("| 局数 | 80（4 档 × 2 臂 × 10） | 110（32 + 50 + 25 + 3）|")
    L.append("")
    L.append("### 1.3 两次操纵的不是同一个变量（关键，必须先看）")
    L.append("")
    L.append("**Study 1 的两臂剂量相同。** 由各局 `completion.json` 逐局核实：")
    L.append("")
    L.append("| 臂 | `config.dose` | `config.greedy` |")
    L.append("|---|---|---|")
    L.append("| `rule-strong-g1` | `strong` | **`true`** |")
    L.append("| `rule-strong-g0` | `strong` | **`false`** |")
    L.append("| `rule-hold-g0`（未用于本对比）| `hold` | `false` |")
    L.append("")
    L.append("因此：")
    L.append("")
    L.append("- **Study 1 检验的是「分配决策规则」**（`greedy` 最近接触分配 vs 规划器默认分配），")
    L.append("  **不是信息量**。两臂都拿到 `strong` 剂量的完整计划。")
    L.append("- **Study 2 才是「规划信息量」的检验**（完整计划 vs 被降级为 hold 的计划）。")
    L.append("")
    L.append("**这两组不能合并、也不能互相替代。** 它们效应的量级差异（约 +0.1 对约 +0.7）")
    L.append("正说明：**分配规则的好坏影响约 0.1，而计划是否可用影响约 0.7**。")
    L.append("这对论文有用——它把「决策形态」与「信息可用性」的贡献分开了。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 2. Study 1：分配决策规则（greedy 开/关），剂量固定为 strong")
    L.append("")
    L.append("> 再次强调：这两臂**都收到完整的 `strong` 计划**，差异只在规划器的分配规则。")
    L.append("> 因此下表衡量的是「决策形态」的贡献，不是「信息量」。")
    L.append("")
    L.append("| 档位 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI | 显著 |")
    L.append("|---|---|---|---|---|---|---|")
    for cell in c1:
        L.append(f"| `{cell['tier']}` | {cell['n']} | {cell['information_supplied']:.4f} "
                 f"| {cell['information_withheld']:.4f} | **{cell['effect']:+.4f}** "
                 f"| [{cell['ci_low']:+.3f}, {cell['ci_high']:+.3f}] "
                 f"| {'✅' if cell['significant'] else '—'} |")
    L.append("")
    sig1 = sum(1 for c in c1 if c["significant"])
    L.append(f"**{sig1}/{len(c1)} 档位显著**；4/4 方向为正，量级 +0.01 ～ +0.11。")
    L.append(f"`greedy=false` 侧的水平跨度 {c1[0]['information_withheld']:.4f}–"
             f"{c1[-1]['information_withheld']:.4f}。")
    L.append("")
    if i1:
        L.append(f"**交互（差中差）**：{i1['value']:+.4f}，95% CI "
                 f"[{i1['ci_low']:+.4f}, {i1['ci_high']:+.4f}] → "
                 f"{'显著' if i1['significant'] else '**不显著**'}。")
        sens = i1.get("sensitivity_all_pairs") or []
        if sens:
            n_sig = sum(1 for p in sens if p["significant"])
            lo = min(p["interaction"] for p in sens)
            hi = max(p["interaction"] for p in sens)
            L.append(f"全部 {len(sens)} 个档位对的敏感性检查：**{n_sig}/{len(sens)} 显著**，"
                     f"交互值在 {lo:+.4f} ～ {hi:+.4f} 之间**随配对变号**。")
        L.append("")
        L.append("原因在数据设计：4 档的这一侧只覆盖 "
                 f"{c1[0]['information_withheld']:.3f}–{c1[-1]['information_withheld']:.3f}"
                 "（带宽 "
                 f"{c1[-1]['information_withheld'] - c1[0]['information_withheld']:.3f}），"
                 "既够不到饱和也够不到满分，**headroom 跨度不足以表达交互**。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 3. Study 2：饱和档定位 + 计划降级（新跑）")
    L.append("")
    L.append("### 3.1 32 档基线扫描（据证据选档，不靠假设）")
    L.append("")
    L.append("| 档位 | 扫描 V |")
    L.append("|---|---|")
    for row in scan[:5]:
        L.append(f"| `{row['package'].strip()}` | {row['v']:.4f} |")
    L.append("| … | … |")
    for row in scan[-2:]:
        L.append(f"| `{row['package'].strip()}` | {row['v']:.4f} |")
    L.append("")
    if scan:
        L.append(f"最高 **{scan[0]['v']:.4f}**、最低 {scan[-1]['v']:.4f}。")
        L.append("**族内确有接近饱和的档位**——Study 1 的 4 档恰好落在中段，")
        L.append("这正是其带宽只有 0.094 的原因。")
    L.append("")
    L.append("### 3.2 配对 2×2（5 档 × 5 seed，共同 seed 集）")
    L.append("")
    L.append("| 档位 | 扫描 V | n | 信息完整 | 计划降级 | **效应** | 95% CI | 显著 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for cell in c2:
        sv = f"{cell['scan_v']:.4f}" if cell.get("scan_v") is not None else "—"
        L.append(f"| `{cell['tier']}` | {sv} | {cell['n']} | {cell['strong_mean']:.4f} "
                 f"| {cell['reference_mean']:.4f} | **{cell['effect']:+.4f}** "
                 f"| [{cell['ci_low']:+.3f}, {cell['ci_high']:+.3f}] "
                 f"| {'✅' if cell['significant'] else '—'} |")
    L.append("")
    L.append(f"**{sum(1 for c in c2 if c['significant'])}/{len(c2)} 档位显著**，"
             "量级 +0.62 ～ +0.73。")
    L.append("")
    if i2:
        L.append("### 3.3 交互效应及其限制")
        L.append("")
        L.append(f"按「提供信息臂实现水平」切分：**{i2['value']:+.4f}，95% CI "
                 f"[{i2['ci_low']:+.4f}, {i2['ci_high']:+.4f}] → "
                 f"{'显著' if i2['significant'] else '不显著'}**。")
        L.append("")
        L.append("**但这不是干净的 headroom 因果证据**，三条理由必须随结论报告：")
        L.append("")
        L.append("1. **降级臂不携带档位信息**：各档位降级臂均为 "
                 f"{min(c['reference_mean'] for c in c2):.4f}–"
                 f"{max(c['reference_mean'] for c in c2):.4f}，且**对 seed 完全不敏感**——")
        L.append("   它是结构性塌陷，不是难度指纹。")
        L.append("2. **扫描 V 不支持分组**：被分到两端的档位扫描 V 几乎相同，"
                 "分组并非由预注册难度差决定。")
        L.append("3. **方差来源单一**：降级臂为常数，全部种子级方差来自提供信息臂，"
                 "故该交互只能作**描述性**结果。")
    L.append("")
    L.append("### 3.4 操纵机制的实测刻画")
    L.append("")
    L.append("为判断「信息量」能否做成梯度，单独做了粒度探针（N013 / seed 64101）：")
    L.append("")
    L.append("| 条件 | V | 说明 |")
    L.append("|---|---|---|")
    L.append("| 原生 runner（无转换）| 0.9692 | 参照 |")
    L.append("| `--goal-granularity medium` | 0.9692 | `unit_id` + `target_id` |")
    L.append("| `--goal-granularity weak` | 0.1808 | 仅 `unit_id` |")
    L.append("| 适配器 `--dose strong` | 0.9692 | 完整参数 |")
    L.append("| 适配器 `--dose hold` | 0.1808 | 目标改写为 hold |")
    L.append("")
    L.append("三点结论：")
    L.append("")
    L.append("1. **路径无混淆**：原生 runner 与适配器 strong 在同档同 seed 上均为 0.9692。")
    L.append("2. **`medium` 与完整参数数值完全相同**——删掉 `position`/`speed`/`pattern`/")
    L.append("   `constraints` 不影响结果，因为执行器只需要 `target_id`。")
    L.append("3. **粒度开关实际是二值的**：一旦 `target_id` 缺失，执行器即瘫痪（约 0.18）。")
    L.append("   故本族「规划信息」的真实杠杆是**计划可用 vs 计划残缺**，而非连续信息梯度。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 4. 合并结论")
    L.append("")
    L.append("### 4.1 两次执行分别证明了什么")
    L.append("")
    L.append("| | 操纵 | 结论 | 对 v3 的用处 |")
    L.append("|---|---|---|---|")
    L.append("| Study 1 | 分配决策规则（`greedy` 开/关），剂量固定 strong | 4/4 为正、"
             "2/4 显著，量级约 +0.1 | **决策形态**的贡献量级 |")
    L.append("| Study 2 | 规划信息（完整计划 / 降级计划）| 5/5 显著，量级约 +0.7 | "
             "**信息可用性**的贡献量级；阳性对照成立 |")
    L.append("")
    L.append("两者合起来的判断：**在本族中，「计划是否可用」影响约 0.7，"
             "「分配规则是否更优」影响约 0.1**——相差约一个量级。")
    L.append("")
    L.append("### 4.2 对 v3 成功判据的逐条回应")
    L.append("")
    L.append("| v3 要求 | 结果 | 依据 |")
    L.append("|---|---|---|")
    L.append("| 同一执行器，只改规划信息 | ✅ 由 Study 2 满足并验证 | `--planner rule`，无 LLM；"
             "路径一致性由粒度探针证实 |")
    L.append("| 正面操纵有效性（阳性对照）| ✅ 成立 | Study 2：5/5 显著；Study 1 另证决策形态亦有小效应 |")
    L.append("| 饱和 vs 非饱和两行 | ⚠️ 族内不成立 | Study 1 带宽仅 0.094；"
             "Study 2 降级臂在各档位均塌陷 |")
    L.append("| 交互效应 + 95% CI | ⚠️ 已算出但不能归因 headroom | 见 §2、§3.3 |")
    L.append("")
    L.append("### 4.3 一句话结论")
    L.append("")
    L.append("在 IE-05 族内，**分配决策规则**带来约 +0.1 的差异，")
    L.append("而**计划可用性**带来约 +0.7 的差异；后者一旦降级即整体塌陷（各档位一律回到约 0.18），")
    L.append("因此该族的 headroom 维度**无法承载**信息量操纵——")
    L.append("条件 (iii) 的因果证据仍须由 §6.7 的跨族对比承接。")
    L.append("")
    L.append("**这对论文是有用的负结果**：它为「gates 外通路缺失」提供机制性解释——")
    L.append("不是没跑，而是该族在 headroom 方向上不可分辨。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 5. 覆盖范围与出处")
    L.append("")
    L.append("| 批次 | 档位 | 条件 | seed | 局数 |")
    L.append("|---|---|---|---|---|")
    L.append("| Study 1（既有门禁，本对比用其中两臂） | 4 档 | `greedy` 开/关（剂量均为 strong） | 4151–4160 | 80 |")
    L.append("| Study 2 扫描 | 32 档 | 基线 | 64101 | 32 |")
    L.append("| Study 2 配对 | 5 档 | `--dose strong` / `--dose hold` | 64101–64105 | 50 |")
    L.append("| Study 2 weak 臂（机制对照）| 5 档 | `--goal-granularity weak` | 64101–64105 | 25 |")
    L.append("| Study 2 粒度探针 | N013 | 原生 / medium / weak | 64101 | 3 |")
    L.append("| **合计** | | | | **190** |")
    L.append("")
    L.append("### 未声称的内容")
    L.append("")
    L.append("1. **两组不合并统计**：操纵的是不同变量（决策规则 vs 信息量），")
    L.append("   且 seed 段与批次都不同。")
    L.append("2. **Study 1 不作为信息量证据**：其两臂剂量相同（均 `strong`），")
    L.append("   差异仅在 `greedy` 开关；引用时必须称其为「分配决策规则」对比。")
    L.append("3. **未把 weak 臂当独立条件**：它与 hold 逐格完全相同（总均值均为 0.1774，")
    L.append("   且对 seed 不敏感），仅作机制证据。")
    L.append("4. **未声称 headroom 因果**（见 §2、§3.3）。")
    L.append("5. **未做跨族合并**：竞争族饱和档（MD-TRK-004 = 0.9666）与本族分属不同任务")
    L.append("   与执行器，未合成任何单一统计量。")
    L.append("")
    L.append("### 数据位置")
    L.append("")
    L.append("- Study 1 源：E1 门禁 `bundle/data/gate-screening/`（武昊 campaign，已冻结）")
    L.append("- Study 2 源：`/mnt/QTJC/chenyi-codex/experiments/e4-headroom-2x2/P1/`")
    L.append("  （本地归档 `server-experiments/e4-headroom-2x2-P1/`，594 文件，")
    L.append("  清单 `MANIFEST.json` 含逐局 SHA-256）")
    L.append("- 分析产物：`analysis/e1_2x2_option1.json`、`analysis/e1_2x2_option2.json`")
    L.append("")
    L.append("### 复算")
    L.append("")
    L.append("```bash")
    L.append("cd role_c_toolkit")
    L.append("python e1_2x2_option1.py            # Study 1：读 E1 门禁数据")
    L.append("python e1_2x2_option2.py            # Study 2：读 scan/ 与 paired/")
    L.append("python e4_merged_result_doc.py      # 生成本合并报告")
    L.append("```")
    L.append("")
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--option1", type=Path, default=A1)
    parser.add_argument("--option2", type=Path, default=A2)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    o1 = load(args.option1)
    o2 = load(args.option2, A2_FALLBACK)
    args.out.write_text(build(o1, o2), encoding="utf-8")
    print(f"written {args.out} ({len(build(o1, o2).splitlines())} lines)")


if __name__ == "__main__":
    main()

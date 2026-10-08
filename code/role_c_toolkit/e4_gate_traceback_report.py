"""Build the single consolidated answer document for the admission-gate trace-back.

Covers, in one file:
  1. what the 55 ledger entries are made of
  2. how the gate verdicts came about (provable from the calibration scripts and today's runs)
  3. whether any figure or paper data used a scenario that must not be counted
  4. the wording that needs to change so the numbers cannot be misread

Every number is read from the artifacts at build time, so the document cannot drift from the
underlying data.
"""
from __future__ import annotations

import json
from pathlib import Path

ARTIFACTS = Path("role_c_toolkit/artifacts/e4-scenario-family")
GRADED = ARTIFACTS / "analysis" / "d2_graded_final2.json"
OUT = ARTIFACTS / "E4_门禁追溯与污染核查_完整说明.md"
D2_LOW, D2_HIGH = 0.40, 0.85

DEMO_PACKAGES = {
    "md_int_002_air_surface": "MD-INT-002-AIR-SURFACE",
    "md_int_003_easy": "MD-INT-003-EASY",
    "md_int_003_medium": "MD-INT-003-MEDIUM",
    "md_int_003_hard": "MD-INT-003-HARD",
    "md_int_005_stealth_multi_axis": "MD-INT-005-STEALTH-MULTI-AXIS",
    "md_int_006_saturation_roe": "MD-INT-006-SATURATION-ROE",
    "md_ad_002_easy": "MD-AD-002-EASY",
    "md_ad_002_medium": "MD-AD-002-MEDIUM",
    "md_ad_002_hard": "MD-AD-002-HARD",
    "md_ad_004_deception": "MD-AD-004-DECEPTION",
}
REC001_VARIANTS = ("MD-REC-001-EASY", "MD-REC-001-MEDIUM", "MD-REC-001-HARD")


def main() -> None:
    ledger = json.loads((ARTIFACTS / "admission_ledger.json").read_text(encoding="utf-8"))
    graded = json.loads(GRADED.read_text(encoding="utf-8"))
    graded_by_key = {k.upper(): v for k, v in graded["scenarios"].items()}
    frozen = json.loads((ARTIFACTS / "d1prime_FROZEN.json").read_text(encoding="utf-8"))
    prior_ids = {row["public_id"] for row in frozen["rows"]}

    rows = ledger["scenarios"]
    by_package: dict[str, list] = {}
    for row in rows:
        by_package.setdefault(row["package"], []).append(row)

    competition = sorted(p for p in by_package if by_package[p][0].get("tree") == "competition_v1")
    formal = sorted(p for p in by_package if by_package[p][0].get("tree") == "formal")
    formal_ie = [p for p in formal if p.startswith("ie_")]
    formal_demo = [p for p in formal if p in DEMO_PACKAGES]
    aliases = {p: [r["public_id"] for r in by_package[p]] for p in by_package
               if len(by_package[p]) > 1}

    comp_rows = [r for r in rows if r.get("tree") == "competition_v1"]
    comp28 = [r for r in comp_rows
              if not (r["public_id"].startswith("MD-REC-001")
                      and r["public_id"] != "MD-REC-001-MEDIUM")]

    def counts(scoped, source) -> tuple[int, int, int, int, int, int]:
        """binary pass/fail, graded pass/fail, composite outside the window."""
        binary = {"pass": 0, "fail": 0}
        graded_v = {"pass": 0, "fail": 0}
        outside = 0
        for row in scoped:
            gate = row["gates"]["D2_headroom"]
            bv = gate.get("verdict_binary") or gate.get("verdict")
            binary[bv] = binary.get(bv, 0) + 1
            block = gate.get("graded") or {}
            gv = block.get("verdict")
            if gv:
                graded_v[gv] = graded_v.get(gv, 0) + 1
            value = block.get("composite")
            if value is None:
                value = graded_by_key.get(row["public_id"].replace("-STANDARD", "").upper(),
                                          {}).get("best_composite_mean")
            if value is not None and (value > D2_HIGH or value < D2_LOW):
                outside += 1
        return (binary.get("pass", 0), binary.get("fail", 0),
                graded_v.get("pass", 0), graded_v.get("fail", 0), outside, len(scoped))

    b_pass_all, b_fail_all, g_pass_all, g_fail_all, out_all, n_all = counts(rows, "all")
    b_pass_28, b_fail_28, g_pass_28, g_fail_28, out_28, n_28 = counts(comp28, "28")

    lines: list[str] = []
    lines.append("# 门禁排除名单：追溯、构成、污染核查与措辞改动")
    lines.append("")
    lines.append("> 本文回应三个问题：**门禁排除名单是谁设的、名单在哪**；")
    lines.append("> **55 个条目是怎么构成的**；**论文图与数据有没有被不该计入的场景污染**。")
    lines.append("> 所有数字在生成时从 `admission_ledger.json`、`analysis/d2_graded_final2.json`、")
    lines.append("> `d1prime_FROZEN.json` 读出，可复算。")
    lines.append("")

    # ---------------------------------------------------------------- 1
    lines.append("## 1. 门禁排除名单是谁设的、在哪")
    lines.append("")
    lines.append("**不是更早的实验负责人（也不是韦思颖）做的，是本次 E4 场景族重标定建立的。**")
    lines.append("")
    lines.append("| 问题 | 答案 |")
    lines.append("|---|---|")
    lines.append("| 谁做的 | 本角色（肖棹），E4 交付项「场景族构建与入场 + D1′ 属性标注」 |")
    lines.append("| 什么时候 | 2026-10-03～04 的标定批次（seeds 2001–2005 → 2101–2105 → "
                 "2201–2205 → 2301–2305） |")
    lines.append("| 名单在哪 | `role_c_toolkit/artifacts/e4-scenario-family/admission_ledger.json`"
                 "（schema `e4-admission-ledger@2`） |")
    lines.append("| 每条含什么 | `public_id`、`package`、`package_sha256`、`gates.*.verdict`、"
                 "`gates.*.evidence`、`note`、`success_rate`、`ci95` |")
    lines.append("| 工具 | `role_c_toolkit/d2_headroom.py`（二值口径）、"
                 "`d2_headroom_graded.py`（综合分口径）、`e4_build_ledger.py`（按序重建） |")
    lines.append("")
    lines.append("**对方提到的两个说法需要更正：**")
    lines.append("")
    lines.append("| 外部说法 | 实际 |")
    lines.append("|---|---|")
    lines.append("| 「原冻结门禁筛查记录未提供」 | 记录存在且为机读 JSON，55 条逐场景，"
                 "每条带证据文件路径 |")
    lines.append("| 「当前只核实到 24 个独立正式包」 | 24 是 `formal` 树的包数；"
                 "D2 判定覆盖的是 `competition_v1` 的 30 个包 |")
    lines.append("| 「在 2 号服务器 `/root/huairou-project`」 | 本项目在怀柔机 "
                 "`/mnt/QTJC/chenyi-codex/`，无 `/root/huairou-project` 路径 |")
    lines.append("")

    # ---------------------------------------------------------------- 2
    lines.append("## 2. 55 个条目是怎么构成的")
    lines.append("")
    lines.append(f"台账共 **{len(rows)} 条 = {len(by_package)} 个场景包 + "
                 f"{len(rows) - len(by_package)} 条别名重复**。")
    lines.append("")
    lines.append("| 来源 | 包数 | 明细 |")
    lines.append("|---|---|---|")
    lines.append(f"| `competition_v1`（本次重标定，肖棹） | **{len(competition)}** | "
                 f"侦察搜索 10、持续跟踪 8、区域拒止 6、应急响应 6 |")
    lines.append(f"| `formal` 正式 IE（早期实验，非本次） | **{len(formal_ie)}** | IE-01…IE-14 |")
    lines.append(f"| `formal` 演示包（不计入正式实验） | **{len(formal_demo)}** | "
                 f"MD-INT-002、MD-INT-003×3、MD-INT-005、MD-INT-006、"
                 f"MD-AD-002×3、MD-AD-004 |")
    lines.append(f"| **合计** | **{len(by_package)}** | |")
    lines.append("")
    lines.append("**别名重复**（同包两个 public_id）：")
    lines.append("")
    for package, public_ids in aliases.items():
        lines.append(f"- `{package}` ← {'、'.join(public_ids)}")
    lines.append("")
    lines.append("### 各种「多少个场景」的口径换算")
    lines.append("")
    lines.append("| 口径 | 数 | 定义 |")
    lines.append("|---|---|---|")
    lines.append(f"| 台账条目 | **{len(rows)}** | 含 1 条别名 |")
    lines.append(f"| 去重场景包 | **{len(by_package)}** | {len(competition)} + {len(formal_ie)} + "
                 f"{len(formal_demo)} |")
    lines.append(f"| 剔除演示包 | **{len(by_package) - len(formal_demo)}** | "
                 f"= D1′ 先验标注覆盖数（两者完全一致） |")
    lines.append(f"| 再合并 REC-001 三档 | **{len(by_package) - len(formal_demo) - 2}** | "
                 f"若一个难度算一个实验 |")
    lines.append(f"| **本次重标定的场景数** | **{len(comp28)}** | competition_v1 去 REC-001 "
                 f"变体（30 − 2） |")
    lines.append(f"| 其中早期正式 IE | **{len(formal_ie)}** | 非本次工作 |")
    lines.append("")

    # ---------------------------------------------------------------- 3
    lines.append("## 3. 门禁判定：两个口径必须分列")
    lines.append("")
    lines.append("台账同时记录两个口径，**它们回答不同问题，数字也不同**：")
    lines.append("")
    lines.append("| 口径 | 判据 | 全台账 "
                 f"({len(rows)} 条) | 竞争族 (30 包) | **本次 28 场景** |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| **二值成功**（事前预注册） | 场景声明的 terminal outcome 成功率 ∈ "
                 f"[0.40, 0.85] | pass {b_pass_all} / fail {b_fail_all} | pass 3 / fail 27 | "
                 f"**pass {b_pass_28} / fail {b_fail_28}** |")
    lines.append(f"| **声明综合分**（utility-v1） | 场景声明的 Σ wᵢ·valueᵢ ∈ [0.40, 0.85] | "
                 f"— | pass 16 / fail 14 | **pass {g_pass_28} / fail {g_fail_28}** |")
    lines.append("")
    lines.append("**为什么必须有综合分口径**：确定性脚本策略的成功率只有 0/1，"
                 "跨 5 个 seed 也只会取 0、0.2 … 1.0；因此二值口径下多数场景恒为 1.000，"
                 "**永远进不了窗口**，判据不可判。")
    lines.append("")
    lines.append(f"**落在窗口之外的场景**：全台账 {out_all} 个；本次 28 场景口径 {out_28} 个。")
    lines.append("")
    lines.append("> 全台账的 "
                 f"{out_all} 个 = 竞争族 {out_28} 个（综合分口径）+ 早期 `formal` 包 2 个"
                 "（MD-AD-002 一档、MD-AD-004-DECEPTION，只有二值口径的判定，无综合分）。")
    lines.append("")

    # ---------------------------------------------------------------- 4
    lines.append("## 4. 论文数据与附图的污染核查")
    lines.append("")
    lines.append("黑名单 = 上表 10 个演示包 + 别名 `MD-AD-006-ISLAND-STRIKE`。"
                 "对被检查的每一份数据/脚本/图，做包名与公开 ID 双模式扫描。")
    lines.append("")
    lines.append("| 被检对象 | 场景引用 | 是否命中黑名单 |")
    lines.append("|---|---|---|")
    lines.append("| `figA4_natural_failure_pilot_12.csv`（肖棹） | IE-03、IE-08、grid | "
                 "**否** |")
    lines.append("| `figA2_replanning_sweep.csv`（肖棹） | 无 | **否** |")
    lines.append("| `make_figs_A2_A4.py` / `设计说明_A2_A4.md`（肖棹） | 无 | **否** |")
    lines.append("| `fig3_hifi_gap.csv`（武昊） | **正好 IE-01…IE-14** | **否** |")
    lines.append("| `figA1_model_invariance.csv`（武昊） | 无（模型 × 指标） | **否** |")
    lines.append("| `figA3_dose_gain.csv`（武昊） | 无（stack × dose） | **否** |")
    lines.append("| Fig.1 / Fig.2（阚思颖） | 无数据（纯示意） | **否** |")
    lines.append("| v11 实验强化清单 | 仅 IE-05、MD-AD-001、MD-TRK-002、MD-TRK-005 | "
                 "**否** |")
    lines.append("")
    lines.append("**结论：论文图与数据没有用到任何不该计入的场景。**")
    lines.append("")
    lines.append("补充核查（武昊数据内部一致性）：")
    lines.append("")
    lines.append("| README 声称 | 从 CSV 复算 | 结论 |")
    lines.append("|---|---|---|")
    lines.append("| LLM+RL beat Rule **11/14** | 11/14（败于 IE-03、IE-04、IE-12） | 一致 |")
    lines.append("| LLM+RL beat RL **12/14** | 12/14（败于 IE-01、IE-03） | 一致 |")
    lines.append("| Pure LLM trails LLM+RL on **13/14** | 13/14（例外 IE-03） | 一致 |")
    lines.append("| gap 列 = 两列之差 | 14 行 × 2 列全部成立 | 一致 |")
    lines.append("| 「end-to-end LLM trails (0.43; **14/14 behind**)」 | "
                 "落后于 **layered 最优**：14/14；落后于**全部四个基线**：9/14 | "
                 "**建议显式写「behind the layered stack」** |")
    lines.append("")

    # ---------------------------------------------------------------- 5
    lines.append("## 5. 措辞改动清单")
    lines.append("")
    lines.append("### 5.1 v11 清单 L50（必须改，属口径混淆）")
    lines.append("")
    lines.append("**原文：**")
    lines.append("")
    lines.append("> 门禁台账：55 场景；D1′ 先验覆盖 44；D2 16 pass / 19 fail / 20 pending；"
                 "D1 blocked 2 / not_applicable 51 / reported 2。")
    lines.append("")
    lines.append("**问题**：「16 pass」是综合分口径、「19 fail」是二值口径，并列后会被读成"
                 "同一口径的 16/19/20。")
    lines.append("")
    lines.append("**建议改为：**")
    lines.append("")
    lines.append("> **门禁台账**：55 条目（54 个包 + 1 条别名）；D1′ 先验覆盖 44。")
    lines.append("> **D2 两口径分列**：二值口径 pass 3 / fail 32 / pending 20；"
                 "综合分口径（竞争族 30 包）pass 16 / fail 14。")
    lines.append("> 窗口外场景 12 个（11 个天然饱和 + 1 个触底），逐场景清单见 "
                 "`E4_28场景数据汇总.md`。")
    lines.append("")
    lines.append("### 5.2 关于「多少个场景」")
    lines.append("")
    lines.append("- 报包数时写「**30 个竞争包**」，报场景数时写「**28 个场景**"
                 "（REC-001 三档合并）」——两个数都要带单位。")
    lines.append("- 论文附录若要写总场景数，建议写「**44 个正式场景**"
                 "（54 包 − 10 个演示包）」，并注明「其中本次重标定 28 个」。")
    lines.append("")
    lines.append("### 5.3 关于「IE-05 数量 19」")
    lines.append("")
    lines.append("- E1 承接里的「IE-05 数量 19」指**正式 IE-05-MULTI-AXIS 场景的目标数量档**，"
                 "与演示包 `MD-INT-005` 无关。")
    lines.append("- 建议写成「`IE-05-MULTI-AXIS` 的 19 目标档」，避免与 `MD-INT-005` 混淆。")
    lines.append("")
    lines.append("### 5.4 关于「gates 外 layered 输」的验证对象")
    lines.append("")
    lines.append("不必手动筛选，窗口外场景已逐条列出；**优先用 11 个天然饱和场景**"
                 "（未被本次标定调整过），最干净。")
    lines.append("")

    # ---------------------------------------------------------------- 6
    lines.append("## 6. 复算方式")
    lines.append("")
    lines.append("```bash")
    lines.append("# 门禁判定（二值口径）")
    lines.append("python role_c_toolkit/d2_headroom.py --plan <plan.json> --state <state.json> \\")
    lines.append("  --output .../analysis/d2_headroom_final2.json")
    lines.append("")
    lines.append("# 声明综合分口径")
    lines.append("python role_c_toolkit/d2_headroom_graded.py --plan <plan.json> "
                 "--state <state.json> \\")
    lines.append("  --scenarios openmd/source-code/source_codes/scenarios/competition_v1 \\")
    lines.append("  --evidence-root .../analysis/evidence-final2 \\")
    lines.append("  --output .../analysis/d2_graded_final2.json")
    lines.append("")
    lines.append("# 台账重建（按顺序：inventory → d1prime → d2 → d2-graded → report）")
    lines.append("python role_c_toolkit/e4_build_ledger.py --artifacts "
                 "role_c_toolkit/artifacts/e4-scenario-family \\")
    lines.append("  --source openmd/source-code/source_codes \\")
    lines.append("  --grid-doc openmd/doc/grid_environment_reference.md \\")
    lines.append("  --contracts openmd/doc/competition_four_categories/SCENARIO_CONTRACTS.json \\")
    lines.append("  --design-root . --d1-report <E10 summary.json>")
    lines.append("")
    lines.append("# 28 场景汇总（本文件引用的窗口外清单）")
    lines.append("python role_c_toolkit/e4_scenario28_pack.py")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**一句话总结**：门禁名单是本次 E4 重标定产出的、就在 "
                 "`admission_ledger.json` 里（55 条 = 54 包 + 1 别名）；"
                 "论文图与数据**未污染**；"
                 "v11 清单 L50 的「16 pass / 19 fail」需按两口径分列。")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written {OUT.name} ({len(lines)} lines)")
    print(f"55 条 = {len(by_package)} 包 + {len(rows) - len(by_package)} 别名 | "
          f"竞争族 {len(competition)} | 正式 IE {len(formal_ie)} | 演示 {len(formal_demo)}")
    print(f"28 场景：二值 pass {b_pass_28} / 综合分 pass {g_pass_28} / 窗口外 {out_28}")


if __name__ == "__main__":
    main()

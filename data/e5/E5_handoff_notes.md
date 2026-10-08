# E5 交接说明（DSH 会话，2026-10-02）

Claude Code 会话 `97d1b75b-e1c5-4e95-8126-0acab23c7a0b`（`~/.claude/projects/C--Code-source-code/`）在 2026-10-02 20:16 之后连续三次"继续"都返回
`No response requested.`，实际工作停在"等 IE-08 s5104 最后一个对照"。本文件记录交接时的状态，便于任何 agent 或人接着做，不必再翻会话记录。

## 1. 会话的长期目标

`/goal` 设过：**持续跟进 E5 任务**，直到归因全部完成并交付汇总。

E5 = 清单 v4 §3 "自然故障盲归因 pilot"：用真实失败局验证论文 §5.1 的反事实归因方法在**未知故障**上的可用性，
由未参与归因的合作者独立标注故障层，算 Cohen's κ；成功判据 **κ ≥ 0.6 且不一致案例 ≤ 2 且可解释**。

协议（开跑前写进 `plan.json`，事后不得改）：

- 样本：IE-03/04/08 的 LLM+RL 新种子 5101–5112（36 局）+ grid medium/continuous LLM+rule 新种子 5201–5212（12 局）。
- 判负：单局防守方评分 < 0.6。
- 选样：按种子顺序取前 9 个高保真失败局 + 前 3 个 grid 失败局。
- 归因：自身回放门禁 → 冻结 LLM 目标换规则执行（ΔE）→ 换规则规划（ΔP）→ 全规则（ΔI）；
  标签取 ΔP、ΔE、|ΔI| 最大者，前两者差 < 0.05 记均衡，最大者 < 0.05 记无法判定。

## 2. 交接时的服务器状态（`/mnt/QTJC/chenyi-codex/experiments/`）

| 内容 | 目录 | 状态 |
|---|---|---|
| 高保真第 1 轮 | `e5-hifi-natural-failures-20261001T1920Z/` | `blocked_too_many_failures`，11 局完成（预期内，样本已够） |
| 高保真续跑 r2 | `e5-hifi-natural-failures-r2-20261002T0220Z/` | 36/36 局完成；`status=running` 只因还有 2 个**非入选**案例在做对照 |
| IE-08 s5101 补跑 | `e5-hifi-attribution-r3b-20261002T0715Z/` | 完成，标签接口 |
| grid | `e5-grid-natural-failures-20261002T0640Z/` | 完成，12 局 / 6 失败 / 选 3 |
| 盲标包 | `e5-annotation-final-20261002T1230Z/` | 12 案例 + KEY + selection.json，待发 |
| 旧记录回放验证 | `e5-hifi-record-validation-20261001/` | IE-08 s31，1056 tick 逐帧一致 |

**入选的 12 个案例与机器标签**（全部 `replay_gate.exact_match = true`）：

- IE-03：s5101 规划、s5102 规划、s5104 执行、s5105 接口
- IE-08：s5101/s5102/s5103/s5104/s5105 全部接口
- grid：s5201 规划、s5202 接口、s5204 接口

合计：接口 7、规划 3、执行 1、均衡 0（均衡那个 s5106 是 IE-03 的第 5 个失败局，按选样规则未入选）。

仍在跑的两个非入选案例：`ie-08-island-strike__llm-rl__s5109`、`s5112`（12:31 UTC 仍在写 `reference_full`）。
它们不参与 E5 选样与 κ，留着只是让"全种子对局记录"更完整。E5 任何一步都不依赖它们。

## 3. 本地交付物

- `role_c_toolkit/artifacts/paper-E5-natural-failures/E5_结果汇总.md`（12/12 最终版）
- `role_c_toolkit/artifacts/paper-E5-natural-failures/annotation-final/`（28 个文件，与服务器逐文件 SHA-256 一致）
- 反向参照：`$HOME\Downloads\给老师_E4_E8_E9执行困难说明.md`（19:22 已交付）

## 4. 剩余的唯一阻塞项

人工盲标。**不能由归因工具作者代填**（清单与论文口径都要求独立标注人）。
发 `annotation-final/packets/` 给合作者（不要发 `KEY_DO_NOT_SHARE.json`、`selection.json`），
收回 `annotation_form.csv` 后按 `E5_结果汇总.md` §7 的命令算 κ。

主要风险（已写进汇总 §5.1）：IE-08 的"接口"标签来自"两层单独换都没用、两层一起换才变好"，
人工标注人可能判成"规划"或"均衡"，κ 有偏低风险；若 κ < 0.6 应按清单如实报告并讨论归因边界。

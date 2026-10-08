# D2 headroom 预注册与执行记录（E4 场景族入场门）

> 状态：**预注册已冻结，seed 2001 小样执行中**
> 工具：`tools/competition_four_categories/calibration_matrix.py`（项目自带，未修改）
> 计划文件：`calibration-plan-20261003T065614097894Z.json`（SHA-256 见文末）

## 1. 目标与判据

D2（headroom，`openmd/doc/hifi_requirements.md` §1 一票否决约束）：

> 每个主实验场景，**最优 pure 基线 SR ∈ [40%, 85%]**。

- **来源**：`ScenarioPackage` 原生终局，`terminal.outcome == "objective_complete"` 记为成功；
  非终局/被中止的对局记为**不可用**并从分母剔除（不当作失败）。
- **抽样单位**：seed。区间为 seed bootstrap 95% CI（10000 次重抽样，RNG 种子 20261003）。
- **判定**：每个场景取"最优纯基线策略"的成功率；落在 [0.40, 0.85] 记 `pass`，
  低于 0.40 记 `fail`（触底无对比空间），高于 0.85 记 `fail`（饱和无 headroom）。
- **粒度说明（必须写进论文）**：成功率是 seed 的分数，5 seeds 下只能取 0.0/0.2/0.4/0.6/0.8/1.0。
  因此可判通过的只有 0.4/0.6/0.8 三档；区间会跨越阈值。**报告必须给成功率与区间，不能只给判定**。

## 2. 种子选择（在看到任何结果之前冻结）

- 规则：**≥2001 的前 5 个未使用整数**，按其自然顺序进入批次。
- 选定：**2001、2002、2003、2004、2005**。
- 依据：工具 `prepare()` 扫描既有 `artifacts/competition_four_categories/*.json` 与历史计划，
  拒绝重复种子；已占用区间在 1901–1905（AD006 三类基线标定）与 1701（不变性采集），
  2001 起无占用（已核验）。
- **本批与旧 300 局（seeds 1201–1205）不是同一版本**，两批**禁止拼接统计**；
  本批是当前引擎版本上的独立标定批次。

## 3. 每个 seed 的案例构成（60 例 / seed，覆盖 28 个场景）

| 场景族 | 场景数 | 每 seed 案例 | 策略对 |
|---|---|---|---|
| MD-REC-001（三档难度） | 1 | 6（easy/medium/hard × A/B） | `idle`（地板控制）/ `sweep`（任务相关基线） |
| MD-REC-002…008 | 7 | 各 2 | `sweep` / `coordinated`（REC-006 为 `observation-patrol`） |
| MD-TRK-001…006 | 6 | 各 2 | `follow` / `allocated` |
| MD-TRK-007/008 | 2 | 各 2 | `report-honest`+`identity-honest` / `beacon-honest`+`coverage-honest` |
| MD-AD-001…006 | 6 | 各 2 | `indiscriminate`（地板控制）/ `guard` |
| MD-ER-001/002/004 | 3 | 各 2 | `direct` / `safe`、`team`、`preissued` |
| MD-ER-003/005 | 2 | 各 2 | `naive`（地板控制）/ `coordinated` |
| MD-ER-006 | 1 | 2 | `watch-coordinated` / `progress-watch` |

**地板控制策略**（`idle`、`indiscriminate`、`naive`）不参与"最优纯基线"的挑选，
但如果某场景**只有**地板控制有数，则该场景记 `not_evaluable` 并在台账里注明，
不得把触底当成 headroom 通过。

**口径边界**：清单 v5 把 D2 描述为"2×2 锚点（rule/LLM planner × heuristic 执行）"，
`hifi_requirements.md` 写的是"最优 pure 基线"。本批采用**已冻结的逐场景任务相关纯基线**
（即上表的 B 侧策略），因为它复用项目既有验证入口、可在当前版本重现；
**不声称**等价于 2×2 锚点标定。若主理人要求后者，需要另建工具与另立批次。

## 4. 执行协议（工具自带，不得绕过）

1. 严格 seed-major：一个 seed 的 60 例跑完才进入下一个 seed。
2. 每个案例单独子进程，900 秒硬超时；超时不自动重试，先核对 PID 与日志。
3. 每例落盘原生报告（`evidence`）并校验 trace 摘要与终局一致性。
4. 运行前后比对冻结输入哈希（工具源码 + catalog + 场景包）；漂移即判该批无效。
5. 保护门 `protected_inputs.verify()` 每例前后各查一次。

## 5. 成本实测（seed 2001 小样，已完成）

| 指标 | 数值 |
|---|---|
| 案例数 | 60（28 个场景） |
| 单例耗时（中位 / 最慢） | **36 s / 351 s** |
| seed 总时长（串行，工具协议） | **2993 s ≈ 50 分钟** |
| 失败案例 | **0**（`execution_error` 0、无 900 s 硬超时） |
| 外推 5 seeds | 串行 ≈ 4.2 小时；**每 seed 各建一个 plan 并行 → 墙钟 ≈ 50–60 分钟** |
| 存储 | 每个 seed 约 60 个 evidence JSON + 60 个日志（量级 MB） |

**结论**：成本可控，工具链无缺陷；**并行方案是把 5 个 seed 拆成 5 个独立 plan**（锁按 plan 分文件，
互不阻塞），单 plan 内仍严格 seed-major。

## 5b. seed 2001 的实测结果（必须如实记录）

| 观测 | 数值 |
|---|---|
| 场景数 | 28 |
| 基线成功率 = 1.00（**饱和**） | **25** |
| 基线成功率 = 0.00（**触底**） | **3**（MD-AD-006、MD-REC-008，两策略均 `rule.timeout`） |
| D2 判据 [0.40, 0.85] 通过 | **0 / 28** |

**这不是缺陷，而是标定口径的结论**：竞争族 28 个场景是**参赛基础场景**，任务相关的基线策略
（sweep / coordinated / guard / follow / allocated / safe / team / preissued / progress-watch …）
在**单 seed 下已经能完成目标**，因此没有 headroom。与之对照，`COMPETITION_ACCEPTANCE_REVIEW_20261001.md`
独立给出了同一判断："合理单档或有效校准的难度档位——**未充分证明**；单策略单 seed 不足以证明非饱和难度分布"，
并把"采集预注册的当前版本多 seed、三类基线与难度分布"列为后续优先级 4。

**结构性限制（影响判据可判性）**：成功率是 seed 的分数，**5 seeds 只能取 0.0/0.2/0.4/0.6/0.8/1.0**，
即只有 0.4/0.6/0.8 能落在 [0.40, 0.85] 内。因此：
- 单 seed 探针**永远不可能**判 pass（只能 0 或 1）——本节的 0/28 是预期的；
- 5 seeds 下若某策略 5/5 成功仍是 1.0 → fail；**要判 pass，必须存在恰好 2–4 次成功的策略**。
- 换言之：D2 在这批场景上能否通过，取决于"是否存在难度适中的场景"，而不取决于跑多少 seed。

**两个真实设计问题（需主理人知悉）**：

1. **地板控制策略在若干场景上得分 = 1.0**（MD-AD-001/002/004 的 `indiscriminate`、MD-ER-003 的 `naive`）。
   说明这些场景**没有区分"任务相关基线"与"乱打/不作为"**，属于区分度不足，印证评审文档"实际区分度未充分证明"。
2. **MD-REC-008 的两个策略标注不一致**：合同写 `coordinated`，实际运行 `sweep`（两例都超时）。
   需要在后续批次前与该工具维护者确认口径。

**下一步需要你决定**（本批只跑了 1 个 seed，其余 4 个未跑）：

| 选项 | 含义 | 代价 |
|---|---|---|
| A. 只跑到此为止 | 台账 D2 列写"单 seed 探针，25/28 饱和"；按清单如实报告 D2 未通过及其原因 | 0 |
| B. 补跑 4 个 seed（并行 ≈ 1 小时） | 把"饱和"从单 seed 观测变成 5-seed 结论，得到 seed-bootstrap 区间；预计结论不变（饱和） | 1 小时墙钟 |
| C. 先改场景难度再跑 | 按评审文档优先级 4 重标定（要动场景包，超出"不实现算法"边界） | 需主理人决策 |

我的建议：**B**。理由是 5 seeds 才能给出区间、才能把"饱和"写成可发表的结论；而且成本已实测只有约 1 小时。

## 6. 失败与边界处理

| 情况 | 处理 |
|---|---|
| 单例 900 秒超时 | 记 `observation_timeout`，核对 PID/日志；该例从 D2 统计剔除并披露 |
| 某场景全部 seed 失败 | SR = 0 → `fail`（触底），如实报告，不改判据、不换种子 |
| 某场景部分 seed 不可用 | 按可用 seed 计算，同时报告可用数 |
| 冻结输入漂移 | 该批作废，保留失败记录，重新预注册新种子 |
| 结果不利于判据 | **不改判据、不删案例、不换策略**；按 §1 如实记 fail |

## 7. 复算命令

```bash
# 生成计划（一个 seed 一个 plan）
python -m tools.competition_four_categories.calibration_matrix --prepare-seeds 2001
# 执行（可反复调用，内部按 seed-major 推进，单次上限 8 例）
python -B -m tools.competition_four_categories.calibration_matrix \
  --run-plan artifacts/competition_four_categories/calibration-plan-<stamp>.json --max-cases 8
# 分析（本地或服务器均可，只读）
python role_c_toolkit/d2_headroom.py --plan <plan.json> --state <plan.state.json> \
  --output analysis/d2_headroom.json --csv analysis/d2_per_case.csv
```

## 8. 产物清单

| 内容 | 路径 |
|---|---|
| 计划 | `artifacts/competition_four_categories/calibration-plan-20261003T065614097894Z.json` |
| 状态 | 同名 `.state.json` |
| 逐例原生报告 | `artifacts/competition_four_categories/<case>-<stamp>.json` |
| 逐例日志 | `artifacts/competition_four_categories/calibration_runs/<plan-stem>/<case>.log` |
| D2 判定 | `role_c_toolkit/artifacts/e4-scenario-family/analysis/d2_headroom.json` |
| 台账回填 | `admission_ledger.json` 的 `D2_headroom` 列 |

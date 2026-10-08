# 实验 2（P2 导出）：规划信息效应与跨族配对

> 数据来源：E1 campaign `bundle/data/gate-screening/`（已冻结）；
> 臂 `rule-strong-g1` vs `rule-strong-g0`——**同一剂量（均为 `dose=strong`）、同一执行器**，
> 差异是 `config.greedy`（`true`/`false`），即**规划器的分配决策规则**。
> ⚠️ 因此本节衡量的是**决策形态**，不是信息量。信息量对照见选项 2。
> 置信区间：`d2_headroom.bootstrap_ci`（10000 draws, seed 20261003）。

## 1. 分配规则效应（族内，可解释）

| 条件 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI | 显著 |
|---|---|---|---|---|---|---|
| COUNT-IE-05-MULTI-AXIS-N017 | 10 | 0.8912 | 0.7850 | **+0.1062** | [0.015, 0.254] | ✅ |
| COUNT-IE-05-MULTI-AXIS-N018 | 10 | 0.8544 | 0.8422 | **+0.0122** | [-0.027, 0.046] | — |
| COUNT-IE-05-MULTI-AXIS-N019 | 10 | 0.8693 | 0.7773 | **+0.0920** | [-0.008, 0.247] | — |
| COUNT-IE-05-MULTI-AXIS-N027 | 10 | 0.8469 | 0.7482 | **+0.0987** | [0.013, 0.224] | ✅ |

2 / 4 个条件的 95% CI 不含 0——分配规则差异本身可测。

## 2. 跨族配对（P2，仅报告不解释）

| 行 | 场景/条件 | 最优纯基线 | V / composite | 族与执行器 |
|---|---|---|---|---|
| **饱和** | MD-TRK-004 | `allocated` | **0.9666** [0.963, 0.971] | competition_v1 (scripted tracking policies) |
| **非饱和** | COUNT-IE-05-MULTI-AXIS-N017（greedy=true） | rule | 0.8912 | IE-05 数量族（另一执行器） |
| **非饱和** | COUNT-IE-05-MULTI-AXIS-N027（greedy=false） | rule | 0.7482 | IE-05 数量族（另一执行器） |

## 3. 必须随表引用的限制

1. **两行不共享任务族与执行器**：饱和行来自竞争族脚本跟踪策略，非饱和行来自 E1 的 IE-05 数量族。
2. **交互项不可解释**：因此本导出**不给出差中差**；headroom 的因果性由 §6.7 的跨族对比承接。
3. **族内 headroom 跨度不足**：E1 全部 38 个数量档中纯基线 V 仅在 0.748–0.891 区间，不构成「饱和 vs 非饱和」两行。
4. **操纵是 goal dose**，不是 LLM 规划器：本导出的对象是「是否提供目标信息」，与 v1 设计中的 LLM/RL 栈无关。

## 4. 可直接引用的英文措辞

> Holding the planner and executor fixed and supplying goal information raises
> utility by +0.106 (95% CI [0.015, 0.254])
> on the IE-05 quantity sweep. The headroom interaction could not be formed on a
> single executor within this family, so condition (iii) rests on the
> between-family contrast in §6.7 rather than on a within-family 2x2.


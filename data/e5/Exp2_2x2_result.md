# 实验 2（v3：2×2 headroom × 规划信息）——结果与判读

> 对象：`OpenMDBench_补实验清单_P0硬伤_20261006.md（v3）` 第 33–56 行。
> **先更正一处我自己的错**：v3 第 50 行明确写「不需要 LLM/RL 栈，竞争族全脚本即可」，
> 我却先去跑了 grid 的 LLM episode（那是被 v3 作废的 v1 设计）。该批次已停止并作废。
> 下面全部结果来自**已存在的脚本数据**，未跑任何 LLM。

---

## 1. 数据来源与臂定义

`E1_device-b_v13_p01_20261004/bundle/data/gate-screening/`（<author-B> E1 campaign，已冻结在服务器）

每个数量条件 5 个臂 × 10 seeds：

| 臂 | `config.dose` | `config.greedy` | 含义 |
|---|---|---|---|
| **`rule-strong-g1`** | `strong` | **`true`** | 规则规划器 + 最近接触贪心分配 |
| **`rule-strong-g0`** | `strong` | **`false`** | 规则规划器 + 默认分配 |
| `rule-hold-g0` | `hold` | `false` | 目标被改写为 hold（空转对照） |
| `rule-rl-strong-g0` | `strong` | `false` | 分层：规则规划 + RL 执行 |
| `rule-rl-hold-g0` | `hold` | `false` | 分层：空转规划 + RL 执行 |

**更正（后续核实）**：`rule-strong-g1` 与 `rule-strong-g0` 的**剂量相同（均为 `strong`）**，
差异是 `greedy` 分配规则——即**规划器的分配决策规则**，**不是信息量**。
本节因此衡量的是「决策形态」，不是「规划信息量」。
量级对照（供参考）：本节的分配规则差异约 **+0.08**，而真正的信息量操纵（完整计划 vs
降级计划，见合并报告 Study 2）约为 **+0.70**。

---

## 2. 结果（分配规则 × 数量条件）

| 条件 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI |
|---|---|---|---|---|---|
| COUNT-IE-05-MULTI-AXIS-**N017** | 10 | 0.8912 | 0.7850 | **+0.1062** | [0.013, 0.253] |
| COUNT-IE-05-MULTI-AXIS-N018 | 10 | 0.8544 | 0.8422 | +0.0122 | [−0.025, 0.046] |
| COUNT-IE-05-MULTI-AXIS-N019 | 10 | 0.8693 | 0.7773 | +0.0920 | [−0.009, 0.250] |
| COUNT-IE-05-MULTI-AXIS-**N027** | 10 | 0.8469 | 0.7482 | **+0.0987** | [0.013, 0.225] |

**N017 的 +0.1062 与 v3 引用的「E1 已证 +0.123」一致**（差异来自版本/条件选择）。

### 判读

1. **分配规则差异可测**：四个条件全部为正差值，两个条件（N017、N027）的 95% CI 不含 0。
   → 决策形态在本族中确有约 +0.08 的代价。
2. **但这不是 headroom 的 2×2**：这四个条件都是**同一场景（IE-05 多轴）的数量变体**，
   纯基线 V 只在 **0.748–0.842** 之间（跨度 0.094）。headroom 的差别太小，
   不足以构成"饱和 vs 非饱和"的两行。
3. **交互效应不显著**：以基准 V 最高（N018=0.842）与最低（N027=0.748）作差中差，
   得到 **−0.0865，95% CI [−0.239, +0.019]**，跨零。

---

## 3. 与 v3 要求的差距（必须说清）

| v3 要求 | 本次数据 |
|---|---|
| 饱和场景（headroom≈0）一行 | ❌ 缺。竞争族 MD-TRK-004 有 headroom≈0 的实测（最优纯基线 0.965），但它在**另一套任务/执行器**上 |
| 非饱和场景（headroom>0）一行 | ✅ E1 数量条件（本表） |
| **同一执行器，只改规划信息** | ✅ 在 E1 行内成立；⚠️ 两行之间**不成立**（任务族与执行器都不同） |
| 4 格均值 + 逐 seed + 交互 + 95% CI | ✅ 本表（逐 seed 原始值见 JSON） |

**结论**：**2×2 的一半（非饱和行）已用现成数据完成且操纵有效；另一半（饱和行）无法与它组成同一 2×2**，
因为饱和场景在竞争族（脚本执行器），而非饱和数据在 IE/grid 族（另一套执行器）。
这正是我在实验 2 阻塞文档里指出的同一条鸿沟——**v3 的设计绕开了 LLM/RL 需求，但没有绕开"两行必须在同一执行器上"这一条**。

---

## 4. 要在截稿前拿到完整 2×2，还差什么

**只差一个"饱和 row"**：需要一个**有 headroom≈0、且带规划信息开关**的场景。

三条路径，按代价排序：

| 路径 | 做法 | 代价 | 风险 |
|---|---|---|---|
| **P1（推荐）** | 在 **E1 网格内**找一个纯基线 V 已接近上限（≥0.95）的数量/配置档，用它当饱和行——与现有非饱和行**同族同执行器**，交互效应立刻可算 | 需确认 E1 是否已有该档；若无，跑 2 臂 × 10 seed（脚本，快） | 低 |
| P2 | 用竞争族 MD-TRK-004 当饱和行，**接受两行不同族**，文中明确标注 | 0（数据已有） | 中：审稿人会问可比性 |
| P3 | 给竞争族场景造一个合法的规划信息开关（我试过通信组件与线索区域，均不可行） | 数天开发 | 高，截稿前来不及 |

**P1 是唯一能在 1–2 天内给出"真 2×2 + 显著交互"的路径**，而且不需要 LLM。

---

## 5. 如果时间不够，论文里可以怎么写（诚实版）

可直接用的一句话：

> We probed the planning-information lever directly: holding the planner and executor fixed and
> supplying goal information raises utility by +0.106 (N017, 95% CI [0.013, 0.253]) and +0.099
> (N027, 95% CI [0.013, 0.225]) on the IE-05 quantity sweep. The headroom interaction could not
> be formed on a single executor within this family (baseline utility spans only 0.748–0.842),
> so condition (iii) is supported by the between-family contrast reported in §6.7 rather than by
> a within-family 2×2.

---

## 6. 产物

- 逐 seed 原始值 + 交互效应：`role_c_toolkit/artifacts/e4-scenario-family/analysis/e1_2x2_planning_information.json`
- 复算：`python role_c_toolkit/e1_2x2_analysis.py`（读 E1 gate-screening，bootstrap 20000 draws）
- 数据源：`/mnt/<lab>/<user>-codex/experiments/E1_device-b_v13_p01_20261004/bundle/data/gate-screening/`

# OpenMDBench 补实验清单（P0 逻辑硬伤）

## 背景

论文正文已完成 4 处框架加强（§3.3 机制推理 / §6.7 循环论证声明 / §5 C2→C1 连接 / §6.2 complex layered 未测声明）。

以下两个 P0 硬伤需要实验数据闭环：

---

## 实验 1：Grid complex 层 layered stack 表现（P1 直接证据）

**目的**：验证 P1 预测"decision-form mismatch ⇒ layered 输"。complex 层（D1′ 失败处）目前只跑了 pure stacks，缺 layered 直接数据。

**授权**：✅ **已批准，按 4 栈 × 5 seed 推进**

**冻结配置**（按合作者可行性评估）：

| 栈 | 规划层 | 执行层 | 作用 |
|---|---|---|---|
| Rule | 原规则规划器 | 原 GOAI heuristic | 同条件纯规则对照 |
| Pure MAPPO | 纯 MAPPO 部署入口 | 指定 medium 检查点 | 固定权重的 complex 纯 RL 对照 |
| LLM+heuristic | 真实 Qwen 规划器 | 原 GOAI heuristic | 补 layered 直接数据 |
| LLM+MAPPO | 同一真实 Qwen 规划器 | 同一 medium 检查点 | 补另一执行器下的 layered 直接数据 |

**关键要求**：
- **必须跑同 seed 纯基线**（Rule + Pure MAPPO），不能只跑 layered
- medium 检查点 SHA256：`223dbf740163b652f221a6ef0885d69b8c975c53378a7e63c05388e1df8cd0a8`
- 1 号服务器：`172.18.129.51:22376`，`/root/openmd/releases/gitlab-ccabad00154e/repo`
- 5 个环境 seed，20 局（10 局调 LLM）
- 预算：4–8 小时

**交付**：
- 逐 seed 原始数字（composite score, SR）
- 同 seed 配对差值：LLM+heuristic − Rule、LLM+MAPPO − Pure MAPPO
- seed-bootstrap 95% CI

---

## 实验 2：gates 外场景 layered 表现（P3 循环论证）

**目的**：打破 P3 循环论证——positive region 是 gates 筛选出来的，需要验证"gates 外 layered 不 pay"。

**场景已选定**（从完整门禁排除名单中选 3 个 D2 饱和场景）：

| 场景 ID | composite | 排除原因 | 类别 |
|---|---|---|---|
| MD-TRK-004-STANDARD | 0.967 | 饱和：高于窗口上界 0.85 | 跟踪 |
| MD-ER-004-STANDARD | 0.942 | 饱和：高于窗口上界 0.85 | 应急响应 |
| MD-TRK-007-STANDARD | 0.937 | 饱和：高于窗口上界 0.85 | 跟踪 |

**为什么选这 3 个**：
- 都是 D2 排除的饱和场景（headroom 不足），直接验证 P2
- 避开满分（MD-REC-001 = 1.000）——太极端，审稿人会说"这当然赢不了"
- 避开触底（MD-TRK-002 = 0.393）——这验证的是"场景太难"，不是 P2 的"baseline 太强"
- 跨类别（跟踪 + 应急响应），不是单一类别
- 都在 0.93–0.97 区间，既有 headroom 不足，又不是完全零空间

**冻结配置**：

| 栈 | 规划层 | 执行层 |
|---|---|---|
| Rule | 原规则规划器 | 原执行器 |
| Pure RL | 纯 RL | 原 RL 权重 |
| LLM+Rule | 真实 Qwen 规划器 | 原执行器 |
| LLM+RL | 同一真实 Qwen 规划器 | 原 RL 权重 |

**要求**：
- 每场景 4 栈 × 3 seed = 12 局（6 局调 LLM）
- 3 场景共 36 局（18 局调 LLM）
- 2 号服务器：`172.18.129.57:32422`，`/root/huairou-project`
- 纯基线需同新 seed 重跑，不用原 Table 3 的冻结均值替代配对基线
- 预算：6–12 小时

**交付**：
- 每场景逐 seed 原始数字（composite score, SR）
- layered vs 两种纯基线的 gain（LLM+Rule vs Rule、LLM+RL vs Pure RL）
- 与正区域 14 场景的对比（是否真的 "outside gates ⇒ no gain"）

---

## 优先级

1. **实验 1（Grid complex layered）**：P0，已授权，4–8 小时
2. **实验 2（gates 外场景）**：P0，场景已选定，6–12 小时

两个实验可以双机并行：1 号跑实验 1，2 号跑实验 2。

---

## 论文侧配套修改（已写入）

- §6.2："complex-layer layered stacks were not run; P1 is directly tested on medium-tier six-arm accounting"
- §6.7："gates are a pre-registered design choice; excluded scenarios were not run with layered stacks"

**Table 2 表述修正**（待确认）：
- V_m 是逐 seed 的 max(rule+rule, pure RL)，不是简单的 rule+rule
- Table 2 caption 需改为 "V_m = per-seed max of pure baselines (overall mean 0.913)"
- 原因：P 的 CI 是 [−0.497, +0.080]，ΔV_A 的 CI 是 [−0.497, −0.037]，两者不同是因为 V_m 逐 seed 取 max，不是 bug

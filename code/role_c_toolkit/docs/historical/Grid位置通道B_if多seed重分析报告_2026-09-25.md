# Grid 原生离散位置通道 B_if 多 seed 重分析

日期：2026-09-25。输入为既有 `grid-campaign-20seed-v1`（grid medium，rule planner × heuristic executor）；该报告是已完成轨迹的预先锁定新投影重分析，不是前瞻性预注册，也不等价于 full structured B_if、连续 KSG 或混合 LLM 架构结论。

## 核心发现

1. 全部 180 个 seed×task_mode×interval 原始报告和自身重放通过新审计器的 hash、配置、引擎源清单及 `exact_match` 校验，审计 `errors=[]`。每个条件保留 20 个 seed，每单位逐 seed 计算 `I(Goal_type/target_cell; own_post_position)` 有限离散 plug-in MI，按 seed 汇总 95% bootstrap 区间。
2. **task_mode 操纵对目标—己方位置通道没有可观测响应。** 同一个 seed、间隔下，independent、sequential、continuous 的活跃 Goal、己方 pre/post 状态、动作、goal reports 和 done 序列在 **60/60 个 triplet** 中完全一致。三种 task_mode 的 B_if 投影数值因此完全重复；这不是三份独立操纵证据。此批 rule 环境运行没有为这条通道提供 C_info/Goal-mode 梯度。
3. 重规划间隔 5/10/20 的位置通道 MI 描述均值与 seed 间区间见下表。各相邻 interval 的 20-seed 配对差区间均跨零，且操纵对象是 planner interval，不是 Goal 字段粒度；不得将它们称为 D3 通过或接口预算定律验证。
4. plug-in 离散 MI 的单 seed 联合格点 singleton 比例平均约 0.56–0.66；这是明显的有限样本稀疏风险。跨 seed bootstrap 只量化 seed 间波动，不校正 plug-in 上偏或 episode 内时间依赖。循环 shift 仅为时序对齐诊断，不是 p 值/去偏器。

## 口径

- X：每转移、每个己方单位，在执行前选择最高 priority active Goal；类别为 Goal type、target-position 存在标记及精确 grid `(x,y)`；无 Goal/无位置显式作为类别。忽略 task_id、issued_at 和下游动作。
- Y：相同单位执行后的 `(alive,x,y)`，死单位为单独类别；不跨单位合并。
- 估计量：native finite-grid discrete empirical plug-in `I(X;Y)`，bits；无偏差修正、不裁剪；每 seed 每 unit 计算，再以 seed 为重抽样单位做 10,000 次 percentile bootstrap。
- 时间位移：每轨迹使用最多 31 个非零循环位移，报告观察 MI 减 shift 平均；仅是依赖诊断。
- 全量 provenance 与每 seed 数值在 `artifacts/grid-position-bif-s100-119-v3/analysis.json`，代码为 `analyze_grid_bif_position_channel.py`，测量口径为 `grid位置通道B_if重分析方案_2026-09-25.md`。

## 按单位与重规划间隔的 seed 统计

每个 interval 的结果对三种 task_mode 完全相同，以下只列一次。均值及 95% CI 为 20 个 seed 的逐 seed plug-in MI 均值 bootstrap；shift-adjusted 均值只作诊断。

| Unit | Interval | Mean MI (bits) | Seed SD | 95% seed-bootstrap CI | Shift-adjusted mean | Mean joint singleton fraction |
|---|---:|---:|---:|---:|---:|---:|
| blue_0 | 5 | 0.698 | 0.225 | [0.606, 0.797] | 0.199 | 0.656 |
| blue_0 | 10 | 0.570 | 0.319 | [0.430, 0.704] | 0.064 | 0.566 |
| blue_0 | 20 | 0.651 | 0.222 | [0.554, 0.740] | 0.141 | 0.558 |
| blue_1 | 5 | 0.915 | 0.256 | [0.809, 1.027] | 0.071 | 0.656 |
| blue_1 | 10 | 0.923 | 0.332 | [0.782, 1.068] | 0.125 | 0.614 |
| blue_1 | 20 | 0.934 | 0.303 | [0.806, 1.061] | 0.170 | 0.624 |
| blue_2 | 5 | 0.794 | 0.189 | [0.712, 0.874] | -0.008 | 0.643 |
| blue_2 | 10 | 0.792 | 0.209 | [0.704, 0.881] | 0.023 | 0.566 |
| blue_2 | 20 | 0.827 | 0.236 | [0.722, 0.922] | 0.125 | 0.603 |

interval 5−10、10−20、5−20 的 seed-paired 差值区间分别为：

| Unit | 5−10 mean [95% CI] | 10−20 mean [95% CI] | 5−20 mean [95% CI] |
|---|---:|---:|---:|
| blue_0 | 0.127 [-0.047, 0.298] | -0.080 [-0.237, 0.088] | 0.047 [-0.098, 0.199] |
| blue_1 | -0.008 [-0.188, 0.168] | -0.011 [-0.162, 0.151] | -0.019 [-0.199, 0.156] |
| blue_2 | 0.002 [-0.102, 0.103] | -0.035 [-0.155, 0.102] | -0.033 [-0.139, 0.086] |

## 解释与后续

该重分析给出了 grid 的一个明确有限离散位置投影和跨 seed 方差，但它的偏差、singleton 稀疏及时间依赖未解决，不能替代论文预期 KSG/full `B_if`。更直接的 construct-validity 结果是 task_mode 变化没有改变己方 Goal/执行轨迹字段；应核查为何所谓跨域耦合任务模式在这组 seed 与 rule policy 上没有触发己方行为差异，再建立新的、确实操纵 Goal-stream 粒度的设计，单独留出未分析 seeds。

此批数据没有 Goal weak/medium/strong 因子，因此不能用于 D3 梯度；也没有 LLM planner 或 GOAI hybrid，因此不能作为目标架构证据。vLLM 高保真实验、IE-01–IE-08 的真实 hybrid B_if 与归因注入门禁均仍未完成。

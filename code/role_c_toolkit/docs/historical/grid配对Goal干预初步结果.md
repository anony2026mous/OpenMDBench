# Grid 配对 Goal→Action 干预初步结果

日期：2026-09-24。目标是给论文 M3 干预式接口测量建立可信的配对运行基础；**不是正式 (B_{if}) 或 (I_{do}(G;A\mid O)) 值**，也不替代已有 20-seed 自然轨迹互信息和归因批次。

## 设计与结果

只读使用 4.0 项目的 grid 代码，难度 medium、规划间隔 5、决策 step 6；seed 100～119，每个 seed 各跑 independent/sequential/continuous 三种任务模式，共 60 个配对 case。每个 case 独立创建三条同 seed 运行：规则 Goal、重复规则 Goal 对照、每个己方单位的合法中性 `hold` Goal；在干预前核对完整 grid 环境状态、可见观测与 broker 指纹，在干预后记录规划提议、实际提交、接受回执、执行动作、己方状态和完整环境指纹。注入仅发生在实验包装层，不改规则策略、执行器、场景或评分。

产物：`artifacts/grid-goal-probe-medium-20seed-step6-v1/summary.json`，SHA256 `7404d479e0262ed51afa8554523fa9b189888a9878aa88c3b3995fd4dcf572b5`；独立内容/哈希审计 `artifacts/grid-goal-probe-medium-20seed-step6-audit-v1/audit.json`，SHA256 `379e34e5857a6845ef8d4b29e3e798a76f5765dacd739a9857d2245dd83d870e`。60/60 case 的干预前状态、规则提议和未注入重复对照均一致；`hold` 指令均被接受，60/60 case 的离散动作与规则 Goal 条件不同，审计无错误。一个可复核的例子：seed 100、continuous、step 6 的规则臂动作三个单位均为 `0`，中性 `hold` 臂均为 `4`；源 `Direction.STAY=4`。两个未注入对照的后一状态指纹完全相同。

同一 seed 的三个任务模式在这个**早期**决策点，规则 Goal 提议、动作和后一 tick 己方状态均相同（20/20 seed）；完整环境指纹不同，因为任务模式本身是环境配置的一部分。这里的 Goal 干预显示下层能响应合法 Goal，但尚未显示模式强弱排序、三档接口预算梯度或有用的任务效用变化。因此不得把“60/60 动作改变”直接解释为 D3 通过。

## 尚缺的论文门禁

当前只用了规则 Goal 与 `hold` 两类条件、一个 step，缺少同一可比观察状态下预注册的多 Goal 随机分配、多个决策窗口和每 seed 的 episode-block 样本。没有估计条件动作分布及其 KL，也没有动作 token/距离尺度稳健性、KSG 敏感性、跨 seed 不确定性。以前自然轨迹的三档规划间隔与任务模式操纵未形成有效 B_if 梯度；本探针不改变这一失败结论。归因仍受独立 oracle 质量未通过的限制（已有 grid 参考 oracle 曾在部分 seed 低于基线），不能用中性 `hold` 来冒充 oracle。

下一步应固定三档**真正被执行器消费**的 Goal 字段/时序操作，先验证档位改变动作分布且差异超过同条件重复噪声；然后按预注册动作编码、多个 seed 与决策窗口估计 (I_{do})，并独立验证规划/执行参考组件质量，再开展五类 A10 已知故障和剂量响应。

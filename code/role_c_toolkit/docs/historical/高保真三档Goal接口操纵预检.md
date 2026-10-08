# 高保真 weak／medium／strong Goal 接口操纵预检

日期：2026-09-24。对应角色 C 的 D3 前置操纵检查。只通过 4.0 引擎现有 `GoalCommand.to_granularity` 路径在决策锚点裁剪 Goal 字段；三档在锚点以前均走同一规则策略。每档独立新进程运行，另有 strong 重复对照。**这里只验证局部动作机制，不估计 B_if，也不宣布 D3 放行。**

## IE-01 早期单 tick：发现门禁失败

IE-01 seed 100、tick 10、窗口 1 tick：`artifacts/hifi-goal-tier-ie01-s100-tick10-v1/probe.json`（SHA256 `c00cc4c894c0b4e67cbaa3ac607f2ec8cd826cfe487d66b204737cd5dc52eb94`）。原始完整 checkpoint 在四臂间一致，strong 重复对照逐项一致。weak 删去目标 ID 后两架无人机速度为 0，而 medium/strong 保留目标 ID 后速度均为 43 m/s；**medium 与 strong 的动作批完全相同**。这是早期一 tick 不足以观察 strong 新增开火教义的直接反例。

独立审计 `artifacts/hifi-goal-tier-ie01-s100-tick10-audit-v1/audit.json`（SHA256 `67da7e8a16517cb33566338dce9a035a2dd8fd68751b7dea767a2fad7c2e0ad9`）还发现 strong 的巡逻 Goal 被 broker 按既有“同签名不可行目标禁止重发”规则拒绝；medium/weak 因为裁掉了巡逻位置字段而被接受。因此 IE-01 这个锚点不仅缺少 medium→strong 的动作梯度，三档实际接受率也不相同，**不符合无歧义接口操纵预检**。失败记录保留，不能只挑动作差异明显的部分报告。

## IE-04 早期开火窗口：三档确实被执行器消费

IE-04 seed 100、tick 70、窗口 10 tick：`artifacts/hifi-goal-tier-ie04-s100-tick70-w10-v1/probe.json`（SHA256 `0d33402896352e04aa5a4ff63d1e34957c20f9ae1b1cab922ffdd38036dcf6ec`）。四臂的干预前**原始完整 checkpoint**、观测、broker 和 planner 指纹一致；strong 两次的 Goal、动作/回执和窗口末完整 checkpoint 一致。每档六条 Goal 均被 broker 接受，无拒绝。字段严格嵌套：weak 保留 Goal 类型和单位指派，medium 增加目标 ID，strong 再保留 `fire_policy=salvo`；弱档无人移动或开火，中档出现目标追踪和 **2 次**开火指令（tick 73、79），强档出现目标追踪和 **3 次**开火指令（tick 73、76、79）。strong 在 tick 76 的额外开火与被 medium 裁掉的 `fire_policy` 的执行路径一致，是机制证据，不是跨 seed 效用收益证明。

独立审计 `artifacts/hifi-goal-tier-ie04-s100-tick70-w10-audit-v1/audit.json`（SHA256 `9eeffefb43e55784de41cdedd64c601636cc5419231009517cfd1f3dfaca9077`）错误列表为空；核实三档参数嵌套、全部 Goal 被接受、锚点和 strong 重复对照一致，以及两组相邻动作批确实不同。

## 结论与正式 D3 的欠账

现有 V2 接口在一个有效的 IE-04 开火窗口里能表现出 weak→medium→strong 的**动作层级**，证明字段不是纯粹增加 JSON 长度；但 IE-01 早期锚点不满足相同门禁，说明响应依赖场景时段、可行性协商和观察窗口。不能挑一个成功窗口就宣称八场景 D3 已通过。下一步需预注册各场景多个锚点、多个 seed 和动作编码/距离，再验证相邻档的 (B_{if}) 差距大于估计方差；同时报告各档接受/拒绝、Goal 消费率、效用和重复噪声。IE-01 的 broker 签名差异须作为接口语义问题单列，而不能暗改引擎或删掉失败样本。

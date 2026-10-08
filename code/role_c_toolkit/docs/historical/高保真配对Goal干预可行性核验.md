# 高保真 Goal→Action 配对干预可行性核验

日期：2026-09-24。此文件记录角色 C 的 M3 干预式接口测量前置核验，**不是正式 B_if 值，也不是 IE-01～IE-08 验收**。源引擎、场景、规则规划器和执行器文件均未修改。

## 方案与可复现产物

脚本：`role_c_measurement/hifi_goal_probe.py`。每个条件在新的 Windows Python 3.11.0rc2 进程里从相同场景/seed 执行到决策 tick，记录干预前完整世界 checkpoint、可见观测、broker 与 planner 指纹。在该决策时点比较：原规则 Goal、同一原规则 Goal 重复对照、以及给每个可机动己方单位提交合法 `hold` Goal 的 `do(G=g_hold)`。记录真实提交的动作批、回执和推进一 tick 后的世界 checkpoint。注入位于实验包装层的 `GOAIBroker.submit_goals` 入口，不改引擎真值或执行器实现。

已运行 IE-01-SINGLE-TARGET、seed 100、规划间隔 10，在决策 tick 10 和 20 各做一 tick 动作窗口。有效产物分别是 `artifacts/hifi-goal-probe-ie01-seed100-tick10-hold-v1/probe.json`（SHA256 `9276a5d1c5c4c884aba65c084f5051ddc957b7b129001ade7f04a8eafc90ac39`）与 `artifacts/hifi-goal-probe-ie01-seed100-tick20-hold-v1/probe.json`（SHA256 `3d8f8fe8ead3da2babb43fe6ae6f5eea5cfb944fcfd409d1385fe8b5f3e486d6`）；脚本 SHA256 均为 `cc0e6818e45c52bd72c49ad4ef811eda6c5ace6b2d59d34ef0f9c6452cae3981`。报告记载源代码清单运行前后相同。

在两个 anchor 各自的三个独立进程中，干预前的**原始完整 checkpoint 哈希一致**；可见观测、broker 和 planner 指纹也相同。两个未注入对照的 Goal、动作批、执行回执及后一 tick 的完整 checkpoint 逐项相同。`hold` 条件所截获的原规则提议与对照完全一致，实际送入 broker 的三个 `hold` Goal 均被接受，无拒绝；动作批和后一 tick 的完整 checkpoint 均与对照不同。tick 10 的原始 anchor 哈希为 `b0fa71ec9f7833a43f23a88a11ccbb9a1a08be93e1739947120e6f52ffe5a136`；两次对照的最终哈希为 `9e6d468999a5750399faa2872d70ddf99a7b719c5edfe33863ee83ac59b6dac6`。其他哈希见产物。

机制层面，tick 10 对照下两架蓝方无人机收到速度 43 m/s、航向约 92.13° 和 100.14° 的导航动作；`hold` 后，两者速度均为 0 m/s。tick 20 对照下第一架无人机速度为 43 m/s，`hold` 后为 0 m/s；另两台平台原本已为 0 m/s。这是同一干预前状态下 Goal 改动造成的**两个局部动作响应实例**；不能由此推断任务收益、总体效应或信息容量。

## 失败先例与边界

最初试验在**同一 Python 进程**里顺序新建多个会话。即使 seed、可见观测、broker 和 planner 相同，原生动力学适配器的全局 `instance_id` 会递增；tick 10 时 `motion_ledger` 也发生差异，因此完整 checkpoint 不相同，重复对照后状态也不相同。其原始试验目录 `hifi-goal-probe-ie01-seed100-tick0-v1/v2`、`hifi-goal-probe-ie01-seed100-tick10-v1` **不合格，不纳入效应估计**。独立进程修正后才得到上述精确配对证据；以可见观测相等代替隐藏状态相等会产生虚假因果归因。

另一个语义陷阱：`GOAIBroker.submit_goals([])` 不会撤销旧活动 Goal，只是不提交新 Goal。因此此前独立进程试验 `tick10-v3` 的速度变化只能称为**抑制新 Goal 提交**的效果，不能称“清空所有 Goal”；在 `tick20-v1`，它甚至与基线动作及后一状态完全相同，因为旧拦截 Goal 仍在执行。以上目录留作反例，不纳入 `do(G=g_hold)` 的配对证据。现在的 `hold` 指令按单位 supersede 旧 Goal，且通过回执核验三条新 Goal 被接受。

本试验只含一个 seed、两个 anchor、原规则 Goal 与中性 `hold` Goal 两个条件。它未随机化四种 Goal 条件、未做 weak/medium/strong 三档、未形成跨 checkpoint 样本分布、未估计 `I_do(G;A|O)`，也没有 episode block bootstrap、连续动作 KSG 敏感性、五类归因故障或 oracle 正控制。后续必须在各场景多个锚点及 seed 上扩展，且每个锚点先通过原始 checkpoint 相等和未注入重复对照门禁；有一项失败即剔除该配对并保留失败记录。

## IE-02～IE-08 同一早期锚点的扩展

使用 `hifi_goal_probe_sweep.py` 对 IE-02～IE-08 均以 seed 100、tick 10、下一 tick 动作窗口运行相同三臂探针。`artifacts/hifi-goal-probe-ie02-08-seed100-tick10-v1/summary.json`（SHA256 `258cca3e41fdd1b001b35ef1bcd5b7bb6c608a3994517635bc8f6b781e22576c`）记录 **7/7** 场景均通过：原始完整 checkpoint/观测/broker/planner 锚点一致，未注入重复对照的动作和后一状态完全相同，原规则提议一致，`hold` Goal 均被接受，动作批均出现差异。独立审计 `artifacts/hifi-goal-probe-ie02-08-seed100-tick10-audit-v1/audit.json`（SHA256 `4d7a701f3f4fcc522e190cbbdb4bcd127fc30f99b8f6a0d2c736b8346b383708`）核对各报告内容与摘要哈希，错误列表为空。

连同 IE-01 的有效试验，**八个场景均至少在一个早期锚点验证 Goal→Action 的局部响应**。这仍只是工程可行性检查：全部使用同一个 seed、规则规划器、同一类型的中性 Goal，不能代表整个场景时段或 LLM 混合系统，也不能由“7/7 动作有差异”推导 (B_{if}>0) 的正式数值、三档梯度或任务效用提升。八场景正式结果仍需多个 seed/锚点、预注册 Goal 分配、可比的动作 token/距离、block bootstrap 和单独的归因注入验证。

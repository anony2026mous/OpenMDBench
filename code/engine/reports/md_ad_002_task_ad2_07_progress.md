# AD2-07 EASY 纵向闭环进展报告

> 已归档：评分 P2 已由 AD2-ADR-016 关闭。最终状态和最新门禁证据见
> `reports/md_ad_002_task_ad2_07.md`。

## 已完成

- 新增只读取 `RedObservation` 的红方规则智能体：雷达搜索、USV守位、contact排序、UAV截击、CIWS优先、弹药/通信/置信度/age/射程/cooldown管理和稳定单目标分配。
- 新增只读取蓝方公开 Observation 与公开保护点配置的 EASY 直飞脚本。
- 新增 EASY runner，串联三波出生、动力学、感知、融合、交战、突破裁决和评分。
- 新增七项指标、N/A 权重重归一化及独立 safety gate。
- seed=17 的正式长轨迹在 tick 1085 得到 `blue_success / breach_threshold_reached / breaches=3`，证明实际失败路径贯通。
- 短轨迹相同 seed 两次结果完全相等。
- 新增显式 hold 的 timeout 轨迹：tick 5 得到 `red_success / timeout_denial_success`。
- 新增 hash-chain JSONL/gzip 权威日志，包含配置/地图身份、逐 tick 双方动作、红方公开观察、公开交战事件和裁判世界快照。
- 日志可离线派生 referee/red/blue/public 四视角，不访问活动 WorldState；红方视角反真值泄露测试通过。
- 环境检查点与红方智能体 cooldown 状态联合恢复后，下一 tick 完整状态逐字段一致。
- CLI 已增加 `selftest --scenario MD-AD-002-EASY` 一键入口。

## 测试

- 本轮 EASY runner、CLI、日志、评分和 checkpoint 定向测试均通过。
- Gym 与 REST 已使用同一红方规则策略核心完成终局一致性验证。
- Matplotlib `Agg` 已完成威海地图、三类平台和禁入区的无图形渲染烟雾测试。
- checkpoint 恢复后的后续状态逐字段一致。
- 全量回归：`340 passed, 15 warnings`；告警均为既有 Taichi/Gym 弃用告警。
- `make lint typecheck`：Ruff 通过，严格 mypy 检查 222 个源文件通过。
- 类型收口后的 24 项相关单元/契约/集成/系统测试通过；需设置
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 隔离宿主 ROS pytest 插件。

## 参数阻断处置

- 经需求方确认，三个正式配置提升为 2.0.0：每架 UAV 12 发、导弹 damage=1.0；
  命中率、射程和 cooldown 不变。原值保留为 `resource-tight-v1` 压力档案。
- 新正式参数下 seed=0 在 tick 1464 达到
  `red_success / all_threats_destroyed / breaches=0 / interception_rate=1.0`。
- 禁用红方交战的失败档案达到
  `blue_success / breach_threshold_reached / breaches=3`。

## 尚未闭合

- 七项评分中的 `usv_early_warning_gain` 仍在 runner 中固定写为 `0.0`，尚未按冻结公式
  `clip((D_usv-D_base)/max(D_base,eps),0,1)` 建立版本化离线 `D_base`，也尚未证明
  在线累计与同一回放离线重算一致。

资源可达性、Gym/REST 整局、日志/视角、checkpoint 和无图形可视化阻断均已解除；
但上述评分 P2 按 `agents3.md` 不能静默延期，因此 AD2-07 仍保持进行中，暂不进入
AD2-08。

## 冻结需求阻断证据

- 胜利要求 `breaches < 3`，即 15 架中至少 13 架必须在进入 8 km 区域前终止。
- CIWS 最大射程 2 km；其射击发生时目标早已进入 8 km 并锁存突破，不能贡献“突破前摧毁”。
- 3 架 UAV 共 18 发导弹；每发 damage=0.6，每个满血目标至少需要 2 发，因此理论最大只能摧毁 9 架。
- 即使 18 发全部命中，仍至少有 6 架进入 8 km，超过固定阈值 3。

该问题已由需求方选择“调整武器资源参数”解决，决策记录在修订后的
AD2-ADR-002 和新增 AD2-ADR-015；旧结论仅作为 v1/resource-tight 历史证据保留。

# RF-ADR-001：平台化重构基础决策集

- 状态：Accepted
- 批准日期：2026-08-25
- 批准来源：用户明确批准 `reports/platform_refactor_rf_00_adr_decision_register.md` 的推荐方案
- 适用范围：RF-00 至 RF-15

## 背景

OpenMDBench 当前具备可复用的仿真、正式场景、接口、日志和可视化能力，但尚未形成统一的 Catalog、ResolvedScenario、SimulationSession、命令生命周期和公共 DTO 边界。平台化重构必须增量复用现有内核，避免产生第二套世界状态或主循环。

## Accepted 决策

1. 采用模块化单体和固定权威 tick 流水线；当前不拆分跨网络仿真微服务。
2. 场景先编译；正式会话只接受不可变、完整解析和可哈希的 `ResolvedScenario`。旧加载器只能通过显式兼容适配器接入。
3. Catalog 正式资源采用精确 `id@semver` 引用，同时记录内容哈希和 Schema 版本；禁止运行时隐式选择最新版。
4. 每个 `SimulationSession` 只有一个 `WorldState` 写入者。REST、Gym、SDK 和 GUI 只能提交命令或读取不可变 DTO。
5. 统一定义 Continuous、Lockstep 和只读 Replay 三种 Runner；加速比只影响墙钟调度，不改变固定物理 tick。
6. 动作分为可持续的 persistent command 和最多执行一次的 discrete action，并分别记录生命周期。
7. 动作必须具有版本化时间戳、命令 ID、幂等语义和明确 TTL/stale policy；拒绝原因稳定且可机读。
8. Observation 是已发布的不可变快照；读取 Observation 不推进或修改仿真，也不暴露可变 `WorldState`。
9. 实时与离线显示共享版本化 `VisualizationFrame`，并在服务端生成 referee/red/blue/public 白名单视角。
10. Live frame 使用有界 `drop_oldest` 背压；权威日志不得因显示消费者过慢而丢失。
11. Replay 只读取版本化日志/帧并校验地图、配置和 Schema 哈希，不重新运行仿真内核。
12. MMG、Taichi 等原生状态必须有会话隔离证据；无法证明线程隔离时使用 spawn worker 进程隔离。
13. 公共 DTO 使用语义版本；兼容新增维持旧消费者，不兼容变化升级 major 并提供弃用周期和迁移说明。

## 影响

- RF-01 及后续设计必须遵循上述边界，不得复制 Schema、WorldState、主循环或 Renderer。
- 旧场景、API、Gym、日志和回放需要显式兼容适配器及迁移测试。
- 本 ADR 只冻结架构方向，不表示 RF-00 门禁已经通过，也不批准进入 RF-01。

## 验证要求

- RF-00 差距矩阵和后续阶段报告逐项引用本 ADR。
- RF-03 验证 ResolvedScenario 的不可变性、规范化和哈希稳定性。
- RF-04 至 RF-06 验证单写入者、动作生命周期和三 Runner 时间等价性。
- RF-08 验证统一帧、视角过滤、背压和非重仿真回放。
- RF-13/RF-14 验证原生状态进程隔离、并发、安全和资源上限。
- RF-15 审查所有不兼容变化的版本与迁移证据。

## 被否决方案

- 一次性重写或拆分仿真微服务。
- 正式会话直接解析原始 YAML/dict。
- 隐式最新版资源、多个世界写入者或请求驱动 continuous。
- 未区分持续命令与一次性动作。
- Renderer/Replay 直接读取或重建活动世界。
- 无界显示队列、客户端自行过滤真值或无版本公共协议。

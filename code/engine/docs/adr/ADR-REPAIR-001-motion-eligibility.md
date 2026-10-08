# ADR-REPAIR-001：生命周期驱动的运动资格与 tick 边界动作投影

- 状态：Accepted for BUG-V2-001 implementation
- 日期：2026-09-07
- 需求：`BUG-V2-001`、AR-003、AR-005、AR-006、AR-007、ENT-005、LIFE-001、CMD-001、
  CMD-002、CMD-003、RUN-001、RUN-002、CHK-001
- 前置证据：`reports/repair/BASE-00_current_head.md`
- 适用范围：所有 V2 `ResolvedScenario`、`WorldStateV2`、`ActionPipelineV2` 和
  `SimulationSession`；不针对 MD-AD-002、任何 faction 或固定实体 ID。

## 背景

BASE-00 证明当前 Session 以“仍有 `dynamics_ref`”生成控制命令，而 World 以
“仍有 `dynamics_ref` 且 lifecycle 为 `active/degraded`”要求命令。实体在 tick 357
由碰撞毁伤转为 `disabled` 后，两个集合在 tick 358 分叉并触发 World 的严格集合校验。

`disabled`、`destroyed`、`wreck` 与 `despawned` 都是通用生命周期语义；修复不得通过
删除动力学资源、按场景/实体 ID 过滤，或仅让 World 放宽其严格校验来掩盖问题。

## 决策

### 1. World 是唯一运动资格事实来源

定义在 tick `t` 的 pre-motion 生命周期边界上的通用谓词：

```text
motion_eligible(entity, t) =
    entity 在该边界存在
    AND lifecycle ∈ {active, degraded}
    AND 存在精确 dynamics_ref、对应已物化 adapter 与 dynamics/move capability token
    AND 运行期 capability 未撤销该 dynamics/move token
```

- `dynamics_ref` 是实体固有组成证据，不因毁伤而删除。
- `disabled`、`destroyed`、`wreck`、`despawned`、`scheduled` 均不满足该谓词。
- `degraded` 仅在仍拥有精确 `dynamics`/`move` capability 时满足；速度或控制限制由既有
  capability modifier 处理，不能用场景逻辑替代资格判定。
- 固定设施如具有合法 fixed dynamics binding，仍按该 binding 的空 controls 进入资格集合；
  “有命令”不等于“位置发生变化”。

World 必须提供一个仅在 Session/World 内部使用的不可变、稳定排序的
`MotionEligibilitySnapshotV2`（具体类名可在 BUG-03 按代码风格落定）。它至少锚定：

- `expected_tick`、resolved hash、World tick；
- motion-eligible entity ID 的字典序元组；
- 每个实体的 exact dynamics binding/controls 形状；
- 在该 pre-motion 边界生效的 lifecycle 计划结果；
- 用于再次核验的规范化 hash/fingerprint。

Session、Command Resolver、运动 provider、可视化、REST/Gym/Python adapter 和 checkpoint
restore 不得自行复刻 eligibility 筛选条件。它们只能消费 World 给出的快照或其投影结果。

### 2. 冻结 tick 内顺序

一个成功 World tick 的权威顺序固定为：

```text
0. World 形成 pre-motion lifecycle 结果和 MotionEligibilitySnapshot
1. Session 原子地校验/投影 pending、persistent、discrete actions 到该 snapshot
2. 对每个 eligible entity 选择新 persistent command、仍有效 persistent command 或 safe hold
3. World 复算并核验同一 snapshot anchor，随后调用 dynamics provider
4. motion → boundary/collision → energy/sensor/communication → combat/effect
5. 同 tick DamageIntent 同时结算、lifecycle/capability 更新、wreck/despawn policy
6. mission/score → authority event/log/frame/next observation
```

第 0 步须包含在本 tick motion 前生效的声明式 spawn/despawn/lifecycle 事件。World 只能以
单写入者方式实际提交这些转换；供 Session 投影的 snapshot 是对该原子边界的只读、可复算
承诺，不允许 Session 修改 World。

第 5 步发生在 motion 与本 tick 合法 discrete action 之后。因此一个实体若在 tick 开始时
eligible、但在该 tick 的 damage 阶段才失效：本 tick 已合法投影的移动和离散 action 保持
有效且最多执行一次；它的旧 persistent command 从**下一** pre-motion 边界开始取消。不得
回溯取消已经合法发生的 fire、RNG 证据或运动。

World 在实际调用 adapter 前必须再次核验 snapshot fingerprint 和命令 ID 集合完全相等；不等
时在 adapter step 前失败，且不得产生部分运动提交。原有严格集合校验保留为内部不变量。

### 3. 动作与 receipt 语义

| 边界情形 | persistent command | discrete action | 资源/RNG/receipt |
|---|---|---|---|
| 提交时已不 active/degraded | 保持既有稳定 `session.entity_lifecycle_invalid` 拒绝 | 同左 | 不入队、不产生 World 副作用。 |
| 已入队/已持有，pre-motion snapshot 表明失去资格 | 从 active persistent 表移除，标记 `cancelled` | 标记 `rejected`，不形成 request | 两者都以稳定 child ID 顺序写入 `ActionChildReceiptV2.error_code=session.entity_lifecycle_invalid`；不推进武器 RNG、不消耗弹药。 |
| tick 开始 eligible，damage 在本 tick 后段才失效 | 本 tick 控制照常执行；下一 tick 取消 | 合法 action 可执行一次；不得因随后 damage 重放或撤销 | 既有 combat receipt 决定 `executed/rejected`；下一 tick 才处理旧 persistent。 |
| 可运动的新出生实体无有效 persistent command | 不写入 active persistent 表 | 不适用 | World snapshot 指示 exact binding；Session 生成仅本 tick 有效的 typed safe hold/fallback，不改变外部 action 语义。 |

失效的 discrete action 是终态 `rejected`，其 action identity 必须记入 consumed-discrete
证据，以避免实体后续恢复时重放同一 action；“不消耗资源”不等于“允许同一 action 再次执行”。

现有公开 DTO 足以表达上述语义：`PersistentCommandStatusV2` 已有 `cancelled`，
`DiscreteActionStatusV2` 已有 `rejected`，`ActionChildReceiptV2` 已有 `status` 和
`error_code`。因此 BUG-V2-001 **不修改** `ActionReceiptV2`、`ActionApplyReceiptV2`、
`SessionCheckpointV2`、REST、Python、Gym 或 VectorEnv 的公开 schema/version；BUG-03 只可
在既有字段中填充稳定证据。若实现发现确需新增公开字段或状态，必须停止并新建兼容性 ADR，
不得静默改变含义。

### 4. 生命周期、wreck、日志与恢复

| lifecycle/policy | motion | 主动系统 | 碰撞与可视化 | checkpoint/restore |
|---|---|---|---|---|
| `active` / 合法 `degraded` | 以 typed dynamics command 推进 | 按 capability 运行 | 按实体 collision/visualization profile | 保存状态、adapter、queue、RNG 与 receipt。 |
| `disabled` | 不进入 motion snapshot | 不运行 sensor/communication/weapon | 保留位置；除非未来有显式 disabled policy，不冒充 wreck collision candidate | 保存为 disabled；恢复后的首个边界取消遗留动作。 |
| `destroyed` + `wreck` | 不调用 dynamics；仅 World 生成静态 wreck candidate | 禁止 | 依 lifecycle policy 保留碰撞体与外形 | `destroyed_lifecycle_ledger` 与 entity state 同时锚定。 |
| `destroyed` + `despawn` / `despawned` | 无 | 无 | 从 active entity registry 移除；保留 tombstone/log | checkpoint 验证 topology、tombstone 与 policy evidence。 |

`destroyed_lifecycle` 仍由 Resolved entity 的 `wreck/despawn` 数据政策选择。没有运动命令不能
被解释为删除实体；没有 wreck policy 也不能让 disabled 实体意外成为静态障碍。

checkpoint 不存储可重新导出的 eligibility snapshot 作为第二事实来源。它保存 World lifecycle、
实体 capability、destroyed lifecycle evidence，以及 Session pending/persistent/consumed/receipt
账本；restore 后由 World 用已恢复状态重算下一 tick snapshot。连续运行与 restore 运行必须生成
相同的取消/拒绝 receipt、事件顺序、RNG 证据、终局和评分。

### 5. 实现边界与拒绝的替代方案

- 不接受仅在 `ActionPipelineV2` 复制 `active/degraded` 条件：这会再次产生两个事实来源。
- 不接受移除 World 的严格命令集合校验：会将缺失命令转为未审计的 adapter 行为。
- 不接受毁伤时改写/删除 `dynamics_ref`：会破坏 Resolved/Catalog 不可变性、日志和 restore。
- 不接受按 MD-AD-002、faction、interceptor、武器或固定 ID 特判。
- 不处理 CLI `stop()` 二次 transition：这是 BASE-00 登记的独立 P2，除非 BUG-03 的最小修复
  直接暴露必需处理，否则留作单独 issue。

## 验证义务（留给后续阶段）

BUG-02 必须先建立 B01–B10 故障测试：disabled 与 destroyed 的上一 tick/当前边界、persistent
取消、discrete exactly-once、wreck/despawn、spawn safe hold、多实体同时毁伤及 checkpoint restore。
BUG-03 只能实现本 ADR 的 World-authoritative snapshot/投影，不得混入 MMG RPC 优化。
BUG-04 再执行三档、接口、日志、frame、checkpoint 和确定性回归。

## 影响

- 兼容性：公开 schema 语义保持；已有客户端在实体失效后将看到既有 lifecycle invalid error 或
  child `cancelled/rejected` 状态，不再导致整个 Session 崩溃。
- 确定性：snapshot、命令投影、取消、fallback、receipt 和 checkpoint 全部稳定排序并锚定 tick。
- 领域：使毁伤、残骸与运动行为同属一个通用 lifecycle—capability 契约，符合 surface、air、
  fixed 和后续第三方实体组合。

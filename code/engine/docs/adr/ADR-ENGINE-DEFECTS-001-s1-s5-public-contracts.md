# ADR-ENGINE-DEFECTS-001：S1–S5 公共契约

- 状态：Accepted
- 日期：2026-09-17
- 范围：EF-01；S1–S5 修复的公开评分、感知、controller、通信与 inbox 契约

## 背景

EF-00 已确认 S1–S5 缺陷存在。本 ADR 冻结修复应遵守的公共语义；它不实施 S1–S5，也不改变 S6 身份认证或 S7 的详细状态可见性契约。既有 `ADR-010`、`ADR-MD3-006`、`ADR-MDINT001-006` 和 `ADR-MD3-008` 继续有效。

## 决定一：AD-002 评分归一范围

评分统一转换为 `[0,1]` 的 utility，且始终越大越好。原始值必须保留，聚合不得直接加权不同量纲的 raw value。

### `score.denial`

- raw value 是保护区内有效入侵者数量。
- 方向为 `minimize`，下界为 `0`，上界为当前 `ResolvedScenario` 的评分 selector 在编译期解析出的有效入侵者总数 `N`。
- `N` 不得硬编码为 `3`。
- `utility = 1 - clamp(raw_value / N, 0, 1)`。
- `N = 0` 时，该指标为 `None` / N.A.，并记录原因。正式 AD-002 若要求该指标而 `N = 0`，场景编译必须失败。

### `score.efficiency` 与 `score.survival`

二者沿用现有指标的 raw 定义，合法范围均为 `[0,1]`，方向均为 `maximize`，并使用：

```text
utility = clamp(raw_value, 0, 1)
```

### 聚合、审计与版本

```text
total = Σ(utility_i × effective_weight_i)
```

- `total` 的范围为 `[0,1]`。`training_rewards.aggregate` 使用同一个 `total`，不得再按场景方向翻转。
- N.A. 指标排除后，重新归一剩余权重。
- 可计算但数据缺失的指标按项目既有规则计 `0`，并产生 `metric_data_missing`。
- raw value 超出声明范围时，保留 raw value、按边界裁剪 utility，并产生 `metric_value_out_of_range`；不得静默处理。
- receipt 至少记录 raw value、utility、direction、effective weight、weighted contribution 和 aggregation version。
- 新聚合采用 `utility-v1` 评分契约版本。现有非 utility 的 ResolvedScenario 使用显式 `raw-v1`，继续以原 raw 聚合语义运行；历史 receipt 或 checkpoint 未声明版本时由兼容读取路径标识为 `legacy-v1`。旧日志和旧排行榜不得被静默重新解释。

## 决定二：AD-002 低空 AGL 参数

低空高度统一是目标相对于局部地表或海面的 AGL；不得使用绝对 MSL 或目标相对传感器的高度差。AD-002 当前具有低空距离声明的传感器冻结如下：

| 传感器 | 低空范围 | 低空上限 | 标称范围 | 过渡方式 |
| --- | ---: | ---: | ---: | --- |
| `sensor.shore-early-warning` | 15,000 m | 300 m AGL | 40,000 m | `step` |
| `sensor.picket-radar` | 20,000 m | 300 m AGL | 30,000 m | `step` |

判定规则：

```text
target_agl <= 300 m  -> low_altitude_range_m
target_agl > 300 m   -> nominal_range_m
```

边界 `300 m` 归入低空。未声明 altitude range profile 的其他传感器保持原 nominal range 行为；内核不得使用隐式 `300 m` 默认值。未来需要低空限制的传感器必须在 Catalog 中显式声明。

地形地图必须通过 `geography/surface-elevation` 接口计算 AGL。当前威海海域可使用局部海面高度。无法取得地表高度时，不得静默将 MSL 当作 AGL。

上述 `300 m` 和探测距离都是 `UNVALIDATED_BENCHMARK`，只用于基准功能和确定性测试，不得声明为真实装备标定。必须创建新的 Catalog 版本和 hash，不得覆盖旧资源。

## 决定三：严格 controller scope 和显式通信发端

采用严格 controller scope。

### 权限与观测

- controller 只能向其 claim 中的实体提交动作。
- `controlled_entity_ids` 必须显式出现在 Observation。
- `own_entities` 只能包含该 controller claim 覆盖的实体；同 faction 内其他未被 claim 的友军不得作为 own entity 返回。
- 集中式 controller 如需观察和控制全 faction，场景必须显式 claim 全部相关实体。
- controller scope 是数据和控制契约，不是身份鉴权；S6 的认证与不可伪造授权仍属后续任务。

### 本方状态

claim 内实体的基础 own-state 不因通信中断或干扰而消失，包括允许公开的位置、速度、航向、生命周期、健康和能量。弹药、冷却、组件和传感器状态是否公开仍由 S7 后续契约确定。S3 修复不得重新变成通信断开后本方实体消失。

### 显式通信发端

每个 controller 必须在场景中声明 `controller_endpoint_ref`，并将其绑定到具有通信组件的实体或固定通信设施。

- 不得从第一个被 claim 的实体推断发端。
- controller claim 决定可以控制谁；controller endpoint 决定命令、共享航迹和消息从哪里进入通信网络。
- endpoint 绑定实体本身的本地控制视为 zero-hop；发往其他实体的命令必须经过通信 transport。
- controller 直接获得绑定 endpoint 产生的 organic contacts；其他平台产生的 contact 必须经过通信 transport 后才成为 shared contacts。
- 无 route、丢包或 TTL 过期时，不得共享或执行。
- formal V2 场景缺少 endpoint 时，场景编译必须失败。
- 旧场景如需兼容，只能通过显式 legacy adapter，必须记录兼容警告，且不得静默恢复 faction 全知视角。

## 决定四：Inbox 范围、容量和淘汰策略

采用 controller-scoped、有界、只读观察的 inbox。

### 接收范围

controller inbox 只接收 transport 已成功投递且满足以下之一的消息：

- `recipient_controller_slots` 显式包含当前 controller；
- 显式 faction broadcast，且当前 controller 属于目标 faction。

inbox 不接收发给其他 controller 的私有消息、dropped/blocked/expired 消息、未显式广播的同 faction 消息、航迹共享和命令 receipt；后两类使用各自独立 DTO。发送方默认不收到自己的消息，除非其同时被显式列为接收方。

### 容量与 payload

- 默认每个 controller 256 条；场景可配置，合法范围为 `1–4096`。
- inbox 禁止无界。
- payload 必须经过 Schema 和大小限制校验。建议默认最大序列化 payload 为 `16 KiB`，且不得包含可执行代码。

### 保留、读取、淘汰与恢复

- 消息保留到自身 TTL 到期或被容量策略淘汰。Observation GET 不消费消息；本版本不引入隐式 read/consume。未来 ACK 必须作为显式动作另行版本化。
- 容量不足时，先删除已过期消息，再按 `delivered_tick` 最早者淘汰；`delivered_tick` 相同时按 `message_id` 稳定排序。每次容量淘汰产生 `communication.inbox_evicted` receipt/event。
- 相同 message ID 的重复投递必须幂等。同 tick 消息按稳定 `(delivered_tick, message_id)` 排序。
- inbox 内容、TTL、淘汰状态和去重状态必须进入 checkpoint。checkpoint 恢复不得重复投递、复活过期消息或改变顺序。

## 结果

EF-02 及之后的实现、Schema/Catalog 版本化和测试必须遵守本 ADR。任何扩大参数、改变未决的 S6/S7 契约或为旧日志隐式补充新语义的变更，都需要新的明确决定。

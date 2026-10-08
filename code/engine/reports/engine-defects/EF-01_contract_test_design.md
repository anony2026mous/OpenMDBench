# EF-01 S1–S5 契约测试设计

TASK_ID: EF-01
STATUS: DONE
TEST_LEVEL: T0（设计审查；本阶段未实现或执行测试）
CONTRACT: `docs/adr/ADR-ENGINE-DEFECTS-001-s1-s5-public-contracts.md`

## 共同设计约束

- 后续实现使用最小、可审计的 Scenario/Catalog fixture；不运行外部缺陷报告中的临时脚本。
- 每个随机检测或通信测试固定 seed，并断言事件、receipt、checkpoint 和公开 DTO 的可重复结果。
- 仅在需要覆盖 AD-002 明确参数时使用其新版本 Catalog；其他契约测试用通用最小 fixture，避免扩大 AD-002 场景参数。
- 所有 legacy 兼容测试都断言显式 adapter、警告与版本标识，绝不接受静默的语义转换。

## S1：评分 utility 与审计

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S1-01 | `score.denial` 的 resolved selector 有 `N=4`；分别得到 raw `0`、`4`、`5` | utilities 依次为 `1`、`0`、`0`；raw `5` 原样保留并有 `metric_value_out_of_range`。 |
| S1-02 | `score.denial` 的 resolved selector 有 `N=4`、raw `1` | utility 为 `0.75`，证明上界来自 resolved selector 而非硬编码 `3`。 |
| S1-03 | efficiency/survival 分别产生 `0`、`0.5`、`1` 以及范围外 raw | 范围内 utility 相等；范围外裁剪并产生 `metric_value_out_of_range`。 |
| S1-04 | 混合 minimize/maximize metrics 和非零权重 | total 为 `Σ(utility × effective_weight)` 且在 `[0,1]`；`training_rewards.aggregate` 与 total 相同，不再翻转。 |
| S1-05 | 一个 N.A.、一个 required-but-missing、一个有效 metric | N.A. 被排除并重新归一；missing utility 为 `0` 且有 `metric_data_missing`；不得把 missing 当作 N.A.。 |
| S1-06 | AD-002 要求 denial 而 resolved selector 产生 `N=0`；另测可选 N.A. | 前者编译失败；后者为带原因的 `None` / N.A.。 |
| S1-07 | 正常聚合与异常 raw 各一次 | receipt 至少含 raw、utility、direction、effective weight、weighted contribution、aggregation version 和相应事件。 |
| S1-08 | 读取 aggregation contract version 不同的历史日志/排行榜 | 旧数据不被按新 utility 规则静默重解释；调用方得到明确版本路径或拒绝。 |

## S2：AGL 距离门

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S2-01 | `sensor.shore-early-warning`，目标 100 m AGL，距离介于 15 km 与 40 km；再改为高于 300 m AGL | 前者因 15 km low range 不可检测，后者按 40 km nominal range 可进入后续检测。 |
| S2-02 | `sensor.picket-radar`，目标恰为 300 m AGL 及刚高于 300 m，距离介于 20 km 与 30 km | 300 m 使用 20 km；高于边界使用 30 km。 |
| S2-03 | 同一目标 MSL、不同 local surface elevation/sea surface；以及 surface elevation 不可取得 | 使用 AGL 而非 MSL 或目标-传感器差；不可取得时得到显式不可计算/拒绝路径，绝不把 MSL 当 AGL。 |
| S2-04 | 无 altitude range profile 的 sensor | 保持其 nominal range，且不触发隐式 300 m 规则。 |
| S2-05 | S2-01/S2-02 的 range gate 失败样本 | 不执行 detection probability 或 measurement RNG，保证随机流未被错误消费。 |
| S2-06 | 旧 Catalog 与新 AD-002 Catalog 各编译一次 | 新资源有不同版本/hash；旧资源的行为与可重放性不被覆盖。 |

## S3 与 S5A：controller scope、own-state 与 Observation

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S3-01 | controller claim 内实体发生通信中断或 HARD jam | 基础 own-state 仍含位置、速度、航向、生命周期、健康、能量。 |
| S5A-01 | 同 faction 有被当前 controller claim 的实体和未被 claim 的实体 | Observation 明示 `controlled_entity_ids`；`own_entities` 只含被 claim 的实体。 |
| S5A-02 | 集中式 controller 显式 claim 全 faction；另测未完整 claim | 完整 claim 才可观察/控制全部；未 claim 实体不因同 faction 泄漏。 |
| S5A-03 | endpoint organic contact 和其他平台 contact | 前者在 organic contacts；后者只有经 transport 成功投递后才在 shared contacts。 |
| S5A-04 | 通信中断、丢包或 TTL 过期的 shared contact | 不成为 shared contact，同时不移除 claim 内基础 own-state。 |
| S5A-05 | 重复 Observation GET | 不推进 tick，不消费 inbox，不改变排序或 visibility。 |
| S5A-06 | controller 向 claim 外实体提交动作 | 被拒绝；该权限测试不把 controller scope 当作 S6 身份鉴权的替代。 |

## S4：环境 capability modifiers

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S4-01 | 新 Catalog 的 clear/cloudy/rainfog 环境各 materialize 一次 | 每个资源 materialize 出实际标准 capability modifier，而不只是 metadata。 |
| S4-02 | 受影响 capability 在三个环境中执行最小检测或对应消费路径 | modifier 影响真实消费者；内核无场景名、环境 ID 或 `visibility_scale` 特判。 |
| S4-03 | modifier 边界、叠加顺序及缺省环境 | 符合既有 modifier order ADR，且无 modifier 时保持基线行为。 |
| S4-04 | 旧环境资源和后续 EF-03 新资源各编译/回放 | 新资源版本/hash 不同；旧资源未被覆盖；不在 EF-01 引入额外环境数值参数。 |

## S5B：航迹共享 transport

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S5B-01 | 非 endpoint 平台生成 contact，经有 route 的 transport | 发送时刻 snapshot 仅在成功投递后成为接收 controller 的 shared contact。 |
| S5B-02 | 无 route、loss 或 TTL 到期 | contact 不共享，且事件/lifecycle 与传输结果一致。 |
| S5B-03 | 非零延迟与 tick quantization | 未早于权威 delivered tick 可见，符合 ADR-010 与 ADR-MD3-006。 |
| S5B-04 | relay、checkpoint、restore | snapshot、route/lifecycle 和可见性重放一致；不重复投递。 |

## S5C：命令 transport 与 endpoint

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S5C-01 | formal V2 有/无 `controller_endpoint_ref`，endpoint 有/无通信组件 | 合法配置编译；缺失或无效 endpoint 编译失败。 |
| S5C-02 | endpoint 绑定实体自身与另一 claim 内实体各收一条命令 | 前者 zero-hop；后者进入 communication transport。 |
| S5C-03 | 非本地命令有 delay | 命令在权威 delivered tick 前不执行。 |
| S5C-04 | 无 route、drop 或 TTL 到期的非本地命令 | 不执行、不消耗弹药、不推进相关 RNG，并产生可审计 transport 结果。 |
| S5C-05 | 相同 command/message identity 重复投递，随后 checkpoint/restore | 执行幂等；恢复后不重复执行或改变顺序。 |
| S5C-06 | 旧场景经 legacy adapter | 有兼容警告和明确版本路径；不恢复 faction 全知视角。 |

## S5D：controller-scoped inbox

| ID | 最小条件与操作 | 必须断言 |
| --- | --- | --- |
| S5D-01 | 私有消息、显式 faction broadcast、发送者自身未列为 recipient | 仅正确 controller 收到；发送者默认不自收。 |
| S5D-02 | 发给其他 controller、未广播同 faction、dropped、blocked、expired 消息 | 全部不进入当前 inbox；contact share 与 command receipt 也不混入 inbox。 |
| S5D-03 | payload 违反 Schema、超过大小限制、或含可执行代码 | 在送入 inbox 前被拒绝并留下可审计失败路径。 |
| S5D-04 | 重复 message ID、同 tick 多条消息、重复 Observation GET | 重复投递幂等；顺序稳定为 `(delivered_tick, message_id)`；GET 不消费。 |
| S5D-05 | 容量小于待投递数，混合已过期及同 tick 消息 | 先删 expired，再按最早 delivered tick，最后按 message ID；每次容量淘汰有 `communication.inbox_evicted`。 |
| S5D-06 | checkpoint/restore 前后含 TTL、已淘汰和去重记录 | 不复活 expired、不重复投递、不改变顺序或淘汰状态。 |

## 通过准则

EF-02 及以后的实现测试必须逐项映射上述 ID，并在实现完成后按阶段允许的 T1/T2 级别执行。EF-01 只冻结设计，未新增测试代码、未运行测试、未进入任何 S1–S5 业务实现。

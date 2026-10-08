# S1–S5 修复需求追踪矩阵

> 创建阶段：EF-01；当前状态：`DONE`。本矩阵只追踪引擎缺陷修复，不改写历史 MD-AD-002 追踪矩阵。

| 缺陷 / 需求 | EF-00 证据 | EF-01 契约状态 | 后续阶段 | 验收证据 |
| --- | --- | --- | --- | --- |
| S1：逐指标方向、量纲与可审计贡献 | `ScoringSystemV2.evaluate` 聚合 raw value，忽略 item direction | EF-02 已实现 `utility-v1`；EF-03 补充修复使 public utility 不会回灌为下一 tick raw input。非 utility 的当前 resolved contract 显式为 `raw-v1`；历史未标版本 receipt/checkpoint 由 `legacy-v1` 兼容读取。resolved selector cardinality、N.A./missing/out-of-range、receipt 和 checkpoint 均受契约测试覆盖 | DONE | `tests/contract/test_engine_defects_s1_scoring_contract.py`（12 passed）；既有评分/编译契约（147 passed） |
| S2：正式 V2 低空探测 | generic sensor 只读取 `range_m`，Catalog 有未消费 `low_altitude_range_m` | 通用 AGL `step` profile 已接入感知距离门；`<=300 m` 低空，地图 surface-elevation 显式提供本地海面，缺失 surface 时 AGL profile 失败关闭；环境量程 modifier 在 profile 选择后生效；旧 profile-less 传感器保持名义量程。新 sensor/map Catalog version 和 hash 不覆盖历史资源 | DONE；S2-01–S2-07，包括 formal receipt、checkpoint/restore 与 resource identity | `tests/contract/test_engine_defects_s2_agl_detection.py`（13 passed）；generic/geography（65 passed）；checkpoint（18 passed）；formal migration（10+7 passed） |
| S3：own-state 不受干扰删除 | jamming target 从 faction `own_entities` 和 contacts 过滤 | faction Observation 已保留 active/degraded 友军的基础 own-state；jamming 继续隔离 shared contact reports 和已有 communication route。严格 claim scope 由 EF-06A 接续 | DONE；S3-01–S3-06，包括 jamming start/end 与 checkpoint restore | `tests/system/test_jamming_observation_v2.py`；checkpoint suite（19 passed） |
| S4：环境 materialize 为零 modifier | AD-002 三资源只含 metadata，materialize 均为 `[]` | 新 `2.1.0` Catalog version 使用标准 `sensor_range_multiplier`，只作用于 `sensor.range`；旧 `2.0.0` 保持 metadata-only/inert，所有数值均标记 `UNVALIDATED_BENCHMARK` | DONE；S4-01–S4-04，包括 medium tick 600 的 weather receipt、checkpoint/restore 和 resource/hash evidence | `tests/contract/test_engine_defects_s4_environment_catalog.py`（8 passed）；`tests/system/test_md_ad_002_v2_migration.py`（17 passed） |
| S5A：controller scope / Observation | Observation 只有 faction scope；ControllerClaim 已有 slot→entity ownership | 严格 claim scope、`controlled_entity_ids`、own/organic/shared/message 分层和显式 legacy warning 已实现；formal V2 endpoint 缺失失败 | DONE | `test_engine_defects_s5a_controller_scope.py`；controller/jamming 组 39 passed |
| S5B：航迹共享 transport | sensor contact 直接写 contact store，再读取 faction view | confirmed organic contact 以发送时刻 snapshot 经 route/delay/TTL/loss/jamming transport 后进入目标 controller shared contacts；checkpoint 已覆盖 | DONE | `test_engine_defects_s5b_contact_transport.py` |
| S5C：命令 transport | active command 直接写 `WorldTickInputV2.entity_commands` | explicit endpoint、self zero-hop、remote command queue、terminal failure isolation 与 checkpoint 已实现 | DONE | `test_engine_defects_s5c_command_transport.py` |
| S5D：消息接收出口 | message delivery 只改变 queue status，Observation 无 inbox | controller-scoped 256 default/1–4096 inbox、TTL、stable eviction、dedupe、checkpoint 与 read-only Observation 已实现；显式 self-recipient 走已记录的 zero-hop transport，未列出的 sender 不接收 | DONE | `test_engine_defects_s5d_inbox.py`；S5D/command/communication 15 passed；EF-07 联合回归 |

## EF-07 联合回归

- `EF-07` 已完成：核心组合 78 passed，S5D 边界组 15 passed，MD-AD-002 V2 38 passed、传统接口/三档 53 passed，MD-INT-003 23 passed；MD-INT-001 当时的 28 项为历史结果，后续已按用户决定退役。
- MD-INT-003 集中 controller 的远端命令现在按 Accepted ADR 的 endpoint transport 在下一 tick 激活；该行为受集成测试保护。

## 已继承的 Accepted 决策

- `docs/decisions/ADR-010-communication-delivery-order.md`：消息不得早于声明的逻辑 tick 可见。
- `docs/adr/ADR-MD3-006-communication-tick-quantization.md`：非零延迟按 `ceil(delay_s / physics_dt)` 量化；TTL、route、loss 与 lifecycle 在投递前决定。
- `docs/decisions/ADR-MDINT001-006-metric-na-reweighting.md` 与 `docs/adr/ADR-MD3-008-score-na-and-missing-data.md`：N/A 为 `None` 且重新归一，required-but-missing 的 utility 为 0 并产生审计证据。

## EF-01 冻结产物

- `docs/adr/ADR-ENGINE-DEFECTS-001-s1-s5-public-contracts.md`：四项用户决定的 Accepted ADR。
- `reports/engine-defects/EF-01_contract_test_design.md`：S1–S5 的最小、可审计契约测试设计与验收 ID。
- 下一工作仅可从 EF-02 起按阶段授权实施；EF-01 不修改业务实现、测试、Schema、Catalog、依赖或场景参数。

## EF-08 / EF-09 收尾

- EF-08 `DONE`：当前树全量 pytest `2047 passed, 1 deselected`，coverage `85.45%`，Bandit 通过；16/32 并发、100 局多 seed、600 s mixed soak 与 HARD 通信高负载均通过。详见 `EF-08.md`。
- EF-09 `DONE`：16 项结构化自审全部通过，P0/P1 为零，`SELF_REVIEWED: true`。详见 `EF-09.md`。
- MD-INT-001 已退役并从公开 registry/CLI/运行时移除；当前正式 V2 场景入口保持 MD-AD-002 与 MD-INT-003。详见 `MD-INT-001_removal.md`。

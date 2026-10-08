# EF-01 公共契约与 ADR 冻结

TASK_ID: EF-01
STATUS: DONE
OBJECTIVE: 在任何实现修改前，冻结 S1–S5 的公开评分、感知、观测与通信语义及兼容策略；不进入 EF-02。
REQ_IDS: EF-01 §7；S1–S5；AR-006；SCR-001；OBS-001/002；CMD-001/003；CHK-001
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`

## 输入与前置结论

- 已完整读取 `reports/engine-defects/EF-00_baseline.md`；EF-00 为 `DONE`，S1–S5 均为 `CONFIRMED`。
- 用户已确认 MD-AD-002 原始需求与实施计划是有意删除；该删除不阻断 EF-01，但不提供可替代的数值或公开语义决策。
- 已读取平台需求、平台实施计划、引擎缺陷修复计划和当前公开 Schema、Catalog、场景、ADR、实现与测试的 EF-00 证据。
- 工作区已有用户修改与未跟踪产物；本阶段不会修改或覆盖它们。

## 权限边界

- ALLOWED_READ: 当前 HEAD 的源码、测试、Schema、Catalog、场景、现有 ADR/报告、Git 元数据与 T0 只读审计输出。
- ALLOWED_WRITE: 本执行记录、需求追踪矩阵、Accepted ADR 与契约测试设计；仅限文档与报告。
- PROHIBITED: 业务源码、测试、Schema、Catalog、依赖和场景参数；EF-02 及后续阶段实现；T4/T5；提交、推送、合并或 PR。

## 执行预算

- TEST_LEVEL: T0
- ALLOWED_COMMANDS: `git status/rev-parse/diff`、`rg`、`sed`、公开 DTO/Catalog/ADR 的静态审计；不执行 pytest。
- PER_COMMAND_TIMEOUT: 120 秒
- TOTAL_TIME_BUDGET: 30 分钟。

## 验收与停止条件

- ADR 必须覆盖 utility 转换、低空定义、观测分层、通信时序、消息读取与兼容策略。
- 追踪矩阵必须把 S1–S5、ADR、后续 EF 阶段与验收映射起来。
- 评分归一范围、低空高度基准或 controller scope 若不能从当前权威材料确定，状态为 `NEEDS_DECISION`；不得以实现默认值、legacy 30 m 阈值或 MD-AD-002 专用分支代替决定。

## 输出

- `reports/engine-defects/EF-01_contract.md`
- `reports/engine-defects/EF_requirements_traceability.md`
- 若准入成立：`docs/adr/ADR-ENGINE-DEFECTS-001-s1-s5-public-contracts.md`

## 已冻结的继承契约

- N/A 保持 `None` 并只对适用 metric 重新归一；required-but-missing 的 utility 为 0，并产生 `metric_data_missing`，不伪装为 N/A。依据 `ADR-MDINT001-006` 与 `ADR-MD3-008`。
- 已有 message transport 保留原始秒值用于审计，权威 delay 使用非零向上取整的 integer tick；route、TTL、loss、lifecycle 和 stable message identity 必须在投递链路中决定。依据 `ADR-010` 与 `ADR-MD3-006`。
- S4 采用 Catalog-only：AD-002 环境在新资源版本中使用通用 capability modifier 键或 `capability_modifiers`，不增加场景名或 `visibility_scale` 内核分支。
- own-state、organic contacts、shared friendly/contact data 与 inbox 必须为不同来源；Observation GET 不推进 tick，也不消费 inbox。

## 已冻结的公开结构

```text
ScoreMetric raw value
  -> declarative normalization bounds/transform
  -> per-metric maximize/minimize utility in [0, 1]
  -> effective-weight contribution
  -> total / competition score / training reward

Observation
  observer_faction_id + controller_slot_id + controlled_entity_ids
  own_entities + shared_friendly_entities
  organic_contacts + shared_contacts + received_messages
  communication metadata
```

低空 profile 使用显式 AGL 基准、`low_altitude_ceiling_m`、`low_altitude_range_m`、`nominal_range_m` 与 `transition`；距离门保持三维斜距，AGL 通过 `geography/surface-elevation` 的地表/海面高程求得。无 profile 的 sensor 维持 nominal range 行为。

## 已接收并冻结的决定

用户于 2026-09-17 明确决定并授权冻结下列四项。完整规范位于 `docs/adr/ADR-ENGINE-DEFECTS-001-s1-s5-public-contracts.md`：

1. S1 的 `[0,1]` utility、动态 `score.denial` 上界 `N`、N.A./missing/out-of-range、聚合和新评分契约版本。
2. S2 的局部地表/海面 AGL、300 m step 边界、两个 AD-002 sensor profile，以及 `UNVALIDATED_BENCHMARK` Catalog 版本化。
3. S3/S5 的严格 claim scope、own/organic/shared 分层、显式 controller endpoint、本地 zero-hop、远端 transport 和 legacy adapter。
4. S5D 的 controller-scoped inbox、接收范围、容量、payload、稳定淘汰、去重、Observation GET 和 checkpoint 契约。

这些决定会改变公开 Observation/Action、评分、Catalog 和 checkpoint 的语义。它们已作为 Accepted ADR 冻结；EF-01 仍不改代码，也不进入 EF-02。

## 执行结果

- 修改文件：本执行记录、需求追踪矩阵、`docs/adr/ADR-ENGINE-DEFECTS-001-s1-s5-public-contracts.md` 与 `reports/engine-defects/EF-01_contract_test_design.md`。
- 实际命令（均退出 0）：读取 `reports/engine-defects/EF-00_baseline.md` 与历史追踪矩阵；读取 ADR-010、ADR-MDINT001-006、ADR-MD3-006、ADR-MD3-008；以 `rg` 审计 ScoreMetric/Observation/controller、sensor altitude 与 message transport 的当前公开路径；读取和静态复核本阶段产物。
- 测试：未运行；EF-01 是 T0 文档/契约审计。
- 审查：完成公共契约、兼容性和确定性边界的只读审查；这不是 EF-09 的结构化代码自审。
- 兼容性与领域影响：新 utility、AGL range profile、controller-scoped Observation 和 inbox 都会改变公开 DTO、日志/checkpoint hash 与旧 agent 适配；ADR 要求新版本、显式 legacy adapter/警告，旧日志和排行榜不得静默重新解释。
- 确定性：继承 ADR-010、ADR-MD3-006、ADR-MDINT001-006、ADR-MD3-008；无运行时变更。
- 准入结论：EF-01 已 `DONE`；契约已足以作为 EF-02 及后续分阶段实施的输入，但依用户指令在此停止，未进入 EF-02。

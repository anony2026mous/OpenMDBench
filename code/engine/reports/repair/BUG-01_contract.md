# BUG-01 生命周期—运动资格契约冻结记录

```text
TASK_ID: BUG-01
STATUS: DONE
OBJECTIVE: 冻结通用 motion_eligible、tick 边界动作投影、失效动作、wreck 和新出生
  实体的契约，为 BUG-02 故障测试和 BUG-03 最小修复提供唯一设计依据。
REQ_IDS: BUG-V2-001; AR-003; AR-005; AR-006; AR-007; ENT-005; LIFE-001;
  CMD-001; CMD-002; CMD-003; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - BASE-00 已完成并在 reports/repair/BASE-00_current_head.md 记录：MD-AD-002-EASY/
    seed 73 于 tick 358 可复现 Session/World 运动集合不一致。
  - 用户已授权按专项计划继续；本阶段严格限于 BUG-01。
ALLOWED_READ:
  - BASE-00 报告；World、Session、Schema、Checkpoint、Catalog、ADR、测试和 Git 只读证据。
ALLOWED_WRITE:
  - reports/repair/BUG-01_contract.md
  - reports/repair/BUG-V2-001_requirements_traceability.md
  - docs/adr/ADR-REPAIR-001-motion-eligibility.md
PROHIBITED:
  - 修改任何业务实现、公开 Schema 定义、测试、Catalog、场景参数、依赖或锁文件。
  - 执行 BUG-02/BUG-03/BUG-04/PERF 阶段，或执行 pytest、T4、T5。
  - 提交、推送、合并、创建 PR、删除文件或修改用户已有工作区改动。
TEST_LEVEL: T0
ALLOWED_COMMANDS:
  - git rev-parse/status/log/blame/diff（只读）
  - rg/sed/find/python 只读检查当前代码、Schema、ADR、测试和既有报告
  - 文档一致性检查（不运行 pytest）
PER_COMMAND_TIMEOUT: 60 s
TOTAL_TIME_BUDGET: 10 min
ACCEPTANCE:
  - 明确 motion_eligible 的唯一事实来源、输入与调用边界；
  - 固化 tick 内 lifecycle、动作投影、motion 的顺序；
  - 定义 persistent/discrete action 在失效、同 tick 失效、checkpoint restore 的语义；
  - 定义 disabled/destroyed/wreck/despawned 的运动、碰撞、日志和恢复语义；
  - 定义新出生动态实体无命令时的安全默认；
  - 结论说明 receipt 是否需 Schema 变更，并给出 BUG-02 的可测试准入。
OUTPUTS:
  - docs/adr/ADR-REPAIR-001-motion-eligibility.md
  - reports/repair/BUG-V2-001_requirements_traceability.md
  - reports/repair/BUG-01_contract.md
STOP_CONDITIONS:
  - 若唯一事实来源、tick 顺序或公开 receipt 语义存在不可由当前证据解决的设计分歧：
    NEEDS_DECISION，禁止进入 BUG-02。
  - 若所需前置报告、Schema 或代码不存在：BLOCKED。
OUTPUT_FORMAT:
  - 状态、范围、修改文件、命令与退出码、测试、审查、兼容性、确定性、领域影响、
    风险与下一阶段准入。
```

## 执行结果

### 修改文件

本阶段仅新增下列文档；未修改源码、公开 Schema、测试、Catalog、场景参数、依赖或锁文件：

1. `docs/adr/ADR-REPAIR-001-motion-eligibility.md`
2. `reports/repair/BUG-V2-001_requirements_traceability.md`
3. `reports/repair/BUG-01_contract.md`

### 实际命令与测试

| 类别 | 退出码 | 结论 |
|---|---:|---|
| 重新读取 `AGENTS.md`、专项计划 BUG-01 段、HEAD 与工作区状态 | 0 | 前置阶段记录存在，当前 HEAD 未变化；用户既有修改保持未触碰。 |
| `rg`/`sed` 审计 Session receipt/status/checkpoint、World lifecycle/damage/restore、capability、现有 ADR 与定向测试 | 0 | 现有公开 receipt/status 可以表达取消与拒绝；World 已保存 lifecycle/policy/queue 恢复所需证据。 |
| 文档与需求追踪产物创建 | 0 | ADR、专项追踪矩阵和阶段报告完整建立。 |
| Python 文档契约检查与受限 `git status` | 0 | 三份文档均为 UTF-8、末尾换行、无尾随空白；确认 `openmdbench/`、`tests/`、`catalog/`、`scenarios/` 无本阶段修改。 |

测试等级为 **T0**：未执行 pytest、T4、T5、性能、并发、压力、soak 或任何场景运行。

### 冻结结论

1. **唯一事实来源**：World 在 pre-motion 边界生成不可变的、稳定排序的
   `MotionEligibilitySnapshot`；Session 只消费该快照投影 commands，World 在 adapter step 前
   复核同一 anchor 与精确命令集合。
2. **资格语义**：实体必须存在、为 `active/degraded`、有精确 dynamics binding/adapter 和
   `dynamics/move` token，且 token 未被运行期 capability 撤销。`disabled`、`destroyed`、
   `wreck`、`despawned` 与 `scheduled` 都不进入 dynamics 命令集合。
3. **动作语义**：失效前已接受的 persistent command 在下个 pre-motion 边界以既有
   `cancelled` 状态移除；已入队的失效 discrete action 以既有 `rejected` 状态终结并写入
   consumed 证据，不产生 weapon RNG、弹药或 request。若实体在 tick 开始仍 eligible 而在
   damage 阶段才失效，本 tick 的合法运动/fire 保持一次性执行，不回溯。
4. **spawn 与 fallback**：当前边界生效的新出生动态实体从 World snapshot 获得 exact binding；
   无有效 persistent command 时只生成该 tick 的 typed safe hold，不写入 active persistent
   表，也不造成命令集合空洞。
5. **wreck/恢复**：wreck 仅以静态 collision candidate 保留，绝不调用主动 dynamics；
   disabled 不冒充 wreck。checkpoint 保存 lifecycle、policy、queue、persistent、consumed 和
   receipt 账本，但不持久化第二份 eligibility 真相；restore 后由 World 重算。
6. **Schema 评估**：不需要公开 schema/version 变化。现有
   `PersistentCommandStatusV2.cancelled`、`DiscreteActionStatusV2.rejected` 与
   `ActionChildReceiptV2.{status,error_code}` 足以表达。若 BUG-03 发现需要公开字段/状态变化，
   必须停止并新建兼容性 ADR。

完整规范见 `ADR-REPAIR-001-motion-eligibility.md`；需求、测试义务和非范围见
`BUG-V2-001_requirements_traceability.md`。

### 审查、兼容性、确定性与领域影响

- 自审：T0 只读复核，确认 ADR 未引入场景 ID、faction、实体 ID、装备参数或 MMG RPC 特例；
  严格集合校验保留，未以降低断言掩盖缺陷。
- 兼容性：公开 Action/receipt/checkpoint schema 不变；客户端将获得现有 lifecycle-invalid
  诊断或稳定 child cancellation/rejection，而非 Session 崩溃。
- 确定性：snapshot、实体 ID、fallback、取消/reject receipt 和 checkpoint 恢复均要求稳定排序，
  但尚未由测试证明；证明留给 BUG-02/B04。
- 领域影响：契约同时覆盖 air、surface、fixed dynamics、disabled、wreck 和 despawn；保持
  `destroyed_lifecycle` 的 Catalog/场景数据政策边界。

### 风险与下一阶段准入

1. **P1 保持开放**：ADR 是设计冻结，尚无故障测试或实现，BASE-00 的 crash 仍存在。
2. **P2 保持隔离**：CLI 二次 `stop()` transition 异常未纳入本阶段；不得在 BUG-03 顺带重构。
3. **实现风险**：World snapshot 必须能表达本 tick 生效的 spawn/despawn 边界，同时不得形成
   第二个可变资格缓存；BUG-02 必须先以 B01–B10 覆盖该边界。

准入结论：**允许进入 BUG-02（T2）建立先失败的 B01–B10 定向测试。**BUG-02 只能修改
与该矩阵直接相关的测试及其阶段记录；不得开始 BUG-03、三档长回归、MMG 优化、T4 或 T5。

# BUG-03 最小实现修复记录

```text
TASK_ID: BUG-03
STATUS: DONE
OBJECTIVE: 让 World 产生唯一、稳定的 pre-motion eligibility projection，且让
  ActionPipeline 只消费它以生成命令/取消失效动作；保留 World 的严格命令集合检查。
REQ_IDS: BUG-V2-001; AR-003; AR-005; AR-006; AR-007; ENT-005; LIFE-001;
  CMD-001; CMD-002; CMD-003; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - BASE-00 已复现 MD-AD-002-EASY/seed 73 tick 358 crash。
  - BUG-01 ADR 已冻结 World-authoritative motion eligibility。
  - BUG-02 B01/B02/B03/B04/B07/B08 已在旧实现可靠红灯；B05/B06/B09/B10 已建立基线。
ALLOWED_READ:
  - BUG-01/02 产物、World/Session/Schema/Checkpoint、直接测试和 git 只读状态。
ALLOWED_WRITE:
  - openmdbench/world/factory_v2.py
  - openmdbench/sessions/lifecycle_v2.py
  - tests/contract/test_motion_eligibility_contract_v2.py
  - reports/repair/BUG-03_minimal_fix.md
  - reports/repair/BUG-V2-001_requirements_traceability.md
PROHIBITED:
  - 场景/faction/entity ID 专用分支、Catalog/场景参数、装备/命中/毁伤/评分变化。
  - 依赖/锁文件、公开 schema/version 改动、MMG RPC 优化、T4/T5、提交/推送/PR。
TEST_LEVEL: T2
ALLOWED_COMMANDS:
  - rg/sed/git 只读；apply_patch 仅改上述直接文件。
  - PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/... .venv/bin/python -m pytest
    tests/contract/test_motion_eligibility_contract_v2.py 及直接 World/Session 定向测试。
PER_COMMAND_TIMEOUT: 15 min
TOTAL_TIME_BUDGET: 20 min
ACCEPTANCE:
  - World 的 snapshot 对 existing/spawn/despawn、lifecycle、runtime capability 和 exact binding
    作稳定排序；Session 不再自行按 dynamics_ref 选择实体。
  - stale persistent 得到 cancelled；stale discrete 得到 rejected+consumed+稳定 child receipt，
    不发起 combat/不消耗资源。
  - 当前 tick 开始 eligible 的动作保持一次性；World strict set check 不删除。
  - B01--B10 和受影响直接回归通过；无公开 Schema 改动。
OUTPUTS:
  - World eligibility projection、Session projection、B01--B10 绿灯及阶段证据。
STOP_CONDITIONS:
  - 若需要改变公开 DTO/receipt schema，或无法表达 spawn/despawn 的单一 World 投影：
    NEEDS_DECISION；不得以放松 World 集合检查替代。
```

## 执行结果

### 修改文件

1. `openmdbench/world/factory_v2.py`
   - 新增不可变 `MotionEligibilityEntryV2` / `MotionEligibilitySnapshotV2`；
   - World 在当前 tick 和唯一的下一 lifecycle batch 上推导 `active_entity_ids` 与
     exact dynamics command entries（lifecycle、runtime token、binding、adapter）；
   - spawn/despawn 的预运动投影和实际 `advance_tick` 采用同一个 lifecycle boundary helper；
   - `advance_tick` 仍在 adapter 前以严格 exact command-set 验证输入，未放松异常条件。
2. `openmdbench/sessions/lifecycle_v2.py`
   - `SessionWorldViewV2` 仅读取 World snapshot；
   - `ActionPipelineV2` 不再以 `entities_stable()+dynamics_ref` 自行选择运动实体，也不再
     独自遍历 schedule 生成 spawn command；
   - stale persistent 生成 `cancelled`，stale discrete 生成 `rejected`、写入 consumed 和
     `session.entity_lifecycle_invalid` child evidence，且不产生 combat/message intent；
   - safe hold controls 改为消费 World entry，新的 spawn 与存量实体都走同一投影。
3. `tests/contract/test_motion_eligibility_contract_v2.py`
   - B07 使用相同 operation identity 比较恢复等价；B09 升级为真正 Session→World spawn
     无动作路径，验证 World snapshot 在 Session 中完成 safety control。
4. `reports/repair/BUG-03_minimal_fix.md`（本记录）。

未改变 Catalog、场景参数、装备参数、命中/毁伤/评分、公开 DTO/schema/version、依赖或锁文件。

### 实际命令与测试

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest tests/contract/test_motion_eligibility_contract_v2.py -q` | 0 | **10 passed**；B01--B10 全部绿灯。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest tests/integration/test_session_action_world_v2.py tests/integration/test_world_motion_pipeline_v2.py tests/contract/test_world_lifecycle_v2.py -q` | 0 | **68 passed**；Session、World motion 与 lifecycle 定向回归通过。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest tests/contract/test_session_action_pipeline_v2.py tests/contract/test_combat_damage_v2.py -q` | 0 | **240 passed**；既有动作、combat/damage 契约通过。 |
| `.venv/bin/python -m compileall -q openmdbench/world/factory_v2.py openmdbench/sessions/lifecycle_v2.py tests/contract/test_motion_eligibility_contract_v2.py` | 0 | 指定源码/测试可编译。 |

上述为 T2 定向测试；未执行 T4/T5、全量 pytest、format/Ruff/mypy/Bandit、压力、并发或 soak。

### 实现不变量核对

- **唯一事实来源**：Session 只调用 `WorldStateV2.motion_eligibility_snapshot()`；没有在
  Session 留下 `entities_stable()+dynamics_ref` 或 lifecycle schedule 的筛选。
- **生命周期**：snapshot 的 `active_entity_ids` 用于动作失效，`entries` 是 runtime
  dynamics/move token、exact binding/adapter 都存在的严格子集；disabled/destroyed 均不进入。
- **动作语义**：本 tick 已开始前 eligible 的 command/action 正常执行；下一个 pre-motion
  boundary 才取消老 persistent / reject queued discrete，动作 ID 会消费且不会在恢复后重放。
- **spawn/despawn**：snapshot 投影同一下一 lifecycle batch，spawn 获得 typed fallback；despawn
  从 active/command projection 移除。
- **wreck**：没有将无 motion command 解释为删除；既有 `destroyed_lifecycle` policy 和静态 wreck
  collision path 未改动。
- **严格检查**：`_invoke_motion_provider` 的 exact ID/tick 检查不变，错误现在不会来自 Session
  的过时复制集合。

### 审查、兼容性、确定性与领域影响

- 自审：对所有新增条件检查 `scenario_id`、固定 faction、MD-AD-002、固定 interceptor ID，
  均不存在；不存在放宽 World command-set 异常或绕过 adapter 的分支。
- 兼容性：没有 public Pydantic schema/version 变动；沿用已有 child `status`/`error_code`、
  `PersistentCommandStatusV2.cancelled` 和 `DiscreteActionStatusV2.rejected`。
- 确定性：entry、active IDs、fallback controls、cancel/reject children 和生成 commands 均稳定
  排序；B07/B10 以 checkpoint/映射顺序验证。跨场景和跨接口的完整确定性由 BUG-04 验收。
- 领域影响：机制对 air、surface、fixed dynamics、spawn、disabled、destroyed/wreck 均通用，
  没有污染任务数据。

### 风险与下一阶段准入

1. BASE-00 的 CLI 二次 `stop()` transition P2 未改，仍独立记录；本 P1 修复不需要触碰它。
2. B01--B10 和 T2 证明局部契约；尚未证明 MD-AD-002 三档自然终局、Python/Gym/REST、
   VisualizationFrame/log/score 与完整 checkpoint 边界等价。
3. 预运动 snapshot 是从 checkpoint 可导出的 transient projection，未序列化；必须由 BUG-04
   验证 restore 后同 seed/动作序列的外部结果。

准入结论：**允许进入 BUG-04（T3）场景、接口和恢复回归。**不得开始 PERF-00，直到 BUG-04
所有 P0/P1 定向回归通过。

## BUG-04 反馈修复（同一 BUG-03 范围）

BUG-04 首次长局并未再出现 motion command-set crash，但 HARD 结束时 `session.checkpoint()`
暴露 `session child and status ledgers disagree`。根因是早已存在的 fallback receipt 写入
`_child_ledger` 时没有同步写入 `_statuses`；本次失效动作修复令更多长局路径可靠进入完整
checkpoint，因此该账本闭包缺口被暴露。它属于动作持久化契约，必须在进入性能阶段前关闭。

- 最小修复：创建 `fallback.safe_hold.<entity>` child receipt 时同步写入 `active` status；不改变
  fallback command、World input、动作调度、Schema 或 checkpoint 格式。
- 新增回归：`test_expired_command_fallback_remains_checkpoint_consistent`，先使 persistent command
  过期并生成 fallback，再验证 status 与 receipt 一致且 checkpoint 可构造。
- 复测：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest
  tests/contract/test_motion_eligibility_contract_v2.py tests/integration/test_session_action_world_v2.py -q`
  退出码 0，**39 passed**。

该修复不扩展至 CLI stop P2、MMG RPC 或任何场景数据；BUG-04 已重新执行真实三档长局和接口回归。

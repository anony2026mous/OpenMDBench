# BUG-02 故障测试先行记录

```text
TASK_ID: BUG-02
STATUS: DONE
OBJECTIVE: 在不修改生产实现的前提下，为 BUG-V2-001 建立 B01--B10 的定向故障回归测试；
  当前实现必须至少在 B01 的真实生命周期--运动边界上稳定失败。
REQ_IDS: BUG-V2-001; AR-003; AR-005; AR-006; AR-007; ENT-005; LIFE-001;
  CMD-001; CMD-002; CMD-003; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - BASE-00 已以 MD-AD-002-EASY/seed 73 复现 tick 358 的严格命令集合异常。
  - BUG-01 已冻结 World-authoritative motion eligibility 与动作取消/reject 语义。
  - 用户已授权按专项计划连续执行；本阶段仍严格限于 BUG-02。
ALLOWED_READ:
  - BUG-01 ADR/追踪/报告、World/Session/Checkpoint/Combat 实现、直接 fixtures 和测试。
ALLOWED_WRITE:
  - tests/contract/test_motion_eligibility_contract_v2.py
  - reports/repair/BUG-02_failure_tests.md
  - reports/repair/BUG-V2-001_requirements_traceability.md
PROHIBITED:
  - 修改 openmdbench 生产源码、公开 Schema、Catalog、场景参数、依赖或锁文件。
  - 执行 BUG-03/BUG-04/PERF 实现、T4、T5、全量 pytest、并发/压力/soak。
  - 提交、推送、合并、创建 PR、删除文件或修改无关用户工作区内容。
TEST_LEVEL: T2
ALLOWED_COMMANDS:
  - rg/sed/find/git 只读审计；apply_patch 新增直接故障测试和阶段记录。
  - .venv/bin/python -m pytest tests/contract/test_motion_eligibility_contract_v2.py
    及该文件中的单一测试选择；每次不超过 15 分钟。
PER_COMMAND_TIMEOUT: 15 min
TOTAL_TIME_BUDGET: 15 min
ACCEPTANCE:
  - B01--B10 均有外部契约断言，不依赖场景/faction/fixed ID 特判；
  - 当前实现的 B01 可稳定暴露原始集合不一致，修复前失败被如实记录；
  - 测试覆盖失效、persistent/discrete、同 tick、wreck/despawn、restore、spawn、
    同时毁伤及稳定顺序义务；
  - 不对生产实现或测试以外范围产生行为改动。
OUTPUTS:
  - tests/contract/test_motion_eligibility_contract_v2.py
  - reports/repair/BUG-02_failure_tests.md
STOP_CONDITIONS:
  - 若无法构造不依赖生产内部私有细节的故障测试，或旧实现不再复现 BASE-00 根因：
    状态 NEEDS_DECISION，不得开始 BUG-03。
  - 若测试暴露与 BUG-V2-001 无关的确定性或 fixture 故障：如实记录并缩小测试，
    不修改生产实现。
```

## 执行结果

### 修改文件

1. `tests/contract/test_motion_eligibility_contract_v2.py`（新增）：B01--B10 的通用
   生命周期--运动资格测试；使用既有 resolved/World/Session fixture，未使用 MD-AD-002、
   faction 或固定任务场景分支。
2. `reports/repair/BUG-02_failure_tests.md`（本记录）。

未修改任何 `openmdbench/` 生产实现、Schema、Catalog、场景参数、依赖或锁文件。

### 实际命令与结果

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `.venv/bin/python -c ... apply_damage_transaction ... session.step(...)` | 1 | 复现 `disabled` 后 Session 仍生成该实体 command、World 仅期待另一个 active entity 的原始故障。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest ...::test_b01... -q` | 1 | B01 稳定失败于 `factory_v2.py:_invoke_motion_provider` 的严格集合校验；实际 `{'asset.000','asset.001'}` 对预期 `{'asset.001'}`。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ... pytest tests/contract/test_motion_eligibility_contract_v2.py -q` | 1 | 10 项中 4 通过、6 失败；失败均为 BUG-V2-001 预期红灯，无 fixture/环境错误。 |

首次 pytest 未禁用外部自动加载插件时受到系统 ROS `launch_testing` 缺失 `lark` 的影响，
未运行到项目测试收集；随后使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 重跑并获得有效结果。
这只是环境隔离措施，不是测试跳过或验收放宽。

### 红灯证据与矩阵覆盖

| 编号 | 覆盖 | 当前结果 | 旧实现根因/证据 |
|---|---|---|---|
| B01 | 上一边界 disabled 不再进入 motion | 失败 | Session 仍按 `dynamics_ref` 生成 command；World 仅接受 `active/degraded`，抛 `World tick requires exactly one current command...`。 |
| B02 | pre-motion queued persistent/discrete 取消/reject | 失败 | `_revalidate_child` 直接抛 `session.entity_lifecycle_invalid`，不能产生日志化 child receipt。 |
| B03 | persistent 取消且永不复活 | 失败 | active persistent 未按 World lifecycle 投影过滤，下一 tick 命令集合仍包括 disabled 实体。 |
| B04 | tick-start 合法 move/fire 仅一次，下一边界失效 | 失败 | 首 tick 正常消费一次；下一 tick 再现集合错配。 |
| B05 | wreck policy | 通过 | 已有通用 resolved policy 将 destroyed 保留为 static wreck。 |
| B06 | despawn policy | 通过 | 已有通用 resolved policy 清理实体并保留 tombstone。 |
| B07 | invalidation checkpoint/restore 等价 | 失败 | restore 后仍在 apply boundary 直接抛 lifecycle invalid，而非确定性取消/reject。 |
| B08 | non-active action 无 ammo/combat 副作用 | 失败 | 与 B02 相同的直接 SessionFailure，尚无终态 rejected/consumed receipt。 |
| B09 | spawn 首边界完整 safe control | 通过 | 已有 World tick spawn 与显式 typed safe control 契约正常。 |
| B10 | simultaneous damage map order stable | 通过 | World damage 聚合稳定排序正常。 |

### 审查、兼容性、确定性与领域影响

- 自审：测试只断言外部 receipt、world receipt、lifecycle、checkpoint 和资源结果；没有改弱
  既有严格 World 集合检查，也没有把内部实现行号作为断言。
- 兼容性：测试按 BUG-01 已冻结的既有 `cancelled/rejected`、`error_code` 语义编写，不要求
  新公开 Schema。
- 确定性：B07/B10 覆盖 restore/顺序；尚为红灯/最小 baseline，BUG-04 才做跨场景完整证明。
- 领域影响：fixture 覆盖 generic air-like dynamics，B05/B06 覆盖 surface wreck/despawn，
  B09 覆盖 spawn；未绑定任何场景专名。

### 风险与下一阶段准入

- BUG-V2-001 仍为 P1：B01/B02/B03/B04/B07/B08 已可靠失败，说明原始崩溃和取消 receipt 缺失
  均被测试锚定。
- B09 目前经 World 显式 typed safe control 覆盖；BUG-03 必须把 scheduled spawn 的资格来源
  收敛至同一 World snapshot，不能保留 Session 的复制筛选。
- ROS 插件自动加载环境噪声已隔离；项目目标 pytest 可正常执行。

准入结论：**允许进入 BUG-03（T2）最小实现。**仅可修改 World/Session 与本测试的直接路径；
不得开始 BUG-04、MMG 优化、T4/T5、场景参数或依赖变更。

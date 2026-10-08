# MD3-04 自爆、碰撞、残骸与生命周期报告

## 状态

`DONE`：首轮只读审查提出的 2 项 P0、1 项 P1 均已修复；修复后的 T2/T3 定向验证和
冻结范围结构化代码自审均已完成，结论为 `SELF_REVIEWED`、剩余 P0/P1 为零。

状态依据更新后的 `AGENTS.md` 3.2：MD3 阶段由当前 Codex 顺序实现、测试和自审；
`SELF_REVIEWED` 不表示独立第三方审查。

## 审查问题与修复

首轮只读审查发现的以下问题均已在同一通用路径中修复，未加入场景、阵营、平台或
实体 ID 特判：

1. **P0：次级殉爆受 `session_id` 影响。** 子流现在由
   `resolved_hash + session_seed + trigger/source/evidence identity` 派生；`session_id`
   不再参与殉爆采样。新增相同 seed、不同 session ID 的 trigger/DamageIntent/ledger
   等价测试，并检查其 checkpoint evidence。
2. **P0：非致命来源可再次触发。** 新增不可变检查点状态
   `spatial_effect_trigger_consumption`，键为 `resolved_hash + trigger_id + source_entity_id`。
   首次连续 zone/collision evidence 只用于审计与排序；来源即使未被毁伤、再次相撞或
   restore 后再次进入，也不会生成第二个 DamageIntent。
3. **P1：所有 destroyed 实体被隐式视为 wreck。** `EntitySpecV2`/`ResolvedEntityV2`
   新增通用 `destroyed_lifecycle: wreck|despawn`。所有 DamageIntent 来源（武器、碰撞、
   apply-effect、spatial trigger）均在同一 simultaneous damage batch 后经
   `destroyed_lifecycle_ledger` 裁决。仅该 ledger 记录为 `wreck` 的 destroyed 实体保留
   碰撞候选；`despawn` 生成 tombstone、清理 adapter/contact 并从 spatial topology 移除。
   默认值为 `wreck`，仅为旧场景包的既有运行兼容；新场景可显式写 `despawn`。

新测试覆盖：非致命重复 collision、restore 后重复 collision、不同 session ID 的同 seed
殉爆、普通武器毁伤的 `wreck|despawn`、两类策略的 checkpoint 恢复。既有高速 crossing、
自爆、二次过滤、wreck 再碰撞和 trigger-despawn 测试继续保留。

## 执行记录

| 字段 | 记录 |
| --- | --- |
| TASK_ID / 阶段 | `MD3-04-001` / `MD3-04` |
| 需求 | `REQ-DMG-001..003`、`REQ-CBT-003`、`REQ-ARCH-001`、`REQ-ARCH-004` |
| 引擎 / Schema | `2.0.0` / `2.0` |
| Catalog / 地图 | `sha256:278377eedacd2fc1e93e10c51edf755f26b1b052eaa9b187afdb5f4624fcc24f` / `map.weihai-local@2.0.0` |
| 场景 / seed / 插件 | 本阶段使用改名合成契约场景；确定性 session seed；`none` |
| 参数可信度 | U7 的殉爆概率、半径等仍为 `UNVALIDATED_BENCHMARK`；本阶段未作真实装备标定声明 |
| 环境 | Ubuntu、`.venv/bin/python`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`MPLCONFIGDIR=/tmp/openmdbench-mpl` |

## 实现范围

- [core_v2.py](../../openmdbench/schemas/core_v2.py)：增加通用声明事件
  `spatial_effect_trigger` 及实体 `destroyed_lifecycle` 策略，不引入任务、阵营、平台或
  实体 ID 字段。
- [declarative_v2.py](../../openmdbench/scenarios/declarative_v2.py)：严格编译和冻结
  source kind（`zone_entry`/`collision`）、来源实体、区域、Effect/Damage 闭包、主/次
  target selector 与 `wreck`/`despawn` 生命周期策略；未知端点、区域、二次链或非法
  概率在编译/完整性检查时拒绝。
- [factory_v2.py](../../openmdbench/world/factory_v2.py)：
  - 用既有连续 zone transition 与 TOI collision evidence 驱动一次性 trigger；
  - 所有主/次作用都生成 `environment` `DamageIntent`，再经同一
    `apply_damage_transaction` 同时结算；没有场景数据直接写 health 或 lifecycle；
  - trigger 的 `tick` 是**最早激活 tick**；事件 ID 仅在首个实际 source event 发生时
    进入权威 event evidence，因而任务规则不会在“预先布设 trigger”时误锁存；
  - secondary 使用 `resolved_hash + session_seed + trigger/source evidence` 的 SHA-256
    命名子流采样，不读取全局 RNG 或 session ID；半径来自 Effect Profile，selector 支持
    排除端点；
  - `spatial_effect_trigger_consumption` 将 trigger/source 锁存为一次性状态并随 checkpoint
    恢复；evidence identity 不再充当幂等键；
  - 所有来源的 destroyed 实体均在 `destroyed_lifecycle_ledger` 中按数据策略裁决：只有
    `wreck` 记录进入 `lifecycle_wreck` 静态候选；`despawn` 清理 contact、adapter 与
    spatial topology 并写 tombstone。destroyed 实体不再接受 dynamics command、传感、通信
    或 fire。
- [checkpoint_v2.py](../../openmdbench/world/checkpoint_v2.py)：checkpoint 记录 armed
  trigger 和已触发 authority ledger；校验 wreck/despawn/tombstone 一致性。恢复时可正确
  重建动态 despawn 的 active topology，且不会重复触发。
- [test_md_int_003_damage_lifecycle.py](../../tests/contract/test_md_int_003_damage_lifecycle.py)：
  通过普通 Compiler 生成改名合成场景，覆盖 collision、连续高速 crossing、secondary
  filter/独立采样、wreck 再碰撞、inactive subsystem、despawn 和两类 checkpoint 恢复。

本阶段只在 `factory_v2.py` 的既有单一 World tick、Damage 和 checkpoint 路径增加通用
机制；该文件开始前已经存在的 append-only tick、presentation 和 MD3-03 pending-impact
未提交改动未被回退或替换。

## 行为与领域结论

1. zone 与 collision 的来源证据按连续 `time_fraction`、稳定实体/事件标识处理；命中
   intent 仍在同一 tick 汇总，因此实体注册顺序不改变毁伤结果。
2. self detonation 一次性 authority ID 由 resolved hash、trigger、source entity 和 source
   evidence 派生；ledger 随 checkpoint 恢复，重复 crossing 或 restore 不会重复爆炸。
3. 若 source 同 tick 既遭毁伤又进入区域，source event 先形成 intent，与外部 intent 同时
   结算；随后再根据结算后的 lifecycle 执行 `wreck` 或 `despawn`。这避免了顺序依赖。
4. `wreck` 是已被 DamageSystem 标为 destroyed 的静态空间对象，而不是第二套实体模型；
   `despawn` 使用 tombstone 保留审计身份。

## 验证

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_md_int_003_damage_lifecycle.py \
  tests/contract/test_md_int_003_surface_combat.py \
  tests/contract/test_combat_damage_v2.py \
  tests/contract/test_world_entity_factory_v2.py \
  tests/contract/test_md_int_003_catalog_closure.py
```

结果：`285 passed in 27.02s`。

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_declarative_resource_expansion_v2.py \
  tests/contract/test_geography_boundary_v2.py \
  tests/contract/test_world_checkpoint_v2.py
```

结果：`201 passed in 7.27s`。

另已执行本阶段生产模块与新测试的 `py_compile`、限定文件的 `git diff --check`，均通过。
对 `declarative_v2.py`、`core_v2.py`、`factory_v2.py`、`checkpoint_v2.py` 的生产扫描未发现
`MD-INT-003`、合成场景/阵营/实体 ID 特判。未运行 T4/T5、全量、性能、并发、压力、安全
或长稳测试。

## 代码审查与兼容性

- 结构化代码自审（`SELF_REVIEWED`）：冻结修复范围后审阅单一 World/Damage authority、
  scenario 旁路、session/RNG 依赖、一次性消费键、通用 lifecycle policy、静态 wreck
  候选、checkpoint 完整性与恢复拓扑，以及故障导向测试；未发现剩余 P0/P1。
- 首轮只读审查的 2 P0/1 P1 已逐项修复并纳入定向回归；按更新后的 `AGENTS.md`，不再把
  新的外部审查会话作为本阶段门禁，也不将本结论表述为独立审查。
- 兼容性：MD3-03 delayed surface impact、既有 combat/damage、world factory、Compiler、
  geography/collision 与 canonical checkpoint 定向回归均通过。
- 风险：为保持既有场景兼容，未声明策略的实体 resolve 为 `wreck`；新场景若不希望被毁实体
  留在空间拓扑中，必须显式声明 `destroyed_lifecycle: despawn`。MD3-07 将在正式场景数据中
  显式选择该策略；MD3-08 再覆盖 Agent 接口层。

## 下一步

MD3-04 已完成；下一步按阶段顺序建立 MD3-05 执行记录，并先实现通用拦截辅助、
弧形几何与任务/评分机制。

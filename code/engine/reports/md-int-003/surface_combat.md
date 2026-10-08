# MD3-03 通用对海交战报告

## 结论

V2 的单一 `CombatSystemV2` 现已支持通用 `surface` 目标域与
`delayed_effect`、`contact_detonation` 投送模式。合法发射在 launch tick 记录独立 RNG 证据、扣除弹药与
能源、设置冷却并创建不可变待决打击；待决打击在下一仿真 tick 经同一
`Effect → DamageIntent → simultaneous DamageResolution` 路径消费一次。实现中没有
场景、阵营、平台或实体 ID 特判。

## 执行记录

| 字段 | 记录 |
| --- | --- |
| TASK_ID / 阶段 | `MD3-03-001` / `MD3-03` |
| 分支 / 基线 | `refactor` / `e85523f`（工作树在开始前已含其他未提交改动） |
| 引擎 / Schema | `2.0.0` / `2.0` |
| 场景 / Catalog / 地图 | `N/A`（本阶段不创建 ScenarioPackage） / `sha256:278377eedacd2fc1e93e10c51edf755f26b1b052eaa9b187afdb5f4624fcc24f` / `map.weihai-local@2.0.0` |
| 插件 / seed | `none` / 合成契约案例由已编译资源闭包与确定性 weapon seed 派生 |
| 环境 | Ubuntu；Python `.venv/bin/python`；`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`；`MPLCONFIGDIR=/tmp/openmdbench-mpl` |

## 实现范围

- [combat/models_v2.py](../../openmdbench/combat/models_v2.py)：新增冻结的
  `PendingImpactV2` 与 `PendingImpactReceiptV2`，并为 `WeaponExecutionV2` 增加
  `pending_impact_ids`。
- [combat/system_v2.py](../../openmdbench/combat/system_v2.py)：将 delivery model
  明确为 `instant`、`guided_missile`、`delayed_effect`、`contact_detonation`；验证延迟配置；在合法发射时
  建立按 shot 编号的待决记录；在到期 tick 只消费一次并产生权威 DamageIntent。
- [combat/v2.py](../../openmdbench/combat/v2.py)：公开待决打击 DTO。
- [world/factory_v2.py](../../openmdbench/world/factory_v2.py)：World tick 在导弹推进后、
  新发射前消费到期打击，并将其与导弹/事件 DamageIntent 合并后做同 tick 结算；增加
  只读待决查询。
- [world/checkpoint_v2.py](../../openmdbench/world/checkpoint_v2.py)：把未到期打击和
  已消费回执纳入 canonical `WorldCheckpointV2`，检查排序、唯一性、时间和实体锚点。
- [新增契约测试](../../tests/contract/test_md_int_003_surface_combat.py)：通过正常
  V2 compiler 构建改名的 surface 合成案例，不依赖 MD-INT-003 场景名或固定实体 ID。

已有的 `factory_v2.py` 在本阶段开始时已经包含 append-only tick / presentation
相关未提交改动；本阶段只在其既有统一 tick 和 checkpoint 路径增加待决打击字段与合并点，
没有覆盖或回退这些改动。

## 行为与确定性

1. `impact_delay_ticks` 允许 `delayed_effect` 与 `contact_detonation` 使用，且必须至少为 1；`instant` 和
   `guided_missile` 继续要求 0，避免隐式改变旧武器时间线。二者均在同一 pending-impact
   authority 中记录、恢复和结算；不同之处只来自 Catalog delivery data 与既有包线/接触合法性。
2. 每个发射 shot 有独立确定性 seed 与 `ShotEvidenceV2`。合法性检查在 RNG/弹药/队列
   修改之前完成；失败请求不会创建 pending impact，也不会推进 weapon RNG。
3. 待决 ID 由 `request_id + shot_index` 派生；待决对象在 launch tick 已锚定 effect、
   damage model、shot evidence、发射点和目标初始点。到期后产生一次 receipt，随后从队列
   删除，重复 tick 不会重复毁伤。
4. 待决对象和已消费回执均进入 checkpoint；恢复后继续同一条时间线，且不会重复结算。
5. 对海命中仍只通过现有 `DamageIntent` 进入 `apply_damage_transaction`，不存在直接写
   `health` 或生命周期的旁路。

## 验证

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_md_int_003_surface_combat.py \
  tests/contract/test_combat_damage_v2.py \
  tests/contract/test_world_entity_factory_v2.py \
  tests/contract/test_md_int_003_catalog_closure.py
```

结果：`277 passed in 24.79s`。

覆盖：改名 surface 平台的 launch/next-tick hit/第三 tick 无重复、弹药扣除、checkpoint
恢复、非法请求无 RNG/弹药/待决副作用；并回归 instant、guided missile、World checkpoint
与 MD3-02 Catalog 闭包。

另执行：

```text
.venv/bin/python -m py_compile [本阶段 5 个生产模块与新测试]
git diff --check -- [本阶段生产模块、新测试、MD3 报告]
rg -n 'MD-INT-003|md_int_003|renamed\.surface|faction\.defender|faction\.attacker' \
  openmdbench/combat openmdbench/world openmdbench/schemas
```

结果：语法与空白检查通过；生产代码扫描无场景/合成测试名称或 faction/实体 ID 命中。

## 代码审查

- **架构**：一个 Combat authority；新行为从 Catalog delivery data 驱动，未建立 parallel
  system 或 scenario branch。
- **领域**：surface 仅由现有 `target_domain in profile.target_domains` 通用矩阵处理；
  对海资源仍为 `UNVALIDATED_BENCHMARK`，本阶段不修改 Pk、弹药或毁伤标定。
- **状态**：Catalog 只存定义；pending/RNG/ammo/cooldown/receipt 均为 World 会话状态，
  同时被 checkpoint 审计。
- **兼容**：既有 209 项 combat/damage 契约和更广的 277 项定向组合回归均通过；
  `guided_missile` 分支没有改变。
- **风险**：World tick 已采用 append-only、失败即锁定策略。若到期 DamageIntent 的后续
  World stage 异常，世界将终止而不是回滚；这与当前项目的“对局中不回滚”决策一致，且
  失败不会继续运行造成重复执行。

## MD3-03-002 回补

MD3-07 的正式场景会话装载证明，Catalog 中已声明的 `contact_detonation` 曾被 profile
白名单拒绝。该缺口已在不改变 Catalog、场景或协议的前提下修复：它与
`delayed_effect` 一样要求正整数延迟，并沿用同一 legality → ShotEvidence →
PendingImpact → DamageIntent → Lifecycle 路径；未知 delivery model 仍被稳定拒绝。

新增故障导向合同测试验证了 contact delivery 的 launch、next-tick 单次命中和 weapon
source evidence。聚焦战斗、World checkpoint、MD-AD formal rule/migration 回归以及
MD-INT-003 L1 公开代理会话均已执行；未运行 T4/T5。所有装备数值仍为
`UNVALIDATED_BENCHMARK`。

## 后续边界

- zone/collision trigger、despawn/wreck 和 secondary explosion 已由 MD3-04 完成。
- 分段 Pk、core-zone/neutral ROE 条件和 engagement capacity 仍由 MD3-04/05 的
  通用事件、几何和任务规则中补齐。
- 当前返回 MD3-07，继续三档 data-only 场景、规则代理与系统级验证。

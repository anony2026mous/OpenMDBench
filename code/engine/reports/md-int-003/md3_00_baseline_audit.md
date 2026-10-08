# MD3-00 基线、架构与领域审计

## 记录

- TASK_ID：`MD3-00-001`
- 阶段：`MD3-00`
- 审计时间：2026-09-02（Asia/Shanghai）
- Git：`refactor` / `e85523f`
- 运行环境：Python `3.11.15`；测试使用项目 `.venv`
- 取样引擎/schema：`2.0.0` / `2.0`；scenario `md-ad-002.easy.v2`；seed `0`（编译取样）
- 取样可复现锚点：resolved `sha256:34f8322ccbdb8ce915002dc8d886235a87b61e833dd6069c992cf8f01e6c1f66`；catalog `sha256:cf34729fad371b07f58d3f4f66ff7cb975a00f97cc716a93b3a2527650ba6350`；map `map.weihai-local@2.0.0` / `sha256:c40a43035b62340c558e1c697823a574b936b50123acb49c4754b4c1d79c398d`；registry/plugin `sha256:573277d4e4495e4b6a22c9cb33fbdbe0fb70020925d8c717009ac503e91af69a` / none
- 结论：`PARTIAL — MD3-00 通过；可进入 MD3-01，不得直接开始 MD3-02 或生产代码修改。`

本阶段仅新增本目录中的审计报告和执行记录。没有修改生产代码、Schema、Catalog、场景包、测试、依赖或配置。

## 起始工作树基线

开始时工作树已脏，包含 `AGENTS.md`、V2 mission/replay/session/world/visualization 代码和多份测试的已修改项，另有地图脚本、可视化 JSONL、MD-INT-003 规范及多份 Word/Markdown 文档等未跟踪文件。它们均不属于本阶段，不回退、不格式化、不纳入实现结论。

`git diff --check` 对既有 `AGENTS.md` 报告了尾随空白；该问题没有在本阶段修复。生产代码扫描未发现 `MD-INT-003`、`MD-INT-003a/b/c` 字符串。旧兼容路径中仍存在固定 `red/blue`、MD-AD 和 MD-INT-001 代码（例如 `openmdbench/runners/md_ad_002.py`、`openmdbench/missions/md_ad_002.py`）；MD3 必须只经 V2 formal 路径接入，禁止复用那些场景专用机制。

## 架构审计

| 主题 | 证据 | 结论 |
|---|---|---|
| 正式 V2 入口 | `scenarios/formal_v2.py:load_formal_scenario_v2/compile_formal_scenario_v2` → `ScenarioPackageV2` → `ScenarioCompilerV2` → `ResolvedScenarioV2` | `VERIFIED`：MD-INT-003 应走此链路。 |
| 会话与世界 | `sessions/formal_v2.py:create_formal_session_v2` → `SessionLifecycleV2.create` → `WorldFactoryV2.build` | `VERIFIED`：无需第二 World 或主循环。 |
| Agent 边界 | `sessions/gateway_v2.py:AgentGatewayV2` 只暴露 observation、submit、step、checkpoint、frame；`sessions/commands.py:CommandQueue` 处理队列和幂等 | `VERIFIED`：统一 ActionBatch/receipt 边界存在。 |
| 编译与冻结 | `scenarios/declarative_v2.py:ScenarioCompilerV2` 有 schema、资源版本、关系、编组、兼容、坐标、边界、事件、任务、可见性、稳定排序和 hash 阶段 | `VERIFIED`：新场景应声明式编译为不可变 resolved。 |
| Catalog/Registry | `catalog/v2.py:CatalogV2/ModelRegistryV2`，`catalog/formal_v2.py:load_catalog_bundle_v2` | `VERIFIED`：可增资源，不应把运行态放入 Catalog。 |
| Scenario ID 特判 | V2 compiler/world/combat/session 的既有反特判契约测试；扫描未发现 MD3 ID | `VERIFIED`（仅 V2 production path）。legacy 目录是隔离风险，不得调用。 |
| 旧并行路径 | `scenarios/compiler.py` 是 compatibility facade，`scenarios/resolved.py` 和 `catalog/models.py` 是旧 schema 路径 | `PARTIAL`：边界已隔离，但文档/导入时易误用；MD3 文档和测试必须显式引用 `*_v2` formal API。 |
| Frame/Replay/Checkpoint | `visualization/formal_v2.py`、`replay/v2.py`、`world/checkpoint_v2.py`、`SessionLifecycleV2` | `PARTIAL`：通用 DTO 和恢复锚点存在；MD3 所需四视角、水面专用覆盖物、pending impact/环境恢复尚未逐项证明。 |

已编译取样的 world tick 为 `1.0 s`，现有实体域为 `air/land/surface`。

## 领域审计

| 项目 | 状态 | 证据与影响 |
|---|---|---|
| MMG、单位、隔离与确定性 | `VERIFIED` | `dynamics/sim2sea_mmg_worker.py` 在每 adapter 子进程中创建 Taichi/Sim2Sea；`native_v2.py:NativeDynamicsAdapterV2._step_mmg` 验证 NPS、舵角、`dt` 和快照。`test_surface_picket_uses_isolated_mmg_through_public_navigation` 已通过。红蓝 USV 参数档案仍是 `UNVALIDATED_BENCHMARK`。 |
| WGS84/local/map、航向 | `VERIFIED` | `world/geography_v2.py:GeographyServiceV2` 和 `core/units.py`；`test_geography_boundary_v2.py` 覆盖坐标往返、北为 0°、高速 sweep。P0/封锁弧/航道仍未建为 MD3 data。 |
| 威海海陆、浅滩与部署 | `PARTIAL` | `catalog/v2/md_ad_002.yaml` 已有 `map.weihai-local@2.0.0`，compiler 在 `declarative_v2.py:_terrain_deployment` 对 surface/underwater 加入 terrain 约束；但 MD3 的 P0、出生区和实点海陆核验尚未完成。 |
| 边界、连续碰撞与 effect | `VERIFIED` | `world/boundary_v2.py`、`factory_v2.py:apply_motion_candidates`；契约测试覆盖切线、高速穿越、实体碰撞和 damage intent。MD3 仍需数据化区分 attacker grounding 与 defender constrain/safety。 |
| surface 目标域 | `VERIFIED` | `schemas/core_v2.py:EntitySpecV2.target_domains`、`catalog/v2.py:validate_full_composition`、`combat/system_v2.py` 使用运行时 target domain；但现有正式 Catalog 的实装武器/传感器为对空资源。 |
| 对海传感/融合 | `PARTIAL` | `systems/generic_v2.py` 可生成带位置、速度、方位、距离、概率、命名随机子流的点迹；目前不执行目标域兼容、量测噪声、两帧确认、三秒 stale 或融合航迹。 |
| 通信 | `PARTIAL` | `systems/generic_v2.py` 仅生成端点清单和队列数量，`factory_v2.py:_apply_message_intents` 同 tick 投递。距离/地形/跳数、延迟、TTL、丢包和融合航迹经链路共享均未接线。 |
| 能源 | `PARTIAL` | generic subsystem 有 idle+motion 消耗；无传感、中继、开火、高海况功耗组合，也未证明低能量 capability 降级或补能动作。 |
| 天气/环境修饰 | `PARTIAL` | `weather_change` 和 `component_suppression` 是受控事件（`factory_v2.py:_execute_typed_events`），当前只记录 state/suppression；未把高海况倍率接至 dynamics、sensor、weapon、energy、communication。 |
| 武器、Effect、Damage、lifecycle | `VERIFIED` | `combat/system_v2.py` 合法性→shot RNG→Effect/DamageIntent；`factory_v2.py:apply_damage_transaction` 做稳定聚合和同时应用；`schemas/domain_v2.py` 有 degraded/disabled/destroyed/despawned。自爆 trigger、残骸静态障碍、殉爆过滤仍 `ABSENT`。 |
| 导弹/延迟命中 | `PARTIAL` | 已有 `world/missile_v2.py` 和 `_advance_missile_flights`；V4 所需地面直射 `impact_delay_ticks=1` 不是已证明的资源契约，必须在 MD3-03 定义。 |
| Mission/Scoring | `PARTIAL` | `missions/engine_v2.py` 支持 selector、zone/state/count/survival/time/event/contact/communication/resource/score、终局锁存、N/A 和评分分离；径向穿越、环扇 duration、front-of-track occupancy、path conflict、阻塞和重规划指标仍 `ABSENT`。 |
| 任意 faction/neutral | `VERIFIED` | `schemas/core_v2.py:FactionV2/RelationshipV2` 支持任意 faction ID 与 hostile/friendly/neutral/protected 关系；原 V4“缺少 neutral side”与现 V2 事实冲突，以 V2 证据为准。仍需 MD3 专项 ROE/可见性测试。 |
| 观察、公平性与可视化 | `PARTIAL` | `WorldStateV2.observation_snapshot`、gateway 和 `VisualizationFrameV2` 有统一边界；MD3 需要融合 contact 而非点迹/真值、断链可见性、四视角脱敏及水面区域/残骸图层。 |

## 已发现的需求冲突与待决项

1. 原 V4 主张扩展 `side=neutral`、surface target domain；当前 V2 已有通用 faction relation 和 string domain。MD3 不新增 side enum，复用 faction/relationship，需在 MD3-01 ADR 记录。
2. 原 V4 将 `interdict_to` 列为新动作；正式需求 `REQ-ACT-003` 要求优先作为公开 SDK/规则策略 helper。MD3-01 必须决定，当前默认是 SDK helper。
3. V4 的“发射当 tick 判定、下一 tick 命中”与现有导弹 flight 不等价。须在 ADR-MD3-001/003 中明确 pending weapon effect 的资源与 checkpoint 语义。
4. V4 规定 50 ms/20 ms/100 ms 的亚秒通信延迟，却同时使用 1 s tick 和 TTL=1 s。须由 ADR-MD3-006 固定 tick quantization，不能让实现细节决定过期。
5. V4 所有 U1–U13 参数在未冻结前均为 `UNVALIDATED_BENCHMARK`；不得用规则策略胜负反向调参或宣称真实装备保真。

## MD3-01 待建 ADR 清单

按计划待创建 `ADR-MD3-001` 至 `ADR-MD3-009`：surface target domain 资源契约；interdict helper/intent 边界；自爆/残骸/殉爆生命周期；弧形与占位几何原语；modifier 组合顺序；通信时间量化；terminated/truncated；N/A/missing；REST bilateral ActionBatch 与权限。

## 门禁复核与下一步

- 无生产代码修改：`PASS`。
- V4 章节和 U1–U13 追踪：见 `requirements_traceability.md`，`PASS`。
- 当前能力均有源码/测试证据或明确非完成状态：`PASS`。
- 需要改变语义的项已标为 `NEEDS_DECISION`：`PASS`。

MD3-00 完成。下一阶段只能是 MD3-01；其目标是冻结契约、ADR、可信度和用户决策项，仍不应建立 MD3 场景包或实现机制。

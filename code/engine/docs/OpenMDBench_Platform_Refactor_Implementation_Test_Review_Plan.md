# OpenMDBench 通用组合仿真平台实施、测试与审查计划

> 文档版本：2.0
> 配套需求：`docs/OpenMDBench_Platform_Refactor_Service_Requirements.md` 2.0
> 执行环境：Ubuntu 22.04/24.04
> 执行方式：增量重构、阶段门禁、独立测试、独立审查

## 1. 计划目标

本计划把现有 OpenMDBench 增量重构为通用组合仿真平台。计划不以 MD-INT-001 或 MD-AD-002 作为内核模板；先通过完全合成的未知场景证明通用性，再将现有正式场景迁移为普通场景包。

任何阶段不得通过新增场景 ID 分支、固定红蓝逻辑、固定实体数量、复制主循环或修改旧测试期望绕过问题。

## 2. 执行原则

1. 先审计，后设计，后实现；
2. 场景数据和底层机制分离；
3. 所有运行配置先编译为不可变 ResolvedScenario；
4. 底层统一处理边界、碰撞、毁伤和生命周期；
5. 任务胜负和评分使用通用规则组合；
6. 同一工作目录同时最多一个写入者；
7. 每个 RF 阶段必须有需求追踪、定向测试、独立审查和阶段报告；
8. RF-10 GEN-GATE 未通过，不得迁移旧正式场景；
9. 全部完成后执行全量、性能、安全和长稳测试，再由未参与实现的发布审计者验收。

## 3. CAO 角色

- `openmd-supervisor`：任务拆解、委派、证据收集和门禁；
- `openmd-architect`：架构和接口边界，只读；
- `openmd-domain-auditor`：动力学、坐标、边界、毁伤和裁决语义，只读；
- `openmd-test-engineer`：验收、契约、异常和确定性测试；
- `openmd-developer`：核心实现和内部单元测试；
- `openmd-test-runner`：独立测试执行和失败分类；
- `openmd-migration-worker`：已批准规则下的配置迁移；
- `openmd-integration-engineer`：REST、Python、Gym、CLI、示例和用户接入；
- `openmd-reviewer`：阶段代码审查；
- `openmd-release-auditor`：RF-15 独立发布审计。

每次委派必须使用 `AGENTS.md` 定义的完整任务包和 T0-T5 测试等级。

## 4. 产物目录

```text
docs/adr/
reports/platform-refactor/
artifacts/platform-refactor/
scenarios/synthetic/
scenarios/legacy/
catalog/
```

每阶段报告：

```text
reports/platform-refactor/rf_XX.md
```

至少包含需求编号、修改文件、设计决定、测试命令和结果、兼容影响、审查发现、遗留风险和下一阶段条件。

## 5. RF-00：通用性阻碍与当前基线审计

### 目标

找出所有妨碍任意场景组合的固定假设，建立不修改生产代码的证据基线。

### RF-00A 架构审计

由 `openmd-architect` 执行 T0：

- 主循环、WorldState、环境和 Runner 调用图；
- 场景 ID、固定实体 ID、固定红蓝、固定实体数量和固定武器搜索；
- 场景专用构造器、裁决器、评分器、Observation 和可视化分支；
- 全局可变 Catalog、MMG/Taichi 状态和跨会话共享；
- REST/Gym/Python 是否复制业务规则；
- 日志、回放、检查点是否绑定特殊场景。

禁止运行完整测试。

### RF-00B 领域基线

由 `openmd-domain-auditor` 执行 T0：

- 现有动力学模型、公式、单位、参数来源和接线；
- WGS84/local/map 坐标和航向；
- 海陆、边界和碰撞能力；
- Weapon/Hit/Damage/Component/Lifecycle；
- 任务裁决和评分；
- RNG、稳定排序和检查点。

结论标记 VERIFIED、PARTIAL、ASSUMPTION、UNVALIDATED 或 DEFECT。

### RF-00C 测试基线

由 `openmd-test-runner` 单独执行。先 T1 收集，再按总控明确授权执行现有 T3/T4；不得交给架构智能体。

### 产物

- 当前架构图；
- 场景耦合清单；
- 可复用/需适配/需替换矩阵；
- 领域模型基线；
- 测试基线；
- ADR 清单和迁移风险。

### 门禁

没有修改生产代码；所有固定假设有文件和符号证据；用户确认目标边界后进入 RF-01。

## 6. RF-01：通用核心 Schema 和版本契约

### 工作内容

- ResourceRef、Faction、Relationship、EntitySpec、FormationSpec、InitialState；
- World、Zone、BoundaryPolicy、EventSpec；
- Platform/Dynamics/Component/Loadout；
- Weapon/Effect/DamageIntent/DamageResult/Lifecycle；
- MissionSelector、Condition、Rule、ScoreMetric；
- Observation、ActionBatch、Event、VisualizationFrame、ReplayMetadata、Checkpoint；
- schema_version、engine compatibility、错误码和迁移规则。

Schema 不得含 MD-INT-001、红蓝固定字段或固定实体槽位。

### 测试

- roundtrip、unknown field、非法类型、NaN/Inf；
- 1/3/4 faction；
- 0/1/10/100 entity schema 边界；
- 旧 schema 兼容或稳定拒绝；
- 公开对象不持有可变 WorldState。

### 门禁

通用 Schema 和契约测试通过；破坏性变化有 ADR。

## 7. RF-02：Catalog、ModelRegistry 和资源兼容

### 工作内容

- 建立 maps/platforms/dynamics/collision_shapes/sensors/communications/weapons/ammunition/effects/damage/energy/environments/loadouts/visualization Catalog；
- 实现 `id@version`、schema、engine compatibility 和内容哈希；
- 分离 Catalog 定义和 SessionRuntime；
- ModelRegistry 登记受信任动力学、探测、命中、毁伤和任务扩展；
- 平台槽位、载荷、目标域、模型输入输出和单位兼容校验；
- 将现有资源抽取为可复用档案，但不迁移整个正式场景。

### 测试

- 重复 ID/version、缺失引用、循环引用；
- 平台—动力学—载荷兼容矩阵；
- 不同会话资源实例隔离；
- hash 稳定和资源内容变更检测；
- 未知、不受信任或接口不兼容插件拒绝。

### 门禁

可以独立查询、校验和冻结资源；Catalog 不含运行时健康、弹药、冷却或 RNG。

## 8. RF-03：声明式场景包、编译器和 ResolvedScenario

### 工作内容

- 场景包目录和多文件/单文件等价语义；
- 任意 faction/relationship；
- 任意实体实例和 formation/count/id pattern；
- WGS84/local/map 坐标；
- world、zone、boundary、event、mission、scoring、controller slot；
- 编译稳定顺序、默认值、单位归一、坐标转换、编组展开、兼容校验、冻结和哈希；
- 稳定、可定位错误；
- 禁止 YAML 任意代码和越界路径访问。

### 测试

- 编组展开 1/10/100；
- 多阵营关系矩阵；
- 相同输入重复编译 hash 一致；
- 场景改名但内容等价；
- 非法坐标、部署、边界、事件依赖和控制槽位；
- property-based 合法/非法组合；
- 包路径和 YAML 安全。

### 门禁

任意合法数据包可编译为不可变 ResolvedScenario，运行期无需读取源 YAML。

## 9. RF-04：通用 WorldFactory、EntityFactory 和能力组件

### 工作内容

- 从 ResolvedScenario 创建 WorldState，不识别场景 ID；
- 创建任意 faction、实体、组件和控制槽位；
- capability-driven 系统查询；
- stable entity/faction/component ordering；
- scheduled spawn/despawn 和生命周期基础；
- 复用现有 UAV、USV/MMG、固定设施等动力学 adapter；
- 资源工厂和运行时状态深复制/冻结边界。

### 测试

- 1/10/100 混合实体；
- 同平台不同动力学参数和载荷；
- 没有 sensor/weapon/dynamics 的合法实体；
- 注册顺序变化结果不变；
- 跨会话组件状态不共享；
- 场景 ID 改名不影响构建结果。

### 门禁

新增实体组合只需 Catalog 和场景数据；WorldFactory 无 Legacy Scenario 分支。

## 10. RF-05：Geography、Boundary 和 Collision 底层系统

### 工作内容

- 统一 WGS84/local/map GeographyService；
- domain-aware 地图、海陆、高度、深度、禁区和障碍；
- 碰撞体和 broad/narrow phase 或现有适合方案；
- 动力学候选状态到边界裁决；
- reject/constrain/stop/reflect/effect/deactivate 等受控政策；
- BoundaryEvent、CollisionEvent 和 DamageIntent；
- 高速跨越和数值容差策略。

### 测试

- 经纬度往返、局部距离和航向；
- 多边形、海岸、岛屿、禁区、高度/深度；
- 点在边界、切线、跨越和 dt 敏感性；
- 静态障碍和实体碰撞；
- 注册顺序变化；
- boundary policy 只改变配置允许的处置，不改变算法。

### 门禁

场景只提供几何和政策；所有边界/碰撞判定在通用底层完成。

## 11. RF-06：通用 Combat、Damage 和 Lifecycle

### 工作内容

- WeaponProfile、Ammunition、HitModel、EffectProfile、DamageModel 分层；
- 通用交战合法性和稳定拒绝码；
- contact、ROE、包线、弹药、cooldown 和目标域；
- 每发独立 RNG 和证据；
- DamageIntent 稳定聚合和同 tick 同时应用；
- 健康、组件、降级、disabled、destroyed；
- 碰撞和环境 effect 进入同一 DamageSystem；
- 生命周期事件和日志。

### 测试

- weapon-target compatibility 矩阵；
- 非法攻击无弹药/RNG 副作用；
- 单发、多发、多攻击者同目标；
- 攻击顺序变化；
- 组件毁伤和 capability 降级；
- 碰撞毁伤与武器毁伤同一流水线；
- 检查点恢复后的 RNG 和 cooldown。

### 门禁

场景不直接修改 health；没有场景专用毁伤器；所有毁伤有可审计证据。

## 12. RF-07：通用 MissionRuleEngine 和 ScoringEngine

### 工作内容

- selector：faction/tag/platform/domain/entity/capability；
- conditions：zone、state、any/all/count、survival、time、event、wave、contact、communication、resource、score、not；
- 显式优先级、锁存和终局幂等；
- 权威胜负、比赛得分和训练 reward 分离；
- N/A 和权重归一化；
- 受信任 MissionPlugin 扩展协议。

### 测试

- 单条件和嵌套 all/any/not；
- selector 0/1/N 匹配；
- 同 tick 多终局优先级；
- 终局重复调用；
- 场景改名和实体 ID 模式变化；
- 评分 N/A、事件重复和 checkpoint；
- 通用规则表达拦截、防御、护航、生存和波次任务。

### 门禁

合成任务不新增 Python 裁决类即可表达；不得以旧任务类作为默认路径。

## 13. RF-08：SimulationSession、CommandQueue 和 Runner

### 工作内容

- Session 状态机和单写入者；
- persistent/discrete actions；
- timestamp、command_id、TTL、原子性、幂等和结果状态；
- last valid command 和 safe fallback；
- Continuous、Lockstep、Replay；
- physics_dt、decision interval、speed ratio、sim/wall time；
- pause、step、resume、terminate、close；
- 会话 RNG、原生状态、日志和资源释放。

### 测试

- 无请求持续推进并保持导航/传感器模式；
- discrete fire 不重复；
- stale/expired/idempotency；
- 1x/10x/unbounded 逻辑等价；
- GET observation 和显示订阅不推进仿真；
- pause/resume/terminate；
- 跨会话和 MMG/Taichi 隔离。

### 门禁

通用 session 可从任意 ResolvedScenario 创建；请求线程不直接写 WorldState。

## 14. RF-09：感知、通信、能源和固定 Tick 通用接线

### 工作内容

- 系统按 capability 运行；
- 复用 sensor、fusion、communication、energy 模型；
- faction/relationship 替换固定红蓝 contact 存储；
- 所有 RNG 使用命名子流；
- 确立并实现需求规定的固定 tick 顺序；
- 统一 Boundary、Damage、Mission、Score、Frame 和 Observation 发布；
- 旧入口通过 adapter 调用新内核，不复制业务逻辑。

### 测试

- 无对应组件实体跳过系统；
- 多 faction contact 和信息共享；
- 传感器/通信/combat RNG 隔离；
- 系统和注册顺序 golden；
- tick 边界同时事件；
- 不同显示/请求频率结果一致。

### 门禁

固定流水线消费 ResolvedScenario 和 SessionRuntime，代码搜索无新增场景 ID 特判。

## 15. RF-10：Synthetic Genericity Scenarios 和 GEN-GATE

RF-10 是平台通用性的强制门禁，优先级高于任何 Legacy Scenario 迁移。

### GS-001 多阵营混合域

- 至少 3 faction；
- 空中、水面、固定设施；
- 同平台不同载荷和 controller slot；
- faction observation 和交战关系。

### GS-002 规模和编组

- formation 展开 1/10/100 实体；
- 稳定 ID、部署、推进和日志；
- 性能和确定性。

### GS-003 边界与毁伤

- 地图、海陆、禁区、高度/深度、障碍和实体碰撞；
- 多 weapon/effect/damage；
- 组件降级、disabled、destroyed 和同时毁伤。

### GS-004 动态任务

- spawn/despawn、波次、天气、干扰；
- 区域、保护、摧毁、生存、超时和评分组合。

### 防伪测试

- 在编写内核完成后才由测试工程师生成部分场景组合；
- 随机改变场景 ID、实体数量、faction 名称、载荷和部署；
- 扫描生产代码中的 known scenario ID、固定 red/blue 和固定 entity ID；
- 每个 GS 只允许新增场景/Catalog/测试数据，不允许修改内核 Python。

### GEN-GATE

四个 GS 完成编译、运行、智能体动作、边界、毁伤、任务、评分、日志、检查点、实时显示和回放；相同 seed 确定性通过；Python/Gym/REST 等价测试可在 RF-12 补齐，但本地统一 Gateway 必须通过。

GEN-GATE 失败则回到对应 RF 修复，不得进入 RF-11/Legacy 迁移。

## 16. RF-11：VisualizationFrame、日志、回放和检查点

### 工作内容

- 通用 visualization/collision assets；
- 任意实体轮廓、尺寸、航向、轨迹和状态；
- referee/faction/public FrameBuilder；
- 有界 LiveFrameBus 和 retained-mode Matplotlib Renderer；
- ReplayWriter/Reader、事件索引和播放控制；
- 权威日志和完整 Checkpoint；
- map/resolved/catalog/plugin hash 验证；
- replay 不初始化仿真内核。

### 测试

- 任意 GS 实体组合可视化；
- live/replay 同 tick frame 等价；
- faction 防泄漏；
- 慢 renderer 和 frame drop 不影响仿真；
- Agg 截图；
- replay 不加载 MMG/Taichi；
- checkpoint 与连续运行逐事件等价；
- 缓存、轨迹和 Artist 有界。

### 门禁

GS-001 至 GS-004 均可实时显示、离线回放和恢复。

## 17. RF-12：AgentGateway、REST、Python、Gym 和 VectorEnv

### 工作内容

- 统一 Observation/Action 规范化、权限、可见性、幂等和队列接入；
- REST session CRUD、observation、actions、commands、events、result、control、checkpoint、visualization 和 artifact；
- StructuredPythonAdapter、GymnasiumAdapter、VectorEnvAdapter 和 REST SDK；
- 动态 entity/faction 的 padding、mask、action mask 和 space；
- continuous 服务和 lockstep 训练；
- 示例规则智能体只使用公开接口。

### 测试

- Python/Gym/REST 相同动作时间线等价；
- 任意实体数量 observation/action mask；
- 无请求 continuous 和 last command；
- REST retry 不重复 fire；
- cross-faction/session 防泄漏；
- reset/step/terminated/truncated；
- 16/32 VectorEnv 原生状态隔离；
- 慢客户端、断线和资源释放。

### 门禁

同一规则智能体核心可通过三种适配运行 GS 场景，不读取内部 WorldState。

## 18. RF-13：Legacy 迁移、场景 SDK、CLI 和文档

只有 RF-10 GEN-GATE 通过后执行。

### Legacy 迁移

顺序：MD-INT-001、MD-AD-002-EASY/MEDIUM/HARD、其他正式场景。每个场景只转换为普通场景包和 Catalog 引用，禁止修改通用内核以容纳场景特例。

比较固定 seed 的初态、轨迹摘要、事件、命中、毁伤、终局、评分、checkpoint、live/replay 和公开接口。差异修复或形成 Accepted ADR。

### 场景 SDK 和 CLI

至少提供：

```bash
openmdbench catalog list
openmdbench catalog show RESOURCE@VERSION
openmdbench scenario create NAME --template generic
openmdbench scenario validate PATH
openmdbench scenario resolve PATH
openmdbench scenario inspect PATH
openmdbench scenario selftest PATH
openmdbench scenario run PATH --seed 73 --headless
openmdbench scenario pack PATH
openmdbench live --session SESSION --view VIEW
openmdbench replay LOG --view VIEW
```

模板至少包括单实体移动、多阵营混合域、区域任务、动态波次、边界/碰撞、武器/毁伤和通信中继。

### 测试

- 新用户只增加 YAML/Catalog 创建新场景；
- 文档命令自动冒烟；
- 模板 validate/resolve/selftest/run/replay；
- pack/unpack hash；
- Legacy 兼容回归；
- 文档不承诺未验证保真度。

### 门禁

干净 Ubuntu 环境中的新用户可以完成“创建—配置任意实体—校验—运行—接入智能体—回放”，无需修改内核 Python。

## 19. RF-14：生产加固、全量、性能、安全和长稳

### 生产加固

- API Gateway、SessionManager、spawn worker、artifact storage；
- 鉴权、faction 权限、配额、限流、请求大小和路径安全；
- worker 心跳、异常、超时、恢复和清理；
- 日志、检查点、回放生命周期；
- 结构化日志、指标和资源观测；
- entity/event/resource 配置上限和编译防 DoS。

### 全量测试层级

1. lint/format/type/security；
2. unit；
3. contract；
4. compiler/property；
5. boundary/damage/mission；
6. integration；
7. GS-001 至 GS-004；
8. Legacy scenarios；
9. determinism；
10. system/API/Gym；
11. visualization/replay/checkpoint；
12. performance/concurrency/security/soak。

### 定量门禁

- 全量 100% 通过；
- 总覆盖率不低于当前门禁且 >=80%；核心新增模块 >=90%，关键分支 >=85%；
- Ruff、format、strict mypy、Bandit 通过；
- 1/10/100 实体组合；
- 16 并发通过，32 并发通过或有批准门槛；
- 100 局无崩溃、死锁和串扰；
- GS 和核心 Legacy 场景长稳；
- RSS、队列、文件句柄、进程、Artist 和缓存无无界增长；
- 报告记录硬件、Python、进程、日志/显示、tick/s、RTF、RSS 和 frame drop。

### 产物

```text
artifacts/platform-refactor/
├── test-report.md
├── junit.xml
├── coverage.xml
├── genericity-report.md
├── boundary-damage-report.md
├── legacy-migration-report.md
├── determinism-report.md
├── performance-report.md
├── security-report.md
├── soak-report.md
├── replay-samples/
└── screenshots/
```

## 20. RF-15：独立代码审查和发布审计

### 独立性

由未参与核心实现的 `openmd-release-auditor` 执行。缺少必要证据时返回 BLOCKED，不重新实现或替代测试。

### 审查重点

- 生产代码是否存在 known scenario ID、固定 red/blue、固定 entity count/ID；
- Catalog/Registry/Compiler/Resolved/Factory/Session 边界；
- Boundary/Collision 和 Damage/Lifecycle 是否真正位于底层；
- 场景是否直接修改 health 或执行任意代码；
- MissionRule 是否通用、锁存、幂等；
- 单写入者、命令保持、一次性动作、时间和确定性；
- Observation 防泄漏和 Python/Gym/REST 等价；
- live/replay/checkpoint/log 一致性；
- GS 防伪证据和“无内核代码变更”证据；
- Legacy 迁移是否引入特判；
- 测试质量、安全、资源限制和文档可执行性。

### 严重度

- P0：错误胜负、真值泄漏、重复发射、数据破坏、不可复现或严重安全问题；
- P1：通用性门禁造假、场景特判、核心系统缺失、主要接口不兼容；
- P2：局部正确性、性能、边界或维护风险；
- P3：非阻断改进。

### 发布结论

- RELEASABLE；
- CONDITIONALLY_RELEASABLE；
- NOT_RELEASABLE；
- BLOCKED。

发布要求：P0/P1 为零，GEN-GATE、Legacy 回归、T4/T5 和证据审计全部通过。

## 21. 代码审查检查表

### 通用性

- 新场景是否只增加数据；
- 场景改名是否等价；
- 任意 faction/entity/loadout/position；
- 系统是否 capability-driven；
- 是否存在专用主循环、裁决器、毁伤器或 renderer。

### 领域机制

- 坐标、单位、航向和 dt；
- Boundary/Collision 数值边界；
- Weapon/Effect/Damage 分层；
- 同 tick 同时毁伤；
- 任务优先级、锁存和评分；
- RNG 子流和检查点。

### 服务和公平性

- 请求不推进仿真；
- last persistent command；
- discrete action 最多一次；
- faction visibility；
- API/Gym/Python 等价；
- 并发和资源释放。

### 可视化和回放

- 任意实体外形来自 Catalog；
- Frame 不持有 WorldState；
- 慢 renderer 不阻塞；
- replay 不重新仿真；
- hash、视角和缓存有界。

## 22. 完成定义

只有以下全部满足才可报告 `DONE`：

1. RF-00 至 RF-15 门禁通过；
2. GS-001 至 GS-004 无内核代码变更通过；
3. BoundarySystem 和 DamageSystem 位于通用底层；
4. 任意 faction/entity/loadout/position 和任务组合通过；
5. Legacy 场景作为普通包迁移并回归；
6. REST/Python/Gym、live/replay/checkpoint 通过；
7. 全量、性能、安全和长稳门禁通过；
8. P0/P1 为零；
9. 所有证据和用户文档可读取、可复现。

任何缺失必须报告 PARTIAL、BLOCKED 或 NOT_RELEASABLE，不得以单个正式场景成功替代通用平台完成证明。

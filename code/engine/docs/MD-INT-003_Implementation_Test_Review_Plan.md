# MD-INT-003 实施、测试与代码审查计划

> 文档版本：1.2  
> 配套需求：`docs/MD-INT-003_Surface_Assault_Requirements.md` 1.1  
> 执行环境：Ubuntu 22.04/24.04  
> 执行方式：普通 Codex/Codex CLI 单会话顺序执行；不使用 CAO；增量开发、阶段门禁、结构化自测和代码自审

## 1. 目标

在不破坏 OpenMDBench V2 通用组合架构的前提下，实现 MD-INT-003a/b/c 三个水面突袭子场景，并补齐它们所依赖的、能够被其他场景复用的 surface combat、self-detonation、interdiction geometry、environment modifier、mission/scoring 和接口能力。

本计划不是重新执行 RF-00 至 RF-15 的平台重构，而是在已实现 V2 基线上进行场景接入。若审计发现基线中的通用能力实际不存在或不完整，应返回对应 V2 RF 阶段修复，不得在 MD-INT-003 中建立第二套旁路。

## 2. 执行原则

1. 先证据审计和需求追踪，后修改代码；
2. 先用 Catalog 和 ScenarioPackage，确有缺口才增加通用机制；
3. 三档场景只允许 data-only 差异；
4. `interdict_to` 优先放在 SDK/策略层，不能把规划算法塞入固定 Tick 内核；
5. 自爆、碰撞、搁浅和武器统一进入 Effect/DamageIntent；
6. 规则智能体只能使用公开 Observation；
7. 每阶段先定义外部行为测试，再实现和复测；MD3-12 由同一 Codex 对冻结范围执行结构化自审；
8. 同一工作目录同一时刻最多一个可写 Codex 会话；
9. 不提交、推送或合并，除非用户明确授权；
10. benchmark 参数必须标记 `UNVALIDATED_BENCHMARK`。

## 3. 单 Codex 工作方式

本项目不使用 CAO、总控、handoff、assign、工作智能体或额外人工审查会话。一个普通 Codex/Codex CLI 会话按 MD3-00 至 MD3-12 顺序推进，每次只处理一个阶段。

当前 Codex 承担：

- 读取需求、源码、Schema、Catalog、测试和前置报告；
- 建立阶段执行记录和需求追踪；
- 完成架构/领域只读审计；
- 编写或补充外部行为和验收测试；
- 实现通用机制、Catalog、ScenarioPackage、规则智能体和接口；
- 执行阶段授权的测试；
- 更新阶段报告、风险和下一阶段条件；
- 在 MD3-12 对冻结的本轮改动执行结构化代码自审。

自审采用以下闭环：

```text
冻结本轮实现和测试结果
→ 只读检查差异、调用链、测试和清单
→ 一次性记录所有发现和严重度
→ 若有问题，退出审查步骤
→ 返回对应阶段修复
→ 重新测试
→ 从头执行 MD3-12 自审
```

自审报告必须标记 `SELF_REVIEWED`，不得表述为独立第三方审查。T4/T5、依赖增删升级、破坏性操作、提交/推送以及会改变实现方向的选择仍需用户明确授权。
## 4. 阶段和门禁总览

| 阶段 | 目标 | 默认测试 | 主要门禁 |
|---|---|---:|---|
| MD3-00 | 基线、能力和需求追踪审计 | T0/T1 | 无生产代码修改 |
| MD3-01 | 冻结契约、ADR 和参数可信度 | T0/T1 | 用户决策项已记录 |
| MD3-02 | 地图、Catalog 和资源闭包 | T2/T3 | Compiler 完整解析 |
| MD3-03 | 通用 surface combat | T2/T3 | 无场景 ID；全证据链 |
| MD3-04 | 自爆、碰撞、残骸和生命周期 | T2/T3 | 统一 DamageSystem |
| MD3-05 | 拦截规划、弧形几何和任务评分 | T2/T3 | 通用原语而非专用裁决器 |
| MD3-06 | 环境、感知、通信和能源修饰器 | T2/T3 | L3 端到端生效 |
| MD3-07 | 三档 data-only 场景和规则双方 | T3 | 不改内核完成三档 |
| MD3-08 | Python/Gym/Vector/REST 接口 | T3 | 相同时间线等价 |
| MD3-09 | 实时可视化、回放和检查点 | T3 | live/replay/restore 等价 |
| MD3-10 | 场景系统、确定性和防泄漏 | T3 | 三档和异常矩阵通过 |
| MD3-11 | 全量、性能、并发、安全和长稳 | T4/T5 | 明确授权后执行 |
| MD3-12 | 结构化代码自审和完成审计 | T0 | `SELF_REVIEWED`，P0/P1 为零 |

不得跨阶段。MD3-00、03、04、05、07、08、11、12 为重点门禁。

## 5. MD3-00：基线与需求追踪审计

### 5.1 目标

验证基线文档描述是否与当前源码、Schema、Catalog、测试和工作树一致，形成 V4 每条需求的可追溯分类。

### 5.2 工作

#### MD3-00A 架构审计

Codex 以架构审计视角执行 T0：

- 找到 Catalog、Compiler、ResolvedScenario、WorldFactory、Session 和 Gateway 的真实入口；
- 确认是否存在 known scenario ID、固定 red/blue 和固定实体 ID；
- 检查 ActionBatch、persistent/discrete、receipt、visibility、Frame 和 Checkpoint 唯一语义源；
- 检查工作树中未提交改动，建立明确起始基线；
- 只读，不运行 pytest。

#### MD3-00B 领域审计

Codex 以领域审计视角执行 T0：

- MMG adapter 输入输出、单位、共享原生状态和确定性；
- WGS84/local/map 和威海地图海陆几何；
- surface sensor/target domain；
- collision、Effect、DamageIntent、lifecycle；
- environment modifier 当前接线；
- MissionRule 和 Scoring 是否支持区域穿越、duration 和自定义指标；
- 中立 faction 是否已经由通用关系矩阵支持。

每项标记 `VERIFIED`、`PARTIAL`、`ABSENT`、`UNVALIDATED` 或 `DEFECT`。

#### MD3-00C 测试基线

Codex 按测试基线步骤执行：

1. T1 收集本次相关测试；
2. 运行少量现有 V2 场景冒烟；
3. 只有用户或本计划当前阶段明确授权才运行 T3/T4；
4. 记录命令、时间、环境和失败分类。

#### MD3-00D 追踪矩阵

至少建立：

```text
V4 条目
→ 本需求 REQ ID
→ 当前代码证据
→ 分类（reuse/data/catalog/generic mechanism/decision）
→ 目标文件
→ 测试 ID
→ 审查结果
```

### 5.3 产物

- `reports/md-int-003/md3_00_baseline_audit.md`；
- `reports/md-int-003/requirements_traceability.md`；
- `reports/md-int-003/test_baseline.md`；
- 待建 ADR 清单；
- 明确的 Git/工作树基线说明。

### 5.4 门禁

- 无生产代码修改；
- V4 所有章节和 U1–U13 已追踪；
- 所有“现有能力”均有文件/符号/测试证据；
- 对冲突给出 `NEEDS_DECISION`，不得凭文档假设。

## 6. MD3-01：契约、ADR 和参数冻结

### 6.1 必须形成的 ADR

- ADR-MD3-001：surface target domain 扩展边界；
- ADR-MD3-002：`interdict_to` 是 SDK helper 还是通用 intent；
- ADR-MD3-003：自爆、接触引爆、殉爆和残骸生命周期；
- ADR-MD3-004：radial arc crossing、occupancy 和 path conflict 原语；
- ADR-MD3-005：environment modifier 顺序和组合规则；
- ADR-MD3-006：亚秒通信延迟在 1 s tick 的量化与 TTL；
- ADR-MD3-007：timeout/truncated 与任务胜负结果并存语义；
- ADR-MD3-008：N/A 与 metric_data_missing 区分；
- ADR-MD3-009：比赛 REST bilateral ActionBatch 和权限模型。

### 6.2 参数策略

- V4 benchmark 参数作为功能基准；
- 所有未标定资源增加 fidelity/source 标记；
- 不因某一规则智能体胜负调整参数；
- 正式比赛参数以后通过新 Catalog version 冻结；
- 当前实现应允许参数替换而不改 Python。

### 6.3 门禁

- Schema 变化和兼容策略明确；
- 破坏性契约有版本升级或迁移；
- 没有待决问题会改变 MD3-02 的资源结构；
- 用户未冻结真实参数不阻塞 benchmark 功能开发，但阻塞“已标定”声明。

## 7. MD3-02：地图、Catalog 和资源闭包

### 7.1 地图和几何

- 复用威海 map resource 和 hash；
- 定义 P0、核心区、航道、封锁弧、巡逻带、预警区和出生区；
- 用 GeographyService 转换并验证坐标；
- 检查 P0、岸基、USV 和出生点与真实海陆几何一致；
- 对切线、边界点和高速跨越建立测试夹具。

### 7.2 Catalog

建立版本化资源闭包：

- defender/attacker USV platform profiles；
- 两套 MMG dynamics profiles；
- collision shapes 和 visualization assets；
- surface radars、EO/IR、navigation radar；
- defender/attacker communication profiles；
- energy profiles；
- surface weapon/ammunition/effect/damage；
- suicide warhead/detonation/collision/secondary explosion effects；
- clear/high sea environment profiles；
- loadouts。

### 7.3 测试

- id@version、hash、roundtrip；
- 平台—动力学—载荷—目标域兼容矩阵；
- 缺失引用、循环引用、非法单位和超槽拒绝；
- Catalog 不含 health、ammo、cooldown、RNG 等运行状态；
- 跨会话资源状态隔离。

### 7.4 门禁

Compiler 能冻结完整资源闭包；资源参数有单位、来源、fidelity 和兼容性；不需要读取源 DOCX 才能创建会话。

## 8. MD3-03：通用 surface combat

### 8.1 Schema 和兼容性

- 将目标域从现有集合扩展为可包含 `surface`；
- 平台、sensor、weapon、effect 和 hit model 使用统一 domain enum；
- 未知 target domain 在编译期拒绝；
- 旧 air weapon 行为保持兼容。

### 8.2 执行链

- contact ownership、confidence、age、relationship、ROE、range、ammo、cooldown；
- `impact_delay_ticks=1` 的待决武器效果队列；
- 每发独立 RNG 和证据；
- 非法请求无 ammo/RNG 副作用；
- 同 tick 对同目标的配置化 engagement capacity；
- 同时 DamageResolution。

### 8.3 测试

- air/surface/fixed 目标域矩阵；
- 近/中/远分段 Pk 边界；
- stale/low confidence/neutral/core-zone/duplicate fire 拒绝；
- 命中延迟不重复、不丢失；
- checkpoint 恢复 pending impact、ammo、cooldown 和 RNG；
- attacker/defender 改名和实体 ID 改名结果等价。

### 8.4 门禁

对海武器通过通用 CombatSystem 工作；生产代码扫描无 MD-INT-003 或固定实体 ID；审查无 P0/P1。

## 9. MD3-04：自爆、碰撞、残骸和生命周期

### 9.1 自爆

- zone entry 产生通用 trigger event；
- trigger 引用 suicide EffectProfile；
- 任务规则锁存核心区爆炸；
- 实体 lifecycle 由配置选择 destroyed/despawned；
- 重复 zone evaluation 不重复爆炸。

### 9.2 碰撞和残骸

- 使用连续 TOI 或现有通用碰撞路径；
- 双方 DamageIntent 同 tick 聚合；
- destroyed attacker 可转为 static wreck obstacle；
- wreck 不再执行 sensor、movement、communication、fire；
- secondary explosion 使用独立 RNG 和 target filter。

### 9.3 测试

- 高速跨越核心区；
- zone 边界点、切线和浮点容差；
- 同 tick 被击毁并进入核心区的优先级；
- 双艇碰撞注册顺序不变；
- 残骸再次碰撞；
- 殉爆概率、半径、港口排除；
- restore 后不重复 detonation。

### 9.4 门禁

所有状态变化来自 Damage/Lifecycle；场景 YAML 不直接写 health；终局证据完整。

## 10. MD3-05：拦截规划、弧形几何、任务和评分

### 10.1 SDK 规划助手

实现可复用 `predict_intercept_waypoint` 或等价能力：

- 输入公开 contact estimate、自身运动能力和目标区域；
- 输出普通 navigation target；
- 不读取真值；
- 不直接控制 WorldState；
- 规则智能体和第三方智能体均可调用。

只有 ADR 批准时才增加 engine intent `interdict_to`。

### 10.2 通用几何事件

- radial/sector crossing；
- annular-sector occupancy duration；
- front-of-track occupancy；
- path conflict with debounce；
- blocked/slow duration；
- replanning latency。

参数由场景配置，不出现 P0、6 km、010–120° 等硬编码。

### 10.3 Mission/Scoring

- 终局优先级和锁存；
- 目标保护、处置、资源、协同、鲁棒和安全分；
- N/A 与 missing data；
- 权威事件重算；
- 训练 reward 单独适配。

### 10.4 测试

- 任意圆心、半径和扇区；
- clockwise/counterclockwise、跨 0° 扇区；
- 进入、离开、切线、高速跨越；
- selector 0/1/N；
- 同 tick 多终局；
- 评分重复事件、N/A、missing 和 checkpoint；
- 把 scenario/faction/entity 全部改名后结果等价。

### 10.5 门禁

一个与 MD-INT-003 无关的合成场景也能复用新增几何和评分原语；没有专用 Mission 类。

## 11. MD3-06：环境、感知、通信和能源

### 11.1 Environment modifier pipeline

明确 modifier 的作用顺序、乘法/覆盖规则、下限和恢复语义。至少接入 dynamics、sensor、weapon、energy 和 communication。

### 11.2 感知和融合

- surface target compatibility；
- 难度噪声档；
- 确认、维持、删除、stale；
- 跨平台分享必须经通信；
- contact 不泄漏真实 ID。

### 11.3 通信

- distance/terrain/path；
- tick-quantized delay 和 TTL；
- 高海况 loss modifier；
- last persistent command；
- local auto-engagement；
- 恢复后不补发过期轨迹。

### 11.4 能源和故障

- 高海况功耗；
- low-energy capability 降级；
- t=400 component suppression 和 t=520 自动恢复；
- 故障不可提前泄漏。

### 11.5 测试

- clear→high_sea_state 精确 tick；
- forecast visibility；
- modifier 组合和恢复；
- RNG 子流隔离；
- 断链、重连、过期消息；
- checkpoint 处于天气/故障中间态；
- request/display frequency 不影响结果。

### 11.6 门禁

L3 所有倍率在权威状态、事件、Observation、Frame 和日志中可验证；L1/L2 不受 L3 配置污染。

## 12. MD3-07：三档场景和规则双方

### 12.1 ScenarioPackage

建议目录：

```text
scenarios/md-int-003/
├── common/
├── md-int-003a/
├── md-int-003b/
├── md-int-003c/
├── agents/
├── tests/
└── README.md
```

可以使用包继承/overlay 的受控机制，但 resolve 后必须完整、不可变并可哈希。三档独立 validate/resolve/run。

### 12.2 规则策略

#### defender

- UAV 搜索和航迹共享；
- ETA 威胁排序；
- USV 一对一扇区分配；
- SDK intercept waypoint；
- 武器合法性和重复开火抑制；
- 弧形阵位恢复；
- 断链本地处置。

#### attacker

- L1 固定直航；
- L2 错时、单次转向、简单稀疏弧选择；
- L3 变速、蛇形、改道、诱导和主攻转移。

### 12.3 场景测试

- 每档至少一个固定 seed golden；
- 每档不少于 30 seed 的统计评测，不断言固定胜率除非参数已冻结；
- 规则策略不访问 WorldState；
- 三档区别只在 resolved diff；
- 仅修改场景/Catalog/agent 数据即可改变数量、出生、噪声和难度；
- 场景改名不改变逻辑摘要。

### 12.4 门禁

在通用机制完成后，三档场景阶段不得再修改核心内核 Python。若需要修改，退回对应阶段并重新审查。

## 13. MD3-08：统一接口

### 13.1 Python/Gym/Vector

- 动态实体列表或稳定 padding/mask；
- defender 一个控制槽位控制 5 平台；
- L3 attacker 可选第二槽位；
- `terminated` 和 `truncated` 分离；
- action mask、contact mask 和 faction visibility；
- reset(seed) 清理所有 SessionRuntime。

### 13.2 REST

- session create/observe/action/command status/events/result/control/checkpoint/artifact；
- bilateral ActionBatch 和 faction token；
- request 只入队，不直接推进 World；
- GET Observation 不推进；
- retry 不重复 fire；
- continuous 模式无请求仍推进并保持上一 persistent command；
- lockstep 模式只由 step 推进。

### 13.3 等价测试

同一 resolved、seed 和规范动作时间线分别通过 Python、Gym 和 REST 运行，比较：

- normalized actions；
- Observation 摘要；
- events；
- ammo/energy/health；
- terminal result；
- score；
- replay/log hash 或结构摘要。

### 13.4 门禁

外部接口不持有可变 WorldState；跨 faction/session 无泄漏；16 个 Vector/REST 会话无原生状态串扰。

## 14. MD3-09：可视化、回放和检查点

### 14.1 Live

- retained-mode Matplotlib；
- 地图、区域、实体、轨迹、coverage、link、weapon、damage、mission、score；
- disabled/destroyed/wreck 的一致图示；
- referee/defender/attacker/public 过滤；
- 有界 frame bus、Artist、轨迹和缓存。

### 14.2 Replay

- 共用 VisualizationFrame/Renderer；
- 只读日志，不加载 MMG/Taichi/World/RNG；
- seek/back/play/pause/speed；
- 公共视角脱敏；
- JSONL/gzip 兼容性按现有契约。

### 14.3 Checkpoint

- 每 100 tick 生成能力；
- 保存 pending impact、event schedule、modifier、contact、queue、mission/score 和所有 RNG；
- hash 不匹配拒绝恢复；
- 连续与恢复逐事件等价。

### 14.4 测试

- Agg 截图和 Artist 数量；
- live/replay 同 tick DTO 等价；
- 慢 renderer 和 frame drop；
- 4 视角泄漏矩阵；
- replay 模块导入不初始化 native solver；
- checkpoint 在发射后命中前、天气切换中、故障中、终局前恢复。

## 15. MD3-10：场景系统和确定性验证

### 15.1 必测场景矩阵

| 维度 | 取值 |
|---|---|
| 难度 | L1/L2/L3 |
| 模式 | Lockstep/Continuous |
| 接口 | Python/Gym/REST |
| 显示 | headless/live/replay |
| 视角 | referee/defender/attacker/public |
| 恢复 | continuous/checkpoint-resume |
| 地理 | normal/boundary/tangent/high-speed crossing |
| 战斗 | legal/stale/neutral/core-zone/duplicate/delayed impact |
| 环境 | clear/high sea/failure/recovery |

### 15.2 确定性

- 同 seed 重复；
- 不同实体注册顺序；
- faction/entity/scenario 改名；
- speed ratio 1×/10×/unbounded；
- renderer on/off；
- request polling 频率变化；
- 单会话与并发会话。

### 15.3 防伪

生产代码扫描：

```text
MD-INT-003
MD-INT-003a/b/c
red-usv-1/2/3
blue-usv-1/2/3
固定 red/blue 分支
```

允许这些字符串存在于 ScenarioPackage、测试数据、文档和示例，但不得进入通用生产机制分支。

### 15.4 门禁

三档、异常、权限、确定性、恢复和防伪全部通过；所有失败已分类且无 flaky 重跑掩盖。

## 16. MD3-11：全量、性能、安全和长稳

只有用户明确授权 T4/T5 后执行。

### 16.1 T4 全量门禁

```text
format check
→ Ruff
→ strict mypy
→ Bandit
→ unit
→ contract
→ integration
→ scenarios
→ determinism
→ API/Gym
→ visualization/replay/checkpoint
→ coverage
```

任一失败非零退出，不得跳过或弱化。

### 16.2 性能

- L1/L2/L3 各自 headless 1500 tick；
- 记录 warm-up、硬件、Python、进程模式、日志/显示设置；
- 报告 p50/p95/p99 tick time、tick/s、RTF、RSS；
- 16 并发必须通过；
- 32 并发通过或报告资源门槛；
- 比较 checkpoint/log flush 策略；
- live 性能单独测量，不与 headless 指标混合。

### 16.3 批量和长稳

- 每档每策略至少 30 seed；
- 总计至少 100 局；
- 检查崩溃、死锁、跨会话污染、句柄、进程、RSS、队列、Artist 和缓存增长；
- 可增加 2 小时 soak，但不得用 soak 代替功能测试。

### 16.4 安全

- faction/session/token 越权；
- Observation/Frame/log/artifact 泄漏；
- path traversal 和恶意 YAML；
- 超大 entity/event/request/queue；
- idempotency 和 replay attack；
- 会话/进程异常和资源清理。

### 16.5 定量门禁

- 全量 100% 通过；
- 总覆盖率 ≥80% 且不低于当前门禁；
- 新增核心模块行覆盖率 ≥90%，关键分支 ≥85%；
- 单会话平均 tick ≤100 ms；
- 16 并发通过；
- 100 局无崩溃、死锁和串扰；
- 无无界资源增长。

## 17. MD3-12：结构化代码自审和完成审计

### 17.1 自审执行约束

由承担开发的同一 Codex 执行 T0 结构化自审，不再要求人工另开会话。进入本阶段前必须冻结本轮修改文件、测试结果和审查基线。

自审期间只读取和分析，不直接修改代码。所有问题先写入 `reports/md-int-003/code_review.md`，包含严重度、文件/符号、证据、影响和建议。完成一轮检查后：

- P0/P1 存在：结论 `REVIEW_FAILED`，退出本阶段，返回对应实现阶段；
- P2 存在：修复或记录用户接受的风险；
- P3：记录，可不阻断；
- 修复后重新运行相关 T2/T3/T4/T5，并从头重做本阶段完整清单；
- P0/P1 为零且证据齐全：结论 `SELF_REVIEWED`。

`SELF_REVIEWED` 只表示完成规定的 Codex 自审闭环，不表示独立第三方审计。
### 17.2 审查清单

#### 通用性

- 是否存在场景 ID、固定 red/blue、固定实体 ID/数量；
- 三档是否只通过 data/Catalog/agents 区分；
- 新机制能否被未知合成场景复用；
- 是否创建第二套 World、main loop、Damage、Mission、Observation 或 Renderer。

#### 领域正确性

- 坐标、单位、航向和 dt；
- MMG 状态隔离；
- surface target compatibility；
- 延迟命中、ammo/cooldown/RNG；
- zone/collision TOI 和数值容差；
- Effect/DamageIntent/同时毁伤；
- lifecycle、残骸和自爆幂等；
- mission 优先级、锁存、N/A/missing。

#### 接口和公平

- persistent/discrete；
- timestamp、TTL、command_id、idempotency；
- GET 不推进；
- 无请求持续推进；
- cross-faction/session 防泄漏；
- Python/Gym/REST 等价；
- 规则智能体不读 WorldState。

#### 可视化和回放

- Frame 不持有 WorldState；
- 任意实体外形来自 Catalog；
- renderer 不阻塞内核；
- replay 不重新仿真；
- checkpoint 全状态和 hash；
- 内存、Artist 和轨迹有界。

#### 测试质量

- 测试能在故障实现上失败；
- 不只断言函数调用或退出码；
- 未弱化旧测试或扩大容差；
- 没有 flaky 重跑掩盖；
- benchmark 参数未冒充真实标定。

### 17.3 严重度

- P0：错误胜负、真值泄漏、重复发射/爆炸、不可复现、数据破坏或严重安全问题；
- P1：场景专用内核、核心链缺失、三档非 data-only、主要接口不兼容；
- P2：局部正确性、边界、性能、资源或维护风险；
- P3：非阻断改进。

### 17.4 结论

- `SELF_REVIEWED`；
- `REVIEW_FAILED`；
- `BLOCKED`。

MD-INT-003 报告 `DONE` 要求自审结论为 `SELF_REVIEWED`、P0/P1 为零、T4/T5 和证据齐全。平台总体发布状态仍由 V2 RF-15 决定。

## 18. 阶段执行记录模板

每个阶段开始前，当前 Codex 必须建立执行记录，完整包含：

```yaml
TASK_ID: MD3-XX-YY
PHASE: MD3-XX
OBJECTIVE: 单一、可验证目标
REQUIREMENTS: [REQ-...]
INPUTS: [文件和前置报告]
ALLOWED_READ: [精确路径或目录]
ALLOWED_WRITE: [精确路径或目录]
PROHIBITED: [明确禁区]
TEST_LEVEL: T0|T1|T2|T3|T4|T5
ALLOWED_COMMANDS: [命令类别]
COMMAND_TIMEOUT: 秒
TOTAL_BUDGET: 分钟
ACCEPTANCE: [可判定条件]
OUTPUTS: [代码/测试/报告]
STOP_CONDITIONS: [BLOCKED/NEEDS_DECISION 条件]
```

禁止把“完善相关功能”“测试一下”“处理问题”解释为全仓库写入或全量测试授权。

## 19. 报告和产物

```text
reports/md-int-003/
├── md3_00_baseline_audit.md
├── requirements_traceability.md
├── test_baseline.md
├── catalog_closure.md
├── surface_combat_report.md
├── damage_lifecycle_report.md
├── mission_scoring_report.md
├── interface_equivalence.md
├── visualization_replay_checkpoint.md
├── determinism_report.md
├── performance_concurrency.md
├── security_report.md
├── full_test_report.md
├── code_review.md
└── release_audit.md

artifacts/md-int-003/
├── junit.xml
├── coverage.xml
├── resolved/
├── replay-samples/
├── checkpoints/
└── screenshots/
```

每份报告至少记录引擎/schema/scenario/catalog/map/plugin hash、seed、环境、命令、耗时、结果、失败分类和遗留风险。

## 20. 最终完成定义

以下全部满足才可报告 `DONE`：

1. MD3-00 至 MD3-12 门禁通过；
2. 三档均为独立 data-only ScenarioPackage；
3. surface combat、自爆、碰撞、残骸、弧形几何和环境修饰器位于通用机制；
4. 规则双方完成整局且不读取 WorldState；
5. Python/Gym/REST、live/replay/checkpoint 等价；
6. 三档定向、确定性、异常和防泄漏测试通过；
7. T4/T5、性能、并发、安全和批量通过；
8. P0/P1 为零；
9. 所有参数可信度、已知限制和发布边界如实记录。

若只完成部分阶段，必须报告 `PARTIAL`、`BLOCKED`、`FAILED` 或 `NEEDS_DECISION`，不得用一个场景、一个 seed 或一个规则策略胜利替代完整验收。






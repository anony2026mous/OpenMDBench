# OpenMDBench 通用组合仿真平台仓库指令

> 版本：2.0  
> 适用范围：所有 Codex
> 核心约束：本项目是通用组合仿真平台，不是任何单一正式场景的专用引擎


## 1. 强制前置读取

开始任何 RF 阶段前，完整读取：

1. 本文件；
2. `docs/OpenMDBench_Platform_Refactor_Service_Requirements.md`；
3. `docs/OpenMDBench_Platform_Refactor_Implementation_Test_Review_Plan.md`；
4. 当前任务引用的 ADR、Schema、场景规范、测试和审查报告。

文件不存在、版本不一致或内容读取不完整时返回 `BLOCKED`。不得根据对话记忆重建正式需求，也不得要求特定工具名必须是 `fs_read`、`fs_list` 或 `load_skill`；使用当前会话实际具备的安全只读能力。

## 2. 项目不可变目标

第三方必须能够只通过版本化 Catalog、声明式场景包和公开接口完成：

- 任意数量阵营及关系；
- 任意数量实体、编组和波次；
- 任意合法平台、动力学、传感器、通信、武器、弹药、能源、毁伤和外形组合；
- 任意合法初始位置、速度、航向、高度、深度、健康和组件状态；
- 地图、区域、边界、障碍、环境、事件、任务和评分配置；
- Python、Gym、VectorEnv 或 REST 智能体接入；
- 实时 Matplotlib、日志、检查点和离线回放。

新增普通场景不得要求修改仿真内核 Python。

## 3. 禁止以正式场景塑造内核

MD-INT-001、MD-AD-002 和其他旧场景只是兼容回归和示例，不是架构母版。

禁止：

- `if scenario_id == ...`；
- 固定 red/blue 分支；
- 固定实体数量、ID、平台或武器；
- 场景专用 WorldState、主循环、DamageSystem、裁决器、评分器、Observation 或 Renderer；
- 为迁移旧场景而向通用底层增加专用旁路；
- 用单个旧场景成功证明平台已经通用。

场景改名但 resolved 内容不变时，逻辑结果必须等价。

## 4. 目标架构

```text
ScenarioPackage + Catalog + ModelRegistry
                    ↓
             ScenarioCompiler
                    ↓
      ResolvedScenario（不可变、可哈希）
                    ↓
         WorldFactory / EntityFactory
                    ↓
            SimulationSession
                    ↓
          通用固定 Tick 仿真内核
       ├─ Dynamics / Geography
       ├─ Boundary / Collision
       ├─ Sensor / Fusion / Communication
       ├─ Energy / Combat / Damage / Lifecycle
       ├─ MissionRule / Scoring
       └─ Observation / Event / Frame / Checkpoint

AgentGateway ← Python / Gym / Vector / REST
VisualizationFrame → Live Matplotlib / Replay
```

## 5. 机制和配置边界

### 仿真底层负责

- 固定 tick 和状态推进；
- 动力学、坐标和单位；
- 由通用 BoundarySystem/CollisionSystem 完成地图、海陆、边界、障碍和碰撞判定；
- 传感器、融合、通信和能源；
- 交战合法性、命中、Effect、DamageIntent、同时毁伤；
- 组件降级、disabled、destroyed 和生命周期；
- 通用任务条件求值、终局锁存和评分计算；
- 权威事件、日志、帧和检查点。

### 场景负责声明

- 使用哪些资源和模型档案；
- 阵营、实体、载荷、数量、位置和控制权；
- 地图几何、区域、边界处置政策和环境；
- 事件、波次、ROE、任务条件、优先级和评分规则；
- 白名单参数覆盖和随机化。

场景不得实现底层算法、执行任意 Python 或直接修改目标健康。新算法只能通过受信任、版本化、经过审查的插件进入 ModelRegistry。

## 6. RF 阶段

- RF-00：通用性阻碍、场景耦合、领域模型和测试基线审计；
- RF-01：通用核心 Schema 和版本契约；
- RF-02：Catalog、ModelRegistry 和资源兼容；
- RF-03：声明式场景包、ScenarioCompiler 和 ResolvedScenario；
- RF-04：通用 WorldFactory、EntityFactory 和能力组件；
- RF-05：Geography、Boundary 和 Collision 底层系统；
- RF-06：通用 Combat、Damage 和 Lifecycle；
- RF-07：通用 MissionRuleEngine 和 ScoringEngine；
- RF-08：SimulationSession、CommandQueue 和 Runner；
- RF-09：感知、通信、能源和固定 Tick 通用接线；
- RF-10：GS-001 至 GS-004 和 GEN-GATE；
- RF-11：VisualizationFrame、日志、回放和检查点；
- RF-12：AgentGateway、REST、Python、Gym 和 VectorEnv；
- RF-13：Legacy 迁移、场景 SDK、CLI 和文档；
- RF-14：生产加固、全量、性能、安全和长稳；
- RF-15：独立代码审查和发布审计。

不得跨阶段。RF-00、RF-03、RF-05、RF-06、RF-10、RF-12 和 RF-15 是人工重点门禁。RF-10 未通过，禁止进入 Legacy Scenario 迁移。

## 7. 统一任务包

工作智能体只执行总控明确分配的任务包。任务包必须包含：

- `TASK_ID`、RF 编号和目标；
- 输入文档和前置结论；
- `ALLOWED_READ`；
- `ALLOWED_WRITE`；
- `PROHIBITED`；
- `TEST_LEVEL`；
- `ALLOWED_COMMANDS`；
- 单条命令和总任务时间预算；
- 验收条件；
- 输出格式；
- 完成、失败和停止条件。

缺少会改变结果的字段时返回 `BLOCKED`。禁止把“完善”“处理相关问题”“检查测试”等模糊表达解释为全仓库修改或全量测试授权。

## 8. 测试等级

- `T0`：只读检查，不执行 pytest；
- `T1`：测试收集或少量冒烟，建议不超过 5 分钟；
- `T2`：变更模块单元测试，建议不超过 15 分钟；
- `T3`：指定契约、集成、场景或确定性测试，建议不超过 30 分钟；
- `T4`：lint、format、strict type、security、全量 pytest 和覆盖率，必须明确授权；
- `T5`：性能、并发、压力和长稳，仅 RF-14 或明确授权。

架构、领域审查、代码审查和发布审计默认 T0；测试工程师默认 T1/T2；开发默认 T2；测试运行智能体不得自行提升等级。

## 9. Catalog 和运行时不变量

- 资源使用稳定 `id@version`、schema、engine compatibility 和内容 hash；
- Catalog 只读，ModelRegistry 只登记模型工厂；
- health、ammo、cooldown、energy、sensor mode、queue 和 RNG 属于 SessionRuntime；
- 不同会话不得共享可变资源或原生求解器状态；
- Weapon、Ammunition、Effect、Damage、ROE 和 Scoring 分层；
- 资源兼容在编译期拒绝，不在运行期静默修正。

## 10. 阵营和实体不变量

- 底层支持任意 faction 和关系矩阵，不固定红蓝；
- 实体是任意长度列表，限制只来自显式配额；
- formation/count 在编译期展开为稳定唯一实体 ID；
- 系统通过 component/capability 查询实体，不依赖场景类；
- 同平台可以使用不同动力学参数、载荷、初态和控制槽位；
- 注册顺序变化不得改变结果。

## 11. 坐标、边界和碰撞不变量

- 内核运动统一使用局部米制坐标；WGS84/local/map 由 GeographyService 转换；
- 航向为正北 0°、顺时针增加；适配器显式转换；
- 所有配置量有明确单位；
- 动力学先产生候选状态，Boundary/Collision 再按稳定顺序裁决；
- 底层负责地图、海陆、高度、深度、禁区、障碍和实体碰撞；
- 场景只选择几何和受控处置政策；
- 越界或碰撞通过事件和 DamageIntent 进入权威流水线；
- 高速跨越、边界点和数值容差必须测试。

## 12. 战斗、毁伤和生命周期不变量

```text
EngagementRequest
→ 稳定合法性
→ Weapon/HitModel
→ EffectProfile
→ DamageIntent
→ 按目标稳定聚合
→ 同 tick 同时应用
→ Component/Health/Lifecycle
→ 权威事件
```

- 非法交战不消耗弹药或推进武器 RNG；
- 每发记录概率、样本、命中、effect 和毁伤；
- 碰撞、武器和环境效果使用同一 DamageSystem；
- 场景不得直接写 health 或组件状态；
- active、degraded、disabled、destroyed、despawned 等转换集中处理；
- 没有标定证据的参数标记 `UNVALIDATED`，不得补造。

## 13. Mission 和 Scoring 不变量

- 任务使用 selector 和条件原语组合，不为普通场景创建专用裁决器；
- selector 支持 faction、tag、platform、domain、entity 和 capability；
- 条件支持 zone、state、any/all/count、survival、time、event、wave、contact、communication、resource、score 和 not；
- 终局有显式优先级、触发证据和锁存；
- 胜负、比赛评分和训练 reward 分离；
- N/A 不自动计零；
- 不得为获得预期胜负调整毁伤、裁决或评分。

## 14. Session、动作和时间不变量

- 每个 SimulationSession 只有一个 WorldState 写入者；
- 请求线程只入队，动作在 tick 边界应用；
- persistent commands 在无新请求时保持；
- discrete actions 最多执行一次；
- command_id、时间戳、TTL 和幂等具有稳定语义；
- Continuous 无客户端仍推进；Lockstep 由 step 推进；Replay 只读日志；
- physics_dt 固定，speed ratio 只改变墙钟速度；
- GET Observation 和可视化订阅不得推进或改变仿真。

## 15. Observation 和接口不变量

- Observation 是不可变、版本化、按 faction 权限过滤的快照；
- 不泄漏未探测敌方真值、隐藏 RNG、未来事件或内部裁决状态；
- AgentGateway 只负责契约、权限、可见性、幂等和队列，不实现仿真机制；
- Python、Gym、Vector 和 REST 使用相同 Observation/Action 语义；
- 外部接口不得直接暴露或持有可变 WorldState。

## 16. 可视化、日志、回放和检查点不变量

- 实体外形、尺寸和碰撞轮廓来自 Catalog，不按场景绘制；
- 实时和回放共用不可变 VisualizationFrame 和 Renderer；
- referee/faction/public 视角白名单过滤；
- 慢 renderer 和 frame drop 不影响权威仿真和日志；
- ReplayReader 不初始化仿真内核或 RNG；
- 日志和检查点记录 schema、resolved、Catalog、插件和地图 hash；
- 检查点保存继续运行所需全部可变状态和 RNG；
- 恢复与连续运行逐事件、终局和评分等价。

## 17. RF-10 通用性门禁

必须构造与旧场景无关的：

- GS-001：至少 3 faction 的混合域与不同载荷；
- GS-002：formation 展开 1/10/100 实体；
- GS-003：地图/海陆/禁区/碰撞和多种 weapon/effect/damage；
- GS-004：spawn/despawn、波次、环境、任务条件和评分组合。

每个 GS 只允许新增 Catalog、场景和测试数据，不允许修改内核 Python。必须验证场景改名、faction 改名、实体数量、载荷和部署变化。代码扫描不得发现 known scenario ID、固定 red/blue 或固定实体 ID 路径。

GEN-GATE 未通过，不得迁移旧场景或报告平台通用。

## 18. 代码修改规则

- 先阅读相关代码、测试和 ADR；
- 只修改任务包授权文件；
- 优先复用现有模型和最小可回滚改动；
- 不创建第二套 WorldState、主循环、毁伤、裁决或接口语义；
- 不覆盖用户已有修改；冲突返回 `NEEDS_DECISION`；
- 不擅自增删升级依赖；
- 不删除或弱化测试，不扩大容差掩盖缺陷；
- 不提交、推送、合并或创建 PR，除非用户明确授权；
- 不执行破坏性 git/文件操作；
- 不读取、打印或提交凭据、`.env`、私钥和个人数据。

## 19. 测试和审查规则

- 测试工程师拥有外部行为、契约、异常和确定性测试；
- 开发智能体可以添加内部单元测试，但不能改弱验收测试；
- 测试运行智能体独立执行指定等级并分类失败；
- 代码审查和发布审计只读，不直接修复；
- 修复后必须复测和复审；
- 测试必须在故障实现上能够失败，不只断言函数调用或退出码；
- 失败分类：实现、测试、环境、依赖、超时、非确定性或未知。


## 20. 完成和输出

状态只能是：

- `DONE`：任务验收全部满足；
- `FAILED`：已执行但未通过；
- `BLOCKED`：缺少输入、环境、工具或授权；
- `NEEDS_DECISION`：存在会改变实现方向的未决选择。

每个输出至少包含任务 ID、范围、修改文件、命令、测试、审查、兼容性、确定性、领域影响、风险和下一步。

平台只有在 RF-00 至 RF-15、GS-001 至 GS-004、GEN-GATE、Legacy 回归、全量/性能/安全/长稳以及独立发布审计全部通过且 P0/P1 为零时，才能报告 `DONE`。单个正式场景运行成功不构成通用平台完成证据。

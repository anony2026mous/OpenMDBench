# OpenMDBench 当前支持实体、武器、挂载与事件清单

本文是当前实现的能力矩阵，不是未来路线图。表中状态含义：

- **正式运行**：正式任务已端到端使用；
- **V2 可执行**：通用 Catalog/Resolved/World/Session 路径有真实实现和 receipt；
- **仅契约**：schema/payload 已冻结，但 Session 会在 submit 时 fail-closed；
- **测试资源**：只用于通用性、攻击或契约测试，不能当作正式装备参数。

## 1. 场景与任务

| 标识 | 路径 | 状态 | 主要内容 |
|---|---|---|---|
| MD-INT-001 | Legacy 正式适配 | 正式运行 | 威海地图，多域拦截，UAV/USV/岸基雷达，MMG |
| MD-AD-002-EASY | V2 `scenarios/formal/md_ad_002_easy` | 正式 V2 | 岛礁拒止、3 波次、clear weather |
| MD-AD-002-MEDIUM | V2 `scenarios/formal/md_ad_002_medium` | 正式 V2 | 2.1.0 感知资源、cloudy/规避事件 |
| MD-AD-002-HARD | V2 `scenarios/formal/md_ad_002_hard` | 正式 V2 | rain/fog、海况、干扰、组件抑制事件 |
| MD-INT-003-EASY | V2 `scenarios/formal/md_int_003_easy` | 正式 V2 | 3 艘自爆 USV 同时直接突入；防守方保护核心区 |
| MD-INT-003-MEDIUM | V2 `scenarios/formal/md_int_003_medium` | 正式 V2 | 突袭艇在 0/30/540 tick 分批出现，首次接触后规避转向 |
| MD-INT-003-HARD | V2 `scenarios/formal/md_int_003_hard` | 正式 V2 | 蛇形/变速突入；高海况与舰载雷达临时压制 |
| GS-001 | V2 `package@2.0` | 可编译 | 任意三阵营、混合域、天气事件 |
| GS-002 | V2 `package@2.0` | 可编译 | 1/10/100 formation 稳定展开 |
| GS-003 | V2 `package@2.0` | 可编译 | 任意命名平台、loadout、武器/弹药/effect/damage |
| GS-004 | V2 `package@2.0` | 可编译 | 动态事件、nested mission、scoring |

新场景不受 MD-INT/MD-AD 的固定实体数量或 red/blue 名称约束。V2 factions、entities、formations、
events、rules 和 metrics 都由数据声明；能否运行取决于 Catalog 资源和 Registry 工厂是否齐全。

## 2. 实体与动力学

### 2.1 正式实体族

| 实体/角色 | 域 | 动力学 | 主要能力 | 正式任务 |
|---|---|---|---|---|
| UAV | air | bounded 3D kinematic / native UAV | 导航、高度、EO/IR、雷达、导弹 | MD-INT、MD-AD interceptor |
| USV | surface | Sim2Sea MMG / native MMG | 水面导航、雷达、通信 relay、碰撞 | MD-INT、MD-AD picket |
| defender-interdictor USV | surface | Sim2Sea MMG / native MMG | 对海航迹、拦截导航、对海武器、雷达/通信 | MD-INT-003 |
| attacker-suicide USV | surface | Sim2Sea MMG / native MMG | 导航雷达、核心区/接触自爆、wreck lifecycle | MD-INT-003 |
| AUV | underwater | native AUV kinematic | 深度导航、边界/碰撞 | V2 合同与集成 |
| shore_radar | land/fixed | fixed | 岸基雷达、wired comm、CIWS | MD-INT、MD-AD |
| wave threat | air/mission entity | 场景调度动力学 | 波次、直接/机动行为、突破判定 | MD-AD |

V2 `platforms` 可定义任意 `platform_type/domain`，但若无 compatible dynamics、shape、energy、
visualization 和受信 factory，Compiler/WorldFactory 会拒绝，而不是退化为 point mass。

### 2.2 V2 EntitySpec 可声明内容

- `platform_ref`（必需）；
- `dynamics_ref`、`loadout_ref`；
- 任意 `component_refs`；
- ammunition exact-ref → count；
- `target_domains`；
- position/velocity/heading/health/energy/component initial state；
- controller slot、tags；
- formation 的 count/id pattern/offset。

运行时 health、ammo、cooldown、energy、sensor mode、message queue、RNG 不属于 Catalog，不能写回场景文件。

## 3. 正式武器

### 3.1 MD-INT-001

| weapon_id | 挂载平台 | 目标域 | 制导 | 射程 | 命中基准 | 毁伤 | 默认弹药 |
|---|---|---|---|---:|---:|---:|---:|
| `uav_interceptor_missile` | UAV | air | EO/IR | 8,000 m | 0.7 | 0.6 normalized | 2/UAV |
| `shore_ciws` | shore_radar | air | radar | 2,000 m | 0.8 | 0.5 normalized | 100/场景岸基单元 |

### 3.2 MD-AD-002

| component | 使用者 | min/max range | hit probability | damage | cooldown | 场景总库存 |
|---|---|---:|---:|---:|---:|---:|
| `uav_interceptor_missile` | interceptor UAV | 500/8,000 m | 0.7 | 1.0 | 5 ticks | 36 |
| `shore_ciws` | island shore defense | 300/2,000 m | 0.8 | 0.5 | 1 tick | 24 |

`profiles/md_ad_002_resource_tight_v1.yaml` 可将 UAV 单机库存改为 6、场景导弹总库存改为 18。
库存必须非负；不足弹药、cooldown 未到、energy 不足、target domain 不兼容都会在开火前拒绝且不消耗 RNG。

### 3.3 Legacy 底层定义但不要直接用于新 V2 场景

Legacy combat model 还包含若干固定表项和专用 adapter。它们没有完整的 V2 exact resource closure、
Registry evidence 或 Session receipt 时，不能仅凭名称写进 `EntitySpecV2.ammunition`。新武器必须依次提供：

```text
weapons resource
  -> compatible ammunition resource
  -> effect resource
  -> damage_models resource
  -> trusted hit/damage model factory metadata
  -> loadout/platform compatibility
```

### 3.4 MD-INT-003 对海武器与自爆闭包

| weapon_id | 使用者 | 目标域 | min/max range | 结算方式 | 默认弹药 |
|---|---|---|---:|---|---:|
| `weapon.usv-surface-interdictor@2.0.0` | defender-interdictor USV | surface | 200 / 6,000 m | `delayed_effect`，下一 tick 结算，命中基准 0.65、2 tick cooldown | 10/拦截艇 |
| `weapon.suicide-usv-warhead@2.0.0` | attacker-suicide USV | surface、land | 0 / 35 m | `contact_detonation` / 核心区空间触发；35 m 自爆半径，可触发 20 m 次生爆炸 | 1/突袭艇 |

两类武器均具备 weapon → ammunition → effect → damage model → loadout/platform 的 V2 资源闭包。
自爆、次生爆炸、碰撞与普通对海火力均经 `DamageIntent` 同 tick 稳定裁决；已毁突袭艇是否保留
为 wreck 由数据化 lifecycle policy 决定。上述命中率、半径和毁伤阈值均为
`UNVALIDATED_BENCHMARK`，可用于功能/训练评测，不能视为真实装备标定。

## 4. V2 武器、弹药、效果和毁伤契约

### 4.1 Catalog 类型

| 类型 | 关键内容 |
|---|---|
| `weapons` | target domains、range/envelope、effect_ref、model evidence |
| `ammunition` | weapon_ref、quantity 单位及兼容信息 |
| `effects` | effect_type、damage_model_ref、单位/参数 |
| `damage_models` | accepted effect types、component/health profile、模型工厂 |
| `loadouts` | 平台组合、sensor/comm/weapon/ammunition 等闭包 |

Compiler 会递归冻结依赖；WorldFactory 为每个 session 创建 fresh adapter。禁止不同 session 共享带 call_count、
RNG 或内部状态的 hit/damage adapter。

### 4.2 空间碰撞毁伤

World 可显式声明 `spatial_damage_policy`：

| magnitude model | 参数 | 含义 |
|---|---|---|
| `constant` | `value` | 固定无量纲毁伤输入 |
| `scaled_relative_speed` | `scale` | 按碰撞前相对速度缩放 |
| `relative_kinetic_energy` | `scale` | 按质量和碰撞前速度计算相对动能 |

还必须提供 `collision_effect_ref` 和 `output_unit: "1"`。策略引用的 effect/damage 进入
`world_resource_bindings`，由 World 自身持有，不要求某个实体挂载武器。无显式策略时不能从“唯一 effect”
猜测碰撞毁伤。

## 5. 传感器

### 5.1 MD-INT-001

| sensor | 平台 | 类型 | range | update | FOV |
|---|---|---|---:|---:|---:|
| `shore_air_radar` | shore_radar | radar | 200 km | 0.2 Hz | 360° |
| `uav_eo_ir` | UAV | EO/IR | 15 km | 1 Hz | 60° |
| `usv_radar` | USV | radar | 20 km | 0.5 Hz | 360° |

### 5.2 MD-AD-002

| sensor_id | 平台 | 类型 | range / low-alt range | report interval | Easy base P(detect) |
|---|---|---|---:|---:|---:|
| `radar_ew` | island radar 1 | radar | 40/15 km | 5 ticks | 0.85 |
| `radar_gap` | island radar 2 | radar | 15/15 km | 2 ticks | 0.90 |
| `radar_usv` | picket USV | radar | 30/20 km | 3 ticks | 0.80 |
| `radar_uav` | interceptor UAV | radar | 15/15 km | 2 ticks | 0.75 |
| `eo_uav` | interceptor UAV | EO/IR | 10/10 km | 1 tick | 0.90 |

Medium 会降低上述检测概率；Hard 还会通过天气/干扰改变有效感知。Observation 只包含符合 owner、freshness、
confidence、visibility 的 contact evidence，不暴露 sensor truth。

## 6. 通信与能源

### 6.1 MD-INT-001 通信

| link | 平台 | 模式 | range | bandwidth |
|---|---|---|---:|---:|
| `uav_los` | UAV | line of sight | 50 km | 10 Mbit/s |
| `usv_los` | USV | line of sight | 30 km | 100 Mbit/s |
| `shore_wired` | shore | wired | 不按距离限制 | 场景定义 |

### 6.2 MD-AD-002 通信

- `shore_uav_los`：50 km、10 Mbit/s、1 tick delay；
- `usv_relay`：30 km、100 Mbit/s、1 tick delay；
- `wired_shore`：0 range 语义为有线、不按无线距离限制，0 tick delay。

能源模型支持 UAV/USV endurance、sensor/relay rate、weapon launch cost；shore 使用 fixed supply。运行时
energy 是 Session 状态，checkpoint/restore 必须连续等价。

## 7. V2 动作清单

### 7.1 Persistent commands

| command_type | payload | world intent | 状态 |
|---|---|---|---|
| `navigation` | speed_mps、heading_deg、altitude_m 或 depth_m | EntityControlCommandV2 | **V2 可执行** |
| `hold` | 空对象 | EntityControlCommandV2 safe hold | **V2 可执行** |
| `patrol` | speed_mps、waypoints_m | PatrolRouteIntentV2 | 仅契约，submit 拒绝 |
| `sensor_mode` | mode | SensorModeIntentV2 | 仅契约，submit 拒绝 |
| `relay_mode` | mode | RelayModeIntentV2 | 仅契约，submit 拒绝 |
| `ciws_auto` | enabled | CiwsPolicyIntentV2 | 仅契约，submit 拒绝 |

### 7.2 Discrete actions

| action_type | payload | world intent | 状态 |
|---|---|---|---|
| `fire_weapon` | weapon_ref、target_id | EngagementRequestV2 | **V2 可执行** |
| `send_message` | recipient_id、message | MessageIntentV2 | **V2 可执行** |
| `release_payload` | payload_ref、可选 target_id | ReleasePayloadIntentV2 | 仅契约，submit 拒绝 |
| `device_action` | device_ref、operation | DeviceActionIntentV2 | 仅契约，submit 拒绝 |
| `ram` | target_id | RamMotionIntentV2 | 仅契约，submit 拒绝 |

状态机：persistent 可经历 queued/accepted/active/completed/replaced/expired/cancelled/failed；discrete 可经历
queued/accepted/applied/executed/rejected。只有真实进入 World 子系统后才能标为 executed。

## 8. V2 场景事件

`EventSpecV2.event_type` 当前白名单：

| event_type | owner/效果 | 关键 payload/说明 |
|---|---|---|
| `spawn` | Lifecycle | blueprint/entity 定义，按 tick 创建并接入 dynamics/boundary |
| `despawn` | Lifecycle | 延迟 close，可在事务失败时 rollback |
| `weather_change` | Weather owner state | 环境引用或 typed weather payload |
| `zone_activation` | Geography/Boundary | zone ID 和 active 状态 |
| `jamming_start` | Jamming owner state | typed jammer/target evidence |
| `jamming_end` | Jamming owner state | 结束对应干扰 |
| `component_suppression` | Component owner state | entity/component、持续/状态信息 |
| `message` | Message owner state | sender/recipient/content evidence |
| `mission_marker` | Mission owner state | typed marker/payload |
| `apply_effect` | Effect owner ledger | exact effect/damage chain |
| `spatial_effect_trigger` | 通用空间触发器 | zone entry 或 collision evidence → effect → DamageIntent；source 一次性消费并可 checkpoint 恢复 |

事件 trigger、priority、depends_on 由 Compiler 校验为 DAG。World tick 固定阶段为 lifecycle → dynamics/motion →
boundary/collision → damage/events → mission → scoring → cooldown；权威事件、状态与日志证据在对局内保留，
对局结束后统一写出日志，慢速 renderer 不影响 tick 推进。

## 9. 场景难度事件与波次

三个难度共享基础三波：

| wave | count | start | altitude | behavior |
|---|---:|---:|---:|---|
| wave-1 | 4 | 0 s | 100 m | direct |
| wave-2 | 5 | 600 s | 100 m | direct |
| wave-3 | 6 | 1200 s | 100 m | direct |

Medium/Hard 的资源版本、weather、jamming、component suppression 和 wave 变体分别以
`scenarios/formal/md_ad_002_medium/scenario.yaml`、`md_ad_002_hard/scenario.yaml` 为配置事实；共享资源
定义在 `catalog/v2/md_ad_002.yaml`。不要在智能体或核心运行时中按 difficulty 名称硬编码事件时间，
应从 Observation/authority event 判断。

MD-INT-003 的共同 1,500 tick 任务是守护核心区。EASY 在开局生成 3 艘突袭艇；MEDIUM/HARD 额外在
30、540 tick 生成后续突袭艇。HARD 在 tick 240 产生高海况预报、tick 300 切换高海况、tick 400
压制 `unit.guard.usv.02` 的舰载雷达 120 tick。所有时刻、资源版本和行为差异均是
ScenarioPackage/Catalog 数据，不属于按场景 ID 编写的内核逻辑。

## 10. 任务条件和评分

### 10.1 Condition operators

`all`、`any`、`not`、`count`、`zone`、`state`、`survival`、`time`、`event`、`wave`、
`contact`、`communication`、`resource`、`score`。

Selector 支持 factions、tags、platforms、domains、entity_ids、capabilities；运行时会处理 future spawn、
active、destroyed、despawned，不把已 despawn 实体重新视为 scheduled。

### 10.2 Scoring

- metric value `null + available:false` 表示 N/A，不等于 0；
- aggregation：sum/mean/min/max/count；
- direction：maximize/minimize；
- scenario total policy 与每 metric policy 分离；
- competition score、terminal result、training reward 分离；
- event/plugin 动态输入必须绑定权威 receipt/Resolved policy，并在 restore 时重放或纯函数重算。

## 11. 生命周期和毁伤

实体生命周期至少区分 scheduled、active、disabled、destroyed、despawned。Destroyed/disabled 是否仍可执行
某能力由 component/capability/controller 状态决定；不能只看总 health。

DamageSystem 统一处理 weapon、collision、environment 来源的 `DamageIntentV2`，同 tick 聚合并原子提交。
component profile 决定部分/完全损伤、能力移除、controller 失效和生命周期迁移；magnitude 0 不会凭 component
名称直接摧毁实体。

## 12. 地理、边界与碰撞

- 坐标：local metre、WGS84、map；编译期统一规范并冻结 map/resource hash；
- 区域：polygon/circle/world/altitude/depth、allowed/excluded、static obstacle；
- policy：reject/constrain/stop/reflect/effect/deactivate/mission event；
- 连续检测：entity-boundary、entity-obstacle、entity-entity earliest TOI；
- shape DTO：sphere、capsule、AABB、OBB、polygon。生产 exact oracle 当前对已支持组合精确执行，对未支持
  continuous sweep 稳定 `boundary.shape_sweep_unsupported`，不会退回 bounding-radius 近似。

## 13. 运行时权威事件与回执

除声明事件外，运行时还产生：

- lifecycle spawn/despawn receipt；
- native dynamics step receipt（model/resource/manifest/input/output/tick/hash）；
- boundary/collision fact、response、DamageIntent；
- Combat shot/hit/effect/damage receipts；
- message、weather、jamming、suppression、zone、marker owner-state receipt；
- mission rule、terminal candidate/result、metric/score/plugin/event accumulator receipt；
- command submit/apply/child status；
- checkpoint/replay/visualization frame evidence。

事件与回执只通过 Observation、Gateway events/result、ActionApplyReceipt 或 checkpoint/replay 公共面读取。
不要读取 `_applied_*`、私有 ledger 或 mutable World 字段。

## 14. 当前限制

1. `patrol/sensor_mode/relay_mode/ciws_auto/release_payload/device_action/ram` 已有严格 payload schema，
   但当前没有完整 World dispatch；submit 会原子 fail-closed。
2. MD-AD-002 与 MD-INT-003 的三个难度均已使用正式 V2 ScenarioPackage；MD-INT-001 与旧 selftest/live
   仍保留 Legacy 兼容入口。MD-INT-003 实时展示可调用 `run_live_formal_v2`；当前 CLI `live` 候选列表
   尚未列出该场景 ID。
3. 测试中出现的 `*.arbitrary`、`*.test`、`*.forged`、`*.missing` 资源用于通用性或攻击测试，不是产品
   装备目录。
4. YAML 能改变参数、数量、部署和组合，但不能凭空新增动力学、传感器、武器算法；算法必须先进入
   Catalog/Registry。
5. 平台仍处于 Pre-Alpha；发布状态以 RF-14/RF-15 报告为准。

## 15. 新资源接入检查表

- 选择合法 resource type，定义稳定 id@semver 和 engine compatibility；
- 建立完整 dependencies，明确所有单位和兼容域/平台；
- 提供受信 ModelFactoryMetadata（artifact SHA-256、interface 2.0、schemas、units、determinism）；
- 不在 Catalog 中放 runtime mutable state；
- 测 0/1/10/100 实体、声明顺序、错误类型、错误单位、缺失/环依赖；
- 测双 session fresh adapter、checkpoint N+M、故障 rollback、cleanup 逆序；
- 若进入智能体动作，必须定义 payload → world intent → authoritative receipt，未接线前保持
  `dispatch_available=False`。

相关可执行样例：`scenarios/synthetic/gs_003`、`tests/contract/test_catalog_registry_v2.py`、
`tests/contract/test_combat_damage_v2.py`、`tests/integration/test_session_action_world_v2.py`。

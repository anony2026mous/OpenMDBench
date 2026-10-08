# MD-INT-003 V4 → V2 需求追踪矩阵

## 记录

- TASK_ID：`MD3-00-001`
- 依据：V4.0 原始 Word 文档（2026-09-02 读取）、`docs/MD-INT-003_Surface_Assault_Requirements.md` 1.0、`docs/MD-INT-003_Implementation_Test_Review_Plan.md` 1.1。
- 取样锚点：engine/schema `2.0.0/2.0`；scenario `md-ad-002.easy.v2`；seed `0`（编译取样）；resolved `sha256:34f8322ccbdb8ce915002dc8d886235a87b61e833dd6069c992cf8f01e6c1f66`；catalog `sha256:cf34729fad371b07f58d3f4f66ff7cb975a00f97cc716a93b3a2527650ba6350`；map `sha256:c40a43035b62340c558e1c697823a574b936b50123acb49c4754b4c1d79c398d`；registry/plugin `sha256:573277d4e4495e4b6a22c9cb33fbdbe0fb70020925d8c717009ac503e91af69a/none`。
- 命令/耗时：T0 源码、Catalog、测试和原始 Word 取证；T1 命令/耗时/结果见 `test_baseline.md`。风险为尚无 MD3 resource/scenario/runtime 证据。
- 分类：`reuse` 已有通用能力；`data` 场景数据；`catalog` 版本化资源；`generic mechanism` 通用内核缺口；`decision` 需 ADR/需求方确认。
- 审查状态：MD3-00 完成可追溯性审计；后续阶段状态以各行和
  `md3_01` 至 `md3_12` 执行记录为准。MD3-11 全量/T5 门禁及 MD3-12
  结构化自审均为 `DONE`；未冻结的 U 参数仍保持
  `UNVALIDATED_BENCHMARK`，不是实现缺失。

## V4 章节追踪

| V4 条目 | REQ ID | 当前代码证据 | 分类 | 目标阶段/文件 | 验收测试 | 审查 |
|---|---|---|---|---|---|---|
| 0 通用约定、1 任务概况 | ARCH-001..004、SCN-001..004 | formal compiler、resolved hash、`SessionLifecycleV2`；三档 data-only package 与改名契约 | reuse + data | MD3-01/07；`scenarios/formal/md_int_003_*` | 三档 compile/rename/determinism | MD3-07 resource refs/compile `DONE`；跨接口与统计验证后续阶段 |
| 2 地图/区域 | GEO-001..004 | `GeographyServiceV2`、`map.weihai-local@2.0.0`、terrain deployment、`interdiction_geometry_v2` 连续圆/扇/路径原语 | reuse + data + generic mechanism | MD3-02/05；map/Catalog/geometry fixture | WGS84、海陆、圆/扇/穿越/高速 crossing | MD3-05 通用机制 `DONE`；具体地图/场景数据待 MD3-07 |
| 3 实体/出生/残骸/neutral | ENT-001..002、SCN-002..004、DMG-003 | `FactionV2`、`RelationshipV2`、`ResolvedEntityV2.destroyed_lifecycle`、通用 lifecycle ledger；MD3-04 通用 wreck/despawn | reuse + data + catalog + generic mechanism | MD3-02/04/07 | 数量/改名/出生/残骸/neutral ROE | MD3-04 `DONE`；P0/P1 修复后的 T2/T3 与结构化 `SELF_REVIEWED` 完成 |
| 4 MMG 动力学 | DYN-001..003 | `NativeDynamicsAdapterV2`、Sim2Sea worker、boundary system | reuse + catalog + data | MD3-02 | MMG 参数、隔离、health modifier、grounding | PENDING |
| 5 传感器/融合/噪声 | SEN-001..002、OBS-001 | generic subsystem 点迹和命名 RNG；MD3-06 capability range/Pd、suppression 与 lifecycle/energy clamp；三档包已精确接入 L1/L2/L3 profile | catalog + generic mechanism + data | MD3-02/06/07 | surface compatibility、确认/stale、噪声、无真值泄漏、exact-ref | MD3-02/06 `DONE`；MD3-07 resource refs `DONE` |
| 6 通信 | COM-001..002 | tick-quantized transport、range/lifecycle/jamming/explicit terrain predicate、stable relay route、TTL/loss audit/checkpoint；三档包已分别接入 20 km surface/shore 与 50 km UAV 资源 | catalog + generic mechanism + data + decision | MD3-01/06/07 | range/terrain/TTL/断链/恢复/确定性、exact-ref | Catalog/generic path/MD3-07 refs `DONE`；MD3-06-003 已修复干扰结束后的有效共享航迹恢复并覆盖 checkpoint；地图派生 LOS 仍 `UNVALIDATED_BENCHMARK` |
| 7 能源 | ENE-001 | generic energy tick；MD3-06 environment multiplier 接至 idle/motion profile 与 weapon shot cost | catalog + generic mechanism | MD3-02/06 | 速度/传感/中继/开火/海况、耗尽降级 | MD3-06 generic path `DONE`；实际参数/场景耗尽覆盖待 MD3-07 |
| 8 天气环境 | ENV-001..003 | `weather_change`、`component_suppression` dispatcher；MD3-06 stable capability modifier pipeline；L3 t=300 已接入 V4 high-sea `@2.1.0` 与 exact L3 suppression ref | catalog + generic mechanism + data | MD3-01/06/07 | t=240/t=300、组合/恢复、子流隔离、exact-ref | Catalog/generic consumption/MD3-07 L3 ref `DONE` |
| 9 武器/射击/占位/自爆 | CBT-001..004、DMG-001..003 | generic target_domains、CombatSystem、DamageIntent、collision；MD3-03 also loads generic `contact_detonation` through the pending-impact authority; MD3-04 one-shot source trigger、seeded secondary、generic wreck/despawn | reuse + catalog + generic mechanism + decision | MD3-01/03/04/05 | surface matrix、pending impact、TOI、自爆、occupancy | MD3-03 follow-up `DONE`；MD3-04 P0/P1 修复后的 T2/T3 与结构化 `SELF_REVIEWED` 完成 |
| 10 ROE/任务/终局/可见性 | MIS-001..002、OBS-001、ACT-002 | MissionEngineV2、World ROE evidence、gateway observation、public `predict_intercept_waypoint` | reuse + generic mechanism + data | MD3-05/07/08 | priority/latch、public/faction visibility、receipt | MD3-05 `DONE`；终局/锁存回归通过，具体 data-only 规则待 MD3-07/08 |
| 11 评分/诊断 | SCR-001..003 | ScoringSystemV2、N/A/zero contract、`MetricDataMissingReceiptV2` | reuse + generic mechanism + data | MD3-05 | authority recomputation、missing/N-A、诊断 metrics | MD3-05 `DONE`；N/A 与 missing=0+审计证据契约完成，具体指标公式待 MD3-07 |
| 12 封锁定量 | GEO-004、SCR-003 | geography distance/heading、swept zone evidence、通用 radial/annular/front-track/path-conflict/duration/replan 原语 | generic mechanism + data | MD3-05 | arc/annular/front-track/path conflict regression | MD3-05 `DONE`；参数和场景评分数据待 MD3-07 |
| 13 智能体接口 | ACT-001..004、OBS-001 | ActionBatchV2、AgentGatewayV2、Gym/Vector/REST adapters；controller-scoped authority 与 fixed-dynamics navigation guard | reuse + generic mechanism + decision | MD3-01/05/08 | bilateral timeline equivalence、mask、GET non-advance、no WorldState | MD3-08 focused interface contract `DONE`；大规模矩阵后续阶段 |
| 14 L1/L2/L3 | L1-001、L2-001、L3-001、LVL-001 | formal registry/pipeline、data-only packages、public rule-agent profiles；L1/L2/L3 exact immutable refs | data + catalog + rules | MD3-07 | fixed-seed compile/run、rename、resolved-only diff、30-seed | MD3-07 resource integration `DONE`；MD3-11 完成 L1 40、L2 30、L3 30 个完整 1,500-tick seed，全部 passed |
| 15 可视化/日志/回放/检查点 | VIZ-001、RPL-001、LOG-001、CHK-001、MEM-001 | formal frame、renderer、replay v2、checkpoint v2、presentation snapshot、声明几何 task viewport | reuse + generic mechanism + catalog | MD3-09 | live/replay/frame、4 views、checkpoint states、bounds | MD3-09 `DONE`：无推进帧、faction/public 白名单隔离、live/replay 等价与 L3 高海况 checkpoint 后逐字段 frame 续跑；MMG 原始弧度状态和 mission fact 稳定排序已修复。MD3-09-002 将默认镜头改为静态任务几何取景，三种 view 不读取隐藏实时实体且不再以百万米地图框压缩任务运动。 |
| 16 附录 A/B/C | ARCH-004、PERF-001、DET-001、SEC-001 | Catalog hash/RNG/checkpoint/test plans | decision + catalog | MD3-01/02/10/11 | fidelity/source、hashes、deterministic and perf tests | MD3-10 `DONE`；MD3-11 `DONE`：静态门禁零问题、全量 pytest 2,111 passed、分组覆盖率 85%、L1/L2/L3 单会话 mean 均 <100 ms、16/32 session 隔离通过，100 局（三档各至少 30 seed）均完成。详见 full/performance/security 三份报告。 |

## U1–U13 参数确认追踪

所有 U 项在需求方冻结前均保持 `UNVALIDATED_BENCHMARK`；目标是可替换的 Catalog/Scenario 数据，而不是通过 Python 常量固定。

| U | V4 参数项 | REQ ID | 当前证据/状态 | 分类 | 目标 | 测试 | 审查 |
|---|---|---|---|---|---|---|---|
| U1 | 红蓝 USV 速度、转弯、舵角、尺度 | DYN-001、DYN-002 | MMG engine `VERIFIED`；MD3 profile `ABSENT` | catalog + decision | MD3-02 dynamics/platform | unit/isolation/trajectory | PENDING |
| U2 | 对海距离、Pd、精度、噪声 | SEN-001..002 | L1/L2/L3 8/4/12/6/20/3 km、Pd/噪声/周期及确认/stale/交战阈值档案 `CATALOG_DONE`；generic named-substream measurement、confirmation/stale、measurement-only observation `VERIFIED`；三档 exact-ref 接线已完成 | catalog + generic mechanism + decision | MD3-02/06/07 | noise/fusion/stale/exact-ref | MD3-02-002/003、MD3-06-002、MD3-07-002 `DONE` |
| U5 | 天气倍率/高海况功耗 | ENV-001..003 | stable environment modifier path `VERIFIED`; MD3-02-004 V4 high-sea data and MD3-06 profile-key/additive capability consumption `VERIFIED`; L3 schedule/reference t=300 已数据化 | catalog + generic mechanism + decision | MD3-01/02/06/07 | exact tick/modifier stack/exact-ref | MD3-02-004、MD3-06-002、MD3-07-002 `DONE` |
| U3 | 通信距离、带宽、时延、TTL、容错 | COM-001..002 | generic range/delay/TTL/loss/route/checkpoint `VERIFIED`; 20 km surface、50 km UAV/2-hop resources `CATALOG_DONE`，地图 LOS 仍 `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-01/06 | range/terrain/TTL | MD3-02-002 `DONE`；MD3-06 generic path `DONE` |
| U4 | 续航与功耗 | ENE-001 | generic energy modifier path `VERIFIED`; 具体 profile/耗尽数据仍 `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-02/06 | consumption/degrade | MD3-06 `DONE` |
| U5 | 天气倍率/高海况功耗 | ENV-001..003 | stable environment modifier path `VERIFIED`; 参数与 forecast timing 仍 `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-01/06 | exact tick/modifier stack | MD3-06 `DONE` |
| U6 | 对海 Pk、毁伤、弹药、门限 | CBT-001..003 | generic surface Combat/Effect/DamageIntent and `delayed_effect`/`contact_detonation` pending impact path `VERIFIED`; benchmark numbers remain `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-01/03 | range/Pk/ROE/ammo/RNG | MD3-03 follow-up `DONE` |
| U7 | 自爆、殉爆概率与半径 | DMG-001..003 | common damage + one-shot generic source trigger/wreck/secondary `VERIFIED`；子流仅锚定 seed/resolved/source evidence，数值仍 `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-01/04 | zone/TOI/secondary/restore | MD3-04 `DONE`；P0/P1 修复后的 T2/T3 与结构化 `SELF_REVIEWED` 完成 |
| U8 | 海流/风场、故障幅度与时刻 | ENV-003、DYN-002 | generic exact-component suppression/recovery `VERIFIED`; flow field 和数值仍 `UNVALIDATED_BENCHMARK` | catalog + generic mechanism + decision | MD3-01/06 | failure/recovery/no leak | MD3-06 `DONE` |
| U9 | 出生抖动、0/30/540 s | L1-001..L3-001、DET-001 | spawn events and RNG exist; MD3 data `ABSENT` | data + decision | MD3-07 | seed/order/rename | PENDING |
| U10 | 1500 s/180 s 时间策略 | SCN-003、MIS-002 | terminal priority/latch `VERIFIED`；具体 duration/truncated data `ABSENT` | data + decision | MD3-01/05/07 | terminated/truncated | MD3-05 机制 `DONE`；参数和三档验证待 MD3-07/08 |
| U11 | 资源建议、10 km 纵深、安全 0.7 | SCR-001..003 | score/N-A/missing audit core `VERIFIED`; formulas `ABSENT` | data + generic mechanism + decision | MD3-01/05 | recompute/missing | MD3-05 机制 `DONE`；公式与参数仍待冻结 |
| U12 | neutral 民船与关系 | SCN-002、CBT-003 | generic faction/relationship `VERIFIED`; scenario/ROE coverage `ABSENT` | data + decision | MD3-02/07 | neutral reject/visibility | PENDING |
| U13 | 6 km、010–120°、岸线接合 | GEO-003..004 | generic coordinate/sweep、连续 arc primitive `VERIFIED`; data `ABSENT` | data + generic mechanism + decision | MD3-01/02/05 | tangent/crossing/geometry | MD3-05 机制 `DONE`；具体参数仍为 `UNVALIDATED_BENCHMARK` |

## 约束性结论

1. MD3-02 只可添加已在 MD3-01 冻结的资源、地图引用和场景数据。
2. 对海交战、自爆、占位几何、环境/通信接线若需代码，必须作为可复用机制进入 MD3-03 至 MD3-06；不允许用场景 ID 或 entity ID 分支代替。
3. 现有 `MD-AD-002` 的 surface picket/MMG 只能作为 adapter、地图和测试参考，不能被误报为 MD3 surface combat 已交付。
4. U1–U13 不阻塞 benchmark 功能开发，但阻塞真实装备标定、正式比赛参数冻结及其宣传。

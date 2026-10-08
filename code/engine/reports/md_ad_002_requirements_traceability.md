# MD-AD-002 v1 需求追踪矩阵

> 工作包：AD2-00；日期：2026-08-17  
> 状态说明：目标代码/测试为计划路径，`TODO` 不表示当前已实现。

| 需求 | 冻结依据 | 当前资产 | 目标模块 | 强制测试 | 状态 |
|---|---|---|---|---|---|
| 三独立ID/YAML/哈希 | ADR-001 | scenario loader/hash | config + scenario registry | config contract、hash isolation | TODO AD2-01 |
| 正式弹药36枚、damage=1.0 | ADR-002/015（需求方批准v2） | combat inventory/damage | AD2 config/world builder/combat | inventory、单发毁伤、拒绝无副作用、成功/失败黄金轨迹 | DONE AD2-01/05/07 |
| CIWS 0.3–2km/1s | ADR-003 | WeaponSpec/engage | combat profiles/cooldown | 299/300/2000/2001m | TODO AD2-05 |
| 突防后武器差异ROE | ADR-004 | legality pipeline | AD2 ROE policy | 导弹拒绝+CIWS允许 | TODO AD2-05 |
| 3架突防阈值 | ADR-005/012 | MD-INT锁存参考 | missions/md_ad_002 | 第2/3架/同时突防 | TODO AD2-05 |
| 续航反推能耗 | ADR-006 | energy model | configured profiles | 续航误差<=2% | TODO AD2-01/02 |
| 即时概率武器 | ADR-007 | combat model | scenario weapon profile | 逐发RNG/同步毁伤 | TODO AD2-05 |
| breached_active/tombstone | ADR-008 | entity lifecycle | spawning + mission state | 突防后摧毁/impact/checkpoint | TODO AD2-03/05 |
| 场景天气profile | ADR-009/017 | weather model | AD2 weather config/runtime | 倍率/边界/checkpoint/旧场景回归 | MEDIUM DONE AD2-08；HARD TODO AD2-10 |
| 正延迟下一tick可见 | ADR-010 | comm queue | routed communication | 不提前可见/恢复顺序 | TODO AD2-09 |
| 安全分独立门槛 | ADR-011 | Metric基础 | scoring/md_ad_002 | 0–4违规/N/A重权 | TODO AD2-07 |
| 单目标单平台单发 | ADR-013 | simultaneous damage | engagement arbitration | 排列/注册顺序一致 | TODO AD2-05 |
| 虚警生命周期 | ADR-014 | sensor RNG/snapshot | false alarm tracker | seed/隔离/恢复 | TODO AD2-04 |
| 威海地图与地理验证 | req §5 | GeoFrame/map hashes | generic runtime + config | 经纬度、海陆、哈希、截图 | TODO AD2-01/02 |
| 7红方固定实体 | req §6.1 | PlatformAsset/build world | generic builder | 数量/类型/初态/海陆 | TODO AD2-01/02 |
| 15蓝方4/5/6波次 | req §6.2/8 | EventQueue | spawning system | 时间边界/ID/恢复 | TODO AD2-03 |
| UAV/USV/岸基动力学 | req §7 | existing domain models | generic scheduler | 类型trace/边界/顺序 | TODO AD2-02/03 |
| 碰撞和impact | req §7.5 | collision geometry | tick collision stage | 掠过/穿越/同步毁伤 | TODO AD2-03/05 |
| 五类传感器 | req §9.1 | Sensor/DetectionEngine | multi-sensor mounts | 范围/周期/修正 | TODO AD2-04 |
| 3确认/5删除/2s融合 | req §9.3 | simple tracks/fusion | track manager | 生命周期/重捕获/关联 | TODO AD2-04 |
| 最多2跳中继/干扰 | req §10 | single-hop network | route graph/queue | 直连/1/2跳/断链/TTL | TODO AD2-09 |
| 五级任务裁决 | req §13 | MD-INT adjudicator | MDAD002Adjudicator | 管理员/资源/清除/终态/超时 | TODO AD2-05 |
| Canonical RedObservation | req §14.2 | Observation DTO | schemas/md_ad_002 | JSON/防泄漏/视角 | TODO AD2-06 |
| Canonical RedActionBatch | req §14.3 | policy ActionBatch | shared schema/adapters | 原子校验/错误码/等价 | TODO AD2-06 |
| 固定tick顺序 | req §16 | env step/scheduler | generic runtime | golden order/checkpoint | TODO AD2-02～10 |
| 七项评分+N/A | req §17 | Metric | scoring/md_ad_002 | 公式/零分母/离线重算 | TODO AD2-07 |
| 日志/checkpoint/replay | req §18 | replay/visualization | extended DTO/snapshots | roundtrip/hash/views | TODO AD2-07～10 |
| 红/蓝规则智能体 | req §19 | MD-INT policies | AD2 policies | public API only/三难度 | EASY/MEDIUM DONE AD2-07/08；HARD TODO AD2-10 |
| 确定性/并发/性能 | req §20 | current tests/benchmark | AD2 test suites | seed/16/32/100局/soak | TODO AD2-11 |
| 独立代码审查 | plan §9 | 无AD2报告 | artifacts/review | P0/P1=0、修复复测 | TODO AD2-11 |
| 全量自测试 | plan §7/8 | make selftest | md-ad-002-selftest/full-test | 全层级100%通过 | TODO AD2-11 |

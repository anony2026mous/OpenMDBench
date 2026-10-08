# MD3-06 环境、能力与通信通用机制

## 交付边界

MD3-06 将环境、故障、通信和能源影响接入 `WorldStateV2` 的固定 tick
权威路径。机制只消费已解析资源、事件和运行时实体状态；没有场景、阵营、
平台或实体 ID 分支。

## 能力修饰顺序

`capability_modifier_v2.py` 的确定性顺序为：

```text
resolved base profile
  -> active environment modifiers (priority, modifier_id)
  -> exact component suppression
  -> lifecycle / energy availability clamp
```

环境资源可显式声明 `capability_modifiers`，也兼容已有的版本化倍率字段：
`motion_speed_multiplier`、`sensor_range_multiplier`、
`sensor_detection_probability_multiplier`、`weapon_hit_probability_multiplier`、
`communication_loss_multiplier` 与 `energy_consumption_multiplier`。资源的
`exact_ref` 和触发事件 ID 是修饰器审计身份的一部分。

- 动力学：修饰 kinematic `target_speed_mps` 与 MMG `nps`，不会改写原生
  adapter 内部状态。
- 传感/能源：修饰 generic subsystem 的范围、探测概率以及 idle/motion
  能耗率。
- 武器：World 安装 CombatSystem 时注入会话内 capability resolver；它影响
  Pk 和每发能耗，导弹在发射时冻结经修饰的 Pk。
- ComponentSuppression 以 `(entity_id, exact_component_ref)` 和
  `[active_from_tick, expires_tick)` 表达，过期后自动恢复。

tick 0 的 weather/suppression 在 World 初始化时就生效。随后事件在其
resolved tick 边界写入同一状态，因而从该 tick 起的动力学、传感、通信和
交战均读取同一份权威证据。

## 通信 transport

`communication_transport_v2.py` 保存原始秒值用于审计，而投递只使用整数
tick：非零延迟为 `ceil(delay_s / physics_dt)`，零延迟为 0。TTL 同样量化为
整数 tick，`scheduled_delivery_tick == expiry_tick` 允许投递。

每个 `send_message` intent 生成一条不可变审计记录，包含：通信资源引用、
原始 delay/TTL、量化 tick、路由、relay hops、链路可用性、loss probability、
命名 RNG 子流、抽样值和最终状态（`queued`、`delivered`、`expired`、
`dropped` 或 `blocked`）。

链路由端点生命周期、有效范围、jamming 和显式 `terrain_blocked` link
predicate 判定；同阵营、数据声明 `max_relay_hops` 的端点可按稳定 BFS 使用
中继。投递前会重新核验已记录路由中各端点的生命周期、jamming、范围和
terrain predicate。断链或丢包不重放消息；已排队消息到期也不会补发。因此 transport 不会
把过期 contact 注入 observation。现有 observation 的己方实体可见性继续由
其公开 jamming/链路隔离规则过滤。

地图派生的无线电遮蔽目前未臆造物理模型：若场景将来提供可验证的地形 LOS
predicate，可通过同一 `terrain_blocked` 输入接入，不需要修改 transport。

## 检查点与确定性

环境状态、suppression 和 message queue 均已属于
`WorldEventStateSnapshotV2`，故 canonical checkpoint 自动保存并恢复其
中间态。通信丢包使用
`sha256(session_seed, resolved_hash, tick, communication:message_id)` 命名
子流，不使用全局 RNG 或 session ID。能力修饰按 `(priority, modifier_id)`
稳定排序。

## MD3-06-002：量测、融合与档案化环境差异

传感器的 `detection_probability`（兼容旧字段 `probability`）、`update_ticks`、
`range_noise_fraction`、`bearing_noise_deg`、`confirmation_frames`、
`stale_after_ticks`、`engagement_max_age_ticks` 和
`minimum_contact_confidence` 均由通用 subsystem 消费。每个到期采样以
`sha256(seed, tick, sensor:owner:ref:target[:measurement])` 派生检测和量测子流；
距离和方位误差为配置上界内的确定性均匀样本。注册顺序及 session ID 不参与种子。

World 以 `(owner, target)` 聚合同 tick 的传感器报告，使用稳定的质量/样本/资源引用
排序选择当前量测，连续同源更新后才确认；未更新达到配置 stale 时限即移除。未确认
航迹的置信度为零且不进入 faction observation。确认航迹的 World evidence 和
checkpoint 保存量测位置、确认计数、stale 时限和源传感器；公开 observation 只发布该
量测位置，不再从当前目标真值重算新航迹位置。

环境可在自身数据中以 `sensor_profile_multiplier_keys` 指向组件档案中的倍率字段，
并以 `<capability>_additive` 施加加法能力调整。因此 V4 高海况的雷达 `×0.75`、
EO/IR `×0.70` 与通信丢包 `+0.05` 可由新版本 Catalog 数据表达；不需要场景、平台或
实体身份分支。

## 测试与已知风险

- `test_md_int_003_environment_communication.py` 覆盖 modifier 次序、失效、
  suppression、延迟/TTL 边界、World 消息延迟后的 checkpoint restore、直接
  路由审计，以及环境对武器 Pk 的通用接线。
- `test_jamming_observation_v2.py` 覆盖通信干扰仅在有效窗口内隐藏被隔离
  endpoint 及其共享航迹；checkpoint 恢复保持隔离，干扰结束后仍在明确
  有效期内的航迹恢复。拥有传感器来源的航迹仍严格使用资源配置的
  `stale_after_ticks`；无传感器来源的显式权威航迹使用其声明的最大有效期，
  到期后不重放。
- 聚焦回归覆盖 combat、checkpoint、declarative event 和 action contracts。
- U3/U4/U5/U8 参数保持 `UNVALIDATED_BENCHMARK`。本阶段没有新增 MD3
  场景或地图数据；其具体数值、forecast 和地图 LOS evidence 由 MD3-07
  data-only 场景接线验证。

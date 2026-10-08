# MD-AD-002 AD2-00 现状核查报告

> 日期：2026-08-17  
> 工作包：AD2-00  
> 结论：当前三个 MD-AD-002 场景均未达到 E2；本报告只审计，不宣称实现。

## 1. 输入与工作树

已完整阅读：

- `docs/parse3/agents3.md`；
- `docs/parse3/MD-AD-002_Three_Scenario_Requirements.md`；
- `docs/parse3/MD-AD-002_Codex_Implementation_Test_Review_Plan.md`；
- `docs/parse2/MD-INT-001_Vertical_Slice_Requirements.md`；
- `docs/parse2/MD-INT-001_Codex_Implementation_and_Test_Plan.md`；
- `docs/MD-AD-002_current_engine_capability_baseline.md`。

开始时无关未跟踪文件为 `../map_modified.py`，本工作包不读取、不修改。`docs/parse3/` 和能力边界文档是用户提供/本任务资料，保留不覆盖。

## 2. 总体结论

现有代码具有一个真实的 MD-INT-001 纵向切片和大量可复用组件，但通用场景 YAML 目前主要承担元数据加载。`OpenMDBenchEnv` 仅在 `scenario_id == "MD-INT-001"` 时加载 GeoFrame、专用配置、正式 `WorldState`、传感器、通信和裁决器（`openmdbench/envs/benchmark.py:95-127`）。MD-AD-002 占位 YAML 加载后 `world is None`，不能执行文档要求的 22 实体闭环。

因此正确路线是先泛化 MD-INT-001 接线，再逐包实现 AD2-01～AD2-10；不能复制三套主循环，也不能只新增三个 YAML。

## 3. 模块处置判定

| 能力 | 路径/调用证据 | 判定 | AD2 处理 |
|---|---|---|---|
| 实体与世界 | `core/entities.py:24-99`、`core/world.py:41-99` | reuse/extend | 复用注册表和 DTO；扩展 scheduled/tombstone/任务状态 |
| GeoFrame/威海地图 | `core/geography.py:18-247`；环境仅在 `benchmark.py:101-109` 加载 | adapt | 抽成所有正式场景可用的世界配置能力 |
| RNG/配置哈希 | `core/rng.py:15-77` | reuse/extend | 保留 SessionRNG；增加 spawn/weather/opponent/false_alarm/route 子流及快照 |
| 调度 | `core/scheduling.py:12-127` | extend | 用事件队列驱动波次、天气、干扰和压制 |
| UAV | `domains/air/uav.py:13-76`，主循环 `benchmark.py:801-846` | adapt | 复用运动学，性能参数场景化，移除固定主控实体假设 |
| USV/MMG | `domains/surface/mmg_adapter.py:24-116`，主循环约 `benchmark.py:750-799` | adapt | 复用 adapter，新增哨艇档案和多会话隔离测试 |
| 岸基 | `domains/shore/radar.py:11-35` | reuse/extend | 固定动力学复用，增加动作拒绝、双雷达/CIWS 配置 |
| 碰撞 | `systems/collision/model.py:12-75` | extend | 几何函数可用；接入统一 tick、同步毁伤和地图/禁入裁决 |
| 能量 | `systems/energy/model.py:11-84`；主循环约 `benchmark.py:848-878` | adapt | 算法复用；档案从全局平台类型改为配置注入，记录分项 |
| 天气 | `systems/weather/model.py:9-91` | extend | 时间线组件可用；主循环当前传感器/战斗固定 CLEAR（`benchmark.py:366,519`） |
| 传感器 | `systems/sensors/model.py:17-210` | extend | 更新率/FOV/RNG/快照可复用；增加距离衰减、RCS、3/5帧、虚警和多载荷 |
| 融合 | `systems/sensors/fusion.py:11-76` | extend | 数学融合可复用；增加2秒节拍、跨传感器稳定关联和生命周期 |
| 通信 | `systems/communications/network.py:14-166` | extend | 距离/带宽/队列/快照可复用；新增正延迟、TTL语义、多跳路由、丢包和干扰 |
| 战斗 | `systems/combat/model.py:15-230`、`damage.py:12-61` | extend | 武器/逐发RNG/同步毁伤复用；增加最小射程、cooldown、breach ROE 和目标级仲裁 |
| MD-INT-001 裁决 | `missions/md_int_001.py:1-83` | reference/new | 只作锁存/优先级参考；新增15目标 MD-AD-002 裁决器 |
| ActionBatch | `policies/actions.py:12-35` | extend | 批次基础可用；新增 schema_version、scenario_id、sensor/relay/ciws_auto 和原子校验 |
| Observation | `schemas/observation.py:12-68`、`core/world.py:69-99` | extend | 阵营白名单基础复用；新增 canonical RedObservation |
| Gym | `envs/benchmark.py:141-179` | replace adapter | 当前 action space 是二维 Box；新增固定槽位/mask wrapper，语义源仍是 DTO |
| REST | `api/models.py:15-17`、`api/app.py:156-183` | extend | 当前只收 `(speed, heading)`；增加版本化 ActionBatch 并保持旧接口兼容 |
| SDK | `sdk/client.py` | extend | 随公共模型同步，不允许独立语义 |
| Replay/checkpoint | `replay/checkpoint.py:23-99`、`replay/log.py:12-67` | extend | 基础可用；覆盖动态实体、波次、路由、天气、cooldown、breach和评分 |
| Visualization | `visualization/schema.py:12-108`、`live.py:105-143`、`renderer.py:70-300` | extend | DTO/retained renderer复用；增加禁入区、生成区、波次、中继和四视角 |
| 评分 | `scoring/metrics.py`、`scoring/md_int_001.py` | new/adapt | 通用 Metric/N/A 复用；新增 MD-AD-002 七项指标和离线重算 |

## 4. MD-INT-001 专用接线清单

必须在 AD2-02 泛化、不得扩散到三个新场景：

1. `benchmark.py:95`：仅 MD-INT-001 创建正式世界；
2. `benchmark.py:97`：配置路径固定为 `md_int_001_v1.yaml`；
3. `benchmark.py:184-190`：初始/目标实体固定为 `blue-uav-1`、`red-uav-1`；
4. `benchmark.py:208-250`：世界构建器为 `_build_md_int_world`，航向、速度和库存含固定规则；
5. `benchmark.py:252-263`：传感器 ID 列表固定为五实体；
6. `benchmark.py:270-299`：指挥端、链路范围和 USV 100 Mbps 固定；
7. `benchmark.py:302-325`：每种平台只能映射一个固定传感器；
8. `benchmark.py:366,519`：探测和战斗天气固定 CLEAR；
9. `benchmark.py:427-435,582-587`：观察、战斗和双边 step 依赖非空的专用 world；
10. `benchmark.py:606,630-640,659,810,881`：主控/威胁实体名固定；
11. `cli/__main__.py:82-85,122,181`：selftest/live/replay 入口只认 MD-INT-001；
12. `visualization/live_match.py:99,153`：实时可视化绑定专用配置和标题；
13. `policies/blue.py:79` 等：MD-INT-001 规则策略固定实体角色，不能用作通用运行时。

处理策略：引入配置驱动的 `ScenarioDefinition/ScenarioRuntime` 等价抽象；系统注册从解析后配置生成；MD-INT-001 通过兼容 definition 继续运行，三种 AD2 definition 共用同一调度器。

## 5. 现有实现缺口和冲突

### 配置与注册

- 公共场景 ID 正则仅允许 `MD-(...)-NNN`（`scenarios/schema.py:83`；`api/models.py:11`），不接受已冻结后缀。
- `EntityDeployment` 只有 id/side/type/position（`scenarios/schema.py:20-24`），无法表达动力学、载荷、通信和生命周期。
- schema 不核对部署数量与 `spawn_counts`，当前占位 MD-AD-002 已出现声明/实际不一致。

### 感知

- 探测概率为有效范围内固定 Pd、范围外0（`sensors/model.py:118-126`），不满足距离衰减。
- 噪声是笛卡尔高斯（`sensors/model.py:142-149`），不是距离/方位均匀误差。
- track 直接以 `(side, truth_entity_id)` 为内部键并按每次扫描增减 confidence（`sensors/model.py:94-100,150-186`），缺少3帧确认/5帧删除和虚警。
- 一个平台只返回一个传感器，无法为 UAV 同时挂雷达和 EO。

### 通信

- `send()` 只检查 sender→recipient 单跳，不计算路由；LOS 默认 latency=0，只有 acoustic 随机2～5 tick（`communications/network.py:72-112`）。
- 带宽只校验单条消息大小，不累计共享链路负载；没有丢包、hop metadata、环路防护和跨阵营路由规则。

### 战斗与裁决

- `WeaponSpec` 无最小射程/cooldown（`combat/model.py:15-23`）。
- 交战阈值和10 tick年龄写死（`combat/model.py:116-120`）。
- 现有 `resolve_combat` 对所有动作逐个结算，不执行“同目标同tick只接受一个平台”仲裁。
- MD-INT-001 裁决只有一个 breach bool，不能表示15个目标和3架阈值。

### 接口

- REST `ActionRequest.action` 是两个 float（`api/models.py:15-17`）。
- Gym action space 是二维 Box（`benchmark.py:141-149`）。
- Python `ActionBatch` 缺少 scenario/schema、sensor、relay和CIWS字段（`policies/actions.py:12-29`）。

## 6. 公平性、确定性与安全风险

- 当前战斗目标由 contact 附近敌方真值中选最近实体（`benchmark.py:458-475`）；这是裁判关联，但必须保证其 tie-break 稳定且不进入观察。
- `contact_tick = message_sent_tick or first_detected_tick` 会把合法 tick 0 当作假值，后续扩展应改为显式 `is not None` 并补边界测试。
- 当前传感器每个实例用 `seed + index`，ID列表顺序变化会改变随机流；AD2 应按稳定传感器 ID 派生具名子流。
- 动态出生、false alarm、route、weather、opponent 尚无完整独立子流和 checkpoint 证据。
- REST/观察已有会话隔离测试基础，但新 ActionBatch 必须重新验证原子拒绝、幂等和大小/NaN/Inf限制。

## 7. 已冻结规则

`docs/adr/AD2-ADR-001` 至 `AD2-ADR-014` 均为 Accepted，并逐项采用核心需求 v1 的固定结论。不存在留给实现者自行选择的裁决默认值。

## 8. AD2-00 结论与下一门禁

AD2-00 只在以下证据全部通过后完成：14 ADR 存在且 Accepted；本审计含专用分支、复用判定和缺口；追踪矩阵覆盖需求到代码/测试；基线测试通过。下一工作包只能是 AD2-01，不能直接实现 EASY 主循环。

## 9. 验证证据

执行日期：2026-08-17。

```bash
test "$(find docs/adr -maxdepth 1 -name 'AD2-ADR-*.md' | wc -l)" -eq 14
for f in docs/adr/AD2-ADR-*.md; do
  rg -q -- '- 状态：Accepted' "$f" || exit 1
done
git diff --check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/mpl-ad2-00 \
  .venv/bin/pytest -q \
  tests/contract/test_md_int_001_adrs.py \
  tests/contract/test_md_int_001_config.py \
  tests/contract/test_observation_no_leak.py \
  tests/scenarios/test_all_scenarios_load.py \
  tests/system/test_md_int_001_gym.py \
  tests/system/test_md_int_001_rest.py \
  tests/determinism/test_md_int_001_checkpoint_replay.py \
  tests/determinism/test_md_int_001_synchronous_order.py
```

结果：ADR 数量和状态检查通过，`git diff --check` 通过，pytest `19 passed`。两条警告分别来自 Taichi 的 Python 3.15 弃用预告和 Gymnasium Box 的输入转换，不是本工作包引入的失败。

AD2-00 状态：DONE。AD2-01 尚未开始。

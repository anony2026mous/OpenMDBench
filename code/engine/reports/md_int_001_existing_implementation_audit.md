# I001-A01：Ubuntu 现有实现审计

- 日期：2026-08-06
- 任务：I001-A01
- 状态：完成（仅审计；未修改生产实现）
- 基准：MD-INT-001 需求/实施计划 v1.1
- 工作树说明：上级 `.git` 目录为空挂载，`git status/diff` 不可用；本次只新增本报告和坐标基线特征测试，未覆盖既有文件。

## 1. 结论摘要

当前代码是“可复用的独立系统集合 + 单受控实体 Gym 主循环”，尚不是 MD-INT-001 五实体纵向切片。
`OpenMDBenchEnv.step()` 只推进第一个蓝方实体；没有调用威海地图、UAV 专用模型、MMG、雷达、
能量、传感器、通信、Combat、Mission 或 Scoring。回放会列出 YAML 中实体，但除首个蓝方实体外均为静态、
满健康和满能量，这不是五实体进入同一主循环的证据。

威海地图与正反 Web Mercator 转换确实存在，不应重写。但现有 XY 是
`EPSG:3857 米 / 50`，不是内部真实米制 ENU；运行时 offset 位于 map loader 外部，逆转换必须由调用者手工扣除。
在威海 ROI 抽样中，把 `XY×50` 当物理距离相对 WGS84 椭球测地距离偏大约 25.82%–26.03%，远超 0.5% 门槛。

## 2. 当前实际调用链

```text
REST actions
  openmdbench/api/app.py:146-177
    -> SessionStore.step() openmdbench/api/sessions.py:146-184
      -> OpenMDBenchEnv.step() openmdbench/envs/benchmark.py:129-151
        -> validate_kinematic_actions()
        -> 统一二维 position += velocity（仅第一个蓝方实体）
      -> SessionStore._write_replay_frame():200-254
        -> 首个蓝方写动态值，YAML 其余实体写静态值
```

未出现在这条调用链中的已有模块：`WorldState`、`EntityRegistry`、`step_uav`、`step_auv`、
Sim2Sea/MMG、`consume_energy`、`DetectionEngine`、`CommunicationNetwork`、`engage`、`Mission`、
`planning_metrics`/`execution_metrics`/`combined_score`、威海 map loader 与碰撞几何。

## 3. 场景与实体事实

`openmdbench/scenarios/interception/MD-INT-001.yaml:16-24` 只部署 `blue-uav-1` 和
`red-uav-1`，但 `spawn_counts:25-35` 声明应有 2 UAV、1 USV、1 雷达和 1 红 UAV；配置内部不一致。
位置只有抽象 `[x,y,z]`，无 WGS84。`world.bounds:6` 是独立 200 km 矩形，`map_id:7` 只是字符串，
没有版本、哈希、投影、scale 或 offset。时间限制为 1800 tick（第36行），不符合冻结前要求的 900 tick。

## 4. 动力学审计与唯一处置结论

| 实体/模型 | 当前文件与入口 | 状态量/控制量/算法与单位 | 测试 | A01 处置 |
|---|---|---|---|---|
| 主 Gym 运动 | `openmdbench/envs/benchmark.py:24,77-90,129-151` | 单一二维位置/速度；`[speed_mps, heading_deg]`；固定隐含 1 s；上限错误地统一为 12.9 m/s | `tests/integration/test_benchmark_env.py` 只验证单环境契约 | **extend/replace path**：保留 Gym 外壳，MD-INT-001 改接多实体引擎 |
| UAV | `openmdbench/domains/air/uav.py:12-62` | 三维位置、航向、速度、能量；30 deg/s 转弯、20 m/s 升降、80 m/s；无加减速度响应、degraded | `tests/unit/test_uav.py` 真实调用独立入口 | **extend**：复用公式并补速度响应/状态，再以 adapter 接主循环，禁止新增重复 UAV 模型 |
| USV MMG | `env/vessel_sim.py:596-618,708-718,768+`；MMG 参数在 `env/MMG_dataclass_f32.py`/`f64.py` | `eta=[x,y,psi]`、`nu=[u,v,r]`，输入 nps/rudder rad；Euler/RK 子步；另有 Nomoto 与 kinematic | 现有 OpenMDBench 测试只覆盖动作校验和几何，没有证明主循环调用 MMG | **adapt**：复用现有 Sim2Sea MMG，新增薄 adapter 和 trace；不得重写 MMG |
| USV 参数/几何 | `env/calibrated_vessels.py`、`openmdbench/domains/surface/usv.py:17-34` | KVLCC2 参数；Lpp/B 转胶囊碰撞尺寸 | `tests/unit/test_usv_geometry.py` | **adapt**：接线可复用；尺度适用性需 ADR，不能声称油轮参数即比赛 USV 实装 |
| 岸基雷达 | `openmdbench/domains/shore/radar.py:11-42` | 固定位置；sensor mode/beam heading；明确拒绝移动 | `tests/unit/test_shore_radar.py` | **adapt**：模型行为可复用，补状态/武器/主循环 adapter |
| AUV（本场景不部署） | `openmdbench/domains/underwater/auv.py:13-76` | 三维运动学；4.1 m/s、15 deg/s、2 m/s 垂向、0–300 m 深度 | `tests/unit/test_auv.py` | **reuse（非本切片）**；不得在 MD-INT-001 主循环制造 AUV |
| legacy kinematic/Nomoto | `env/vessel_sim.py:608-618,623-668,731-757` | Nomoto `r_dot=(Kδ-r)/T`；kinematic 有 0.3 加速度限幅 | 无 MD-INT-001 主循环测试 | **reuse only as explicit comparison/fast mode**，正式 USV 必须 MMG |

`env/vessel_sim.py:626-635,641-648,771-775` 在开启 legacy randomization 时直接使用 `ti.random`；
其确定性、seed 和 checkpoint 接入尚未证明。正式 MMG adapter 默认应禁用该路径或将其纳入可恢复 RNG 契约。

## 5. 世界、地图与坐标全链路

### 5.1 已有资产与身份

| 资产 | SHA-256 | 内容 |
|---|---|---|
| `env/map_data/weihai_raw_lonlat.txt` | `1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675` | 137 多边形、7620 顶点，WGS84 source of truth |
| `env/map_data/weihai_map.txt` | `6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067` | 同多边形的 Web Mercator/50 XY |

WGS84 范围：lon `[121.8166667, 122.7058362]`，lat `[37.05, 37.5743889]`。
未 offset XY 范围：X `[-408.171392, 1571.466527]`，Y `[-978.616455, 489.304593]`。
默认 margin=10 后 offset 为 `(418.171392, 988.616455)`。

### 5.2 正向路径

```text
WGS84 source
  -> tools/regenerate_map_data.py:118 GeoConverter(origin=[122.0,37.4], scale=50)
  -> env/geo_coordinate.py:96-116 EPSG:4326 -> EPSG:3857，减原点、除50
  -> weihai_map.txt
  -> env/map_loader.py:78-114 load_map
  -> env/map_loader.py:117-159 apply_coordinate_offset
  -> env/navigation_env.py:55-64 setup_line_obstacles
  -> Sim2Sea Taichi obstacle/collision grid
```

### 5.3 反向路径与缺口

`GeoConverter.xy_to_lonlat()`（`env/geo_coordinate.py:118-141`）对“未 offset 的 Mercator/50 XY”严格互逆。
它不知道 `navigation_env` 的 `map_offset_x/y`；调用者必须手工扣除 offset。当前没有统一对象保证实体、岸线、
checkpoint、回放和显示都做相同扣除。`map_origin_lonlat`/`map_scale` 未进入新版 `OpenMDBenchEnv`；
legacy `navigation_env` 也只从 args 读取 map 文件路径，没有把 origin/scale 注入 converter。

### 5.4 距离精度

从 7620 个真实顶点抽取四对跨 ROI 样本，以 WGS84 `Geod(ellps=WGS84)` 为基准：

| 测地距离 m | 现有 XY×50 m | 相对误差 |
|---:|---:|---:|
| 11971.229 | 15085.689 | 26.016% |
| 46895.838 | 59055.732 | 25.930% |
| 10320.761 | 13007.080 | 26.028% |
| 43131.862 | 54270.022 | 25.824% |

原因是 EPSG:3857 在纬度约 37° 的尺度畸变；现有 XY 适合作为兼容地图显示/碰撞坐标，不能作为传感器、
武器和动力学的真实米制距离。A01 判定：**extend existing coordinate capability**，后续建立唯一 GeoFrame，
保留旧 map XY adapter，同时增加真正局部 ENU 米层；不得复制投影公式到场景或系统模块。

### 5.5 基线特征测试

新增 `tests/unit/world/test_geo_converter_existing_behavior.py`，只描述当前行为：

- 默认原点/scale 和 WGS84↔XY 往返；
- checked-in XY 与原始 WGS84 投影一致；
- offset 必须在逆转换前显式扣除；
- 当前实现拒绝零 scale、但接受负 scale（待后续契约修复）。

命令：
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/unit/world/test_geo_converter_existing_behavior.py`

结果：4 passed，0 failed，0 skipped，退出码 0。Ruff 修复测试文件 import 分组后通过；mypy strict 通过。

## 6. 系统模块审计

| 模块 | 当前能力与证据 | 主循环状态 | A01 处置 |
|---|---|---|---|
| Entity/WorldState | `core/entities.py` 有 registry/lifecycle；`core/world.py:31-102` 有 side observation 白名单 | 未调用；Lifecycle 缺 degraded/crashed/drifting | **extend** |
| RNG | `core/rng.py:15-67` 命名子流、snapshot/restore | sensors/comms/combat 可用；主 Gym 使用 Gym numpy RNG，未统一 | **adapt** 到单一 session RNG |
| Energy | `systems/energy/model.py` 分段线性推进/传感器/中继/开火消耗 | 未调用 | **adapt** 接入每 tick；参数移 YAML |
| Sensors | `systems/sensors/model.py:41-155` 周期、天气、side contact、噪声/置信度 | 未调用；EO/IR 目前只允许 air→surface（55-72），不满足 UAV 拦截 air contact；低空 200 m 硬编码 | **extend** 后接入 |
| Fusion | `systems/sensors/fusion.py` | 独立测试 | **adapt** 接入并补过期时间 |
| Communications | `systems/communications/network.py:41-149` 范围、带宽、队列、snapshot | 未调用；LOS 无传播时延，wired 逻辑可复用 | **adapt** |
| Combat | `systems/combat/model.py:14-100` contact/ROE/射程/弹药/RNG | 未调用；使用至少一发命中概率且只伤害一次、统一 radar 天气修正、无 track/status multiplier、无同时毁伤 | **extend**，不能保留现有多发语义 |
| Collision | `systems/collision/model.py` 包围体/线段/多边形 | 新主循环未调用；legacy map collision 在 Sim2Sea | **adapt**，正式水面地图约束复用 legacy 路径 |
| Mission | `missions/state.py` 不可逆状态和到期事件 | 未调用；无 breach latch/优先级 | **extend** |
| Scoring | `scoring/metrics.py` 十指标和不可用值 | 未调用；`combined_score:117-133` 遇任一 N/A 整组不可用，不满足重加权；TE 公式不符合本场景 | **extend** 场景裁判，不复制通用 Metric |
| Replay | `replay/log.py` 流式 JSONL；`visualization/schema.py` 实体/detection/event/score | SessionStore 调用，但 metadata 无地图身份/solver，frame 无通信/弹药/多坐标；mission/environment 未填 | **extend schema/version** |
| Visualization | renderer/dashboard/playback 已按 frame 工作 | 只画空白坐标轴，无威海底图/ROI/轨迹/范围 | **adapt** frame 驱动，接同版地图 adapter |

## 7. 参数与配置审计

业务代码硬编码的 MD-INT-001 相关值包括：UAV 80 m/s、30 deg/s、20 m/s（`air/uav.py`）；
AUV 4.1/15/2（`underwater/auv.py`）；传感器低空 200 m、噪声 1%、初始 confidence 0.7、每次 ±0.1、
未探测 uncertainty×1.25（`sensors/model.py:51-71,120-149`）；武器表射程/命中/伤害（`combat/model.py:23-28`）；
能量表（`energy/model.py`）；主环境 12.9 m/s、10 m 到达阈值、1 s 隐含 tick（`envs/benchmark.py`）；
场景 200 km 矩形和 1800 tick。后续必须迁入版本化 YAML 并记录来源。

OpenMDBench 路径未发现直接 `random.random` 或未受控 `np.random` 抽样；均使用 `SessionRNG` 或 Gym RNG。
legacy Sim2Sea 的 `ti.random` 是确定性风险，需在正式 solver 接入时处理并测试。

## 8. 测试真实性审计

相关基线回归命令覆盖 48 项，结果 `48 passed, 0 failed, 0 skipped`，退出码 0；有 12 条 Gymnasium
类型/空间建议告警。独立测试真实调用各模块生产入口，但只有 `test_benchmark_env.py` 进入当前 Gym 主循环，
它仍是单实体。`test_match_logging.py` 证明日志包含 YAML 实体集合，不证明实体参与动力学或系统管线。

当前不存在以下真实性证据：五实体同 tick；威海世界进入新版环境；UAV/USV/雷达类型调用 trace；雷达→通信→contact→
策略→交战；逐发/同时毁伤；breach 优先级；蓝胜/红胜/timeout/同 tick 四轨迹；地图 checkpoint/replay 对齐。

## 9. 保留、修改、删除建议

- 保留：威海两份地图 source、GeoConverter 投影核心、map loader、Sim2Sea/MMG、SessionRNG、独立系统公共模型、
  ReplayWriter/Reader、VisualizationFrame 架构。
- 修改/扩展：GeoFrame/offset/米制层、MD-INT-001 schema/YAML、WorldState/Lifecycle、UAV 加速度、所有系统主循环接入、
  Combat 多发语义、任务裁决、N/A 评分、回放 metadata/frame。
- 增加薄 adapter：legacy map XY、Sim2Sea MMG、各类型动力学到统一实体状态。
- 后续替换：`OpenMDBenchEnv.step()` 的单实体内核；保留公共 Gym/REST 外壳兼容。
- 不删除：现有模型和其余 35 场景；迁移期通过显式路由兼容。

## 10. A01 验收判断与下一依赖

A01 审计产物、文件/行号、调用链、坐标基线、距离误差、缺口和唯一复用判定已经形成。
生产实现未改动。下一允许任务是 **I001-A02（建立 8 份 ADR）**；A03/A04 和阶段 B 均不得越级。

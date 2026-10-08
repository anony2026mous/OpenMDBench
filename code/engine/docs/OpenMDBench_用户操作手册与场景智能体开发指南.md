# OpenMDBench 用户操作手册与场景、智能体开发指南

本文从“第一次打开仓库”的视角，说明怎样认识目录、安装运行、配置兵力与武器、编译并加载新
场景、接入对抗智能体、实时显示、保存日志与回放，以及设置训练中的时间参数。内容以当前
公共 V2 契约为准，贯穿示例为 `MD-AD-002-EASY/MEDIUM/HARD` 和
`MD-INT-003-EASY/MEDIUM/HARD`。

## 0. 第一次阅读的建议路线

如果你只想先看到结果，按下列顺序：

1. 执行第 2 章的安装命令。
2. 执行第 3.2 节的 `live` 命令，看一场自动对抗。
3. 对照 `scenarios/formal/md_ad_002_easy/scenario.yaml` 阅读第 4～6 章。
4. 对照 `agents.yaml` 和 `examples/md_ad_002_sdk_policy.py` 阅读第 8～11 章。
5. 带 `--replay-output` 再运行一次，按第 14 章做离线回放。

## 1. 项目目录是做什么的

| 目录/文件 | 作用 | 初学者是否应直接修改 |
|---|---|---|
| `openmdbench/` | V2 引擎和公共 Python API | 新场景通常不改 |
| `openmdbench/schemas/` | 场景、观测、动作、事件等 DTO | 只在升级公共契约时改 |
| `openmdbench/catalog/` | Catalog/ModelRegistry 加载与受信模型登记 | 新资源通常只加 YAML |
| `openmdbench/scenarios/` | 场景安全解析、编译、ResolvedScenario | 新场景不加 ID 分支 |
| `openmdbench/world/` | 实体、动力学、边界、碰撞、生命周期的权威状态 | 不由场景直接调用 |
| `openmdbench/combat/` | ROE、接触、武器、命中、effect、damage | 新场景只选择资源 |
| `openmdbench/missions/` | 通用任务规则和评分 | 用 YAML 组合条件 |
| `openmdbench/sessions/` | Session 状态机、动作队列、唯一 tick writer、Runner | 智能体的主要入口 |
| `openmdbench/policies/` | 规则智能体示例 | 可复制 V2 示例，不要复制 Legacy |
| `openmdbench/visualization/` | 实时 FrameBuilder、Matplotlib renderer、回放显示 | 实体外形优先在 Catalog 配置 |
| `openmdbench/replay/` | JSONL 记录和不重新仿真的回放读取 | 通常直接使用 |
| `catalog/v2/` | 平台、动力学、外形、传感器、武器、弹药、毁伤等 data-only 资源 | 新挂载/资源在这里加 |
| `scenarios/formal/` | 可直接编译运行的正式 V2 场景 | 新场景首选复制模板 |
| `scenarios/synthetic/` | GS-001～004 通用性门禁场景 | 学习多阵营/规模/毁伤/动态事件 |
| `examples/` | 可执行的 SDK/智能体示例 | 推荐从这里开始 |
| `tests/` | contract/integration/determinism/system/security/performance | 新场景必须增加验收 |
| `artifacts/` | 用户指定的 replay、报告和测试产物的推荐根目录 | 不是自动日志黑洞 |
| `reports/` | 阶段性验收/审计报告 | 只保存经验证证据 |
| `docs/` | 需求、ADR、用户和开发文档 | 公共行为变更时同步更新 |
| `env/` `model/` 及旧 runner | Legacy 兼容路径 | 新 V2 场景不从这里派生 |

### 1.1 先理解两条运行路径

#### 推荐的新场景路径：schema-v2

```text
scenario.yaml (package@2.0)
  -> ScenarioPackageV2（安全解析、logical/content/archive hash）
  -> CatalogV2 + ModelRegistryV2（精确资源与受信工厂）
  -> ScenarioCompilerV2
  -> ResolvedScenarioV2（完整闭包、稳定排序、resolved_hash）
  -> WorldFactoryV2
  -> SessionLifecycleV2
  -> ObservationV2 / ActionBatchV2 / receipts / checkpoint / replay
```

新场景不得导入 Python、执行脚本、按场景 ID 分支、直接写 health/ammo/energy，也不得把模型算法塞入
YAML。新算法必须注册为受信、版本化的 ModelRegistry 工厂。

#### 正式场景与兼容路径

`MD-AD-002-EASY/MEDIUM/HARD` 与 `MD-INT-003-EASY/MEDIUM/HARD` 均为
`scenarios/formal/` 下独立的 V2 data-only ScenarioPackage，分别通过
`catalog/v2/md_ad_002.yaml` 与 `catalog/v2/md_int_003.yaml`、`ScenarioCompilerV2`、
`WorldFactoryV2`、`SessionLifecycleV2` 运行。它们是当前推荐的新场景复制范例。
`MD-INT-001` 与旧 CLI/live 路径仍保留 Legacy 兼容用途；不要从 Legacy runner 或专用 Python 分支
派生新场景。

选择建议：

| 目标 | 推荐入口 |
|---|---|
| 运行 MD-AD-002 V2 | CLI `run --scenario MD-AD-002-*` / `create_formal_session_v2` |
| 运行 MD-INT-003 V2 | CLI `run --scenario MD-INT-003-*` / `create_formal_session_v2` |
| 展示 MD-INT-003 实时画面 | `run_live_formal_v2`（当前 CLI `live` 的候选列表尚未列出该 ID） |
| 运行 Legacy 兼容回归 | CLI `selftest` / `live` |
| 新建通用场景 | `ScenarioPackageV2` + `ScenarioCompilerV2` |
| 新建智能体 | `StructuredPythonAdapterV2` 或 REST V2 |
| 强化学习 | `GymnasiumAdapterV2` / `VectorEnvAdapterV2` |
| 保持旧实验结果 | Legacy env/runner，不向其增加新权威逻辑 |

## 2. 安装与验证

支持 Ubuntu 22.04/24.04、Python 3.11/3.12。CPU 是发布基线。

```bash
make setup PYTHON=python3.11
source .venv/bin/activate
python -c "import openmdbench; print(openmdbench.__version__)"
make lint
make typecheck
make test
```

可选依赖：

```bash
.venv/bin/python -m pip install -e ".[train]"
.venv/bin/python -m pip install -e ".[server]"
.venv/bin/python -m pip install -e ".[cuda]"
```

服务器环境建议设置 `MPLCONFIGDIR=/tmp/openmdbench-mpl`，并使用 Agg/headless 渲染。

## 3. 运行现有任务

### 3.1 自测试

```bash
make selftest
make md-ad-002-selftest

# 或逐项
.venv/bin/python -m openmdbench.cli selftest --scenario MD-INT-001 --seed 7
.venv/bin/python -m openmdbench.cli selftest --scenario MD-AD-002-HARD --seed 7 --ticks 1800
.venv/bin/python -m openmdbench.cli run --scenario MD-INT-003-EASY --seed 73 --ticks 1500
```

MD-AD-002 的 `selftest` 默认把 authority log 写入
`artifacts/md-ad-002/<difficulty>-selftest.jsonl.gz`；其他命令以自身输出参数为准。
固定 seed、配置 hash、地图 hash 和 checkpoint/replay 证据用于复现。

### 3.2 实时可视化

```bash
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m openmdbench.cli live \
  --scenario MD-AD-002-MEDIUM --seed 73 --speed 10 --view referee \
  --replay-output artifacts/md-ad-002-medium-v2.jsonl
```

V2 正式场景窗口从版本化 Catalog 和已编译 ResolvedScenario 构建，不读取 Legacy runtime 私有字段。
以 MD-AD-002 为例，窗口显示威海海岸/陆地、任务区与生成区、实体外形和轨迹、传感器/武器
覆盖、能量与续航、通信/传感器/健康徽标、权威跟踪/锁定线、通信路由、打击命中/未命中效果、
波次、天气、任务终局和评分。tick 间展示子帧只做位置插值，不写 World，也不进入 Replay 权威记录。
EASY/MEDIUM/HARD 使用同一个 FrameBuilder 和
Renderer，仅由各自 data-only 配置决定实体、波次、环境和资源。

#### MD-INT-003 水面突袭的运行与实时展示

MD-INT-003 的共同任务是：防守方用拦截 USV、侦察 UAV 和岸基雷达保护核心区；进攻方自爆
USV 向核心区突入。突袭方进入核心区并触发自爆即为进攻方胜，全部突袭艇被消灭则防守方胜。
三档只由场景和规则智能体数据区分，不存在难度专用内核：

| 场景 | 进攻方式 | 环境/故障 |
|---|---|---|
| `MD-INT-003-EASY` | 3 艘突袭 USV 开局同时直接突入 | 正常海况 |
| `MD-INT-003-MEDIUM` | 0、30、540 tick 分批出现；首次被发现后规避转向 | 正常海况 |
| `MD-INT-003-HARD` | 多方向蛇形、变速、分批突入 | tick 300 高海况；tick 400 一部舰载雷达压制 120 tick |

当前 CLI `live --scenario` 的参数候选尚未列出 MD-INT-003；请直接使用正式 V2 实时入口：

```bash
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -c 'from openmdbench.visualization.live_formal_v2 import run_live_formal_v2; run_live_formal_v2("MD-INT-003-EASY", seed=73, speed=5, render_fps=12, view="referee")'
```

`speed` 是目标仿真秒/墙钟秒，`render_fps` 只限制 GUI 刷新，不会跳过权威 tick。formal V2
renderer 使用场景声明的核心区、航路、封锁区等任务几何计算默认镜头，完整威海底图仍在该任务
视野内绘制；镜头不读取实时实体位置，因此 faction/public 视图不会借此获知隐藏敌方航迹。
如需保存可回放记录，请在 Python 调用中传入 `replay_path=Path("artifacts/md-int-003-easy.jsonl")`。

`--view` 可选 `referee/faction/public`，使用 `faction` 时同时传 `--faction-id`（Legacy 命令仍
保留旧视角名）；智能体不能使用
`referee` 真值视图决策。窗口关闭只停止展示循环，不会把 Renderer 变成 World 写入者。

以 MD-AD-002 的 referee 视图为例：

- 蓝色是突防/进攻方，红色是防守方；这是可视化 faction role，不是内核固定红蓝阵营；
- UAV、USV、岸基设施的外形和尺寸来自 `visualization_assets` Catalog；
- `E` 电量徽标显示能量百分比，信号形徽标显示通信质量，`S+ / S-` 显示传感器状态；
- 实线/动效线用于通信、航迹跟踪、锁定和打击，命中/未命中来自 Combat receipt；
- 侧栏显示 tick/sim time、波次、环境/干扰、任务状态和评分；
- Renderer 只消费不可变 `VisualizationFrameV2`，窗口刷新快慢不改变仿真。

阵营视图命令：

```bash
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m openmdbench.cli live \
  --scenario MD-AD-002-HARD --seed 73 --speed 10 \
  --view faction --faction-id coalition.defender \
  --replay-output artifacts/md-ad-002-hard-defender.jsonl
```

### 3.3 回放

```bash
.venv/bin/python -m openmdbench.cli verify-replay artifacts/example.jsonl.gz
.venv/bin/python -m openmdbench.cli replay artifacts/example.jsonl.gz \
  --headless --output /tmp/frame.png --view public

# V2 丰富帧回放：不初始化仿真、Session、动力学或 RNG
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m openmdbench.cli replay-v2 \
  artifacts/md-ad-002-medium-v2.jsonl --speed 20
```

`live --replay-output` 写入的每条记录保存当 tick 实际显示的完整 `VisualizationFrameV2`、
World checkpoint hash 和事件 receipt hash。`replay-v2` 只验证 artifact 的
resolved/catalog/model-registry/record hash 并重绘同一帧，因此实时画面和回放画面不存在两套
场景专用逻辑。

ReplayWriter 会创建父目录，但为避免误覆盖实验证据，目标 JSONL 必须不存在。
需要重跑时请换新文件名或先将旧文件归档。

### 3.4 对抗结束后文件在哪里

OpenMDBench 不会把所有运行隐式写到某个全局目录。文件位置由调用者显式指定：

- `live --replay-output artifacts/name.jsonl`：权威可视化/replay 日志；
- CLI `run`：只在 stdout 输出终局、得分和 checkpoint hash 摘要；
- `session.checkpoint()`：返回 `SessionCheckpointV2`，是否落盘由你的应用决定；
- 测试/发布报告：通常放在 `artifacts/platform-refactor/` 和 `reports/`。

推荐每次实验建立独立目录：

```text
artifacts/experiments/2026-08-28-hard-seed73/
├── replay.jsonl
├── final-checkpoint.json
├── run-summary.json
└── notes.md
```

Replay JSONL 首行是 `ReplayHeaderV2`，后续每行是一个 `ReplayRecordV2`。重要字段包括
session/resolved/catalog/model-registry hash、seed、tick、完整 frame、World checkpoint hash 和
event receipt hashes。这是“显示过什么就回放什么”的证据，不是只保存坐标的普通视频。
它也不代替训练数据库；若要保存 observation/action/reward、submit/apply receipt
和模型梯度，应由训练程序另行持久化。

程序化读取：

```python
from pathlib import Path
from openmdbench.replay.v2 import ReplayReaderV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
reader = ReplayReaderV2(
    Path("artifacts/md-ad-002-medium-v2.jsonl"),
    expected_resolved_hash=resolved.resolved_hash,
    expected_catalog_hash=resolved.catalog_hash,
    expected_model_registry_hash=resolved.model_registry_hash,
)
print(reader.header.resolved_hash, reader.header.seed)
for record in reader.records():
    print(record.tick, record.frame.mission, record.frame.scores_by_faction)
```

## 4. V2 场景包结构

可直接参考：

- 场景注册：`scenarios/formal/registry.yaml`；
- EASY/MEDIUM/HARD：`scenarios/formal/md_ad_002_*/scenario.yaml`；
- 共享资源：`catalog/v2/md_ad_002.yaml`；
- 编译入口：`openmdbench.scenarios.formal_v2.compile_formal_scenario_v2`；
- Session/Gateway：`openmdbench.sessions.formal_v2`；
- 智能体：`examples/md_ad_002_sdk_policy.py`。
- 对抗规则参数：`scenarios/formal/md_ad_002_*/agents.yaml`；通用实现：
  `openmdbench.policies.rule_v2.FormalRuleAgentTeamV2`。

### 4.0 从 MD-AD-002 复制一个可运行的新场景

对初学者最稳妥的方式是先复制包，再逐项替换数据：

```bash
cp -a scenarios/formal/md_ad_002_easy scenarios/formal/harbor_defence_demo
```

然后修改 `harbor_defence_demo/scenario.yaml` 中的：

1. `scenario_id` 和 `display_name`；
2. `factions/relationships`；
3. `entities` 中的兵力、初始位置和挂载；
4. `world.zones/roe_rules`；
5. `events`、`mission_rules`、`scoring`；
6. `controller_slots/visibility`。

在 `scenarios/formal/registry.yaml` 注册公开名称：

```yaml
- public_id: HARBOR-DEFENCE-DEMO
  package: harbor_defence_demo
  catalog_bundle: md_ad_002
```

`catalog_bundle` 是 `catalog/v2/<name>.yaml` 的文件名。开始时可以复用
`md_ad_002`；当你新增平台或武器时，再建立独立 bundle。

#### 阵营和敌我关系

```yaml
factions:
  - {schema_version: "2.0", id: coalition.defender, display_name: 防守方}
  - {schema_version: "2.0", id: coalition.intruder, display_name: 突防方}
relationships:
  - {schema_version: "2.0", source_faction_id: coalition.defender,
     target_faction_id: coalition.intruder, relation: hostile}
  - {schema_version: "2.0", source_faction_id: coalition.intruder,
     target_faction_id: coalition.defender, relation: hostile}
```

`hostile` 只表示关系，不自动授权开火。可交战方向必须在 `world.roe_rules`
显式声明：

```yaml
world:
  schema_version: "2.0"
  coordinate_system: local_m
  map_ref: map.weihai-local@2.0.0
  tick_seconds: 1.0
  duration_ticks: 1800
  roe_rules:
    - schema_version: "2.0"
      id: roe.defender-engage-intruder
      source_faction_id: coalition.defender
      target_faction_id: coalition.intruder
      relationship: hostile
      engagement_permitted: true
```

#### 配置一个实体和其武器挂载

MD-AD-002 拦截机的可直接编译配置是：

```yaml
- schema_version: "2.0"
  id: defender.interceptor-001
  faction_id: coalition.defender
  platform_ref: platform.interceptor-uav@2.0.0
  dynamics_ref: dynamics.interceptor-uav@2.0.0
  loadout_ref: loadout.interceptor-uav@2.0.0
  component_refs:
    - sensor.interceptor-radar@2.0.0
    - sensor.interceptor-eo@2.0.0
    - communication.command-network@2.0.0
  ammunition: {ammunition.interceptor-missile@2.0.0: 12}
  target_domains: [air]
  initial_state:
    schema_version: "2.0"
    position_m: [7048.0, 3330.0, 800.0]
    velocity_mps: [25.0, 0.0, 0.0]
    heading_deg: 90.0
    health: 1.0
    energy: 1.0
  controller_slot: controller.defender.interceptor-001
  tags: [defence, interceptor]
```

其中：

- `platform_ref` 决定平台域、槽位、尺寸、碰撞体和可视化资产；
- `dynamics_ref` 决定速度、转弯、垂直运动等执行模型；
- `loadout_ref` 声明安装了哪些 weapon/ammunition 资源；
- `component_refs` 是传感器、通信、能源等组件；
- `ammunition` 是本 session 的初始弹药数，不写在 Catalog 全局状态中；
- `controller_slot` 决定哪个智能体可以控制它；
- `tags` 供任务 selector、智能体策略和可视化使用。

挂载在 Catalog 中的闭包是：

```text
loadout.interceptor-uav@2.0.0
  -> weapon.interceptor-missile@2.0.0
  -> ammunition.interceptor-missile@2.0.0
weapon.interceptor-missile@2.0.0
  -> effect.interceptor-hit@2.0.0
  -> damage.kinetic-terminal@2.0.0
```

修改武器时不能只换 `weapon_ref`；必须同时保证平台槽位、loadout、弹药、
effect、damage model、目标域和单位形成完整 exact-ref 闭包。

#### 动态兵力（波次生成）

不在 tick 0 出现的兵力放在 `events` 的 `spawn` payload 中。MD-AD-002 的第二波
在 tick 600 生成：

```yaml
- schema_version: "2.0"
  id: wave-2.intruder-001
  event_type: spawn
  trigger: {kind: tick, tick: 600}
  priority: 90
  depends_on: []
  payload:
    entity:
      schema_version: "2.0"
      id: intruder.wave-2-001
      faction_id: coalition.intruder
      platform_ref: platform.interceptor-uav@2.0.0
      dynamics_ref: dynamics.interceptor-uav@2.0.0
      component_refs: [communication.command-network@2.0.0]
      initial_state:
        {schema_version: "2.0", position_m: [24668.0, 3130.0, 100.0],
         velocity_mps: [-35.0, -5.0, 0.0], heading_deg: 262.0, energy: 1.0}
      tags: [intruder, wave-2]
```

动态实体仍必须在 `controller_slots`、mission selector 和 visibility 的编译闭包中可解析；
不要在 tick 时用 Python 临时创建未编译实体。

三个难度不通过 `if scenario_id == ...` 分支实现，而是分别声明 exact resource version、环境与
typed events。spawn 波次实体也在编译期进入 selector/controller 闭包，实际 spawn 后由 World 更新
authority grant；智能体只提交公开 `ActionBatchV2`。

`agents.yaml` 中的 `attack.pattern` 选择 `direct`/`split_evasion`/`multi_axis_serpentine`，
`defence.weapon_policies` 声明 tag selector、exact weapon ref、射程和 cooldown。防守策略只消费
`ObservationV2` 的估计航迹；不可解析 contact ID 推测实体 ID，也不可读取 World 私有状态。
射击 payload 使用 `contact_id`，Session 内部再将其解析为目标并完成 contact/ROE/射程/
弹药/cooldown 复验。

最小目录：

```text
scenarios/local/example/
└── scenario.yaml
```

单文件必须是：

```yaml
schema_version: package@2.0
scenario:
  schema_version: "2.0"
  scenario_id: example.harbor-patrol
  factions:
    - {schema_version: "2.0", id: coalition.alpha}
  relationships: []
  entities: []
  formations: []
  world:
    schema_version: "2.0"
    coordinate_system: local_m
    tick_seconds: 1.0
    duration_ticks: 600
    zones: []
  events: []
  mission_rules: []
  score_metrics: []
```

多文件包可在 manifest 中使用 `includes`，但文件必须位于包根目录内；绝对路径、`..`、symlink、
重复 ZIP 路径、加密条目、超限条目和 YAML anchor/alias 会被拒绝。

### 4.1 生成、验证、打包

```python
from pathlib import Path
from openmdbench.scenarios.sdk_v2 import ScenarioSdkV2

root = Path("scenarios/local/example")
ScenarioSdkV2.create(root, name="example.harbor-patrol")
package = ScenarioSdkV2.validate(root)
archive_hash = ScenarioSdkV2.pack(root, Path("/tmp/example.zip"))
print(package.logical_hash, archive_hash)
```

`logical_hash` 忽略场景名称和打包差异，用于通用性/重命名等价；`content_hash` 和 `archive_hash`
保留来源证据。不要自行拼接或覆盖这些 hash。

### 4.2 场景顶层字段

| 字段 | 说明 |
|---|---|
| `factions` | 任意阵营 ID、名称、tags；不得假设只有 red/blue |
| `relationships` | `hostile/friendly/neutral/protected` 有向关系 |
| `entities` | 独立实体及其精确资源引用、初态、controller slot |
| `formations` | `count + id_pattern + entity_template + offsets_m` 稳定展开 |
| `world` | 坐标、地图、区域、边界、碰撞毁伤策略、tick 与持续时间 |
| `events` | typed event、trigger、priority、dependencies、payload |
| `mission_rules` | typed condition tree、selector、priority、outcome、latch |
| `score_metrics` | value/N-A、weight；扩展 scoring/plugin 由编译器冻结 |

### 4.3 实体定义

```yaml
- schema_version: "2.0"
  id: asset.uav.001
  faction_id: coalition.alpha
  platform_ref: platform.uav@2.0.0
  dynamics_ref: models.native-uav-kinematics@2.0.0
  loadout_ref: loadout.interceptor@2.0.0
  component_refs: [sensor.radar@2.0.0, link.los@2.0.0]
  ammunition: {round.interceptor@2.0.0: 2}
  target_domains: [air]
  initial_state:
    schema_version: "2.0"
    position_m: [1000.0, 2000.0, 1200.0]
    velocity_mps: [40.0, 0.0, 0.0]
    heading_deg: 90.0
    health: 1.0
    energy: 1.0
  controller_slot: controller/asset.uav.001
  tags: [interceptor, airborne]
```

上例引用名称仅示意，必须在你的 Catalog 中真实存在且类型、依赖、单位、平台兼容、模型工厂完全匹配。
可直接编译的实际示例见 `scenarios/synthetic/gs_003`。

### 4.4 编组

```yaml
formations:
  - schema_version: "2.0"
    id: formation.patrol
    count: 10
    id_pattern: patrol-{index:03d}
    offsets_m: [[0.0, 0.0, 0.0]]
    entity_template: { ...完整 EntitySpecV2... }
```

`id_pattern` 必须含 `{index}`；offset 数量只能为 0、1 或等于 count；展开后实体 ID 和 controller
slot 必须全局唯一。`gs_002` 覆盖 1/10/100 稳定展开。

## 5. Catalog 与 ModelRegistry

### 5.1 Catalog 资源类型

`CatalogResourceV2.resource_type` 支持：maps、platforms、dynamics、collision_shapes、sensors、
communications、weapons、ammunition、effects、damage_models、energy、environments、loadouts、
visualization_assets、missions、scoring、trusted_model_plugins。

每个资源都必须有：

- `id`、semantic `version` 和精确 `exact_ref=id@version`；
- `engine_compatibility`；
- `model_id`，且 ModelRegistry 中存在同版本受信工厂；
- data-only `content` 和精确 `dependencies`；
- 不包含 health、remaining ammo、cooldown、RNG、queue 等 session mutable state。

典型武器闭包：

```text
platform/loadout
  -> ammunition
  -> weapon
  -> effect
  -> damage_model
```

任何 missing、wrong type、wrong unit、untrusted artifact 或依赖环都会在 Catalog/Compiler 边界拒绝。

### 5.2 Registry 工厂要求

`ModelFactoryMetadataV2` 必须声明 interface 2.0、input/output schema、units、determinism、线程/进程
安全属性、trusted、artifact SHA-256 和允许的 resource types。Registry 在构建 Catalog 前冻结；每个
session 通过 factory 创建新实例，不共享带状态 adapter。

## 6. 编译和 ResolvedScenario

```python
from pathlib import Path
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2

package = ScenarioPackageV2.from_directory(Path("scenarios/local/example"))
resolved = ScenarioCompilerV2(catalog=catalog).compile(package)
resolved.validate_integrity()
Path("/tmp/resolved.json").write_text(resolved.to_json(), encoding="utf-8")
```

Compiler 固定执行 schema、resource versions、defaults、units、faction/relationship、formation、
compatibility、coordinates、boundary、event dependency、mission/scoring/controller、visibility、stable
order、freeze/hash 阶段。失败采用稳定的“最早阶段 + 文件路径”策略。

运行期只消费 `ResolvedScenarioV2`，不重新读取源 YAML 或 Catalog。Checkpoint restore 必须重新提供
相同 Resolved、Registry、session ID、seed 和 expected checkpoint hash。

### 6.1 注册后怎样加载场景

已加入 `scenarios/formal/registry.yaml` 的场景，使用：

```python
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.formal_v2 import create_formal_session_v2

resolved, catalog = compile_formal_scenario_v2("MD-AD-002-EASY")
print(resolved.scenario_id, resolved.resolved_hash)

session = create_formal_session_v2(
    "MD-AD-002-EASY",
    session_id="tutorial.session.001",
    seed=73,
)
session.load().start()
try:
    receipt = session.step(operation_id="tutorial.tick.0", expected_tick=0)
    print(receipt.tick)
finally:
    session.stop().close()
```

命令行无头运行：

```bash
.venv/bin/python -m openmdbench.cli run \
  --scenario MD-AD-002-EASY --seed 73 --ticks 1800
```

`run` 把最终摘要写到 stdout，它不会默认创建 replay 文件。要保存可回放记录，
必须使用第 3.2 节的 `live --replay-output PATH`，或在自己的 runner 中显式创建
`ReplayWriterV2`。

## 7. World 与 Session 生命周期

状态机：

```text
created -> loaded -> running <-> paused -> stopped -> closed
   |          |                     |
   +----------+---------------------+-> closed（仅允许表内转换）
```

标准调用：

```python
session = SessionLifecycleV2.create(
    session_id="session.example.001",
    seed=73,
    resolved=resolved,
    expected_resolved_hash=resolved.resolved_hash,
    catalog_hash=resolved.catalog_hash,
    model_registry_hash=resolved.model_registry_hash,
    world_factory=world_factory,
    runner_mode="lockstep",
    physics_dt_seconds=1.0,
    decision_interval_ticks=1,
)
session.load().start()
observation = session.world_view.observation(observer_faction_id="coalition.alpha")
checkpoint = session.checkpoint()
session.stop().close()
```

`world_factory` 由应用装配层使用相同 Catalog/Registry 构造。Session 不公开 mutable World 或 queue；
只公开 `world_view`、`queue_view`、`action_status_view`。所有变更必须经过 `submit_actions` 和 `step`。

## 8. 智能体观察契约

`ObservationV2` 包含：

- `session_id`、`tick`、`observer_faction_id`；
- `own_entities`：己方权威实体视图；
- `contacts_by_faction`：按 visibility/contact evidence 过滤的联系人；
- `metadata`：公开、冻结的补充信息。

contact 的公开字段包含 `contact_id`、`observer_entity_id`、`estimated_position_m`、
`observed_tick/age_ticks`、`confidence/quality`。`estimated_position_m` 是与传感器证据绑定的
确定性有界航迹估计，不是敌方 World 真值引用。

不要依赖字典字段顺序、私有 World 属性、敌方真实 entity ID、全局 health 或 referee frame。智能体应按
schema 字段和能力证据编程，并容忍 0/1/10/100 实体。

## 9. 动作批次

### 9.1 批次不变量

`ActionBatchV2` 必须绑定 session、faction、based/valid tick；`batch_id`、`idempotency_key`、每个
command/action ID 在 session 内必须唯一。child 的 faction 和 tick window 必须完全落在 batch 内。

验证顺序固定为：session state → operation fingerprint → tick window → controller authority → entity
lifecycle → faction ownership → action schema → required capability → payload。整批部分无效会原子拒绝。

### 9.2 导航示例

```python
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2

tick = observation.tick
nav = PersistentCommandV2(
    schema_version="2.0",
    command_id=f"cmd.nav.{tick}",
    command_type="navigation",
    entity_id="asset.uav.001",
    faction_id="coalition.alpha",
    based_on_tick=tick,
    valid_until_tick=tick + 5,
    payload={"speed_mps": 40.0, "heading_deg": 135.0, "altitude_m": 1000.0},
)
batch = ActionBatchV2(
    schema_version="2.0",
    session_id=observation.session_id,
    batch_id=f"batch.{tick}",
    idempotency_key=f"decision.{tick}",
    faction_id="coalition.alpha",
    based_on_tick=tick,
    valid_until_tick=tick + 5,
    persistent_commands=(nav,),
)
```

### 9.3 开火和消息

```python
from openmdbench.schemas.interface_v2 import DiscreteActionV2

fire = DiscreteActionV2(
    schema_version="2.0",
    action_id=f"fire.{tick}",
    action_type="fire_weapon",
    entity_id="asset.uav.001",
    faction_id="coalition.alpha",
    based_on_tick=tick,
    valid_until_tick=tick,
    payload={
        "weapon_ref": "weapon.interceptor-missile@2.0.0",
        "contact_id": "sensor.contact.opaque-track-ref",
    },
)
message = DiscreteActionV2(
    schema_version="2.0",
    action_id=f"message.{tick}",
    action_type="send_message",
    entity_id="asset.uav.001",
    faction_id="coalition.alpha",
    based_on_tick=tick,
    valid_until_tick=tick,
    payload={"recipient_id": "asset.usv.001", "message": "track contact.042"},
)
```

规则智能体应使用当前 `ObservationV2` 发布的 opaque `contact_id`。Session 内部才解析
真实目标，并复验 contact owner/freshness/confidence、ROE、射程、弹药和 cooldown。
`target_id` 是受信系统集成的精确目标入口；普通 faction 智能体不应从 referee 真值构造它。

### 9.4 当前 dispatch 状态

| 类型 | 当前状态 |
|---|---|
| `navigation` | 可执行，映射到 native dynamics control |
| `hold` | 可执行，生成安全保持控制 |
| `fire_weapon` | 可执行，进入 World-owned CombatSystem |
| `send_message` | 可执行，进入 typed message/event 路径 |
| patrol/sensor_mode/relay_mode/ciws_auto | schema 已定义，当前 submit fail-closed |
| release_payload/device_action/ram | schema 已定义，当前 submit fail-closed |

在 inventory 文档或 `persistent_action_contract_v2()` / `discrete_action_contract_v2()` 返回
`dispatch_available=False` 时，不要等待运行时“以后也许执行”；submit 必须失败且 queue/World 不变。

## 10. Python、Gym、Vector 智能体

### 10.1 Structured Python

```python
from openmdbench.sessions.gateway_v2 import StructuredPythonAdapterV2

agent_io = StructuredPythonAdapterV2(
    gateway, session_id="session.example.001", faction_id="coalition.alpha"
)
observation = agent_io.observation()
submit_receipt = agent_io.submit(
    batch, authority_token=authority_token, operation_id=f"agent.submit.{observation.tick}"
)
apply_receipt = agent_io.step(operation_id=f"agent.tick.{observation.tick}")
```

重复同一 operation ID 和相同 fingerprint 返回同一 receipt；同 ID 不同输入会冲突。不要通过重试重复
开火。

### 10.2 Gymnasium

`GymnasiumAdapterV2` 保持标准 `reset()`、`step()` 五元组；动作是 `ActionBatchV2 | None`，不是任意
浮点数组。当前 reward 适配层默认 0，任务得分和训练 reward 应从 Mission/Scoring 的声明与 receipt
读取，不能混为一项。

### 10.3 Vector

`VectorEnvAdapterV2` 要求动作数量与 session 数量一致。每个 session 拥有独立 World、RNG、Registry
runtime adapter、queue 和 checkpoint；不要跨 session 复用 mutable policy state。

## 11. Runner

- `LockstepRunnerV2`：每次显式推进 `decision_interval_ticks`，适合评测和训练。
- `ContinuousRunnerV2`：唯一后台 writer，按 `speed_ratio` pacing；支持 pause/resume/terminate/close。
- `ReplayRunnerV2`：只消费记录，不初始化 mutable World。

### 11.1 时间和训练参数

| 参数 | 含义 | MD-AD-002 例子 |
|---|---|---|
| `seed` | Session RNG 根种子；同 Resolved+动作时间线用于复现 | `73` |
| `physics_dt_seconds` | 一个 physics tick 代表的仿真时间 | `1.0` s |
| `decision_interval_ticks` | 智能体每次决策之间推进多少 physics tick | 训练可设 `5` |
| `speed_ratio` | 目标仿真时间/墙钟时间；`10` 表示目标 10x | `10.0` |
| CLI `--speed` | 实时窗口的目标播放速率（tick/s） | tick=1s 时 `10` 约等于 10x |
| CLI `--ticks` | 本次最多推进 tick 数 | `1800` |
| command `valid_until_tick` | persistent command 的有效窗口 | 通常覆盖下一决策点 |

`physics_dt_seconds` 会改变积分的物理时间；`speed_ratio`/CLI `--speed` 只改变墙钟
pacing，不应改变逻辑结果。训练中想“不等待实时”，优先使用 Lockstep 快速调用，
而不是改大 `physics_dt_seconds`。`speed_ratio=float("inf")` 表示不主动 sleep 的 unbounded
continuous pacing，仍受实际 CPU/模型耗时限制。

```python
from openmdbench.sessions.runners_v2 import LockstepRunnerV2, RunnerConfigV2

runner = LockstepRunnerV2(
    session=session,
    config=RunnerConfigV2(
        physics_dt_seconds=1.0,
        decision_interval_ticks=5,
        speed_ratio=10.0,
    ),
)
decision = runner.step(operation_id="decision.0001", expected_tick=session.world_view.tick)
```

规则或 RL 训练的典型循环：

```python
from openmdbench.policies.rule_v2 import FormalRuleAgentTeamV2
from openmdbench.sessions.formal_v2 import create_formal_session_v2

agents = FormalRuleAgentTeamV2.for_scenario("MD-AD-002-HARD", seed=73)
session = create_formal_session_v2(
    "MD-AD-002-HARD", session_id="train.episode.0001", seed=73
)
session.load().start()
try:
    while session.world_view.tick < 1800:
        observation = session.world_view.observation(
            observer_faction_id="coalition.intruder"
        )
        agents(session)  # RL 时替换成 model(observation) + submit_actions
        receipt = session.step(
            operation_id=f"train.tick.{observation.tick}",
            expected_tick=observation.tick,
        )
        mission = receipt.world_receipt.mission_receipts
        scores = receipt.world_receipt.score_receipts
        # 将 observation/action/reward/done 写入你的训练 buffer
finally:
    session.stop().close()
```

关闭顺序：停止 runner → join/close runner → stop session → close session。

## 12. REST V2

REST 是 `AgentGatewayV2` 的薄传输层，不拥有第二套仿真语义。应用必须注入：

```python
gateway = AgentGatewayV2(
    session_factory=create_session_from_approved_scenario,
    restore_factory=restore_session_from_checkpoint,
)
app = create_gateway_app_v2(gateway)
```

创建和启动：

```bash
curl -X POST http://127.0.0.1:8000/v2/sessions \
  -H 'content-type: application/json' \
  -d '{"session_id":"session.rest.001","seed":73}'
curl -X POST http://127.0.0.1:8000/v2/sessions/session.rest.001/control \
  -H 'content-type: application/json' -d '{"operation":"load"}'
curl -X POST http://127.0.0.1:8000/v2/sessions/session.rest.001/control \
  -H 'content-type: application/json' -d '{"operation":"start"}'
```

动作请求体：

```json
{
  "batch": {"schema_version":"2.0", "session_id":"session.rest.001", "...":"..."},
  "authority_token": "<controller-issued-token>",
  "operation_id": "rest.submit.0001",
  "expected_tick": 0
}
```

端点完整表见 README。409 表示状态、tick、authority、schema 或 fingerprint 冲突；404 表示未知
session/child。客户端应先刷新 observation/status，而不是盲目重试并修改同一个 operation ID。

## 13. 事件、任务和评分

事件类型包括 spawn/despawn、weather、zone activation、jamming、component suppression、message、
mission marker 和 apply effect。事件由 trigger、priority、dependency 决定稳定执行顺序，并写入 typed
receipt/checkpoint。

任务条件支持：all/any/not/count/zone/state/survival/time/event/wave/contact/communication/resource/
score。Selector 可按 faction、tag、platform、domain、entity ID、capability 动态选择，并正确处理 scheduled、
active、destroyed、despawned。

评分必须区分 N/A 和 0；支持 sum/mean/min/max/count、maximize/minimize、competition score 和 training
reward。事件/插件动态得分必须绑定 Resolved policy 和权威输入 receipt；不能由智能体直接提交任意分数。

## 14. Checkpoint、回放和确定性

Checkpoint 包含 Resolved/Catalog/Registry hash、seed、tick、World/Combat/Mission/Scoring/Session queue、
RNG、adapter/plugin state 和 receipts。恢复时必须传 expected hash 和原始锚；只重算外层 hash 不能绕过
内层语义校验。

确定性要求：

- 同 Resolved + seed + ActionBatch 序列产生相同 semantic state；
- 字典/实体注册/并发提交顺序不影响结果；
- command/action ID、operation ID、provider receipt 不跨 session 复用；
- checkpoint 后 N+M 与不中断 N+M 等价；
- replay 是证据读取路径，不是新的 World writer。

## 15. 新场景开发流程

1. 明确任务域、阵营、实体、单位、终局和评分，不从既有场景复制名称特判。
2. 复用 Catalog 资源；缺资源时先新增 data-only resource 和受信模型工厂。
3. 从 `gs_001`/`gs_002`/`gs_003`/`gs_004` 选择最接近的模板。
4. `ScenarioPackageV2.from_directory` 做安全解析。
5. 使用冻结 Registry/Catalog 编译；保存 `resolved.to_json()` 和 hash。
6. 用真实 World/Session 运行 0/1/10/100 实体和边界输入。
7. 添加 contract、integration、determinism、security 测试；故障注入验证全事务 rollback。
8. 验证 Python/Gym/REST/Visualization/Replay 在同 tick 下语义一致。
9. 跑 Ruff、strict mypy、Bandit、pytest 和覆盖率；性能场景再跑 T5。

禁止做法：修改 Legacy 主路径承载新通用算法；在 runtime 根据 scenario_id/阵营颜色分支；YAML 中
执行代码；直接更新 health；为了过测添加场景名特判；用 skip/xfail 隐藏 RED。

## 16. 智能体开发流程

### 16.1 直接运行 MD-AD-002 的双方规则智能体

```bash
.venv/bin/python examples/md_ad_002_sdk_policy.py \
  --scenario MD-AD-002-HARD --seed 73 --ticks 300
```

入侵方和防守方的参数位于各包 `agents.yaml`：

```yaml
schema_version: rule-agent-team@2.0
objective_m: [0.0, 0.0]
decision_interval_ticks: 5
attack:
  faction_id: coalition.intruder
  pattern: multi_axis_serpentine
  speed_mps: 45.0
  split_angle_deg: 32.0
  serpentine_angle_deg: 18.0
  serpentine_period_ticks: 24
defence:
  faction_id: coalition.defender
  intercept_speed_mps: 40.0
  contact_confidence: 0.68
  maximum_contact_age_ticks: 6
  weapon_policies:
    - selector_tags: [interceptor]
      weapon_ref: weapon.interceptor-missile@2.0.0
      minimum_range_m: 500.0
      maximum_range_m: 8000.0
      cooldown_ticks: 5
```

EASY/MEDIUM/HARD 分别使用 `direct`、`split_evasion`、`multi_axis_serpentine`；通用
`FormalRuleAgentTeamV2` 不包含这三个场景 ID 的运行分支。它每次只做三件事：

1. 读取两个 faction 的公开 `ObservationV2`；
2. 用 World 签发的单实体 authority token 提交 `ActionBatchV2`；
3. 由 Session 唯一 writer 执行动力学和 Combat。

在新场景中复用它时，复制 `agents.yaml`，修改 faction、objective、selector tags、
weapon exact ref 和策略参数。如果需要全新策略，实现新的 observation→ActionBatch
决策函数，但保留 Session 提交边界。

### 16.2 自己实现智能体时的步骤

1. 定义只依赖 `ObservationV2` 的纯 decision 函数。
2. 把 contact、entity、capability 缺失视为正常输入，不读取私有真值。
3. 每个决策 tick 生成全新的 batch/child/operation ID，并设置合理 TTL。
4. 先处理 submit receipt，再由唯一 writer step；读取 child status 和 apply receipt。
5. 对 409/tick conflict 重新观察；不要改变同 operation ID 的 payload。
6. 用 checkpoint/replay 验证相同 seed 和动作序列。
7. 多 session 并发时，policy memory 按 session ID 隔离。

推荐接口：

```python
from typing import Protocol
from openmdbench.schemas.core_v2 import ObservationV2
from openmdbench.schemas.interface_v2 import ActionBatchV2


class AgentV2(Protocol):
    def act(self, observation: ObservationV2) -> ActionBatchV2 | None: ...
```

## 17. 测试清单

场景：

- package directory/archive 安全边界；rename logical equivalence；exact refs；完整 dependency closure；
- entity/formation ID、controller slot、单位、坐标、区域、event DAG；
- mission terminal priority/tie/latch；mixed scoring；checkpoint inner+outer rehash 攻击；
- 0/1/10/100 实体、不同声明顺序和同 seed 复现。

智能体：

- observation 无真值泄漏；batch partial invalid 原子拒绝；stale/future tick；authority/ownership；
- persistent replacement/expiry/fallback；discrete exactly-once；重复 request 幂等、不同 fingerprint 冲突；
- submit 与 pause/stop/close 并发线性化；多 session 隔离；checkpoint N+M；
- unsupported action submit fail-closed，不能产生 ACTIVE/EXECUTED 假回执。

常用命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/contract
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/integration
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/determinism
.venv/bin/ruff check openmdbench tests
.venv/bin/mypy --strict openmdbench
.venv/bin/bandit -q -r openmdbench -lll -ii
```

## 18. 常见问题

### package/compile 失败

按稳定 error code/path 修复最早错误。常见原因：资源未使用精确版本、Registry 未冻结、dependency
缺失/成环、单位不兼容、formation ID 冲突、event dependency 不存在。

### submit 成功但实体没动

确认 command status 已从 queued 变为 active、Session 是 running、调用了 step、实体有可执行 native
dynamics，并且 payload 使用 `speed_mps/heading_deg/altitude_m|depth_m`。

### 开火被拒

检查当前 contact 是否存在且未过期、authority/ROE、target domain、weapon/ammunition/effect/damage 闭包、
ammo/energy/cooldown、实体 lifecycle 和 expected tick。

### Unsupported action

这是预期 fail-closed。查询 `persistent_action_contract_v2(kind)` 或
`discrete_action_contract_v2(kind)` 的 `dispatch_available`，不要绕过 Session 直接写 World。

### 结果不复现

比较 resolved/catalog/registry/map hash、seed、checkpoint hash、动作及 operation ID 序列；确认没有使用
墙钟时间、全局 random、跨 session mutable adapter 或 referee 信息。

### 无头环境不显示窗口

使用 replay `--headless --output` 或设置 Agg backend；不要在服务器上依赖 `plt.show()`。

## 19. 进一步阅读

- `README.md`
- `docs/OpenMDBench_当前支持实体武器挂载与事件清单.md`
- `docs/OpenMDBench_Platform_Refactor_Service_Requirements.md`
- `docs/OpenMDBench_Platform_Refactor_Implementation_Test_Review_Plan.md`
- `docs/platform-refactor/T5_QUALIFICATION.md`
- `scenarios/synthetic/gs_001`～`gs_004`
- `tests/integration/test_session_action_world_v2.py`
- `tests/integration/test_gateway_equivalence_v2.py`
- `tests/system/test_synthetic_genericity_gate_v2.py`

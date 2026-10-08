# OpenMDBench

OpenMDBench 是面向多域海上任务研究的确定性仿真与基准平台。项目在保留 Sim2Sea/MMG
既有研究实现的同时，提供了新的 schema-v2 通用链路：

```text
data-only ScenarioPackage
  -> CatalogV2 + ModelRegistryV2
  -> ScenarioCompilerV2 / ResolvedScenarioV2
  -> WorldFactoryV2
  -> SessionLifecycleV2（唯一写入者）
  -> Python / Gymnasium / REST / Vector / Replay / Visualization
```

核心原则是：场景只声明数据，算法通过受信 ModelRegistry 插件进入；运行时状态只归 Session/World
所有；智能体只能读取按阵营过滤的 Observation，并提交带 tick、权限和幂等锚的 ActionBatch。

> 项目版本为 `0.1.0`，开发状态为 Pre-Alpha。Python 3.11/3.12、Ubuntu 22.04/24.04
> 是当前支持环境。`env/`、`model/`、`framework/` 是 Legacy 实现源；新接入优先使用
> `openmdbench.*` 的 V2 API。

## 已支持内容

- 正式任务：`MD-AD-002-EASY/MEDIUM/HARD` 已提供三个独立、可直接编译的
  V2 data-only 包（`scenarios/formal/`）及共享版本化 Catalog。
- 通用性场景：`scenarios/synthetic/gs_001`～`gs_004`，均为可直接加载和编译的
  `package@2.0` data-only 场景包。
- 实体与域：固定岸基设施、UAV、USV、AUV，以及 Catalog 定义的任意平台类型。
- 通用系统：Catalog/Registry、声明式编译、World、地理/边界/碰撞、Combat/Damage、
  Lifecycle、Mission/Scoring、Session/Command、checkpoint/replay、可视化和接口适配。
- 公共入口：结构化 Python、Gymnasium、Vector、REST V2、锁步/连续/回放 Runner。
- 当前 V2 可执行动作：`navigation`、`hold`、`fire_weapon`、`send_message`。
  其他已定义动作会在 submit 边界稳定拒绝，不会伪造执行回执。

完整实体、武器、挂载、事件和动作状态见
[当前支持实体武器挂载与事件清单](docs/OpenMDBench_当前支持实体武器挂载与事件清单.md)。

## 安装

```bash
git clone <repository-url>
cd source_codes
make setup PYTHON=python3.11
source .venv/bin/activate
python -c "import openmdbench; print(openmdbench.__version__)"
```

`make setup` 安装 `core,dev`。按用途增加依赖：

```bash
.venv/bin/python -m pip install -e ".[train]"   # PyTorch/W&B 等
.venv/bin/python -m pip install -e ".[server]"  # FastAPI/Uvicorn
.venv/bin/python -m pip install -e ".[cuda]"    # 显式声明可选加速；CPU 仍是基线
```

Ubuntu 系统依赖和 CPU-only PyTorch 安装方法见
[Ubuntu installation](docs/ubuntu_installation.md)。

## 五分钟运行

运行正式自测试：

```bash
make selftest
make md-ad-002-selftest
```

运行交互/无头任务：

```bash
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m openmdbench.cli live \
  --scenario MD-AD-002-MEDIUM --seed 73 --speed 10 --view referee \
  --replay-output artifacts/md-ad-002-medium-v2.jsonl

# 回放直接消费实时运行保存的同一批 VisualizationFrameV2；不重建 World/Session
MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m openmdbench.cli replay-v2 \
  artifacts/md-ad-002-medium-v2.jsonl --speed 20

.venv/bin/python -m openmdbench.cli run \
  --scenario MD-AD-002-EASY --seed 7 --ticks 60

# V2 对抗规则智能体：突防、拦截、航迹制导射击均经公开 ActionBatch
.venv/bin/python examples/md_ad_002_sdk_policy.py \
  --scenario MD-AD-002-HARD --seed 7 --ticks 60
```

MD-AD-002 三种难度的 V2 实时窗口均由 Catalog/ScenarioPackage 驱动，包含威海海岸线与陆地、
任务/生成区域、Catalog 原始 UAV/USV/岸基矢量外形、实体轨迹、能量/续航/通信/传感器/健康
徽标、传感器和武器覆盖、权威目标跟踪线、通信路由与打击效果、波次进度、环境、任务与评分。
实时与推演后回放共用不可变 `VisualizationFrameV2` 和同一个 retained renderer；回放读取器不导入
Session、World 或动力学模块，也不会推进 RNG。

三个包各自包含 data-only `agents.yaml`：EASY 为直线突防，MEDIUM 为分轴规避，HARD 为多轴蛇形；
防守方共用公开观测驱动的前出拦截策略。`fire_weapon` 使用 opaque `contact_id`，由 Session 在权威
接触存储中解析并复验目标、ROE、射程、弹药和 cooldown，规则智能体不读取目标真值或 World 私有状态。

运行质量门禁：

```bash
make lint
make typecheck
make security-check
make test
```

## 创建 V2 data-only 场景

最小空场景可由 SDK 生成：

```python
from pathlib import Path
from openmdbench.scenarios.sdk_v2 import ScenarioSdkV2

root = Path("scenarios/local/my_first_scenario")
ScenarioSdkV2.create(root, name="example.harbor-patrol")
package = ScenarioSdkV2.validate(root)
print(package.logical_hash)
```

完整场景必须使用精确 `id@semver` 资源引用，并由与之匹配的 `CatalogV2` 和冻结的
`ModelRegistryV2` 编译。不要从测试 fixture 或 Legacy 全局表回读资源。可复制
`scenarios/synthetic/gs_001` 作为纯场景模板，复制 `gs_003` 学习武器/弹药/effect/damage
闭包，复制 `gs_004` 学习事件、任务和评分。

```python
from pathlib import Path
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2

package = ScenarioPackageV2.from_directory(Path("scenarios/local/my_scenario"))
resolved = ScenarioCompilerV2(catalog=my_catalog).compile(package)
resolved.validate_integrity()
print(resolved.resolved_hash)
```

`my_catalog` 必须由应用装配层显式提供；平台故意不提供“扫描目录并信任所有 Python”的入口。

## 智能体动作最小示例

```python
from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2

tick = observation.tick
command = PersistentCommandV2(
    schema_version="2.0",
    command_id="cmd.nav.0001",
    command_type="navigation",
    entity_id="asset.uav.001",
    faction_id=observation.observer_faction_id,
    based_on_tick=tick,
    valid_until_tick=tick + 10,
    payload={"speed_mps": 35.0, "heading_deg": 90.0, "altitude_m": 1200.0},
)
batch = ActionBatchV2(
    schema_version="2.0",
    session_id=observation.session_id,
    batch_id="batch.0001",
    idempotency_key="decision.0001",
    faction_id=observation.observer_faction_id,
    based_on_tick=tick,
    valid_until_tick=tick + 10,
    persistent_commands=(command,),
)

receipt = adapter.submit(
    batch,
    authority_token=authority_token,
    operation_id="agent.submit.0001",
)
tick_receipt = adapter.step(operation_id="agent.tick.0001")
```

智能体不得保存或修改 `WorldStateV2`，不得根据 referee/敌方真值决策，也不得复用旧 tick
或跨 session 的 command/action ID。详细接入、REST 请求、Runner、回放和测试方法见
[用户操作手册与场景智能体开发指南](docs/OpenMDBench_用户操作手册与场景智能体开发指南.md)。

## REST V2

应用通过 `create_gateway_app_v2(AgentGatewayV2(...))` 注入 session/restore factory。主要端点：

```text
POST   /v2/sessions
POST   /v2/sessions/restore
POST   /v2/sessions/{id}/control
GET    /v2/sessions/{id}/observation?faction_id=...
POST   /v2/sessions/{id}/actions
POST   /v2/sessions/{id}/step
GET    /v2/sessions/{id}/commands/{child_id}
GET    /v2/sessions/{id}/events
GET    /v2/sessions/{id}/result
GET    /v2/sessions/{id}/visualization?faction_id=...
GET    /v2/sessions/{id}/replay?faction_id=...
GET    /v2/sessions/{id}/checkpoint
DELETE /v2/sessions/{id}
```

## 文档索引

- [用户操作手册与场景智能体开发指南](docs/OpenMDBench_用户操作手册与场景智能体开发指南.md)
- [当前支持实体武器挂载与事件清单](docs/OpenMDBench_当前支持实体武器挂载与事件清单.md)
- [平台重构需求](docs/OpenMDBench_Platform_Refactor_Service_Requirements.md)
- [实施、测试与审查计划](docs/OpenMDBench_Platform_Refactor_Implementation_Test_Review_Plan.md)
- [T5 资源长稳验收说明](docs/platform-refactor/T5_QUALIFICATION.md)
- [Ubuntu 安装说明](docs/ubuntu_installation.md)
- [变更记录](CHANGELOG.md)

新场景、智能体、REST、训练、实时可视化、日志和回放均以第一份 V2 用户手册为准；
已删除重复或与 V2 公共契约冲突的 1.0/旧场景开发文档。

## 开发状态说明

当前测试、功能和正式 T5 长稳已通过，但发布审计仍记录覆盖率细分、历史全仓格式漂移和独立审计
门禁。请以 `reports/platform-refactor/rf_14.md`、`rf_15.md` 为发布状态依据，不要仅凭一个场景
成功运行宣称整个平台已发布。

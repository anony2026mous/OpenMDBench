# RF-04 补充报告：SURFACE-MMG-V2-001

## 结论

- 状态：DONE（限定于本任务的水面实体 MMG 接线；不代表全平台发布完成）。
- 需求关联：RF-02 Catalog/Registry、RF-04 World/实体工厂与原生状态、RF-05 海陆边界、RF-08 公开导航动作、RF-11 checkpoint。
- 代码审查：P0=0，P1=0；实现、测试和静态检查均通过。

## 范围与设计

- 将 `dynamics.picket-usv@2.0.0` 从 UAV 运动学资源迁移到版本化
  `models.native-sim2sea-mmg@2.0.0`；模型参数、执行子步和控制器限制均由 Catalog 声明。
- 增加每实体一个 spawn-process 的 Sim2Sea/Taichi MMG worker。父进程只保存可序列化协议，
  worker 负责真实 `kvlcc2_l7` / RK 求解器状态；worker artifact 的真实源码 hash 被 Registry、
  World materialize 与 checkpoint identity 共同锚定。
- 公开接口仍为 speed/heading navigation；通用 surface controller 将其映射为受限的 nps/rudder，
  agent 和场景不接触 MMG 原始执行器字段。
- checkpoint 保存 worker 状态和 solver identity；恢复后下一步与连续执行的输出一致。
- MotionCandidate 显式保留动力学输出的航向；World 只在没有模型航向时从地速计算航向。边界或碰撞
  改写 MMG 候选位置/速度后，World 将裁决后的权威状态回灌到 worker，避免下一 tick 将合法裁决误判为
  外部篡改。
- 海陆部署和跨岸裁决继续复用通用 BoundarySystem；水面实体被禁止部署/越过陆地，航空实体可按自身
  边界策略跨越陆地。未增加场景 ID、阵营或固定实体分支。

## 主要修改

- `catalog/v2/md_ad_002.yaml`
- `openmdbench/dynamics/sim2sea_mmg_worker.py`
- `openmdbench/dynamics/native_v2.py`
- `openmdbench/domains/surface/controller_v2.py`
- `openmdbench/sessions/lifecycle_v2.py`
- `openmdbench/world/factory_v2.py`
- `openmdbench/catalog/__init__.py`
- 对应 MMG 契约、确定性、集成、正式场景与地形测试。

## 测试证据

- `pytest tests/contract/test_native_dynamics_adapter_v2.py -q`：46 passed。
- `pytest tests/unit/test_mmg_navigation_controller_v2.py tests/unit/test_mmg_adapter.py tests/determinism/test_native_dynamics_isolation_v2.py tests/integration/test_native_mmg_adapter_v2.py -q`：41 passed。
- `pytest tests/system/test_md_ad_002_v2_migration.py -k 'not native_v2_gateway and not surface_picket' -q`：9 passed，4 deselected。
- `pytest tests/system/test_md_ad_002_v2_migration.py::test_surface_picket_uses_isolated_mmg_through_public_navigation tests/system/test_map_terrain_v2.py -q`：5 passed。
- `test_native_v2_gateway_builds_steps_checkpoints_and_restores` 对 Easy、Medium、Hard 分别通过（各 1 passed）。
- 真实 live 风格的无界面 3 tick 连续运行通过；该用例在修复前会以
  `dynamics.state_authority_conflict` 失败。
- Ruff check、strict mypy（6 个生产模块）和 `git diff --check` 通过。

## 兼容、确定性与遗留风险

- 三个 MD-AD-002 难度场景共同引用同一版本化 picket-usv dynamics 资源，无场景专用代码迁移。
- worker 一实体一进程，避免 Taichi/Sim2Sea 可变状态跨会话共享；恢复续推由契约测试验证。
- Taichi 离线缓存仅缓存编译内核，不缓存仿真状态；它减少 worker 重建时间，不改变 seed 或物理状态。
- `kvlcc2_l7` 当前作为可执行 MMG 代理船型。其长度/宽度与正式场景 visual/collision 外形的物理标定仍为
  UNVALIDATED，需后续以经验证的本船参数集替换或标定；本任务未声称保真度完成。
- 本任务为 T3 定向验证；未执行全仓覆盖率、性能/压力、全量 pytest 或独立发布审计。

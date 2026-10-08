# RF-07 阶段报告：配置驱动的通用内核接线

## 本阶段需求编号

- 固定 tick 流水线第 1～19 项的既有内核复用要求。
- RF-07：ResolvedScenario、SessionRuntime、Session 和 Runner 正式纵向切片。

## 修改文件

- `openmdbench/core/session_runtime.py`：解析能力选择及旧内核的唯一 adapter。
- `openmdbench/sessions/session.py`：默认 kernel 改为 SessionRuntime。
- `openmdbench/envs/benchmark.py`：构造/reset 持续消费同一 ResolvedScenario。
- `tests/integration/test_session_runtime_rf07.py`：正式 E2 和能力选择测试。

## 设计选择和 ADR

- 不建立第二套 `WorldState`、动力学或裁决主循环；SessionRuntime 每 tick 委托既有
  `OpenMDBenchEnv.step/step_bilateral`。
- 根据 resolved component key 选择能力，不根据具体场景 ID 选择核心行为。
- 既有 UAV、Sim2Sea MMG、固定设施、传感器、通信、combat、同时毁伤、mission 和 scoring
  保持唯一权威实现。
- 旧环境继续作为兼容 adapter；正式会话入口不重新读取 YAML。

## 新增/修改测试

- MD-INT-001 完整运行：`ResolvedScenario → SimulationSession → LockstepRunner →
  SessionRuntime → OpenMDBenchEnv`。
- seed 73 在原 E2 基线第 170 tick 得到 `blue_success`。
- 运行中禁止调用 ScenarioCompiler，证明不回退到原始配置入口。
- 验证 `step_uav`、`sim2sea_mmg`、`fixed_shore` 三类动力学 adapter 调用证据。
- 修改外层 scenario ID 但保留 resolved capability，仍使用同一正式内核能力。
- 复跑注册顺序、RNG、combat、同时毁伤、裁决和旧基线回归。

## 实际命令和结果

- RF-07 新增集成测试：2 项通过。
- RF-05～RF-07 受影响回归：145 项通过，用时 94.53 秒。
- Ruff、mypy strict（262 个源文件）、Bandit：通过。
- `make full-test`：495 项通过、93 个既有 warning，用时 2409.21 秒。

## 覆盖率与性能

- 全仓覆盖率 90.63%，通过 80% 门槛。
- 全部既有性能、soak smoke 和正式系统长局通过；未复制循环，未发现逻辑性能回归。

## 兼容影响

- MD-INT-001、MD-AD-002 EASY/MEDIUM/HARD、Gym、REST、CLI、回放和可视化全仓回归通过。
- 旧场景 ID adapter 保留在兼容边界，核心 SessionRuntime 不依赖具体 ID。

## 未完成、风险和下一依赖

- 全量场景能力插件化和清除 CLI/展示层 ID 分派属于后续兼容清理，不影响 RF-07 核心门禁。
- VisualizationFrame/live/replay 统一进入 RF-08；REST 新会话纵向切片进入 RF-09。
- RF-07 完成门禁通过。

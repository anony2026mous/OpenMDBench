# PERF-00 修复后 MMG 性能基线记录

```text
TASK_ID: PERF-00
STATUS: DONE
OBJECTIVE: 在 BUG-04 correctness gate 通过后，固定场景/seed/运行开关，测量当前每 tick
  MMG step/snapshot RPC 数、RPC 时延、motion provider 与完整 tick 时间；不修改实现。
REQ_IDS: PERF-MMG-001; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - BUG-04 DONE：三档 MD-AD-002/seed 73/1800 CLI 与 T3 指定回归通过。
  - 本阶段仅重新建立优化前基线，不能借性能测量更改物理、substeps、快照或场景。
ALLOWED_READ:
  - MMG adapter/worker/RPC、formal session/scenario、现有性能工具、环境/version/CPU 信息与报告。
ALLOWED_WRITE:
  - reports/repair/PERF-00_baseline.md
  - /tmp/openmdbench-perf-* 临时 profiler/measurement 文件
PROHIBITED:
  - 修改生产源码、测试、RPC、快照策略、dt/substeps/积分器、场景/Catalog/依赖；
    T4/T5、16/32 并发、压力/soak、提交/推送/PR。
TEST_LEVEL: T3
ALLOWED_COMMANDS:
  - rg/sed/read-only inspect；.venv/bin/python 运行单进程、固定 seed 的有界测量；
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 的直接性能/adapter smoke（如存在）。
PER_COMMAND_TIMEOUT: 10 min
TOTAL_TIME_BUDGET: 20 min
ACCEPTANCE:
  - 记录 commit、Python/Taichi/MMG、OS/CPU、scenario/catalog hash、seed、实体和 active MMG 数、
    dt/substeps、log/viz/checkpoint/profiling 开关、warmup/sample/repeat。
  - 报告 mean/P50/P95/P99 tick，step/snapshot RPC per tick，send/poll/recv、motion/total 时间，
    父/worker CPU/内存（若当前安全工具可用）；不做跨机器虚拟化因果结论。
OUTPUTS:
  - 可复现的单进程基线与 PERF-01 的 RPC schema/测试准入结论。
STOP_CONDITIONS:
  - 若无法分离 MMG time/RPC count，或基线测量需要改变快照/物理/场景：BLOCKED，
    不得直接开始 PERF-01 实现。
```

## 实际路径核验

- `openmdbench/dynamics/native_v2.py::_step_mmg` 在父进程按 `substeps` 循环，逐次调用
  `SpawnedSim2SeaMMGCoreV2.step(...)`。
- `openmdbench/dynamics/sim2sea_mmg_worker.py` 的现行 `step` RPC 一次只做一个 RK4 子步；
  worker 使用一条共享 Pipe、一个 spawn 进程和按 handle 隔离的 engine。
- `openmdbench/world/factory_v2.py::_invoke_motion_provider` 在每个 dynamics adapter step 前后调用
  `snapshot()`，MMG adapter 的 snapshot 各产生一个额外 RPC。
- 因此，在本样本的两个活动 MMG 实体、每实体 10 个子步下，理论值为每 tick 20 次 step
  RPC 与 4 次 snapshot RPC；实测计数与此一致。

## 固定测量配置

| 项目 | 值 |
|---|---|
| commit | `4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e` |
| 场景 / seed | `MD-AD-002-HARD` / `73` |
| Resolved / Catalog hash | `sha256:e76f945b5df6efeba5ed5eaa1d3070b4703e667ee4ed4464d0b198c3e7042d2e` / `sha256:85f5845a22242f5be5268f3d8289310ac99d781acbef9caa999ea770ef920ffb` |
| Python / Taichi / MMG | Python `3.11.15` / Taichi `1.7.4` / `sim2sea-mmg:kvlcc2-l7:rk4:worker-v2` |
| 系统 / CPU / 内存 | Ubuntu Linux `6.8.0-136-generic`，Intel i7-10875H（16 logical CPUs），38 GiB RAM；native Linux，不是 WSL2 |
| world | 11 个实体；活动 MMG 恒为 2：`defender.picket-001`、`defender.picket-002` |
| 物理 | `physics_dt=1.0 s`；每 MMG `substeps=10`，`integration_dt=0.1 s`；RK4、float32 和控制保持未改 |
| 开关 | GUI、日志、磁盘 checkpoint 均关闭；仅在 140 tick 末尾显式生成一次 checkpoint；运行时 parent-side profiler 开启 |
| 预热 / 采样 / 重复 | 20 tick 预热、120 tick 稳态采样、2 次无 connection wrapper 重复；第 3 次仅用于 send/poll/recv 拆分 |

测量命令（临时脚本仅在 `/tmp`，未写入仓库）：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-perf00-mpl \
  .venv/bin/python /tmp/openmdbench_perf00_probe.py
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 仅隔离宿主 ROS pytest 自动插件（缺少 `lark`），不跳过本测量的
任何执行路径。

## 稳态基线（无 connection wrapper 的两次重复）

| 指标（ms） | Run 1 | Run 2 | 结论 |
|---|---:|---:|---|
| 完整 `session.step` mean / P50 / P95 / P99 | 43.24 / 43.07 / 46.35 / 46.95 | 43.32 / 43.27 / 46.39 / 47.82 | 稳定，均值 43.28 |
| motion provider mean / P50 / P95 / P99 | 25.66 / 25.58 / 26.67 / 27.07 | 25.78 / 25.55 / 26.80 / 28.14 | 稳定，均值 25.72 |
| 每个 MMG adapter `_step_mmg` mean | 7.86 | 7.91 | 两实体合计约 15.77/tick |
| step RPC | 20.0/tick | 20.0/tick | 2 entity × 10 substeps |
| snapshot RPC | 4.0/tick | 4.0/tick | 每实体 step 前后各一次 |

末尾显式 checkpoint 的单次耗时约 3.60 s；它不在逐 tick 计时路径中，但说明完整历史
checkpoint 的成本应在 PERF-04 单独决策，不能在本阶段删除或弱化。

## RPC 细分（第 3 次，120 tick，额外计时 wrapper）

该次完整 `session.step` mean 为 44.77 ms（wrapper 本身有轻微观测开销），因此只用于分项归因，
不替代上述基线均值。

| 单次 parent-side RPC 分项 | count | mean (ms) | P50 | P95 | P99 |
|---|---:|---:|---:|---:|---:|
| `send` | 2,880 | 0.017 | 0.015 | 0.026 | 0.033 |
| `poll` | 2,880 | 0.649 | 0.678 | 1.100 | 1.335 |
| `recv` | 2,880 | 0.014 | 0.012 | 0.019 | 0.024 |
| worker `step` round-trip | 2,400 | 0.804 | 0.734 | 1.174 | 1.395 |
| worker `snapshot` round-trip | 480 | 0.104 | 0.078 | 0.200 | 0.225 |

`poll` 是每次同步 RPC 的主要等待段；20 次子步 IPC/每 tick 直接放大该等待。没有对 WSL2 或
虚拟化固定倍率作因果推断。

## 资源快照与限制

- 采样末尾父进程：max RSS 约 249 MiB；累计 user/system CPU 约 12.34/0.23 s。
- worker 进程：RSS/HWM 约 184 MiB；累计 user/system CPU 约 6.02/2.23 s。
- 这是单次受控进程终点快照，不是并发或长稳内存趋势；T5 未获授权，未执行。
- T4（全量 lint/mypy/pytest/coverage）和 T5（并发、压力、soak、跨环境性能）均未执行。

## 阶段结果与下一阶段准入

- 修改文件：无生产源码、无测试、无场景/Catalog/依赖修改；仅本阶段记录和 `/tmp` 探针。
- 测试：定向 T3 单进程测量成功（3 次 probe，退出码均为 0）；pytest 用例 0 个，跳过 0 个。
- 风险：采样窗口在 tick 20--140，尚未覆盖长局毁伤后的负载变化；但它已覆盖两个实际 MMG
  实体的稳定运行和现行完整 action/world 路径。
- 准入：**PASS**。已量化并分离 step/snapshot/RPC/motion provider，满足 PERF-01 契约与故障
  测试先行的前置条件。下一阶段只能新增批量子步契约与红灯测试，暂不改 worker 实现。

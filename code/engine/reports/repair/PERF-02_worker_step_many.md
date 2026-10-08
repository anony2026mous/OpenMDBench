# PERF-02 Worker-side `step_many` 实现记录

```text
TASK_ID: PERF-02
STATUS: DONE
OBJECTIVE: 将每个 MMG entity 每个 public tick 的 N 次同步 step RPC 合并为一次 worker-side
  batch RPC，同时保持旧子步积分、输入、状态、失败和 checkpoint 语义。
REQ_IDS: PERF-MMG-001; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
TEST_LEVEL: T2
```

## 实现范围

- `openmdbench/dynamics/sim2sea_mmg_worker.py`
  - 新增 `MMG_BATCH_MAX_SUBSTEPS_V2 = 256` 和严格 `substeps` 校验。
  - 新增 worker engine / Pipe operation / parent handle 三层 `step_many`；legacy `step` 未删除。
  - `step_many` 按原顺序调用同一个 `step` N 次，返回最后一个 six-value state，因此不改 RK4、
    float32、坐标、角度、控制输入或每子步重建方式。
  - 请求开始时保存 canonical engine snapshot；任一子步异常时恢复后再失败返回。
  - 修复 `set_state` 后、首次积分前的合法 pending-initialization snapshot restore：它可没有
    `integration_dt_s`，但仍须保留完整 position/heading/body velocity。这是 P01-04 原子回滚测试
    直接暴露的状态表示缺口，不是快照裁剪。
- `openmdbench/dynamics/native_v2.py`
  - `_MMGCoreV2` 增加 batch protocol；`NativeDynamicsAdapterV2._step_mmg` 从父进程 N 次
    `_native_core.step` 改为一次 `_native_core.step_many(..., substeps=N)`。
  - 缺少 batch protocol 的 core 以稳定 `dynamics.native_core_invalid` 失败，避免静默退回 N 次 RPC。
- `tests/contract/test_native_dynamics_adapter_v2.py`、
  `tests/determinism/test_native_dynamics_isolation_v2.py`
  - 测试用 fake core 显式实现同一 batch protocol；保留原逐次调用记录以验证控制与顺序。
- `tests/contract/test_mmg_step_many_contract_v2.py`
  - PERF-01 的 11 个红灯断言转绿。

未修改场景、Catalog、装备/毁伤、physics dt、子步数、积分器、快照调用频率、worker 数量、并发模型、
日志或公开 schema。

## 测试

```bash
.venv/bin/python -m compileall -q \
  openmdbench/dynamics/native_v2.py \
  openmdbench/dynamics/sim2sea_mmg_worker.py \
  tests/contract/test_mmg_step_many_contract_v2.py \
  tests/contract/test_native_dynamics_adapter_v2.py \
  tests/determinism/test_native_dynamics_isolation_v2.py
# exit 0

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-perf02b-mpl \
  .venv/bin/python -m pytest \
    tests/contract/test_mmg_step_many_contract_v2.py \
    tests/contract/test_native_dynamics_adapter_v2.py \
    tests/determinism/test_native_dynamics_isolation_v2.py -q
# 80 passed in 19.46s; exit 0
```

首轮运行得到 `79 passed, 1 failed`：P01-04 在第三子步异常后试图 restore 一个已 set_state、但
尚未有 dt 的 engine snapshot，旧 restore 错误拒绝其 `integration_dt_s=None`。修复后同一命令
`80 passed`；没有忽略、删改或放宽该断言。

REVIEW-01 反馈补强：fake core 记录 `batch_calls`，并断言 adapter 对两个子步只调用一次
`step_many(..., substeps=2)`；这防止未来的父进程循环实现因 fake 内部循环而误通过。补强后同一
T2 命令再次 `80 passed in 19.50s`。

## 风险与 PERF-03 准入

- worker 的 batch rollback 恢复的是 canonical engine state；下一次真实 `step` 一如原来从该状态
  重建 Taichi core。P01-04、P01-05 和真实 worker comparison 覆盖了此基础，但完整场景逐 tick
  等价性仍需 PERF-03。
- 旧 `step` 保留意味着低层协议向后兼容；正式 adapter 已没有合法 fallback，因此性能门禁不会被
  意外绕开。
- 准入：**PASS**。下一阶段 PERF-03 必须验证场景确定性、checkpoint/replay 语义和 RPC 数量，
  再重测与 PERF-00 相同配置的性能。T4/T5 仍未获授权、不会执行。

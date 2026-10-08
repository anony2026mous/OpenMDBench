# PERF-03 确定性与性能复测记录

```text
TASK_ID: PERF-03
STATUS: NEEDS_DECISION
OBJECTIVE: 对比 legacy per-substep RPC 与 step_many 的固定 seed/action 序列等价性，
  再以 PERF-00 同一困难场景配置测量优化收益。
REQ_IDS: PERF-MMG-001; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - PERF-02 T2 通过：80 passed；无场景/物理/快照策略改动。
PROHIBITED:
  - T4/T5、并发、压力、GUI、修改场景与参数、删减 tick/子步、快照优化。
TEST_LEVEL: T3
```

## 等价性结果

两个独立 Python 进程分别运行 600 个相同的 `MD-AD-002-HARD` formal tick（seed `73`、相同
session ID、相同 rule team 和 operation ID）：

- legacy 对照仅在运行时将 parent-side `step_many` 投影为原先的 N 次 `step`，未修改文件或 Worker；
- batch 对照使用实际 `step_many`；
- `600/600` 个 Action/World receipt canonical hash 完全相等；
- `resolved_hash`、World checkpoint hash、Session checkpoint hash 均完全相等；
- 本次等价 checkpoint hash：`sha256:c7e3bca7ae0c5eae7fac12d8c4dba4e703f724e8c287ff7eda1debb4b15a1aba`。

这证明 worker 内单次初始化、顺序 N 次 `core_step` 与原先每子步 Pipe 往返、重初始化的权威状态和
账本结果严格等价。P01-04 另证明任一中间子步失败会恢复本请求前 engine state。

## 场景与接口回归

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-perf03-regression-mpl \
  .venv/bin/python -m pytest \
  tests/contract/test_md_ad_002_gym.py \
  tests/system/test_md_ad_002_rest.py \
  tests/integration/test_gateway_equivalence_v2.py \
  tests/determinism/test_md_ad_002_easy_checkpoint.py \
  tests/system/test_md_ad_002_v2_visualization.py \
  tests/system/test_md_ad_002_v2_rule_agents.py \
  tests/system/test_md_ad_002_v2_migration.py \
  tests/contract/test_md_int_003_damage_lifecycle.py \
  tests/contract/test_md_int_003_surface_combat.py \
  tests/system/test_md_int_003_scenarios.py \
  tests/integration/test_md_int_003_interfaces.py \
  tests/system/test_md_int_003_visualization.py \
  tests/determinism/test_md_int_003_system_determinism.py -q
# 81 passed, 1 warning, 301.42s; exit 0

MPLCONFIGDIR=/tmp/openmdbench-perf03-cli-mpl \
  .venv/bin/python -m openmdbench.cli run --scenario MD-AD-002-HARD --seed 73 --ticks 1800
# exit 0
```

1800 tick CLI：resolved `md-ad-002.hard.v2`，终局仍为 `intruder_success` at tick `547`，最终仍推进至
tick `1800`；checkpoint `sha256:d9a148b1ee9931e3cd01e169313e48a9c39739b0a0901e1e52739038ce62d0f8`。
唯一 warning 是 Taichi 对 Python 3.15 `locale.getdefaultlocale` 的第三方弃用提醒，不是测试失败。

## 性能复测

PERF-00 的完全相同配置（HARD/73、20 warmup + 120 sample、2 active MMG、无 GUI/日志/磁盘
checkpoint、末尾一次显式 checkpoint）重跑两次：

| 指标 | PERF-00（两次均值） | PERF-03 batch（两次均值） | 变化 |
|---|---:|---:|---:|
| 完整 `session.step` mean | 43.28 ms | 37.31 ms | **-13.80%** |
| 完整 tick P50 | 43.17 ms | 37.17 ms | - |
| 完整 tick P95 | 46.37 ms | 40.05 ms | - |
| 完整 tick P99 | 47.39 ms | 41.36 ms | - |
| MMG step RPC | 20.0/tick | **2.0/tick** | -90% |
| MMG snapshot RPC | 4.0/tick | 4.0/tick | 未改变 |
| MMG adapter step mean（单 entity） | 7.89 ms | 约 4.86 ms | 降低 |

优化后两个 run 的 mean 分别为 36.96 ms、37.65 ms；RPC batch mean 约 4.80 ms/实体，snapshot
round-trip 仍约 0.10 ms/次。`≤100 ms/tick` 既有门禁继续满足且有余量。

## 结论与下一阶段准入

- 正确性门禁：**PASS**（低层 legacy 对照、600 tick receipt/checkpoint 等价、81 个指定 T3 回归、
  HARD/73/1800 CLI 均通过）。
- RPC 数量门禁：**PASS**（step RPC = active MMG entities = 2/tick）。
- 相对性能门禁：**FAIL**。13.80% 小于计划要求的 30%；没有通过改变 fidelity、减少 tick/substep、
  减少日志或删除 snapshot 伪造收益。
- 阶段状态：**NEEDS_DECISION**。按计划必须如实保留该状态；可进入 PERF-04 仅作 snapshot
  优化是否另立 PERF-MMG-002 的决策，不能直接实施该专项。
- T4/T5 未获授权，未执行。

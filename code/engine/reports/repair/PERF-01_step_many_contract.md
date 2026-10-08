# PERF-01 Worker-side 批量子步契约与故障测试记录

```text
TASK_ID: PERF-01
STATUS: DONE
OBJECTIVE: 在不修改 MMG worker/adapter 实现前，冻结 step_many RPC 的输入、原子性、等价性、
  checkpoint/restore 与失败行为，并建立当前实现必然失败的定向测试。
REQ_IDS: PERF-MMG-001; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - PERF-00 DONE：困难场景的当前实现为 2 active MMG × 10 substeps = 20 step RPC/tick。
ALLOWED_WRITE:
  - reports/repair/PERF-01_step_many_contract.md
  - tests/contract/test_mmg_step_many_contract_v2.py
PROHIBITED:
  - 生产实现、场景/Catalog、dt/substeps/积分器/精度、快照策略、依赖；T4/T5。
TEST_LEVEL: T2
```

## 待冻结契约

`step_many(nps, rudder_rad, dt_s, substeps)` 是仅限父进程到已隔离 MMG worker 的 RPC：对一个
已初始化 handle 以同一个控制输入、相同 `dt_s` 和严格递增的子步顺序积分 `substeps` 次，仅返回
最后一个 canonical six-value 状态。

1. `substeps` 必须为非 bool 的正整数，且有固定上限；`nps`、`rudder_rad`、`dt_s` 和初始状态继续
   服从原有严格有限数/执行器范围/已 set_state 约束。
2. `substeps=1` 与原 `step` 完全等价；`substeps=N` 与同一 handle 连续 N 次原 `step` 字段严格相等。
3. worker 在任一第 k 子步失败时，向父进程返回失败且恢复该 handle 到本次请求开始前的完整状态；不得
   输出中间状态或推进 RNG。
4. Pipe timeout、断连、closed handle/worker 的错误类别沿用现有 `RuntimeError`/parent-side
   `ValueError` 转译，不悄悄重试或隐藏失败。创建新 handle 后仍应能按已有 worker lifecycle 建立新连接。
5. 多实体批量调用的顺序仍由 World 现有稳定 entity-id 排序决定；`step_many` 不建立跨 handle 的共享
   可变状态。
6. adapter checkpoint 保持完整 worker state；restore 后第一次 `step_many` 必须等价于未中断继续运行。

该契约不更改公开场景、Action、Frame、receipt 或 checkpoint schema；也不删除每 tick 前后 snapshot。

## 红灯测试与现状证据

新增 `tests/contract/test_mmg_step_many_contract_v2.py`，覆盖：

| 用例 | 要求 | 当前实现结果 |
|---|---|---|
| P01-01 | `substeps=1` 与一次 legacy `step` 严格相等 | FAIL（不存在 `step_many`） |
| P01-02 | `substeps=4` 与严格顺序四次 legacy `step` 相等 | FAIL（不存在 `step_many`） |
| P01-03 | bool/0/负数/float/超过 256 的 substeps 稳定拒绝 | FAIL（不存在 `step_many`） |
| P01-04 | 第 3 子步失败后 engine state 完整回滚 | FAIL（不存在 `step_many`） |
| P01-05 | checkpoint/restore 后首个批量步进等价 | FAIL（不存在 `step_many`） |
| P01-06 | closed handle、worker 断连可见失败；新 handle 使用新 worker 恢复 | FAIL（不存在 `step_many`） |

执行命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-perf01-mpl \
  .venv/bin/python -m pytest tests/contract/test_mmg_step_many_contract_v2.py -q
```

结果：退出码 `1`，`10 failed`，`0 passed`，`0 skipped`，耗时 `8.65 s`。所有失败均为预期的
`AttributeError: SpawnedSim2SeaMMGCoreV2/_Sim2SeaMMGWorkerEngine has no attribute step_many`；没有
发现与本契约无关的基线失败。

`P01-06` 的断连用例只终止该测试创建的 spawn worker，随后用新 handle 验证既有 shared-worker
lifecycle 的重建语义；它不影响源码、场景或外部进程。

## 阶段结果与 PERF-02 准入

- 实际修改文件：本报告、`tests/contract/test_mmg_step_many_contract_v2.py`；无生产实现变更。
- 契约决定：上限固定为 `256`；每次 RPC 仅服务一个 handle，调用顺序仍归 World 稳定 ID 排序；
  worker 内在任一子步异常时恢复 pre-request engine snapshot，再向 parent 失败返回。
- Schema 影响：worker 内部协议新增 `step_many` operation；公开 Action/Frame/receipt/checkpoint schema
  不变。现有 legacy `step` 保留供严格等价测试和向后兼容。
- 风险：worker 内恢复依赖每次子步前按 engine state 重初始化同一 Taichi core；PERF-02 必须以真实
  worker 测试和 restore 测试证明这一假设。
- 准入：**PASS**。红灯测试已先行并可复现；PERF-02 只可在 `native_v2.py`、
  `sim2sea_mmg_worker.py` 及直接相关测试中实现该契约，不能修改快照策略或物理参数。

# RF-06 阶段报告：Continuous、Lockstep 与 Replay Runner

## 本阶段需求编号

- RUN-001～RUN-005。
- RF-06：统一 Runner 控制和明确时钟语义。

## 修改文件

- `openmdbench/runners/session.py`：RunnerClock、ContinuousRunner、LockstepRunner。
- `openmdbench/runners/replay.py`：完全只读、无内核依赖的 ReplayRunner。
- `openmdbench/runners/__init__.py`：惰性公共导出，避免 replay 导入仿真模块。
- `tests/unit/runners/test_session_runners_rf06.py`：模式、时钟、暂停和等价性测试。
- `tests/unit/runners/test_replay_import_rf06.py`：独立进程导入隔离测试。

## 设计选择和 ADR

- `physics_dt_s`、`decision_interval_ticks`、`speed_ratio`、wall timeout 独立建模。
- Continuous 自有后台 writer，客户端不轮询也持续推进；speed ratio 只影响等待间隔。
- Lockstep 每次决策推进确定数量的逻辑 tick。
- Replay 只移动记录帧游标；通过惰性包导出保证导入 replay 不加载 env/Taichi。
- 自然任务终局优先于迟到的 terminate。

## 新增/修改测试

- Continuous 无请求运行至终局；1x/10x/unbounded 动作时间线一致。
- 高频 observation polling 不推进；pause 冻结 tick，resume/terminate 状态正确。
- Lockstep decision interval 和 sim_time 计算。
- Lockstep/Continuous 相同动作时间线、终帧等价。
- Replay 只读步进；子进程确认不导入环境和 Taichi。

## 实际命令和结果

- RF-06 单元测试：9 项通过。
- RF-04～RF-07 组合定向：32 项通过。
- 受影响回归：145 项通过。
- Ruff、mypy strict、Bandit：通过。
- 最终 `make full-test`：495 项通过。

## 覆盖率与性能

- 最终全仓覆盖率 90.63%。
- 1x/10x/unbounded 均保持相同逻辑动作序列；完整性能测试通过。

## 兼容影响

- 原有场景 runner 保留并通过惰性导出兼容原 import 表面。
- 管理员 Runner 控制不与显示控制耦合。

## 未完成、风险和下一依赖

- Replay authority log、事件跳转和可视化播放控制属于 RF-08。
- 多进程 worker wall timeout 强制终止属于 RF-13。
- RF-06 完成门禁通过。

# RF-11-LIVE-PACING-002 — 实时可视化播放节拍解耦

## 状态

`DONE`（仅本任务；不代表整个通用仿真平台完成）。

## 目标与范围

将正式 V2 场景的交互式实时可视化从“每推进一个 tick 就全量重绘一次”改为：

- 固定物理 tick 仍逐步执行；
- 以墙钟调度目标仿真倍率，而不是改变 `tick_seconds`；
- GUI 按独立的最大刷新率抽样展示最新不可变 `VisualizationFrameV2`；
- 落后的 GUI 先让仿真补齐所有到期 tick，再绘制最新帧；
- 若单个权威 tick 本身已慢于目标倍率，会优先绘制未展示的最新状态，避免持续 catch-up 造成 GUI 饥饿；
- 可选 replay 输出仍逐 tick 写入权威 frame；
- GUI 标题显示权威 tick、仿真时间、目标倍率、实际平均倍率、显示 FPS 与未绘制 tick 数。

本任务未修改物理模型、会话写入者、动作语义、事件判定、检查点格式或 replay schema。

## 修改文件

- `openmdbench/visualization/live_formal_v2.py`
  - 增加仅管理墙钟/展示的 `_LivePacerV2`；
  - 高于 `0.5x` 的交互式模式先补齐到期仿真 tick，再限制 GUI 刷新；
  - 每次绘制完成后才开始下一次 GUI 刷新间隔；当 authority tick 已落后目标时，先展示最新帧再继续推进；
  - 非录制 live 会话仅在实际绘制时构建 frame；录制会话仍每 tick 构建并写入 frame；
  - 保留 `<=0.5x` 的慢速插值展示；慢速分支的预算改为 `tick_seconds / speed`。
- `openmdbench/visualization/renderer_v2.py`
  - 增加本地 `LivePresentationStatusV2`；不修改 authority frame；
  - 标题增加目标/实际倍率、刷新 FPS 与跳过 tick 指示。
- `openmdbench/cli/__main__.py`
  - 正式 V2 live 增加 `--render-fps`（默认 `12.0`）；该参数只限制 GUI 刷新。
- `tests/system/test_md_ad_002_v2_visualization.py`
  - 覆盖节拍计算、加速模式 catch-up、逐 tick replay 记录、标题状态和慢速插值兼容。

## 测试证据

已用禁用外部 pytest 自动插件的隔离运行方式执行：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/system/test_md_ad_002_v2_visualization.py::test_live_pacer_separates_tick_deadlines_from_frame_sampling \
  tests/system/test_md_ad_002_v2_visualization.py::test_interactive_live_path_paints_when_authority_tick_is_slower_than_target \
  tests/system/test_md_ad_002_v2_visualization.py::test_interactive_slow_motion_retains_interpolated_presentations \
  tests/system/test_md_ad_002_v2_visualization.py::test_renderer_consumes_frame_only_and_retains_bounded_trajectories \
  -vv --tb=short
```

结果：4 项通过。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/system/test_md_ad_002_v2_visualization.py::test_live_record_and_simulation_free_replay_render_exact_same_rich_frames \
  -vv --tb=short
```

结果：`1 passed in 11.33s`（live/replay 权威帧等价性）。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/system/test_md_ad_002_v2_migration.py::test_headless_live_runner_continues_mmg_after_world_adjudication \
  -vv --tb=short
```

结果：`1 passed in 9.38s`。

补充检查：

```bash
.venv/bin/python -m py_compile \
  openmdbench/visualization/live_formal_v2.py \
  openmdbench/visualization/renderer_v2.py \
  openmdbench/cli/__main__.py \
  tests/system/test_md_ad_002_v2_visualization.py
git diff --check
.venv/bin/python -m openmdbench.cli live --help
```

均通过；CLI 帮助中可见 `--render-fps`。帮助命令产生 Matplotlib 默认配置目录不可写的临时缓存警告，不影响命令返回或本任务逻辑。

## 代码审查

- 未发现本任务生产代码中的 `scenario_id == ...`、MD-AD-002、固定红蓝或固定实体 ID 分支；实现按正式 V2 的通用 session/frame 接口工作。
- `speed` 和 `render_fps` 只驱动墙钟等待、frame 抽样和本地标题数据；不会写入 `WorldState`、改变 `tick_seconds`、RNG、动作顺序或任务裁决。
- 每次 `advance_authority_tick()` 仅调用一次 `session.step()`；GUI 延迟时可连续调用该函数补齐到期 tick，但未展示状态达到刷新时间后会优先绘制，防止 GUI 饥饿。交互式回归断言 replay 仍包含 tick 1、2、3。
- `LivePresentationStatusV2` 不进入不可变 authority frame、检查点或 replay，因此不会污染回放等价性。
- 公共 Python 调用保持兼容：`render_fps` 是默认 `12.0` 的新增关键字参数；原有调用无需修改。

## 确定性、领域影响与风险

- 确定性：同一 seed 和动作时间线下，显示频率只影响何时展示 frame，不影响权威 tick、日志或 replay 内容；已覆盖连续 replay tick。
- 领域影响：无。飞行器、舰艇、导弹、探测、通信、毁伤和任务评分的物理时间仍由固定 `tick_seconds` 推进。
- 风险：标题中的“实际倍率”是从本次 live 开始到当前帧的平均仿真时间/墙钟时间比。若单 tick 仿真或逐 tick replay 落盘本身超过预算，实际倍率仍会低于目标值；此时系统以持续展示最新状态优先，不应通过跳过权威 tick 追求目标倍率。
- 非范围：离线 replay 的播放循环仍采用原有逐记录展示节拍；本任务只优化用户提出的正式 V2 实时 live 可视化。

## 后续建议

在真实桌面 GUI 下运行 `openmdbench live --scenario MD-AD-002-MEDIUM --speed 10 --render-fps 12`，观察标题中的实际倍率与跳过 tick 数；若场景规模增大，再根据显卡/Matplotlib 吞吐调整 `--render-fps`。

# MD3-05 拦截规划、弧形几何、任务与评分报告

## 状态

`DONE`，代码审查结论为 `SELF_REVIEWED`。本阶段只新增通用机制，不创建
MD-INT-003 场景、任务常量或规则智能体；三档参数、数据包和展示日志分别留给 MD3-07、
MD3-08 和 MD3-09。

## 交付

- `openmdbench/sdk/intercept_v2.py`：公开 `predict_intercept_waypoint`。输入是调用者已获授权的
  contact estimate、自身能力、standoff 和可选区域，输出普通导航 waypoint/速度/航向建议。
  模块不导入 World/Session，也不创建新的 action type 或改变 WorldState。
- `openmdbench/world/interdiction_geometry_v2.py`：局部米制、连续路径的通用事实：
  radial crossing、跨 0° 的顺/逆时针 annular-sector occupancy、front-of-track、同步 path
  conflict；`InterdictionGeometryAccumulatorV2` 记录占位/阻塞持续时间、冲突去抖和重规划时延，
  并可 snapshot/restore。
- `openmdbench/missions/engine_v2.py`：在既有单一评分权威上区分三种状态：结构性 N/A 保持
  `None`；预期但缺少的输入强制为数值 `0.0`，附带 `MetricDataMissingReceiptV2`；正常数值保持
  不变。MissionEngine 的插件输出缺失会用其 deterministic output hash 作为审计证据来源。

几何工具只产生事实，绝不直接修改 health、速度、任务胜负或评分。后续场景通过数据将事实
接入 mission rule/metric；本阶段没有硬编码 P0、半径、扇区、持续时间、阵营或实体 ID。

## 验证

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_md_int_003_mission_geometry.py \
  tests/contract/test_mission_scoring_engine_v2.py
```

结果：`66 passed in 1.30s`。

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_md_int_003_mission_geometry.py \
  tests/contract/test_mission_scoring_engine_v2.py \
  tests/contract/test_declarative_mission_control_v2.py \
  tests/contract/test_geography_boundary_v2.py \
  tests/contract/test_world_checkpoint_v2.py \
  tests/contract/test_session_action_pipeline_v2.py \
  tests/contract/test_generic_core_schema_v2.py \
  tests/contract/test_generic_domain_schema_v2.py
```

结果：`302 passed in 8.85s`。另已通过 `py_compile`、限定 `git diff --check` 和生产模块的
场景/阵营/实体 ID 特判扫描；未运行 T4/T5、全量、性能、并发、压力、安全或长稳测试。

## 审查与风险

冻结范围自审覆盖了 SDK 不触及 World 的边界、所有几何输入的有限值和身份校验、连续交叉和
跨 0° 扇区、静态 checkpoint 恢复、去抖、以及 missing 不能伪装为 N/A 的失败用例；没有发现
P0/P1。此结论为 `SELF_REVIEWED`，不表示独立第三方审查。

U10/U11/U13 的实际时长、权重、距离和阈值仍是 `UNVALIDATED_BENCHMARK`。具体场景把这些
通用能力配置为比赛规则之前，仍须在 MD3-07 使用 data-only 包并完成 rename/determinism
验证。

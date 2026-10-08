# MD3-00 测试基线

## 记录

- TASK_ID：`MD3-00-001`
- 测试等级：T1（MD3-00 计划明确允许）
- 环境：Ubuntu workspace、Python `3.11.15`、`.venv`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`MPLCONFIGDIR=/tmp/openmdbench-mpl`
- Git：`refactor` / `e85523f`；运行前已有未提交改动，见 `md3_00_baseline_audit.md`。
- 取样锚点：engine/schema `2.0.0/2.0`；scenario `md-ad-002.easy.v2`；seed `0`；resolved `sha256:34f8322ccbdb8ce915002dc8d886235a87b61e833dd6069c992cf8f01e6c1f66`；catalog `sha256:cf34729fad371b07f58d3f4f66ff7cb975a00f97cc716a93b3a2527650ba6350`；map `sha256:c40a43035b62340c558e1c697823a574b936b50123acb49c4754b4c1d79c398d`；registry/plugin `sha256:573277d4e4495e4b6a22c9cb33fbdbe0fb70020925d8c717009ac503e91af69a/none`。

## 收集

命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest --collect-only -q \
  tests/contract/test_catalog_registry_v2.py \
  tests/contract/test_declarative_compiler_pipeline_v2.py \
  tests/contract/test_geography_boundary_v2.py \
  tests/contract/test_combat_damage_v2.py \
  tests/contract/test_mission_scoring_engine_v2.py \
  tests/contract/test_session_action_pipeline_v2.py \
  tests/integration/test_native_mmg_adapter_v2.py \
  tests/integration/test_session_action_world_v2.py \
  tests/scenarios/test_md_ad_002_registration.py \
  tests/system/test_md_ad_002_v2_migration.py
```

结果：`652 tests collected in 1.32s`。

收集范围覆盖 V2 Catalog/registry、compiler、geography/boundary、combat/damage、mission/scoring、action pipeline、MMG native adapter、session/world、正式场景注册以及 MD-AD-002 V2 迁移。此结果只说明当前可发现的测试面，不等同于通过。

## 小型 V2 冒烟

命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/scenarios/test_md_ad_002_registration.py::test_variant_loads_and_creates_empty_session_with_config_metadata[MD-AD-002-EASY] \
  tests/system/test_md_ad_002_v2_migration.py::test_surface_picket_uses_isolated_mmg_through_public_navigation \
  tests/system/test_md_ad_002_v2_migration.py::test_formal_tick_uses_append_only_memory_records_not_durable_checkpoint[MD-AD-002-EASY]
```

结果：`3 passed in 15.06s`。

| 验证项 | 结果 | 能证明的边界 |
|---|---|---|
| formal package 装载/空会话 | PASS | V2 registry、compiler、resolved、session 创建链路可工作。 |
| public navigation 驱动 surface picket MMG | PASS | MMG adapter 可经公开 V2 动作链运行，且 native state 隔离。 |
| append-only tick | PASS | tick 记录保存在内存，而非每 tick 建 durable checkpoint。 |

## 失败与告警分类

| 项目 | 分类 | 处理 |
|---|---|---|
| 一次只读元数据探查访问 `resolved.world.map_hash` | 审计脚本字段假设错误；不是测试/产品失败 | 已改为读取实际 world fields；不影响测试结论。 |
| 未设置 `MPLCONFIGDIR` 的只读导入出现 Matplotlib cache 警告 | 环境告警 | 后续所有 pytest 已设置 `/tmp/openmdbench-mpl`。 |
| 未运行 T2/T3/T4/T5 | 授权边界 | 正确：MD3-00 仅授权 T0/T1；全量、性能、并发、安全、长稳保留至 MD3-11 且需用户明确授权。 |

## 未覆盖风险

- 当前没有 MD-INT-003 ScenarioPackage、surface weapon、suicide effect、arc geometry、天气 modifier pipeline、通信运输或规则智能体，因此不能用本基线宣称任何 MD3 功能已通过。
- 冒烟运行于已有脏工作树；它是当前状态证据，不替代后续每个阶段的独立定向复测。
- 未测 16/32 并发、1500 tick 性能、30 seed、100 局、REST/Gym 等价、四视角、live/replay/checkpoint 的 MD3 专项状态；这些不属于本阶段。

## 下一阶段条件

MD3-00 的 T1 基线通过。进入 MD3-01 前，需以 ADR 固定 U1–U13 的 benchmark 可信度、`interdict_to` 边界、pending impact、自爆/残骸、几何、通信 tick 量化、终局/N-A 与 REST bilateral 语义；随后才可以修改资源或代码。

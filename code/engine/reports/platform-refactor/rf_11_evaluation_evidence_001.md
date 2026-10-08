# RF-11-EVALUATION-EVIDENCE-001：评估级对局事件证据

## 范围

依据 `LOG-001`、`DMG-003`、`OBS-002` 与 RF-11 日志/回放要求，补充通用 V2 权威 tick 回执中的时空和毁伤证据。未新增场景 ID、阵营、实体或武器特判；不改变公开 Observation 的字段白名单。

## 变更

- `SensorContactReceiptV2` 记录传感器位置、目标审计真值位置/速度、距离、方位、俯仰、传感器量程与 `local-m` 坐标系。该完整记录仅在权威回执/检查点中保存。
- `WeaponExecutionV2` 记录发射点、发射平台速度及目标在发射时的位置/速度。
- 导弹推进和末端回执记录目标位置、导弹速度、最近接近的 tick 内时间比例、终止位置；命中时单独记录 `impact_position_m`，近炸未命中不伪造命中点。
- 武器 `DamageIntent` 记录打击位置和坐标系；`DamageApplyReceiptV2.results` 记录每个目标的毁伤意图、生命值前后、组件生命值及生命周期前后，用于指标计算。

## 可用性与公平性

- 新字段由 capability-driven 通用传感器、战斗、导弹和毁伤流水线生成，随 `WorldTickReceiptV2` 进入检查点并可恢复。
- 完整目标真值、随机数和内部关联仍不进入 faction Observation；训练智能体只使用既有权限过滤后的实体和航迹观测。
- `impact_position_m`、`terminal position_m` 和 `closest_approach_m` 明确分开，支持命中精度与未命中原因的独立统计。

## 验证

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/unit/world/test_missile_v2.py \
  tests/contract/test_generic_subsystems_v2.py \
  tests/contract/test_combat_damage_v2.py -q
# 215 passed in 18.84s

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/integration/test_session_action_world_v2.py \
  tests/system/test_md_ad_002_v2_migration.py -q
# passed (targeted session/checkpoint and MD-AD V2 migration suite)

git diff --check
# passed
```

首次 pytest 启动曾被系统 ROS 的外部 pytest 插件加载失败（缺少 `lark`）；使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 后运行项目测试，属于环境插件隔离，不影响项目代码。

## 审查

- 手工检查：没有场景 ID、固定 faction、固定实体 ID 或隐式策略分支。
- 手工检查：坐标统一标为 `local-m`；未把“最近接近位置”误记为未命中时的命中点。
- 手工检查：新增证据随现有 World tick/检查点路径序列化和恢复，未创建第二套 WorldState、战斗或日志真源。

## 风险与后续

- 当前通用传感器是检测模型，完整审计回执记录几何真值；若后续引入带噪测量模型，应另增 `measurement_position_m`、协方差和测量模型版本，不能把真值当作测量值。
- 本任务没有定义区域覆盖、协助拦截归因或训练 reward；这些指标可基于本次新增的权威证据在后续评分任务中声明和计算。

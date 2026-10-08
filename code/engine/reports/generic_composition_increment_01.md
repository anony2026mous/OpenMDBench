# 通用场景组合增量 01

## 状态

PARTIAL。通用 schema、Catalog 包边界、Compiler、ResolvedScenario、WorldState 装配、
动态波次、受控事件和 CLI 已贯通；通用 Catalog 武器/任务/评分运行时尚未贯通，不能
声明平台化重构全部完成。

## 本阶段变更

- 新增 `composition@1.0`：静态实体和波次分别配置平台、动力学、Loadout、传感器、
  通信、弹药、阵营、数量、初态和速度。
- ScenarioPackage 支持任意数量包内 Catalog 文件，pack/unpack/hash 覆盖这些文件。
- 新增安全 Catalog YAML loader；只接受数据模型，不接受 Python 导入。
- Compiler 做精确版本解析、依赖闭包、平台兼容、载荷质量和弹药从属校验。
- ResolvedDeployment/ResolvedWave 冻结完整组件引用；运行时按波次定义生成任意数量、
  阵营和平台类型实体。
- 通用场景复用唯一 WorldState 和现有 OpenMDBenchEnv 固定 tick，没有新增主循环。
- 新增 scenario-validate/scenario-resolve/scenario-inspect CLI。

## 兼容性

MD-INT-001 和 MD-AD-002 EASY/MEDIUM/HARD 继续走既有兼容 adapter。本阶段不修改
其组件配置、裁决规则和基线参数。

## 已知阻断

P1：通用 Catalog 武器尚未接入统一结构化 engage 动作和战斗裁决；Catalog mission、
scoring 尚未成为通用运行时插件。因此自定义组合当前仅适用于编组、部署、动力学、
波次、基础通信、事件和可视化开发，不能替代专用任务裁决。

## 测试与独立审查

- Ruff lint：通过；本阶段 9 个文件 Ruff format check 通过。
- mypy strict：124 个源文件通过。
- Bandit：通过。
- 通用组合/Compiler/Catalog 定向：44 passed。
- 分层单元与 Catalog 契约：40 passed；功能/集成/正式迁移系统测试：11 passed。
- 独立审查首轮：P0=0、P1=6、P2=3、P3=1；已关闭 Gym ID/space、地图身份、
  场景身份问题，并补充兼容、波次、归档资源边界。
- 最终仍有 P1：MD-AD 普通组合包迁移和 Catalog sensor/communication/weapon/
  mission/scoring E2 未完成。本阶段保持 PARTIAL / NOT RELEASED。
- 全量 pytest 曾运行到 41% 后因本轮审查修复使结果失效而终止；不能记录为全量通过。

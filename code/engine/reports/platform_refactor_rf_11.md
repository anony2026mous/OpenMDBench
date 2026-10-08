# RF-11 阶段报告：四个正式场景迁移

迁移对象：MD-INT-001、MD-AD-002-EASY、MEDIUM、HARD。

- 四场景均由 ScenarioCompiler 生成冻结 ResolvedScenario，再创建 SessionRuntime。
- MD-INT 和 AD 三难度内置规则策略仅消费公开 observation。
- 每个场景均完成 reset、权威 tick 推进与清理；全量套件继续验证完整终局、回放、REST、Gym、CLI、可视化和基线。
- 能力选择依据 resolved component/difficulty，不新增 WorldState、物理循环或裁决器。

结论：四个核心正式场景迁移后 E2 回归通过。

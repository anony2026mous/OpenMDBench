# RF-01 R1：公共 Schema 1.0 核心与兼容层

STATUS: IMPLEMENTED / TARGETED-GATE-PASS

## 结果

- 建立唯一规范模型源 `openmdbench.schemas.platform`，覆盖 RF-01 列出的公共 DTO；
- 冻结显式 schema version、枚举、可见性、错误码、单位字段、有限数和生命周期约束；
- Observation、VisualizationFrame、ReplayMetadata 纳入统一 JSON Schema；
- JSON Schema 发布端点及 OpenAPI components 已接入；
- 原有通用 ActionBatch 和 MD-AD-002 RedActionBatch 由显式单向 adapter 迁移，主循环暂不改写；
- 接口示例、兼容策略和稳定错误码已记录于 `docs/platform_schema_1_0.md`。

## 测试与审查

新增契约测试覆盖规范模型 roundtrip、缺失版本、NaN、TTL、重复 ID、关闭的错误码/可见性、
OpenAPI/端点发布、旧动作模型映射、不变输入和 ActionBatch Python/JSON 等价。

定向门禁：9 passed。代码审查未发现通过修改概率、阈值、golden 或放宽校验绕过测试的行为。
R2 将执行既有 observation/replay/REST 兼容回归与全仓静态检查，最终 T4 后才宣告 RF-01 完成。

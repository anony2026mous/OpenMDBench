# RF-01 final gate and independent diff review

STATUS: PASS / RF-02-READY-PENDING-USER-APPROVAL
TASK_ID: RF-01-FINAL-GATE-20260826
TEST_LEVEL: T4
REVIEW_SCOPE: RF-01 canonical schemas, compatibility adapters, OpenAPI publication and docs

## Outcome

公共平台 Schema 1.0 已冻结。唯一规范入口为 `openmdbench.schemas.platform`，JSON Schema
通过 `platform_json_schema()`、`GET /v1/schemas/platform/1.0` 和 OpenAPI components 发布。
后续 RF 不得复制 DTO 定义。

## Implemented

- 冻结资源/场景、会话、观测、动作生命周期、事件、可视化/replay、checkpoint 和稳定错误模型；
- 规范输入显式要求 `schema_version="1.0"`；旧 Observation/replay DTO 的缺省仅保留为读取适配；
- 全层级拒绝 NaN/Inf，物理字段显式单位，额外字段 fail closed；
- Event visibility 关闭为 referee/red/blue/public，稳定错误码关闭为 `StableErrorCode`；
- ActionBatch 校验批次/子项 TTL、ID 唯一性，并规范化任意 JSON tuple/list 以保证往返等价；
- 旧通用 ActionBatch 与 MD-AD-002 RedActionBatch 通过显式单向 adapter 接入；撞击映射为离散 `ram`；
- 文档 `docs/platform_schema_1_0.md` 给出兼容规则、错误码和接口示例。

## T4 evidence

Command: `make full-test`

- Ruff: PASS；
- Mypy strict: PASS, 238 source files；
- Bandit: PASS；
- Pytest: PASS, 425 tests；
- Coverage: 91.24%, threshold 80%；
- Warnings: 93，仅为既有 Taichi 弃用、Gymnasium 建议/类型转换、CJK 字体和 Agg 非交互提示；
- Duration: 2275.03s (37m55s)；
- 正式报告：`reports/md_int_001_full_test.json`, `passed: true`。

首次 T4 在 collection 阶段发现 `schemas -> visualization -> core.world -> schemas` 循环导入。
可视化 schema 合并改为惰性加载后，从头重跑完整 T4 并通过。最终审查进一步将三类兼容读取
DTO 在规范 JSON Schema 中标记为版本必填；随后 24 项相关契约/replay/REST 回归及全仓静态门禁通过。

## Independent review

Correctness：JSON/Pydantic/OpenAPI roundtrip、合法/非法输入、旧动作适配、旧 replay、REST、
Gym、三难度系统链均通过；没有修改场景概率、阈值、种子选择或 golden。

Security and visibility：DTO schema 不包含 `WorldState`；额外字段拒绝；Event 视角为显式白名单；
既有 red/blue/public 防泄漏测试通过。

Compatibility：旧 producer/reader 的默认字段继续可用并在重序列化时写出 1.0；规范 schema 和新
canonical ActionBatch 要求调用者显式提交版本。既有主循环仍消费旧 DTO，迁移由 adapter 隔离，
未在 RF-01 偷跑 RF-02 Catalog 或后续 session runner 改造。

Worktree hygiene：未恢复或纳入既有 `docs/agents.md` 删除、`../map_modified.py`、`.cao/` 等无关
工作区内容；`git diff --check` 通过。

## Verdict

P0: 0 open.
P1: 0 undispositioned.
RF-01: PASS.
RF-02: READY，尚未开始，等待用户明确批准。

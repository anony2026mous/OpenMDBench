# Phase 5：训练接口、REST、SDK、检查点与审计

## 完成范围

- T5.1：注册 `OpenMDBench-v1` Gymnasium 环境，提供结构化 JSON 观测与显式张量 wrapper。
- T5.2：同步向量环境、子会话独立 reset，以及并行顺序确定性。
- T5.3：FastAPI 会话、观测、动作、结果、场景、健康、checkpoint 和 restore 接口。
- T5.4：request ID、幂等键、timestamp 冲突、原子动作校验、会话级限流和统一错误模型。
- T5.5：仅依赖公开 REST 契约的同步 Python SDK 与随机策略示例。
- T5.6：完整状态 checkpoint、版本/场景哈希、防篡改摘要及 JSONL 审计哈希链。

## 关键验收

- 本地 Gym、REST 和 SDK 对相同 seed、场景和动作序列逐步等价。
- 向量环境顺序不改变会话结果，独立 reset 不影响其他会话。
- checkpoint 恢复后继续 100 tick 与连续运行逐字段一致。
- checkpoint 和审计记录被修改后均会拒绝加载。
- SDK 和公开示例不导入内部 `core`、`envs` 或 `replay` 模块。

## 测试结果

- Ruff：通过。
- mypy：106 个源文件无问题。
- M5 接口模块测试：20 passed。
- 全量测试：134 passed。

全量测试的 14 条警告均为非阻塞上游提示：Taichi locale API 弃用提示，以及
Gymnasium 对物理量动作空间、JSON 列表观测和 wrapper 检查方式的建议。

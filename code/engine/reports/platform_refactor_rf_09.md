# RF-09 阶段报告：REST 纵向切片

- 新增 `AgentGateway`，REST 不读取环境或 WorldState。
- 新增 `/v2/sessions` CRUD、observation、step、control 和按视角 frame 端点。
- 生命周期冲突稳定返回 409，不推进 tick；未知会话返回 404。
- 原 `/v1` 的 action idempotency、checkpoint/restore、result、请求大小和限流保持兼容。
- API 委托测试与原 REST 系统测试全部通过。

结论：统一 Session 权威入口的最小纵向闭环通过。

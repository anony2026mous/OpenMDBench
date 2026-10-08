# RF-13 阶段报告：进程隔离

- 新增 spawn 模式 `SessionWorker`，每个 native session 可置于独立进程。
- 请求/响应队列有界，支持 heartbeat、start、step、snapshot、close 和超时。
- ResolvedScenario 以 JSON DTO 跨进程并在 worker 内重新严格校验，避免冻结映射 pickle 缺陷。
- worker 异常转为稳定边界错误，close 后 join；超时兜底 terminate，防止孤儿进程。
- 真实 MD-INT worker 生命周期与清理测试通过。

结论：进程隔离核心通过；API worker 池、租户鉴权/配额和服务重启恢复仍属于生产部署层工作。

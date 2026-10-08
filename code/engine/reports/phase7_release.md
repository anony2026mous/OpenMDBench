# Phase 7：性能、安全、审查与发布

## 已完成

- T7.1：三档场景、4/8 并发、日志与回放性能基准。
- T7.2：1000 个短会话资源回收 smoke 和可配置 12 小时 soak runner。
- T7.3：会话隔离、动作时序、检查点、contact、频率、路径、请求体和日志恶意输入测试。
- T7.4：九维独立审查，Ruff/mypy/pytest/coverage/Bandit/OSV；P0/P1 清零。
- T7.5：`make selftest` 生成 JSON、Markdown、日志、覆盖率和性能报告。
- T7.6：非 root CPU Dockerfile、健康检查、最小 Compose、训练/场景/API/回放指南和 changelog。

## 验证证据

- Python sdist/wheel 构建成功，wheel 包含全部 36 个场景 YAML。
- 发布契约、API 契约和场景模块测试：19 passed。
- 正式自测首次通过：167 passed，0 failed，0 skipped，覆盖率 90.58%。
- Ruff、strict mypy、Bandit：零发现。
- 性能：三档 RTF 16955–17390；峰值 RSS 96.47 MiB；4/8 会话合计约 11821/12101 tick/s。

## 未伪报的外部验证

- 当前宿主没有 `docker` 命令，因此 Dockerfile/Compose 已做静态契约测试，但镜像构建、非 root
  实际启动和 `/health/ready` 容器探测仍需在装有 Docker 的 Ubuntu CI/主机执行。
- 12 小时 wall-clock soak runner 已实现，但当前只执行了 1000 会话 smoke；正式发布标签前仍需运行
  `.venv/bin/python -m openmdbench.cli soak --hours 12 --minimum-sessions 1000`。

在这两项外部运行门禁完成前，不创建或宣称最终发布标签。

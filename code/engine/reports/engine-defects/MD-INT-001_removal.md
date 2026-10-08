# MD-INT-001 旧场景移除记录

STATUS: DONE
OBJECTIVE: 按用户指示移除不再需要的 MD-INT-001 旧接口场景，同时保持正式 V2 场景入口可用。

- 已移除 MD-INT-001 场景定义、配置、专用评分/裁决、runner、自测和专用测试。
- 已从 formal runtime registry、CLI 选项、Makefile 自测和 README 的正式场景列表移除；CLI 对该 ID 返回 argparse 的无效选项错误。
- 历史 ADR、审计报告和既有产物作为历史证据保留，不作为可运行入口。
- 删除后的收敛回归：`65 passed, 1 warning in 94.37s`；warning 为 Taichi 的 Python locale 弃用警告。
- 当前树完整回归：`2047 passed, 1 deselected, 70 warnings`；coverage `85.45%`。全仓收集为 `2048 tests collected`，无收集或导入错误。
- `rg` 核验显示可执行源码、README、Makefile 与测试中不再有 MD-INT-001 运行时引用；仅 REST 契约测试保留“已退役且不在公开列表”的负断言。

兼容性：MD-INT-001 的旧 CLI、Gym、REST、replay 和 selftest 调用现在均不再受支持；MD-AD-002 与 MD-INT-003 正式 V2 路径保持。

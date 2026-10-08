# Phase 4：任务、场景与评分

## 完成范围

- T4.1：场景 schema、YAML 加载器及公开/裁判信息隔离。
- T4.2：任务状态机与稳定事件序列。
- T4.3–T4.7：侦察、跟踪、拦截、区域拒止、应急处置共 36 个独立场景。
- T4.8–T4.9：规划层、执行层及 0.5/0.5 综合评分。
- T4.10：五类代表场景的确定性成功/失败脚本及全场景合法策略 smoke。

需求未明确的拦截限制、天气和坐标默认值记录于
`docs/decisions/ADR-011-scenario-defaults.md`。

## 验收结果

- `make scenario-test`：7 passed。
- `make lint`：通过。
- `make typecheck`：通过，88 个源文件无问题。
- `make test`：116 passed。

全量测试仅有两个非阻塞上游警告：Taichi 使用即将弃用的 locale API，以及
Gymnasium 对物理量动作空间未归一化的建议。后者是保留公开物理动作语义的有意设计。

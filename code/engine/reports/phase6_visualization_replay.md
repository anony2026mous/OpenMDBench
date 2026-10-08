# Phase 6：可视化与回放

## 完成范围

- T6.1：现有界面、地图、数据源、Artist 生命周期和线程模型盘点。
- T6.2：版本化 VisualizationFrame、metadata、实体、contact、事件和得分 schema。
- T6.3：referee、blue、red、public 实时安全视角适配。
- T6.4–T6.5：JSONL/gzip 写入、流式读取、磁盘字节索引和精确 seek。
- T6.6：定义项目权威对抗日志格式，并在生产 REST 会话中逐局、逐 tick 自动保存。
- T6.7–T6.8：五类原创矢量外型、主题/状态样式和 retained-mode Matplotlib renderer。
- T6.9–T6.11：播放控制、视角/事件/得分面板和确定性 Agg PNG 导出。
- T6.12：可选动作重演与首个配置/状态漂移定位。

## 关键验收

- 100,000 帧顺序读取峰值内存低于 12 MiB。
- 1000 实体和轨迹连续更新不重建已有 Artist。
- 普通 renderer/replay 路径不加载 Taichi 仿真内核。
- 蓝方、红方和 public 视角不显示未授权真实实体。
- 日志动作重演一致；篡改动作定位首个漂移 tick，篡改配置定位 tick 0。
- 无 DISPLAY 环境下相同输入产生字节一致 PNG。

## 标准产物

- `samples/example.replay.jsonl`：四域标准示例日志。
- `reports/replay-four-domain-referee.png`：四域裁判视角截图。
- `reports/replay-blue-view.png`：蓝方防泄漏视角截图。
- `reports/replay-red-view.png`：红方防泄漏视角截图。
- `docs/match_log_format.md`：首版对抗日志格式及写入时序。

## 测试结果

- M6 专项测试：33 passed。
- Ruff：通过。
- mypy：127 个源文件无问题。
- `make selftest`：通过。
- 全量测试：161 passed。

14 条警告均为既有非阻塞上游提示：Taichi locale API 弃用，以及 Gymnasium 对物理
动作空间、JSON 列表观测和 wrapper 检查方式的建议。只读 HOME 下运行 CLI 时
Matplotlib 会将字体缓存自动放入 `/tmp`，不影响确定性导出结果。

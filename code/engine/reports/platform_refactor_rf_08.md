# RF-08 阶段报告：实时帧与回放边界

- 新增有界 `LiveFrameBus`，满载采用 drop-oldest，发布不等待渲染器。
- Session 从既有权威 WorldState 构造 referee/blue/red/public 帧，只公开只读 `LiveFrameSource`。
- live/replay 共用 `VisualizationFrame`；ReplayReader 增加 resolved/map hash 拒绝策略。
- 测试覆盖队列溢出、不可变帧、live→replay roundtrip 和哈希不匹配。
- 全量门禁：509 项通过，覆盖率 90.51%，静态检查通过。

结论：RF-08 核心门禁通过；既有 PlaybackController、Matplotlib retained renderer、Agg 和正式场景实时显示继续复用。

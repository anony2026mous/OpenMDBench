# OpenMDBench Legacy 对抗日志格式 1.0

> 仅为 `SessionStore`/MD-REC-001 兼容回归保留。新 V2 场景请使用
> `ReplayHeaderV2`/`ReplayRecordV2` 和
> `docs/OpenMDBench_用户操作手册与场景智能体开发指南.md`，不要依据本文开发新功能。

每局产生一个 `<match_id>.replay.jsonl` 文件。第一行必须是 `ReplayMetadata`，后续每行
是一个完整 `VisualizationFrame`。所有记录使用 UTF-8 JSON，禁止差量帧和多行 JSON。

Metadata 固定记录 schema_version、match/scenario ID、seed、tick 时长、坐标系、引擎
版本和配置哈希。Frame 固定记录 timestamp、当 tick 已接受动作、全部可见实体快照、
双方当时实际 contact、事件以及当时权威 scores。未知 1.x 字段由 schema 的兼容策略
处理，未知主版本直接拒绝。

写入顺序为：创建会话时写 metadata 和 tick 0；动作整批验证并成功推进后每 tick 写新帧；
动作拒绝不产生物理帧，只进入独立审计日志；终止、超时或显式关闭时 flush 并关闭。
默认每帧 flush，允许部署显式提高 flush_every 以换取吞吐量。

普通回放只读取该日志，不加载仿真内核、不重跑传感器、不重算历史得分。未压缩日志
可生成 `.idx` 二进制时间索引；`.gz` 归档按顺序读取。

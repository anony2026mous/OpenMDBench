# MD-INT-001 Phase F 回放与可视化报告

- 状态：通过。
- 对抗日志：逐 tick 记录五实体、双方动作批次与高层意图、contact、武器库存、公开战斗事件、地图及动力学元数据。
- 视角隔离：裁判、蓝方、红方、公共视角由同一 DTO 过滤生成。
- 底图：固定 `weihai_v1` 多边形与地图哈希，正式验收未使用空白世界。
- 无显示渲染：Matplotlib Agg；可视化导入不会提前加载 Taichi。
- 阶段测试：31 passed；仅有第三方 Taichi 弃用告警。
- 关键帧：`reports/md_int_001_phase_f_keyframe.png`。


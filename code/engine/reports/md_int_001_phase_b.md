# MD-INT-001 阶段 B 报告

状态：完成（I001-B01 至 I001-B05）。

- 五实体统一注册、索引和稳定遍历。
- 红蓝 UAV 共用受限三维动力学。
- USV 正式调用既有 Sim2Sea MMG/RK4。
- 岸基雷达固定且拒绝移动。
- 同步推进不依赖注册顺序。
- ReplayFrame 记录实际五实体；metadata 记录地图和动力学身份。

阶段测试：38 passed；Ruff 与严格 mypy 通过。唯一警告为第三方 Taichi 使用已弃用的 Python locale API。

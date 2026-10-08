# MD-INT-001 系统测试报告

- 状态：通过，9 passed，0 failed，0 skipped。
- CLI：场景 selftest 命令及六项产物契约通过。
- 威海世界：地图 ID/版本/双哈希、五实体、海岸碰撞数据和 MMG 元数据通过。
- Gymnasium：reset/step、space 实值、终止标志和五实体主循环通过。
- REST：创建、蓝方公开观察、动作、幂等/时间戳冲突、结果、checkpoint/restore、跨会话 404 与删除通过。
- 并发：使用 spawn 隔离运行四个完整场景，seed、结果、contact/RNG 无跨会话污染。
- 回放：不加载仿真环境即可解析终态；渲染前强制验证 `weihai_v1` 地图身份和哈希。
- 告警：Taichi 使用 Python 将弃用的 locale API；Gymnasium 对 list observation 做 NumPy cast。均来自第三方且不影响断言。
- 总耗时：43.66 秒。


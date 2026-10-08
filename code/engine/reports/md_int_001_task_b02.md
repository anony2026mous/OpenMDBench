# MD-INT-001 I001-B02 实施报告

状态：完成。

## 复用判定

结论：`extend`。仓库已有 `openmdbench.domains.air.uav.step_uav`，已具备三维位置、最短角转向、升降率和高度边界，因缺少加减速响应及 degraded 性能限制而原地扩展；未新增另一套 UAV 模型。

最终实现：`openmdbench/domains/air/uav.py` 的 `UAVState`、`UAVCommand`、`step_uav`。

## 接入结果

- 速度按最大加速度 8 m/s²、最大减速度 10 m/s² 响应。
- 最大速度 80 m/s、最大转弯率 30 deg/s、最大升降率 20 m/s、高度范围 0–3000 m。
- degraded 将最大速度和最大转弯率乘 0.70。
- 三架红蓝 UAV 均由环境主循环调用同一个 `step_uav`；destroyed/crashed 不进入推进集合。
- `last_dynamics_trace` 明确记录每实体调用的 `step_uav` 或 `hold`，不存在 UAV 走 USV 12.9 m/s 二维路径。

验证：方位 0/90/180/270、跨零最短角、转弯率、加减速、高度、degraded、三 UAV 主循环接入及确定性相关共 15 项通过；Ruff、mypy 通过。

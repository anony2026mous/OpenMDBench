# AD2-06 公开接口阶段报告

## 完成范围

- 新增版本化 `RedObservation`、`RedActionBatch` 和嵌套平台动作 DTO。
- `RedActionBatch` 最多控制 7 个红方实体，整批校验版本、场景、时间戳、重复 ID、实体归属、生命周期、岸基移动、USV 武器、contact 所有权、count、数值范围及 NaN/Inf。
- 缺失平台动作按显式 `hold` 处理并记录 `action_defaulted_hold`。
- 环境新增 canonical batch 入口；导航、传感器、通信和交战使用同一批次语义。
- 新增固定槽位 Gym 适配器：7 个己方槽位、15 个 contact 槽位及有效 mask；实际 reset/step 返回值通过 space.contains。
- REST 接收 `action_batch`，继续提供时间戳冲突、幂等键、会话隔离和统一错误响应；MD-AD-002 拒绝旧单平台动作。
- SDK 新增 `submit_action_batch`，并提供仅依赖公开接口的最小示例。
- AD2 REST observation 使用红方字段白名单，不返回 WorldState、蓝方真值 ID 或 RNG 样本。

## 验证结果

- AD2-06 及既有 REST/SDK/接口等价定向测试：11 passed。
- 新增 DTO/Gym/API/环境/SDK 8 个核心文件严格 mypy：通过。
- Ruff：通过。
- 全仓回归可稳定执行至既有 `test_md_int_001_matrix`；该测试触发 Taichi 进程级提前退出，无法生成正常 pytest 汇总。该问题在 AD2-06 变更之外，但意味着本阶段不能声称全量测试门禁闭合。

## 超时语义

- 仿真核心不等待墙钟，动作 timestamp 必须等于当前 tick。
- 托管比赛服务的动作等待上限为 5000 ms；超时由服务适配层生成 `action_timeout` 和 hold batch。当前仓库没有外部 agent 调度器，因此本阶段公开 DTO 固定暴露 `action_deadline_ms=5000`，实际等待循环留给托管 runner 接入。

## 已知限制

- FastAPI TestClient 在线程中构建正式威海场景时，底层原生地图/字体依赖会提前结束测试进程；DTO、SessionStore 和既有 REST 路由分别完成测试，但正式 MD-AD-002 的 TestClient 端到端请求尚无稳定自动化证据。
- “同一规则智能体通过本地和 REST 完成整局”依赖 AD2-07 红方/蓝方规则智能体，当前只能验证同一 DTO 的单步等价入口。


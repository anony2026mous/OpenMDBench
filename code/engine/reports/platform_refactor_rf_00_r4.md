# RF-00R4 MD-INT collision-contract remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R4-MDINT-COLLISION-CONTRACT
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包关闭 RF-00R3 遗留的三个 MD-INT-001 问题：禁用蓝方交战时红方未能突防、红方悬停且双方不交战时发生非预期碰撞，以及旧 Gym `info` 精确契约被扩张。未进入 RF-01，未修改武器概率、毁伤规则、碰撞阈值、保护区半径、时间上限或冻结 golden。

## Root causes and remediation

### Red ingress altitude

MD-INT runner 将海平面的保护点同时作为红方三维航路目标。红方从 1500 m 持续下降，最终在保护区外触地，导致禁用蓝方交战的基线以 timeout 而非 red breach 结束。

修复后，二维保护点和裁决半径保持不变；红方航路目标的高度取威胁实体初始高度。因此高度作为主循环策略输入保留，红方可在任务飞行高度完成水平突防。

### Baseline interceptor standoff

蓝方规则策略此前始终追踪到 contact 的预测坐标。在 `red_hold + disable_blue_engage` 路径中，蓝方最终与红方发生非意图碰撞，错误地产生 `threat_destroyed`。

新增 1000 m baseline 拦截安全间距：进入间距后使用 `hold_position`，但在挂载和射程允许时仍可提交合法武器意图。该变更只约束默认规则策略，不改变底层显式 `ram_target_id`、碰撞检测或碰撞毁伤能力。

### Gym compatibility

`collision_events` 是双边正式仿真和实时可视化所需字段，但旧 Gym `step()` 的 `info` 有稳定的精确字典契约。修复将该字段放在 `step_bilateral()` 返回信息中，旧 Gym `step()` 恢复为 `outside_world` 与 `reached_goal` 两字段。

## Test-first evidence

新增策略测试在实现前失败：500 m 距离下实际行为为 `move_to`，预期 `hold_position`。既有系统测试分别覆盖 red breach、无交战 timeout 和 Gym 精确 `info`，在修复前均失败。

聚焦回归结果：11 passed，2 warnings，32.49s。覆盖冻结成功链、red breach、timeout、Gym 契约和 MD-AD 显式撞击。

T3 回归集合：

```text
tests/unit/policies/test_rule_agents.py
tests/determinism/test_md_int_001_matrix.py
tests/determinism/test_md_int_001_checkpoint_replay.py
tests/determinism/test_md_int_001_synchronous_order.py
tests/system/test_md_int_001_baselines.py
tests/system/test_md_int_001_gym.py
tests/integration/test_md_ad_002_ramming.py
```

结果：21 passed，2个第三方 warning，48.35s。

静态检查：

- Ruff（受影响源文件和测试）：通过；
- Mypy strict（`blue.py`、`md_int_001.py`、`benchmark.py`）：通过；
- `git diff --check`：通过。

## Code review

- 明确撞击仍由动作字段触发并由底层碰撞模型裁决；默认策略安全间距不会禁用后续智能体的自杀式撞击策略。
- 红方只改变导航目标高度，不改变保护区的二维裁决语义。
- 实时可视化继续从双边接口取得碰撞事件，Gym 兼容调用方不受影响。
- 本工作包未发现新增 P0/P1。

## Gate decision

RF-00R4 范围内问题已关闭，但 RF-00 总体仍为 NO-GO。全仓 mypy、Bandit、全量 pytest、覆盖率以及 RF-00 登记表中的其余 P1 尚未在本工作包执行或关闭；因此不得据此进入 RF-01。

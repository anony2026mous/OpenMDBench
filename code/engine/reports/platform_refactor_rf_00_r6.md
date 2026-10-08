# RF-00R6 AD2 swept-breach remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R6-AD2-SWEPT-BREACH
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-07：MD-AD-002 突防裁决只检查动力学推进后的当前距离，无法识别同一 tick 内进入后又离开8 km拒止区的扫掠路径。未进入 RF-01，未修改拒止区半径、突防阈值、动力学、武器、碰撞、评分权重或 frozen golden。

## Requirement and root cause

`docs/parse3/MD-AD-002_Three_Scenario_Requirements.md` 要求在动力学推进后锁存本 tick 新 breach，进入8 km区域即不可逆计数。当前 `MDAD002Adjudicator.latch_breaches()` 仅比较实体 tick 末端位置与保护点的距离。

常规向中心飞行会被末端检测捕获，但公共动作允许改变航向；浅弦路径可以在一个 tick 内短暂进入圆区且两个 tick 端点均位于圆外，因此原实现并不等价于“本 tick 进入”。

## Remediation

- 环境在同步动力学推进前保存的 `previous_positions` 继续传入任务裁决阶段；
- AD2 裁决器计算本 tick 水平运动线段到保护点的最短距离；
- 最短距离不大于既有8 km半径时锁存 breach；
- 没有前态位置的直接调用仍退化为原有端点判断；
- checkpoint 结构不变：扫掠判断在当前 tick 内完成，既有 `breached_ids` 继续保存不可逆结果。

## Test-first evidence

新增测试构造两个端点均在8 km外、线段中部进入圆区的浅弦路径。实现前调用因不支持 `previous_positions` 失败；实现后正确产生 `breach_latched`。

## Verification

指定 T3 集合：

```text
tests/unit/missions/test_md_ad_002_adjudication.py
tests/integration/test_md_ad_002_ramming.py
tests/determinism/test_md_ad_002_easy_checkpoint.py
tests/system/test_md_ad_002_easy.py
tests/system/test_md_ad_002_medium.py
tests/system/test_md_ad_002_hard.py
```

结果：30 passed，1个第三方 Taichi deprecation warning，323.40s。

静态检查：

- Ruff（受影响实现和测试）：通过；
- Mypy strict（受影响实现和测试）：通过；
- `git diff --check`：通过。

## Code review

- 扫掠判定使用同步推进前后的正式 WorldState 坐标，不依赖策略或感知真值映射；
- 只比较水平距离，保持既有任务拒止区语义；
- 端点位于边界、静止实体和旧直接调用行为保持兼容；
- 三难度正式结果和 MEDIUM frozen fixture 均通过；
- 同 tick 显式撞击与突防锁存回归通过；
- 本工作包未发现新增 P0/P1。

## Gate decision

RF-00B P1-07 可标记为 CLOSED。其余历史 P1 仍需逐项复现或审查；全仓 Ruff/mypy/Bandit/full pytest/coverage 属 T4，未包含在本工作包授权内。因此 RF-00 总体继续为 NO-GO，RF-01 仍不得开始。

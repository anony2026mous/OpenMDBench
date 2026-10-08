# RF-00R8 REST AD2 replay completeness report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R8-REST-AD2-REPLAY
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-10：REST 的 MD-AD-002 `RedActionBatch` 路径推进仿真但不写 replay 帧。未进入 RF-01，未修改动作、动力学、通信、裁决、评分、配置或 frozen golden。

## Root cause and remediation

`SessionStore.step()` 在每次旧运动动作后调用统一 `_write_replay_frame()`，而 `step_action_batch()` 只更新会话和 audit 后立即返回。因此 REST AD2 replay 永远只有 session 创建时的 tick 0 帧。

修复后 action-batch 路径：

- 每次成功推进写入一帧；
- 记录序列化后的 `red_action_batch`；
- 复用运行时事件、实体、探测和得分 DTO；
- 终局帧包含 `session_ended` 并关闭 writer；
- 支持没有 `entity_id` 的全局 weather/jamming 等运行时事件。

## Test-first evidence

新增测试创建带 replay 目录的 EASY REST 会话并提交一个合法动作批次。实现前仿真推进到 tick 1，但 replay timestamps 只有 `[0]`，预期 `[0, 1]`。

首次接线后进一步暴露全局运行时事件使用必选 `record["entity_id"]` 的潜在 KeyError；按 `VisualizationEvent.entity_id: str | None` 契约修正后完整通过。

## Verification

指定测试覆盖 AD2 REST、MD-INT REST、出生事件 replay 和 VisualizationFrame schema：8 passed，1个第三方 warning，13.99s。

静态检查：Ruff 通过；受影响文件 mypy strict 通过；`git diff --check` 通过。

## Gate decision

RF-00B P1-10 可标记为 CLOSED。P1-09 已确认是七项需求权重与三项 v2 配置的版本分叉，需要版本化配置迁移，不能在 RF-00 中静默改写配置哈希或 golden。RF-00 总体继续为 NO-GO。

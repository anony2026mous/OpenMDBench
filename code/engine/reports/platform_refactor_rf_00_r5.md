# RF-00R5 MD-INT terminal wiring remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R5-MDINT-TERMINAL-WIRING
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-08：MD-INT-001 裁决器已有 `all_interceptors_unavailable` 结果，但环境主循环从未向裁决器传入该条件，导致正式仿真中不可达。未进入 RF-01，未修改武器、碰撞、动力学、任务时间、保护半径、评分权重或冻结 golden。

## Requirement

`docs/parse2/MD-INT-001_Vertical_Slice_Requirements.md` 第12.1节规定：两架蓝方 UAV 均为 `destroyed/crashed/offline`，且岸基近防无法交战时，锁存 `all_interceptors_unavailable`。

实现严格按该集合判断 UAV 生命周期。岸基近防仅在自身生命周期可用、武器组件可用且仍有 `shore_ciws` 弹药时视为能够交战。

## Test-first evidence

新增环境接线测试在实现前失败：测试将两架蓝方 UAV 和岸基近防置为 destroyed，调用正式任务结果更新后仍得到 `in_progress`，预期 `red_success/all_interceptors_unavailable`。

修复后增加反例：两架 UAV 不可用但岸基近防仍可交战时，任务必须保持 `in_progress`。

## Verification

聚焦回归覆盖环境接线、裁决优先级、冻结基线、检查点续跑和 MD-AD 显式撞击：15 passed，1个第三方 warning，33.99s。

指定 T3 集合覆盖：

```text
tests/integration/test_md_int_001_adjudication_wiring.py
tests/unit/missions/test_md_int_001_adjudication.py
tests/determinism/test_md_int_001_matrix.py
tests/determinism/test_md_int_001_checkpoint_replay.py
tests/determinism/test_md_int_001_synchronous_order.py
tests/system/test_md_int_001_baselines.py
tests/system/test_md_int_001_gym.py
tests/integration/test_md_ad_002_ramming.py
```

结果：19 passed，2个第三方 warning，49.57s。

静态检查：

- Ruff（受影响实现和新增测试）：通过；
- Mypy strict（受影响实现和新增测试）：通过；
- `git diff --check`：通过。

## Code review

- 条件从正式 WorldState 计算，不依赖策略私有状态或未授权真值视图。
- UAV 不可用状态没有泛化到 scheduled、impacted、out-of-bounds 等需求未列出的生命周期。
- 岸基近防可用反例防止仅凭 UAV 损失过早终止任务。
- 既有 breach、threat destroyed、timeout 的裁决顺序与实现保持不变。
- 本工作包未发现新增 P0/P1。

## Gate decision

RF-00B P1-08 可标记为 CLOSED。其余历史 P1 仍需逐项复现或审查；全仓 Ruff/mypy/Bandit/full pytest/coverage 属 T4，尚未获得本工作包的明确授权。因此 RF-00 总体继续为 NO-GO，RF-01 仍不得开始。

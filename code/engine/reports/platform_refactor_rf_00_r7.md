# RF-00R7 AD2 spawn-order stability report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R7-AD2-SPAWN-ORDER-STABILITY
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-11：MD-AD-002 出生描述符编译依赖配置中 `waves` 的序列化顺序，导致等价的具名波次配置可以改变实体身份、RNG 消耗和出生参数。未进入 RF-01，未修改波次数量、出生时间、抖动范围、区域、速度、武器、裁决、评分或 frozen golden。

## Root cause

出生执行阶段已经按实体 ID 稳定排序，但 `_build_md_ad()` 直接遍历 `config.waves`，并在遍历过程中：

- 分配 `blue-striker-uav-NN`；
- 顺序消费 timing/position/altitude RNG；
- 绑定 wave ID、区域和行为。

因此仅反转同一组具名波次，就会使 `blue-striker-uav-01` 从 wave-1 变成 wave-3，并重排后续随机样本。

## Remediation

编译前按 `(time_seconds, wave.id)` 规范化具名波次顺序。当前三个正式 YAML 原本就是该顺序，因此既有正式结果不变；配置解析、哈希和验证逻辑保持不变。

## Test-first evidence

新增测试先创建 MEDIUM 基线运行时，再通过 loader 注入仅反转 `waves` 序列的等价配置。实现前测试失败，首个实体的 wave ID、scheduled tick 等字段不同；实现后完整 `scheduled_entities` 相同。

## Verification

指定 T3 集合覆盖：

```text
tests/integration/test_md_ad_002_waves.py
tests/contract/test_scenario_runtime.py
tests/contract/test_md_ad_002_config.py
tests/determinism/test_entity_registration_order.py
tests/determinism/test_md_ad_002_easy_checkpoint.py
tests/system/test_md_ad_002_easy.py
tests/system/test_md_ad_002_medium.py
tests/system/test_md_ad_002_hard.py
```

结果：55 passed，1个第三方 Taichi deprecation warning，332.97s。

静态检查：

- Ruff（受影响实现和测试）：通过；
- Mypy strict（受影响实现和测试）：通过；
- `git diff --check`：通过。

## Code review

- 生产改动仅为波次规范化排序；
- 当前三个正式配置及 frozen 轨迹保持不变；
- RNG 仍使用原有具名子流，seed 语义不变；
- 出生执行、事件顺序和 checkpoint 恢复测试通过；
- 配置顺序不再成为未声明的随机输入；
- 本工作包未发现新增 P0/P1。

## Gate decision

RF-00B P1-11 可标记为 CLOSED。其余历史 P1 仍需逐项复现或审查；全仓 Ruff/mypy/Bandit/full pytest/coverage 属 T4，未包含在本工作包授权内。因此 RF-00 总体继续为 NO-GO，RF-01 仍不得开始。

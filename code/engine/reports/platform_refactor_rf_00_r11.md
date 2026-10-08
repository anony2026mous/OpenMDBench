# RF-00R11 MD-INT contact legalization report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R11-MDINT-CONTACT-LEGALIZATION
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-02：MD-INT 交战通过 contact 估计位置选择最近敌方真值实体，未关联的 legacy/contact 在多目标候选下可能被错误合法化。未进入 RF-01，未向公开 Observation/Event 增加真值 ID，未修改武器概率、射程、伤害或 frozen baseline。

## Remediation

- DetectionEngine 提供仅供内部裁决使用的 active contact→truth association；
- 环境在交战合法性阶段聚合内部 association 并选择唯一关联实体；
- 场上只有一个域匹配敌方候选时保留旧单目标兼容；
- 多候选且 association 缺失或冲突时拒绝，拒绝码稳定为 `contact_not_owned`；
- 公开 Contact、阵营观察和公开战斗事件仍不包含 truth ID。

## Test-first evidence

新增测试注入一个未关联 contact 和两个敌方 UAV。实现前动作被合法化并消耗1枚弹药；修复后弹药、能量和 RNG 不发生交战副作用，并返回 `contact_not_owned`。

## Verification

传感器、MD-INT combat/detection、冻结基线、确定性矩阵、checkpoint 和 AD2 撞击回归：24 passed，1个第三方 warning，48.01s。

静态检查：Ruff 通过；受影响文件 mypy strict 通过；`git diff --check` 通过。

## Gate decision

RF-00B P1-02 可标记为 CLOSED。RF-00 总体继续为 NO-GO，通信/配置分叉、MMG 隔离和七项权重版本迁移仍需处理或形成门禁决议。

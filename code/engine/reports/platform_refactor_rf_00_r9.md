# RF-00R9 AD2 energy-profile remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R9-AD2-ENERGY-PROFILE
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-01：MD-AD-002 使用了引擎通用/MD-INT 能耗档案，而非任务需求冻结的 UAV/USV 速度和续航点。未进入 RF-01，未改变 MD-INT 能耗、AD2 配置哈希、武器、裁决、评分或 golden。

## Root cause and remediation

原通用档案为 UAV 40/80m/s、60/30min，USV 7.7/12.9m/s、24/8h；AD2 需求规定 UAV 25/60m/s、40/15min，USV 6/12m/s、8/3h。

新增 `AD2_ENERGY_PROFILES`，复用原有分段归一化算法、传感/中继/交战附加消耗和终态语义，只替换 AD2 明确冻结的速度/续航点。环境仅在正式 runtime 含 `md_ad_config` 时选用该档案；MD-INT 和其他场景继续使用 `ENERGY_PROFILES`。

## Test-first evidence

测试先导入并断言 AD2 四个续航标定点；实现前因 `AD2_ENERGY_PROFILES` 不存在而在收集阶段失败。实现后增加环境接线测试，确认 EASY 正式 world step 的主 UAV 实际使用 AD2 档案。

## Verification

指定测试覆盖能耗单元、AD2 接线、MD-INT frozen baseline 和 AD2 三难度正式系统轨迹：31 passed，1个第三方 warning，324.32s。

静态检查：Ruff 通过（一次机械导入排序后复跑）；受影响文件 mypy strict 通过；`git diff --check` 通过。

## Code review

- 场景专用参数没有覆盖或修改通用全局档案；
- AD2 最大 UAV/USV 速度均在新档案包线内；
- 能量耗尽后的 crashed/drifting 语义不变；
- 三难度正式结果与 MEDIUM frozen golden 通过；
- 本工作包未发现新增 P0/P1。

## Gate decision

RF-00B P1-01 可标记为 CLOSED。RF-00 总体继续为 NO-GO，剩余 P1 和门禁继续处理。

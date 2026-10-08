# RF-00R10 open-shoreline physics remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R10-WEIHAI-OPEN-SHORELINE
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包复现并关闭 RF-00B P1-06：威海地图的开放海岸折线在物理碰撞分段中被隐式首尾闭合，产生源数据不存在的长距离虚假岸线。未进入 RF-01，未修改地图源文件、地图哈希、坐标变换、场景参数或 golden。

## Root cause and remediation

可视化层已明确保留110条开放折线，但 `GeoFrame.coastline_segments` 对每条路径使用 `index-1 -> index` 且从 index 0 遍历，因此额外生成 `last -> first` 边。

修复后只生成相邻源点 `index-1 -> index`（index 从1开始）。开放路径不再封口；源数据本身首尾点相同的闭合路径仍通过最后一个相邻点保留闭合边。

## Test-first evidence

新增测试选取端点相距超过12 km的 source coastline 130，断言物理 segments 不包含其 `last -> first` 人工边且所有真实相邻边存在。实现前测试失败并精确显示该人工边存在。

## Verification

地图语义、坐标、AD2 波次/出生、MD-INT world、MD-INT frozen baseline 和 EASY 系统轨迹：33 passed，1个第三方 warning，93.20s。

静态检查：Ruff 通过；受影响文件 mypy strict 通过；`git diff --check` 通过。

## Gate decision

RF-00B P1-06 可标记为 CLOSED。RF-00 总体继续为 NO-GO，剩余 P1 和门禁继续处理。

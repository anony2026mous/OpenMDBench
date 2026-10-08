# ADR-MD3-004：封锁与占位的通用几何原语

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-05 Geography/Mission/Scoring

## 决策

新增需求只以通用、局部米制连续几何原语表达：`radial_crossing`、`sector_contains`、`annular_sector_occupancy_duration`、`front_of_track_occupancy`、`path_conflict`、`blocked_or_slow_duration` 和 `replanning_latency`。

每个原语必须接收圆心、半径、方位、距离、持续时间、容差和 debounce 等数据参数；所有判断使用 tick 起止的连续路径，输出可审计事实/event，不直接造成 health 改变。`interdiction_occupancy` 是任务/评分事件或碰撞风险信号，绝不是隐式强制停船。

## 依据与兼容

`GeographyServiceV2`、boundary swept crossing 和 mission 的 zone/event condition 可复用；P0、6 km、010–120°、50 m、5 s 只允许写进 Catalog/Scenario data。

## 验证义务

MD3-05 必须覆盖任意圆心、跨 0° 扇区、顺逆向 crossing、切线、高速跨越、不同注册顺序、duration/debounce 和无关合成场景复用。

U13 和占位阈值在冻结前为 `UNVALIDATED_BENCHMARK`。

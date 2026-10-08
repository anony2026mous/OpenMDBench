# MD-AD-002 AD2-03 阶段报告

## 结论

AD2-03“动态波次、实体生命周期和碰撞”完成。

## 实现

- 三份 YAML 配置独立定义东侧/东北侧出生区中心和采样尺度，解析后进入配置哈希。
- 使用场景命名的 `spawn_timing`、`spawn_position`、`spawn_altitude` RNG 子流。
- 蓝方固定 ID `01–15`，按 4/5/6 三波在 T=0、T=600±120、T=1200 激活。
- 出生点必须位于威海地图范围、水域上空和合法高度；重复 ID、陆地/地图外出生失败关闭。
- scheduled descriptor 在出生前不进入 WorldState；出生后稳定注册且不得二次使用 ID。
- 生命周期扩展 scheduled、breached_active、impacted、out_of_bounds、removed；终态实体作为 tombstone 保留。
- 接入边界、USV 上岸、UAV 撞地、实体接触和大步长 swept collision。
- 剩余波次、事件、实体与 MMG continuation state 进入 checkpoint；出生/终态事件进入 replay。

## 验证

- T=0/599/600/1200 数量边界及重复调用。
- MEDIUM/HARD 同 seed 重现、不同 seed 合法差异、Wave 2 位于 480–720。
- checkpoint 跨真实 T=600 `step()` 与连续运行完全一致。
- 非法出生与 swept collision 负路径。
- 三场景分别无策略运行至 1800 tick：每场景 22 个唯一实体、15 个蓝方实体、0 个剩余 scheduled descriptor，正常 timeout。
- AD2-03/AD2-02/MD-INT-001 定向回归通过；Ruff、mypy、`git diff --check` 通过。

独立审查见 `artifacts/review/md-ad-002-code-review-ad2-03.md`，P0/P1/P2/P3 均为 0。

## 边界

本阶段只负责真实状态生命周期与物理/几何事件。`breached_active` 的 8 km 裁决锁存、毁伤语义和评分分别在 AD2-05 及后续阶段完成；传感器与 contact 不在本阶段实现。

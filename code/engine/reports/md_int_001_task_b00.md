# I001-B00：威海世界与统一 GeoFrame 接入

- 状态：PASS
- 地图：`weihai_v1` / `1.0`
- 正式回退策略：无；文件缺失或任一 SHA-256 不一致即失败

## 调用证据

`OpenMDBenchEnv(MD-INT-001)` 加载冻结配置，调用 `load_weihai_geoframe` 校验两份地图并建立
WGS84_AEQD 真米制局部坐标。受控初始点和目标点已由冻结 WGS84 转为局部米，不再使用旧抽象坐标。
`GeoFrame` 集中提供 WGS84、local metre、legacy EPSG:3857/50+offset 三套双向转换；海陆与岸线
碰撞使用同一137多边形/7620顶点数据。

地图 identity 已进入环境配置哈希、导出状态、checkpoint import 校验和 ReplayMetadata。
map ID/version/hash/origin/scale/offset 任一不一致均不允许恢复或静默空白回放。

## 数值与测试

- WGS84 往返门槛：`<=1e-7 deg`，通过。
- local/map/local 往返门槛：`<=1e-3 m`，通过。
- 25 km及5 km控制线的局部距离相对WGS84测地距离：`<=0.5%`，通过。
- offset 非零正反转换、NaN/Inf、负scale、错误hash负向测试通过。
- 雷达陆地点产生海岸碰撞；冻结USV水域点不碰撞。
- checkpoint和replay使用相同 map identity。

专项回归：11 passed；包含旧坐标基线与checkpoint/replay扩展回归时为19 passed。Ruff和strict mypy通过。

## 边界

B00只建立世界坐标和岸线约束能力。五实体注册、USV MMG实际逐tick调用和地图碰撞后的任务事件分别属于
B01/B03及后续任务，未在本任务中提前宣称完成。

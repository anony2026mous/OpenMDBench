# MD-AD-002 AD2-02 阶段报告

## 结论

AD2-02“配置驱动的通用世界构建与主循环”已完成。MD-INT-001 与 MD-AD-002 三个难度均通过 `ScenarioRuntime` 注册表创建，不再由环境构造器按场景 ID 特判。AD2 三场景目前各构建 7 个红方正式实体，并保存 15 个尚未生成的稳定波次实体描述。

## 主要实现

- 新增 `openmdbench/scenarios/runtime.py`，统一承载世界、GeoFrame、配置/规则元数据、主兼容实体、保护点和 scheduled descriptors。
- 抽出 MD-INT-001 世界构建，保留旧传感器、通信、战斗和裁决行为。
- 三个 AD2 场景共享同一个配置驱动工厂；难度差异不进入核心主循环分支。
- 所有正式部署使用威海地图哈希、统一参考原点和 AEQD 本地米制坐标；岸基/USV 执行实际海陆检查。
- 实体遍历、注册、日志和 adapter 保存使用稳定 ID 顺序。
- MMG 状态从单个共享 adapter 改为按会话、按 USV 隔离，并支持 checkpoint snapshot/restore。
- checkpoint、audit 和 replay metadata 记录地图身份、参考原点、坐标约定、配置哈希、配置版本和规则版本。
- AD2 正式运行时按 1800 tick 超时，不再继承旧占位场景的 5400 tick。

## 验证

- AD2-02 契约覆盖：四场景构建、同 seed 初态、7+15 结构、地图海陆、会话隔离、无难度 ID 分支、checkpoint 防篡改、MMG 精确续跑。
- MD-INT-001 回归覆盖：五实体推进、稳定注册顺序、Gym、REST、CLI、checkpoint/replay。
- 全量 `tests` 执行返回成功。
- Ruff：通过。
- mypy（受影响模块）：通过。
- `git diff --check`：通过。

## 能力边界

本阶段的“15 个蓝方实体”仍是不可见 scheduled descriptor，尚未动态注册到世界；波次出生、时间抖动、碰撞和完整生命周期属于 AD2-03。本阶段也不宣称 AD2 感知、通信、武器、裁决或多实体公共 ActionBatch 已完成。

## 审查

独立审查报告：`artifacts/review/md-ad-002-code-review-ad2-02.md`。P0/P1/P2/P3 均为 0；审查期间发现的 MMG 串扰和 REST checkpoint 表示差异已修复并回归。

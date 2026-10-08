# MD-INT-003 可视化、回放与检查点记录

## 范围与结论

MD3-09 完成了三档场景共用的 live frame、回放、视图隔离和检查点续跑契约验证。结果为 `DONE`：帧构建为只读操作，不推进 authority tick；同一 seed、session 和动作时间线的 live/replay referee frame 相同；高海况条件下从检查点恢复后，后续丰富帧与连续运行逐字段相同。

本阶段没有添加场景、faction 或 entity-ID 分支，也没有让 renderer 改变仿真状态。

## 视图和帧边界

- `presentation_snapshot()` 是专门供帧构建读取的小型不可变快照，不构造可恢复 checkpoint，也不写文件；完整权威账本仍由世界在对局结束前保存在内存中。
- `destroyed`/`despawned` 生命周期不会出现在任何视图的可显示实体集合中，因此受毁实体不会继续留在地图上。
- referee 可读取本 tick 的权威事件和通信审计信息。faction/public 帧只保留已声明的全局天气与区域激活状态，且事件集合为空；原始事件调度状态、消息载荷、触发器配置、组件抑制目标和攻击方标识均不输出。
- faction 的实体、传感器/武器覆盖与通信连线仅在双方端点均属于该 faction 时显示；public 只显示显式 `public` 标签实体。
- 默认镜头从声明的非 terrain 任务区域几何计算，并加上通用留白；不再直接使用可覆盖完整威海源地图的百万米坐标框。该镜头只依赖静态、公开的场景几何，故 referee/faction/public/live/replay 的同 tick 取景相同，不会把隐藏实体的实时位置编码为镜头变化。没有任务几何时才回退到坐标框或固定安全默认值。

## 检查点续跑修正

审计发现两个通用续跑缺口，均非 MD-INT-003 专用逻辑：

1. MMG worker 过去把 Taichi 内部 float32 弧度航向转换为公开角度后才快照；恢复时再反向转换，造成下一个积分步的舍入漂移。快照现保留 `heading_math_rad`，恢复时将该求解器原始角度直接写回；老快照若没有该字段仍可恢复，但使用旧的角度换算路径，不能获得本次新增的逐字段续跑保证。
2. mission fact 过去按账本字典插入次序折叠事件；检查点 restore 会以规范化 operation ID 顺序重建该字典，导致超过双位 tick 的等价世界得出不同 fact hash。现按 `(start_tick, tick, operation_id)` 明确排序。

这两个字段均在通用、受哈希保护的原生/世界快照内，未改变场景数据或真实装备参数。

## 测试证据

所有命令均使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 和 `MPLCONFIGDIR=/tmp/openmdbench-mpl`：

| 验证 | 结果 |
|---|---|
| 修改模块 `py_compile` | 通过 |
| 转向 MMG 的生产 worker 快照/恢复精确续跑 | `1 passed in 5.06s` |
| `tests/system/test_md_int_003_visualization.py`：非推进、faction/public 无真值泄露、live/replay、L3 高海况 checkpoint | `3 passed in 115.70s` |
| 相邻 T3：`test_native_dynamics_adapter_v2.py`、`test_md_int_003_interfaces.py`、`test_md_int_003_scenarios.py`、`test_md_int_003_visualization.py` | `58 passed in 267.95s` |
| MD3-09-002 task viewport：MD-INT-003 三种 view 的同一静态任务视野、live/replay/checkpoint 回归 | `4 passed in 66.62s` |
| 通用 formal renderer 回归 | `tests/system/test_md_ad_002_v2_visualization.py`: `13 passed in 59.14s` |
| 三档 ScenarioPackage/规则策略回归 | `tests/system/test_md_int_003_scenarios.py`: `6 passed in 17.93s` |

高海况用例在 L3 环境事件生效后创建 checkpoint，并将连续运行与恢复运行随后两 tick 的 defender frame JSON 作全量相等比较。测试也断言 faction/public 帧不含攻击方 ID、无事件收据，且 view 构建前后 tick 相同。

## 代码审查与边界

结构化自审结论：未发现新增 P0/P1。修复使用通用 snapshot 状态、稳定排序和声明几何；视图侧采用白名单而非过滤黑名单，避免新增 event dispatcher 字段时意外泄露。任务视野不读取 live entity state，避免在 faction/public 视图侧暴露敌方机动。现有 visual profile ID 仅增加到通用形状别名映射，未改变 Catalog。

未运行 T4/T5、30-seed 统计或并发压力测试。所有 Catalog 场景数值仍为 `UNVALIDATED_BENCHMARK`；本记录不作真实装备标定或实时性能结论。

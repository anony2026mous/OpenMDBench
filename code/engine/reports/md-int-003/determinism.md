# MD-INT-003 系统确定性与防泄漏记录

## 结论

MD3-10 状态为 `DONE`。三档在相同 seed 与相同公开操作时间线下，即使使用不同 session ID，去除仅用于溯源的 `VisualizationFrame.session_id` 后，逐 tick referee 权威帧语义相等。Lockstep 与 Continuous 会话通过同一显式步进时间线得到相同帧；1×、10×和 1000× headless live 回放帧也相同。未发现需要修改生产机制的确定性、防泄漏或伪造输入缺口。

## 运行锚点

- 引擎/schema：`2.0.0/2.0`；插件：`none`。
- Catalog：`sha256:c070a2cc0540b1deb37db6375149acbc7304b929927708dbc0cf8d6f0bb7caf9`。
- map：`map.weihai-local@2.0.0`，源数据 `sha256:1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675`。
- resolved：L1 `sha256:0092d1d741def7237ae01c8333024746a9ed6e734a9078c9f917322288769ba5`；L2 `sha256:7138184abbae2def40ac6a596b9743ec2328c59293b709a222d92d6d3819ef83`；L3 `sha256:f76536982aa0feeb4b252ac9d3a7e9e9905922428bc2604f404f0b1404175395`。
- 主验证 seed 为 `73`；seed 变更验证为 `74`。执行环境为 Python 3.11.15、Taichi 1.7.4 的本地隔离 worker。

## 新增外部行为契约

`tests/determinism/test_md_int_003_system_determinism.py` 验证：

- L1/L2/L3 各自以同一 seed、同一操作 ID 时间线在两个不同 session ID 中运行三 tick；仅忽略 frame 的 session 溯源字段后逐帧相等。
- Lockstep 与 Continuous 在相同显式 tick 调用下逐帧相等。复用同一个 session ID 与操作时间线、只把 seed 从 73 改为 74 时，session/world checkpoint 内的 seed 和 checkpoint hash 都改变。
- 1×、10×、1000× headless live replay 与无 renderer 的直接 Session、以及每 tick 三次只读 observation 轮询，产生相同 authority frame；轮询不会推进 tick。
- referee、defender、attacker、public 四个视角的实体集合、事件集合和 environment 白名单符合权限边界；faction 视图没有对方 faction 标识。
- 伪造 session checkpoint 的 seed 即使重新计算外层 hash 也会被拒绝，原会话 tick 和 gateway 会话集合不改变。
- 对 `api/combat/dynamics/missions/replay/sessions/sdk/systems/visualization/world` 通用生产目录扫描，不存在 `MD-INT-003`、固定 red/blue USV fixture 或 `scenario_id ==` 分支。

跨 session 比较有意保留实际 frame/replay 中的 `session_id`，仅在等价断言中删除它：该字段是可追溯上下文而不是仿真输入，不能把两个独立会话误判为同一记录。

## 测试证据与失败分类

| 命令类别 | 结果 |
|---|---|
| 新增 MD3-10 确定性/视图/伪造 checkpoint 契约 | `8 passed in 218.30s` |
| 强化后的同 session ID、仅变 seed 契约 | `1 passed in 47.32s` |
| 相邻 T3：Catalog、surface combat、damage lifecycle、mission geometry、environment/communication、接口、三档场景、可视化、native/world checkpoint | `92 passed in 266.75s` |
| `py_compile` 与 scoped `git diff --check` | 通过 |

首轮新增测试有 4 项失败，分类为 **测试语义错误**，不是实现或非确定性：断言直接比较了不同 session 的完整 frame，其中 `session_id` 按设计不同。修正为只比较权威语义后单次完整运行通过；未使用 flaky 重跑、未扩大任何数值容差。

## 审查、兼容性与边界

本阶段结构化自审为 `SELF_REVIEWED`：审查了 session ID/seed 输入、runner mode、frame 构建、回放读取、checkpoint anchor 和静态专用分支扫描，未发现 P0/P1。新增的只是外部测试和报告；不改变 DTO schema、Catalog、ScenarioPackage 或生产行为。

本阶段没有 T4/T5 授权，因此未执行全量 pytest、format/Ruff/mypy/Bandit、16/32 并发、100 局、30-seed 统计、内存/Artist 长稳或 GUI 墙钟性能测量。headless 速度测试证明 authority 结果不因配置速度而变，并不宣称达到真实 GUI 端到端倍率。所有 benchmark 参数仍为 `UNVALIDATED_BENCHMARK`。

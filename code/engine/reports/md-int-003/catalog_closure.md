# MD3-02 Catalog 闭包报告

## 结论

MD-INT-003 已具备独立、版本化的 Catalog 资源闭包；它不包含场景包、固定
实体 ID、场景名分支或任何可变会话状态。Catalog 解析、依赖闭包、原生动力学
绑定和五类平台的完整组件组合均通过定向验证。

## 执行记录

| 字段 | 记录 |
| --- | --- |
| TASK_ID / 阶段 | `MD3-02-001` / `MD3-02` |
| 时间 | `2026-09-02T12:35:46+08:00` |
| 分支 / 基线 | `refactor` / `e85523f` |
| 引擎 / Schema | `2.0.0` / `2.0` |
| 场景哈希 | `N/A`；本阶段按计划禁止创建 `ScenarioPackage` |
| Catalog 哈希 | `sha256:278377eedacd2fc1e93e10c51edf755f26b1b052eaa9b187afdb5f4624fcc24f` |
| Catalog 文件 SHA-256 | `d32e238d47e8a494b4012a42e5cb67411be34f856a2697366a2307086644776b` |
| 注册表哈希 | `sha256:573277d4e4495e4b6a22c9cb33fbdbe0fb70020925d8c717009ac503e91af69a` |
| 地图 | `map.weihai-local@2.0.0`；原始数据哈希 `sha256:1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675` |
| 插件 / seed | `none` / `N/A`（Catalog 阶段没有会话） |
| 环境 | Ubuntu；Python `.venv/bin/python`；`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`；`MPLCONFIGDIR=/tmp/openmdbench-mpl` |

## 范围和文件

- 新增 [资源 Catalog](../../catalog/v2/md_int_003.yaml)：51 个精确
  `id@version` 资源，覆盖地图、平台、MMG/UAV/固定动力学、外形、显示、传感器、
  通信、能源、武器/弹药/效果/毁伤、载荷、环境、任务模板和评分模板。
- 新增 [Catalog 闭包测试](../../tests/contract/test_md_int_003_catalog_closure.py)：
  资源类型和 ID、威海地图重用、动力学绑定、五类实体组合、超槽/目标域拒绝、可变状态
  拒绝、跨加载实例隔离。
- 无运行时、Schema、场景注册、任务 ID 分支或现有文件修改。

## 关键设计和兼容性

1. `surface` 只作为通用目标域；平台名称为资源类型，不是场景或固定实体 ID。
2. 威海地图的 `raw_sha256`、地形来源和可视化来源逐字段复用现有
   `map.weihai-local@2.0.0`；本 Catalog 仅补充来源/可信度元数据。
3. 所有 V4 功能参数使用 `parameter_source: MD-INT-003-V4` 和
   `fidelity: UNVALIDATED_BENCHMARK`。地图重用标为 `VERIFIED_REUSE`。
4. `dynamics.*` 仅把 V2 原生接口认可的参数交给执行模型。防御/攻击 USV 的运行
   上限均为已验证的 12.9 m/s；V4 请求的 15/18 m/s 分别保留为
   `benchmark_requested_max_speed_mps`，不会被误当作可执行 MMG 能力。
5. `impact_delay_ticks: 1`、contact detonation、secondary effect 和环境/通信字段
   是不可变定义数据；其通用运行时语义将由 MD3-03 至 MD3-06 逐阶段实现。
6. Catalog 校验器拒绝 `health`、`pending_*`、`rng_*` 等可变状态，保证资源定义
   不能成为跨对局状态载体。

## 验证

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/contract/test_md_int_003_catalog_closure.py \
  tests/contract/test_catalog_registry_v2.py
```

结果：`52 passed in 1.11s`（新增 MD3-02 测试 13 项，既有 Catalog 注册表测试 39 项）。

另执行了 Catalog 直接加载与哈希输出（成功，51 resources），以及：

```text
git diff --check -- catalog/v2/md_int_003.yaml \
  tests/contract/test_md_int_003_catalog_closure.py reports/md-int-003
```

结果：无空白错误。

开发中首次解析发现两个新文件录入错误：一个资源漏写 `resource_type`，以及
`current_speed_mps` 被 Catalog 运行时状态防线正确拒绝。前者补齐，后者改为静态
环境定义字段 `water_current_speed_mps` 后才开始正式测试；两项均为本阶段新增数据的
即时修正，不是已有基线回归。

## 领域审查

- 资源依赖链完整：平台→能源/外形/显示，载荷→武器/弹药，武器→效果→毁伤。
- 五个可组合平台为防御拦截 USV、攻击自爆 USV、ISR UAV、岸基水面雷达和中立民船
  USV；最后一类验证通用 faction 机制可承载中立实体，未引入第三套阵营实现。
- Catalog 不声称已经实现雷达噪声、航迹融合、通信时延、环境修正、自爆或殉爆；这些
  值均仅作为可追溯定义，由后续通用机制消费。

## 风险和后续

| 项目 | 分类 | 处置 |
| --- | --- | --- |
| V4 的 15/18 m/s USV 指标超过当前 MMG 已验证边界 | `UNVALIDATED_BENCHMARK` | 保持可追溯目标值；不得在未扩展/校准 MMG 前宣称实现。 |
| Catalog 对通用数据字段没有完整维度类型系统 | 既有 V2 限制 | 本阶段采用 SI 后缀、来源和可信度字段；MD3-06 以运行时契约测试覆盖被消费字段。 |
| `delayed_effect`、contact detonation 和 secondary effect 仍无执行机制 | 计划内缺口 | MD3-03/04 在统一 Effect/DamageIntent 路径实现。 |
| 地图几何点位、切线与高速跨越尚未形成场景夹具 | 计划内缺口 | MD3-07 创建 data-only 场景后，由 MD3-10 验证。 |

下一阶段：MD3-03，仅补充通用 surface combat 的 Schema/Compiler/World 接线和证据链；
不得把上述资源做成 MD-INT-003 专用运行时分支。

## MD3-02-002：三档感知与 UAV 通信资源回补

MD3-07 的只读资源审计发现，三个待编译场景此前共用了同一套传感器资源，且 UAV
错误复用了 20 km 水面战术网。依照阶段边界，本回补只修改 Catalog 和其契约测试：

- 增加六类传感器各三份不可变 `@2.1.0` / `@2.2.0` / `@2.3.0` 档案。它们分别定义
  V4 的 8/4/12/6/20/3 km 距离、`0.95/0.88/0.80` Pd、±5/8/10% 距离噪声、
  ±1/2/3° 方位噪声、报告周期和雷达/EO 高海况距离倍率。
- 保留所有已有 `@2.0.0` 资源不变，新增 `communication.defender-surface-tactical@2.1.0`
  （20 km、最多 2 跳）和仅兼容 UAV 的
  `communication.defender-uav-surface-tactical@2.1.0`（50 km、最多 2 跳）。
- 全部新参数保持 `MD-INT-003-V4` / `UNVALIDATED_BENCHMARK`。它们是 benchmark
  配置，不构成真实装备标定主张。

验证命令为 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl
.venv/bin/python -m pytest -q tests/contract/test_md_int_003_catalog_closure.py
tests/contract/test_catalog_registry_v2.py`，结果 `56 passed in 1.91s`；Catalog 直接加载
为 71 个资源，content hash 为
`sha256:7b78ab0877afcfb7ca25a9ff5ced52cce9895188a996ff16d9da7316a3e57413`，文件 hash 为
`dafe1a27486a73c27786dd458c0270d9847afb30f0886929e36709ce95390f25`；定向 diff
检查无空白错误。

该回补通过 Catalog 闭包验收，但不把“字段已入库”误记为“量测噪声已经生效”。
审计发现 generic subsystem 尚未消费 `range_noise_fraction`、`bearing_noise_deg` 和
`update_ticks`；必须先回到 MD3-06 实现通用、命名子流的消费逻辑，再恢复 MD3-07。

### MD3-02-003：融合门限闭包

在 MD3-06 开始实现前，进一步确认“连续 2 帧确认、3 s stale、0.70 交战置信度、
10 s 最大交战航迹年龄”也不能作为 MD-INT-003 专用内核常量。因此为所有新三档
传感器档案补全 `confirmation_frames: 2`、`stale_after_ticks: 3`、
`minimum_contact_confidence: 0.70` 和 `engagement_max_age_ticks: 10`。

同一组 Catalog 闭包测试再次通过 `56 passed in 1.95s`，直接加载得到 71 个资源；
最终本轮 Catalog content hash 为
`sha256:18ec40f5e3c9f05e990f677f68f467bf76cf39e56da3786f71f9d635592cc723`，文件 hash 为
`fc83a172aa32f579a67865cff33498d732f7e993e07b0ea4bd73284bc1959d31`，定向 diff
检查无空白错误。资源仍完全不含会话可变状态、场景 ID、faction ID 或实体 ID。

### MD3-02-004：高海况版本资源闭包

保留旧 `environment.md3-high-sea@2.0.0` 不变，新增
`environment.md3-high-sea@2.1.0`。新资源将 V4 的 USV 速度 `×0.70`、武器 Pk
`×0.80`、推进功耗 `×1.30` 和通信丢包 `+0.05` 明确写成数据；
`sensor_profile_multiplier_keys` 把 `sensor.range` 与各传感器档案的
`high_sea_range_multiplier` 连接，使雷达 `×0.75`、EO/IR `×0.70` 无需平台或
场景身份判断。

本次 Catalog 定向测试 `57 passed in 2.12s`，72 个资源；content hash 为
`sha256:c070a2cc0540b1deb37db6375149acbc7304b929927708dbc0cf8d6f0bb7caf9`，文件 hash
为 `70b6367ec712f4401f55fce3a47d6d1b8696155b6687591efee1950cb3b4d434`。字段仍标记
`UNVALIDATED_BENCHMARK`；其通用运行时消费由 MD3-06-002 负责。

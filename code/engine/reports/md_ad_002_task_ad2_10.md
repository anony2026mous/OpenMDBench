# AD2-10 HARD 纵向闭环完成报告

## 结论

`MD-AD-002-HARD` 已达到 AD2-10 E2：环境事件、持续规避、通信退化、任务级 USV 压制、成功/失败/超时裁决、评分、日志、检查点、公开视角和可视化形成闭环。至此 EASY、MEDIUM、HARD 三个独立场景均具备可运行和可验收产品面；发布级性能、32 并发、100 局和长稳门禁仍属于 AD2-11。

## 已实现能力

- tick 900 通过 `hard_weather` 具名 RNG 等概率选择 `light_rain/fog`，未到期不消费子流；
- tick 900 海况从 2 升至 4，仅使 USV 雷达 Pd 乘 0.8；天气按冻结倍率影响雷达/EO；
- tick 900–1200 通信干扰继续与 AD2-09 的 USV 中继、延迟和恢复语义联动；
- 蓝方使用公开 Observation 执行多轴、持续、确定性蛇形，不访问红方私有信息；
- 蓝方 UAV 距 USV-1 不超过 5 km 时触发一次 90 tick E4 压制；
- 压制只关闭目标 USV 的传感器、通信、推进和武器组件，端点离线、速度归零；
- 到期恢复压制前的组件、生命周期和端点状态，不把原有损伤恢复为健康；
- 海况、事件 RNG、压制状态/原状态、HARD 蓝方策略、通信队列和最近命令进入 checkpoint；
- HARD 正式 runner 改为使用 routed command 路径，CLI 增加独立 HARD selftest 与 gzip 日志；
- relay_required/success tick 进入权威 metric state，HARD 中继指标可在线计算和离线重算；
- authority log 增加逐 tick scenario events，非 referee 回放仍按白名单过滤；
- 红方公开 suppression 事件剔除蓝方 truth/source ID；天气、海况和通信状态进入观察与可视化 DTO。

## 固定 seed 基线

- 正常成功：seed=0，tick 1751，`red_success / all_threats_destroyed`，breaches=0，interception=1.0，relay_effectiveness=1.0；
- 失败路径：seed=0、禁用红方交战，tick 848，`blue_success / breach_threshold_reached`，breaches=3；
- 超时路径：seed=401、裁决上限2 tick，`red_success / timeout_denial_success`；
- 正常成功日志的在线评分与脱离环境的离线重算逐字段相等。

## 配置身份

- EASY：`sha256:1adaa81c574ffa6a0e05c88be0da7029d45d5f24a1fa73d3ef2ad20065c81f16`
- MEDIUM：`sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4`
- HARD：`sha256:9a057519c2a6f53d0cf5d4d9073a4c7b9ad9976d1228e6b846505d9a49f8bc42`

## 质量门禁

- Ruff：全仓零错误；
- 严格 mypy：228 个源文件零错误；
- Bandit：零问题；
- `git diff --check`：通过；
- HARD 长路径成功、失败、超时和离线评分测试通过；
- 全量回归：`382 passed, 90 warnings in 541.20s`；
- 告警为既有 Taichi/Gymnasium 提示及缺少中文字体时的 Matplotlib glyph 提示，无失败；
- 未增加 skip/xfail，未放宽断言或排除核心环境、通信、裁决与评分代码。

## 保真度和剩余边界

- E4 是比赛任务级压制状态机，不是物理级电子战或真实装备毁伤模型；
- 冻结 HARD 配置只声明 USV-1 接近压制，本版本没有自行增加岸基设施压制；
- 风场/UAV 漂移未在冻结配置启用，因此没有隐式加入；
- AD2-11 仍需执行覆盖率、性能、16/32 并发、100 局批量、长稳和发布准备门禁。

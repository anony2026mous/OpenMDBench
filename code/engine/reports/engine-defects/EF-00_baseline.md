# EF-00 当前 HEAD 与缺陷证据核验

TASK_ID: EF-00
STATUS: DONE
OBJECTIVE: 在不修改实现、测试、Schema、Catalog、依赖或场景参数的前提下，核验当前 HEAD 上 S1–S5 的证据、真实路径与最小可审计复现。
REQ_IDS: EF-00 §6；S1–S5
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`

## 输入与前置结论

- 已完整读取：`AGENTS.md`、平台服务需求、平台实施/测试/审查计划、`docs/OpenMDBench_V2_Engine_Defects_S1_S5_Repair_Development_Plan.md`。
- 修复计划要求的 MD-AD-002 原始需求与实施计划（历史路径为 `docs/parse3/MD-AD-002_Three_Scenario_Requirements.md` 与 `docs/parse3/MD-AD-002_Codex_Implementation_Test_Review_Plan.md`）不在当前 HEAD；`git log --all` 仅显示其曾在历史提交中存在。当前可读替代证据为 `reports/md_ad_002_requirements_traceability.md`，仅用于定位，不替代原始需求。
- 工作区在开始前已脏：删除的 `.cao/agents/*` 和 `docs/platform-refactor/T5_QUALIFICATION.md`，修改的 `AGENTS.md` 与用户手册，以及多项未跟踪脚本、日志、报告和本修复计划。它们均为既有用户工作，本阶段不覆盖、不修改。

## 权限边界

- ALLOWED_READ: 当前 HEAD 的源码、测试、Schema、Catalog、场景、ADR、Git 元数据、现有报告和只读运行输出。
- ALLOWED_WRITE: 仅本文件及测试临时输出。
- PROHIBITED: 修改源码、测试、Schema、Catalog、依赖、场景参数；执行外部缺陷报告的临时脚本；T4/T5；提交、推送、合并或创建 PR。

## 执行预算

- TEST_LEVEL: T1
- ALLOWED_COMMANDS: `git status/rev-parse/log/diff`、`rg`、`sed`、`pytest --collect-only`、针对现有或本地内联最小复现的定向 `pytest`。
- PER_COMMAND_TIMEOUT: 120 秒
- TOTAL_TIME_BUDGET: 5 分钟的测试执行时间（不含文档与源码只读审计）。

## 验收与停止条件

- 对 S1–S5 分别给出 `CONFIRMED`、`NOT_REPRODUCED` 或 `CHANGED_ROOT_CAUSE`，附真实路径、可审计最小复现和结果。
- 记录 commit、Python/依赖版本、工作区已有修改、公开 Schema 与兼容风险。
- 如果原始 MD-AD-002 输入缺失、根因不一致、最小复现不能确定，停止并给出 `BLOCKED` 或 `NEEDS_DECISION`；不进入 EF-01。

## 输出

- 本执行记录：`reports/engine-defects/EF-00_baseline.md`
- 定向 T1 输出（若运行）仅写入测试临时目录。

## 运行环境与工作区基线

- HEAD：`cb8924bc097729fcc5f5c4222a32065fd1fdeea9`。
- 项目声明 `requires-python = >=3.11,<3.13`；默认 `python` 为 3.14.6，超出支持范围，且缺少 `gymnasium`。该解释器不能作为本次测试证据。
- 已有仓库 `.venv` 可用：Python 3.11.15；`pydantic=2.13.4`、`PyYAML=6.0.3`、`pytest=9.1.1`、`numpy=2.4.6`、`gymnasium=1.3.0`。
- 既有工作区修改在阶段开始前已存在：删除 `.cao/agents/*` 与 `docs/platform-refactor/T5_QUALIFICATION.md`，修改 `AGENTS.md` 与用户手册，以及多项未跟踪脚本、日志、报告和修复计划。未读取敏感文件、未覆盖这些修改；本阶段唯一新增内容为本报告。
- `pytest` 默认会自动加载 `/opt/ros/humble` 的外部插件并因缺少 `lark` 失败。定向测试使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，仅禁用外部 setuptools pytest 插件自动加载；项目未声明必需 pytest 插件。

## S1 — 评分逐指标方向

**结论：CONFIRMED。**

- 真实实现位于 `openmdbench/missions/engine_v2.py` 的 `ScoringSystemV2.evaluate`：可用指标按原始 `value` 做聚合；只有 aggregate `direction` 用于对 training reward 整体乘以 `-1`。`ScoreInputV2.direction` 和 `MetricScoreReceiptV2.direction` 被保存，却不参与 total、competition score 或 utility 的计算。
- 三个正式 V2 AD-002 场景均声明 aggregate `maximize`，却将 `score.denial` 声明为 `minimize`（例如 `scenarios/formal/md_ad_002_hard/scenario.yaml` 的 scoring 段）。终局 ranking 则由 mission rule 的静态 `ranking` 映射给出，不从 score total 推导。因此没有可按逐指标方向改变的 score ranking。
- 最小探针（仓库 `.venv`）使用一项 maximize=1、权重 0.5 与一项 minimize、权重 0.5，在 aggregate=maximize 下得到：

  ```text
  minimize=0  -> total=0.5, training_reward.aggregate=0.5
  minimize=3  -> total=2.0, training_reward.aggregate=2.0
  ```

  即 minimize 指标变坏反而提高 total 与 reward；`competition_scores` 仍暴露原始值。
- 既有 `tests/integration/test_mission_scoring_world_v2.py::test_world_tick_executes_each_resolved_metric_policy` 通过，但其断言正是 minimize aggregate 仅翻转 reward 的当前行为，不能证明逐指标 direction 已生效。

## S2 — 低空有效探测距离

**结论：CONFIRMED。**

- Catalog 的正式 V2 传感器已有 `low_altitude_range_m`，如 `catalog/v2/md_ad_002.yaml` 的 `sensor.shore-early-warning@2.1.0`（range=40,000 m，low-altitude range=15,000 m）。
- 正式 V2 入口为 `WorldStateV2._evaluate_generic_subsystems`（`openmdbench/world/factory_v2.py`），其将 resolved sensor profile 交给 `GenericSubsystemEngineV2.evaluate`（`openmdbench/systems/generic_v2.py`）。后者仅读取 `range_m`，按三维 `distance <= range_m` 判定，并没有读取 `low_altitude_range_m`、高度参考、ceiling 或 transition。
- 旧的 `openmdbench/systems/sensors/ad2.py::detection_probability` 确实读取该字段，但这是 legacy AD2 路径，还硬编码 `target.position[2] <= 30.0`，不能作为正式 V2 接线证据。
- 最小探针以 `range_m=40,000`、`low_altitude_range_m=15,000`、目标高度 100 m、距离约 20,000.25 m、probability=1 运行正式 `GenericSubsystemEngineV2`，结果为 `effective_sensor_range_m=40000.0`、`detected=True`。低空字段没有影响结果。

## S3 — own-state 与干扰职责

**结论：CONFIRMED。**

- `WorldStateV2._shared_observation_unavailable_entity_ids`（`openmdbench/world/factory_v2.py`）把每个 active jamming session 的 `target_entity_id` 加入 unavailable 集合。
- `WorldStateV2.observation_snapshot` 将当前 faction 全体 entity IDs 减去该集合后生成 `own_entities`，并用同一集合过滤 contact owner。它因此同时删除仍 active 的本方实体状态及其 contact；这不是仅对 communication/shared data 的退化。
- 既有、可审计的最小系统复现 `tests/system/test_jamming_observation_v2.py` 在干扰 tick 明确断言 `defender.interceptor-001` 不在 `own_entities`，其 reports 也不在 contacts；jamming 结束后又恢复。该测试通过，证明的是当前缺陷行为。

## S4 — MD-AD-002 环境 modifier

**结论：CONFIRMED。**

- 真实环境资源为 `environment.clear@2.0.0`、`environment.cloudy@2.0.0`、`environment.rain-fog@2.0.0`（`catalog/v2/md_ad_002.yaml`）。它们只包含 `weather`、`visibility_scale`、`sea_state`，分别为 1.0/1、0.88/2、0.65/4。
- 正式世界在 `WorldStateV2._environment_modifiers` 调用 `modifiers_from_environment_content_v2`。该 materializer 仅识别 `capability_modifiers` 或标准 multiplier 键（motion、sensor range/probability、weapon hit、communication loss、energy consumption）；上述三份环境资源不提供任一键。
- 从当前 Catalog 内容直接 materialize 的最小探针输出：

  ```text
  environment.clear: []
  environment.cloudy: []
  environment.rain-fog: []
  ```

- 潜在消费方是 `WorldStateV2._resolve_entity_capability`（dynamics、sensor、energy、weapon）与 `_communication_profile`（range/loss）。本次三个 AD-002 环境实际产生零 modifier，因此没有任何上述消费方得到环境能力变化；`visibility_scale` 与 `sea_state` 在正式 V2 capability pipeline 中没有实际消费。

## S5 — controller scope、共享 contact、命令与消息 transport

**结论：CONFIRMED。**

- 公开 `ObservationV2`（`openmdbench/schemas/core_v2.py`）只有 `observer_faction_id`、`own_entities`、`contacts_by_faction` 和 metadata；没有 controller slot/scope、controlled entity IDs、organic contacts、shared contacts 或 received inbox。`ActionBatchV2` 只有 faction scope；`MessageIntentV2` 只以 entity ID 指定 recipient。
- 正式 V2 sensor contact 从 `_evaluate_generic_subsystems` 直接写入 `contact_store`；`observation_snapshot` 再按 faction 和 owner 直接读取它。此调用图没有 contact message、route、delivery、TTL 或 shared-contact store，因此 organic 与共享轨迹未分层，航迹没有经过 transport。
- persistent command 在 `SessionActionQueueV2.apply_tick` 被标记 active、转换为 `EntityControlCommandV2`，并直接装入同 tick 的 `WorldTickInputV2.entity_commands`；只有 `send_message` 会创建 `MessageIntentV2`。因此命令绕开 communication transport。
- `send_message` 的确进入 `_apply_message_intents`，经 route/delay/TTL/loss 记录到 `_message_queue`，并由 `_advance_message_transport` 标记 delivered/blocked/expired；delivery 后没有写入任何 controller/entity inbox 或 Observation 字段，故没有 agent 接收出口。
- 既有定向测试确认两端事实：`test_world_transport_is_checkpointed_and_delivers_only_at_quantized_tick` 证明显式消息可经 transport 在量化 tick 投递；`test_send_message_dispatches_to_world_communication_stage_exactly_once` 证明 action 只在 queue 中形成 blocked transport record；`test_persistent_command_survives_empty_ticks_and_discrete_action_executes_once` 证明 persistent command 可直接在 tick 生效并保持。

## T1 命令与结果

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `python -m pytest -q <首组 6 个目标>` | 1 | pytest 初始化时加载外部 ROS `launch_testing`，缺少 `lark`；未收集项目测试。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -q <首组 6 个目标>` | 0 | 13 passed, 14.40 s。覆盖 S1、S3、S4 pipeline、S5 message 及 generic subsystem。 |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -q <第二组 2 个目标>` | 0 | 2 passed, 2.07 s。覆盖 persistent command 与已投递 message 的 checkpoint/量化时序。 |
| `.venv` 的 4 个内联、只读最小探针 | 0 | 分别得到 S1 方向倒挂、S2 低空门未接线、S4 零 modifier、S5 Schema 缺字段的上述结果。 |

首组目标依次为：`tests/system/test_jamming_observation_v2.py`、`tests/contract/test_generic_subsystems_v2.py::test_subsystems_are_order_independent_and_use_named_sensor_substreams`、`tests/contract/test_md_int_003_environment_communication.py::test_capability_modifier_order_expiry_and_availability_clamp`、`tests/contract/test_md_int_003_environment_communication.py::test_world_capability_pipeline_reaches_weapon_and_suppression_without_scenario_branch`、`tests/integration/test_session_action_world_v2.py::test_send_message_dispatches_to_world_communication_stage_exactly_once`、`tests/integration/test_mission_scoring_world_v2.py::test_world_tick_executes_each_resolved_metric_policy`。第二组为 `tests/integration/test_session_action_world_v2.py::test_persistent_command_survives_empty_ticks_and_discrete_action_executes_once` 与 `tests/contract/test_md_int_003_environment_communication.py::test_world_transport_is_checkpointed_and_delivers_only_at_quantized_tick`。

默认 Python 的 3 个 package-import probe 因缺少 `gymnasium` 退出 1；一个初始 YAML one-liner 有 shell quoting 语法错误，未作为证据，随后已由 `.venv` 的成功 probe 替代。所有测试均为 T1；未运行 T4/T5、全量测试、性能、并发或 soak。

## 公开契约、兼容性与确定性影响

- **Schema/日志/checkpoint：** S1 需要明确 raw、normalized/utility、contribution 与 aggregation version；S5 需要 scope、contact provenance、inbox 和 command/message transport 状态。它们都会触及公开 Observation/receipt、日志和 checkpoint 的版本与旧读取策略。
- **Catalog：** S4 必须发布新的 environment resource version 和 hash；不得原地修改 `@2.0.0`。S2 的低空高度基准、ceiling、transition 目前没有正式 V2 Schema/receipt 语义，旧 sensor 的无 profile 行为也需保持。
- **接口：** Python、Gym、Vector、REST 当前共同使用 faction-scoped Observation；改变为 controller-scoped 数据将影响旧 agent 和 adapter。现有 controller slot 是编译期 ownership/visibility 数据，尚不是 Observation 的调用方 scope，也不是鉴权。
- **确定性：** 当前 message transport 已使用命名 `communication:<message_id>` 子流并被 checkpoint；S1/S2/S3/S4/S5 修复不得改变既有未命中路径的 RNG 消耗、stable ordering 或 Observation GET 的只读语义。现有 S3 和 S5 定向测试覆盖部分 checkpoint 行为，未构成全量确定性证明。

## 阶段结论与准入

- S1、S2、S3、S4、S5 全部为 `CONFIRMED`，且真实根因与修复计划描述一致；未发现需要进入 S6–S11 才能完成本次核验。
- MD-AD-002 原始需求与实施计划不在当前 HEAD；用户已在本会话明确确认这是其有意删除，不构成 EF-00 输入阻断。历史路径仅作为定位证据，不恢复、不读取或替代为当前权威输入。
- **EF-01 准入：就 EF-00 核验而言准入。** 五项缺陷均已确认，真实根因与计划一致。EF-01 仍需单独建立执行记录，并先冻结 S1 归一范围、S2 高度基准、S3/S5 controller scope 与兼容策略；本阶段未进入 EF-01。

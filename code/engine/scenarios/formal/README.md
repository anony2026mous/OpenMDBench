# Formal V2 场景包

本目录是“只复制数据即可派生新场景”的正式范例。注册表在 `registry.yaml`，每个场景目录只含
`package@2.0` YAML/JSON/CSV/GeoJSON 等数据文件；资源定义位于 `catalog/v2/`。场景包不得包含
Python、动态导入、表达式执行或按场景 ID 选择算法的代码。

MD-AD-002 的三个难度是三个独立包：

- `md_ad_002_easy/`：clear 环境和基础三波次；
- `md_ad_002_medium/`：2.1.0 感知资源、cloudy 与规避标记事件；
- `md_ad_002_hard/`：rain/fog、海况、干扰和组件抑制事件。

三者共享 `catalog/v2/md_ad_002.yaml` 中的 exact-ref 资源，但数量、资源版本、事件和任务参数全部
由各自 `scenario.yaml` 声明。运行时不会读取 public ID 来改变语义。

## 复制为新场景

1. 复制最接近的目录并修改 `scenario_id`、`display_name`。
2. 在 `catalog/v2/<bundle>.yaml` 定义或复用版本化资源及完整 dependencies。
3. 只在 `entities`、`events`、`mission_rules`、`scoring`、`controller_slots` 中组合资源和规则。
4. 在 `registry.yaml` 添加 public ID、包目录和 catalog bundle。
5. 编译并运行：

```python
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.formal_v2 import create_formal_session_v2

resolved, catalog = compile_formal_scenario_v2("MD-AD-002-EASY")
session = create_formal_session_v2("MD-AD-002-EASY", session_id="example.session", seed=7)
session.load().start()
receipt = session.step(operation_id="tick.0", expected_tick=0)
```

## 智能体范例

每个包的 `agents.yaml` 只声明策略参数。通用实现
`openmdbench.policies.rule_v2.FormalRuleAgentTeamV2` 展示完整的双边对抗 V2 接法：攻击方分别采用
直线突防、分轴规避、多轴蛇形；防守方只依据公开的 opaque contact、估计航迹、置信度和时效进行
拦截与射击。射击提交 `contact_id`，真实目标只在 Session/Combat 权威边界解析。三种难度没有
场景 ID 分支，开发者可直接复制 `agents.yaml` 改策略参数。

`examples/md_ad_002_sdk_policy.py` 运行该规则智能体组。它只读取只读 `world_view`、使用 World 签发的
单实体 authority token、构造 `ActionBatchV2`，再由 `SessionLifecycleV2.step` 作为唯一 World writer
推进。CLI 的 formal V2 `run/live` 入口也默认装载同一组规则智能体。

```bash
.venv/bin/python examples/md_ad_002_sdk_policy.py \
  --scenario MD-AD-002-HARD --seed 7 --ticks 60
```

禁止复制 Legacy `env/`、`model/` 或 `openmdbench.scenarios.legacy` 的专用分支作为新场景入口。

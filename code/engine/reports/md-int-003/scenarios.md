# MD-INT-003 三档场景资源接入记录

## 范围

- 阶段：`MD3-07`（资源接入补充）。
- 包：`MD-INT-003-EASY`、`MD-INT-003-MEDIUM`、`MD-INT-003-HARD`。
- 本次只修改三个 `ScenarioPackage` 的数据引用和系统测试；没有修改运行时、Schema、Catalog 或规则智能体。

## 不可变资源选择

| 档位 | 所有对海传感器 | 防守水面/岸基通信 | 防守 UAV 通信 | L3 环境事件 |
|---|---|---|---|---|
| L1 | `@2.1.0` | `communication.defender-surface-tactical@2.1.0` | `communication.defender-uav-surface-tactical@2.1.0` | 不适用 |
| L2 | `@2.2.0` | `communication.defender-surface-tactical@2.1.0` | `communication.defender-uav-surface-tactical@2.1.0` | 不适用 |
| L3 | `@2.3.0` | `communication.defender-surface-tactical@2.1.0` | `communication.defender-uav-surface-tactical@2.1.0` | `environment.md3-high-sea@2.1.0`，tick 300 |

传感器集合为 defender USV 雷达/EO-IR、UAV 雷达/EO-IR、岸基雷达和 attacker 导航雷达。出生 attacker 与初始 attacker 使用同一档位。L3 的雷达压制事件也精确指向 `sensor.defender-usv-surface-radar@2.3.0`，避免事件作用于历史版本。

## 编译取证

Catalog：`sha256:c070a2cc0540b1deb37db6375149acbc7304b929927708dbc0cf8d6f0bb7caf9`。

| 包 | resolved hash |
|---|---|
| `MD-INT-003-EASY` | `sha256:0092d1d741def7237ae01c8333024746a9ed6e734a9078c9f917322288769ba5` |
| `MD-INT-003-MEDIUM` | `sha256:7138184abbae2def40ac6a596b9743ec2328c59293b709a222d92d6d3819ef83` |
| `MD-INT-003-HARD` | `sha256:f76536982aa0feeb4b252ac9d3a7e9e9905922428bc2604f404f0b1404175395` |

验证命令：

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/openmdbench-mpl \
  .venv/bin/python -m pytest -q \
  tests/system/test_md_int_003_scenarios.py \
  tests/contract/test_md_int_003_catalog_closure.py \
  tests/contract/test_md_int_003_environment_communication.py
```

首次运行时，新增测试错误读取了未公开的 `ResolvedScenarioV2.event_resource_bindings` 字段；已改为验证解析后的 `environment_binding`，未修改产品代码。修正后通过的结果记录在 MD3-07 执行记录中。

## 边界

这些参数仍由 Catalog 标记为 `UNVALIDATED_BENCHMARK`；本阶段证明引用、编译、公开规则智能体和既有环境/通信契约正确，不构成真实装备标定或 30-seed 统计评测结论。

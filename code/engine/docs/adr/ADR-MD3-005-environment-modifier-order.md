# ADR-MD3-005：环境与能力修饰器的组合顺序

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-06 环境、动力学、传感、武器、能源、通信

## 决策

环境与故障均为版本化、可组合的 capability modifier，不得写入场景 ID 分支。每个 modifier 明确 selector、target capability、operation（multiply/add/override）、priority、生效/失效 tick、下限和来源 event。

某 tick 的有效能力按稳定次序计算：resolved base profile → active environment modifiers（priority、ID）→ component suppression/failure → lifecycle/energy availability clamp。相同配置和 tick 必须得到相同值；event 在其声明 tick 的权威 pipeline 开始时生效，因而 t=300 的天气会影响 tick 300 的后续运动、探测、武器、能源和通信计算。

## 依据与兼容

`weather_change` 和 `component_suppression` 已是受控 V2 event，但当前仅保存 state。MD3-06 扩展其通用消费链，不改变 ActionBatch、World 或 Scenario ID 边界。

## 验证义务

精确 tick 的 forecast/切换、乘法组合、恢复、RNG isolation、checkpoint 中间态、request/renderer frequency 等价均为 MD3-06 门禁。

U5/U8 的倍率和故障参数在冻结前为 `UNVALIDATED_BENCHMARK`。

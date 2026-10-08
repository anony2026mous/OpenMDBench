# REVIEW-01 结构化代码自审记录

```text
TASK_ID: REVIEW-01
STATUS: DONE
MODE: 冻结后只读审查；发现问题后退出审查、修复、定向复测，再重新审查。
SCOPE: BUG-V2-001 生命周期—运动资格修复；PERF-MMG-001 step_many 批量子步优化；
  本专项新增 ADR、测试与阶段记录。
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
```

## 审查证据

- scoped `git diff --check`（`factory_v2.py`、`lifecycle_v2.py`、`native_v2.py`、
  `sim2sea_mmg_worker.py` 与直接测试）：通过，无空白错误。
- 代码路径审查：World 仍以 `sorted(expected_entity_ids)` 形成稳定 motion 顺序；Session 仅消费
  World `motion_eligibility_snapshot`，没有重新推导 lifecycle/dynamics 集合。
- `rg` 审查：生产 step_many/native 路径无 `MD-AD`/`MD-INT`/faction/entity ID 特例；无场景参数、
  物理 dt、substeps、武器或评分修改。
- T2：step_many/native/isolation 定向集 `80 passed`（覆盖补强后复跑）。
- T3：legacy-vs-batch 600 tick receipt/checkpoint 严格等价；指定 MD-AD/MD-INT 回归 `81 passed`；
  HARD/73/1800 CLI exit 0。

## 检查项与结论

| 检查项 | 结论 | 证据 |
|---|---|---|
| Session/World 是否重复推导运动资格 | PASS | Session 调用 World-only snapshot；World 内部 strict set check 保留 |
| lifecycle 是否撤销 active motion/command | PASS | B01--B10、三档/MD-INT T3 证据；disabled/destroyed 不进入 entries |
| persistent/discrete 是否可重复执行 | PASS | cancelled/rejected/consumed 状态及 checkpoint 闭包测试 |
| wreck 是否主动运动/错误移出碰撞 | PASS | policy 仅生成 static wreck candidate，MD-INT 生命周期回归通过 |
| step_many 子步顺序、dtype、控制保持 | PASS | legacy 连续 step 与 batch 严格字段/600 tick receipt/checkpoint 等价 |
| 子步失败/超时/断连是否泄露部分状态 | PASS | P01-04 rollback、closed/断连/新 worker P01-06；无静默重试 |
| checkpoint 是否保留 worker continuation | PASS | P01-05 与 Session/World checkpoint hash 等价 |
| 外部 schema/事件/receipt 是否未版本化改变 | PASS | 无 Action/Frame/receipt/checkpoint schema 字段修改；T3 gateway/REST/replay 覆盖 |
| 不受限 RPC / lock / worker 泄漏 | PASS（定向） | `substeps` 限为 1..256；shared worker lock 未改；T2 worker lifecycle 成功清理。未执行 T5 长稳/并发 |
| 测试是否被弱化 | PASS | 红灯 10 failed 先行；79+1 缺口修复为 80 passed；无 skip/容差扩大 |

## 审查发现及闭环

| ID | 严重度 | 发现 | 处置 | 复测 |
|---|---|---|---|---|
| R-01 | P1（已关闭） | fake core 在 `step_many` 内循环，旧 parent-side N 次 `step` 可能让原断言误绿，未直接证明 adapter 只发一次 batch 调用。 | 退出审查，给 fake 添加 `batch_calls` 并断言一次 `step_many(..., substeps=2)`。 | 受影响 T2 `80 passed`。 |

重新审查后：P0 `0`，未关闭 P1 `0`，P2 `0`。工作区中 `AGENTS.md` 的已有尾随空白、用户操作文档和
历史 artifacts 不属于本专项，未修改、未计入 scoped diff check。

## 最终质量结论

- 正确性、确定性、场景/接口回归、worker 失败语义与 RPC 数量目标：通过。
- 30% 端到端相对性能目标：**未通过**（实际约 13.80%）；PERF-04 已证明轻量 snapshot 不是可安全
  达成该缺口的目标，故没有越权继续改动。
- T4/T5：未获授权，未执行。
- 本专项的工程审查闭环完成，但总体交付状态必须保持 **NEEDS_DECISION**，不得因代码审查通过而
  宣称全部性能验收完成。

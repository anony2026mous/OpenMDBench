# PERF-04 快照优化决策门记录

```text
TASK_ID: PERF-04
STATUS: DONE
OBJECTIVE: 在 PERF-03 后只评估每 tick MMG snapshot 是否应另立 PERF-MMG-002；本阶段不改实现。
REQ_IDS: PERF-MMG-001; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
TEST_LEVEL: T0/T3 evidence review
```

## 证据

- PERF-03 中每 tick有 4 次 snapshot RPC（2 entity × step 前后）；单次均值约 0.10 ms，合计约
  0.4 ms/tick，约为优化后 37.31 ms 完整 tick 的 1.1%。
- 显式完整 Session checkpoint 约 3.59 s，但不属于每 tick 路径；其成本主要来自完整历史、World
  账本与验证，而非 4 次轻量 worker snapshot。
- 优化后距离 `≤100 ms/tick` 仍有约 62.7 ms 余量；没有并发或长稳资源压力证据。T5 未获授权。
- PERF-03 未达到 30% 的主要剩余时间在非 MMG RPC 的 action/world/receipt 管线；删除 snapshot
  不能弥补约 7.0 ms/tick 的相对目标缺口。

## 决定

**不提出、不实施 PERF-MMG-002。** 当前每 tick snapshot 并非显著瓶颈，且修改它会触及
checkpoint/失败回滚完整性；在没有新的受控证据和单独 ADR/测试前，不应为追逐指标削弱该契约。

## 遗留项

- 专项总体仍为 `NEEDS_DECISION`，唯一未满足项是 PERF-03 的 30% 相对收益目标。
- 若后续允许扩展范围，应先建立新的性能 ADR/计划，分别测量 World/receipt/mission/action 管线，
  而不是假定 MMG snapshot 是根因；不得直接续改当前专项。
- 本阶段无生产/测试/场景/Catalog/依赖改动；T4/T5 未执行。

## REVIEW-01 准入

**PASS**。所有实现与定向证据已冻结，可进入只读结构化自审；审查期间不边审边改。

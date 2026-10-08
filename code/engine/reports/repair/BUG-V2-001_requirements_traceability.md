# BUG-V2-001 需求追踪矩阵

- 状态：BUG-01 已冻结；BUG-02 红灯测试已完成；BUG-03 已通过 T2（含 fallback checkpoint 闭包）；BUG-04 已通过 T3；PERF-00--04 与 REVIEW-01 已完成（总体性能门禁为 NEEDS_DECISION）
- 当前 HEAD：`4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e`
- 前置证据：`reports/repair/BASE-00_current_head.md`
- 权威设计：`docs/adr/ADR-REPAIR-001-motion-eligibility.md`

| 需求/不变量 | BASE-00 证据 | BUG-01 冻结设计 | 后续验收 | 状态 |
|---|---|---|---|---|
| BUG-V2-001：Session/World 运动集合一致 | EASY/73：tick 358，Session 11 vs World 9；B01 红灯复现 generic disabled 边界 | BUG-03 World snapshot 已取代 Session 复制筛选，World strict set check 保留 | B01、B02、B09；三档 1800 tick | BUG-04 T3 PASS |
| AR-003 / ENT-005：机制与场景政策分离、capability-driven | 三档共用相同 Session/World 路径 | 不含 scenario/faction/entity ID；以 lifecycle + exact dynamics/move token 判定 | 合成 fixture、MD-AD、MD-INT 回归 | FROZEN |
| AR-005 / CMD-003：单写入者、原子与幂等 | World 是 tick writer；Session 仅投影命令 | World 原子形成/复核 snapshot；ID 集合不等失败于 adapter 前 | B02、B04、B10 | BUG-04 T3 PASS |
| LIFE-001：集中生命周期 | tick 357 collision damage 将两实体 active → disabled 且清 capability | disabled/destroyed/wreck/despawned 均由 World lifecycle 解释，`dynamics_ref` 不删除 | B01、B05、B06、B10 | BUG-04 T3 PASS |
| CMD-001 / CMD-002：persistent/discrete 语义 | 现有 status 有 cancelled/rejected；B02/B07/B08 曾显示直接中断 tick；长局首次暴露 fallback status 缺失 | stale persistent 取消；stale discrete 终态拒绝并 consumed；fallback child/status 成对保存 | B03、B04、B08、fallback checkpoint | BUG-04 T3 PASS |
| AR-006：公开契约唯一 | `ActionChildReceiptV2` 已有 status/error_code | 不新增/变更公开 schema；使用现有 cancelled/rejected 与 lifecycle-invalid code | Python/Gym/REST 对比 | FROZEN |
| AR-007 / RUN-002：确定性与时间 | 仅单次固定 seed 复现，未作完整重复证明 | snapshot、fallback、取消与 receipt 按稳定 ID/tick 排序；speed 不影响语义 | B07、B10、两次同 seed | FROZEN |
| CHK-001：完整恢复 | checkpoint 已保存 entity lifecycle、policy evidence、pending/persistent/consumed 账本 | 不持久化第二 eligibility 事实；restore 后由 World 重算并产生相同投影 | B07、击毁前/中/后 restore | BUG-04 T3 PASS |
| ADR-MD3-003：wreck 无主动运动 | 已有 `destroyed_lifecycle=wreck/despawn` 与 static wreck path | wreck 是非 dynamics 静态 collision candidate；disabled 不冒充 wreck | B05、B06、MD-INT-003a/b/c | FROZEN |
| 领域兼容：air/surface/fixed | 复现使用 UAV；三档也含 USV/fixed dynamics | fixed binding 仍有空 controls；air/surface 均以同一 predicate | 既有 air/surface 契约、MD-INT 回归 | FROZEN |
| PERF-MMG-001：每活动 MMG 每 tick 至多一次 step RPC | PERF-00：2 activity × 10 子步 = 20 step RPC/tick | worker-side `step_many`；legacy step 保留为等价基准，参数限制 1..256 | P01-01--06、T2 80 passed、PERF-03 probe | PASS：2 step_many/tick |
| PERF-MMG-001：子步/恢复确定性 | 旧路径逐次 RPC 是基准 | worker 一次初始化、严格 N 次原序 core_step；异常恢复 request 前 canonical state | 600 tick receipt + World/Session checkpoint hash 等价；HARD/73/1800 | PASS |
| PERF-MMG-001：相对端到端收益至少 30% | PERF-00 mean 43.28 ms | 未降低 fidelity/快照/日志伪造收益 | PERF-03 mean 37.31 ms，-13.80% | NEEDS_DECISION |

## 非范围与未证明项

- BUG-02 新增 B01--B10；在旧实现上 4 通过、6 按预期失败，完整证据见
  `reports/repair/BUG-02_failure_tests.md`。这不是测试通过声明。
- 未改变 MMG RPC、physics dt、子步、快照策略、场景兵力、装备参数、命中/毁伤/评分。
- BASE-00 登记的 CLI 二次 `stop()` transition P2 不属于本修复契约；除非最小实现无法隔离，
  不得借 BUG-03 扩展处理。
- PERF-02 改变的是 MMG RPC 的调度位置：每 entity/tick 的 N 次 Pipe step 合并为一次 batch RPC；未
  改变 physics dt、子步数、RK4、float32、控制保持或每 tick snapshot 策略。PERF-03 证明其权威
  receipt 与 checkpoint 等价。
- PERF-04 未立项快照优化；其约 0.4 ms/tick（约 1.1%）不足以安全弥补 30% 性能缺口。

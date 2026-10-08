# ADR-MD3-007：终局与截断并存语义

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-05/07/08 mission 与外部接口

## 决策

权威终局按 `REQ-MIS-002` 固定优先级评估并锁存：管理员/系统故障；核心区自爆（defender loss）；全部 attacker destroyed/disabled/grounded/energy-depleted（defender win）；全部受控 defender 作战平台不可用且仍有 attacker 推进（defender loss）；1500 tick；连续 180 s 无有效交互。

前三类确定性结果为 `terminated=True, truncated=False`。时间上限和无交互中止为 `terminated=False, truncated=True`，同时产生当前态势的 mission result 和 score receipt；二者不互相替代。自爆与拦截同 tick 时，先使用连续 TOI/zone event 的权威时序，再应用上述优先级，禁止实体遍历顺序决定结果。

## 验证义务

MD3-05/07/08 覆盖终局幂等、同 tick 竞争、无交互定义、Gym/Python/REST terminated/truncated 等价、checkpoint 临界恢复。

U10 的时长与窗口在冻结前为 `UNVALIDATED_BENCHMARK`。

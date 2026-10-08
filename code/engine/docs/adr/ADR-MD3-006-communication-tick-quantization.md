# ADR-MD3-006：通信延迟、TTL 与 1 秒 tick 量化

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-06 通信 transport 与 observation sharing

## 决策

通信模型保存原始延迟秒值用于审计，但权威投递只使用整数 tick：`delay_ticks = 0` 当延迟为零，否则 `ceil(delay_s / physics_dt)`。消息在 `scheduled_delivery_tick <= origin_tick + ttl_ticks` 时投递；否则稳定标记为 expired/drop。TTL=1 s、physics_dt=1 s 时，任何非零且不大于 1 s 的延迟均量化为下一 tick，且允许该一次投递，不会因亚秒采样位置产生实现相关的随机过期。

距离、terrain、最多跳数、loss 和 endpoint lifecycle 必须在投递前决定；恢复仅补传审计，不补发已过期 contact。断链时保持最后有效 persistent command；本地传感满足通用 ROE 的 entity 可执行已声明 auto-engagement capability。

## 不采用

- 在 1 s fixed tick 内部分支模拟 20/50/100 ms 子步。
- 将 delayed message 直接写入 observation 或 World 真值。
- 以 entity ID 定义中继拓扑。

## 验证义务

MD3-06 覆盖 0/非零/多 tick 延迟、TTL 边界、range/terrain/relay/loss、断链恢复、checkpoint 和顺序/显示频率确定性。

U3 的数值在冻结前为 `UNVALIDATED_BENCHMARK`。

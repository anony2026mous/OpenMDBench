# ADR-MD3-008：N/A 与 metric_data_missing 的分离

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-05 scoring、日志和回放

## 决策

结构上不适用的 metric 输出 `value=None` 并按现有 V2 N/A 归一规则处理。理论上应可计算但因 authority state、event 或日志缺失而无法计算的 metric 必须输出数值 `0`，并追加 `metric_data_missing` 审计事件，包含 metric ID、缺失输入、tick 和证据来源。实现错误、解析错误和权限错误不得静默转为 N/A。

比赛 score、terminal result 与训练 reward 为独立通道；所有 MD3 指标必须可由权威 event 和 state 重算。safety_score 是独立乘数/排名门槛，不改变一级权重的语义。

## 验证义务

MD3-05 覆盖 N/A、missing、重复 event、权重归一、checkpoint/replay 重算和错误注入。U11 的公式/阈值为 `UNVALIDATED_BENCHMARK`，直至评测方冻结。

# ADR-MD3-009：双边 ActionBatch 与权限模型

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-08 Python/Gym/Vector/REST

## 决策

每个控制 faction 在一个 decision tick 可提交一个独立、带 faction ID、timestamp/TTL、batch ID/idempotency key 的标准 ActionBatch；一个 batch 可合法控制该 faction controller slot 所拥有的任意数量实体。L1/L2 attacker 可由规则控制而不提交外部 batch；L3 可声明第二 controller slot。固定岸基没有导航 capability，因此不能提交导航。

gateway/session 仍是唯一命令写入边界：REST/Python/Gym 规范化至同一 queue，GET observation 不推进 world，persistent command 续存至替换/过期，discrete action 最多执行一次。token 绑定 session、faction 和 controller ownership；observer、frame、event、artifact 均按 faction/public/referee 权限过滤。

## 依据与兼容

`ActionBatchV2`、`AgentGatewayV2`、controller ownership 和 `CommandQueue` 已提供基础语义。本 ADR 不创建 red/blue 字段或第二 REST 业务规则；必要的动态 mask/padding 只作为 adapter 表示层。

## 验证义务

MD3-08 覆盖 defender 五平台、可选 attacker slot、跨 faction/session 拒绝、idempotent fire、continuous/lockstep、GET 不推进和 Python/Gym/REST 等价。

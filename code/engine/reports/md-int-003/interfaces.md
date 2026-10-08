# MD-INT-003 统一智能体接口记录

## 交付边界

MD3-08 没有新增场景专用动作、faction 分支或隐藏真值读取。Python、Gymnasium、Vector 与 REST 均通过同一个 `AgentGatewayV2`/`SessionLifecycleV2` 动作队列工作，并使用同一份 `ActionBatchV2` 和 faction Observation。

## 通用权限修正

原实现仅发布 `authority.<entity_id>` 单实体令牌；因此一个 batch 即使来自同一 controller slot，也无法同时控制该 slot 的多个实体。现已保留这些旧令牌，并新增由 controller ID 稳定派生、与任意实体 ID 命名空间隔离的控制器范围令牌：

- 每个子动作仍逐一核验 controller ownership、faction、生命周期、能力、时间窗和 schema；
- 控制器令牌只覆盖其 immutable slot 中的实体，不能跨 faction 或跨 session；
- 所以一个防守 controller 可在一次 `ActionBatchV2` 中下达 3 艘 USV 与 2 架 UAV 的命令；
- 固定动力学实体仍拥有 `dynamics` 组件证据，但通用动作校验拒绝 `navigation`/`patrol`，不会把岸基站点误当作可机动平台；
- 旧单实体令牌语义保持不变，检查点恢复时令牌由同一 immutable controller ownership 重建。

## 运输与观察边界

`send_message` 作为离散动作只消费一次，并进入通用通信运输状态。零时延消息可在当前 tick 解析；链路不可达时记录为 `blocked`，而不是伪造为 queued/delivered。GET Observation 只读取当前 faction 可见状态，不推进 tick；REST 重试以 operation/idempotency 证据返回同一 receipt。

## 验收测试

新增 `tests/integration/test_md_int_003_interfaces.py` 覆盖：

- 一份 defender batch 同时控制五个可机动平台；
- 固定岸基导航和跨 faction 权限令牌均被拒绝且 tick 不前进；
- Python、Gymnasium、两个隔离的 Vector 会话与 REST 的相同动作时间线产生相同的 faction Observation 摘要；
- REST 的 GET Observation 不推进，重复提交不重复排队。

相关既有 `send_message` 测试同步从过时的“队列计数”断言升级为权威运输记录断言：一条消息、链路不可达、状态 `blocked`、离散动作不重放。

## 边界与后续

接口语义已验证为 benchmark 行为；具体装备参数仍是 `UNVALIDATED_BENCHMARK`。更大规模接口/权限矩阵、30-seed 和 16/32 并发属于 MD3-10/MD3-11，不在本阶段宣称完成。

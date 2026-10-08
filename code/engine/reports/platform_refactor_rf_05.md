# RF-05 阶段报告：CommandQueue 与命令生命周期

## 本阶段需求编号

- CMD-001～CMD-006。
- RF-05：persistent/discrete 动作、幂等、有效期、替换、取消和结果生命周期。

## 修改文件

- `openmdbench/sessions/commands.py`：权威命令队列、tick 应用结果和稳定错误。
- `openmdbench/sessions/session.py`：会话提交/查询入口及 tick 边界消费。
- `openmdbench/sessions/manager.py`：可信 command applier 注入边界。
- `tests/unit/sessions/test_command_queue_rf05.py`：命令生命周期与负向契约。

## 设计选择和 ADR

- 复用 RF-01 的 `ActionBatch`、`PersistentCommand`、`DiscreteAction`、receipt/result DTO。
- 请求线程只完成原子校验和排队；`SimulationSession.step` 是唯一 `apply_tick` 调用者。
- persistent 按 `(entity_id, command_type)` 替换并 hold-last；discrete 用 action ID 永久去重。
- `received/queued`、`applied`、`executed/rejected` 分阶段记录，业务结果不得在排队时伪造。
- 队列持有输入深拷贝，输出 persistent 深拷贝，避免调用者修改权威命令。

## 新增/修改测试

- 持续导航和传感器跨 tick 保持；替换只在 tick 边界生效。
- fire 只应用一次，业务执行结果显式回写，停止请求后弹药不继续减少。
- 相同 command ID 同内容幂等、不同内容冲突。
- stale、unknown entity、wrong side、NaN、断联后过期、destroyed/fallback。
- 输入排列不改变稳定应用顺序；批次失败无部分副作用。

## 实际命令和结果

- RF-05 单元测试：11 项通过。
- RF-04～RF-07 组合定向：32 项通过。
- 受影响回归：145 项通过。
- Ruff、mypy strict（262 个源文件）、Bandit：通过。
- 最终 `make full-test`：495 项通过。

## 覆盖率与性能

- 最终全仓覆盖率 90.63%，通过 80% 门槛。
- 队列仅做稳定排序和映射查找；完整性能测试通过，未声明吞吐提升。

## 兼容影响

- 旧 Gym/REST 动作路径保持兼容；新会话可接收平台 1.0 ActionBatch。
- 未修改旧动作 golden 或裁决结果。

## 未完成、风险和下一依赖

- 场景特定 canonical action 到各系统的全面映射继续由 RF-07/RF-09 adapter 扩展。
- checkpoint 中持久命令和排队恢复属于 RF-13。
- RF-05 完成门禁通过。

# EF-06D S5 Controller Inbox

TASK_ID: EF-06D
STATUS: DONE
OBJECTIVE: 让 delivered `send_message` 及 controller/faction recipient scope 进入 controller-scoped、只读、有界 inbox。
REQ_IDS: EF-06D §12.4；S5D-01–S5D-06；ADR-ENGINE-DEFECTS-001 决定四；CHK-001
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`
WORKTREE: `/home/<user>/Competition_projects/source_codes/source_codes`

## OUTPUTS_AND_EVIDENCE

- `send_message` payload 支持且只允许 entity、explicit controller slots、或 faction broadcast 之一；payload 维持 Schema text 限制（4 KiB，严于建议的 16 KiB）并不含执行路径。
- transport 成功 delivery 才写入接收 controller inbox；私有发送方不会自动收到。消息包含 stable/源 ID、sender、recipient scope、sent/delivered/expiry tick、payload type 与 payload。
- 每个 slot 默认 256、场景 `inbox_capacity` 可显式设为 1–4096；先删除 expired，再按 `(delivered_tick, message_id)` 淘汰，并记录 `communication.inbox_evicted`。GET Observation 不消费；同 ID delivery 幂等。
- inbox、淘汰和 transport queue 已写入 checkpoint；restore 不重复 delivery 或改变排序。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/pytest -q tests/contract/test_engine_defects_s5d_inbox.py` — 初始 3 passed；EF-07 新增显式 self-recipient zero-hop 边界后，S5D/command/communication 定向组 **15 passed**。`compileall`、`git diff --check` 通过。

## COMPATIBILITY_AND_ADMISSION

- 旧 entity-recipient message 在没有 controller claim 时保留既有 entity transport record，不会伪造 controller inbox；formal controller recipient 必须有 explicit endpoint。
- 发端 controller 仅在自身 slot 被显式列为 recipient 时才收到消息；同一 endpoint 使用记录了 `zero_hop=true` 的本地 transport，而未显式列出时仍不接收。
- REST/Gym/Vector 仍经核心 `ObservationV2`，未各自复制 inbox state；跨接口回归留给 EF-07。
- EF-07 准入：通过，执行指定 T3 联合回归；不执行 T4/T5。

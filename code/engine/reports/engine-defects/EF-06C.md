# EF-06C S5 命令投递经过通信链路

TASK_ID: EF-06C
STATUS: DONE
OBJECTIVE: 将 controller action 从提交队列转换为 endpoint-backed transport；仅 delivered action 进入 authoritative World tick，endpoint self-control 为 zero-hop。
REQ_IDS: EF-06C §12.3；S5C-01–S5C-06；ADR-ENGINE-DEFECTS-001 决定三；CHK-001
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`
WORKTREE: `/home/taizun/Competition_projects/source_codes/source_codes`

## OUTPUTS_AND_EVIDENCE

- 每个 accepted child action 生成稳定 `controller-command:<action_id>` transport evidence，记录 endpoint、route、delay、TTL、loss RNG、zero-hop、terminal status 与一次性 claim 状态。
- remote persistent command 在 delivered 前不替换 active command；blocked/dropped/expired persistent 被取消。remote discrete action 在终端失败时 rejected，fire 不进入 combat，因此不消耗 ammunition 或 combat RNG。endpoint self-control 在同一 tick zero-hop delivered。
- queue 纳入 World event-state checkpoint；Session action status/child ledger 在 accepted 与 terminal state 一致，restore 后不会重复交付。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/pytest -q tests/contract/test_engine_defects_s5c_command_transport.py` — 3 passed。
- 同时执行 action/motion 契约（44 passed）及 MD-AD-002 controlled/surface-picket 迁移定向组（1 passed）；`compileall`、`git diff --check` 通过。

## COMPATIBILITY_AND_ADMISSION

- 未带 endpoint 的非 formal 旧 fixture 仅通过 transport record 中的 `legacy-controller-endpoint@2.0` 标记走 zero-hop compatibility；formal V2 不可进入该路径。
- command queue 是审计状态，ActionReceipt 仍是 session-level API；未增加 S6 鉴权或 S7 状态公开。
- EF-06D 准入：通过；仅实现 controller inbox 与 send_message 接收出口。

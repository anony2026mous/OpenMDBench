# EF-06B S5 航迹共享经过通信链路

TASK_ID: EF-06B
STATUS: DONE
OBJECTIVE: 将 confirmed organic contact 以发送时刻不可变 snapshot 经既有通信 route/delay/TTL/loss/jamming transport 投递到指定 controller 的 shared contacts。
REQ_IDS: EF-06B §12.2；S5B-01–S5B-04；ADR-ENGINE-DEFECTS-001 决定三；CHK-001
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`
WORKTREE: `/home/<user>/Competition_projects/source_codes/source_codes`

## BOUNDARY

- ALLOWED_WRITE: shared-contact queue/store、checkpoint event state、controller Observation projection、定向 transport tests。
- PROHIBITED: command transport（EF-06C）、controller inbox（EF-06D）、S6/S7、Catalog/scenario parameter tuning、依赖、提交和推送。

## OUTPUTS_AND_EVIDENCE

- 每个 `(source_contact_id, recipient_controller_slot)` 只建立一个稳定 queue identity；snapshot 在发送时固化，投递时不读取目标当前真值。
- queue 复用 common communication route、delay quantization、TTL、loss RNG stream、relay 和 jamming revalidation；无 route/loss/jamming 均不发布 shared contact。delivery 使用稳定 idempotent store，checkpoint 记录 queue 与 delivered store。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/pytest -q tests/contract/test_engine_defects_s5b_contact_transport.py tests/contract/test_engine_defects_s5a_controller_scope.py tests/contract/test_md_int_003_environment_communication.py` — 20 passed.
- `compileall` 与受影响文件 `git diff --check` 通过。

## COMPATIBILITY_AND_ADMISSION

- legacy faction adapter 保留既有 contacts 形状并继续显示 compatibility warning；strict controller DTO 只显示 endpoint organic contact 和实际 transport-delivered shared contact。
- 共享 track 保持 ragged source reports，未引入 S8 fusion。route 在发送时不可用会得到 terminal blocked receipt；本阶段没有 retry policy。
- EF-06C 准入：通过；仅实现 command transport。

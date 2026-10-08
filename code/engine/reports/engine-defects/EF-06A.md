# EF-06A S5 严格 controller scope 与 Observation Schema

TASK_ID: EF-06A
STATUS: DONE
OBJECTIVE: 将 controller claim、Observation own-state 与 action scope 统一为严格、显式且可编译验证的契约，并要求 formal V2 controller 声明显式通信 endpoint。
REQ_IDS: EF-06A §12.1；S5A-01–S5A-06；ADR-ENGINE-DEFECTS-001 决定三；CHK-001
CURRENT_COMMIT: `cb8924bc097729fcc5f5c4222a32065fd1fdeea9`
WORKTREE: `/home/<user>/Competition_projects/source_codes/source_codes`

## PRECONDITIONS_AND_AUTHORIZATION

- EF-05 为 DONE；基础 own-state 已与 jamming/shared report 分离。
- 用户于 2026-09-18 授权连续执行 EF-04 至 EF-09，无需阶段间询问。

## BOUNDARY

- ALLOWED_WRITE: controller declaration/Resolved DTO/compiler validation、Observation DTO/core gateway adapter、strict claim validation、formal scenario endpoint data、显式 legacy adapter/warning、定向测试和记录。
- PROHIBITED: shared-contact transport（EF-06B）、command transport（EF-06C）、inbox（EF-06D）、S6 身份认证、S7 状态公开扩展、依赖变更、提交或推送。

## ACCEPTANCE

- controller 只能提交 claim 内实体的 action；Observation 公开 controller slot 和 controlled IDs，own_entities 恰为该 claim 覆盖的 active/degraded 实体基础状态。
- formal V2 controller 缺少有通信组件的 endpoint 时编译失败；不得从第一个 claim 推断 endpoint。
- 当前 faction Observation 如需保留，只能经显式 legacy adapter 并带可检测 warning；不恢复全 faction 真值。

## OUTPUTS_AND_EVIDENCE

- `ObservationV2` 现含 `controller_slot_id`、`controlled_entity_ids`、organic/shared/message 分层字段；`controller_observation_snapshot` 仅返回 claim 中 active/degraded 实体的基础 own-state。
- controller authority token 的现有逐动作 claim 校验保留并由定向反例覆盖；scope metadata 明确其不是 S6 鉴权。
- formal V2 编译器拒绝缺少 `controller_endpoint_ref` 的 controller；MD-AD-002 与 MD-INT-003 六个 formal package 都显式绑定同阵营 communication endpoint。旧 faction DTO 仅经 `legacy_faction_observation_snapshot`，每次带 `legacy-faction-observation@2.0` warning。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/pytest -q tests/contract/test_engine_defects_s5a_controller_scope.py tests/contract/test_world_controller_ownership_v2.py tests/system/test_jamming_observation_v2.py` — 39 passed.
- `compileall` 与受影响文件 `git diff --check` 通过。

## COMPATIBILITY_AND_ADMISSION

- 旧 faction 调用保持可用，但已可检测地标记为 legacy；不会伪装为 controller-scope DTO。历史 Resolved 未声明 endpoint 仍可读，formal V2 helper 将其拒绝。
- 风险：controller endpoint 是公开数据/控制契约，并非认证边界；S6 仍未实施。共享 contacts、命令 transport 和 inbox 尚未实施。
- EF-06B 准入：通过；仅实现 shared-contact transport。

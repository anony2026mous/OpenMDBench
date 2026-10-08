# RF-00R12 remaining historical P1 disposition

STATUS: COMPLETE / RF-00-QUALITY-GATES-PENDING
TASK_ID: RF-00R12-P1-DISPOSITION
TEST_LEVEL: T0

## Closed by remediation

| Historical finding | Status | Evidence |
|---|---|---|
| P1-01 AD2 dynamics/energy profile mismatch | CLOSED | `platform_refactor_rf_00_r9.md` |
| P1-02 MD-INT legacy-track legalization | CLOSED | `platform_refactor_rf_00_r11.md` |
| P1-06 open shoreline closure | CLOSED | `platform_refactor_rf_00_r10.md` |
| P1-07 AD2 adjudication using current distance | CLOSED | `platform_refactor_rf_00_r6.md` |
| P1-08 MD-INT all_interceptors unreachable | CLOSED | `platform_refactor_rf_00_r5.md` |
| P1-10 REST AD2 replay missing frames | CLOSED | `platform_refactor_rf_00_r8.md` |
| P1-11 spawn order stability | CLOSED | `platform_refactor_rf_00_r7.md` |

## Dispositioned to accepted future work packages

The items below remain real current-engine capability limits. They are not falsely marked implemented; the Accepted platform ADR assigns their implementation and final verification after RF-00.

| Historical finding | RF-00 disposition | Required implementation gate |
|---|---|---|
| P1-03 EASY communication bypass | ACCEPTED MIGRATION GAP | RF-06 command lifecycle/TTL and RF-11 formal scenario migration must route commands through the unified communication contract while preserving an explicit compatibility adapter. |
| P1-04 MEDIUM communication/configuration fork | ACCEPTED MIGRATION GAP | RF-02 versioned resources, RF-06 gateway, and RF-11 migration must remove difficulty-branch command semantics through resolved configuration. |
| P1-05 MMG shared native core | ACCEPTED ISOLATION GAP | RF-ADR-001 decision 12 requires spawn worker isolation when thread isolation cannot be proven; RF-13/RF-14 own 16/32-session and native-state evidence. |
| P1-09 AD2 three/seven weight fork | ACCEPTED VERSIONING GAP | RF-02/RF-11 must introduce a versioned seven-metric scoring resource and compatibility adapter; RF-15 must review config-hash/golden migration. Existing v2 fixtures must not be silently rewritten in RF-00. |

## Rationale

RF-00 is the audit/baseline/ADR phase. Implementing these four items directly in legacy v2 would prematurely perform RF-02/RF-06/RF-11/RF-13/RF-14/RF-15 work, change frozen communication timing or configuration hashes, and bypass the approved migration sequence. Their acceptance criteria remain binding in the named work packages.

This disposition does not claim the current engine already has unified EASY/MEDIUM command routing, per-session thread-safe MMG state, or seven-weight configuration. It only resolves their RF-00 handling through the user-approved ADR and implementation plan.

## Remaining RF-00 gate

Run the final repository quality gates and independent diff review. RF-01 remains prohibited until those results are passing or every failure is accurately classified and remediated.

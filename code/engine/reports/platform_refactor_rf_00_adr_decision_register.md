# RF-00 proposed ADR decision register

STATUS: ACCEPTED
TASK_ID: RF-00R1-EVIDENCE-001

用户于 2026-08-25 明确批准本表全部推荐方案；正式决定、影响和验证要求已固化到 `docs/adr/RF-ADR-001-platform-foundation-decisions.md`。批准不等同于 RF-00 门禁通过，也不单独授权公共契约变更。

| Topic | Status | Options | Proposed recommendation | Compatibility risk |
|---|---|---|---|---|
| Modular monolith | ACCEPTED | A single in-process modular monolith; split services now | Keep a modular monolith with a fixed authoritative tick pipeline. | Premature service separation can duplicate state/order. |
| ResolvedScenario as only formal input | ACCEPTED | Accept raw YAML/dicts at runtime; compile once to immutable input | Compile first; formal sessions accept only immutable ResolvedScenario. | Legacy loaders need explicit adapters and hash migration. |
| Catalog identity `id@semver` | ACCEPTED | Latest implicit lookup; exact version references | Use exact `id@semver` with content/schema hashes. | Existing scenarios without versions need migration/failure policy. |
| Single writer | ACCEPTED | Direct API/Gym/GUI WorldState mutations; one session writer | One SimulationSession writer; other clients enqueue/read DTOs. | Direct callers must migrate; concurrency behavior changes need tests. |
| Runner modes | ACCEPTED | Independent loops; Continuous/Lockstep/Replay under one mode contract | Define Continuous, Lockstep and read-only Replay with fixed physical tick semantics. | Existing request-driven entry points require compatibility adapters. |
| Persistent vs. discrete actions | ACCEPTED | One undifferentiated action type; separate lifecycles | Separate persistent commands from one-shot discrete actions. | Existing three action paths require mapping and duplicate-fire regression tests. |
| Stale action and TTL | ACCEPTED | Implicit timing; versioned timestamp/TTL with stable rejection codes | Require timestamps, sequence/idempotency and explicit stale/TTL policy. | Clients without fields need versioning or rejection/migration. |
| Read-only Observation | ACCEPTED | Observation may touch state/advance; immutable published snapshot | Observation is immutable and does not advance or expose WorldState. | Existing direct environment readers must use snapshots. |
| VisualizationFrame and views | ACCEPTED | Renderer reads WorldState; versioned immutable frames filtered by view | Shared versioned VisualizationFrame with referee/red/blue/public filtering. | Existing frames/replay schemas need explicit compatibility handling. |
| Live backpressure | ACCEPTED | Unbounded/blocking delivery; bounded drop-oldest bus | Bounded drop-oldest live queue; authoritative logs never dropped. | Consumers must tolerate frame gaps. |
| Replay does not resimulate | ACCEPTED | Replay reruns kernel; reader consumes recorded artifacts | Replay reads versioned logs/frames only and verifies map/config hashes. | Historical replay files may need reader adapters or rejection. |
| MMG/Taichi isolation | ACCEPTED | Shared native state; session/process isolation | Use proven isolation; spawn workers where native state is not thread-safe. | Performance/deployment changes; requires concurrency evidence. |
| Schema compatibility | ACCEPTED | Ad hoc changes; semantic versioning, deprecation and migration | Version public DTOs, preserve compatible additions, document major migrations. | All REST/Python/Gym/Vector/replay consumers must move together. |

## Decision boundary

本登记表的推荐已被接受，ADR coverage 的“等待用户决策”部分关闭。RF-01 仍需等待 RF-00 其他失败项修复、复测和重新审查，不得仅凭 ADR 批准进入。

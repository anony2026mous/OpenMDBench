# RF-00A current-state audit — transcribed evidence

STATUS: DONE (historical worker result; this R1 only persists evidence)
TASK_ID: RF-00A
TEST_LEVEL: T0 (historical); no test was run while creating this record.

## Provenance and scope

This is a faithful operational transcription of the RF-00A worker-return summary supplied in `RF-00R1-EVIDENCE-001`, cross-checked only against the current source locations named by that summary. It is **not** an original worker-terminal transcript and it does not claim a new architecture analysis.

## Historical result

- **MISSING:** Catalog, ScenarioCompiler, ResolvedScenario, SimulationSession, CommandQueue, ContinuousRunner, and AgentGateway.
- **PARTIAL:** unified Observation/Action, determinism, checkpoint, live/replay, and MMG isolation.
- Existing direct paths include environment/world use, three action paths, two replay paths, and three checkpoint paths.

## Current source-location cross-check

| Evidence location | Current observable evidence | RF-00A relevance |
|---|---|---|
| `openmdbench/scenarios/loader.py:16-24` | `load_scenario` and `load_scenario_id` load `Scenario` directly. | Legacy loader path; no recorded ScenarioCompiler. |
| `openmdbench/scenarios/runtime.py:49` | `ScenarioRuntime` exists. | Runtime exists but is not the immutable ResolvedScenario described by the target architecture. |
| `openmdbench/core/world.py` | Existing world implementation is the current authority path cited by RF-00A. | Reuse/adapt candidate, not a new parallel world. |
| `openmdbench/envs/benchmark.py:1347-1427` | `step_bilateral` calls `self.step(...)`, then `resolve_combat(...)`. | Existing direct environment stepping remains material to the audit. |
| `openmdbench/api/sessions.py:161-196,201-230` | session manager invokes `session.env.step(...)` / `step_red_action_batch(...)`. | API reaches environment/session objects directly; no recorded AgentGateway. |
| `openmdbench/runners/md_ad_002.py:194-253` | Runner computes external `metric_state`, logs it, and checkpoint payload contains simulation plus two agent snapshots. | Existing runner/log/checkpoint path is partial. |
| `openmdbench/visualization/*` | Live renderer/playback consume current visualization structures. | Live chain exists, but shared versioned VisualizationFrame contract remains partial. |
| `openmdbench/replay/reader.py:20-119` | `ReplayReader` parses metadata and visualization frames from disk. | Replay reader exists; it is not evidence of the required unified replay contract. |

The specific class-name scan of these locations found no `ScenarioCompiler`, `ResolvedScenario`, `SimulationSession`, `CommandQueue`, `ContinuousRunner`, or `AgentGateway` definition. This is only a mechanical cross-check of the supplied RF-00A conclusion, not a claim of exhaustive repository search.

## Risks and uncompleted gate work

- Public API, Gym and REST semantics have not been proven to share one gateway.
- Current partial determinism/checkpoint/live/replay/MMG evidence is insufficient to close target-platform requirements.
- This historical DONE marker is not RF-00 approval and must not authorize RF-01.

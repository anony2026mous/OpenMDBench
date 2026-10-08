# Four-category competition suite — candidate implementation

Current candidate-only surface mapping and cooperative tracking evidence is documented in
`openmd/doc/competition_four_categories/SURFACE_CALIBRATION.md`. Independent straight-speed
checks pass; the complete turn steady-state gate does not. Original engine mechanisms,
catalog resources and the fourteen interception scenarios remain frozen. This is not
real-vessel calibration or competition acceptance.

## Referee-only denial raw-statistic export

`denial_state_audit.py` observes existing candidate plugin snapshots without changing
native score/state or giving referee data to controllers. Use `--scenario N --policy
guard --seed 2001 --pair` for a frozen, separate-process control/observed comparison;
AD006's recorded task-aware case uses `--policy planning-lead-salvo`.
The six-scenario v1 matrix contains 12 natural-terminal episodes with exact native
result equality and 4356 recorded metric states. Export schema v2 corrects a historical
occupancy label and adds the last actual sampling tick; all saved states were re-exported
offline, and a further AD006 pair verifies v2 native behavior. This is not six new v2
native pairs, strategy calibration, checkpoint recovery, or competition acceptance.

See `openmd/doc/competition_four_categories/DENIAL_RAW_METRICS_20261001.md` for
source-bound evidence, the recorded 37-test regression, original checkpoint failures,
counter/window definitions and missing supplemental metrics. Engine files and
canonical packages remain unchanged; original archives are never overwritten.

### Public information age and final-wave cohort supplement

`denial_information_age.py --scenario N --result <frozen-result.json>` derives
measurement age from public observation/measurement ticks, retaining missing data
and original age fields. Six frozen seed2001 traces provide 4800 controller-time
rows; this is offline processing, not additional policy calibration.

`denial_state_audit.py --scenario 6 --policy planning-lead-salvo --seed 2001
--pair --breach-inputs` additionally records immutable inputs already received by
the candidate score plugin. The corrected native pair preserves all 43 result
fields and verifies every tick's existing breach counter. AD006's one late-window
entry is from the middle wave; the final declared spawn cohort has zero entries.
The original task still fails. The first observer-interface failure is retained.

Current supplemental regression: 61 passed, separate from the still-failing native
checkpoint acceptance tests. Definitions, limitations, failed attempt and native
evidence are in `openmd/doc/competition_four_categories/DENIAL_SUPPLEMENTAL_METRICS_20261001.md`.

## Current candidate scoring revision: 1.0.1

The tracking and delivered-dispatch candidate metric plugins now preserve N/A
before any scoring sample, rather than presenting an available numeric zero.
Only TRK001–008 and ER003/005/006 require changed model references. No assets,
deadlines, thresholds, sampled score arithmetic or engine mechanisms changed.
The prior 300-episode collection remains immutable evidence for its original
candidate revision; it is not current-revision calibration.

Seed1301 bounded native receipt probes cover all eleven affected packages and
355 advancement ticks, with 366 JSONL rows including initial observations.
Availability checks pass in every probe. The 47 checkpoint attempts retain
32 native integrity failures and 15 successful extractions; extraction does not
prove full restore equivalence. These are idle boundary probes, not full
natural-terminal experiments, controller comparisons or competition acceptance.

Evidence: `artifacts/competition_four_categories/availability-native-20261001T041110286365Z/report.json`.
Scope and limitations: `openmd/doc/competition_four_categories/SCORE_AVAILABILITY_REVISION.md`.

## Frozen cross-scenario calibration

The later, separately frozen native invariance matrix is documented in
`openmd/doc/competition_four_categories/NATIVE_INVARIANCE.md`. It covers all
30 packages with five full-episode conditions each: baseline, repeat, native
scenario rename, declaration reversal and resource/model registration reversal.
The completed seed1701 plan is
`artifacts/competition_four_categories/native-invariance-plan-20261001T052359023264Z/plan.json`.
All 150 episodes are recorded and independently read back for identity, trace
hashes, complete natural terminals and immutable inputs. The next case is null.
Repeat, native rename and registration reversal each have30/30 byte-identical
journal pairs; declaration reversal has13/30, with public behavior changes in
three packages. Do not relabel this completed source archive for a later revision.
Full evidence is in `native-invariance-complete-review-20261001T114835585733Z.json`;
requirement-level limitations are in
`openmd/doc/competition_four_categories/COMPETITION_ACCEPTANCE_REVIEW_20261001.md`.
Collection completion is not competition acceptance. A pilot exposed resolved-hash-dependent
communication loss-sample changes after declaration reversal; identical scores
in a zero-loss setting do not establish general invariance. The engine remains
unchanged, failures are retained, and checkpoint recovery is still a separate gate.

Completed frozen collection:
`artifacts/competition_four_categories/calibration-plan-20260930T233933542581Z.json`.
It reserves previously unused seeds **1201–1205** in that order: 30 difficulty
instances × two preselected controls × five seeds = **300 planned episodes**.
The A/B controls differ by task family; this is not a uniform-policy leaderboard,
LLM/RL comparison, or proof of statistical significance. Native failures and
missing metrics remain explicit. Preparing a plan is not completing its trials.

Seeds **1201–1205 are fully recorded (60/60 each)**; collection is
**300/300**. `CALIBRATION_PROGRESS.json` records `collection_complete=true`,
`next_case=null`, and `goal_complete=false`. Collection completion is not
competition acceptance.
`calibration-seed1201-summary-20261001T003033014984Z.json` records the complete
identity/hash/trajectory verification and all 30 paired outcomes. Sixteen pairs
have task completion only for B, thirteen complete for both controls, and one
completes for neither. These task-specific pairs are not a common algorithm
leaderboard or a statistical-significance result. Twelve episodes retain native
checkpoint failures across six scenarios, and 28 episodes lack a recorded
checkpoint-extraction result. No such missing/failed gate is counted as passed.
The original engine, frozen candidate sources and canonical inputs remain
unchanged; formal competition acceptance is still unproven.

`calibration-seed1202-summary-20261001T011757083219Z.json` adds the second
complete seed: fifteen pairs complete only for B, twelve complete for both,
and three complete for neither. The latter are TRK005, TRK008 and AD006;
TRK005/008 differ from the first seed and demonstrate why one favorable seed
is insufficient. Seed1202 again records twelve checkpoint failures and 28
episodes without checkpoint-extraction evidence. All 120 raw artifacts were
rechecked for identity, trace digest, summary consistency and native episode
completion without modifying the frozen sources or canonical inputs.

`calibration-seed1203-summary-20261001T020541033810Z.json` records the third
complete seed: fifteen pairs complete only for B, thirteen complete for both,
and two complete for neither (TRK008 and AD006). Twelve native checkpoint
failures and 28 cases without checkpoint-extraction evidence remain explicit.
All 180 recorded artifacts have been rechecked against the frozen case identity,
trace digest, summary and native episode completion. The slower TRK008 process
was observed through its original execution handle and owned process identity;
it completed naturally and was not restarted. This does not change the remaining
calibration or formal acceptance requirements.

`calibration-seed1204-summary-20261001T025223546713Z.json` records the fourth
complete seed: sixteen pairs complete only for B, thirteen complete for both,
and one completes for neither (AD006). Twelve checkpoint failures and 28
episodes without checkpoint-extraction evidence remain explicit. All 240
recorded artifacts have been revalidated for identity, trace digest, summary
consistency and native episode completion. At that checkpoint 1205 had not
started; no competition acceptance claim was made.

`calibration-seed1205-summary-20261001T034207665863Z.json` records the fifth
seed: fifteen pairs complete only for B, thirteen complete for both, and two
complete for neither. `calibration-complete-summary-20261001T034207665863Z.json`
contains all 300 verified identities, hashes, trajectories, native outcomes and
the five-seed raw metric distributions for every difficulty instance. There are
205 task-completion episodes, 60 recorded checkpoint failures and 140 episodes
without checkpoint-extraction evidence. AD006 has no task-success episode among
its ten frozen controls; this does not prove that the scenario is impossible.

**Confirmed score-contract issue:** 80 tracking episodes report available zero
for one or more metrics before their declared measurement window. The declared
contract requires unavailable=N/A, not zero. Evidence is in
`contract-review-prewindow-availability-20261001T030903805368Z.json`; the complete
summary enumerates the affected cases/ticks. These raw records are preserved,
not retrospectively edited, and the behavior is not accepted as compliant. This
finding does not itself establish that final in-window numeric comparisons are
wrong, but it must be addressed in a separately identified candidate revision.

`completion-audit-20261001T034644190148Z.json` separates verified structure/data
coverage from confirmed failures and unproven requirements. The full original
candidate source and canonical inputs are archived with hashes under
`frozen_versions/calibration-plan-20260930T233933542581Z-complete/`. Engine
mechanisms and original interception scenarios remain untouched.

**The completed plan, source archive and raw results are immutable historical
evidence.** Its collection used unchanged source/input hashes. Candidate repairs
now require an explicitly new revision and new unused validation seeds; do not
silently relabel or retune this completed collection.
The adjacent `.state.json` binds recorded artifacts and records active child
PIDs/logs. Unknown/running cases, stale locks and execution errors require actual
process/log/evidence reconciliation, never blind retry. A timeout is not proof
that the child has stopped. Local execution is not a promise of surviving a
computer shutdown.

The command below is retained for reproducibility. The completed plan has no
remaining cases; do not use it to validate a changed candidate version:

```powershell
$env:PYTHONPATH = (Resolve-Path 'openmd/source-code/source_codes').Path
$env:OPENMDBENCH_ROOT = $env:PYTHONPATH
$py = 'C:/Code/source-code/source_codes/.venv/Scripts/python.exe'
& $py -B -m tools.competition_four_categories.calibration_matrix --run-plan 'openmd/source-code/source_codes/artifacts/competition_four_categories/calibration-plan-20260930T233933542581Z.json' --max-cases 4
```

## Public-capability screening study

The subsequent AD006 controller study is documented in
`openmd/doc/competition_four_categories/AD006_REFERENCE_CONTROLS.md`.
Seeds1401/1402 completed four frozen native episodes comparing contact-centroid
and observed-velocity screening; neither control completed the task. The study
also exposed a queued-versus-executed accounting error: an own rejected request
still consumed the reference controller's local ammunition/flight reservation.
An isolated `receipt-aware-salvo` control reconciles only whitelisted own request
execution statuses. It does not expose referee missile/hit/opponent state or
change native resources, scene rules or engine mechanisms. Tests and complete
episode results are separate evidence; do not promote an accounting unit test
or improved detection time to competition acceptance.
The separate seed1501/1502 receipt-aware study also completed all four natural
terminal episodes. Own native rejection/refund/retry behavior and unchanged
ammunition budgets are verified, but neither paired control completes AD006.
One receipt-aware case improves protection to 0.995833 while still failing
the native breach gate. Post-step geometry is not a replacement for native
adjudication, especially when entities disappear within a simulation step.
The source-bound 132-test controller regression passes; native checkpoint
failures remain recorded. Both study plans, source archives, traces and
comparison reports are retained without changing any original scenario.

AD public briefs now expose own platform mobility, initial own positions,
nominal sensor ranges and existing navigation limits directly from the declared
resources. Native entities, ammunition, hit models and score rules are unchanged.
The original AD006 surface station is at least 1090 m from the southern zone,
outside its 1000 m nominal range. `screen_guard_policy.py` tests public-geometry
repositioning with unchanged selectable guard/salvo weapon policies. It never
reads hidden wave plans, target roles or referee flight state.

`screen-control-plan-20260930T230856821389Z.json` freezes the seed601 2×2 study.
`screen-control-comparison-20260930T233757821314Z.json` records that movement
makes the previously unseen southern contact observable and changes shot
allocation, but **none of the four controls completes AD006**. Parameters were
not changed during those episodes. This is a retained limitation, not a solution.
The report separates rejected requests from expected cancellation of persistent
commands when entities are destroyed; generic error-code counts must not be
interpreted as rejection counts.

`pytest-screen-calibration-20260930.xml` and its log/provenance sidecars record
76 passing targeted tests, including an existing native missile/damage fixture,
with unchanged sources/inputs during the run and unchanged protected engine
inputs. These tests do not constitute release acceptance.

## Current development-seed coverage (2026-09-30)

`artifacts/competition_four_categories/seed601-current-coverage-20260930T224503582189Z.json`
inventories source/input-matched seed601 runs for all **28 base scenarios**.
Every base scenario has a recorded natural terminal, continuous trajectory
ticks, and an initial/every-step native visibility audit. Twenty-seven have at
least one task-success record under the selected development baselines;
**AD006 does not yet have task-success evidence in this revision**.
This is a feasibility inventory across different policies, not a uniform-policy
win rate or evidence of held-out generalization.

REC006/007/008, ER006, AD004 and AD006 report native checkpoint failures.
The audit now recognizes both `native_checkpoint_evidence` and the AD recorder's
`native_terminal_checkpoint_gate`; the latter's failed checks were previously
only visible in the raw artifact. Missing evidence remains unrecorded, and
successful extraction is not promoted to restoration-equivalence proof.
`STATUS.json` still reports zero formally accepted scenarios. Multi-seed
controls, complete-contract verification, calibrated difficulty/duration and
the unresolved checkpoint requirements remain open. No engine or original
interception scenario is modified to turn these gates green.

## Public task contracts and control trials (2026-09-30)

ER002/006's native success conditions already required 65% contact continuity,
but their public briefs omitted that standing goal. `standing_missions` now
publishes the requirement, freshness definition and a coarse operating sector
around the own-side support station. It does not disclose the hidden contact ID,
fault time or an exact future incident destination. The eight affected AD/ER
native `scenario.yaml` files remain byte-identical to their archived versions.
AD inventories now expose the existing guided weapon's flight speed/lifetime
parameters; weapon effects, ammunition, hit probabilities and scoring are unchanged.

`task-contract-control-study-20260930T223909544362Z.json` in the artifact
directory records both positive and negative development findings:

- `validate_salvo_denial` is an isolated experimental entrypoint. Its original
  guard control reproduces the earlier outcome while recording native flights.
  The original guard launches six rounds at one contact before those flights
  finish. Waiting for estimated assessment in the new `salvo` policy does **not**
  solve AD006: protection falls from 0.9833 to 0.7875 on seed601. This is a
  retained negative result, not a recommended improvement or a promoted baseline.
- `validate_standing_response` adds stable incident assignment and returns to
  the published watch. `watch-coordinated` raises continuity from 0.2207 to
  0.5541 but still misses 0.65. `progress-watch` estimates motion attenuation
  only from stable own-velocity/issued-command pairs, compensating within the
  existing 80 m/s action limit. It reaches 0.6519 and the unchanged native task
  success at tick199, with safety/arrival/triage all 1.0. This early natural
  terminal is not evidence of surveillance through the maximum tick241.
- Both ER controller versions still report `FAILED_CHECKPOINT_GATE`. AD's
  corresponding native checkpoint failures are also retained, not hidden by
  successful command exits or a high task score.

Original controller/action adapters remain intact. New entrypoints reuse the
existing authorized actions; referee-only missile state is never an agent input.
The historical public briefs and sources are preserved in `frozen_versions/`.
`pytest-task-contract-controls-20260930.xml` and its log/provenance sidecars
record 101 passing targeted unit/configuration/native regression cases with
unchanged source/config hashes during the test and the unchanged protected
226-file inventory. These are development trials, not held-out calibration,
LLM/RL experiments, real-world calibration or competition acceptance.

## Observation-only REC controls (2026-09-30)

`observation_search_policy.py` and `validate_observation_search.py` add isolated
public-observation patrol/adaptive baselines without editing the original
`recon_policy.py`, its runner, canonical scenarios or engine. Both controls use
12 m/s air and 8 m/s surface cruise settings within the existing dynamics
limits. The original coordinated baseline uses 6 m/s surface cruise, so it is
not a matched-speed control. Adaptive pursuit begins only after the controller
visits its assigned public survey cells; it uses actual measured positions,
not target identities, hidden event times or the opponent's future plan.

```powershell
& $py -B -m tools.competition_four_categories.validate_observation_search --scenario 6 --seed 601 --mode paired
```

Each run streams initial DTOs, all per-tick controller observations/submitted
actions, policy diagnostics, and a final status to a **referee-only JSONL**
artifact. Every record is flushed as produced; interrupted streams are not
complete trials. The result binds the stream digest, source hashes, settings
and canonical input hashes. The audit rejects truncated streams, mismatched
DTOs/actions, altered sources/settings and forged final-status summaries.

`artifacts/competition_four_categories/observation-search-feasibility-rec006-20260930T211221845943Z.json`
records the seed601 pair. Both reach the unchanged native task objective with
coverage/discovery 1.0, fresh-contact fraction 0.3333 and information timeliness
0.4058. Their primary scores tie; the adaptive policy submits 116 contact
reports versus 91 for the same-speed patrol. There is **no observed primary-score
advantage from following contacts in this pair**, and no statistical or held-out
generalization claim. Both streams contain all 241 steps plus initial/final
records; no action receipt is rejected.

Both runs still retain `FAILED_CHECKPOINT_GATE` for the frozen engine's
unavailable-score receipt issue. Task feasibility is not release acceptance.
`pytest-observation-search-20260930.xml`, `.log` and `.provenance.json` record
88 passing targeted unit/configuration/evidence-integrity checks, with unchanged
source/package hashes and the unchanged 226-file protected-input inventory.

## Terminal-event declaration repair (2026-09-30)

The new REC/TRK/AD/ER generators now declare separate success and timeout
marker events. Previously both qualifying rules emitted `event.deadline`,
which caused native checkpoint validation to reject the deduplicated terminal
receipt. Rule conditions, priorities, rankings, deadlines, metric thresholds,
platforms and all protected engine files are unchanged by this repair.
ER006's extended deadline also applies to its two result markers.

`artifacts/competition_four_categories/pytest-terminal-evidence-20260930.xml`
and its `.provenance.json` / `.log` record **154 passing targeted tests**,
including all 30 difficulty packages (28 base scenarios), four native
simultaneous-terminal fixtures, affected fixtures and historical-input checks.
Source and generated-package hashes match before/after the test. This subset
overlaps older reports; do not add their counts or treat it as a full release.
The older 446-test report is historical for its recorded source revision.

The paired seed601 REC002–008 rerun is recorded in
`artifacts/competition_four_categories/terminal-event-repair-rec-seed601-20260930T203124837010Z.json`.
All recorded nonterminal trace fields, per-tick terminal semantics and final
scores match their pre-repair runs exactly. Native trigger-evidence identities
intentionally change, so this is not a byte-identical replay claim.

`artifacts/competition_four_categories/terminal-repair-controls-seed601-20260930T203427017187Z.json`
records six further natural-terminal controls: TRK001 idle/cooperative, AD001
idle/guard, and ER003 idle/coordinated. Each idle run misses the objective and
each active baseline completes it, with no validation failure, every step's
trace present and the initial plus all subsequent observations audited. These
are representative development controls, not proof of calibrated difficulty
or generalization across all scenarios and seeds.

- REC002–005 complete their tasks and pass native terminal checkpoint extraction.
- REC006–008 still fail native checkpoint validation with
  `plugin score input lacks authoritative output evidence` when earlier
  group windows have genuinely unavailable scores. Their `None` values and
  missing-data status are preserved, not converted to zero to pass the gate.
- REC006's original coordinated baseline misses **information timeliness**
  (0.2464 below 0.25); its fresh-contact fraction already clears 0.2. The
  matched-speed controls above show feasibility without lowering any threshold.
- Restore fixtures compare durable state excluding fresh-adapter provenance
  hashes. `checkpoint_semantic_restore_gate` records that limited evidence;
  `checkpoint_full_hash_gate` remains unproven.

Historical failed traces and frozen inputs remain intact. The 226-file
engine/catalog/legacy freeze still matches its original captured baseline.
Current evidence remains candidate validation, not competition acceptance,
held-out calibration, or an LLM/RL comparison.

`TRACKING_COMPARISON.md` in the same documentation directory reports the complete
seed601 idle/follow/cooperative comparison for all eight tracking candidates.
The additional `allocated` baseline lives in `allocated_tracking_policy.py` and
uses an isolated runner so the original policy/validator sources remain unchanged:

```powershell
$py = 'C:/Code/source-code/source_codes/.venv/Scripts/python.exe'
& $py -m tools.competition_four_categories.validate_allocated_tracking --scenario 5 --seed 601
```

It uses public three-dimensional measurements, temporal association and platform
assignment, never hidden target-domain labels, parsed contact identities or future
routes. The output separately hashes the evaluated policy and unchanged native
action/score adapter. Its internal track estimates are diagnostics, **not**
delivered contestant track reports. Referee traces
remain evaluation-only data and must not be supplied to contestants as observations.
`ALLOCATED_TRACKING_VALIDATION.md` records the frozen pre-report-contract 32-episode development
matrix, the frozen weather holdout result (1/3 task successes), the exact
from-scratch repeat, and the still-unmet acceptance conditions.

TRK007/008 now additionally require native-delivered `track-report@1.0` identity
reports. `TRACK_REPORT_PROTOCOL.md` defines public fields, raw and utility
thresholds, organic-only provenance and the remaining position-error gap. The
extra model is registered only when declared by a package. Earlier TRK007/008
results remain historical evidence, not acceptance of the added report contract.

```powershell
& $py -m tools.competition_four_categories.validate_tracking_reports --scenario 7 --mode honest --seed 601
```

Modes `silent` and `swapped` provide communication and identity negative controls.
Preserve raw metric availability and the native terminal outcome.
`TRACK_REPORT_VALIDATION.md` records six earlier seed601 trials of the spatial
association baseline, which did not meet the full task thresholds. Those results
and the earlier TRK008 `cue.02` omission remain preserved.

`IDENTITY_TRACKING_VALIDATION.md` records the persistent-identity and actual peer
communication baseline. It uses opaque token equality, never token contents.
TRK007 passes the native task for development seed601 and preregistered
seeds801/802/803; that version of TRK008 remains incomplete and has no report for `cue.06`.

```powershell
& $py -m tools.competition_four_categories.validate_identity_tracking --scenario 7 --mode honest --seed 601
```

For this baseline, `silent` suppresses official sink reports only; peer binding
traffic remains active. `swapped` changes official labels only. These are
candidate feasibility checks, not full competition acceptance.

`SHORE_BEACON_VALIDATION.md` records the next isolated agent extension. A declared
stationary observer broadcasts only its own measured bindings through native
messages; official reporters and scoring rules are unchanged. On TRK008/601 all
six labels now receive mobile reports, but minimum report coverage is only
39.82% and the native task remains incomplete.

```powershell
& $py -m tools.competition_four_categories.validate_beacon_tracking --scenario 8 --mode honest --seed 601
```

`COVERAGE_BUDGET_CALIBRATION.md` records controlled policy/asset experiments kept
outside the canonical scenario directory. The reference-aligned DEF-P3 profile
uses 2 UAVs, 3 USVs and 2 shore observers. After a native collision diagnosis and
an agent-only range-hold correction, the short profile passes seed601 and
preregistered seeds901/902/903; its complete sink-silent negative control fails.
The validated profile is now promoted to the **canonical TRK008 candidate**, not
competition acceptance. At promotion, the standard seed601 entrypoint exactly reproduced
all 241 trace ticks, terminal evidence, actions and delivered messages from calibration.
See `TRK008_CANDIDATE_PROMOTION.md` for the input-isolation and test evidence.
The later localization-audit version timed out at its 285-second limit on TRK008;
that additional verification remains pending rather than inheriting an old pass.

```powershell
& $py -m tools.competition_four_categories.validate_coverage_tracking --scenario 8 --mode honest --seed 601
```

The original four-cell calibration retains three complete failures and one
timeout with no complete score. Partial 60-tick motion probes are diagnostics,
not completed trials. Only the TRK008 candidate scenario and public brief changed;
the other 29 package variants, scoring thresholds and protected engine files did not.
For further calibration, `--profile current` now means canonical DEF-P3; use
`--profile legacy-four-observers` for the pre-promotion sparse asset layout.

## Task package

- TASK_ID: SCENARIO-28-20260929.
- RF stage: no existing RF stage is advanced or declared accepted; this is an isolated
  scenario/model-extension candidate using the existing native compiler and session.
- Objective: **28 distinct base scenarios**, REC 8 / TRK 8 / AD 6 / ER 6. Difficulty
  variants do not count toward those 28. The final deliverable remains the full suite.
- Inputs: `openmd/doc/OpenMDBench.md` Appendix A; user-supplied
  `task_settings_v2.0_parameterized.md` sections 1–10 and 14–15; engine `AGENTS.md`;
  current V2 catalog/compiler/mission/session APIs and their contract tests.
- ALLOWED_READ: these specifications, existing native code, fixtures and local results.
- ALLOWED_WRITE: this tool directory, `scenarios/competition_v1`,
  `catalog/v2/competition_four_categories.yaml`, `artifacts/competition_four_categories`,
  `openmd/doc/competition_four_categories`.
- PROHIBITED: simulation-kernel edits, old scenario/catalog/registry edits, old experiment
  restarts, installing dependencies, training, git commits/pushes, cloud synchronization.
- TEST_LEVEL: T2 new-module tests and bounded new-candidate smoke episodes only. No full
  repository suite, performance study, long training or prior experiment-gap filling.
- Commands: Python module build/validate, targeted pytest in this directory; read-only
  file inspection and scoped diffs; apply_patch within the write scope.
- Budget: one command <= 5 minutes, one local validation group <= 15 minutes.
- Output: declarative packages, public briefs, resolved/source hashes, raw local traces,
  explicit candidate/accepted status, test results and unmet acceptance gates.
- Stop/failure: preserve diagnostics and fail closed on invalid schema, unauthorized
  actions, missing score inputs, nondeterminism or privacy leaks; do not zero-fill missing
  scores or change existing engine semantics to manufacture passing outcomes.

## Current scope (not completion)

`SCENARIO_CONTRACTS.json` in the documentation directory defines all 28 challenges,
mechanisms, success conditions and metrics. It is a **design register, not proof of
runtime implementation**.

Generated packages now cover **28 base candidates**: REC001 (three variants),
REC002–008, TRK001–008, AD001–006, and ER001–006 (one standard each). **None is
competition accepted.** Runtime coverage is now 8 / 8 / 6 / 6, but every full
contract still requires acceptance. These are short synthetic
vertical slices, not paper-duration reproductions. A score's availability, source,
definition and stopping behavior matter more than merely generating 28 YAMLs.

The pilot uses the native UAV kinematics, native MMG surface dynamics, perception,
communication, mission rules and session runner. There is no second world or simulation
loop. Agents use controller-scoped observations; the sweep baseline reads only its own
observation and the public search-sector brief. It cannot read target positions, truth
labels, resolved scenario contents or future events.

`metrics_v1.py` is a **candidate generic model plugin**, parameterized by observer/item
selectors and score window; it has no scenario-ID or fixed-faction branches. It computes:

- Distinct target recall (duplicate detections from multiple observers count once).
- Distinct visited active zones (destroyed/disabled observers do not count).
- Minimum per-target fresh-contact fraction (intended for the next tracking slice).

Metrics consume authoritative `MissionEvaluationSnapshotV2` evidence via the existing
scoring extension interface, participate in native checkpoints, and carry the actual
plugin source SHA-256 in the model registry hash. The plugin is not silently registered
in the production catalog. Local candidate registration explicitly opts in; independent
review/acceptance remains required. All numerical scenario values are **UNVALIDATED**
synthetic benchmark parameters, not calibrated real-world capability claims.

## Local reproduction

Run from `openmd/source-code/source_codes` with the existing project Python:

```powershell
$py = 'C:/Code/source-code/source_codes/.venv/Scripts/python.exe'
& $py -m tools.competition_four_categories.protected_inputs
& $py -m tools.competition_four_categories.build
& $py -m pytest tools/competition_four_categories/tests -q --tb=short
& $py -m tools.competition_four_categories.validate --difficulty easy --policy idle --seed 601
& $py -m tools.competition_four_categories.validate --difficulty easy --policy sweep --seed 601
```

The build writes only the isolated candidate asset paths. Validation writes timestamped
JSON evidence and never uploads it. Results retain scenario/difficulty/policy/seed,
native terminal receipt, per-metric outputs, trajectory, observation audit count,
action submission statuses, resolved/catalog/model hashes and trajectory digest.
Do not compare historical records from different resolved/model hashes as repeat runs.

## Unmet final acceptance gates

Visibility update: visibility_audit.py checks the unmodified controller DTO against
compiled ownership, native measured contacts, historical source samples and actual
receiver delivery. A unit.x substring alone is no longer treated as a leak. The
new rule is fail-closed on unsupported fields, forged measurements and undelivered
data; it is not an anonymizer or an authentication layer. Legacy gate evidence stays
separate. Historical complete seed601 visibility traces exist for all 28 base
candidates, but they do not certify later input or validator revisions. See
`STATUS.json` for current-hash-matched evidence; task outcomes and independent
checkpoint/calibration gates still require work.
See openmd/doc/competition_four_categories/VISIBILITY_VALIDATION_20260929.md.

Delivered-response update: response.py, message_policy.py, delivered_dispatch_v1.py,
response_policy.py and validate_response.py upgrade ER003/005/006 without kernel edits.
Task release now requires actual native recipient-specific message delivery. ER003/005
have paired development runs for seeds 601/602/603 under idle/naive/coordinated policies.
These are not held-out trials, not LLM/RL comparisons, and not competition acceptance.
Full checkpoint hashes and ER006 privacy still fail. See
openmd/doc/competition_four_categories/RESPONSE_VALIDATION_20260929.md.

Reconnaissance expansion adds REC002–008 via reconnaissance.py, recon_metrics_v1.py,
recon_policy.py and validate_recon.py. Independent sector/domain/wave windows use
minimum-group coverage and recall. Handoff requires native send_message delivery
and matching sender-owned observations; detection unions cannot stand in for delivery.
This does not fix declarative SOS delivery or contact-ID privacy. See
openmd/doc/competition_four_categories/REC_VALIDATION_20260929.md.

**Engine freeze (2026-09-29):** the user prohibits engine-mechanism changes.
`protected_inputs.py` checks a captured working-tree SHA-256 inventory of 226
engine Python files, original catalog files and formal scenario files. Candidate
catalog loading fails closed if any protected file is changed, added or removed;
each episode validator checks again after closing its session. The baseline is
never auto-refreshed, and `--capture` refuses an existing file. This preserves the
current local engine, including pre-existing uncommitted changes; it is **not**
proof that old experiment data used those exact bytes. No legacy data is rewritten
and the original 14 interception scenarios are not rerun.

**Area-denial update:** `denial.py`, `denial_metrics_v1.py`, `denial_policy.py`
and `validate_denial.py` add six single-standard candidates. They use native
spawn/control, sensors, ROE, finite ammunition, combat/damage, zone transitions
and the existing mission/scoring extension interface. No world or combat kernel
is replaced. The declared protection deadline includes all waves and cannot end
on an early kill. Native-mechanism fixtures are referee tests, not privacy-passing
agent episodes. Details are in `openmd/doc/competition_four_categories/AD_VALIDATION_20260929.md`.

`denial_harm_audit.py` adds **referee-only actual protected-target hull-damage
attribution**, without changing native scores or terminals. Immediate weapon
damage requires the complete native damage transaction ledger, not just tick
receipts. Native terminal-checkpoint failures remain explicit; a strictly verified
noncombat tail can complete supplemental evidence without accepting that checkpoint.
See `DENIAL_HARM_ATTRIBUTION.md`; missing evidence is unavailable, never zero harm.

```powershell
& $py -m tools.competition_four_categories.validate_denial --all --policy guard --seed 601
& $py -m tools.competition_four_categories.protected_inputs
```

**Tracking update:** `tracking.py`, `tracking_metrics_v1.py`, `tracking_policy.py`
and `validate_tracking.py` add eight distinct candidates. Targets execute a
content-hashed own-side plan via the normal authorized native Action API; the
plan never enters the red public brief or observer policy. Success is impossible
before the horizon. Details and limitations are in
`openmd/doc/competition_four_categories/TRK_VALIDATION_20260929.md`. Run native
MMG episodes via `python -m ...` (a real guarded entrypoint), not `python -` on
Windows, because the native backend spawns child processes.

`native_localization_audit.py` records referee-only **native measurement RMSE**,
matching actual visible contacts to measurement and truth in the same native
sensor receipt. It is not agent trajectory RMSE. TRK007/601 completes with
1,132 unique samples and an exactly unchanged native trace; observed measurement
noise parameters are zero, so near-zero error is not calibrated physical accuracy.
See `NATIVE_LOCALIZATION_VALIDATION.md` for evidence, source hashes and pending gates.

The native scoring checkpoint currently rejects history containing pre-window
`None` plugin outputs. Keep those outputs unavailable; do **not** turn them into
zero to manufacture a passing checkpoint. Tracking result files use public
step-receipt `raw_value` and `data_status` and also retain the internal score state
for diagnosis. The failing native checkpoint test remains enabled.

**2026-09-29 update:** six single-standard ER candidates now exist alongside the
REC001 pilot. These are **7 base candidates, not 7 accepted scenarios**. New tools
are `emergency.py`, `dispatch_metrics_v1.py` and `validate_emergency.py`. Full
scope, actual native evidence, reproduction commands and failed gates are recorded
in `openmd/doc/competition_four_categories/ER_VALIDATION_20260929.md`. The current
targeted suite has a real failing full-checkpoint-hash assertion and a strict
xfail for native message-event delivery; it must not be described as all green.

**Known failed gate:** strict controller contact-ID validation detects native evidence
IDs containing target entity IDs. The validator fails closed and saves a
`privacy-failure-*.json` record; the kernel is not patched or silently wrapped. See
`openmd/doc/competition_four_categories/ENGINE_DEPENDENCIES.md`. Earlier functional
success trajectories do not establish privacy compliance.

1. All 28 runtime contracts, including category-specific events and real objective logic.
2. First-detection latency and the other supplementary per-contract metrics, not only
   pilot coverage/recall; correct same-tick deadline adjudication.
3. Actual controller-visible privacy audit, opaque IDs, observation-history handling,
   protected traffic, decoys and delayed alert confirmation where appropriate.
4. Native checkpoint restore, continuous-vs-restored equivalence, rename/reorder
   invariance and invalid-action rejection for every affected mechanism.
5. Multiple fixed seeds with idle, simple and task-aware policies; failure paths and
   reachable success; evidence that difficulty and distinct base challenges matter.
6. Competition-duration/asset-budget selection, held-out seeds, evaluation protocol,
   independent review and clear release/candidate status per scenario.
7. ER scope remains navigation/dispatch. Arrival is never reported as completed physical
   rescue; unsupported communication-relay/decoy/rescue actions are not advertised.

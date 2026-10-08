# RF-00E review — authoritative transcribed report

STATUS: DONE
TASK_ID: RF-00E-REVIEW-001-R2
REVIEW_SCOPE: T0 only. Read-only review of RF-00A/B/C/D message evidence, RF-00D worktree `a23abb68`, specified logs, relevant source/tests, Makefile/CI, two platform documents, scenario requirements and Accepted ADR; no modification or retest.

## Provenance

The supervisor retrieved and verified the complete reviewer terminal `62b3307c` `last_output` through its trusted CAO status interface. The content below is transcribed from that authoritative report; R1 does not supplement or change its conclusion.

## RF-00D command verification

- T3-A: log confirms 43 passed, 1 warning, 40.17s; report exit 0; no failure.
- T3-B: 113 passed, 7 failed, 55 warnings, 321.42s; report exit 1. First failure: `test_same_process_same_seed_is_identical`; `benchmark.py:1726` constructs a `UAVCommand` with negative `altitude_m`.
- T4-C: Ruff PASS; mypy 128 errors in 9 files, first item Taichi missing typed marker; report exit 1/21.69s. Makefile stopped at typecheck: Bandit, full pytest, coverage and full_test_report are NOT_RUN.
- The three logs do not record an outer command or shell exit code. Exact prescribed command/exit is supported by JSON/Markdown, not independently by the logs.

## Failure-classification review

- Four failures (two determinism and two MD-INT system baseline) are `IMPLEMENTATION_FAILURE`, sharing the invalid `altitude_m=-213.513…` cause.
- `test_red_hold_and_no_blue_engage_reaches_timeout` is `UNKNOWN`: actual `threat_destroyed`, expected `timeout_without_breach`.
- Gym info extra `collision_events` is `UNKNOWN`: possible interface change or stale test.
- MEDIUM golden absence is `DEPENDENCY_FAILURE`: missing `artifacts/md-ad-002/medium-v2-golden.json` in the reviewed worktree.
- mypy is `MIXED`: at least six Taichi untyped-import dependency errors plus project/test type errors; it must not all be called implementation failure.

## Artifact and scope compliance

- RF-00D worktree tracked diff was empty: no tracked production/test/config modification.
- `/tmp/rf00d_*.log` was outside the authorized write scope and is ephemeral: P2 compliance/reproducibility issue.
- Baseline `input_sources` omit the two mandatory platform documents.
- Baseline JSON has `schema_version`, but no corresponding repository schema or field specification supports mechanical validation.
- RF-00A/B/C had no persisted reports, reproduction scripts, or logs; message conclusions alone were insufficient as a later auditable gate.

## Gate matrix

- Catalog, ScenarioCompiler, ResolvedScenario, SimulationSession, CommandQueue, ContinuousRunner, AgentGateway: `CONFIRMED/OPEN`.
- P0 collision-before-combat swallowing legal fire: `CONFIRMED/OPEN`.
- P0 AD2 runner checkpoint missing metric state: `CONFIRMED/OPEN`.
- RF-00B P1-01 through P1-11: `UNVALIDATED/OPEN`; do not close.
- RF-00C 403 collected: `UNVALIDATED` (no persisted log).
- RF-00C new P0/P1 reproduction nodes: `MISSING`.
- RF-00A/B/C handoff products: `OPEN` (not persisted before R1).
- ADR coverage: `OPEN` for modular monolith, unique Resolved input, Catalog id@version, single writer, runner modes, TTL/persistent-discrete, live backpressure, schema migration, and related decisions.
- RF-00D: `DONE-with-baseline-failures`; it is not RF-00 approval.

## Findings, risks, and test gaps

- **P0-1:** `benchmark.py` resolves collision and immediately destroys before `resolve_combat`, producing `attacker_unavailable` for a legal same-tick shot. Minimum remedy: collect/legalize fire and collision intents, then apply damage together with a collision-plus-legal-fire behavior test. R1 does not implement it.
- **P0-2:** `runners/md_ad_002.py` checkpoint does not include metric state, first engagement, USV warning, relay, or ammunition accumulators. R1 does not implement it.
- **P1:** MD-INT fixed-seed negative-altitude failures; MEDIUM independent golden missing; mypy red blocks safety/full pytest/coverage; RF-00 evidence/ADR gates incomplete.
- **P2:** ephemeral `/tmp` logs and nonconforming baseline schema.
- **Pre-existing:** both P0s, MD-INT altitude, MEDIUM golden, mypy red, seven core gaps and eleven P1s have no RF-00D tracked diff.
- **Test gaps:** Bandit/full pytest/coverage; four scenario fixed-seed traces; complete checkpoint/replay; concurrency/MMG; performance/soak; 403 collection log; and new P0/P1 nodes have no current passing evidence.
- **Residual risk:** T3-A’s 43 passes do not prove platform contract, fairness or determinism; `/tmp` logs can disappear; outer commands cannot be independently reconstructed from logs.

## Reviewer conclusion (unaltered)

RF-00D status recommendation: **DONE-with-baseline-failures**.
CONCLUSION: **REJECTED**.
RF_01_ALLOWED: **NO**.

Original reviewer minimum gate remediation:

1. Repair and directionally verify both P0 issues.
2. Repair MD-INT altitude failure and provide MEDIUM golden.
3. Close mypy and have an independent runner execute the security/full/coverage stages that were short-circuited.
4. Persist A/B/C/D reports, reproduction nodes, commands and logs.
5. Complete and Accept missing RF-00 ADRs, then re-review the new diff.

## Subsequent user scope decision (recorded, not a review-conclusion change)

The user directs that RF-00 first-stage minimum remediation presently performs only evidence persistence, P0 reproduction, and the ADR decision package. It does not modify production code in R1 and does not make full/coverage an R1 completion condition. The original `REJECTED` history and the reviewer’s five minimum-remediation items above remain in force.

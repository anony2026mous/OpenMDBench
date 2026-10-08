# RF-00B domain audit — transcribed evidence

STATUS: DONE / NO-GO (historical worker result; evidence persistence only)
TASK_ID: RF-00B
TEST_LEVEL: T0 (historical)

## Provenance

This record transcribes the RF-00B authoritative summary supplied to R1 and labels it as worker-return evidence plus the current source locations below. It is not an original terminal transcript and performs no new domain review.

## P0 findings — CONFIRMED / OPEN

1. **P0-01 — collision before combat:** `openmdbench/envs/benchmark.py:1347-1427` advances the environment through `self.step(...)` before constructing the combined batch and calling `resolve_combat(...)`. RF-00B records that the collision stage may destroy an entity first and cause a legal same-tick shot to be rejected/absorbed. This conflicts with the intended same-tick aggregate intent and simultaneous damage semantics.
2. **P0-02 — AD2 checkpoint omits external metric state:** `openmdbench/runners/md_ad_002.py:194-253` constructs `metric_state` and logs it, while the checkpoint payload shown at lines 235-243 contains only `simulation`, `red_agent`, and `blue_agent`. RF-00B records that metrics such as first engagement, USV warning/relay and ammunition accumulation are not restored.

## P1 findings — UNVALIDATED / OPEN

The following historical RF-00B findings are retained exactly as open and must not be closed by this R1 transcription:

1. AD2 dynamics/energy profile mismatch.
2. MD-INT legacy-track legalization.
3. EASY communication bypass.
4. MEDIUM communication/configuration fork.
5. MMG shared native core.
6. Open shoreline closure.
7. AD2 adjudication using current distance.
8. MD-INT `all_interceptors` unreachable.
9. AD2 three/seven weight fork.
10. REST AD2 replay missing frames.
11. Spawn order stability.

## Parameter evidence status

All equipment parameters are task-level **ASSUMPTION / UNVALIDATED**. This record does not supply, calibrate, or alter any dynamics, probability, damage, adjudication, or score parameter.

## Risk

P0 findings remain release-blocking for the target architecture. P1 items require reproduction or review evidence before any closure decision.

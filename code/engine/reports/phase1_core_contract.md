# Phase 1 core and public-contract report

- Date: 2026-08-05
- Status: PASS
- Prerequisite: Phase 0 PASS

## Delivered tasks

- T1.1: ADR-001 through ADR-010 accepted and checked.
- T1.2: immutable unified entities, component state, permanent session IDs, lifecycle registry,
  and a read-only legacy USV adapter.
- T1.3: fixed logical clock, stable delayed-event queue, and ordered system scheduler.
- T1.4: stable named RNG streams with checkpointable state.
- T1.5: internal WorldState and immutable allowlisted Observation DTO with leakage tests.
- T1.6: versioned minimal checkpoint containing clock, entities, events, RNG, task state, and
  configuration hash.

## Verification

```text
make lint       PASS
make typecheck  PASS (36 checked source files)
make test       PASS (46 tests)
```

Checkpoint restoration matched continuous execution for the next 100 ticks, including exact
named-RNG draws and event delivery. Public observation tests confirm that undetected enemy IDs,
referee intent, and future events cannot be serialized.

## Known warnings

- Taichi 1.7.4 emits a locale deprecation warning relevant to future Python 3.15, outside the
  supported Python 3.11/3.12 matrix.
- Gymnasium recommends normalized actions, while the benchmark intentionally exposes explicit
  physical action units.

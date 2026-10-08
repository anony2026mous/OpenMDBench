# ADR-003: CIWS envelope and cooldown

Status: Accepted

## Context

Close-in engagement requires a deterministic range and timing boundary.

## Decision

Use the frozen CIWS minimum/maximum engagement envelope and configured cooldown in the combat
legality pipeline.

## Consequences

Boundary results are stable across replay and checkpoint restore. The envelope is a scenario
benchmark parameter rather than a real-system calibration assertion.

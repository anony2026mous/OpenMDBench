# ADR-005: Breach threshold and mission latch

Status: Accepted

## Context

Multiple breach events require one stable mission outcome regardless of registration order.

## Decision

Use the frozen breach threshold and latch the resulting mission transition in the authoritative
mission state.

## Consequences

Simultaneous events yield deterministic adjudication, and the latched result survives checkpoints
and replay.

# ADR-007: Probabilistic weapon resolution

Status: Accepted

## Context

Weapon outcomes may be probabilistic but must remain reproducible under the same seed.

## Decision

Derive each legal engagement outcome from named deterministic RNG streams and resolve the tick's
damage effects through the common simultaneous-damage pipeline.

## Consequences

Changing session identity alone does not alter the same seeded action timeline; evidence records
the resolved outcome without exposing hidden RNG state.

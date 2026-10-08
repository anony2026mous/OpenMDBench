# ADR-006: Energy accounting

Status: Accepted

## Context

Platform endurance must be represented consistently across dynamics, sensors and combat.

## Decision

Use the configured energy profiles and deterministic tick consumption accounting for movement,
sensing, communications and firing.

## Consequences

Energy state is observable only through permitted DTO fields and is checkpointed. Profile values
remain benchmark assumptions.

# ADR-MDINT001-008: Authority tick order

Status: Accepted

## Context

Command application, movement, sensing, communication, combat, damage, mission and score
updates must have one stable order for determinism and checkpoint/replay equivalence.

## Options

- Permit each scenario or adapter to sequence these operations.
- Use the common fixed-tick authority pipeline.

## Decision

Apply accepted actions at the tick boundary, then advance dynamics/boundary, capability
systems, combat and simultaneous damage before mission, score, log/checkpoint and published
observation/frame outputs.

## Consequences

No reader advances the simulation and same seed/action timeline has a stable causal order.
Changing the sequence is a versioned platform decision requiring compatibility regression.

## Configuration

The fixed tick is selected by `clock` in `md_int_001_v1.yaml`; operation order is owned by
the common world/session implementation.

